# -*- coding: utf-8 -*-
"""Fix test_mtf_phase6_monitor.py to use correct Strategy API"""

import re

test_file = "tests/test_mtf_phase6_monitor.py"

with open(test_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Add make_strategy helper function after make_tree
helper_func = '''

def make_strategy(name, buy_tree, sell_tree):
    """创建策略（使用默认元数据和参数）"""
    from vnpy.strategy_condition.core.strategy import Strategy, StrategyMeta
    meta = StrategyMeta(name=name)
    return Strategy(meta=meta, buy_tree=buy_tree, sell_tree=sell_tree)
'''

# Insert after make_tree function
insert_pos = content.find('\n\ndef create_daily_bars(')
if insert_pos > 0:
    content = content[:insert_pos] + helper_func + content[insert_pos:]
    print("✓ Added make_strategy helper function")

# Replace all Strategy(name=..., buy_tree=..., sell_tree=...) with make_strategy(...)
content = re.sub(
    r'Strategy\(\s*name="([^"]+)",\s*buy_tree=([^,]+),\s*sell_tree=([^,\)]+)[,\)]',
    lambda m: f'make_strategy("{m.group(1)}", {m.group(2)}, {m.group(3)})',
    content
)
print("✓ Replaced Strategy(...) with make_strategy(...)")

with open(test_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✅ Fixed {test_file}")