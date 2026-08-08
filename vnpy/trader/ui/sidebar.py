"""
vnpy/trader/ui/sidebar.py
VeighNa Apps 入口 — patch 方案

点击工具栏"VeighNa Apps"图标弹出应用中心窗口。
"""
from __future__ import annotations
from functools import partial
from importlib import import_module
from typing import Callable, Dict, List, Tuple
import pathlib
import logging

from .qt import QtCore, QtGui, QtWidgets

_ICO_DIR   = pathlib.Path(__file__).parent / "ico"
_logger = logging.getLogger("vnpy.sidebar")

# 这些 App 保留在工具栏直接显示（原 VeighNa 自带）
_TOOLBAR_APPS: set = {"CtaStrategy", "CtaBacktester", "DataManager", "PortfolioManager", "PaperAccount"}
_APPS_ICON = str(_ICO_DIR / "editor.ico")

APP_GROUPS: List[Tuple[str, str, str, List[str]]] = [
    ("交易执行", "📊", "#4a6cf7", [
        "CtaStrategy", "CtaBacktester", "ExecutionEngine",
        "LiveProduction", "ExecutionIntelligence",
    ]),
    ("研究平台", "🔬", "#13c2c2", [
        "BatchResearch", "FactorResearch", "ResearchValidation",
        "QuantResearch", "ResearchOps", "StrategyCondition",
        "KLineBehaviorLab",
    ]),
    ("AI 智能", "🤖", "#722ed1", [
        "AlphaFactory2", "CapitalAllocation", "MarketRegime",
        "StrategyLifecycle", "AdaptiveLearning", "DataIntelligence",
        "MarketReality", "TemporalIntelligence",
    ]),
    ("组合风控", "🛡", "#fa8c16", [
        "PortfolioEngine", "RiskEngine2",
        "GlobalPortfolioIntelligence", "PlatformEngineering",
    ]),
    ("基础设施", "⚙", "#52c41a", [
        "DataManager", "QuantOS", "SystemIntegrationBus",
        "PerformanceMonitor", "BacktestBridge", "SystemConsole",
    ]),
]

_GROUPED: set = {n for _, _, _, ns in APP_GROUPS for n in ns}


def _rgba(c: str, a: int) -> str:
    h = c.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


