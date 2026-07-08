import pathlib

P = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\examples\veighna_trader\run.py")
src = P.read_text(encoding="utf-8")

old = "    main_window = MainWindow(main_engine, event_engine)\n"
new = (
    "    from vnpy.trader.ui.sidebar import apply_sidebar_patch\n"
    "    apply_sidebar_patch()\n"
    "\n"
    "    main_window = MainWindow(main_engine, event_engine)\n"
)

assert old in src, "patch point not found"
src = src.replace(old, new, 1)

import ast; ast.parse(src)
P.write_text(src, encoding="utf-8")
print("patch injected OK")
