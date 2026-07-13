"""
cross_market_ai/ui/validation_tab.py

Phase 5: Cross-Market Validation — 跨市场验证面板。
"""
from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtWidgets, QtCore, QtGui

from ..constant import APP_NAME
from ..engine import CrossMarketEngine
from ..event import EVENT_VALIDATION_COMPLETED

_VERDICT_COLORS = {
    "PASS":     "#4caf50",
    "DEGRADED": "#ff9800",
    "FAIL":     "#f44336",
}


class ValidationTab(QtWidgets.QWidget):
    """跨市场验证面板 — Phase 5。"""

    signal_validated = QtCore.pyqtSignal(dict)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._cm_engine: CrossMarketEngine = main_engine.get_engine(APP_NAME)
        self._init_ui()
        self._register_events()

    def _init_ui(self) -> None:
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)
        root.addWidget(self._build_control(), stretch=0)
        right = QtWidgets.QVBoxLayout()
        right.addWidget(self._build_verdict_card(),  stretch=0)
        right.addWidget(self._build_metrics_panel(), stretch=0)
        right.addWidget(self._build_compat_panel(),  stretch=0)
        right.addWidget(self._build_history_table(), stretch=1)
        rw = QtWidgets.QWidget()
        rw.setLayout(right)
        root.addWidget(rw, stretch=1)

    def _build_control(self) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        frame.setFixedWidth(240)
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        lbl = QtWidgets.QLabel("Cross-Market Validation")
        lbl.setStyleSheet("font-weight:bold; color:#4fc3f7; font-size:12px;")
        layout.addWidget(lbl)
        layout.addWidget(_hline())

        layout.addWidget(QtWidgets.QLabel("Alpha 类型:"))
        self._combo_alpha = QtWidgets.QComboBox()
        self._combo_alpha.addItems([
            "momentum", "mean_reversion", "value", "volatility", "carry"
        ])
        layout.addWidget(self._combo_alpha)

        layout.addWidget(QtWidgets.QLabel("训练市场:"))
        self._combo_train = QtWidgets.QComboBox()
        self._combo_train.addItems([
            "equity_cn", "futures_cn", "equity_us", "crypto", "forex", "fixed_income"
        ])
        layout.addWidget(self._combo_train)

        layout.addWidget(QtWidgets.QLabel("测试市场:"))
        self._combo_test = QtWidgets.QComboBox()
        self._combo_test.addItems([
            "futures_cn", "equity_cn", "equity_us", "crypto", "forex", "fixed_income"
        ])
        layout.addWidget(self._combo_test)

        self._chk_force = QtWidgets.QCheckBox("强制刷新")
        layout.addWidget(self._chk_force)

        btn_val = QtWidgets.QPushButton("▶  执行验证")
        btn_val.setStyleSheet("background:#1565c0; color:white; padding:4px;")
        btn_val.clicked.connect(self._on_validate_single)
        layout.addWidget(btn_val)

        layout.addWidget(_hline())

        layout.addWidget(QtWidgets.QLabel("批量验证 — Alpha:"))
        self._combo_batch_alpha = QtWidgets.QComboBox()
        self._combo_batch_alpha.addItems([
            "momentum", "mean_reversion", "value", "volatility", "carry"
        ])
        layout.addWidget(self._combo_batch_alpha)

        layout.addWidget(QtWidgets.QLabel("批量验证 — 训练市场:"))
        self._combo_batch_train = QtWidgets.QComboBox()
        self._combo_batch_train.addItems([
            "equity_cn", "futures_cn", "equity_us", "crypto", "forex", "fixed_income"
        ])
        layout.addWidget(self._combo_batch_train)

        btn_batch = QtWidgets.QPushButton("▶▶  批量验证所有市场")
        btn_batch.setStyleSheet("background:#2e7d32; color:white; padding:4px;")
        btn_batch.clicked.connect(self._on_validate_batch)
        layout.addWidget(btn_batch)

        btn_matrix = QtWidgets.QPushButton("⊞  全市场交叉验证")
        btn_matrix.setStyleSheet("background:#4a148c; color:white; padding:4px;")
        btn_matrix.clicked.connect(self._on_validate_matrix)
        layout.addWidget(btn_matrix)

        layout.addWidget(_hline())
        self._stat_total   = _stat_row("总验证次数")
        self._stat_pass    = _stat_row("PASS")
        self._stat_degrade = _stat_row("DEGRADED")
        self._stat_fail    = _stat_row("FAIL")
        self._stat_decay   = _stat_row("平均衰减率")
        for w in [self._stat_total, self._stat_pass, self._stat_degrade,
                  self._stat_fail, self._stat_decay]:
            layout.addWidget(w)
        layout.addStretch()
        return frame

    def _build_verdict_card(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("验证结论")
        layout = QtWidgets.QHBoxLayout(group)
        self._lbl_verdict = QtWidgets.QLabel("—")
        self._lbl_verdict.setStyleSheet(
            "font-size:36px; font-weight:bold; color:#888;")
        self._lbl_verdict.setAlignment(QtCore.Qt.AlignCenter)
        self._lbl_verdict.setFixedWidth(140)
        self._lbl_detail = QtWidgets.QLabel("—")
        self._lbl_detail.setWordWrap(True)
        self._lbl_detail.setStyleSheet("color:#ccc; font-size:11px; padding:8px;")
        layout.addWidget(self._lbl_verdict)
        layout.addWidget(self._lbl_detail, stretch=1)
        return group

    def _build_metrics_panel(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("性能衰减指标")
        layout = QtWidgets.QGridLayout(group)
        layout.setSpacing(8)
        self._lbl_sharpe_train = _metric_label("-")
        self._lbl_sharpe_test  = _metric_label("-")
        self._lbl_sharpe_decay = _metric_label("-")
        self._lbl_ic_train     = _metric_label("-")
        self._lbl_ic_test      = _metric_label("-")
        self._lbl_ic_decay     = _metric_label("-")
        self._lbl_dd_ratio     = _metric_label("-")
        self._lbl_composite    = _metric_label("-")
        self._lbl_pred_decay   = _metric_label("-")
        self._lbl_pred_err     = _metric_label("-")
        layout.addWidget(QtWidgets.QLabel("Sharpe(训练):"),  0, 0)
        layout.addWidget(self._lbl_sharpe_train,             0, 1)
        layout.addWidget(QtWidgets.QLabel("Sharpe(测试):"),  0, 2)
        layout.addWidget(self._lbl_sharpe_test,              0, 3)
        layout.addWidget(QtWidgets.QLabel("Sharpe衰减:"),    1, 0)
        layout.addWidget(self._lbl_sharpe_decay,             1, 1)
        layout.addWidget(QtWidgets.QLabel("IC衰减:"),         1, 2)
        layout.addWidget(self._lbl_ic_decay,                 1, 3)
        layout.addWidget(QtWidgets.QLabel("IC(训练):"),       2, 0)
        layout.addWidget(self._lbl_ic_train,                 2, 1)
        layout.addWidget(QtWidgets.QLabel("IC(测试):"),       2, 2)
        layout.addWidget(self._lbl_ic_test,                  2, 3)
        layout.addWidget(QtWidgets.QLabel("回撤比率:"),        3, 0)
        layout.addWidget(self._lbl_dd_ratio,                 3, 1)
        layout.addWidget(QtWidgets.QLabel("综合衰减率:"),      3, 2)
        layout.addWidget(self._lbl_composite,                3, 3)
        layout.addWidget(QtWidgets.QLabel("预测衰减:"),        4, 0)
        layout.addWidget(self._lbl_pred_decay,               4, 1)
        layout.addWidget(QtWidgets.QLabel("预测误差:"),        4, 2)
        layout.addWidget(self._lbl_pred_err,                 4, 3)
        return group

    def _build_compat_panel(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("结构兼容性（Phase 2/3 成果复用）")
        layout = QtWidgets.QGridLayout(group)
        layout.setSpacing(8)
        self._lbl_struct_sim   = _metric_label("-")
        self._lbl_regime_align = _metric_label("-")
        self._lbl_t_coeff      = _metric_label("-")
        self._lbl_portability  = _metric_label("-")
        self._lbl_compat       = _metric_label("-")
        layout.addWidget(QtWidgets.QLabel("结构相似度:"),   0, 0)
        layout.addWidget(self._lbl_struct_sim,              0, 1)
        layout.addWidget(QtWidgets.QLabel("Regime对齐:"),   0, 2)
        layout.addWidget(self._lbl_regime_align,            0, 3)
        layout.addWidget(QtWidgets.QLabel("迁移系数 T:"),    1, 0)
        layout.addWidget(self._lbl_t_coeff,                 1, 1)
        layout.addWidget(QtWidgets.QLabel("可迁移性先验:"),  1, 2)
        layout.addWidget(self._lbl_portability,             1, 3)
        layout.addWidget(QtWidgets.QLabel("综合兼容性:"),    2, 0)
        layout.addWidget(self._lbl_compat,                  2, 1)
        return group

    def _build_history_table(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("验证历史记录")
        layout = QtWidgets.QVBoxLayout(group)
        self._history_table = QtWidgets.QTableWidget(0, 9)
        self._history_table.setHorizontalHeaderLabels([
            "Alpha", "训练市场", "测试市场",
            "综合衰减", "预测衰减", "预测误差",
            "兼容性", "结论", "时间",
        ])
        self._history_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch)
        self._history_table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers)
        self._history_table.setAlternatingRowColors(True)
        layout.addWidget(self._history_table)
        return group

    # ���� �¼�ע�� ������������������������������������������������������������������������������������������������������������

    def _register_events(self) -> None:
        self.signal_validated.connect(self._on_validated_event)
        self._event_engine.register(EVENT_VALIDATION_COMPLETED, self.signal_validated.emit)

    # ���� �ۺ��� ����������������������������������������������������������������������������������������������������������������

    def _on_validate_single(self) -> None:
        alpha_id     = self._combo_alpha.currentText()
        market_train = self._combo_train.currentText()
        market_test  = self._combo_test.currentText()
        force        = self._chk_force.isChecked()
        result = self._cm_engine.validate_cross_market(
            alpha_id, market_train, market_test, force_refresh=force)
        if result.get("status") == "ok":
            self._refresh_from_record(result["record"])
            self._append_history_row(result["record"])
            self._update_state_labels(result.get("state", {}))

    def _on_validate_batch(self) -> None:
        alpha_id     = self._combo_batch_alpha.currentText()
        market_train = self._combo_batch_train.currentText()
        result = self._cm_engine.validate_batch(alpha_id, market_train)
        if result.get("status") == "ok":
            records = result.get("records", [])
            for rec in records:
                self._append_history_row(rec)
            if records:
                self._refresh_from_record(records[0])
            self._update_state_labels(result.get("state", {}))

    def _on_validate_matrix(self) -> None:
        alpha_id = self._combo_batch_alpha.currentText()
        markets  = ["equity_cn", "futures_cn", "equity_us",
                    "crypto", "forex", "fixed_income"]
        result = self._cm_engine.validate_matrix(alpha_id, markets)
        if result.get("status") == "ok":
            records = result.get("records", [])
            for rec in records:
                self._append_history_row(rec)
            if records:
                self._refresh_from_record(records[0])
            self._update_state_labels(result.get("state", {}))

    def _on_validated_event(self, data: dict) -> None:
        if data.get("status") == "ok" and data.get("record"):
            self._refresh_from_record(data["record"])

    # ���� ˢ���߼� ������������������������������������������������������������������������������������������������������������

    def _refresh_from_record(self, rec: dict) -> None:
        verdict = rec.get("verdict", "")
        detail  = rec.get("verdict_detail", "")
        color   = _VERDICT_COLORS.get(verdict, "#888")
        self._lbl_verdict.setText(verdict or "��")
        self._lbl_verdict.setStyleSheet(
            f"font-size:36px; font-weight:bold; color:{color};")
        self._lbl_detail.setText(detail)

        pt = rec.get("perf_train",   {})
        pe = rec.get("perf_test",    {})
        dg = rec.get("degradation",  {})
        cp = rec.get("compatibility",{})

        self._lbl_sharpe_train.setText(f"{pt.get('sharpe', 0.):.4f}")
        self._lbl_sharpe_test.setText( f"{pe.get('sharpe', 0.):.4f}")
        self._lbl_ic_train.setText(    f"{pt.get('ic_mean', 0.):.5f}")
        self._lbl_ic_test.setText(     f"{pe.get('ic_mean', 0.):.5f}")

        sharpe_d  = dg.get("sharpe_decay",    0.0)
        ic_d      = dg.get("ic_decay",        0.0)
        dd_r      = dg.get("drawdown_ratio",  1.0)
        composite = dg.get("composite_decay", 0.0)
        pred_d    = rec.get("predicted_decay",  0.0)
        pred_err  = rec.get("prediction_error", 0.0)

        for lbl, val in [
            (self._lbl_sharpe_decay, sharpe_d),
            (self._lbl_ic_decay,     ic_d),
            (self._lbl_composite,    composite),
            (self._lbl_pred_decay,   pred_d),
            (self._lbl_pred_err,     pred_err),
        ]:
            lbl.setText(f"{val:.4f}")
            eff = 1.0 - val
            c   = "#4caf50" if eff >= 0.6 else "#ff9800" if eff >= 0.35 else "#f44336"
            lbl.setStyleSheet(f"font-size:13px; font-weight:bold; color:{c};")

        self._lbl_dd_ratio.setText(f"{dd_r:.4f}")
        c = "#4caf50" if dd_r <= 1.3 else "#ff9800" if dd_r <= 2.0 else "#f44336"
        self._lbl_dd_ratio.setStyleSheet(f"font-size:13px; font-weight:bold; color:{c};")

        for lbl, val in [
            (self._lbl_struct_sim,   cp.get("structural_similarity",  0.0)),
            (self._lbl_regime_align, cp.get("regime_alignment_score", 0.0)),
            (self._lbl_t_coeff,      cp.get("transfer_coefficient",   0.0)),
            (self._lbl_portability,  cp.get("portability_prior",      0.0)),
            (self._lbl_compat,       cp.get("compatibility_score",    0.0)),
        ]:
            lbl.setText(f"{val:.4f}")
            c = "#4caf50" if val >= 0.6 else "#ff9800" if val >= 0.35 else "#f44336"
            lbl.setStyleSheet(f"font-size:13px; font-weight:bold; color:{c};")

    def _append_history_row(self, rec: dict) -> None:
        row     = self._history_table.rowCount()
        self._history_table.insertRow(row)
        verdict = rec.get("verdict", "")
        color   = _VERDICT_COLORS.get(verdict, "#888")
        decay   = rec.get("actual_decay",      0.0)
        pred_d  = rec.get("predicted_decay",   0.0)
        err     = rec.get("prediction_error",  0.0)
        compat  = rec.get("compatibility", {}).get("compatibility_score", 0.0)

        self._history_table.setItem(row, 0, _cell(rec.get("alpha_id",     "")))
        self._history_table.setItem(row, 1, _cell(rec.get("market_train", "")))
        self._history_table.setItem(row, 2, _cell(rec.get("market_test",  "")))

        d_i = _cell(f"{decay:.4f}")
        d_i.setForeground(QtGui.QColor(
            "#4caf50" if decay < 0.3 else "#ff9800" if decay < 0.5 else "#f44336"))
        self._history_table.setItem(row, 3, d_i)
        self._history_table.setItem(row, 4, _cell(f"{pred_d:.4f}"))
        self._history_table.setItem(row, 5, _cell(f"{err:.4f}"))

        c_i = _cell(f"{compat:.4f}")
        c_i.setForeground(QtGui.QColor(
            "#4caf50" if compat >= 0.6 else "#ff9800" if compat >= 0.35 else "#f44336"))
        self._history_table.setItem(row, 6, c_i)

        v_i = _cell(verdict)
        v_i.setForeground(QtGui.QColor(color))
        self._history_table.setItem(row, 7, v_i)
        self._history_table.setItem(row, 8, _cell(rec.get("validated_at", "-")))
        self._history_table.scrollToBottom()

    def _update_state_labels(self, state: dict) -> None:
        self._stat_total.findChild(  QtWidgets.QLabel, "val").setText(str(state.get("total_validations", 0)))
        self._stat_pass.findChild(   QtWidgets.QLabel, "val").setText(str(state.get("passed",   0)))
        self._stat_degrade.findChild(QtWidgets.QLabel, "val").setText(str(state.get("degraded", 0)))
        self._stat_fail.findChild(   QtWidgets.QLabel, "val").setText(str(state.get("failed",   0)))
        avg = state.get("avg_decay_rate", 0.0)
        self._stat_decay.findChild(  QtWidgets.QLabel, "val").setText(f"{avg:.4f}")


# ���� С���� ������������������������������������������������������������������������������������������������������������������������

def _hline() -> QtWidgets.QFrame:
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return line


def _metric_label(value: str) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(value)
    lbl.setStyleSheet("font-size:13px; font-weight:bold; color:#4fc3f7;")
    return lbl


def _cell(text: str) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(text)
    item.setTextAlignment(QtCore.Qt.AlignCenter)
    return item


def _stat_row(label: str) -> QtWidgets.QWidget:
    w = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 0)
    lbl = QtWidgets.QLabel(f"{label}:")
    lbl.setStyleSheet("color:#aaa; font-size:10px;")
    lbl.setFixedWidth(80)
    val = QtWidgets.QLabel("0")
    val.setObjectName("val")
    val.setStyleSheet("font-size:11px;")
    layout.addWidget(lbl)
    layout.addWidget(val)
    return w