class AppCard(QtWidgets.QPushButton):
    def __init__(self, display_name: str, func: Callable,
                 accent: str = "#4a6cf7", parent=None):
        super().__init__(parent)
        parts  = display_name.split("  ", 1)
        short  = parts[0].strip()[:16]
        sub    = parts[1].strip()[:22] if len(parts) > 1 else ""
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)
        for text, style in [
            (short, "color:#fff;font-size:14px;font-weight:bold;"
                    "background:transparent;border:none;"),
            (sub,   "color:rgba(255,255,255,0.55);font-size:14px;"
                    "background:transparent;border:none;"),
        ]:
            if not text:
                continue
            lbl = QtWidgets.QLabel(text)
            lbl.setStyleSheet(style)
            lbl.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            lay.addWidget(lbl)
        self.setToolTip(display_name)
        self.setFixedSize(220, 66)
        self.clicked.connect(func)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton{{background:{_rgba(accent,28)};
                border:1px solid {_rgba(accent,60)};border-radius:6px;}}
            QPushButton:hover{{background:{_rgba(accent,55)};
                border:1px solid {accent};}}
            QPushButton:pressed{{background:{_rgba(accent,80)};}}
        """)


class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent=None, hs=10, vs=10):
        super().__init__(parent)
        self._hs = hs; self._vs = vs; self._items = []

    def addItem(self, item):        self._items.append(item)
    def count(self):                return len(self._items)
    def itemAt(self, i):            return self._items[i] if 0 <= i < len(self._items) else None
    def takeAt(self, i):            return self._items.pop(i) if 0 <= i < len(self._items) else None
    def expandingDirections(self):  return QtCore.Qt.Orientation(0)
    def hasHeightForWidth(self):    return True
    def heightForWidth(self, w):    return self._layout(QtCore.QRect(0, 0, w, 0), True)
    def setGeometry(self, r):       super().setGeometry(r); self._layout(r, False)
    def sizeHint(self):             return self.minimumSize()

    def minimumSize(self):
        s = QtCore.QSize()
        for it in self._items: s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return s + QtCore.QSize(m.left()+m.right(), m.top()+m.bottom())

    def _layout(self, rect, test):
        m = self.contentsMargins()
        r = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, rh = r.x(), r.y(), 0
        for it in self._items:
            nx = x + it.sizeHint().width() + self._hs
            if nx - self._hs > r.right() and rh > 0:
                x = r.x(); y += rh + self._vs; nx = x + it.sizeHint().width() + self._hs; rh = 0
            if not test:
                it.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), it.sizeHint()))
            x = nx; rh = max(rh, it.sizeHint().height())
        return y + rh - rect.y() + m.bottom()


class GroupBox(QtWidgets.QWidget):
    def __init__(self, label: str, emoji: str, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 16); lay.setSpacing(8)
        hdr = QtWidgets.QLabel(f"  {emoji}  {label}")
        hdr.setFixedHeight(34)
        hdr.setStyleSheet(
            f"color:{color};font-size:14px;font-weight:bold;"
            f"background:{_rgba(color,18)};"
            f"border-left:3px solid {color};"
            f"border-radius:2px;padding-left:6px;")
        lay.addWidget(hdr)
        self._flow_w = QtWidgets.QWidget()
        self._flow   = FlowLayout(self._flow_w, hs=10, vs=8)
        lay.addWidget(self._flow_w)

    def add_app(self, display_name: str, func: Callable):
        self._flow.addWidget(AppCard(display_name, func, self._color))


class VeighNaAppsWindow(QtWidgets.QDialog):
    def __init__(self, app_funcs: Dict[str, tuple], parent=None):
        super().__init__(parent)
        self.setWindowTitle("VeighNa Apps  —  量化平台应用中心")
        self.setMinimumSize(880, 560)
        self.resize(1040, 660)
        self.setWindowFlags(
            self.windowFlags() |
            QtCore.Qt.WindowType.WindowMaximizeButtonHint)
        self.setStyleSheet("background:#0d1117;")
        self._build(app_funcs)

    def _build(self, app_funcs):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # 标题栏
        hdr = QtWidgets.QWidget()
        hdr.setFixedHeight(54)
        hdr.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #0d1117,stop:1 #1a1f36);")
        hl = QtWidgets.QHBoxLayout(hdr)
        hl.setContentsMargins(24, 0, 24, 0)
        for text, style in [
            ("⚡", "font-size:20px;color:#58a6ff;background:transparent;"),
            ("VeighNa Apps",
             "color:#fff;font-size:17px;font-weight:bold;"
             "background:transparent;margin-left:6px;"),
            ("量化平台应用中心",
             "color:rgba(255,255,255,0.4);font-size:14px;"
             "background:transparent;margin-left:10px;"),
        ]:
            lbl = QtWidgets.QLabel(text); lbl.setStyleSheet(style)
            hl.addWidget(lbl)
        hl.addStretch()
        # 使用实际加载成功的应用数量
        total = len(app_funcs)
        cnt = QtWidgets.QLabel(f"{total} 个应用")
        cnt.setStyleSheet("color:#58a6ff;font-size:14px;background:transparent;")
        hl.addWidget(cnt)
        root.addWidget(hdr)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet("color:#21262d;")
        root.addWidget(sep)

        # 滚动区
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea{background:#0d1117;}"
            "QScrollBar:vertical{background:#161b22;width:6px;margin:0;}"
            "QScrollBar::handle:vertical{background:#30363d;"
            "border-radius:3px;min-height:24px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}")

        body = QtWidgets.QWidget()
        body.setStyleSheet("background:#0d1117;")
        bl = QtWidgets.QVBoxLayout(body)
        bl.setContentsMargins(24, 18, 24, 24); bl.setSpacing(4)

        for label, emoji, color, app_names in APP_GROUPS:
            items = [(n,)+app_funcs[n] for n in app_names if n in app_funcs]
            if not items: continue
            grp = GroupBox(label, emoji, color)
            for _, dname, func in items:
                grp.add_app(dname, func)
            bl.addWidget(grp)

        ungrouped = [(n,)+v for n,v in app_funcs.items() if n not in _GROUPED]
        if ungrouped:
            grp = GroupBox("其他", "📎", "#8c8c8c")
            for _, dname, func in ungrouped:
                grp.add_app(dname, func)
            bl.addWidget(grp)

        bl.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

    def closeEvent(self, event):
        self.hide(); event.ignore()


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

    # ── 功能菜单：只保留三个固定 App + VeighNa Apps 入口 ────────
    _MENU_APPS = {"CtaBacktester", "DataManager", "PortfolioManager", "PaperAccount"}
    app_menu = bar.addMenu("功能")
    self._app_funcs: Dict[str, tuple] = {}

    for app in self.main_engine.get_all_apps():
        try:
            ui_mod = import_module(app.app_module + ".ui")
            wcls   = getattr(ui_mod, app.widget_name)
        except Exception as _e:
            import traceback
            _logger.warning(
                "跳过应用 %s: %s\n%s", app.app_name, _e,
                traceback.format_exc())
            continue
        func = partial(self.open_widget, wcls, app.app_name)
        on_toolbar = app.app_name in _TOOLBAR_APPS
        # 菜单只保留三个，其余只收入弹窗
        if app.app_name in _MENU_APPS:
            self.add_action(app_menu, app.display_name,
                            app.icon_name, func, toolbar=on_toolbar)
        elif on_toolbar:
            # 工具栏白名单但不在菜单里（CtaStrategy）：只加工具栏
            icon = QtGui.QIcon(app.icon_name)
            act  = QtGui.QAction(app.display_name, self)
            act.setIcon(icon)
            act.triggered.connect(func)
            self.toolbar.addAction(act)
        self._app_funcs[app.app_name] = (app.display_name, func)

    # VeighNa Apps 菜单项（功能菜单最末）
    app_menu.addSeparator()
    def _open_apps():
        if self._apps_window is None:
            self._apps_window = VeighNaAppsWindow(self._app_funcs, self)
        self._apps_window.show()
        self._apps_window.raise_()
        self._apps_window.activateWindow()
    va_menu_act = QtGui.QAction("VeighNa Apps — 量化平台应用中心", self)
    va_menu_act.setIcon(QtGui.QIcon(_APPS_ICON))
    va_menu_act.triggered.connect(_open_apps)
    app_menu.addAction(va_menu_act)

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

def apply_sidebar_patch() -> None:
    """在 MainWindow 实例化前调用。"""
    _inject_portfolio_icon()
    from vnpy.trader.ui.mainwindow import MainWindow
    MainWindow.init_menu = _patched_init_menu