#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
手动测试多周期策略数据需求分析
"""
import sys
sys.path.insert(0, 'c:/Users/11229/Documents/GitHub/vnpy')

from vnpy.trader.constant import Interval
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.core.condition_tree import ConditionNode, ConditionTree
from vnpy.strategy_condition.constant import ConditionCategory, ConditionIndicator, NodeOp
from vnpy.strategy_condition.core.strategy import Strategy

# 手动创建条件并设置 data_interval
ma_cond = Condition(
    category=ConditionCategory.TREND,
    indicator=ConditionIndicator.MA_ALIGNMENT,
    params={"periods": [5, 10, 20, 60], "max_gap_pct": 0.0},
    data_interval=Interval.DAILY  # 手动设置日线
)

vol_cond = Condition(
    category=ConditionCategory.VOLUME,
    indicator=ConditionIndicator.VOLUME_SHRINK,
    params={"vol_ratio": 0.8, "period": 5},
    data_interval=Interval.MINUTE_5  # 手动设置5分钟
)

# 构建条件树
buy_tree = ConditionTree(
    op=NodeOp.AND,
    children=[
        ConditionNode(op=NodeOp.LEAF, condition=ma_cond),
        ConditionNode(op=NodeOp.LEAF, condition=vol_cond)
    ]
)

strategy = Strategy(name="手动测试MTF", buy_tree=buy_tree, sell_tree=None)

# 分析数据需求
from vnpy.strategy_condition.core.mtf_auto_loader import analyze_strategy_data_requirements
req = analyze_strategy_data_requirements(strategy, Interval.DAILY, 100)

print("="*60)
print("多周期策略数据需求分析")
print("="*60)
print(f"所需周期: {[i.value for i in req.required_intervals]}")
print(f"锚点周期: {req.anchor_interval.value}")
print(f"执行周期: {req.execution_interval.value}")
print()
if req.execution_interval == Interval.MINUTE_5:
    print("✓ 正确：回测将按5分钟遍历")
else:
    print("✗ 错误：回测仍按日线遍历")