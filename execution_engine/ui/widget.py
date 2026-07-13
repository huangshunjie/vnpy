"""
execution_engine/ui/widget.py

ExecutionWidget — 交易执行系统主窗口（Phase 2 实现）。

布局：
┌──────────────────────────────────────────────────────────┐
│  左侧配置区（220px）  │  右侧 TabWidget（stretch）         │
│  - 手动下单表单       │  Order View                       │
│  - 启动/停止按钮      │  Execution Monitor                │
│                      │  Slippage Model                   │
│                      │  Cost Analysis                    │
│                      │  Report                           │
├──────────────────────┴───────────────────────────────────┤
│  底部日志栏                                               │
└──────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import APP_NAME
from ..event import (
    EVENT_EXECUTION_LOG,
    EVENT_ORDER_UPDATE,
    EVENT_FILL_UPDATE,
    EVENT_EXECUTION_ERROR,
    EVENT_EXECUTION_DONE,
)
from ..model.order_model import Order
from ..model.fill_model import FillRecord
from .order_tab import OrderTab
from .execution_tab import ExecutionTab
from .slippage_tab import SlippageTab
from .cost_tab import CostTab
from .report_tab import ReportTab

_INPUT_STYLE = (
    "QLineEdit, QDoubleSpinBox, QComboBox {"
    " background: #313244; color: #cdd6f4; border: 1px solid #45475a;"
    " border-radius: 3px; padding: 2px 6px; font-size: 12px; }"
)


class ExecutionWidget(QtWidgets.QWidget):
    """交易执行系统主窗口（Phase 2 实现）。"""

    _signal_log   = QtCore.Signal(Event)
    _signal_order = QtCore.Signal(Event)
    _signal_fill  = QtCore.Signal(Event)
    _signal_error = QtCore.Signal(Event)
    _signal_done  = QtCore.Signal(Event)

    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__()
        self.main_engine  = main_engine
        self.event_engine = event_engine

        self.setWindowTitle("交易执行系统")
        self.resize(1280, 800)

        self._init_ui()
        self._register_events()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        root.addWidget(self._build_left_panel())

        right = QtWidgets.QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(4)
        right.addWidget(self._build_tab_widget())
        right.addWidget(self._build_log_bar())
        root.addLayout(right, stretch=1)

    def _build_left_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(220)
        panel.setStyleSheet("background: #181825; border-radius: 4px;")

        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(8, 10, 8, 10)
        v.setSpacing(8)

        # 标题
        title = QtWidgets.QLabel("手动下单")
        title.setStyleSheet(
            "color: #cdd6f4; font-size: 13px; font-weight: bold;"
        )
        v.addWidget(title)

        # 下单表单
        form = QtWidgets.QFormLayout()
        form.setSpacing(6)
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        lbl_style = "color: #a6adc8; font-size: 11px;"

        self._edt_symbol = QtWidgets.QLineEdit()
        self._edt_symbol.setPlaceholderText("如 rb2501.SHFE")
        self._edt_symbol.setStyleSheet(_INPUT_STYLE)
        lbl = QtWidgets.QLabel("合约：")
        lbl.setStyleSheet(lbl_style)
        form.addRow(lbl, self._edt_symbol)

        self._cmb_direction = QtWidgets.QComboBox()
        self._cmb_direction.addItems(["LONG（做多）", "SHORT（做空）"])
        self._cmb_direction.setStyleSheet(_INPUT_STYLE)
        lbl2 = QtWidgets.QLabel("方向：")
        lbl2.setStyleSheet(lbl_style)
        form.addRow(lbl2, self._cmb_direction)

        self._spn_volume = QtWidgets.QDoubleSpinBox()
        self._spn_volume.setRange(0.01, 9999.0)
        self._spn_volume.setValue(1.0)
        self._spn_volume.setDecimals(2)
        self._spn_volume.setStyleSheet(_INPUT_STYLE)
        lbl3 = QtWidgets.QLabel("数量：")
        lbl3.setStyleSheet(lbl_style)
        form.addRow(lbl3, self._spn_volume)

        self._spn_signal_price = QtWidgets.QDoubleSpinBox()
        self._spn_signal_price.setRange(0.0001, 999999.0)
        self._spn_signal_price.setValue(100.0)
        self._spn_signal_price.setDecimals(4)
        self._spn_signal_price.setStyleSheet(_INPUT_STYLE)
        lbl4 = QtWidgets.QLabel("信号价：")
        lbl4.setStyleSheet(lbl_style)
        form.addRow(lbl4, self._spn_signal_price)

        self._cmb_order_type = QtWidgets.QComboBox()
        self._cmb_order_type.addItems(["MARKET", "LIMIT"])
        self._cmb_order_type.setStyleSheet(_INPUT_STYLE)
        lbl5 = QtWidgets.QLabel("订单类型：")
        lbl5.setStyleSheet(lbl_style)
        form.addRow(lbl5, self._cmb_order_type)

        v.addLayout(form)

        # 下单按钮
        btn_send = QtWidgets.QPushButton("发送订单")
        btn_send.setStyleSheet(
            "QPushButton { background: #89b4fa; color: #1e1e2e; border-radius: 4px;"
            " padding: 7px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background: #b4befe; }"
        )
        btn_send.clicked.connect(self._on_send_order)
        v.addWidget(btn_send)

        # 分隔线
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet("color: #45475a;")
        v.addWidget(sep)

        # 引擎控制
        ctrl_lbl = QtWidgets.QLabel("引擎控制")
        ctrl_lbl.setStyleSheet(
            "color: #cdd6f4; font-size: 13px; font-weight: bold;"
        )
        v.addWidget(ctrl_lbl)

        self._btn_start = QtWidgets.QPushButton("启动引擎")
        self._btn_start.setStyleSheet(
            "QPushButton { background: #a6e3a1; color: #1e1e2e; border-radius: 4px;"
            " padding: 6px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background: #cba6f7; }"
        )
        self._btn_start.clicked.connect(self._on_start)
        v.addWidget(self._btn_start)

        self._btn_stop = QtWidgets.QPushButton("停止引擎")
        self._btn_stop.setStyleSheet(
            "QPushButton { background: #313244; color: #f38ba8; border-radius: 4px;"
            " padding: 6px; font-size: 12px; }"
            "QPushButton:hover { background: #45475a; }"
        )
        self._btn_stop.clicked.connect(self._on_stop)
        v.addWidget(self._btn_stop)

        v.addStretch()

        # 底部状态指示
        self._lbl_status = QtWidgets.QLabel("● 未启动")
        self._lbl_status.setStyleSheet("color: #6c7086; font-size: 11px;")
        self._lbl_status.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self._lbl_status)

        # 上游信号监控区（Phase 4）
        v.addWidget(self._build_signal_monitor())

        return panel

    def _build_signal_monitor(self) -> QtWidgets.QWidget:
        """上游信号计数卡片（Phase 4）。"""
        w = QtWidgets.QWidget()
        w.setStyleSheet("background: #11111b; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(6, 4, 6, 4)
        v.setSpacing(3)
        ttl = QtWidgets.QLabel("上游信号")
        ttl.setStyleSheet("color: #6c7086; font-size: 10px;")
        v.addWidget(ttl)
        self._lbl_sig_portfolio = self._sig_lbl("Portfolio", "0")
        self._lbl_sig_cta       = self._sig_lbl("CTA",       "0")
        self._lbl_sig_factor    = self._sig_lbl("Factor",    "0")
        self._lbl_sig_done      = self._sig_lbl("已完成批次", "0")
        for lbl in (self._lbl_sig_portfolio, self._lbl_sig_cta,
                    self._lbl_sig_factor, self._lbl_sig_done):
            v.addWidget(lbl)
        self._sig_counts = {"portfolio": 0, "cta": 0, "factor": 0, "done": 0}
        return w

    @staticmethod
    def _sig_lbl(label: str, val: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(f"{label}: {val}")
        lbl.setStyleSheet("color: #cdd6f4; font-size: 11px;")
        return lbl

    def _update_sig_count(self, source: str) -> None:
        self._sig_counts[source] = self._sig_counts.get(source, 0) + 1
        n = self._sig_counts[source]
        lbl_map = {
            "portfolio": self._lbl_sig_portfolio,
            "cta":       self._lbl_sig_cta,
            "factor":    self._lbl_sig_factor,
            "done":      self._lbl_sig_done,
        }
        name_map = {
            "portfolio": "Portfolio",
            "cta":       "CTA",
            "factor":    "Factor",
            "done":      "已完成批次",
        }
        if source in lbl_map:
            lbl_map[source].setText(f"{name_map[source]}: {n}")

    def _build_tab_widget(self) -> QtWidgets.QTabWidget:
        tw = QtWidgets.QTabWidget()

        self.order_tab     = OrderTab(self)
        self.execution_tab = ExecutionTab(self)
        self.slippage_tab  = SlippageTab(self)
        self.cost_tab      = CostTab(self)
        self.report_tab    = ReportTab(self)

        # SlippageTab 配置变更 → 通知引擎
        self.slippage_tab.config_changed.connect(self._on_slippage_config_changed)
        self.cost_tab.config_changed.connect(self._on_cost_config_changed)

        tw.addTab(self.order_tab,     "Order View")
        tw.addTab(self.execution_tab, "Execution Monitor")
        tw.addTab(self.slippage_tab,  "Slippage Model")
        tw.addTab(self.cost_tab,      "Cost Analysis")
        tw.addTab(self.report_tab,    "Report")

        return tw

    def _build_log_bar(self) -> QtWidgets.QTextEdit:
        self.txt_log = QtWidgets.QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(80)
        self.txt_log.setStyleSheet(
            "background: #181825; color: #cdd6f4;"
            " font-size: 11px; font-family: monospace;"
        )
        return self.txt_log

    # ------------------------------------------------------------------ #
    #  事件注册
    # ------------------------------------------------------------------ #

    def _register_events(self) -> None:
        self._signal_log.connect(self._on_log)
        self._signal_order.connect(self._on_order_update)
        self._signal_fill.connect(self._on_fill_update)
        self._signal_error.connect(self._on_error)
        self._signal_done.connect(self._on_execution_done)

        reg = self.event_engine.register
        reg(EVENT_EXECUTION_LOG,   self._signal_log.emit)
        reg(EVENT_ORDER_UPDATE,    self._signal_order.emit)
        reg(EVENT_FILL_UPDATE,     self._signal_fill.emit)
        reg(EVENT_EXECUTION_ERROR, self._signal_error.emit)
        reg(EVENT_EXECUTION_DONE,  self._signal_done.emit)

    def _unregister_events(self) -> None:
        unreg = self.event_engine.unregister
        unreg(EVENT_EXECUTION_LOG,   self._signal_log.emit)
        unreg(EVENT_ORDER_UPDATE,    self._signal_order.emit)
        unreg(EVENT_FILL_UPDATE,     self._signal_fill.emit)
        unreg(EVENT_EXECUTION_ERROR, self._signal_error.emit)
        unreg(EVENT_EXECUTION_DONE,  self._signal_done.emit)

    # ------------------------------------------------------------------ #
    #  事件回调
    # ------------------------------------------------------------------ #

    def _on_log(self, event: Event) -> None:
        msg = event.data if isinstance(event.data, str) else str(event.data)
        self.txt_log.append(msg)
        sb = self.txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_order_update(self, event: Event) -> None:
        """接收 EVENT_ORDER_UPDATE → 刷新 OrderTab。"""
        order = event.data
        if isinstance(order, Order):
            self.order_tab.update_order(order)

    def _on_fill_update(self, event: Event) -> None:
        """接收 EVENT_FILL_UPDATE → 刷新 SlippageTab 滑点记录。"""
        fill = event.data
        if isinstance(fill, FillRecord):
            self.slippage_tab.add_slippage(fill.slippage_pct)

    def _on_error(self, event: Event) -> None:
        msg = event.data if isinstance(event.data, str) else str(event.data)
        self.txt_log.append(f"<span style='color:#f38ba8'>[ERROR] {msg}</span>")

    def _on_execution_done(self, event: Event) -> None:
        """接收 EVENT_EXECUTION_DONE，刷新信号计数和 Tab 数据。"""
        data = event.data if isinstance(event.data, dict) else {}
        self._update_sig_count("done")
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is None:
            return
        history  = engine.get_execution_history()
        stats    = engine.get_execution_stats()
        bds      = engine.get_cost_breakdowns()
        cost_sum = engine.get_cost_summary()
        self.execution_tab.update_stats(stats)
        self.execution_tab.refresh_all(history)
        self.order_tab.refresh_all(engine.get_all_orders())
        self.cost_tab.refresh_all(bds, cost_sum)
        self.report_tab.refresh_all(history, stats)
        n = data.get("batch_count", 0)
        f = data.get("filled_count", 0)
        self.txt_log.append(f"[DONE] 批量执行完成 {f}/{n} 笔成交")

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _on_start(self) -> None:
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is None:
            self.txt_log.append("[WARN] ExecutionEngine 未加载。")
            return
        engine.start()
        self._lbl_status.setText("● 运行中")
        self._lbl_status.setStyleSheet("color: #a6e3a1; font-size: 11px;")

    def _on_stop(self) -> None:
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is not None:
            engine.stop()
        self._lbl_status.setText("● 已停止")
        self._lbl_status.setStyleSheet("color: #f38ba8; font-size: 11px;")

    def _on_send_order(self) -> None:
        """读取左侧表单，向引擎发送手动订单。"""
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is None:
            self.txt_log.append("[WARN] ExecutionEngine 未加载。")
            return

        symbol = self._edt_symbol.text().strip()
        if not symbol:
            self.txt_log.append("[WARN] 请填写合约代码。")
            return

        direction = "LONG" if self._cmb_direction.currentIndex() == 0 else "SHORT"
        order_req = {
            "symbol":       symbol,
            "direction":    direction,
            "volume":       self._spn_volume.value(),
            "signal_price": self._spn_signal_price.value(),
            "order_type":   self._cmb_order_type.currentText(),
            "source":       "manual",
        }
        order_id = engine.send_order(order_req)
        if order_id:
            stats    = engine.get_execution_stats()
            history  = engine.get_execution_history()
            bds      = engine.get_cost_breakdowns()
            cost_sum = engine.get_cost_summary()
            # ExecutionTab
            self.execution_tab.update_stats(stats)
            self.execution_tab.refresh_all(history)
            # OrderTab
            self.order_tab.refresh_all(engine.get_all_orders())
            # CostTab
            self.cost_tab.refresh_all(bds, cost_sum)
            # ReportTab
            self.report_tab.refresh_all(history, stats)

    def _on_slippage_config_changed(
        self,
        slip_cfg,
        fill_cfg,
    ) -> None:
        """SlippageTab 应用按钮 → 更新引擎配置。"""
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is None:
            return
        engine.update_slippage_config(slip_cfg)
        engine.update_fill_config(fill_cfg)

    def _on_cost_config_changed(self, cost_cfg) -> None:
        """CostTab 应用按钮 → 更新引擎成本配置。"""
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is None:
            return
        engine.update_cost_config(cost_cfg)

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def closeEvent(self, event) -> None:
        self._unregister_events()
        super().closeEvent(event)
