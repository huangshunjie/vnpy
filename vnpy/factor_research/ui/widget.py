"""

factor_research/ui/widget.py



FactorResearchWidget — 因子研究工作台主窗口。



布局：

┌──────────────────────────────────────────────────────────┐

│  标题栏                                                    │

├────────────┬─────────────────────────────────────────────┤

│            │  Tab①  Tab②  ...  Tab⑫                      │

│  左侧配置区 │─────────────────────────────────────────────│

│  LeftPanel │                                              │

│            │  当前 Tab 内容                                │

│            │                                              │

├────────────┴─────────────────────────────────────────────┤

│  状态栏（日志最新一条）                                      │

└──────────────────────────────────────────────────────────┘



设计原则：

  - 继承 QMainWindow，以独立窗口 show() 打开

  - Widget 不访问数据库，不写算法

  - 通过 Signal/Slot 接收 EventEngine 事件，避免跨线程操作 Qt

  - 每个 Tab 独立文件，widget.py 只负责组装与路由

  - _on_plot_ready 按 event.data["tab"] 路由到对应 Tab 的 update_* 方法

"""



from __future__ import annotations



from vnpy.event import Event, EventEngine

from vnpy.trader.engine import MainEngine

from vnpy.trader.ui import QtCore, QtWidgets



from ..constant import APP_NAME

from ..event import (

    EVENT_FACTOR_ERROR,

    EVENT_FACTOR_FINISHED,

    EVENT_FACTOR_LOG,

    EVENT_FACTOR_PLOT_READY,

    EVENT_FACTOR_PROGRESS,

)

from ..dispatcher import FactorResearchEngine

from .left_panel import LeftPanel

from .overview_tab import OverviewTab

from .ic_tab import IcTab

from .ic_series_tab import IcSeriesTab

from .ic_distribution_tab import IcDistributionTab

from .quantile_tab import QuantileTab

from .longshort_tab import LongShortTab

from .decay_tab import DecayTab

from .correlation_tab import CorrelationTab

from .redundancy_tab import RedundancyTab

from .score_tab import ScoreTab

from .stability_tab import StabilityTab

from .report_tab import ReportTab





