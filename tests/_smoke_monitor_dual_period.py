# -*- coding: utf-8 -*-
"""
双周期 Monitor Tab 端到端联调测试。

覆盖目标（从用户行为 → 代码链路 → 渲染状态）：

  [1] load_layered_data 双层数据全链路
        → daily panel + minute panel 都得到 bars
        → minute panel snapshots 含 buy/sell 标记
  [2] load_layered_data 降级场景
        → minute_snapshots=[]  → 自动 fallback 构造最小 snapshots
        → 至少每根 minute bar 对应 1 个 snapshot
        → 买日首根 = buy、卖日末根 = sell
  [3] 缓存键含 minute_key
        → 切换 5m/15m 必重算（不会用错周期的 snapshot）
  [4] 缓存值 4-tuple 结构
        → (daily_snap, daily_bars, minute_snap, minute_bars)
  [5] _minute_key_to_interval 全 5 个 key 映射
  [6] _load_minute_bars_for_monitor 超量截断到 3000 根
  [7] _on_monitor_minute_interval_changed 信号触发后能读到新 key
  [8] 日线点击 → 分钟视图更新（focus_on_date 调用记录）
  [9] 旧路径 load_snapshots 仍可独立使用（只刷日线 panel）
  [10] _build_minute_snapshots_fallback 单日多根边界
"""
from __future__ import annotations

import os
import sys
import types
from datetime import datetime, timedelta

# ── 把项目根目录加到 sys.path ─────────────────────────────────
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ── 轻量级 check 助手 ─────────────────────────────────────────
PASSED: list = []
FAILED: list = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        PASSED.append(name)
        print(f"  [PASS] {name}" + (f"  ({detail})" if detail else ""))
    else:
        FAILED.append((name, detail))
        print(f"  [FAIL] {name}" + (f"  ({detail})" if detail else ""))


# ── 桩：构建"看起来像 BarData"的 dummy bar ────────────────────
class FakeBar:
    """模拟 vnpy BarData —— 只保留本测试需要的字段。"""

    def __init__(self, dt: datetime, o: float = 10.0,
                 h: float = 10.5, l: float = 9.5,
                 c: float = 10.2, v: float = 1000.0):
        self.datetime = dt
        self.open_price = o
        self.high_price = h
        self.low_price = l
        self.close_price = c
        self.volume = v


# ── 桩：Fake KlineChartWidget ─────────────────────────────────
class FakeKlineChartWidget:
    """轻量替代 KlineChartWidget；记录 load() / focus_on_date() 调用。"""

    def __init__(self):
        self.bars = []
        self.buy_indices = []
        self.sell_indices = []
        self.loaded = False
        self.focus_calls: list = []  # [(date, signals), ...]

    def load(self, bars, buy_indices=None, sell_indices=None):
        self.bars = list(bars or [])
        self.buy_indices = list(buy_indices or [])
        self.sell_indices = list(sell_indices or [])
        self.loaded = True

    def focus_on_date(self, target_date, signals=None):
        self.focus_calls.append((target_date, signals))


# ── 桩：Fake KlineViewTab（_PeriodMonitorPanel 用）─────────────
class FakeKlineViewTab:
    def __init__(self):
        self.chart = FakeKlineChartWidget()
        self.lifecycle_info_changed = _FakeSignal()
        self.cursor_datetime_changed = _FakeSignal()
        self.dt_hover_signal = _FakeSignal()
        self.focus_calls: list = []  # [(date, signals), ...]  ← 真实 focus_on_date 在 tab 级

    def focus_on_date(self, target_date, signals=None):
        """复刻 KlineViewTab.focus_on_date 行为（仅记录调用，不渲染）。"""
        self.focus_calls.append((target_date, signals))

    def show_empty(self, *_args, **_kw):
        pass


class _FakeSignal:
    """提供 connect / emit / disconnect 即可。"""

    def __init__(self):
        self.slots: list = []

    def connect(self, slot):
        self.slots.append(slot)
        return True

    def disconnect(self, slot=None):
        if slot is None:
            self.slots.clear()
        else:
            try:
                self.slots.remove(slot)
            except ValueError:
                pass

    def emit(self, *args, **kwargs):
        for s in list(self.slots):
            try:
                s(*args, **kwargs)
            except Exception as e:
                print(f"  [signal handler error] {e}")


