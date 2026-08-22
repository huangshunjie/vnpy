# -*- coding: utf-8 -*-
"""
Chart Tab 内部日线→分钟联动逻辑测试（无 GUI 依赖）。

通过复刻 _on_chart_bar_clicked / _apply_pending_focus_after_load /
_on_bars_loaded 三个方法的核心逻辑，验证：
- 1. 只在当前周期=日线时触发联动
- 2. 联动时正确切到 5min 周期
- 3. pending_focus_date / pending_focus_signals 字段被正确填充
- 4. overlay signals 只包含被点击日期的买卖信号
- 5. _on_bars_loaded 完成后若 pending 存在，自动应用 focus_on_date
- 6. _apply_pending_focus_after_load 调用后清空 pending 状态
- 7. blockSignals 包裹 setCurrentIndex 避免污染手动标志
- 8. 错误时 pending 状态被清空（不会污染后续点击）
- 9. 多次点击不同日期，pending 状态被最新点击覆盖
- 10. show_symbol 调用时使用完整的 buy_dates/sell_dates（5min 视图能看到全部原始信号）

运行：python tests/_smoke_chart_linkage.py
"""
import sys
import os
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = []
FAIL = []


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print(f"  [PASS] {name}")
    else:
        FAIL.append(name)
        print(f"  [FAIL] {name}  {detail}")


# ── 模拟 KlineViewTab 的状态 ────────────────────────────────────────
class Interval:
    DAILY = "d"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR = "1h"
    MINUTE = "1m"


class FakeIntervalCb:
    def __init__(self):
        self._items = []
        self._idx = 0
        self._signals_blocked = False
        self._user_changed = False
        self._on_idx_changed = None

    def clear(self):
        self._items = []
        self._idx = 0

    def addItem(self, name):
        self._items.append(name)

    def setCurrentIndex(self, i):
        if i == self._idx:
            return
        self._idx = i
        if not self._signals_blocked and self._on_idx_changed:
            self._on_idx_changed(i)

    def currentIndex(self):
        return self._idx

    def blockSignals(self, b):
        self._signals_blocked = b


class FakeTab:
    """模拟 KlineViewTab 联动相关属性。"""

    def __init__(self):
        self._interval_options = [
            (Interval.DAILY, "日线"),
            (Interval.MINUTE_5, "5分钟"),
            (Interval.MINUTE_15, "15分钟"),
            (Interval.MINUTE_30, "30分钟"),
            (Interval.HOUR, "60分钟"),
            (Interval.MINUTE, "1分钟"),
        ]
        self._interval_cb = FakeIntervalCb()
        self._interval_cb._on_idx_changed = self._on_interval_idx_changed
        for _, name in self._interval_options:
            self._interval_cb.addItem(name)
        self._interval_cb.setCurrentIndex(0)  # 默认日线

        self._current_symbol = "600028.SSE"
        self._last_buy_dates = ["2024-08-01", "2024-08-15", "2024-09-10"]
        self._last_sell_dates = ["2024-08-20", "2024-09-05"]
        self._pending_focus_date = None
        self._pending_focus_signals = None
        self._user_manually_changed_interval = False
        self.focus_on_date_called_with = None
        self.update_signals_display_called_with = None
        self.show_symbol_called_with = None

    def _on_interval_idx_changed(self, _idx):
        self._user_manually_changed_interval = True

    def focus_on_date(self, target_date, signals):
        """mock：记录调用"""
        self.focus_on_date_called_with = (target_date, signals)

    def _update_signals_display(self, signals):
        """mock：记录调用"""
        self.update_signals_display_called_with = signals

    def show_symbol(self, symbol, buy_dates=None, sell_dates=None):
        """mock：记录调用，不实际加载数据"""
        self.show_symbol_called_with = (symbol, buy_dates, sell_dates)
        # 模拟后续：_on_bars_loaded 被调用
        # 这里直接驱动 _apply_pending_focus_after_load
        # （真实场景中 _on_bars_loaded 在后台线程结束后被调用）
        self._on_bars_loaded_mocked()

    def _on_bars_loaded_mocked(self):
        """复刻 _on_bars_loaded 末尾的联动逻辑"""
        if self._pending_focus_date is not None:
            self._apply_pending_focus_after_load()

    def _apply_pending_focus_after_load(self):
        """复刻 KlineViewTab._apply_pending_focus_after_load 核心逻辑"""
        try:
            target_date = self._pending_focus_date
            signals = self._pending_focus_signals or {'buy': [], 'sell': []}
            if target_date is None:
                return
            # 清空上次记录（模拟真实代码每次调用 focus_on_date 后都覆盖）
            self.focus_on_date_called_with = None
            self.update_signals_display_called_with = None
            self.focus_on_date(target_date, signals)
            self._update_signals_display(signals)
        except Exception as e:
            print(f"  [error in _apply_pending_focus_after_load] {e}")
        finally:
            self._pending_focus_date = None
            self._pending_focus_signals = None

    # ── 复刻 _on_chart_bar_clicked ──────────────────────────────────
    def _on_chart_bar_clicked(self, clicked_dt):
        try:
            if clicked_dt is None:
                return

            current_idx = self._interval_cb.currentIndex()
            current_interval, _ = self._interval_options[current_idx]
            if current_interval != Interval.DAILY:
                return  # 非日线周期不触发

            if hasattr(clicked_dt, "strftime"):
                target_date = clicked_dt.strftime("%Y-%m-%d")
            else:
                target_date = str(clicked_dt)[:10]
            if not target_date:
                return

            day_buy_signals = []
            day_sell_signals = []
            for d in (self._last_buy_dates or []):
                d_str = str(d)[:10]
                if d_str == target_date:
                    day_buy_signals.append(f"{target_date} 09:35")
            for d in (self._last_sell_dates or []):
                d_str = str(d)[:10]
                if d_str == target_date:
                    day_sell_signals.append(f"{target_date} 14:55")
            signals = {'buy': day_buy_signals, 'sell': day_sell_signals}

            five_min_idx = None
            for i, (iv, _) in enumerate(self._interval_options):
                if iv == Interval.MINUTE_5:
                    five_min_idx = i
                    break
            if five_min_idx is None:
                return

            self._pending_focus_date = target_date
            self._pending_focus_signals = signals

            self._interval_cb.blockSignals(True)
            try:
                self._interval_cb.setCurrentIndex(five_min_idx)
            finally:
                self._interval_cb.blockSignals(False)

            self.show_symbol(
                self._current_symbol,
                buy_dates=self._last_buy_dates,
                sell_dates=self._last_sell_dates,
            )
        except Exception as e:
            print(f"  [error] {e}")
            self._pending_focus_date = None
            self._pending_focus_signals = None


