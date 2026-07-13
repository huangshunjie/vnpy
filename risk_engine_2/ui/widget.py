"""
risk_engine_2/ui/widget.py

RiskEngineWidget — Risk Engine 2.0 主窗口（Phase 1 骨架）。

布局：
  左侧（固定宽度）: 风控配置面板（占位）+ 状态指示
  右侧（TabWidget）: 6 个 Tab 骨架（全部为空）

Phase 1：UI 结构完整，内容全部为占位符。
"""

from __future__ import annotations

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import APP_NAME
from ..event import (
    EVENT_RISK_UPDATE,
    EVENT_RISK_ALERT,
    EVENT_RISK_LIMIT,
    EVENT_RISK_DRAWDOWN,
    EVENT_RISK_LOG,
)
from .overview_tab  import OverviewTab
from .exposure_tab  import ExposureTab
from .drawdown_tab  import DrawdownTab
from .limit_tab     import LimitTab
from .alert_tab     import AlertTab
from .report_tab    import ReportTab

_DARK_BG  = "#1e1e2e"
_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_RED      = "#f38ba8"


class RiskEngineWidget(QtWidgets.QMainWindow):
    """
    Risk Engine 2.0 主窗口。

    Phase 1：骨架完整，所有 Tab 内容为空占位符。
    """

    _signal_log         = QtCore.Signal(Event)
    _signal_update      = QtCore.Signal(Event)
    _signal_alert       = QtCore.Signal(Event)
    _signal_limit       = QtCore.Signal(Event)
    _signal_drawdown    = QtCore.Signal(Event)
    _signal_attribution     = QtCore.Signal(Event)
    _signal_factor_exposure = QtCore.Signal(Event)
    _signal_style_drift     = QtCore.Signal(Event)
    _signal_status          = QtCore.Signal(Event)

    def __init__(
        self,
        main_engine:  MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__()
        self.main_engine  = main_engine
        self.event_engine = event_engine

        self._init_ui()
        self._register_events()

    # ------------------------------------------------------------------ #
    #  UI 初始化
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        self.setWindowTitle("Risk Engine 2.0 — 机构级风控系统")
        self.setMinimumSize(1200, 720)
        self.setStyleSheet(f"QMainWindow, QWidget {{ background: {_DARK_BG}; color: {_FG}; }}")

        # 中央容器
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # 左侧配置面板
        root.addWidget(self._build_left_panel(), stretch=0)

        # 右侧 TabWidget
        root.addWidget(self._build_tab_widget(), stretch=1)

    def _build_left_panel(self) -> QtWidgets.QWidget:
        """左侧：风控配置面板（Phase 1 占位）。"""
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(220)
        panel.setStyleSheet(
            f"QWidget {{ background: {_PANEL_BG}; border-radius: 4px; }}"
        )
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(8)

        # 标题
        title = QtWidgets.QLabel("Risk Engine 2.0")
        title.setStyleSheet(
            f"color: {_FG}; font-size: 13px; font-weight: bold;"
            f" border-bottom: 1px solid {_BORDER}; padding-bottom: 6px;"
        )
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        v.addWidget(title)

        # 状态指示
        self._lbl_status = QtWidgets.QLabel("● 未启动")
        self._lbl_status.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        self._lbl_status.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self._lbl_status)

        # 启动 / 停止按钮
        btn_row = QtWidgets.QHBoxLayout()
        self._btn_start = self._action_btn("启动", "#a6e3a1", "#1e1e2e")
        self._btn_stop  = self._action_btn("停止", "#f38ba8", "#1e1e2e")
        self._btn_start.clicked.connect(self._on_start)
        self._btn_stop.clicked.connect(self._on_stop)
        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_stop)
        v.addLayout(btn_row)

        # 配置占位框
        cfg_box = QtWidgets.QGroupBox("风控配置")
        cfg_box.setStyleSheet(
            f"QGroupBox {{ color: {_MUT}; font-size: 11px;"
            f" border: 1px solid {_BORDER}; border-radius: 4px; margin-top: 6px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; padding: 0 4px; }}"
        )
        cfg_layout = QtWidgets.QVBoxLayout(cfg_box)
        ph = QtWidgets.QLabel("Phase 2 实现")
        ph.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        ph.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        cfg_layout.addWidget(ph)
        v.addWidget(cfg_box)

        # 风险等级指示（占位）
        risk_box = QtWidgets.QGroupBox("当前风险等级")
        risk_box.setStyleSheet(cfg_box.styleSheet())
        risk_layout = QtWidgets.QVBoxLayout(risk_box)
        self._lbl_risk_level = QtWidgets.QLabel("—")
        self._lbl_risk_level.setStyleSheet(
            f"color: {_FG}; font-size: 16px; font-weight: bold;"
        )
        self._lbl_risk_level.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        risk_layout.addWidget(self._lbl_risk_level)
        v.addWidget(risk_box)

        v.addStretch()

        # 日志区
        self._txt_log = QtWidgets.QTextEdit()
        self._txt_log.setReadOnly(True)
        self._txt_log.setFixedHeight(160)
        self._txt_log.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_MUT};"
            f" font-size: 10px; border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt_log)

        return panel

    def _build_tab_widget(self) -> QtWidgets.QTabWidget:
        """右侧：6 个 Tab 骨架。"""
        tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane {{ border: 1px solid {_BORDER}; border-radius: 4px; }}"
            f"QTabBar::tab {{ background: {_PANEL_BG}; color: {_MUT};"
            f" padding: 6px 16px; border-radius: 3px; margin-right: 2px; }}"
            f"QTabBar::tab:selected {{ background: #313244; color: {_FG}; }}"
        )

        self.overview_tab  = OverviewTab(self)
        self.exposure_tab  = ExposureTab(self)
        self.drawdown_tab  = DrawdownTab(self)
        self.limit_tab     = LimitTab(self)
        self.alert_tab     = AlertTab(self)
        self.report_tab    = ReportTab(self)

        tabs.addTab(self.overview_tab,  "Overview（总览）")
        tabs.addTab(self.exposure_tab,  "Exposure（风险暴露）")
        tabs.addTab(self.drawdown_tab,  "Drawdown（回撤）")
        tabs.addTab(self.limit_tab,     "Limit Control（限制）")
        tabs.addTab(self.alert_tab,     "Alerts（预警）")
        tabs.addTab(self.report_tab,    "Report（报告）")

        return tabs

    # ------------------------------------------------------------------ #
    #  事件注册
    # ------------------------------------------------------------------ #

    def _register_events(self) -> None:
        self._signal_log.connect(self._on_log)
        self.limit_tab.limit_added.connect(self._on_limit_added)
        self.drawdown_tab.thresholds_changed.connect(self._on_thresholds_changed)
        self.alert_tab.acknowledge_requested.connect(self._on_ack_alert)
        self.alert_tab.ack_all_requested.connect(self._on_ack_all_alerts)
        self._signal_update.connect(self._on_risk_update)
        self._signal_alert.connect(self._on_risk_alert)
        self._signal_limit.connect(self._on_risk_limit)
        self._signal_drawdown.connect(self._on_risk_drawdown)
        self._signal_attribution.connect(self._on_attribution_result)
        self.report_tab.attribution_requested.connect(self._on_attribution_requested)
        self._signal_factor_exposure.connect(self._on_factor_exposure)
        self._signal_style_drift.connect(self._on_style_drift)
        self._signal_status.connect(self._on_risk_status)
        self.exposure_tab.drift_threshold_changed.connect(self._on_drift_threshold_changed)

        reg = self.event_engine.register
        reg(EVENT_RISK_LOG,             self._signal_log.emit)
        reg(EVENT_RISK_UPDATE,          self._signal_update.emit)
        reg(EVENT_RISK_ALERT,           self._signal_alert.emit)
        reg(EVENT_RISK_LIMIT,           self._signal_limit.emit)
        reg(EVENT_RISK_DRAWDOWN,        self._signal_drawdown.emit)
        reg('eAttributionResult',       self._signal_attribution.emit)
        reg('eRisk.factorExposure',     self._signal_factor_exposure.emit)
        reg('eRisk.styleDrift',         self._signal_style_drift.emit)
        reg('eRisk.status',             self._signal_status.emit)

    def _unregister_events(self) -> None:
        unreg = self.event_engine.unregister
        unreg(EVENT_RISK_LOG,      self._signal_log.emit)
        unreg(EVENT_RISK_UPDATE,   self._signal_update.emit)
        unreg(EVENT_RISK_ALERT,    self._signal_alert.emit)
        unreg(EVENT_RISK_LIMIT,    self._signal_limit.emit)
        unreg(EVENT_RISK_DRAWDOWN,        self._signal_drawdown.emit)
        unreg('eAttributionResult',       self._signal_attribution.emit)
        unreg('eRisk.factorExposure',     self._signal_factor_exposure.emit)
        unreg('eRisk.styleDrift',         self._signal_style_drift.emit)
        unreg('eRisk.status',             self._signal_status.emit)

    # ------------------------------------------------------------------ #
    #  事件回调（Phase 1：仅记录日志，不做逻辑处理）
    # ------------------------------------------------------------------ #

    def _on_log(self, event: Event) -> None:
        msg = event.data if isinstance(event.data, str) else str(event.data)
        self._txt_log.append(msg)
        sb = self._txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_risk_update(self, event: Event) -> None:
        """Phase 2: 刷新 OverviewTab + LimitTab。"""
        exposure = event.data
        if not hasattr(exposure, 'leverage'):
            return
        # OverviewTab
        self.overview_tab.update_exposure(exposure)
        # LimitTab：触发完整限制校验
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is not None:
            report = engine.get_last_limit_report()
            if report is not None:
                self.limit_tab.update_report(report)
        # 更新左侧风险等级指示
        from ..constant import RiskLevel
        lev = getattr(exposure, '_risk_level', None)
        lev_map = {
            RiskLevel.NORMAL:   ('NORMAL',   '#a6e3a1'),
            RiskLevel.WARNING:  ('WARNING',  '#f9e2af'),
            RiskLevel.CRITICAL: ('CRITICAL', '#fab387'),
            RiskLevel.BREACH:   ('BREACH',   '#f38ba8'),
        }
        lev_str, lev_color = lev_map.get(lev, ('—', '#cdd6f4'))
        self._lbl_risk_level.setText(lev_str)
        self._lbl_risk_level.setStyleSheet(
            f"color: {lev_color}; font-size: 16px; font-weight: bold;"
        )

    def _on_risk_alert(self, event: Event) -> None:
        """Phase 3: 预警推送到 AlertTab + 日志。"""
        data = event.data
        from ..model.drawdown_model import AlertRecord
        if isinstance(data, AlertRecord):
            self.alert_tab.add_alert(data)
            msg = data.message
        else:
            msg = str(data)
        self._txt_log.append(
            f"<span style='color:#f9e2af'>[ALERT] {msg}</span>"
        )

    def _on_risk_limit(self, event: Event) -> None:
        """Phase 2+: 限制触发，更新 LimitTab 状态。"""
        msg = event.data if isinstance(event.data, str) else str(event.data)
        self._txt_log.append(
            f"<span style='color:#f38ba8'>[LIMIT] {msg}</span>"
        )

    def _on_risk_drawdown(self, event: Event) -> None:
        """Phase 3: 回撤状态更新 → DrawdownTab。"""
        state = event.data
        if hasattr(state, 'current_drawdown_pct'):
            self.drawdown_tab.update_state(state)

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _on_start(self) -> None:
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is None:
            self._txt_log.append("[WARN] RiskEngine2 未加载，请检查 run.py。")
            return
        engine.start()
        self._lbl_status.setText("● 运行中")
        self._lbl_status.setStyleSheet(f"color: {_GRN}; font-size: 11px;")

    def _on_stop(self) -> None:
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is not None:
            engine.stop()
        self._lbl_status.setText("● 已停止")
        self._lbl_status.setStyleSheet(f"color: {_RED}; font-size: 11px;")

    def _on_limit_added(self, limit) -> None:
        """LimitTab 提交新规则 → 推送到引擎。"""
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is None:
            self._txt_log.append("[WARN] RiskEngine2 未加载。")
            return
        engine.add_limit(limit)
        self._txt_log.append(
            f"[LIMIT] 规则已添加：{limit.label}  hard={limit.hard_limit:.4f}  warn={limit.warning_threshold:.4f}"
        )

    def _on_thresholds_changed(
        self, dd_warn: float, dd_limit: float,
        dl_warn: float, dl_limit: float,
    ) -> None:
        """DrawdownTab 阈值变更 → 推送到引擎。"""
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is not None:
            engine.set_drawdown_thresholds(
                drawdown_warning  = dd_warn,
                drawdown_limit    = dd_limit,
                daily_loss_warn   = dl_warn,
                daily_loss_limit  = dl_limit,
            )
        self._txt_log.append(
            f'[THRESHOLD] 回撤预警={dd_warn:.1%}  限制={dd_limit:.1%}  '
            f'日亏损预警={dl_warn:.1%}  限制={dl_limit:.1%}'
        )

    def _on_ack_alert(self, alert_id: str) -> None:
        """AlertTab 双击确认单条预警。"""
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is not None:
            engine.acknowledge_alert(alert_id)
        self.alert_tab.mark_acknowledged(alert_id)

    def _on_ack_all_alerts(self) -> None:
        """AlertTab 全部确认按钮。"""
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is not None:
            for a in engine.get_alert_history():
                engine.acknowledge_alert(a.alert_id)
        history = engine.get_alert_history() if engine else []
        self.alert_tab.refresh_all(history)
        self._txt_log.append('[ALERT] 已全部确认。')

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def _on_attribution_result(self, event) -> None:
        """Phase 4: 归因结果 → ReportTab。"""
        result = event.data
        if hasattr(result, 'total_pnl'):
            self.report_tab.update_result(result)
            self._txt_log.append(
                f"<span style='color:#89b4fa'>[归因] "
                f"PnL={result.total_pnl:+.2f}  "
                f"Beta={result.portfolio_beta:.3f}  "
                f"MaxDD={result.max_drawdown_pct:.2%}</span>"
            )

    def _on_attribution_requested(self) -> None:
        """ReportTab 手动触发归因计算。"""
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is None:
            self._txt_log.append('[WARN] RiskEngine2 未加载。')
            return
        result = engine.compute_attribution()
        if result is not None:
            self.report_tab.update_result(result)
            self._txt_log.append(
                f'[归因] 手动触发完成  PnL={result.total_pnl:+.2f}'
            )
        else:
            self._txt_log.append('[归因] 暂无持仓数据，归因结果为空。')

    def _on_factor_exposure(self, event) -> None:
        """Phase 5: 因子暴露更新 → ExposureTab。"""
        data = event.data
        if not isinstance(data, dict):
            return
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is not None:
            self.exposure_tab.update_factor_exposures(engine.get_factor_exposures())

    def _on_style_drift(self, event) -> None:
        """Phase 5: 风格漂移预警 → ExposureTab + 日志。"""
        drift_info = event.data
        if isinstance(drift_info, dict):
            self.exposure_tab.add_drift_record(drift_info)
            msg = drift_info.get('message', str(drift_info))
            self._txt_log.append(
                f"<span style='color:#fab387'>[漂移] {msg}</span>"
            )

    def _on_risk_status(self, event) -> None:
        """Phase 5: 引擎状态变更 → 左侧状态指示。"""
        data = event.data
        if not isinstance(data, dict):
            return
        status  = data.get('status', '')
        message = data.get('message', '')
        color_map = {
            'running': ('#a6e3a1', '● 运行中'),
            'halted':  ('#f38ba8', '● 已暂停'),
            'warning': ('#f9e2af', '● 预警中'),
        }
        color, lbl = color_map.get(status, ('#6c7086', f'● {status}'))
        self._lbl_status.setText(lbl)
        self._lbl_status.setStyleSheet(f'color: {color}; font-size: 11px;')
        if message:
            self._txt_log.append(f'[STATUS] {message}')

    def _on_drift_threshold_changed(self, threshold: float) -> None:
        """ExposureTab 阈值变更 → 推送到引擎。"""
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is not None:
            engine.set_drift_threshold(threshold)
        self._txt_log.append(f'[Factor] 漂移阈值已更新：{threshold:.4f}')

    def closeEvent(self, event) -> None:
        self._unregister_events()
        super().closeEvent(event)

    # ------------------------------------------------------------------ #
    #  工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _action_btn(text: str, bg: str, fg: str) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(text)
        btn.setStyleSheet(
            f"QPushButton {{ background: {bg}; color: {fg}; border-radius: 4px;"
            f" padding: 5px; font-size: 12px; font-weight: bold; }}"
            f"QPushButton:hover {{ opacity: 0.85; }}"
        )
        return btn
