# -*- coding: utf-8 -*-
"""Fix test_mtf_phase6_monitor.py to use correct ConditionNode API"""

import re

test_file = "tests/test_mtf_phase6_monitor.py"

with open(test_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Add make_tree helper function after imports
helper_func = '''

def make_tree(*conditions):
    """用多个条件构建一个 AND 树"""
    from vnpy.strategy_condition.core.condition_tree import ConditionNode, NodeOp
    leaves = [ConditionNode(op=NodeOp.LEAF, condition=c) for c in conditions]
    return ConditionNode(op=NodeOp.AND, children=leaves)
'''

# Insert after the MockBar class definition
insert_pos = content.find('def create_daily_bars(')
if insert_pos > 0:
    content = content[:insert_pos] + helper_func + '\n\n' + content[insert_pos:]
    print("✓ Added make_tree helper function")

# Replace all ConditionNode(conditions=[...]) with make_tree(...)
content = re.sub(
    r'ConditionNode\(conditions=\[([^\]]+)\]\)',
    lambda m: f'make_tree({m.group(1)})',
    content
)
print("✓ Replaced ConditionNode(conditions=[...]) with make_tree(...)")

# Remove unused ConditionNode imports from test functions
content = re.sub(
    r'from vnpy\.strategy_condition\.core\.condition_tree import ConditionNode\n\s+',
    '',
    content
)
print("✓ Removed unused ConditionNode imports")

with open(test_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✅ Fixed {test_file}")