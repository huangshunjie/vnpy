"""append_sidebar3.py"""
import pathlib, ast

P = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\trader\ui\sidebar.py")

PART3 = '''

def _patched_init_menu(self) -> None:
    from vnpy.trader.ui.mainwindow import get_icon_path
    from vnpy.trader.ui.widget import ContractManager, AboutDialog

    bar = self.menuBar()
    bar.setNativeMenuBar(False)

    # ── 系统菜单 ──────────────────────────────────────────────────
    sys_menu = bar.addMenu("系统")
    for name in self.main_engine.get_all_gateway_names():
        self.add_action(
            sys_menu, f"连接{name}",
            get_icon_path(__file__, "connect.ico"),
            partial(self.connect_gateway, name))
    sys_menu.addSeparator()
    self.add_action(sys_menu, "退出",
                    get_icon_path(__file__, "exit.ico"), self.close)

    # ── 功能菜单（App 只在菜单里，不单独上工具栏）────────────────
    app_menu = bar.addMenu("功能")
    self._app_funcs: Dict[str, tuple] = {}

    for app in self.main_engine.get_all_apps():
        try:
            ui_mod = import_module(app.app_module + ".ui")
            wcls   = getattr(ui_mod, app.widget_name)
        except Exception:
            continue
        func = partial(self.open_widget, wcls, app.app_name)
        self.add_action(app_menu, app.display_name,
                        app.icon_name, func, toolbar=False)
        self._app_funcs[app.app_name] = (app.display_name, func)

    # ── 配置 / 微信 ───────────────────────────────────────────────
    for text, slot in [("配置", self.edit_global_setting),
                       ("微信", self.open_wechat_dialog)]:
        act = QtGui.QAction(text, self)
        act.triggered.connect(slot)
        bar.addAction(act)

    # ── 帮助菜单（保留工具栏图标） ────────────────────────────────
    help_menu = bar.addMenu("帮助")
    self.add_action(
        help_menu, "查询合约",
        get_icon_path(__file__, "contract.ico"),
        partial(self.open_widget, ContractManager, "contract"), True)
    self.add_action(
        help_menu, "恢复窗口",
        get_icon_path(__file__, "restore.ico"),
        self.restore_window_setting)
    self.add_action(
        help_menu, "测试邮件",
        get_icon_path(__file__, "email.ico"),
        self.send_test_email)
    self.add_action(
        help_menu, "社区论坛",
        get_icon_path(__file__, "forum.ico"),
        self.open_forum, True)
    self.add_action(
        help_menu, "关于",
        get_icon_path(__file__, "about.ico"),
        partial(self.open_widget, AboutDialog, "about"))

    # ── VeighNa Apps 工具栏按钮（论坛下方） ───────────────────────
    self._apps_window = None

    def _open():
        if self._apps_window is None:
            self._apps_window = VeighNaAppsWindow(self._app_funcs, self)
        self._apps_window.show()
        self._apps_window.raise_()
        self._apps_window.activateWindow()

    act = QtGui.QAction("VeighNa Apps", self)
    act.setIcon(QtGui.QIcon(_APPS_ICON))
    act.setToolTip("VeighNa Apps — 量化平台应用中心")
    act.triggered.connect(_open)
    self.toolbar.addAction(act)


def apply_sidebar_patch() -> None:
    """在 MainWindow 实例化前调用。"""
    from vnpy.trader.ui.mainwindow import MainWindow
    MainWindow.init_menu = _patched_init_menu
'''

with open(P, "a", encoding="utf-8") as f:
    f.write(PART3)

src = P.read_text(encoding="utf-8")
ast.parse(src)
print("Part3 OK, total lines:", len(src.splitlines()))
