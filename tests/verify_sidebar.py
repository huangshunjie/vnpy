"""verify_sidebar.py — 适配新版 sidebar"""
import sys, pathlib
sys.path.insert(0, r"c:\Users\11229\Documents\GitHub\vnpy")

# ── 语法检查 ──────────────────────────────────────────────────────
import ast
src = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\trader\ui\sidebar.py"
).read_text(encoding="utf-8")
ast.parse(src)
print("syntax: OK  (lines:", len(src.splitlines()), ")")

# ── 导入检查 ──────────────────────────────────────────────────────
from vnpy.trader.ui.sidebar import (
    apply_sidebar_patch, APP_GROUPS,
    VeighNaAppsWindow, GroupBox, AppCard, FlowLayout,
    _patched_init_menu, _APPS_ICON, _GROUPED,
)
print("import: OK")

# 分组完整性
total = sum(len(ns) for _,_,_,ns in APP_GROUPS)
print(f"groups: {len(APP_GROUPS)},  total app slots: {total}")
for label, emoji, color, names in APP_GROUPS:
    print(f"  [{label}] {len(names)} apps")

# patch 替换正确
from vnpy.trader.ui.mainwindow import MainWindow
orig = MainWindow.init_menu
apply_sidebar_patch()
assert MainWindow.init_menu is _patched_init_menu, "init_menu not patched"
print("patch apply: OK")

# 可逆
MainWindow.init_menu = orig
print("patch reversible: OK")

# run.py 注入点存在
run_src = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\examples\veighna_trader\run.py"
).read_text(encoding="utf-8")
assert "apply_sidebar_patch" in run_src
print("run.py injection: OK")

# 图标文件存在
import pathlib as _p
assert _p.Path(_APPS_ICON).exists(), f"icon missing: {_APPS_ICON}"
print(f"icon: OK  ({_APPS_ICON})")

print()
print("=== All checks PASSED ===")
