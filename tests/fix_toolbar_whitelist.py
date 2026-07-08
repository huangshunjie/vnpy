import pathlib, ast

P = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\trader\ui\sidebar.py")
src = P.read_text(encoding="utf-8")

old = (
    "        func = partial(self.open_widget, wcls, app.app_name)\n"
    "        self.add_action(app_menu, app.display_name,\n"
    "                        app.icon_name, func, toolbar=False)\n"
    "        self._app_funcs[app.app_name] = (app.display_name, func)\n"
)
new = (
    "        func = partial(self.open_widget, wcls, app.app_name)\n"
    "        on_toolbar = app.app_name in _TOOLBAR_APPS\n"
    "        self.add_action(app_menu, app.display_name,\n"
    "                        app.icon_name, func, toolbar=on_toolbar)\n"
    "        self._app_funcs[app.app_name] = (app.display_name, func)\n"
)

assert old in src, "pattern not found"
src = src.replace(old, new, 1)
ast.parse(src)
P.write_text(src, encoding="utf-8")
print("fixed OK")
