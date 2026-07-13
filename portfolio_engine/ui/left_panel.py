"""
portfolio_engine/ui/left_panel.py

LeftPanel — 左侧参数面板。

Phase 1：基础控件布局（可操作），但"运行"按钮不触发实际计算。
Phase 2：连接 engine.py，触发组合构建流程。

控件清单：
  - 组合名称输入框
  - 策略槽位列表（可增删，每行：名称 / 合约 / 类型）
  - 日期范围（开始 / 结束）
  - 权重方法下拉（等权 / 波动率目标 / 风险平价）
  - 调仓频率下拉（日 / 周 / 月 / 手动）
  - 基准合约输入框（可选）
  - [运行] [停止] 按钮
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import WeightMethod, RebalanceFreq, StrategyType

_WEIGHT_LABELS = {
    WeightMethod.EQUAL:             "等权（Equal Weight）",
    WeightMethod.VOLATILITY_TARGET: "波动率目标（Vol Target）",
    WeightMethod.RISK_PARITY:       "风险平价（Risk Parity）",
}

_REBAL_LABELS = {
    RebalanceFreq.DAILY:   "每日",
    RebalanceFreq.WEEKLY:  "每周",
    RebalanceFreq.MONTHLY: "每月",
    RebalanceFreq.MANUAL:  "手动",
}


class LeftPanel(QtWidgets.QWidget):
    """左侧参数面板（Phase 1：UI 可操作，不触发计算）。"""

    run_requested:  QtCore.Signal = QtCore.Signal(dict)   # Phase 2 接入
    stop_requested: QtCore.Signal = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(300)
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        root.addWidget(self._build_portfolio_section())
        root.addWidget(self._build_separator())
        root.addWidget(self._build_slot_section())
        root.addWidget(self._build_separator())
        root.addWidget(self._build_params_section())
        root.addWidget(self._build_separator())
        root.addWidget(self._build_buttons())
        root.addStretch()

    def _build_portfolio_section(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        self.edit_name = QtWidgets.QLineEdit("Portfolio_1")
        self.edit_benchmark = QtWidgets.QLineEdit()
        self.edit_benchmark.setPlaceholderText("如 000300.SSE（可留空）")

        layout.addRow("组合名称", self.edit_name)
        layout.addRow("基准合约", self.edit_benchmark)
        return w

    def _build_slot_section(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        hdr = QtWidgets.QLabel("策略槽位")
        hdr.setStyleSheet("font-weight: bold;")
        layout.addWidget(hdr)

        self.tbl_slots = QtWidgets.QTableWidget(0, 3)
        self.tbl_slots.setHorizontalHeaderLabels(["名称", "合约", "类型"])
        self.tbl_slots.setFixedHeight(140)
        self.tbl_slots.horizontalHeader().setStretchLastSection(True)
        self.tbl_slots.verticalHeader().setVisible(False)
        self.tbl_slots.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked
        )
        layout.addWidget(self.tbl_slots)

        btn_row = QtWidgets.QHBoxLayout()
        btn_add = QtWidgets.QPushButton("+ 添加")
        btn_add.setFixedHeight(24)
        btn_add.clicked.connect(self._add_slot_row)
        btn_del = QtWidgets.QPushButton("- 删除")
        btn_del.setFixedHeight(24)
        btn_del.clicked.connect(self._del_slot_row)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        layout.addLayout(btn_row)
        return w

    def _build_params_section(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        # 日期范围
        from vnpy.trader.ui import QtCore as _QC
        today = _QC.QDate.currentDate()
        self.date_start = QtWidgets.QDateEdit(today.addYears(-3))
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_end = QtWidgets.QDateEdit(today)
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")

        # 权重方法
        self.combo_weight = QtWidgets.QComboBox()
        for method, label in _WEIGHT_LABELS.items():
            self.combo_weight.addItem(label, method)

        # 调仓频率
        self.combo_rebal = QtWidgets.QComboBox()
        for freq, label in _REBAL_LABELS.items():
            self.combo_rebal.addItem(label, freq)
        self.combo_rebal.setCurrentIndex(2)  # default: monthly

        layout.addRow("开始日期", self.date_start)
        layout.addRow("结束日期", self.date_end)
        layout.addRow("权重方法", self.combo_weight)
        layout.addRow("调仓频率", self.combo_rebal)
        return w

    def _build_separator(self) -> QtWidgets.QFrame:
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        return line

    def _build_buttons(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.btn_run = QtWidgets.QPushButton("运行")
        self.btn_run.setFixedHeight(32)
        self.btn_run.clicked.connect(self._on_run_clicked)

        self.btn_stop = QtWidgets.QPushButton("停止")
        self.btn_stop.setFixedHeight(32)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_requested.emit)

        layout.addWidget(self.btn_run)
        layout.addWidget(self.btn_stop)
        return w

    # ------------------------------------------------------------------ #
    #  槽位操作
    # ------------------------------------------------------------------ #

    def _add_slot_row(self) -> None:
        row = self.tbl_slots.rowCount()
        self.tbl_slots.insertRow(row)
        self.tbl_slots.setItem(row, 0, QtWidgets.QTableWidgetItem(f"Slot_{row+1}"))
        self.tbl_slots.setItem(row, 1, QtWidgets.QTableWidgetItem(""))
        # type combo
        combo = QtWidgets.QComboBox()
        for st in StrategyType:
            combo.addItem(st.value, st)
        self.tbl_slots.setCellWidget(row, 2, combo)

    def _del_slot_row(self) -> None:
        row = self.tbl_slots.currentRow()
        if row >= 0:
            self.tbl_slots.removeRow(row)

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def set_idle(self) -> None:
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def collect_params(self) -> dict:
        """收集所有参数为 dict，供 Phase 2 engine.run() 使用。"""
        slots = []
        for row in range(self.tbl_slots.rowCount()):
            name_item = self.tbl_slots.item(row, 0)
            sym_item  = self.tbl_slots.item(row, 1)
            combo     = self.tbl_slots.cellWidget(row, 2)
            slots.append({
                "name":    name_item.text() if name_item else f"Slot_{row+1}",
                "symbol":  sym_item.text()  if sym_item  else "",
                "type":    combo.currentData() if combo else StrategyType.CUSTOM,
            })
        return {
            "portfolio_name":   self.edit_name.text().strip() or "Portfolio_1",
            "benchmark_symbol": self.edit_benchmark.text().strip(),
            "start":            self.date_start.date().toPython(),
            "end":              self.date_end.date().toPython(),
            "weight_method":    self.combo_weight.currentData(),
            "rebalance_freq":   self.combo_rebal.currentData(),
            "slots":            slots,
        }

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _on_run_clicked(self) -> None:
        params = self.collect_params()
        if not params["slots"]:
            QtWidgets.QMessageBox.warning(self, "参数错误", "请至少添加一个策略槽位。")
            return
        if self.date_start.date() >= self.date_end.date():
            QtWidgets.QMessageBox.warning(self, "参数错误", "开始日期必须早于结束日期。")
            return
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.run_requested.emit(params)
