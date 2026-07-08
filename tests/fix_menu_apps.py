import pathlib, ast

P = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\trader\ui\sidebar.py")
src = P.read_text(encoding="utf-8")

# 1. 工具栏白名单加入 PortfolioStrategy
src = src.replace(
    '_TOOLBAR_APPS: set = {"CtaStrategy", "CtaBacktester", "DataManager"}',
    '_TOOLBAR_APPS: set = {"CtaStrategy", "CtaBacktester", "DataManager", "PortfolioStrategy"}'
)

# 2. 功能菜单只保留这三个，其余全部移除，最后加 VeighNa Apps 菜单项
# 定位功能菜单循环代码块，替换整个 App 循环部分
old_block = (
    "    # ── 功能菜单（App 只在菜单里，不单独上工具栏）────────────────\n"
    "    app_menu = bar.addMenu(\"功能\")\n"
    "    self._app_funcs: Dict[str, tuple] = {}\n"
    "\n"
    "    for app in self.main_engine.get_all_apps():\n"
    "        try:\n"
    "            ui_mod = import_module(app.app_module + \".ui\")\n"
    "            wcls   = getattr(ui_mod, app.widget_name)\n"
    "        except Exception:\n"
    "            continue\n"
    "        func = partial(self.open_widget, wcls, app.app_name)\n"
    "        on_toolbar = app.app_name in _TOOLBAR_APPS\n"
    "        self.add_action(app_menu, app.display_name,\n"
    "                        app.icon_name, func, toolbar=on_toolbar)\n"
    "        self._app_funcs[app.app_name] = (app.display_name, func)\n"
)

new_block = (
    "    # ── 功能菜单：只保留三个固定 App + VeighNa Apps 入口 ────────\n"
    "    _MENU_APPS = {\"CtaBacktester\", \"DataManager\", \"PortfolioStrategy\"}\n"
    "    app_menu = bar.addMenu(\"功能\")\n"
    "    self._app_funcs: Dict[str, tuple] = {}\n"
    "\n"
    "    for app in self.main_engine.get_all_apps():\n"
    "        try:\n"
    "            ui_mod = import_module(app.app_module + \".ui\")\n"
    "            wcls   = getattr(ui_mod, app.widget_name)\n"
    "        except Exception:\n"
    "            continue\n"
    "        func = partial(self.open_widget, wcls, app.app_name)\n"
    "        on_toolbar = app.app_name in _TOOLBAR_APPS\n"
    "        # 菜单只保留三个，其余只收入弹窗\n"
    "        if app.app_name in _MENU_APPS:\n"
    "            self.add_action(app_menu, app.display_name,\n"
    "                            app.icon_name, func, toolbar=on_toolbar)\n"
    "        elif on_toolbar:\n"
    "            # 工具栏白名单但不在菜单里（CtaStrategy）：只加工具栏\n"
    "            icon = QtGui.QIcon(app.icon_name)\n"
    "            act  = QtGui.QAction(app.display_name, self)\n"
    "            act.setIcon(icon)\n"
    "            act.triggered.connect(func)\n"
    "            self.toolbar.addAction(act)\n"
    "        self._app_funcs[app.app_name] = (app.display_name, func)\n"
    "\n"
    "    # VeighNa Apps 菜单项（功能菜单最末）\n"
    "    app_menu.addSeparator()\n"
    "    def _open_apps():\n"
    "        if self._apps_window is None:\n"
    "            self._apps_window = VeighNaAppsWindow(self._app_funcs, self)\n"
    "        self._apps_window.show()\n"
    "        self._apps_window.raise_()\n"
    "        self._apps_window.activateWindow()\n"
    "    va_menu_act = QtGui.QAction(\"VeighNa Apps \u2014 \u91cf\u5316\u5e73\u53f0\u5e94\u7528\u4e2d\u5fc3\", self)\n"
    "    va_menu_act.setIcon(QtGui.QIcon(_APPS_ICON))\n"
    "    va_menu_act.triggered.connect(_open_apps)\n"
    "    app_menu.addAction(va_menu_act)\n"
)

assert old_block in src, "old block not found"
src = src.replace(old_block, new_block, 1)

# 3. 原来的 _open_apps_window 闭包和工具栏按钮仍在文件末尾，
#    但那里的 _apps_window 初始化引用了局部 _open，不影响，
#    只需确保末尾工具栏追加逻辑里 _open_apps_window → _open_apps 同步
#    （两者独立工作，弹窗单例 self._apps_window 共享）
ast.parse(src)
P.write_text(src, encoding="utf-8")
print("OK, lines:", len(src.splitlines()))