class FactorResearchWidget(QtWidgets.QMainWindow):

    """

    因子研究工作台主窗口。



    通过 main_engine.get_engine(APP_NAME) 持有 FactorResearchEngine 引用。

    事件订阅使用 Signal/Slot 保证线程安全。

    _on_plot_ready 按 event.data["tab"] 把数据路由到对应 Tab。

    """



    signal_log:        QtCore.Signal = QtCore.Signal(Event)

    signal_progress:   QtCore.Signal = QtCore.Signal(Event)

    signal_finished:   QtCore.Signal = QtCore.Signal(Event)

    signal_error:      QtCore.Signal = QtCore.Signal(Event)

    signal_plot_ready: QtCore.Signal = QtCore.Signal(Event)



    def __init__(

        self,

        main_engine: MainEngine,

        event_engine: EventEngine,

    ) -> None:

        super().__init__()



        self.main_engine: MainEngine = main_engine

        self.event_engine: EventEngine = event_engine

        self.factor_engine: FactorResearchEngine = (

            main_engine.get_engine(APP_NAME)  # type: ignore[assignment]

        )



        self._init_ui()

        self._register_events()

        self._load_symbols_to_panel()



    # ------------------------------------------------------------------ #

    #  UI 构建

    # ------------------------------------------------------------------ #



    def _init_ui(self) -> None:

        self.setWindowTitle("因子研究工作台")

        self.resize(1400, 900)

        self._init_central()

        self._init_status_bar()



    def _init_central(self) -> None:

        central = QtWidgets.QWidget(self)

        self.setCentralWidget(central)



        main_layout = QtWidgets.QHBoxLayout(central)

        main_layout.setContentsMargins(4, 4, 4, 4)

        main_layout.setSpacing(4)



        self.left_panel = LeftPanel(self)

        self.left_panel.run_requested.connect(self._on_run_requested)

        self.left_panel.stop_requested.connect(self._on_stop_requested)

        main_layout.addWidget(self.left_panel)



        self.tab_widget = self._build_tab_widget()

        self.score_tab.score_ready.connect(self.report_tab.feed_score)

        main_layout.addWidget(self.tab_widget, stretch=1)



    def _build_tab_widget(self) -> QtWidgets.QTabWidget:

        tab = QtWidgets.QTabWidget(self)



        self.overview_tab    = OverviewTab(self)

        self.ic_tab          = IcTab(self)

        self.ic_series_tab   = IcSeriesTab(self)

        self.ic_dist_tab     = IcDistributionTab(self)

        self.quantile_tab    = QuantileTab(self)

        self.longshort_tab   = LongShortTab(self)

        self.decay_tab       = DecayTab(self)

        self.correlation_tab = CorrelationTab(self)

        self.redundancy_tab  = RedundancyTab(self)

        self.score_tab       = ScoreTab(self)

        self.stability_tab   = StabilityTab(self)

        self.report_tab      = ReportTab(self)



        tabs: list[tuple[str, QtWidgets.QWidget]] = [

            ("因子概览",    self.overview_tab),

            ("IC 统计",    self.ic_tab),

            ("IC 时序",    self.ic_series_tab),

            ("IC 分布",    self.ic_dist_tab),

            ("分层收益",   self.quantile_tab),

            ("Long-Short", self.longshort_tab),

            ("IC Decay",   self.decay_tab),

            ("相关矩阵",   self.correlation_tab),

            ("冗余分析",   self.redundancy_tab),

            ("综合评分",   self.score_tab),

            ("因子稳定性", self.stability_tab),

            ("报告中心",   self.report_tab),

        ]

        for title, widget in tabs:

            tab.addTab(widget, title)



        return tab



    def _init_status_bar(self) -> None:

        self.status_bar = self.statusBar()

        self.status_bar.showMessage("就绪")



    # ------------------------------------------------------------------ #

    #  数据注入

    # ------------------------------------------------------------------ #



    def _load_symbols_to_panel(self) -> None:

        """从 DataEngine 取得数据库概览，注入到 LeftPanel 股票池列表。"""

        try:

            items = self.factor_engine.data_engine.get_overview()

            self.left_panel.load_symbols(items)

            self.status_bar.showMessage(f"数据库就绪：共 {len(items)} 条 K 线数据")

        except Exception as exc:

            self.status_bar.showMessage(f"数据库加载失败：{exc}")



    # ------------------------------------------------------------------ #

    #  LeftPanel 信号处理

    # ------------------------------------------------------------------ #



    def _on_run_requested(self, params: dict) -> None:

        """把配置参数转发给 Engine，不在 Widget 层做任何计算。"""

        ft = params.get("factor_type")

        name = params.get("factor_name") or (ft.value if ft else "unknown")

        self.status_bar.showMessage(f"正在运行：{name} ...")

        # 运行前清空所有已实现的 Tab

        self.overview_tab.clear()

        self.ic_tab.clear()

        self.ic_series_tab.clear()

        self.ic_dist_tab.clear()

        self.decay_tab.clear()

        self.quantile_tab.clear()

        self.longshort_tab.clear()

        self.score_tab.clear()

        self.report_tab.clear()

        self.stability_tab.clear()

        self.correlation_tab.clear()
        self.redundancy_tab.clear()
        self.factor_engine.run(params)



    def _on_stop_requested(self) -> None:

        self.status_bar.showMessage("正在停止…")

        self.factor_engine.stop()



    # ------------------------------------------------------------------ #

    #  事件注册

    # ------------------------------------------------------------------ #



    def _register_events(self) -> None:

        self.signal_log.connect(self._on_log)

        self.signal_progress.connect(self._on_progress)

        self.signal_finished.connect(self._on_finished)

        self.signal_error.connect(self._on_error)

        self.signal_plot_ready.connect(self._on_plot_ready)



        self.event_engine.register(EVENT_FACTOR_LOG,        self.signal_log.emit)

        self.event_engine.register(EVENT_FACTOR_PROGRESS,   self.signal_progress.emit)

        self.event_engine.register(EVENT_FACTOR_FINISHED,   self.signal_finished.emit)

        self.event_engine.register(EVENT_FACTOR_ERROR,      self.signal_error.emit)

        self.event_engine.register(EVENT_FACTOR_PLOT_READY, self.signal_plot_ready.emit)



    def _unregister_events(self) -> None:

        self.event_engine.unregister(EVENT_FACTOR_LOG,        self.signal_log.emit)

        self.event_engine.unregister(EVENT_FACTOR_PROGRESS,   self.signal_progress.emit)

        self.event_engine.unregister(EVENT_FACTOR_FINISHED,   self.signal_finished.emit)

        self.event_engine.unregister(EVENT_FACTOR_ERROR,      self.signal_error.emit)

        self.event_engine.unregister(EVENT_FACTOR_PLOT_READY, self.signal_plot_ready.emit)



    # ------------------------------------------------------------------ #

    #  事件槽

    # ------------------------------------------------------------------ #



    def _on_log(self, event: Event) -> None:

        self.status_bar.showMessage(str(event.data))



    def _on_progress(self, event: Event) -> None:

        if event.data is not None:

            self.status_bar.showMessage(str(event.data))



    def _on_finished(self, event: Event) -> None:

        self.status_bar.showMessage("计算完成")

        self.left_panel.set_idle()



    def _on_error(self, event: Event) -> None:

        self.status_bar.showMessage(f"[错误] {event.data}")

        self.left_panel.set_idle()



    def _on_plot_ready(self, event: Event) -> None:

        """

        按 event.data["tab"] 路由到对应 Tab 的 update_* 方法。

        后续每新增一个有数据的 Tab，在此处追加一个分支即可。

        """

        data: dict = event.data

        if not isinstance(data, dict):

            return



        tab_name = data.get("tab", "")

        payload  = data.get("payload")



        if payload is None:

            return



        if tab_name == "overview":

            self.overview_tab.update_summary(payload)

            self.report_tab.feed_overview(payload)

            self.tab_widget.setCurrentWidget(self.overview_tab)



        elif tab_name == "ic":

            self.ic_tab.update_stats(payload)

            self.score_tab.feed_ic(payload)

            self.report_tab.feed_ic(payload)



        elif tab_name == "ic_series":

            self.ic_series_tab.update_series(payload)

            self.ic_dist_tab.update_dist(payload)

            self.report_tab.feed_ic(payload)

            self.stability_tab.update_stability(payload)



        elif tab_name == "decay":

            self.decay_tab.update_decay(payload)

            self.report_tab.feed_decay(payload)



        elif tab_name == "quantile":

            self.quantile_tab.update_quantile(payload)

            self.longshort_tab.update_ls(payload)

            self.score_tab.feed_quantile(payload)

            self.report_tab.feed_quantile(payload)


        elif tab_name == "correlation":
            for ic_item in payload:
                self.correlation_tab.feed_ic(ic_item)
                self.redundancy_tab.feed_ic(ic_item)


    # ------------------------------------------------------------------ #

    #  窗口生命周期

    # ------------------------------------------------------------------ #



    def closeEvent(self, event: QtCore.QEvent) -> None:

        self._unregister_events()

        event.accept()

