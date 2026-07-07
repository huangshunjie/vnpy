"""
cross_market_ai/ui/scoring_tab.py

Phase 4: Universality Scoring — 普适性评分面板。
"""
from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtWidgets, QtCore, QtGui

from ..constant import APP_NAME
from ..engine import CrossMarketEngine
from ..event import EVENT_UNIVERSALITY_SCORED


_GRADE_COLORS = {
    "UNIVERSAL": "#4caf50",
    "PORTABLE":  "#ff9800",
    "LOCAL":     "#ff5722",
    "FRAGILE":   "#f44336",
}


class ScoringTab(QtWidgets.QWidget):
    """普适性评分面板。"""

    signal_scored = QtCore.pyqtSignal(dict)

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
        right.addWidget(self._build_score_card(),   stretch=0)
        right.addWidget(self._build_dim_panel(),    stretch=0)
        right.addWidget(self._build_market_table(), stretch=1)
        right.addWidget(self._build_leaderboard(),  stretch=1)
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

        lbl = QtWidgets.QLabel("Universality Scoring Engine")
        lbl.setStyleSheet("font-weight:bold; color:#4fc3f7; font-size:12px;")
        layout.addWidget(lbl)
        layout.addWidget(_hline())

        layout.addWidget(QtWidgets.QLabel("Alpha 类型:"))
        self._combo_alpha = QtWidgets.QComboBox()
        self._combo_alpha.addItems([
            "momentum", "mean_reversion", "value", "volatility", "carry"
        ])
        layout.addWidget(self._combo_alpha)

        self._chk_force = QtWidgets.QCheckBox("强制刷新")
        layout.addWidget(self._chk_force)

        btn_score = QtWidgets.QPushButton("▶  计算普适性评分")
        btn_score.setStyleSheet("background:#1565c0; color:white; padding:4px;")
        btn_score.clicked.connect(self._on_score_single)
        layout.addWidget(btn_score)

        layout.addWidget(_hline())

        layout.addWidget(QtWidgets.QLabel("批量评分 — Alpha 列表:"))
        self._list_alphas = QtWidgets.QListWidget()
        self._list_alphas.addItems([
            "momentum", "mean_reversion", "value", "volatility", "carry"
        ])
        self._list_alphas.setSelectionMode(
            QtWidgets.QAbstractItemView.MultiSelection
        )
        self._list_alphas.setMaximumHeight(100)
        layout.addWidget(self._list_alphas)

        btn_batch = QtWidgets.QPushButton("▶▶  批量评分")
        btn_batch.setStyleSheet("background:#2e7d32; color:white; padding:4px;")
        btn_batch.clicked.connect(self._on_score_batch)
        layout.addWidget(btn_batch)

        layout.addWidget(_hline())

        btn_lb = QtWidgets.QPushButton("刷新排行榜")
        btn_lb.clicked.connect(self._on_refresh_leaderboard)
        layout.addWidget(btn_lb)

        layout.addWidget(_hline())

        self._stat_total     = _stat_row("已评分")
        self._stat_avg       = _stat_row("平均分")
        self._stat_top       = _stat_row("最高Alpha")
        self._stat_universal = _stat_row("UNIVERSAL")
        self._stat_portable  = _stat_row("PORTABLE")
        for w in [self._stat_total, self._stat_avg, self._stat_top,
                  self._stat_universal, self._stat_portable]:
            layout.addWidget(w)
        layout.addStretch()
        return frame

    def _build_score_card(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("普适性评分 & 等级")
        layout = QtWidgets.QHBoxLayout(group)

        self._lbl_score = QtWidgets.QLabel("—")
        self._lbl_score.setStyleSheet(
            "font-size:42px; font-weight:bold; color:#4fc3f7;"
        )
        self._lbl_score.setAlignment(QtCore.Qt.AlignCenter)
        self._lbl_score.setFixedWidth(120)

        self._lbl_grade = QtWidgets.QLabel("—")
        self._lbl_grade.setStyleSheet(
            "font-size:22px; font-weight:bold; color:#888;"
        )
        self._lbl_grade.setAlignment(QtCore.Qt.AlignCenter)
        self._lbl_grade.setFixedWidth(160)

        self._lbl_verdict = QtWidgets.QLabel("—")
        self._lbl_verdict.setWordWrap(True)
        self._lbl_verdict.setStyleSheet("color:#ccc; font-size:11px; padding:8px;")

        layout.addWidget(self._lbl_score)
        layout.addWidget(self._lbl_grade)
        layout.addWidget(self._lbl_verdict, stretch=1)
        return group

    def _build_dim_panel(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("四维评分分解")
        layout = QtWidgets.QGridLayout(group)
        layout.setSpacing(8)

        self._dim_cs = _DimBar("跨市场稳定性",  0.35)
        self._dim_rr = _DimBar("Regime 鲁棒性", 0.25)
        self._dim_si = _DimBar("结构不变性",    0.25)
        self._dim_ei = _DimBar("执行独立性",    0.15)

        layout.addWidget(self._dim_cs, 0, 0)
        layout.addWidget(self._dim_rr, 0, 1)
        layout.addWidget(self._dim_si, 1, 0)
        layout.addWidget(self._dim_ei, 1, 1)
        return group

    def _build_market_table(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("各市场性能切片")
        layout = QtWidgets.QVBoxLayout(group)
        self._market_table = QtWidgets.QTableWidget(0, 6)
        self._market_table.setHorizontalHeaderLabels([
            "市场", "T系数", "IC估计", "IC衰减", "对齐分", "可迁移",
        ])
        self._market_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self._market_table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self._market_table.setAlternatingRowColors(True)
        self._market_table.setMaximumHeight(180)
        layout.addWidget(self._market_table)
        return group

    def _build_leaderboard(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Alpha 普适性排行榜")
        layout = QtWidgets.QVBoxLayout(group)
        self._lb_table = QtWidgets.QTableWidget(0, 6)
        self._lb_table.setHorizontalHeaderLabels([
            "排名", "Alpha", "综合评分", "等级", "CS", "RR",
        ])
        self._lb_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self._lb_table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self._lb_table.setAlternatingRowColors(True)
        layout.addWidget(self._lb_table)
        return group

    # ���� �¼�ע�� ������������������������������������������������������������������������������������������������������������

    def _register_events(self) -> None:
        self.signal_scored.connect(self._on_scored_event)
        self._event_engine.register(EVENT_UNIVERSALITY_SCORED, self.signal_scored.emit)

    # ���� �ۺ��� ����������������������������������������������������������������������������������������������������������������

    def _on_score_single(self) -> None:
        alpha_id = self._combo_alpha.currentText()
        force    = self._chk_force.isChecked()
        result   = self._cm_engine.evaluate_universality(alpha_id, force_refresh=force)
        if result.get("status") == "ok":
            self._refresh_from_record(result["record"])
            self._update_state_labels(result.get("state", {}))

    def _on_score_batch(self) -> None:
        selected = [item.text() for item in self._list_alphas.selectedItems()]
        if not selected:
            selected = ["momentum", "mean_reversion", "value", "volatility", "carry"]
        result = self._cm_engine.evaluate_universality_batch(selected)
        if result.get("status") == "ok":
            records = result.get("records", [])
            if records:
                self._refresh_from_record(records[0])
            self._update_state_labels(result.get("state", {}))
            self._on_refresh_leaderboard()

    def _on_refresh_leaderboard(self) -> None:
        lb = self._cm_engine.get_universality_leaderboard(20)
        self._refresh_leaderboard(lb.get("leaderboard", []))

    def _on_scored_event(self, data: dict) -> None:
        if data.get("status") == "ok" and data.get("record"):
            self._refresh_from_record(data["record"])

    # ���� ˢ���߼� ������������������������������������������������������������������������������������������������������������

    def _refresh_from_record(self, rec: dict) -> None:
        score   = rec.get("score",   0.0)
        grade   = rec.get("grade",   "")
        verdict = rec.get("verdict", "")
        color   = _GRADE_COLORS.get(grade, "#888")

        self._lbl_score.setText(f"{score:.3f}")
        self._lbl_score.setStyleSheet(
            f"font-size:42px; font-weight:bold; color:{color};")
        self._lbl_grade.setText(grade)
        self._lbl_grade.setStyleSheet(
            f"font-size:22px; font-weight:bold; color:{color};")
        self._lbl_verdict.setText(verdict)

        for bar, key in [
            (self._dim_cs, "dim_cross_market"),
            (self._dim_rr, "dim_regime"),
            (self._dim_si, "dim_structural"),
            (self._dim_ei, "dim_execution"),
        ]:
            d = rec.get(key, {})
            bar.set_value(d.get("score", 0.0), d.get("evidence", ""))

        slices = rec.get("market_slices", [])
        self._market_table.setRowCount(0)
        for s in slices:
            row = self._market_table.rowCount()
            self._market_table.insertRow(row)
            tc   = s.get("transfer_coeff",  0.0)
            ic_e = s.get("ic_estimated",    0.0)
            ic_d = s.get("ic_decay",        0.0)
            al   = s.get("alignment_score", 0.0)
            ok   = s.get("is_transferable", False)

            self._market_table.setItem(row, 0, _cell(s.get("market_id", "")))
            tc_i = _cell(f"{tc:.4f}")
            tc_i.setForeground(QtGui.QColor(
                "#4caf50" if tc >= 0.6 else "#ff9800" if tc >= 0.35 else "#f44336"))
            self._market_table.setItem(row, 1, tc_i)
            self._market_table.setItem(row, 2, _cell(f"{ic_e:.5f}"))
            dc_i = _cell(f"{ic_d:.4f}")
            dc_i.setForeground(QtGui.QColor(
                "#4caf50" if ic_d < 0.3 else "#ff9800" if ic_d < 0.6 else "#f44336"))
            self._market_table.setItem(row, 3, dc_i)
            al_i = _cell(f"{al:.4f}")
            al_i.setForeground(QtGui.QColor(
                "#4caf50" if al >= 0.6 else "#ff9800" if al >= 0.35 else "#f44336"))
            self._market_table.setItem(row, 4, al_i)
            ok_i = _cell("?" if ok else "?")
            ok_i.setForeground(QtGui.QColor("#4caf50" if ok else "#f44336"))
            self._market_table.setItem(row, 5, ok_i)

    def _refresh_leaderboard(self, records: list[dict]) -> None:
        self._lb_table.setRowCount(0)
        for i, rec in enumerate(records):
            row   = self._lb_table.rowCount()
            self._lb_table.insertRow(row)
            score = rec.get("score", 0.0)
            grade = rec.get("grade", "")
            color = _GRADE_COLORS.get(grade, "#888")
            self._lb_table.setItem(row, 0, _cell(str(i + 1)))
            self._lb_table.setItem(row, 1, _cell(rec.get("alpha_id", "")))
            sc_i = _cell(f"{score:.4f}")
            sc_i.setForeground(QtGui.QColor(color))
            self._lb_table.setItem(row, 2, sc_i)
            gr_i = _cell(grade)
            gr_i.setForeground(QtGui.QColor(color))
            self._lb_table.setItem(row, 3, gr_i)
            cs = rec.get("dim_cross_market", {}).get("score", 0.0)
            rr = rec.get("dim_regime",       {}).get("score", 0.0)
            self._lb_table.setItem(row, 4, _cell(f"{cs:.4f}"))
            self._lb_table.setItem(row, 5, _cell(f"{rr:.4f}"))

    def _update_state_labels(self, state: dict) -> None:
        self._stat_total.findChild(QtWidgets.QLabel, "val").setText(
            str(state.get("total_scored", 0)))
        self._stat_avg.findChild(QtWidgets.QLabel, "val").setText(
            f"{state.get('avg_score', 0.0):.4f}")
        self._stat_top.findChild(QtWidgets.QLabel, "val").setText(
            str(state.get("top_alpha", "-")))
        self._stat_universal.findChild(QtWidgets.QLabel, "val").setText(
            str(state.get("universal_count", 0)))
        self._stat_portable.findChild(QtWidgets.QLabel, "val").setText(
            str(state.get("portable_count", 0)))


# ���� ά�Ƚ�������� ��������������������������������������������������������������������������������������������������������

class _DimBar(QtWidgets.QFrame):
    def __init__(self, label: str, weight: float) -> None:
        super().__init__()
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        top = QtWidgets.QHBoxLayout()
        self._lbl_name = QtWidgets.QLabel(label)
        self._lbl_name.setStyleSheet("font-size:11px; color:#aaa;")
        self._lbl_val = QtWidgets.QLabel("��")
        self._lbl_val.setStyleSheet("font-size:14px; font-weight:bold; color:#4fc3f7;")
        top.addWidget(self._lbl_name)
        top.addStretch()
        top.addWidget(self._lbl_val)
        layout.addLayout(top)

        self._bar = QtWidgets.QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        layout.addWidget(self._bar)

        self._lbl_ev = QtWidgets.QLabel("")
        self._lbl_ev.setStyleSheet("font-size:9px; color:#666;")
        self._lbl_ev.setWordWrap(True)
        layout.addWidget(self._lbl_ev)

        wt = QtWidgets.QLabel(f"Ȩ�� {int(weight * 100)}%")
        wt.setStyleSheet("font-size:9px; color:#555;")
        layout.addWidget(wt)

    def set_value(self, score: float, evidence: str = "") -> None:
        pct   = int(score * 100)
        color = "#4caf50" if score >= 0.6 else "#ff9800" if score >= 0.35 else "#f44336"
        self._lbl_val.setText(f"{score:.4f}")
        self._lbl_val.setStyleSheet(
            f"font-size:14px; font-weight:bold; color:{color};")
        self._bar.setValue(pct)
        self._bar.setStyleSheet(
            f"QProgressBar::chunk {{ background:{color}; border-radius:3px; }}")
        self._lbl_ev.setText(evidence[:80] if evidence else "")


# ���� С���� ������������������������������������������������������������������������������������������������������������������������

def _hline() -> QtWidgets.QFrame:
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return line


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
