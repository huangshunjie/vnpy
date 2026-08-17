# -*- coding: utf-8 -*-
"""
Phase 4 多周期架构改造测试

测试 ScanEngine 的多周期支持：
1. 分析策略的数据需求
2. 构造 MultiTimeframeContext
3. 多周期条件评估
4. 向后兼容性
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime, timedelta
from vnpy.strategy_condition.core.mtf_context import (
    MultiTimeframeContext, analyze_data_requirements
)
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.core.condition_tree import ConditionNode
from vnpy.strategy_condition.core.strategy import Strategy, StrategyMeta, StrategyParams
from vnpy.strategy_condition.constant import ConditionCategory, ConditionIndicator, NodeOp
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
from vnpy.strategy_condition.engine.scan_engine import ScanEngine
from vnpy.trader.constant import Interval


class MockBar:
    def __init__(self, dt, open_price, high, low, close, volume):
        self.dt = dt
        self.datetime = dt
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


def create_mock_bars(n, start_price=10.0, interval=Interval.DAILY):
    bars = []
    base_date = datetime(2024, 1, 1)
    for i in range(n):
        if interval == Interval.DAILY:
            dt = base_date + timedelta(days=i)
        else:
            dt = base_date + timedelta(minutes=i * 5)
        close = start_price * (1 + (i % 10 - 5) * 0.02)
        open_price = close * 0.99
        high = close * 1.02
        low = close * 0.98
        volume = 1000000 + i * 10000
        bars.append(MockBar(dt, open_price, high, low, close, volume))
    return bars


print("=" * 60)
print("Phase 4 多周期架构改造测试")
print("=" * 60)

# ===== 测试 1: 数据需求分析 =====
print("\n[测试 1] 数据需求分析")

c1 = Condition(ConditionCategory.TREND, ConditionIndicator.MA_SLOPE,
               {"ma_period": 20}, data_interval=Interval.DAILY)
c2 = Condition(ConditionCategory.VOLUME, ConditionIndicator.VOLUME_RATIO,
               {"period": 20, "min_ratio": 1.5}, data_interval=Interval.MINUTE_5)

buy_tree = ConditionNode.and_node(
    ConditionNode.leaf(c1), ConditionNode.leaf(c2), label="多周期买入"
)

req = analyze_data_requirements(buy_tree, Interval.MINUTE_5)
print(f"  执行周期: {req.strategy_execution_interval.value}")
print(f"  需要周期: {[i.value for i in req.intervals]}")
assert Interval.DAILY in req.intervals
assert Interval.MINUTE_5 in req.intervals
print("  ✓ PASS")

# ===== 测试 2: MultiTimeframeContext =====
print("\n[测试 2] MultiTimeframeContext")

ctx = MultiTimeframeContext("600000.SH")
daily_bars = create_mock_bars(100, 10.0, Interval.DAILY)
minute_bars = create_mock_bars(300, 10.0, Interval.MINUTE_5)
ctx.set_bars(Interval.DAILY, daily_bars)
ctx.set_bars(Interval.MINUTE_5, minute_bars)

assert ctx.has_interval(Interval.DAILY)
assert ctx.has_interval(Interval.MINUTE_5)
assert len(ctx.get_bars(Interval.DAILY)) == 100
assert len(ctx.get_bars(Interval.MINUTE_5)) == 300
print("  ✓ PASS")

# ===== 测试 3: ConditionEngine 多周期评估 =====
print("\n[测试 3] ConditionEngine 多周期评估")

engine = ConditionEngine()
passed1, score1 = engine.eval_condition(c1, "600000.SH", daily_bars)
passed2, score2 = engine.eval_condition(c1, "600000.SH", [], _mtf_context=ctx)
assert passed1 == passed2, f"结果不一致: {passed1} vs {passed2}"
print(f"  单周期: passed={passed1}, score={score1:.4f}")
print(f"  多周期: passed={passed2}, score={score2:.4f}")
print("  ✓ PASS")

# ===== 测试 4: 向后兼容 =====
print("\n[测试 4] 向后兼容（无 data_interval）")

c_old = Condition(ConditionCategory.TREND, ConditionIndicator.MA_SLOPE, {"ma_period": 20})
old_tree = ConditionNode.leaf(c_old)
req_old = analyze_data_requirements(old_tree, Interval.DAILY)
assert len(req_old.intervals) == 1
assert Interval.DAILY in req_old.intervals
print(f"  旧版条件需要周期: {[i.value for i in req_old.intervals]}")
print("  ✓ PASS")

# ===== 测试 5: ScanEngine 单周期扫描 =====
print("\n[测试 5] ScanEngine 单周期扫描")

ce = ConditionEngine()
se = ScanEngine(condition_engine=ce)

simple_tree = ConditionNode.leaf(
    Condition(ConditionCategory.MOMENTUM, ConditionIndicator.MACD_GOLDEN, {})
)
sell_tree = ConditionNode.leaf(
    Condition(ConditionCategory.EXIT, ConditionIndicator.STOP_LOSS, {"pct": 8.0})
)
simple_strategy = Strategy(
    meta=StrategyMeta(name="简单策略"),
    buy_tree=simple_tree,
    sell_tree=sell_tree,
    params=StrategyParams(min_bars=20),
)

bars_dict = {"600000.SH": create_mock_bars(200)}
batch = se.scan(
    symbols=["600000.SH"],
    strategy=simple_strategy,
    _bars_dict=bars_dict,
)
print(f"  扫描结果: {batch.count} 个信号")
print("  ✓ PASS")

# ===== 测试 6: 多周期策略标记检测 =====
print("\n[测试 6] 多周期策略标记检测")

mtf_tree = ConditionNode.and_node(
    ConditionNode.leaf(Condition(
        ConditionCategory.TREND, ConditionIndicator.MA_SLOPE,
        {"ma_period": 20}, data_interval=Interval.DAILY)),
    ConditionNode.leaf(Condition(
        ConditionCategory.VOLUME, ConditionIndicator.VOLUME_RATIO,
        {"period": 5, "min_ratio": 1.5}, data_interval=Interval.MINUTE_5)),
    label="多周期买入"
)

req_mtf = analyze_data_requirements(mtf_tree, Interval.MINUTE_5)
is_multi = len(req_mtf.intervals) > 1
print(f"  是否多周期: {is_multi}")
assert is_multi, "应该检测为多周期策略"
print("  ✓ PASS")

# ===== 测试 7: Condition 序列化保持 data_interval =====
print("\n[测试 7] Condition 序列化")

c_with_interval = Condition(
    ConditionCategory.TREND, ConditionIndicator.MA_SLOPE,
    {"ma_period": 20}, data_interval=Interval.DAILY
)
d = c_with_interval.to_dict()
c_restored = Condition.from_dict(d)
assert c_restored.data_interval == Interval.DAILY
print(f"  序列化后 data_interval: {c_restored.data_interval}")
print("  ✓ PASS")

# ===== 总结 =====
print("\n" + "=" * 60)
print("ALL PHASE 4 TESTS PASSED")
print("=" * 60)