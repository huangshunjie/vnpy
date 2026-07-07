"""fix_workspace_tab2.py — 全面修复所有截断的字符串字面量"""
import pathlib, ast, re

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\workspace_tab.py"
)
src = P.read_text(encoding="utf-8")
lines = src.splitlines(keepends=True)

fixed = []
i = 0
merges = 0
while i < len(lines):
    cur = lines[i]
    stripped = cur.rstrip("\r\n")

    # 条件：当前行以未闭合的 f"  或  普通 " 结尾（不含续行符 \）
    # 且不是注释行、不是文档字符串开头
    if (
        not stripped.lstrip().startswith("#")
        and not stripped.strip().startswith('"""')
        and not stripped.strip().startswith("'''")
        and stripped.endswith('"')
        and i + 1 < len(lines)
    ):
        # 用 tokenize 检测是否语法合法；不合法才合并
        test_src = "".join(fixed) + stripped + "\n"
        try:
            ast.parse(test_src + "".join(lines[i+1:]))
            # 合法，不需要合并
            fixed.append(cur)
            i += 1
        except SyntaxError:
            # 合并下一行
            next_line = lines[i + 1].rstrip("\r\n").lstrip()
            merged = stripped + next_line + "\n"
            fixed.append(merged)
            i += 2
            merges += 1
            print(f"  merge @ orig line {i-1}: {repr(merged[:100])}")
    else:
        fixed.append(cur)
        i += 1

result = "".join(fixed)
try:
    ast.parse(result)
    P.write_text(result, encoding="utf-8")
    print(f"\nAll fixed. merges={merges}, lines={len(fixed)}, size={len(result)}")
except SyntaxError as e:
    print(f"\nStill broken at line {e.lineno}: {e.msg}")
    rlines = result.splitlines()
    for j in range(max(0, e.lineno - 3), min(len(rlines), e.lineno + 3)):
        print(f"  {j+1:4d}: {repr(rlines[j])}")
