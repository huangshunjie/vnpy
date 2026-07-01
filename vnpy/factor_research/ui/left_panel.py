"""
factor_research/ui/left_panel.py

LeftPanel — 左侧配置区面板。

布局（从上到下）：
  ① 参数配置表单（因子类型/名称/频率/时间/标准化/中性化）
  ② 分隔线
  ③ 股票池区块（搜索框 + 多选列表 + 全选/清空按钮）
  ④ 分隔线
  ⑤ 运行 / 停止按钮

职责：
  - 收集用户参数并通过 run_requested Signal 传给 Widget
  - 通过 stop_requested Signal 通知 Widget 停止计算
  - 严禁直接调用 Engine 或数据库
  - 股票池数据由 Widget 通过 load_symbols() 注入

联动规则：
  - 点击"运行" → 运行禁用、停止启用
  - set_idle() → 恢复按钮状态
  - 搜索框实时过滤列表显示（不改变实际数据）
  - lag 改变 → max_lag 下限跟随，max_lag 上限由预估 bar 数约束
  - 日期 / 频率改变 → 实时更新预估 bar 数标签，并收紧 lag / max_lag 上限
"""

from __future__ import annotations

from datetime import datetime

from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import FactorType, FrequencyType, NormalizationMethod, NeutralizeMethod
from ..model import BarOverviewItem

# 每种频率每自然日产生的 bar 数（经验估算，仅用于 UI 提示）
_BARS_PER_DAY: dict[str, float] = {
    "daily":  252 / 365,
    "60min":  252 * 4 / 365,
    "15min":  252 * 16 / 365,
}
_DEFAULT_BARS_PER_DAY = 252 / 365

_LAG_MAX_RATIO     = 1 / 5   # lag 上限 = bars * 1/5
_MAX_LAG_MAX_RATIO = 1 / 3   # max_lag 上限 = bars * 1/3
_MAX_LAG_SCALE     = 4       # lag 增大时 max_lag 自动提升到 lag * 4


