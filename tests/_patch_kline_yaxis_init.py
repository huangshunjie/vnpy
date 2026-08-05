"""Fix _auto_yaxis: either add init or use getattr."""
import os

filepath = os.path.join(os.path.dirname(__file__), '..', 
                        'vnpy', 'strategy_condition', 'ui', 'kline_view.py')
filepath = os.path.abspath(filepath)

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 492 (0-indexed: 491) should be "        if not self._auto_yaxis:"
# Replace with getattr version
target_idx = 491  # 0-indexed
if '_auto_yaxis' in lines[target_idx] and 'getattr' not in lines[target_idx]:
    lines[target_idx] = '        if not getattr(self, "_auto_yaxis", True):\n'
    print(f"Fixed line {target_idx+1}: {lines[target_idx].rstrip()}")
else:
    print(f"Line {target_idx+1} already OK or different: {lines[target_idx].rstrip()}")

# Also do same for set_auto_yaxis method (line 481): use getattr in the method too
# Actually set_auto_yaxis always sets it, so it's fine there.

# Save
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)

# Syntax check
import ast
content = ''.join(lines)
try:
    ast.parse(content)
    print("Syntax: OK")
except SyntaxError as e:
    print(f"Syntax ERROR: {e}")