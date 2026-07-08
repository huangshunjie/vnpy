import pathlib, ast

p = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\trader\ui\sidebar.py")
src = p.read_text(encoding="utf-8")

src = src.replace(
    '{"CtaStrategy", "CtaBacktester", "DataManager", "PortfolioEngine"}',
    '{"CtaStrategy", "CtaBacktester", "DataManager", "PortfolioStrategy"}'
)
src = src.replace(
    '{"CtaBacktester", "DataManager", "PortfolioEngine"}',
    '{"CtaBacktester", "DataManager", "PortfolioStrategy"}'
)

ast.parse(src)
p.write_text(src, encoding="utf-8")
print("OK")

# 验证结果
for i, l in enumerate(src.splitlines(), 1):
    if "TOOLBAR_APPS" in l or "MENU_APPS" in l:
        print(i, l)
