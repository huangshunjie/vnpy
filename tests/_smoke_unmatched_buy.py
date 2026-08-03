"""
验证 _find_unmatched_buys + _simulate_sell_dates 联合工作：
场景：sell 在 buy 之前（前一笔交易的卖出），当前 buy 无配对 sell
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from datetime import datetime, timedelta
from vnpy.strategy_condition.monitor.condition_monitor_engine import ConditionMonitorEngine
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
from vnpy.strategy_condition.core.strategy import Strategy, StrategyParams, StrategyMeta
from vnpy.strategy_condition.core.condition_tree import ConditionNode
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.constant import NodeOp, ConditionIndicator, ConditionCategory


class FakeBar:
    def __init__(self, dt, c):
        self.dt = dt
        self.open = c
        self.high = c + 0.1
        self.low = c - 0.1
        self.close = c
        self.volume = 1000


# 构造日线 K线序列（A股 T+1 需要跨日）
# bar 0-9: day 1-10, close=35 (前一笔持仓区间)
# bar 10: day 11, 前一笔卖出点
# bar 11-15: day 12-16, close=35 (空仓区间)
# bar 16: day 17 (2024-06-17), 当前买入点, close=35
# bar 17-30: day 18-31, 涨到36 (>2%=35.7) -- 次日起可卖
# bar 31-50: day 32-51, 从36跌到34.5 (回撤>2% from peak=36)
base = datetime(2024, 6, 1)
bars = []
for i in range(60):
    t = base + timedelta(days=i)
    if i <= 10:
        c = 35.0
    elif i <= 15:
        c = 35.0
    elif i == 16:
        c = 35.0  # buy point
    elif i <= 30:
        # 涨到 36 (peak)
        c = 35.0 + (i - 16) * (1.0 / 14)
    elif i <= 50:
        # 从36跌到34.5
        c = 36.0 - (i - 30) * (1.5 / 20)
    else:
        c = 34.5
    bars.append(FakeBar(t, c))

# 构造策略：卖出条件只有 TRAILING_STOP (take_profit=2%, trail_drawdown=2%)
sell_tree = ConditionNode(op=NodeOp.OR)
trailing_cond = Condition(
    indicator=ConditionIndicator.TRAILING_STOP,
    category=ConditionCategory.EXIT,
    params={"take_profit": 2.0, "trail_drawdown": 2.0}
)
sell_tree.add_child(ConditionNode.leaf(trailing_cond))

buy_tree = ConditionNode(op=NodeOp.AND)  # 空买入树

params = StrategyParams(
    stop_loss_pct=8.0,
    take_profit_pct=2.0,
    trail_drawdown=2.0,
    max_hold_days=10000,
)
strategy = Strategy(
    meta=StrategyMeta(name="test"),
    buy_tree=buy_tree,
    sell_tree=sell_tree,
    params=params,
)

ce = ConditionEngine()
me = ConditionMonitorEngine(ce)

# 模拟：前一笔 sell 在 day 11, 当前 buy 在 day 17
sell_dates = ['2024-06-11']
buy_dates = ['2024-06-17']

print("=== Test: sell before buy (unmatched buy, daily bars) ===")
print(f"Buy: 2024-06-17 (bar 16, close=35.0)")
print(f"Sell (previous trade): 2024-06-11 (bar 10)")
print(f"Strategy: trailing_stop take_profit=2%, trail_drawdown=2%")
print(f"Peak should be ~36.0 at bar 30")
print(f"Trigger: when price drops 2% from peak (36*0.98=35.28)")
print()

# 先测试 _find_unmatched_buys
unmatched = me._find_unmatched_buys(bars, buy_dates, sell_dates)
print(f"Unmatched buys: {unmatched}")
assert len(unmatched) == 1, f"Expected 1 unmatched buy, got {len(unmatched)}"
print("  -> Correctly identified 1 unmatched buy")

# 测试 generate_snapshots（完整流程）
snapshots = me.generate_snapshots(
    'TEST.SSE', bars, strategy,
    warmup=5, buy_dates=buy_dates, sell_dates=sell_dates)

print(f"\nSnapshots: {len(snapshots)}")
print(f"Simulated sell dates: {me.last_simulated_sell_dates}")

if me.last_simulated_sell_dates:
    print("\nSUCCESS: Simulated sell produced!")
    # 验证卖出时间合理性：应该在 peak(bar30) 之后
    sell_str = me.last_simulated_sell_dates[0]
    print(f"  Sell at: {sell_str}")
    # 价格验证
    for i, bar in enumerate(bars):
        dt_str = bar.dt.strftime("%Y-%m-%d %H:%M")
        if dt_str == sell_str:
            print(f"  Bar {i}: close={bar.close:.4f}")
            print(f"  Peak was ~36.0, trigger at 36*0.98=35.28")
            print(f"  Actual close: {bar.close:.4f} <= 35.28? {bar.close <= 35.28}")
            break
else:
    print("\nFAILED: No simulated sell produced!")
    # Debug: 手动检查价格序列
    print("Price sequence around peak:")
    for i in range(25, 45):
        print(f"  bar {i} ({bars[i].dt.strftime('%H:%M')}): close={bars[i].close:.4f}")