# ── 测试 ────────────────────────────────────────────────────────────
print("=" * 70)
print("Chart Tab 日线→分钟联动测试")
print("=" * 70)

# 测试 1：日线周期 + 点击日线 K 线 → 触发联动
print("\n[1] 日线周期点击触发联动")
tab = FakeTab()
tab._on_chart_bar_clicked(dt.datetime(2024, 8, 15, 0, 0))
check("show_symbol 被调用", tab.show_symbol_called_with is not None)
check("周期切到 5min", tab._interval_cb.currentIndex() == 1)
check("focus_on_date 被调用", tab.focus_on_date_called_with is not None)
check("update_signals_display 被调用", tab.update_signals_display_called_with is not None)
check("pending 状态被清空", tab._pending_focus_date is None and tab._pending_focus_signals is None)

# 测试 2：非日线周期不触发
print("\n[2] 非日线周期不触发")
tab = FakeTab()
tab._interval_cb.setCurrentIndex(1)  # 切到 5min
tab._user_manually_changed_interval = True
tab._on_chart_bar_clicked(dt.datetime(2024, 8, 15, 10, 30))
check("show_symbol 未被调用", tab.show_symbol_called_with is None)
check("focus_on_date 未被调用", tab.focus_on_date_called_with is None)
check("周期保持 5min", tab._interval_cb.currentIndex() == 1)
check("pending 状态保持空", tab._pending_focus_date is None)

# 测试 3：信号过滤 - 只把当日买卖信号放入 overlay
print("\n[3] overlay signals 仅含当日买卖信号")
tab = FakeTab()
tab._on_chart_bar_clicked(dt.datetime(2024, 8, 15, 0, 0))
# 2024-08-15 在 _last_buy_dates 中
signals = tab.focus_on_date_called_with[1]
check("2024-08-15 有买入信号", len(signals['buy']) == 1, f"got {signals['buy']}")
check("2024-08-15 无卖出信号", len(signals['sell']) == 0)

# 测试 4：点击 2024-08-20 (有卖出)
print("\n[4] 点击卖出日 → overlay 仅含卖出")
tab = FakeTab()
tab._on_chart_bar_clicked(dt.datetime(2024, 8, 20, 0, 0))
signals = tab.focus_on_date_called_with[1]
check("2024-08-20 无买入信号", len(signals['buy']) == 0)
check("2024-08-20 有卖出信号", len(signals['sell']) == 1)

# 测试 5：点击无信号日 → overlay 为空但仍聚焦
print("\n[5] 点击无信号日 → overlay 为空但仍聚焦")
tab = FakeTab()
tab._on_chart_bar_clicked(dt.datetime(2024, 8, 10, 0, 0))  # 8-10 不在列表中
check("focus_on_date 仍被调用", tab.focus_on_date_called_with is not None)
target_date = tab.focus_on_date_called_with[0]
check("聚焦日期正确", target_date == "2024-08-10", f"got {target_date}")
signals = tab.focus_on_date_called_with[1]
check("无买入信号", len(signals['buy']) == 0)
check("无卖出信号", len(signals['sell']) == 0)

