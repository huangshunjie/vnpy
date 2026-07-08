"""fix_portfolio_engine.py"""
import pathlib, ast

# ── 1. run.py：恢复注释 PortfolioStrategyApp ──────────────────────
run = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\examples\veighna_trader\run.py")
src = run.read_text(encoding="utf-8")
src = src.replace(
    "from vnpy_portfoliostrategy import PortfolioStrategyApp",
    "# from vnpy_portfoliostrategy import PortfolioStrategyApp"
)
src = src.replace(
    "    main_engine.add_app(PortfolioStrategyApp)",
    "    # main_engine.add_app(PortfolioStrategyApp)"
)
ast.parse(src)
run.write_text(src, encoding="utf-8")
print("run.py: PortfolioStrategyApp re-commented")

# ── 2. sidebar.py：替换 PortfolioStrategy → PortfolioEngine ───────
sb = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\trader\ui\sidebar.py")
src = sb.read_text(encoding="utf-8")

# 工具栏白名单
src = src.replace(
    '"CtaStrategy", "CtaBacktester", "DataManager", "PortfolioStrategy"',
    '"CtaStrategy", "CtaBacktester", "DataManager", "PortfolioEngine"'
)

# 功能菜单白名单
src = src.replace(
    '_MENU_APPS = {"CtaBacktester", "DataManager", "PortfolioStrategy"}',
    '_MENU_APPS = {"CtaBacktester", "DataManager", "PortfolioEngine"}'
)

# APP_GROUPS 里也要换（组合风控分组里原来是 PortfolioEngine，保持不变，只检查）
assert '"PortfolioEngine"' in src, "PortfolioEngine not in APP_GROUPS"

ast.parse(src)
sb.write_text(src, encoding="utf-8")
print("sidebar.py: PortfolioStrategy -> PortfolioEngine")

# ── 3. PortfolioEngineApp.icon_name 动态注入 ─────────────────────
# 直接 patch PortfolioEngineApp.icon_name 在 run.py 里也行，
# 但更干净的方式是在 sidebar patch 里处理 icon 缺失的情况。
# 这里直接给 PortfolioEngineApp 设置 icon_name：
import sys
sys.path.insert(0, r"c:\Users\11229\Documents\GitHub\vnpy")
from vnpy.portfolio_engine import PortfolioEngineApp
ico = str(pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\trader\ui\ico\portfolio.ico"))
PortfolioEngineApp.icon_name = ico
print(f"PortfolioEngineApp.icon_name = {ico}")

# ── 4. 在 sidebar patch 里追加 icon 注入逻辑 ─────────────────────
sb_src = sb.read_text(encoding="utf-8")
INJECT = '''

def _inject_portfolio_icon() -> None:
    """给 PortfolioEngineApp 补充图标路径（该 App 原生没有 icon_name）。"""
    import pathlib as _pl
    try:
        from vnpy.portfolio_engine import PortfolioEngineApp
        _ico = str(_pl.Path(__file__).parent / "ico" / "portfolio.ico")
        if not PortfolioEngineApp.icon_name:
            PortfolioEngineApp.icon_name = _ico
    except Exception:
        pass
'''

# 追加到 apply_sidebar_patch 调用之前
if "_inject_portfolio_icon" not in sb_src:
    old = "def apply_sidebar_patch() -> None:"
    sb_src = sb_src.replace(old, INJECT + "\n" + old)
    old_body = '    from vnpy.trader.ui.mainwindow import MainWindow\n    MainWindow.init_menu = _patched_init_menu'
    new_body = '    _inject_portfolio_icon()\n    from vnpy.trader.ui.mainwindow import MainWindow\n    MainWindow.init_menu = _patched_init_menu'
    sb_src = sb_src.replace(old_body, new_body)
    ast.parse(sb_src)
    sb.write_text(sb_src, encoding="utf-8")
    print("sidebar.py: icon injection added")
else:
    print("sidebar.py: icon injection already present")

print("\n=== All done ===")
