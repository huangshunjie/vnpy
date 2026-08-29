"""V26 print 静态分析（不依赖Qt，只读AST）。"""
import ast

path = 'vnpy/strategy_condition/ui/kline_view.py'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()
lines = src.splitlines()
tree = ast.parse(src)

# 找到所有 print 节点 + 它们的祖先函数
def find_ancestor_function(node, tree):
    """在 AST 中找到包含 node 的最近函数定义（用 lineno 范围匹配）。"""
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if hasattr(n, 'lineno') and hasattr(n, 'end_lineno'):
                if n.lineno <= node.lineno <= (n.end_lineno or 10**9):
                    return n
    return None

markers = ['[KlineView]', '[联动V26]']
results = []
for node in ast.walk(tree):
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        call = node.value
        if isinstance(call.func, ast.Name) and call.func.id == 'print':
            if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
                s = call.args[0].value
                for m in markers:
                    if m in s:
                        func = find_ancestor_function(node, tree)
                        func_name = func.name if func else '<top-level>'
                        line_no = node.lineno
                        # 判断：print 是不是函数/方法体的第一个有效语句（即 docstring）
                        is_docstring = False
                        if func and func.body:
                            first_stmt = func.body[0]
                            if (isinstance(first_stmt, ast.Expr)
                                and isinstance(first_stmt.value, ast.Constant)
                                and isinstance(first_stmt.value.value, str)):
                                if first_stmt.lineno == line_no:
                                    is_docstring = True
                        results.append((line_no, func_name, is_docstring, s[:100]))
                        break

print('='*80)
print(f'V26 print 静态分析: {path}')
print('='*80)
for line_no, func_name, is_doc, s in sorted(results, key=lambda x: x[0]):
    flag = '⚠️ 在 docstring 内' if is_doc else '✅ 函数体内'
    print(f'  L{line_no:4d} | {func_name:35s} | {flag} | {s}...')
print('='*80)
print(f'共 {len(results)} 个 V26 print 节点')
print(f'其中 {sum(1 for r in results if r[2])} 个在 docstring 内（应为0）')
print(f'其中 {sum(1 for r in results if not r[2])} 个在函数体内（应=5）')