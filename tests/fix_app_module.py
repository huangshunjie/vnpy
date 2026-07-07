import pathlib, os

P = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\app.py")
src = P.read_text(encoding="utf-8")

src = src.replace(
    '    app_module:  str   = __module__\n'
    '    app_path:    str   = __file__\n',
    '    app_module:  str   = "vnpy.platform_engineering"\n'
    '    app_path:    str   = str(pathlib.Path(__file__).parent)\n'
)

# make sure pathlib is imported
if "import pathlib" not in src:
    src = src.replace("from __future__", "import pathlib\nfrom __future__", 1)

P.write_text(src, encoding="utf-8")
import ast; ast.parse(src)
print("fixed OK")
print([l for l in src.splitlines() if "app_module" in l or "app_path" in l])
