# -*- coding: utf-8 -*-
import ast, sys

files = [
    "vnpy/strategy_condition/indicators/trend.py",
    "vnpy/strategy_condition/core/condition.py",
    "vnpy/strategy_condition/engine/condition_engine.py",
    "vnpy/strategy_condition/ui/condition_editor.py",
]
for f in files:
    try:
        ast.parse(open(f, encoding="utf-8").read())
        print("SYNTAX OK :", f)
    except SyntaxError as e:
        print("SYNTAX ERR:", f, e)
        sys.exit(1)

from vnpy.strategy_condition.indicators.trend import check_ma_alignment

# 构造收盘价序列，使 MA10 > MA20 > MA30 严格递减
# 用一个稳定上升趋势即可
closes = [100 + i * 0.5 for i in range(60)]  # 稳步上升
r1 = check_ma_alignment(closes, [10, 20, 30])
print("排列(不限间距):", r1)

# 靠近约束：MA10-MA20-MA30 间距都很小 -> 通过
r2 = check_ma_alignment(closes, [10, 20, 30], max_gap_pct=5.0)
print("排列+间距<=5%:", r2)

# 靠近约束太严 -> 不通过
r3 = check_ma_alignment(closes, [10, 20, 30], max_gap_pct=0.1)
print("排列+间距<=0.1%:", r3)

# 非多头排列(下跌趋势) -> 不通过
closes_down = [100 - i * 0.5 for i in range(60)]
r4 = check_ma_alignment(closes_down, [10, 20, 30], max_gap_pct=5.0)
print("下跌趋势:", r4)
