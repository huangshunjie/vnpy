"""
quant_research/ui/widget.py

ResearchPlatformWidget — 量化研究平台主窗口（Phase 8 动态 ProjectExplorer）。
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QSplitter,
    QTabWidget, QTreeWidget, QTreeWidgetItem,
    QLabel, QVBoxLayout, QPushButton, QMenu,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import MainEngine

from ..engine import ResearchEngine
from ..constant import APP_NAME
from ..event import (
    EVENT_EXPERIMENT_CREATED, EVENT_EXPERIMENT_UPDATED, EVENT_EXPERIMENT_DELETED,
    EVENT_DATASET_CREATED,    EVENT_DATASET_UPDATED,    EVENT_DATASET_DELETED,
    EVENT_FEATURE_CREATED,    EVENT_FEATURE_UPDATED,    EVENT_FEATURE_DELETED,
    EVENT_STRATEGY_CREATED,   EVENT_STRATEGY_UPDATED,   EVENT_STRATEGY_DELETED,
    EVENT_MODEL_CREATED,      EVENT_MODEL_UPDATED,      EVENT_MODEL_DELETED,
    EVENT_BACKTEST_CREATED,   EVENT_BACKTEST_UPDATED,   EVENT_BACKTEST_DELETED,
)

from .dashboard_tab  import DashboardTab
from .experiment_tab import ExperimentTab
from .dataset_tab    import DatasetTab
from .feature_tab    import FeatureTab
from .strategy_tab   import StrategyTab
from .model_tab      import ModelTab
from .backtest_tab   import BacktestTab
from .report_tab     import ReportTab
from .pipeline_tab   import PipelineTab
from .artifact_tab   import ArtifactTab
from .log_tab        import LogTab


# ─────────────────────────────────────────────────────────────────────
# Tab index constants — keep in sync with addTab order
# ─────────────────────────────────────────────────────────────────────
TAB_DASHBOARD  = 0
TAB_EXPERIMENT = 1
TAB_DATASET    = 2
TAB_FEATURE    = 3
TAB_STRATEGY   = 4
TAB_MODEL      = 5
TAB_BACKTEST   = 6
TAB_REPORT     = 7
TAB_PIPELINE   = 8
TAB_ARTIFACT   = 9
TAB_LOG        = 10


class ProjectExplorer(QWidget):
    """左侧项目资源管理器 — 动态数据驱动（Phase 8）。"""

    # 节点类型标记
    _TYPE_KEY = Qt.UserRole
    _ID_KEY   = Qt.UserRole + 1
    _TAB_KEY  = Qt.UserRole + 2

    def __init__(self, engine: ResearchEngine,
                 on_navigate=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._on_navigate = on_navigate   # callback(tab_index)
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(4, 4, 4, 4)
        lyt.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel("资源管理器")
        title.setStyleSheet("font-weight:bold; color:#495057; padding:2px;")
        header.addWidget(title)
        header.addStretch()
        refresh_btn = QPushButton("↺")
        refresh_btn.setFixedSize(22, 22)
        refresh_btn.setToolTip("刷新")
        refresh_btn.clicked.connect(self._refresh)
        header.addWidget(refresh_btn)
        lyt.addLayout(header)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setColumnCount(1)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        lyt.addWidget(self._tree)

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in (
            EVENT_EXPERIMENT_CREATED, EVENT_EXPERIMENT_UPDATED, EVENT_EXPERIMENT_DELETED,
            EVENT_DATASET_CREATED,    EVENT_DATASET_UPDATED,    EVENT_DATASET_DELETED,
            EVENT_FEATURE_CREATED,    EVENT_FEATURE_UPDATED,    EVENT_FEATURE_DELETED,
            EVENT_STRATEGY_CREATED,   EVENT_STRATEGY_UPDATED,   EVENT_STRATEGY_DELETED,
            EVENT_MODEL_CREATED,      EVENT_MODEL_UPDATED,      EVENT_MODEL_DELETED,
            EVENT_BACKTEST_CREATED,   EVENT_BACKTEST_UPDATED,   EVENT_BACKTEST_DELETED,
        ):
            ee.register(ev, self._on_event)

    def _on_event(self, event: Event):
        self._refresh()

    def _refresh(self):
        self._tree.clear()

        sections = [
            ("实验中心",
             TAB_EXPERIMENT,
             "experiment",
             self._engine.list_experiments(),
             lambda r: r.experiment_id,
             lambda r: r.name,
             lambda r: r.status.value),
            ("数据集",
             TAB_DATASET,
             "dataset",
             self._engine.list_datasets(),
             lambda r: r.dataset_id,
             lambda r: r.name,
             lambda r: r.status.value),
            ("因子库",
             TAB_FEATURE,
             "feature",
             self._engine.list_features(),
             lambda r: r.feature_id,
             lambda r: r.name,
             lambda r: r.status.value),
            ("策略库",
             TAB_STRATEGY,
             "strategy",
             self._engine.list_strategies(),
             lambda r: r.strategy_id,
             lambda r: r.name,
             lambda r: r.status.value),
            ("模型库",
             TAB_MODEL,
             "model",
             self._engine.list_models(),
             lambda r: r.model_id,
             lambda r: r.name,
             lambda r: r.status.value),
            ("回测记录",
             TAB_BACKTEST,
             "backtest",
             self._engine.list_backtests(),
             lambda r: r.backtest_id,
             lambda r: r.name,
             lambda r: r.status.value),
        ]

        for title, tab_idx, type_key, records, get_id, get_name, get_status in sections:
            count = len(records)
            parent_item = QTreeWidgetItem([f"{title}  ({count})"])
            parent_item.setData(0, self._TYPE_KEY, "section")
            parent_item.setData(0, self._TAB_KEY, tab_idx)
            parent_item.setExpanded(True)

            for rec in records[-20:]:   # 最多显示最近 20 条
                label = f"{get_id(rec)}  {get_name(rec)}"
                status = get_status(rec)
                child = QTreeWidgetItem([label])
                child.setData(0, self._TYPE_KEY, type_key)
                child.setData(0, self._ID_KEY,   get_id(rec))
                child.setData(0, self._TAB_KEY,  tab_idx)
                child.setToolTip(0, f"{label} [{status}]")
                parent_item.addChild(child)

            if count > 20:
                more = QTreeWidgetItem([f"  … 共 {count} 条，双击节标题查看全部"])
                more.setData(0, self._TYPE_KEY, "more")
                more.setData(0, self._TAB_KEY,  tab_idx)
                parent_item.addChild(more)

            self._tree.addTopLevelItem(parent_item)

    def _on_double_click(self, item: QTreeWidgetItem, _col: int):
        tab_idx = item.data(0, self._TAB_KEY)
        if tab_idx is not None and self._on_navigate:
            self._on_navigate(tab_idx)

    def _on_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        if not item:
            return
        tab_idx = item.data(0, self._TAB_KEY)
        if tab_idx is None:
            return

        menu = QMenu(self)
        nav_action = QAction("跳转到该模块", self)
        nav_action.triggered.connect(
            lambda: self._on_navigate(tab_idx) if self._on_navigate else None)
        menu.addAction(nav_action)
        menu.exec(self._tree.viewport().mapToGlobal(pos))


class ResearchPlatformWidget(QWidget):
    """量化研究平台主窗口。"""

    widget_name: str = "ResearchPlatformWidget"

    def __init__(self, main_engine: MainEngine,
                 event_engine: EventEngine) -> None:
        super().__init__()
        self.main_engine  = main_engine
        self.event_engine = event_engine
        self.engine: ResearchEngine = main_engine.get_engine(APP_NAME)
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Quant Research Platform  量化研究平台")
        self.resize(1440, 920)

        splitter = QSplitter(Qt.Horizontal)

        # 左侧 ProjectExplorer（动态）
        self._explorer = ProjectExplorer(
            self.engine,
            on_navigate=self._navigate_to_tab,
        )
        self._explorer.setMinimumWidth(220)
        self._explorer.setMaximumWidth(320)
        splitter.addWidget(self._explorer)

        # 右侧 TabWidget
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.North)
        self._tabs.setDocumentMode(True)

        self._dashboard_tab  = DashboardTab(self.engine)
        self._experiment_tab = ExperimentTab(self.engine)
        self._dataset_tab    = DatasetTab(self.engine)
        self._feature_tab    = FeatureTab(self.engine)
        self._strategy_tab   = StrategyTab(self.engine)
        self._model_tab      = ModelTab(self.engine)
        self._backtest_tab   = BacktestTab(self.engine)
        self._report_tab     = ReportTab(self.engine)
        self._pipeline_tab   = PipelineTab(self.engine)
        self._artifact_tab   = ArtifactTab(self.engine)
        self._log_tab        = LogTab(self.engine)

        tabs = [
            (self._dashboard_tab,  "📊 Dashboard"),
            (self._experiment_tab, "🔬 Experiments"),
            (self._dataset_tab,    "🗄 Datasets"),
            (self._feature_tab,    "🧩 Features"),
            (self._strategy_tab,   "📈 Strategies"),
            (self._model_tab,      "🤖 Models"),
            (self._backtest_tab,   "⏮ Backtests"),
            (self._report_tab,     "📄 Reports"),
            (self._pipeline_tab,   "⚙ Pipelines"),
            (self._artifact_tab,   "📦 Artifacts"),
            (self._log_tab,        "📋 Logs"),
        ]
        for widget, label in tabs:
            self._tabs.addTab(widget, label)

        splitter.addWidget(self._tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.addWidget(splitter)

    def _navigate_to_tab(self, tab_index: int):
        self._tabs.setCurrentIndex(tab_index)
