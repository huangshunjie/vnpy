#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断 execution_interval 为何还是 DAILY
"""
import sys
sys.path.insert(0, 'c:/Users/11229/Documents/GitHub/vnpy')

from vnpy.trader.constant import Interval
from vnpy.strategy_condition.core.strategy import ConditionStrategy
from vnpy.strategy_condition.core.condition_tree import ConditionTree, ConditionOperator
from vnpy.strategy_condition.core.mtf_auto_loader import analyze_strategy_data_requirements

# 模拟用户的策略：日线MA + 5分钟缩量
def create_test_strategy():
    """创建测试策略"""
    from vnpy.strategy_condition.indicators.trend import MA均线向上
    from vnpy.strategy_condition.indicators.volume_advanced import 缩量阴线
    
    # 日线条件
    ma_cond = MA均线向上(period=20, data_interval=Interval.DAILY)
    
    # 5分钟条件
    vol_cond = 缩量阴线(vol_ratio=0.8, data_interval=Interval.MINUTE_5)
    
    # 组合条件树
    buy_tree = ConditionTree(
        operator=ConditionOperator.AND,
        children=[ma_cond, vol_cond]
    )
    
    strategy = ConditionStrategy(
        name="诊断测试",
        buy_tree=buy_tree
    )
    
    return strategy

# 诊断
print("=" * 60)
print("诊断 execution_interval 计算")
print("=" * 60)

strategy = create_test_strategy()

print(f"\n1. 策略买入条件:")
print(f"   - 条件1: {strategy.buy_tree.children[0]}")
print(f"     data_interval = {getattr(strategy.buy_tree.children[0], 'data_interval', 'N/A')}")
print(f"   - 条件2: {strategy.buy_tree.children[1]}")
print(f"     data_interval = {getattr(strategy.buy_tree.children[1], 'data_interval', 'N/A')}")

# 分析数据需求
req = analyze_strategy_data_requirements(
    strategy,
    anchor_interval=Interval.DAILY,
    anchor_bar_count=100
)

print(f"\n2. 分析结果:")
print(f"   - required_intervals: {req.required_intervals}")
print(f"   - anchor_interval: {req.anchor_interval}")
print(f"   - execution_interval: {req.execution_interval}")

print(f"\n3. 判断:")
if req.execution_interval == Interval.MINUTE_5:
    print("   ✅ execution_interval 正确识别为 5分钟")
elif req.execution_interval == Interval.DAILY:
    print("   ❌ execution_interval 错误：仍然是日线")
    print(f"\n   原因分析:")
    print(f"   - 条件树可能没有正确设置 data_interval")
    print(f"   - 或者 analyze_data_requirements 没有识别到分钟周期")
else:
    print(f"   ⚠️  execution_interval 是 {req.execution_interval}")

print("\n" + "=" * 60)