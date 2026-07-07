"""check_tab_engine_source.py"""
import pathlib, re

root = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui")
for p in sorted(root.glob("*_tab.py")):
    src = p.read_text(encoding="utf-8", errors="ignore")
    lines = src.splitlines()
    init_lines = []
    in_init = False
    for l in lines:
        if "def __init__" in l:
            in_init = True
        if in_init:
            init_lines.append(l)
            if len(init_lines) > 12:
                break
    engine_assign = [l.strip() for l in init_lines if "_engine" in l and "=" in l]
    print(f"{p.name}: {engine_assign[:3]}")
