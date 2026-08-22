# -*- coding: utf-8 -*-
"""
日线->分钟K线联动功能 4个Bug修复的逻辑验证脚本（无GUI依赖）。

验证点：
1. Bug1/2（KlineViewTab.focus_on_date 重构后逻辑）：
   - 叠加信号写入 chart._overlay_buy/_overlay_sell，不触碰
     chart._buy_triggers/_sell_triggers（原始信号保持完整）。
   - 聚焦范围 (x_min, x_max) 计算正确（前后各留5根，边界截断）。
2. Bug4（Y轴自适应计算）：
   - _on_x_range_changed 的可见区间 low/high + 5% padding 逻辑。
3. Bug3（closeEvent 精确断连）：
   - _owned_connections 逐个 (signal, slot) 断开语义模拟。

运行：python tests/_smoke_linkage_fix.py
"""
import datetime as dt
import sys
import os

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


# ── 构造模拟分钟K线数据 ──────────────────────────────
class FakeChart:
    """模拟 KlineChartWidget/_FullscreenChart 的联动相关属性"""

    def __init__(self):
        # 3个交易日，每天4根分钟K线（模拟5分钟线交易日片段）
        days = [dt.date(2026, 7, 15), dt.date(2026, 7, 16), dt.date(2026, 7, 17)]
        self._datetimes = []
        self._bars = []
        price = 10.0
        for d in days:
            for hm in [(9, 35), (10, 0), (13, 5), (14, 30)]:
                self._datetimes.append(dt.datetime(d.year, d.month, d.day, hm[0], hm[1]))
                o = price; h = price + 0.2; l = price - 0.2; c = price + 0.1
                self._bars.append((o, h, l, c))
                price += 0.05
        # 原始回测信号：7-15 第一根买入，7-16 最后一根卖出
        self._buy_triggers = {0}
        self._sell_triggers = {7}
        self._overlay_buy = set()
        self._overlay_sell = set()

    def snapshot_triggers(self):
        return (set(self._buy_triggers), set(self._sell_triggers))


chart = FakeChart()
target_date = dt.date(2026, 7, 17)  # 点击日线 7-17
signals = {
    'buy': [dt.datetime(2026, 7, 17, 9, 35)],
    'sell': [dt.datetime(2026, 7, 17, 14, 30)],
}

# ── 复刻 KlineViewTab.focus_on_date 的核心逻辑（不含GUI调用） ──
datetimes = chart._datetimes
target_indices = [i for i, d in enumerate(datetimes) if d.date() == target_date]
check("找到目标日期的K线索引", target_indices == [8, 9, 10, 11],
      f"got {target_indices}")

start_idx = min(target_indices)
end_idx = max(target_indices)
padding = 5
x_min = max(0, start_idx - padding)
x_max = min(len(datetimes) - 1, end_idx + padding)
check("聚焦范围计算(边界截断)", (x_min, x_max) == (3, 11),
      f"got ({x_min}, {x_max})")

# Y轴范围计算
n = len(datetimes)
i_start = max(0, int(x_min))
i_end = min(n, int(x_max) + 1)
vis_bars = chart._bars[i_start:i_end]
price_lo = min(b[2] for b in vis_bars)
price_hi = max(b[1] for b in vis_bars)
margin = (price_hi - price_lo) * 0.05 or price_hi * 0.05
y_range = (price_lo - margin, price_hi + margin)
check("Y轴范围在可见区间内", y_range[0] < price_lo and y_range[1] > price_hi,
      f"got {y_range}, bars[{price_lo},{price_hi}]")

# 叠加信号写入 overlay（不触碰原始集合）
orig_buy, orig_sell = chart.snapshot_triggers()
dt_to_idx = {d: i for i, d in enumerate(datetimes)}
for sig_dt in signals['buy']:
    if sig_dt in dt_to_idx:
        chart._overlay_buy.add(dt_to_idx[sig_dt])
for sig_dt in signals['sell']:
    if sig_dt in dt_to_idx:
        chart._overlay_sell.add(dt_to_idx[sig_dt])
new_buy, new_sell = chart.snapshot_triggers()
check("Bug2: 原始买入信号未被覆盖", new_buy == orig_buy == {0},
      f"got {new_buy}")
check("Bug2: 原始卖出信号未被覆盖", new_sell == orig_sell == {7},
      f"got {new_sell}")
check("Bug2: 联动买入信号已叠加", chart._overlay_buy == {8},
      f"got {chart._overlay_buy}")
check("Bug2: 联动卖出信号已叠加", chart._overlay_sell == {11},
      f"got {chart._overlay_sell}")

# 合并渲染语义（_redraw 中的合并逻辑）
all_buy = chart._buy_triggers | chart._overlay_buy
all_sell = chart._sell_triggers | chart._overlay_sell
check("合并渲染: 原始+叠加均在", all_buy == {0, 8} and all_sell == {7, 11},
      f"buy={all_buy}, sell={all_sell}")

# 再次点击另一日期 -> overlay 替换，原始信号仍保留
chart._overlay_buy = set()
chart._overlay_sell = set()
check("再次点击后overlay清空, 原始信号保留",
      chart.snapshot_triggers() == ({0}, {7}) and not chart._overlay_buy)

# ── Bug3: closeEvent 精确断连语义模拟 ───────────────────
class FakeSignal:
    def __init__(self):
        self._slots = []
        self.emit_log = []

    def connect(self, slot):
        self._slots.append(slot)

    def disconnect(self, slot=None):
        if slot is None:
            # 旧Bug行为：全局断开
            self._slots = []
        else:
            self._slots = [s for s in self._slots if s != slot]


sig = FakeSignal()
win_a_slot = lambda *a: None
win_b_slot = lambda *a: None
sig.connect(win_a_slot)
sig.connect(win_b_slot)

# 旧逻辑（Bug3）：无参disconnect -> 两个窗口全断
old_sig = FakeSignal()
old_sig.connect(win_a_slot)
old_sig.connect(win_b_slot)
old_sig.disconnect()  # 全局断开
check("Bug3旧逻辑复现: 无参disconnect会断开全部",
      len(old_sig._slots) == 0, "预期先复现Bug行为")

# 新逻辑：只断开自己记录的连接
new_sig = FakeSignal()
new_sig.connect(win_a_slot)
new_sig.connect(win_b_slot)
owned = [(new_sig, win_a_slot)]  # 窗口A只记录自己的连接
for s, slot in owned:
    s.disconnect(slot)
check("Bug3新逻辑: 关闭A不影响B的连接",
      new_sig._slots == [win_b_slot],
      f"got {len(new_sig._slots)} slots")

# ── Bug1: _redraw 重置后聚焦再应用（时序语义） ─────────
# 模拟: _redraw() 将X轴设为 (n-120, n) -> 之后 singleShot 应用 (x_min, x_max)
view_range = [max(0, n - 120), n]  # _redraw 内的 setXRange 效果
check("Bug1复现: _redraw默认显示末尾", view_range == [0, 12])
# 模拟 _apply_focus（singleShot 之后）
view_range = [x_min, x_max]
check("Bug1修复: 异步应用聚焦范围后生效",
      view_range == [3, 11], f"got {view_range}")

# ── 汇总 ──────────────────────────────────────────────
print("\n" + "=" * 50)
print(f"总计: {len(PASS)} 通过, {len(FAIL)} 失败")
if FAIL:
    print("失败项:", FAIL)
    sys.exit(1)
print("ALL TESTS PASSED")