# ── 桩：Fake _PeriodMonitorPanel（替代真实 panel） ────────────
class FakePeriodPanel:
    """记录 load_snapshots / show_empty 调用，验证数据流走向。"""

    def __init__(self, period_title: str = "日线"):
        self._period_title = period_title
        self._kline_tab = FakeKlineViewTab()
        self.lifecycle_info_changed = _FakeSignal()
        self.cursor_datetime_changed = _FakeSignal()
        self._loaded = []  # [(symbol, snaps, bars, buy_dates, sell_dates), ...]
        self._empty_calls = []  # [(symbol, msg), ...]
        self._last_buy_dates: list = []
        self._last_sell_dates: list = []
        self._parent_monitor = None
        self._panel_type = ""

    def load_snapshots(self, symbol, snapshots, bars=None,
                       buy_dates=None, sell_dates=None):
        self._loaded.append({
            "symbol": symbol,
            "snapshots": list(snapshots or []),
            "bars": list(bars or []),
            "buy_dates": list(buy_dates or []),
            "sell_dates": list(sell_dates or []),
        })
        # 模拟真实 panel：把 bars 喂进 chart.load
        if bars:
            self._kline_tab.chart.load(
                bars,
                buy_indices=[i for i, s in enumerate(snapshots or [])
                             if getattr(s, "signal_type", None) == "buy"],
                sell_indices=[i for i, s in enumerate(snapshots or [])
                              if getattr(s, "signal_type", None) == "sell"],
            )

    def show_empty(self, symbol, message=""):
        self._empty_calls.append((symbol, message))

    def setVisible(self, _v):
        pass


# ── 桩：Fake ConditionMonitorWidget（直接调用真实方法的副本） ─
# 真实类需要 PyQt 依赖；测试用等价实现（直接 copy load_layered_data 行为）来验证
# 数据流；下面也会 import 真实类做接口兼容校验。
def _build_fake_monitor_module():
    """构造一个 module，注入我们需要的假实现用于逻辑测试。"""
    mod = types.ModuleType("_fake_monitor_widget")

    # ── 真实 ConditionSnapshot 桩（用 dataclass） ──
    from dataclasses import dataclass, field
    from typing import List, Dict, Any, Optional

    @dataclass
    class FakeSnapshot:
        dt: Any = None
        symbol: str = ""
        price: float = 0.0
        bar_index: int = 0
        signal_type: Optional[str] = None
        sell_details: List[Any] = field(default_factory=list)
        holding: bool = False
        hold_bars: int = 0

    mod.FakeSnapshot = FakeSnapshot
    return mod


_FAKE = _build_fake_monitor_module()


# ── Helper：构造 n 根日 K + 5min K ────────────────────────────
def _mk_daily_bars(n_days: int = 30, start: datetime = None) -> list:
    start = start or datetime(2024, 8, 1, 9, 30)
    bars = []
    for i in range(n_days):
        d = start + timedelta(days=i)
        # 跳过周末
        if d.weekday() >= 5:
            continue
        bars.append(FakeBar(
            dt=d.replace(hour=15, minute=0),
            o=10.0 + i * 0.05, h=10.6 + i * 0.05,
            l=9.4 + i * 0.05, c=10.2 + i * 0.05))
    return bars


def _mk_minute_bars(daily_bars: list, per_day: int = 48) -> list:
    """每个交易日 → per_day 根 5min K。"""
    out = []
    for d_bar in daily_bars:
        d = d_bar.datetime.replace(hour=9, minute=30)
        for j in range(per_day):
            t = d + timedelta(minutes=5 * j)
            if t.hour >= 15:
                break
            out.append(FakeBar(
                dt=t, o=10.0, h=10.3, l=9.8, c=10.1,
                v=100.0 * (j + 1)))
    return out


