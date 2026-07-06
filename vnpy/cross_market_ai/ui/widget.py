"""
cross_market_ai/ui/widget.py

Cross-Market Intelligence System — 主窗口。
Phase 5: 左侧状态面板展示全五阶段数据。
"""
from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtWidgets, QtCore

from ..constant import APP_NAME, APP_VERSION, EngineStatus
from ..engine import CrossMarketEngine
from ..event import EVENT_CROSS_MARKET_LOG

from .dashboard_tab  import DashboardTab
from .structure_tab  import StructureTab
from .transfer_tab   import TransferTab
from .regime_tab     import RegimeTab
from .scoring_tab    import ScoringTab
from .validation_tab import ValidationTab
from .log_tab        import LogTab


class CrossMarketWidget(QtWidgets.QMainWindow):
    """
    跨市场智能系统主窗口。
    左侧 — 系统状态面板（Phase 2-5 全数据）
    右侧 — 7 个功能 Tab
    """

    signal_log = QtCore.pyqtSignal(dict)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._cm_engine: CrossMarketEngine = main_engine.get_engine(APP_NAME)
        self._init_ui()
        self._register_events()

    def _init_ui(self) -> None:
        self.setWindowTitle(f"Cross-Market Intelligence System  {APP_VERSION}")
        self.setMinimumSize(1420, 860)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        self._status_panel = SystemStatusPanel(self._cm_engine)
        root.addWidget(self._status_panel, stretch=0)

        self._tabs = QtWidgets.QTabWidget()
        self._tabs.setDocumentMode(True)

        self._tab_dashboard  = DashboardTab( self._main_engine, self._event_engine)
        self._tab_structure  = StructureTab( self._main_engine, self._event_engine)
        self._tab_transfer   = TransferTab(  self._main_engine, self._event_engine)
        self._tab_regime     = RegimeTab(    self._main_engine, self._event_engine)
        self._tab_scoring    = ScoringTab(   self._main_engine, self._event_engine)
        self._tab_validation = ValidationTab(self._main_engine, self._event_engine)
        self._tab_log        = LogTab(       self._main_engine, self._event_engine)

        self._tabs.addTab(self._tab_dashboard,  "Dashboard  总览")
        self._tabs.addTab(self._tab_structure,  "Structure  结构映射")
        self._tabs.addTab(self._tab_transfer,   "Transfer   Alpha迁移")
        self._tabs.addTab(self._tab_regime,     "Regime     状态对齐")
        self._tabs.addTab(self._tab_scoring,    "Scoring    普适性评分")
        self._tabs.addTab(self._tab_validation, "Validation 跨市场验证")
        self._tabs.addTab(self._tab_log,        "Logs       日志")

        root.addWidget(self._tabs, stretch=1)
        self._build_toolbar()

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Controls")
        toolbar.setMovable(False)

        btn_start = QtWidgets.QAction("▶  启动引擎", self)
        btn_start.triggered.connect(self._on_start)
        toolbar.addAction(btn_start)

        btn_stop = QtWidgets.QAction("■  停止引擎", self)
        btn_stop.triggered.connect(self._on_stop)
        toolbar.addAction(btn_stop)

        toolbar.addSeparator()

        self._lbl_status = QtWidgets.QLabel(f"状态: {EngineStatus.IDLE.value}")
        self._lbl_status.setStyleSheet("padding: 0 8px; font-weight: bold;")
        toolbar.addWidget(self._lbl_status)

    def _register_events(self) -> None:
        self.signal_log.connect(self._on_log)
        self._event_engine.register(EVENT_CROSS_MARKET_LOG, self.signal_log.emit)

    def _on_start(self) -> None:
        self._cm_engine.init()
        self._cm_engine.start()
        self._lbl_status.setText(f"状态: {EngineStatus.RUNNING.value}")
        self._status_panel.refresh()

    def _on_stop(self) -> None:
        self._cm_engine.stop()
        self._lbl_status.setText(f"状态: {EngineStatus.STOPPED.value}")
        self._status_panel.refresh()

    def _on_log(self, data: dict) -> None:
        self._tab_log.append_log(data.get("line", ""))
        self._status_panel.refresh()

    def closeEvent(self, event) -> None:
        self._cm_engine.stop()
        self._event_engine.unregister(EVENT_CROSS_MARKET_LOG, self.signal_log.emit)
        super().closeEvent(event)


# ── 左侧系统状态面板（Phase 5 完整版）─────────────────────────────────

