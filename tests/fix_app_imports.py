import pathlib

P = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\app.py")
src = P.read_text(encoding="utf-8")

# 移除错误插入的 import pathlib，重新放到 from __future__ 之后
src = src.replace("import pathlib\nfrom __future__ import annotations\n",
                  "from __future__ import annotations\nimport pathlib\n")

P.write_text(src, encoding="utf-8")

import ast
ast.parse(src)
print("app.py fixed OK")
print("first 10 lines:")
for i, l in enumerate(src.splitlines()[:10], 1):
    print(f"  {i:2d}: {l}")