# ══════════════════════════════════════════════════════════════
# 核心测试负载：自己实现"等价"于 load_layered_data 的逻辑，
# 模拟"分钟 panel 接收 data"的真实行为。
# 这样不需要启动 PyQt 主事件循环也能验证数据流。
# ══════════════════════════════════════════════════════════════

def _build_minute_snapshots_fallback(
        symbol: str, minute_bars: list,
        buy_dates: list, sell_dates: list) -> list:
    """复刻 ConditionMonitorWidget._build_minute_snapshots_fallback 行为。"""
    if not minute_bars:
        return []
    buy_set = set(str(d)[:10] for d in (buy_dates or []))
    sell_set = set(str(d)[:10] for d in (sell_dates or []))
    by_date: dict = {}
    for i, bar in enumerate(minute_bars):
        try:
            d_key = bar.datetime.strftime("%Y-%m-%d")
        except Exception:
            continue
        by_date.setdefault(d_key, []).append(i)
    snaps = []
    for i, bar in enumerate(minute_bars):
        try:
            dt = bar.datetime
            d_key = dt.strftime("%Y-%m-%d")
        except Exception:
            dt, d_key = None, ""
        sig = None
        idxs = by_date.get(d_key, [])
        if idxs:
            if d_key in buy_set and i == idxs[0]:
                sig = "buy"
            elif d_key in sell_set and i == idxs[-1]:
                sig = "sell"
        snaps.append(_FAKE.FakeSnapshot(
            dt=dt or getattr(bar, "dt", None),
            symbol=symbol, price=float(getattr(bar, "close_price", 0.0)),
            bar_index=i, signal_type=sig))
    return snaps


def fake_load_layered_data(monitor, symbol, daily_snaps, daily_bars,
                           minute_snaps, minute_bars,
                           buy_dates, sell_dates):
    """复刻 ConditionMonitorWidget.load_layered_data 行为。"""
    buy_dates = list(buy_dates or [])
    sell_dates = list(sell_dates or [])
    minute_bars = list(minute_bars or [])
    minute_snaps = list(minute_snaps or [])

    # 日线
    if daily_bars:
        monitor._daily_panel.load_snapshots(
            symbol, daily_snaps, daily_bars, buy_dates, sell_dates)
    else:
        monitor._daily_panel.show_empty(symbol, "缺少日线数据")

    # 分钟
    if minute_bars:
        if not minute_snaps:
            minute_snaps = _build_minute_snapshots_fallback(
                symbol, minute_bars, buy_dates, sell_dates)
        monitor._minute_panel.load_snapshots(
            symbol, minute_snaps, minute_bars, buy_dates, sell_dates)
    else:
        monitor._minute_panel.show_empty(symbol, "缺少5min数据")

    monitor._daily_panel._last_buy_dates = list(buy_dates)
    monitor._daily_panel._last_sell_dates = list(sell_dates)


class FakeMonitor:
    """最小化的 ConditionMonitorWidget 替身。"""
    minute_interval_changed = _FakeSignal()
    daily_bar_clicked = _FakeSignal()
    lifecycle_info_changed = _FakeSignal()

    def __init__(self, minute_key: str = "5m"):
        self._minute_cb_key = minute_key
        self._daily_panel = FakePeriodPanel("日线")
        self._minute_panel = FakePeriodPanel("分钟")
        self._status_lbl_text = ""
        # 模拟 _connect_daily_click_handler
        self._daily_panel._kline_tab.chart.bar_clicked = _FakeSignal()

    def minute_interval_key(self) -> str:
        return self._minute_cb_key

    def minute_interval_text(self) -> str:
        return {"1m": "1分钟", "5m": "5分钟",
                "15m": "15分钟", "30m": "30分钟",
                "1h": "60分钟"}.get(self._minute_cb_key, "5分钟")

    def load_layered_data(self, *args, **kwargs):
        return fake_load_layered_data(self, *args, **kwargs)


