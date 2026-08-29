"""分析 kline_view.py 中 _KlineFullscreenWindow 类的真实结构"""
import ast

src = open('vnpy/strategy_condition/ui/kline_view.py', encoding='utf-8').read()
tree = ast.parse(src)

for node in tree.body:
    if isinstance(node, ast.ClassDef) and 'Fullscreen' in node.name:
        print(f'Class: {node.name} @ line {node.lineno}-{node.end_lineno}')
        for m in node.body:
            if isinstance(m, ast.FunctionDef):
                print(f'  - {m.name} @ {m.lineno}-{m.end_lineno}')
            else:
                print(f'  [other] {type(m).__name__} @ {getattr(m, "lineno", "?")}')

# Also: check module-level functions
print()
print('Module-level top-level defs (sample around 1400-1500):')
for node in tree.body:
    if isinstance(node, ast.ClassDef) and 'Fullscreen' in node.name:
        # Found the class
        for n in tree.body:
            if isinstance(n, ast.FunctionDef) and 1400 < n.lineno < 1500:
                print(f'  TOP-LEVEL: {n.name} @ {n.lineno}')
        break