class LeftPanel(QtWidgets.QWidget):
    """左侧配置区面板。"""

    run_requested:  QtCore.Signal = QtCore.Signal(dict)
    stop_requested: QtCore.Signal = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._all_items: list[BarOverviewItem] = []
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        self.setFixedWidth(260)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(0)
        outer.addWidget(self._build_form())
        outer.addSpacing(10)
        outer.addWidget(self._build_separator())
        outer.addSpacing(10)
        outer.addWidget(self._build_symbol_pool())
        outer.addSpacing(10)
        outer.addWidget(self._build_separator())
        outer.addSpacing(10)
        outer.addWidget(self._build_buttons())
        outer.addStretch()

    def _build_form(self) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget(self)
        form = QtWidgets.QFormLayout(container)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.combo_factor_type = QtWidgets.QComboBox()
        for ft in FactorType:
            self.combo_factor_type.addItem(ft.value, ft)
        form.addRow("因子类型", self.combo_factor_type)

        self.edit_factor_name = QtWidgets.QLineEdit()
        self.edit_factor_name.setPlaceholderText("如 momentum_20")
        form.addRow("因子名称", self.edit_factor_name)

        self.combo_frequency = QtWidgets.QComboBox()
        for freq in FrequencyType:
            self.combo_frequency.addItem(freq.value, freq)
        form.addRow("数据频率", self.combo_frequency)

        self.date_start = QtWidgets.QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_start.setDate(QtCore.QDate(datetime.now().year - 3, 1, 1))
        form.addRow("开始日期", self.date_start)

        self.date_end = QtWidgets.QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.setDate(QtCore.QDate.currentDate())
        form.addRow("结束日期", self.date_end)

        self.lbl_bar_est = QtWidgets.QLabel()
        self.lbl_bar_est.setStyleSheet("color: gray; font-size: 11px;")
        self.lbl_bar_est.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        form.addRow("", self.lbl_bar_est)

        self.combo_norm = QtWidgets.QComboBox()
        for nm in NormalizationMethod:
            self.combo_norm.addItem(nm.value, nm)
        form.addRow("标准化", self.combo_norm)

        self.combo_neutral = QtWidgets.QComboBox()
        self.combo_neutral.addItem("（不中性化）", None)
        for nm in NeutralizeMethod:
            self.combo_neutral.addItem(nm.value, nm)
        form.addRow("中性化", self.combo_neutral)

        form.addRow(self._build_separator())

        self.spin_lag = QtWidgets.QSpinBox()
        self.spin_lag.setRange(1, 60)
        self.spin_lag.setValue(5)
        self.spin_lag.setSuffix(" 天")
        self.spin_lag.setToolTip("IC 计算与分层收益的持有期（天）")
        form.addRow("持有期 lag", self.spin_lag)

        self.spin_n_quantiles = QtWidgets.QSpinBox()
        self.spin_n_quantiles.setRange(2, 10)
        self.spin_n_quantiles.setValue(5)
        self.spin_n_quantiles.setSuffix(" 档")
        self.spin_n_quantiles.setToolTip("分层收益的分档数（Q1～Qn）")
        form.addRow("分层档数", self.spin_n_quantiles)

        self.spin_max_lag = QtWidgets.QSpinBox()
        self.spin_max_lag.setRange(5, 60)
        self.spin_max_lag.setValue(20)
        self.spin_max_lag.setSuffix(" 天")
        self.spin_max_lag.setToolTip("IC Decay 图的最大持有期（不能小于持有期 lag）")
        form.addRow("Decay max_lag", self.spin_max_lag)

        self.spin_lag.valueChanged.connect(self._on_lag_changed)
        self.date_start.dateChanged.connect(self._on_date_changed)
        self.date_end.dateChanged.connect(self._on_date_changed)
        self.combo_frequency.currentIndexChanged.connect(self._on_date_changed)

        self._on_date_changed()
        return container

    def _build_symbol_pool(self) -> "QtWidgets.QWidget":
        container = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title_row = QtWidgets.QHBoxLayout()
        pool_label = QtWidgets.QLabel("股票池")
        pool_label.setStyleSheet("font-weight: bold;")
        self.lbl_selected = QtWidgets.QLabel("（0 / 0）")
        self.lbl_selected.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        title_row.addWidget(pool_label)
        title_row.addStretch()
        title_row.addWidget(self.lbl_selected)
        layout.addLayout(title_row)

        self.edit_search = QtWidgets.QLineEdit()
        self.edit_search.setPlaceholderText("搜索合约代码…")
        self.edit_search.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.edit_search)

        self.list_symbols = QtWidgets.QListWidget()
        self.list_symbols.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.MultiSelection
        )
        self.list_symbols.setFixedHeight(180)
        self.list_symbols.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_symbols)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(4)
        btn_all = QtWidgets.QPushButton("全选")
        btn_all.setFixedHeight(24)
        btn_all.clicked.connect(self._select_all)
        btn_clear = QtWidgets.QPushButton("清空")
        btn_clear.setFixedHeight(24)
        btn_clear.clicked.connect(self._clear_selection)
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_clear)
        layout.addLayout(btn_row)
        return container

    def _build_separator(self) -> "QtWidgets.QFrame":
        line = QtWidgets.QFrame(self)
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        return line

    def _build_buttons(self) -> "QtWidgets.QWidget":
        container = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.btn_run = QtWidgets.QPushButton("运行")
        self.btn_run.setFixedHeight(32)
        self.btn_run.clicked.connect(self._on_run_clicked)
        self.btn_stop = QtWidgets.QPushButton("停止")
        self.btn_stop.setFixedHeight(32)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self.btn_run)
        layout.addWidget(self.btn_stop)
        return container

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def load_symbols(self, items: "list[BarOverviewItem]") -> None:
        self._all_items = items
        self._populate_list(items)

    def set_idle(self) -> None:
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)

    # ------------------------------------------------------------------ #
    #  联动逻辑
    # ------------------------------------------------------------------ #

    def _estimate_bars(self) -> int:
        start = self.date_start.date().toPython()
        end   = self.date_end.date().toPython()
        if end <= start:
            return 0
        days = (end - start).days
        freq_obj = self.combo_frequency.currentData()
        freq_key = freq_obj.value if freq_obj is not None else "daily"
        rate = _BARS_PER_DAY.get(freq_key, _DEFAULT_BARS_PER_DAY)
        return max(1, int(days * rate))

    def _on_date_changed(self) -> None:
        bars  = self._estimate_bars()
        start = self.date_start.date().toPython()
        end   = self.date_end.date().toPython()
        days  = max(0, (end - start).days)

        if days <= 0:
            self.lbl_bar_est.setText("（日期范围无效）")
            self.lbl_bar_est.setStyleSheet("color: #c0392b; font-size: 11px;")
            return

        years = days / 365
        self.lbl_bar_est.setText(f"约 {bars} bars（{years:.1f} 年）")
        self.lbl_bar_est.setStyleSheet("color: gray; font-size: 11px;")

        # tighten lag upper bound: at most 1/5 of available bars
        lag_max = max(1, int(bars * _LAG_MAX_RATIO))
        cur_lag = self.spin_lag.value()
        self.spin_lag.blockSignals(True)
        self.spin_lag.setMaximum(lag_max)
        if cur_lag > lag_max:
            self.spin_lag.setValue(lag_max)
        self.spin_lag.blockSignals(False)

        # tighten max_lag upper bound: at most 1/3 of available bars
        max_lag_ceiling = max(self.spin_lag.value(), int(bars * _MAX_LAG_MAX_RATIO))
        self.spin_max_lag.setMaximum(max_lag_ceiling)
        if self.spin_max_lag.value() > max_lag_ceiling:
            self.spin_max_lag.setValue(max_lag_ceiling)

        self._on_lag_changed(self.spin_lag.value())

    def _on_lag_changed(self, new_lag: int) -> None:
        self.spin_max_lag.setMinimum(new_lag)
        if self.spin_max_lag.value() < new_lag:
            target = min(new_lag * _MAX_LAG_SCALE, self.spin_max_lag.maximum())
            self.spin_max_lag.setValue(target)
        self.spin_lag.setToolTip(
            f"IC 计算与分层收益的持有期（天）\n当前可用上限：{self.spin_lag.maximum()} 天"
        )
        self.spin_max_lag.setToolTip(
            f"IC Decay 图的最大持有期\n"
            f"下限 = lag（{new_lag} 天），上限 = {self.spin_max_lag.maximum()} 天"
        )

    # ------------------------------------------------------------------ #
    #  列表操作
    # ------------------------------------------------------------------ #

    def _populate_list(self, items: "list[BarOverviewItem]") -> None:
        self.list_symbols.clear()
        for ov in items:
            start_str = str(ov.start) if ov.start else "?"
            end_str   = str(ov.end)   if ov.end   else "?"
            label = f"{ov.vt_symbol}  [{start_str} ~ {end_str}]"
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, ov.vt_symbol)
            self.list_symbols.addItem(item)
        self._update_selected_label()

    def _on_search_changed(self, text: str) -> None:
        keyword = text.strip().lower()
        filtered = self._all_items if not keyword else [
            ov for ov in self._all_items if keyword in ov.vt_symbol.lower()
        ]
        self._populate_list(filtered)

    def _select_all(self) -> None:
        self.list_symbols.selectAll()

    def _clear_selection(self) -> None:
        self.list_symbols.clearSelection()

    def _on_selection_changed(self) -> None:
        self._update_selected_label()

    def _update_selected_label(self) -> None:
        selected = len(self.list_symbols.selectedItems())
        total    = self.list_symbols.count()
        self.lbl_selected.setText(f"（{selected} / {total}）")

    def _get_selected_symbols(self) -> "list[str]":
        return [
            item.data(QtCore.Qt.ItemDataRole.UserRole)
            for item in self.list_symbols.selectedItems()
        ]

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _on_run_clicked(self) -> None:
        if not self._validate():
            return
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.run_requested.emit(self._collect_params())

    def _on_stop_clicked(self) -> None:
        self.stop_requested.emit()

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    def _validate(self) -> bool:
        if self.date_start.date() >= self.date_end.date():
            QtWidgets.QMessageBox.warning(self, "参数错误", "开始日期必须早于结束日期。")
            return False
        if self.spin_max_lag.value() < self.spin_lag.value():
            QtWidgets.QMessageBox.warning(
                self, "参数错误",
                f"Decay max_lag（{self.spin_max_lag.value()}）"
                f"不能小于持有期 lag（{self.spin_lag.value()}）。",
            )
            return False
        if not self._get_selected_symbols():
            QtWidgets.QMessageBox.warning(self, "参数错误", "请在股票池中至少选择一个合约。")
            return False
        return True

    def _collect_params(self) -> dict:
        return {
            "factor_type":    self.combo_factor_type.currentData(),
            "factor_name":    self.edit_factor_name.text().strip(),
            "frequency":      self.combo_frequency.currentData(),
            "start":          self.date_start.date().toPython(),
            "end":            self.date_end.date().toPython(),
            "normalization":  self.combo_norm.currentData(),
            "neutralization": self.combo_neutral.currentData(),
            "symbols":        self._get_selected_symbols(),
            "lag":            self.spin_lag.value(),
            "n_quantiles":    self.spin_n_quantiles.value(),
            "max_lag":        self.spin_max_lag.value(),
        }
