"""check_tab_base.py — 查看各 Tab 基类和 _engine 完整赋值"""
import pathlib, re, ast

root = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui")

for p in sorted(root.glob("*_tab.py")):
    src = p.read_text(encoding="utf-8", errors="ignore")
    lines = src.splitlines()

    # 找 class 定义
    class_lines = [l for l in lines if l.startswith("class ")]
    # 找所有含 _engine 的行
    eng_lines = [(i+1, l.strip()) for i, l in enumerate(lines)
                 if "_engine" in l and ("=" in l or "stats" in l or "engine." in l)]

    print(f"\n=== {p.name} ===")
    for cl in class_lines[:3]: print(f"  {cl}")
    print(f"  _engine usages (first 8):")
    for ln, l in eng_lines[:8]: print(f"    {ln:4d}: {l}")
