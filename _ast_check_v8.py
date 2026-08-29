# -*- coding: utf-8 -*-
import ast
from pathlib import Path
tree = ast.parse(Path(r"vnpy\strategy_condition\ui\kline_view.py").read_text(encoding="utf-8"))
out = []
for c in tree.body:
    if isinstance(c, ast.ClassDef) and c.name in ('_KlineFullscreenWindow','_FullscreenChart'):
        out.append(f"CLASS: {c.name} L{c.lineno}")
        for n in c.body:
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Assign)):
                out.append(f"  L{n.lineno}-{n.end_lineno}: {type(n).__name__} {getattr(n,'name','-')}")
Path("_ast_check_v8.txt").write_text("\n".join(out), encoding="utf-8")
print("written")
print("\n".join(out))