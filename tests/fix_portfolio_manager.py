import pathlib, ast

# ── 1. run.py：注释回 PortfolioStrategyApp ────────────────────────
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

# 验证 PortfolioManagerApp 已正确启用
for i, l in enumerate(src.splitlines(), 1):
    if "PortfolioManager" in l or "PortfolioStrategy" in l:
        print(f"  {i:3d}: {l}")

# ── 2. sidebar.py：替换白名单 ─────────────────────────────────────
sb = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\trader\ui\sidebar.py")
src = sb.read_text(encoding="utf-8")

src = src.replace(
    '{"CtaStrategy", "CtaBacktester", "DataManager", "PortfolioStrategy"}',
    '{"CtaStrategy", "CtaBacktester", "DataManager", "PortfolioManager"}'
)
src = src.replace(
    '{"CtaBacktester", "DataManager", "PortfolioStrategy"}',
    '{"CtaBacktester", "DataManager", "PortfolioManager"}'
)

assert '"PortfolioManager"' in src
ast.parse(src)
sb.write_text(src, encoding="utf-8")
print("\nsidebar.py: whitelist updated to PortfolioManager")

for i, l in enumerate(src.splitlines(), 1):
    if "TOOLBAR_APPS" in l or "MENU_APPS" in l:
        print(f"  {i:3d}: {l}")

print("\n=== Done ===")
