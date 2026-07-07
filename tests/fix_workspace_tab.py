"""fix_workspace_tab.py — 修复截断的 f-string"""
import pathlib

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\workspace_tab.py"
)
src = P.read_text(encoding="utf-8")
lines = src.splitlines(keepends=True)

# 找到截断位置并合并
fixed_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # 检测以 f" 结尾（不含右引号）的行，需要与下一行合并
    stripped = line.rstrip("\r\n")
    if stripped.endswith('f"') and i + 1 < len(lines):
        next_line = lines[i + 1].rstrip("\r\n")
        merged = stripped + next_line.lstrip() + "\n"
        fixed_lines.append(merged)
        i += 2
        print(f"  merged line {i-1} + {i}: {repr(merged[:80])}")
    else:
        fixed_lines.append(line)
        i += 1

result = "".join(fixed_lines)

# 验证语法
import ast
try:
    ast.parse(result)
    P.write_text(result, encoding="utf-8")
    print(f"workspace_tab.py fixed OK, {len(fixed_lines)} lines")
except SyntaxError as e:
    print(f"Still broken at line {e.lineno}: {e.msg}")
    # 显示周围行
    rlines = result.splitlines()
    for j in range(max(0, e.lineno - 3), min(len(rlines), e.lineno + 2)):
        print(f"  {j+1:4d}: {repr(rlines[j])}")
