#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断：多周期回测为什么0笔交易
"""
import sys
sys.path.insert(0, 'c:/Users/11229/Documents/GitHub/vnpy')

# 模拟你的策略
from vnpy.trader.constant import Interval
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.core.condition_tree import ConditionNode
from vnpy.strategy_condition.constant import ConditionCategory, ConditionIndicator

# 创建你的策略
ma_cond = Condition(
    category=ConditionCategory.TREND,
    indicator=ConditionIndicator.MA_ALIGNMENT,
    params={"periods": [5, 10, 20, 60], "max_gap_pct": 0.0, "_data_interval": "d"}
)

回踩_cond = Condition(
    category=ConditionCategory.PULLBACK,
    indicator=ConditionIndicator.PULLBACK_TO_MA20,
    params={"vol_ratio": 0.8, "_data_interval": "d"}
)

vol_cond = Condition(
    category=ConditionCategory.VOLUME,
    indicator=ConditionIndicator.VOLUME_SHRINK,
    params={"vol_ratio": 0.8, "period": 5, "_data_interval": "5m"}
)

# 构造买入树：AND(ma, 回踩, vol)
buy_tree = ConditionNode.and_node([
    ConditionNode.leaf(ma_cond),
    ConditionNode.leaf(回踩_cond),
    ConditionNode.leaf(vol_cond)
])

# 创建一个 Strategy-like 对象（只需要 buy_tree）
class SimpleStrategy:
    def __init__(self, name, buy_tree):
        self.name = name
        self.buy_tree = buy_tree

strategy = SimpleStrategy(name="测试MTF", buy_tree=buy_tree)

# 分析数据需求
from vnpy.strategy_condition.core.mtf_context import analyze_data_requirements
req = analyze_data_requirements(strategy.buy_tree, Interval.DAILY)

print("="*60)
print("策略数据需求分析")
print("="*60)
print(f"所需周期: {[i.value for i in req.intervals]}")
print(f"锚点周期: {req.strategy_execution_interval.value}")
print()

# 检查每个条件
for cond in strategy.buy_tree.all_conditions():
    ind = cond.indicator.value
    has_attr = hasattr(cond, 'data_interval') and cond.data_interval
    param_val = cond.params.get("_data_interval")
    print(f"条件 {ind}:")
    print(f"  - data_interval属性: {cond.data_interval if has_attr else 'None'}")
    print(f"  - params[_data_interval]: {param_val}")
    print()

if len(req.intervals) > 1:
    print("✓ 正确：检测到多周期策略")
else:
    print("✗ 错误：未检测到多周期，回测将按单周期执行")