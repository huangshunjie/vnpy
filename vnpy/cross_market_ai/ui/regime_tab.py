"""
cross_market_ai/ui/regime_tab.py

Phase 3: Regime Alignment Map — 市场状态对齐可视化面板。
"""
from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtWidgets, QtCore, QtGui

from ..constant import APP_NAME
from ..engine import CrossMarketEngine
from ..event import EVENT_REGIME_ALIGNED


class RegimeTab(QtWidgets.QWidget):
    """Regime 对齐面板。"""

    signal_aligned = QtCore.pyqtSignal(dict)

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
        root.addWidget(self._build_control_panel(), stretch=0)
        right = QtWidgets.QVBoxLayout()
        right.addWidget(self._build_metrics_panel(), stretch=0)
        right.addWidget(self._build_mapping_panel(), stretch=1)
        right.addWidget(self._build_history_table(), stretch=1)
        rw = QtWidgets.QWidget()
        rw.setLayout(right)
        root.addWidget(rw, stretch=1)

    def _build_control_panel(self) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        frame.setFixedWidth(240)
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        lbl = QtWidgets.QLabel("Regime Alignment Engine")
        lbl.setStyleSheet("font-weight:bold; color:#4fc3f7; font-size:12px;")
        layout.addWidget(lbl)
        layout.addWidget(_hline())

        layout.addWidget(QtWidgets.QLabel("市场 A（源）:"))
        self._combo_a = QtWidgets.QComboBox()
        self._combo_a.addItems([
            "equity_cn", "futures_cn", "equity_us", "crypto", "forex", "fixed_income"
        ])
        layout.addWidget(self._combo_a)

        layout.addWidget(QtWidgets.QLabel("市场 B（目标）:"))
        self._combo_b = QtWidgets.QComboBox()
        self._combo_b.addItems([
            "futures_cn", "equity_cn", "equity_us", "crypto", "forex", "fixed_income"
        ])
        layout.addWidget(self._combo_b)

        self._chk_force = QtWidgets.QCheckBox("强制刷新")
        layout.addWidget(self._chk_force)

        btn_align = QtWidgets.QPushButton("▶  执行对齐")
        btn_align.setStyleSheet("background:#1565c0; color:white; padding:4px;")
        btn_align.clicked.connect(self._on_align_single)
        layout.addWidget(btn_align)

        layout.addWidget(_hline())

        btn_batch = QtWidgets.QPushButton("▶▶  批量对齐全市场")
        btn_batch.setStyleSheet("background:#2e7d32; color:white; padding:4px;")
        btn_batch.clicked.connect(self._on_align_batch)
        layout.addWidget(btn_batch)

        layout.addWidget(_hline())

        self._stat_total = _stat_row("总对齐次数")
        self._stat_ok    = _stat_row("可对齐")
        self._stat_fail  = _stat_row("不可对齐")
        self._stat_avg   = _stat_row("平均对齐分")
        for w in [self._stat_total, self._stat_ok, self._stat_fail, self._stat_avg]:
            layout.addWidget(w)

        layout.addStretch()
        return frame

    def _build_metrics_panel(self) -> QtWidgets.QGroupBox:
        group  = QtWidgets.QGroupBox("Regime 对齐指标")
        layout = QtWidgets.QGridLayout(group)
        layout.setSpacing(8)

        self._lbl_overlap   = _metric_label("-")
        self._lbl_kl        = _metric_label("-")
        self._lbl_entropy_a = _metric_label("-")
        self._lbl_entropy_b = _metric_label("-")
        self._lbl_persist_a = _metric_label("-")
        self._lbl_persist_b = _metric_label("-")
        self._lbl_score     = _metric_label("-")
        self._lbl_alignable = _metric_label("-")

        layout.addWidget(QtWidgets.QLabel("分布重叠度:"),  0, 0)
        layout.addWidget(self._lbl_overlap,   0, 1)
        layout.addWidget(QtWidgets.QLabel("KL 散度:"),     0, 2)
        layout.addWidget(self._lbl_kl,        0, 3)
        layout.addWidget(QtWidgets.QLabel("熵(A):"),        1, 0)
        layout.addWidget(self._lbl_entropy_a, 1, 1)
        layout.addWidget(QtWidgets.QLabel("熵(B):"),        1, 2)
        layout.addWidget(self._lbl_entropy_b, 1, 3)
        layout.addWidget(QtWidgets.QLabel("留存率(A):"),    2, 0)
        layout.addWidget(self._lbl_persist_a, 2, 1)
        layout.addWidget(QtWidgets.QLabel("留存率(B):"),    2, 2)
        layout.addWidget(self._lbl_persist_b, 2, 3)
        layout.addWidget(QtWidgets.QLabel("对齐评分:"),     3, 0)
        layout.addWidget(self._lbl_score,     3, 1)
        layout.addWidget(QtWidgets.QLabel("可对齐:"),       3, 2)
        layout.addWidget(self._lbl_alignable, 3, 3)
        return group

    def _build_mapping_panel(self) -> QtWidgets.QGroupBox:
        group  = QtWidgets.QGroupBox("Regime 标签映射 A → B")
        layout = QtWidgets.QVBoxLayout(group)

        self._mapping_table = QtWidgets.QTableWidget(0, 3)
        self._mapping_table.setHorizontalHeaderLabels(
            ["市场A Regime", "→ 映射", "市场B Regime"]
        )
        self._mapping_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self._mapping_table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self._mapping_table.setMaximumHeight(150)
        layout.addWidget(self._mapping_table)

        self._lbl_unmatched = QtWidgets.QLabel("未匹配: —")
        self._lbl_unmatched.setStyleSheet("color:#888; font-size:10px;")
        layout.addWidget(self._lbl_unmatched)
        return group

    def _build_history_table(self) -> QtWidgets.QGroupBox:
        group  = QtWidgets.QGroupBox("对齐历史记录")
        layout = QtWidgets.QVBoxLayout(group)

        self._history_table = QtWidgets.QTableWidget(0, 7)
        self._history_table.setHorizontalHeaderLabels([
            "市场A", "市场B", "重叠度", "KL散度", "对齐评分", "可对齐", "时间",
        ])
        self._history_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self._history_table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self._history_table.setAlternatingRowColors(True)
        layout.addWidget(self._history_table)
        return group

    # ���� �¼�ע�� ������������������������������������������������������������������������������������������������������������

    def _register_events(self) -> None:
        self.signal_aligned.connect(self._on_aligned_event)
        self._event_engine.register(EVENT_REGIME_ALIGNED, self.signal_aligned.emit)

    # ���� �ۺ��� ����������������������������������������������������������������������������������������������������������������

    def _on_align_single(self) -> None:
        market_a = self._combo_a.currentText()
        market_b = self._combo_b.currentText()
        force    = self._chk_force.isChecked()
        result   = self._cm_engine.align_regime(market_a, market_b, force_refresh=force)
        if result.get("status") == "ok":
            rec = result["record"]
            self._update_metrics(rec)
            self._refresh_mapping(rec)
            self._append_history_row(rec)
            self._update_state_labels(result.get("state", {}))

    def _on_align_batch(self) -> None:
        markets = ["equity_cn", "futures_cn", "equity_us", "crypto", "forex", "fixed_income"]
        pairs   = [(markets[i], markets[j])
                   for i in range(len(markets)) for j in range(i + 1, len(markets))]
        result  = self._cm_engine.align_regime_batch(pairs)
        if result.get("status") == "ok":
            for rec in result.get("records", []):
                self._append_history_row(rec)
            self._update_state_labels(result.get("state", {}))

    def _on_aligned_event(self, data: dict) -> None:
        if data.get("status") == "ok" and data.get("record"):
            self._update_metrics(data["record"])

    # ���� ˢ���߼� ������������������������������������������������������������������������������������������������������������

    def _update_metrics(self, rec: dict) -> None:
        overlap   = rec.get("overlap_score",   0.0)
        kl        = rec.get("kl_divergence",   0.0)
        ent_a     = rec.get("entropy_a",       0.0)
        ent_b     = rec.get("entropy_b",       0.0)
        pers_a    = rec.get("persistence_a",   0.0)
        pers_b    = rec.get("persistence_b",   0.0)
        score     = rec.get("alignment_score", 0.0)
        alignable = rec.get("is_alignable",    False)

        self._lbl_overlap.setText(f"{overlap:.4f}")
        self._lbl_kl.setText(f"{kl:.4f}")
        self._lbl_entropy_a.setText(f"{ent_a:.4f}")
        self._lbl_entropy_b.setText(f"{ent_b:.4f}")
        self._lbl_persist_a.setText(f"{pers_a:.4f}")
        self._lbl_persist_b.setText(f"{pers_b:.4f}")
        self._lbl_score.setText(f"{score:.4f}")

        _apply_score_color(self._lbl_overlap, overlap)
        _apply_score_color(self._lbl_kl, max(0.0, 1.0 - kl))
        _apply_score_color(self._lbl_score, score)

        if alignable:
            self._lbl_alignable.setText("?  �ɶ���")
            self._lbl_alignable.setStyleSheet("font-size:13px; font-weight:bold; color:#4caf50;")
        else:
            self._lbl_alignable.setText("?  �ṹ�������")
            self._lbl_alignable.setStyleSheet("font-size:13px; font-weight:bold; color:#f44336;")

    def _refresh_mapping(self, rec: dict) -> None:
        mapping     = rec.get("aligned_regimes", {})
        unmatched_a = rec.get("unmatched_a", [])
        unmatched_b = rec.get("unmatched_b", [])
        self._mapping_table.setRowCount(0)
        for ra, rb in mapping.items():
            row = self._mapping_table.rowCount()
            self._mapping_table.insertRow(row)
            self._mapping_table.setItem(row, 0, _cell(ra, "#4fc3f7"))
            self._mapping_table.setItem(row, 1, _cell("��"))
            self._mapping_table.setItem(row, 2, _cell(rb, "#4fc3f7"))
        parts = []
        if unmatched_a:
            parts.append(f"Aδƥ��: {', '.join(unmatched_a)}")
        if unmatched_b:
            parts.append(f"Bδƥ��: {', '.join(unmatched_b)}")
        self._lbl_unmatched.setText("  ".join(parts) if parts else "ȫ��ƥ�� ?")

    def _append_history_row(self, rec: dict) -> None:
        row      = self._history_table.rowCount()
        self._history_table.insertRow(row)
        overlap  = rec.get("overlap_score",   0.0)
        kl       = rec.get("kl_divergence",   0.0)
        score    = rec.get("alignment_score", 0.0)
        alignable = rec.get("is_alignable",   False)

        self._history_table.setItem(row, 0, _cell(rec.get("market_a", "")))
        self._history_table.setItem(row, 1, _cell(rec.get("market_b", "")))
        ov_i = _cell(f"{overlap:.4f}")
        _apply_score_color_item(ov_i, overlap)
        self._history_table.setItem(row, 2, ov_i)
        kl_i = _cell(f"{kl:.4f}")
        _apply_score_color_item(kl_i, max(0.0, 1.0 - kl))
        self._history_table.setItem(row, 3, kl_i)
        sc_i = _cell(f"{score:.4f}")
        _apply_score_color_item(sc_i, score)
        self._history_table.setItem(row, 4, sc_i)
        ok_i = _cell("?" if alignable else "?")
        ok_i.setForeground(QtGui.QColor("#4caf50" if alignable else "#f44336"))
        self._history_table.setItem(row, 5, ok_i)
        self._history_table.setItem(row, 6, _cell(rec.get("aligned_at", "-")))
        self._history_table.scrollToBottom()

    def _update_state_labels(self, state: dict) -> None:
        self._stat_total.findChild(QtWidgets.QLabel, "val").setText(
            str(state.get("total_alignments", 0)))
        self._stat_ok.findChild(QtWidgets.QLabel, "val").setText(
            str(state.get("successful", 0)))
        self._stat_fail.findChild(QtWidgets.QLabel, "val").setText(
            str(state.get("failed", 0)))
        avg = state.get("avg_alignment", 0.0)
        self._stat_avg.findChild(QtWidgets.QLabel, "val").setText(f"{avg:.4f}")


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


def _cell(text: str, color: str = "") -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(text)
    item.setTextAlignment(QtCore.Qt.AlignCenter)
    if color:
        item.setForeground(QtGui.QColor(color))
    return item


def _apply_score_color(lbl: QtWidgets.QLabel, score: float) -> None:
    c = "#4caf50" if score >= 0.6 else "#ff9800" if score >= 0.35 else "#f44336"
    lbl.setStyleSheet(f"font-size:13px; font-weight:bold; color:{c};")


def _apply_score_color_item(item: QtWidgets.QTableWidgetItem, score: float) -> None:
    c = "#4caf50" if score >= 0.6 else "#ff9800" if score >= 0.35 else "#f44336"
    item.setForeground(QtGui.QColor(c))


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