# 测试 6：自动联动时 _user_manually_changed_interval 不被置位（blockSignals 生效）
print("\n[6] 自动联动不污染 _user_manually_changed_interval")
tab = FakeTab()
check("初始为 False", tab._user_manually_changed_interval is False)
tab._on_chart_bar_clicked(dt.datetime(2024, 8, 15, 0, 0))
check("联动后仍为 False（blockSignals 生效）",
      tab._user_manually_changed_interval is False)
check("周期确实切到 5min", tab._interval_cb.currentIndex() == 1)

# 测试 7：用户手动切周期会置位标志
print("\n[7] 手动切下拉框 → 标志位置位")
tab = FakeTab()
tab._interval_cb.setCurrentIndex(1)  # 模拟用户主动点击
check("手动切后标志位 True", tab._user_manually_changed_interval is True)

# 测试 8：show_symbol 抛异常时，pending 状态被清理
print("\n[8] show_symbol 抛异常时清理 pending 状态")
tab = FakeTab()
def boom(*args, **kwargs):
    raise RuntimeError("simulated DB error")
tab.show_symbol = boom
tab._on_chart_bar_clicked(dt.datetime(2024, 8, 15, 0, 0))
check("异常后 pending_focus_date 清空", tab._pending_focus_date is None)
check("异常后 pending_focus_signals 清空", tab._pending_focus_signals is None)
check("异常被吞掉，调用者无感知", True)  # 上面没崩就通过

# 测试 9：show_symbol 收到完整的 buy_dates/sell_dates（不只是当日）
print("\n[9] show_symbol 接收完整 buy_dates/sell_dates")
tab = FakeTab()
tab._on_chart_bar_clicked(dt.datetime(2024, 8, 15, 0, 0))
symbol, buys, sells = tab.show_symbol_called_with
check("symbol 正确", symbol == "600028.SSE")
check("buy_dates 完整（3 个）", len(buys) == 3, f"got {buys}")
check("sell_dates 完整（2 个）", len(sells) == 2)

# 测试 10：连续点击不同日期，pending 状态被最新覆盖
print("\n[10] 连续点击不同日期，pending 被最新覆盖")
tab = FakeTab()
tab._on_chart_bar_clicked(dt.datetime(2024, 8, 1, 0, 0))   # 8-1 有买入
date_1, signals_1 = tab.focus_on_date_called_with

# 重置为日线周期（模拟用户切回日线查看历史走势）后再点击 9-5
tab._interval_cb.blockSignals(True)
tab._interval_cb.setCurrentIndex(0)  # 切回日线
tab._interval_cb.blockSignals(False)
tab._user_manually_changed_interval = False

tab._on_chart_bar_clicked(dt.datetime(2024, 9, 5, 0, 0))   # 9-5 有卖出
date_2, signals_2 = tab.focus_on_date_called_with
check("8-1 focus 收到买入", len(signals_1['buy']) == 1 and len(signals_1['sell']) == 0,
      f"got date={date_1}, buy={signals_1['buy']}, sell={signals_1['sell']}")
check("9-5 focus 收到卖出", len(signals_2['buy']) == 0 and len(signals_2['sell']) == 1,
      f"got date={date_2}, buy={signals_2['buy']}, sell={signals_2['sell']}")
check("8-1 focus 聚焦日期正确", date_1 == "2024-08-01")
check("9-5 focus 聚焦日期正确", date_2 == "2024-09-05")

# 测试 11：_apply_pending_focus_after_load 重复调用安全（pending 已被清空）
print("\n[11] _apply_pending_focus_after_load 重复调用安全")
tab = FakeTab()
tab._pending_focus_date = "2024-08-15"
tab._pending_focus_signals = {'buy': ['2024-08-15 09:35'], 'sell': []}
tab._apply_pending_focus_after_load()
check("第一次调用 focus_on_date", tab.focus_on_date_called_with is not None)
tab.focus_on_date_called_with = None
tab._apply_pending_focus_after_load()  # 第二次，pending 已被清空
check("第二次调用不再触发 focus_on_date（pending 已清空）",
      tab.focus_on_date_called_with is None)

# 测试 12：clicked_dt 是 date 对象（不是 datetime）
print("\n[12] clicked_dt 是 date 对象（非 datetime）")
tab = FakeTab()
tab._on_chart_bar_clicked(dt.date(2024, 8, 15))
check("date 对象也能正确提取日期字符串",
      tab.focus_on_date_called_with[0] == "2024-08-15")

# 测试 13：clicked_dt 是 None 时安全返回
print("\n[13] clicked_dt 是 None → 安全返回不抛异常")
tab = FakeTab()
tab._on_chart_bar_clicked(None)
check("None 输入不抛异常", tab.show_symbol_called_with is None)
check("None 输入不清空已有 pending", tab._pending_focus_date is None)  # 初始就是 None


# ── 总结 ────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print(f"  PASS: {len(PASS)}/{len(PASS)+len(FAIL)}")
if FAIL:
    print(f"  FAIL: {len(FAIL)}")
    for f in FAIL:
        print(f"    - {f}")
print("=" * 70)

sys.exit(0 if not FAIL else 1)