class SystemStatusPanel(QtWidgets.QFrame):
    """左侧跨市场系统状态面板 — Phase 5 五阶段全数据。"""

    def __init__(self, engine: CrossMarketEngine) -> None:
        super().__init__()
        self._engine = engine
        self.setFixedWidth(240)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._rows: dict[str, QtWidgets.QLabel] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(3)

        title = QtWidgets.QLabel("Cross-Market AI")
        title.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#4fc3f7;"
        )
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(_sep())

        for key, label in [
            ("version", "版本"),
            ("phase",   "阶段"),
            ("status",  "状态"),
            ("uptime",  "运行时长(s)"),
        ]:
            self._add_row(layout, key, label)
        layout.addWidget(_sep())

        lbl_p2 = QtWidgets.QLabel("Phase 2 — 市场结构映射")
        lbl_p2.setStyleSheet("color:#2e7d32; font-size:10px; font-weight:bold;")
        layout.addWidget(lbl_p2)
        for key, label in [
            ("markets_mapped", "已映射市场"),
            ("last_market",    "最近映射"),
        ]:
            self._add_row(layout, key, label)
        self._lbl_markets = QtWidgets.QLabel("-")
        self._lbl_markets.setStyleSheet(
            "color:#4fc3f7; font-size:9px; padding:1px;"
        )
        self._lbl_markets.setWordWrap(True)
        layout.addWidget(self._lbl_markets)

        layout.addWidget(_sep())

        lbl_p3 = QtWidgets.QLabel("Phase 3 — 迁移 / Regime")
        lbl_p3.setStyleSheet("color:#6a1b9a; font-size:10px; font-weight:bold;")
        layout.addWidget(lbl_p3)
        for key, label in [
            ("total_transfers",    "迁移次数"),
            ("avg_transfer_coeff", "平均T系数"),
            ("total_alignments",   "Regime对齐"),
        ]:
            self._add_row(layout, key, label)

        layout.addWidget(_sep())

        lbl_p4 = QtWidgets.QLabel("Phase 4 — 普适性评分")
        lbl_p4.setStyleSheet("color:#e65100; font-size:10px; font-weight:bold;")
        layout.addWidget(lbl_p4)
        for key, label in [
            ("total_scored",    "已评分Alpha"),
            ("avg_univ_score",  "平均普适性分"),
            ("top_alpha",       "最高Alpha"),
            ("universal_count", "UNIVERSAL"),
            ("portable_count",  "PORTABLE"),
        ]:
            self._add_row(layout, key, label)

        layout.addWidget(_sep())

        lbl_p5 = QtWidgets.QLabel("Phase 5 — 跨市场验证")
        lbl_p5.setStyleSheet("color:#1565c0; font-size:10px; font-weight:bold;")
        layout.addWidget(lbl_p5)
        for key, label in [
            ("total_validations", "验证次数"),
            ("validation_passed", "PASS"),
            ("validation_failed", "FAIL"),
            ("avg_decay_rate",    "平均衰减率"),
        ]:
            self._add_row(layout, key, label)

        layout.addStretch()

        note = QtWidgets.QLabel("Full Pipeline  Phase 2-5")
        note.setStyleSheet("color:#555; font-size:10px;")
        note.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(note)

        self.refresh()

    def _add_row(self, layout: QtWidgets.QVBoxLayout,
                 key: str, label: str) -> None:
        row = _LabelRow(label)
        layout.addWidget(row)
        self._rows[key] = row.value_label

    def refresh(self) -> None:
        s = self._engine.get_summary()

        def _set(key: str, val) -> None:
            if key in self._rows:
                self._rows[key].setText(str(val))

        _set("version",           s.get("version", "-"))
        _set("phase",             f"Phase {s.get('phase', 5)}")
        _set("status",            s.get("status", "-"))
        _set("uptime",            s.get("uptime", 0.0))
        _set("markets_mapped",    s.get("markets_mapped", 0))
        _set("last_market",       s.get("last_market", "-") or "-")
        mapped = s.get("mapped_list", [])
        self._lbl_markets.setText(", ".join(mapped) if mapped else "-")
        _set("total_transfers",    s.get("total_transfers",    0))
        _set("avg_transfer_coeff", f"{s.get('avg_transfer_coeff', 0.0):.3f}")
        _set("total_alignments",   s.get("total_alignments",   0))
        _set("total_scored",       s.get("total_scored",       0))
        _set("avg_univ_score",     f"{s.get('avg_univ_score', 0.0):.3f}")
        _set("top_alpha",          s.get("top_alpha", "-") or "-")
        _set("universal_count",    s.get("universal_count",    0))
        _set("portable_count",     s.get("portable_count",     0))
        _set("total_validations",  s.get("total_validations",  0))
        _set("validation_passed",  s.get("validation_passed",  0))
        _set("validation_failed",  s.get("validation_failed",  0))
        _set("avg_decay_rate",     f"{s.get('avg_decay_rate', 0.0):.3f}")


# ── 小工具 ────────────────────────────────────────────────────────────

def _sep() -> QtWidgets.QFrame:
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return line


class _LabelRow(QtWidgets.QWidget):
    def __init__(self, label: str) -> None:
        super().__init__()
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QtWidgets.QLabel(f"{label}:")
        lbl.setStyleSheet("color:#aaa; font-size:10px;")
        lbl.setFixedWidth(96)

        self.value_label = QtWidgets.QLabel("-")
        self.value_label.setStyleSheet("font-size:10px;")

        layout.addWidget(lbl)
        layout.addWidget(self.value_label)
