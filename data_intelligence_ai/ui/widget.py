"""
data_intelligence_ai/ui/widget.py  (Phase 1 Stub)

DataIntelligenceWidget — 数据智能系统主窗口骨架。
布局：左侧数据状态面板 + 右侧 6-Tab（全部占位）。
Phase 1: 全部为空占位，无任何功能逻辑。
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine, EventEngine
from ..event import APP_NAME

_BG  = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"; _FG = "#cdd6f4"
_MUT = "#6c7086"; _BLUE = "#89b4fa"; _GRN  = "#a6e3a1"; _YLW = "#f9e2af"
_RED = "#f38ba8"; _MAV  = "#cba6f7"; _HEAD = "#313244"; _CYN = "#89dceb"
_TEA = "#94e2d5"


class DataIntelligenceWidget(QtWidgets.QMainWindow):
    """
    数据智能系统主窗口（Phase 1）。

    左侧：数据系统状态面板（占位）
    右侧：6-Tab 布局
      0. Dashboard    — 总览
      1. Ingestion    — 数据接入
      2. Feature Store— 特征仓库
      3. Quality      — 数据质量
      4. Fusion       — 数据融合
      5. Logs         — 日志流
    """

    widget_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine       = main_engine.get_engine(APP_NAME)
        self._init_ui()
        self._init_menu()

    # ── UI construction ───────────────────────────────────────────────
    def _init_ui(self) -> None:
        self.setWindowTitle("Data Intelligence AI  数据智能系统")
        self.resize(1440, 840)
        self.setStyleSheet(f"background:{_BG}; color:{_FG};")

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self._build_status_panel(), stretch=0)
        layout.addWidget(self._build_tab_widget(),   stretch=1)

    def _build_status_panel(self) -> QtWidgets.QWidget:
        """左侧数据状态面板（Phase 1 占位）。"""
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(220)
        panel.setStyleSheet(
            f"background:{_DARK};border-radius:6px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(12, 14, 12, 14)
        vb.setSpacing(12)

        title = QtWidgets.QLabel("数据系统状态")
        title.setStyleSheet(
            f"color:{_TEA};font-weight:bold;font-size:13px;border:none;")
        vb.addWidget(title)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(
            f"border:none;border-top:1px solid {_BORDER};background:transparent;")
        vb.addWidget(sep)

        self._status_labels: dict[str, QtWidgets.QLabel] = {}
        for key, label in [
            ("status",   "系统状态"),
            ("phase",    "当前阶段"),
            ("uptime",   "运行时间"),
            ("ingested", "接入数据"),
            ("features", "特征数量"),
            ("quality",  "质量评分"),
            ("fusions",  "融合次数"),
        ]:
            row = QtWidgets.QWidget()
            row.setStyleSheet("background:transparent;border:none;")
            rh = QtWidgets.QHBoxLayout(row)
            rh.setContentsMargins(0, 0, 0, 0)

            lk = QtWidgets.QLabel(label)
            lk.setStyleSheet(
                f"color:{_MUT};font-size:10px;border:none;background:transparent;")
            lk.setFixedWidth(72)

            lv = QtWidgets.QLabel("--")
            lv.setStyleSheet(
                f"color:{_FG};font-size:11px;font-weight:bold;"
                f"border:none;background:transparent;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

            rh.addWidget(lk); rh.addStretch(); rh.addWidget(lv)
            self._status_labels[key] = lv
            vb.addWidget(row)

        vb.addStretch()

        btn_start = QtWidgets.QPushButton("▶  启动数据引擎")
        btn_start.setStyleSheet(
            f"QPushButton{{background:{_TEA};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:8px;font-size:11px;}}"
            f"QPushButton:hover{{background:#89dceb;}}")
        btn_start.clicked.connect(self._on_start)
        vb.addWidget(btn_start)

        btn_refresh = QtWidgets.QPushButton("刷新状态")
        btn_refresh.setStyleSheet(
            f"QPushButton{{background:transparent;color:{_MUT};"
            f"border:1px solid {_BORDER};border-radius:4px;"
            f"padding:6px;font-size:11px;}}"
            f"QPushButton:hover{{background:{_HEAD};}}")
        btn_refresh.clicked.connect(self._on_refresh)
        vb.addWidget(btn_refresh)

        return panel

    def _build_tab_widget(self) -> QtWidgets.QTabWidget:
        """右侧 6-Tab 布局（Phase 1 全部占位）。"""
        tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane{{background:{_DARK};border:1px solid {_BORDER};"
            f"border-radius:4px;}}"
            f"QTabBar::tab{{background:{_HEAD};color:{_MUT};"
            f"padding:8px 16px;font-size:11px;border:none;"
            f"border-bottom:2px solid transparent;margin-right:2px;}}"
            f"QTabBar::tab:selected{{color:{_FG};border-bottom:2px solid {_TEA};}}"
            f"QTabBar::tab:hover{{color:{_FG};background:{_BORDER};}}")

        tab_defs = [
            ("Dashboard",    "总览",      _TEA),
            ("Ingestion",    "数据接入",  _BLUE),
            ("Feature Store","特征仓库",  _GRN),
            ("Quality",      "数据质量",  _YLW),
            ("Fusion",       "数据融合",  _MAV),
            ("Logs",         "日志流",    _MUT),
        ]
        for eng_name, cn_name, color in tab_defs:
            tabs.addTab(
                self._build_placeholder(eng_name, cn_name, color),
                f"{eng_name}  {cn_name}")

        self._tabs = tabs
        return tabs

    def _build_placeholder(self, name: str, cn: str,
                            color: str) -> QtWidgets.QWidget:
        """Phase 1 Tab 占位页面。"""
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_DARK};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QtWidgets.QLabel("◈")
        icon_lbl.setStyleSheet(
            f"color:{color};font-size:48px;border:none;background:transparent;")
        icon_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        name_lbl = QtWidgets.QLabel(name)
        name_lbl.setStyleSheet(
            f"color:{color};font-size:20px;font-weight:bold;"
            f"border:none;background:transparent;")
        name_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        cn_lbl = QtWidgets.QLabel(cn)
        cn_lbl.setStyleSheet(
            f"color:{_MUT};font-size:13px;border:none;background:transparent;")
        cn_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        phase_lbl = QtWidgets.QLabel("Phase 1  —  占位中，待后续阶段实现")
        phase_lbl.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:1px solid {_BORDER};"
            f"border-radius:3px;padding:6px 16px;background:{_HEAD};")
        phase_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        vb.addStretch()
        vb.addWidget(icon_lbl)
        vb.addWidget(name_lbl)
        vb.addWidget(cn_lbl)
        vb.addSpacing(20)
        vb.addWidget(phase_lbl)
        vb.addStretch()
        return w

    # ── menu ─────────────────────────────────────────────────────────
    def _init_menu(self) -> None:
        mb = self.menuBar()
        mb.setStyleSheet(
            f"QMenuBar{{background:{_DARK};color:{_FG};border:none;}}"
            f"QMenuBar::item:selected{{background:{_HEAD};}}"
            f"QMenu{{background:{_DARK};color:{_FG};border:1px solid {_BORDER};}}"
            f"QMenu::item:selected{{background:{_HEAD};}}")

        sys_menu = mb.addMenu("系统")
        sys_menu.addAction("启动引擎").triggered.connect(self._on_start)
        sys_menu.addAction("停止引擎").triggered.connect(self._on_stop)
        sys_menu.addSeparator()
        sys_menu.addAction("关闭窗口").triggered.connect(self.close)

    # ── slots ─────────────────────────────────────────────────────────
    def _on_start(self) -> None:
        if self._engine:
            self._engine.init()
            self._engine.start()
            self._on_refresh()

    def _on_stop(self) -> None:
        if self._engine:
            self._engine.stop()
            self._on_refresh()

    def _on_refresh(self) -> None:
        if self._engine is None:
            return
        summ = self._engine.get_summary()
        self._status_labels["status"].setText(summ.get("status", "--"))
        self._status_labels["phase"].setText(
            f"Phase {summ.get('phase', 1)}")
        self._status_labels["uptime"].setText(
            f"{summ.get('uptime', 0):.0f}s")
        eng = summ.get("engine", {})
        self._status_labels["ingested"].setText(
            str(eng.get("ingest_count", 0)))
        self._status_labels["features"].setText(
            str(eng.get("feature_count", 0)))
        self._status_labels["quality"].setText("--")
        self._status_labels["fusions"].setText("--")