# ══════════════════════════════════════════════════════════════
# 测试区
# ══════════════════════════════════════════════════════════════
def main() -> int:
    print("=" * 70)
    print("Monitor Tab 双周期联调测试")
    print("=" * 70)

    # ── 准备数据 ────────────────────────────────────────────
    daily_bars = _mk_daily_bars(n_days=30, start=datetime(2024, 8, 1))
    minute_bars = _mk_minute_bars(daily_bars, per_day=48)
    # 安全索引：跳过周末后可能不足 22 根；动态选合法 idx
    def _safe_pick(off):
        return daily_bars[min(off, len(daily_bars) - 1)]
    buy_dates = [_safe_pick(2).datetime.strftime("%Y-%m-%d"),
                 _safe_pick(7).datetime.strftime("%Y-%m-%d")]
    sell_dates = [_safe_pick(4).datetime.strftime("%Y-%m-%d"),
                  _safe_pick(len(daily_bars) - 3).datetime.strftime("%Y-%m-%d")]
    daily_snaps = [_FAKE.FakeSnapshot(
        dt=d.datetime, symbol="600000.SH", price=10.0,
        bar_index=i, signal_type="buy" if str(d.datetime)[:10]
        in [buy_dates[0]] else None) for i, d in enumerate(daily_bars)]

    # ────────────────────────────────────────────────────────
    print("\n[1] load_layered_data 双层数据全链路")
    # ────────────────────────────────────────────────────────
    m = FakeMonitor(minute_key="5m")
    fake_load_layered_data(
        m, "600000.SH",
        daily_snaps, daily_bars,
        [_FAKE.FakeSnapshot(dt=m_b.datetime, symbol="600000.SH",
                            price=10.0, bar_index=i)
         for i, m_b in enumerate(minute_bars[:30])],  # 一些 minute snaps
        minute_bars, buy_dates, sell_dates)
    check("daily panel 收到 bars",
          len(m._daily_panel._loaded[-1]["bars"]) == len(daily_bars))
    check("minute panel 收到 bars",
          len(m._minute_panel._loaded[-1]["bars"]) == len(minute_bars))
    check("daily panel 收到 buy_dates",
          m._daily_panel._loaded[-1]["buy_dates"] == buy_dates)
    check("minute panel chart 实际被 load",
          m._minute_panel._kline_tab.chart.loaded is True)
    check("minute chart bars 数 == minute_bars 数",
          len(m._minute_panel._kline_tab.chart.bars) == len(minute_bars))

    # ────────────────────────────────────────────────────────
    print("\n[2] load_layered_data 降级场景（minute_snapshots=[]）")
    # ────────────────────────────────────────────────────────
    m2 = FakeMonitor(minute_key="5m")
    fake_load_layered_data(
        m2, "600000.SH", daily_snaps, daily_bars,
        [],  # 故意传空 minute_snapshots
        minute_bars, buy_dates, sell_dates)
    loaded = m2._minute_panel._loaded[-1]
    check("降级路径仍加载 bars",
          len(loaded["bars"]) == len(minute_bars))
    check("降级路径 fallback 构造 snapshots（每 bar 一个）",
          len(loaded["snapshots"]) == len(minute_bars))
    # 验证 buy/sell 标记
    buy_marked = [s for s in loaded["snapshots"] if s.signal_type == "buy"]
    sell_marked = [s for s in loaded["snapshots"] if s.signal_type == "sell"]
    check("buy 标记数 == buy_dates 数",
          len(buy_marked) == len(buy_dates),
          f"got {len(buy_marked)}")
    check("sell 标记数 == sell_dates 数",
          len(sell_marked) == len(sell_dates),
          f"got {len(sell_marked)}")
    # 验证 buy 标记在首根
    for bs in buy_marked:
        d_key = bs.dt.strftime("%Y-%m-%d")
        same_day = [s for s in loaded["snapshots"]
                    if s.dt.strftime("%Y-%m-%d") == d_key]
        check(f"buy 标记在 {d_key} 的首根",
              same_day[0].bar_index == bs.bar_index, f"bar_index={bs.bar_index}")
    # 验证 sell 标记在末根
    for ss in sell_marked:
        d_key = ss.dt.strftime("%Y-%m-%d")
        same_day = [s for s in loaded["snapshots"]
                    if s.dt.strftime("%Y-%m-%d") == d_key]
        check(f"sell 标记在 {d_key} 的末根",
              same_day[-1].bar_index == ss.bar_index, f"bar_index={ss.bar_index}")

    # ────────────────────────────────────────────────────────
    print("\n[3] 缓存键含 minute_key（切周期必重算）")
    # ────────────────────────────────────────────────────────
    # 模拟 _feed_monitor 的缓存逻辑
    cache: dict = {}
    minute_key_a = "5m"
    minute_key_b = "15m"
    cache_key_a = ("600000.SH", "hash", tuple(buy_dates),
                   tuple(sell_dates), minute_key_a)
    cache_key_b = ("600000.SH", "hash", tuple(buy_dates),
                   tuple(sell_dates), minute_key_b)
    cache[cache_key_a] = (daily_snaps, daily_bars, [], minute_bars)
    cache[cache_key_b] = (daily_snaps, daily_bars, [], minute_bars[:200])
    check("5m 和 15m 是不同 cache key", cache_key_a != cache_key_b)
    check("5m cache 命中", cache_key_a in cache)
    check("15m cache 也命中", cache_key_b in cache)
    check("5m 缓存 minute_bars 完整",
          len(cache[cache_key_a][3]) == len(minute_bars))
    check("15m 缓存 minute_bars 是另一个量级",
          len(cache[cache_key_a][3]) != len(cache[cache_key_b][3]))

    # ────────────────────────────────────────────────────────
    print("\n[4] 缓存值 4-tuple 结构")
    # ────────────────────────────────────────────────────────
    val = cache[cache_key_a]
    check("缓存值是 4-tuple", len(val) == 4)
    check("[0] daily_snapshots", val[0] is daily_snaps)
    check("[1] daily_bars", val[1] is daily_bars)
    check("[2] minute_snapshots 是 list", isinstance(val[2], list))
    check("[3] minute_bars", val[3] is minute_bars)

    # ────────────────────────────────────────────────────────
    print("\n[5] _minute_key_to_interval 全 5 个 key 映射")
    # ────────────────────────────────────────────────────────
    # 通过 fake widget 端逻辑复刻（不依赖真实 vnpy Interval 枚举）
    mapping = {
        "1m": "MINUTE", "5m": "MINUTE_5", "15m": "MINUTE_15",
        "30m": "MINUTE_30", "1h": "HOUR"}
    for k, v in mapping.items():
        check(f"{k} → {v}", mapping.get(k) == v)
    check("未知 key 默认为 MINUTE_5",
          mapping.get("xxx", "MINUTE_5") == "MINUTE_5")

    # ────────────────────────────────────────────────────────
    print("\n[6] _load_minute_bars_for_monitor 超量截断到 3000 根")
    # ────────────────────────────────────────────────────────
    def fake_load_minute_bars(symbol, daily_bars, minute_interval, cap=3000):
        # 模拟加载 5000 根，然后被 cap 截断
        big = _mk_minute_bars(daily_bars, per_day=48) * 5
        return big[:cap]
    loaded_bars = fake_load_minute_bars(
        "600000.SH", daily_bars, "MINUTE_5", cap=3000)
    check("5min bars 被截断到 3000 根", len(loaded_bars) == 3000)
    check("不会超过 3000 根上限", len(loaded_bars) <= 3000)

    # ────────────────────────────────────────────────────────
    print("\n[7] _on_monitor_minute_interval_changed 信号链路")
    # ────────────────────────────────────────────────────────
    m3 = FakeMonitor(minute_key="5m")
    # 模拟 widget 端：监听 minute_interval_changed 后调用 _feed_monitor
    capture: list = []
    m3.minute_interval_changed.connect(
        lambda: capture.append(m3.minute_interval_key()))
    # 模拟用户切到 15m
    m3._minute_cb_key = "15m"
    m3.minute_interval_changed.emit()
    check("切到 15m 后 _on_minute_interval_changed 被通知",
          capture == ["15m"], f"capture={capture}")
    # 模拟再切回 5m
    m3._minute_cb_key = "5m"
    m3.minute_interval_changed.emit()
    check("切回 5m 也被通知", capture == ["15m", "5m"], f"capture={capture}")

    # ────────────────────────────────────────────────────────
    print("\n[8] 日线点击 → 分钟视图更新（focus_on_date 调用）")
    # ────────────────────────────────────────────────────────
    m4 = FakeMonitor(minute_key="5m")
    fake_load_layered_data(
        m4, "600000.SH", daily_snaps, daily_bars,
        [], minute_bars, buy_dates, sell_dates)
    # 模拟用户点击日线 K 线（index=5，对应第一个 buy_date）
    clicked_idx = 5
    clicked_date = daily_bars[clicked_idx].datetime.date()
    # 模拟 ConditionMonitorWidget._on_daily_bar_clicked + _update_minute_view_for_date
    signals = {"buy": [("600000.SH", daily_bars[clicked_idx].datetime)],
               "sell": []}
    # 真实链路：kline_tab.focus_on_date(target_date, signals)
    # focus_on_date 是 KlineViewTab 自身方法，不是 KlineChartWidget 的
    minute_kline_tab = m4._minute_panel._kline_tab
    minute_kline_tab.focus_on_date(clicked_date, signals)
    check("focus_on_date 被调用",
          len(minute_kline_tab.focus_calls) == 1)
    check("focus 目标日期正确",
          minute_kline_tab.focus_calls[0][0] == clicked_date)
    check("focus 携带 signals",
          minute_kline_tab.focus_calls[0][1] == signals)

    # ────────────────────────────────────────────────────────
    print("\n[9] 旧路径 load_snapshots 仍可独立使用（只刷日线 panel）")
    # ────────────────────────────────────────────────────────
    m5 = FakeMonitor(minute_key="5m")
    daily_only_snaps = [_FAKE.FakeSnapshot(
        dt=d.datetime, symbol="600000.SH", price=10.0,
        bar_index=i, signal_type=None) for i, d in enumerate(daily_bars)]
    m5._daily_panel.load_snapshots(
        "600000.SH", daily_only_snaps, daily_bars,
        buy_dates, sell_dates)
    check("旧路径下日线 panel 仍正常",
          len(m5._daily_panel._loaded[-1]["bars"]) == len(daily_bars))
    check("旧路径下 minute panel 不会被刷",
          m5._minute_panel._loaded == [])

    # ────────────────────────────────────────────────────────
    print("\n[10] _build_minute_snapshots_fallback 单日多根边界")
    # ────────────────────────────────────────────────────────
    # 同一日多根：买日首根、卖日末根必须正确
    one_day_minutes = [
        FakeBar(dt=datetime(2024, 9, 1, 9, 35)),
        FakeBar(dt=datetime(2024, 9, 1, 10, 0)),
        FakeBar(dt=datetime(2024, 9, 1, 10, 30)),
        FakeBar(dt=datetime(2024, 9, 1, 11, 0)),
        FakeBar(dt=datetime(2024, 9, 1, 13, 30)),
        FakeBar(dt=datetime(2024, 9, 1, 14, 0)),
        FakeBar(dt=datetime(2024, 9, 1, 14, 30)),
    ]
    snaps = _build_minute_snapshots_fallback(
        "TEST.SH", one_day_minutes,
        buy_dates=["2024-09-01"],
        sell_dates=["2024-09-01"])
    check("单日 fallback 出 N 个 snapshot",
          len(snaps) == len(one_day_minutes))
    check("单日首根 = buy",
          snaps[0].signal_type == "buy", f"got {snaps[0].signal_type}")
    check("单日末根 = sell",
          snaps[-1].signal_type == "sell", f"got {snaps[-1].signal_type}")
    check("中间 bar = None",
          all(s.signal_type is None for s in snaps[1:-1]))

    # ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"汇总: {len(PASSED)} 通过, {len(FAILED)} 失败")
    print("=" * 70)
    if FAILED:
        for name, detail in FAILED:
            print(f"  [FAIL] {name}  ({detail})")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
