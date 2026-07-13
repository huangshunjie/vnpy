"""
cross_market_ai/ui/dashboard_tab.py

Phase 4: Dashboard — 跨市场总览面板。
"""
from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtWidgets, QtCore, QtGui

from ..constant import APP_NAME
from ..engine import CrossMarketEngine
from ..event import EVENT_CROSS_MARKET_MAPPING_COMPLETED, EVENT_UNIVERSALITY_SCORED

_GRADE_COLORS = {
    "UNIVERSAL": "#4caf50", "PORTABLE": "#ff9800",
    "LOCAL": "#ff5722",     "FRAGILE":  "#f44336",
}


class DashboardTab(QtWidgets.QWidget):
    signal_mapped = QtCore.pyqtSignal(dict)
    signal_scored = QtCore.pyqtSignal(dict)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._cm_engine: CrossMarketEngine = main_engine.get_engine(APP_NAME)
        self._init_ui()
        self._register_events()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        root.addWidget(self._build_status_cards())
        mid = QtWidgets.QHBoxLayout()
        mid.addWidget(self._build_summary_table(),      stretch=1)
        mid.addWidget(self._build_feasibility_matrix(), stretch=1)
        root.addLayout(mid, stretch=1)
        root.addWidget(self._build_universality_panel(), stretch=0)
        btn = QtWidgets.QPushButton("⟳  刷新总览")
        btn.clicked.connect(self._on_refresh)
        btn.setStyleSheet("padding:4px 16px;")
        root.addWidget(btn, alignment=QtCore.Qt.AlignRight)

    def _build_status_cards(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        self._card_status   = _StatusCard("系统状态",    "IDLE",    "#607d8b")
        self._card_phase    = _StatusCard("当前阶段",    "Phase 4", "#1565c0")
        self._card_mapped   = _StatusCard("已映射市场",  "0",       "#2e7d32")
        self._card_transfer = _StatusCard("迁移次数",    "0",       "#6a1b9a")
        self._card_scored   = _StatusCard("已评分Alpha", "0",       "#e65100")
        self._card_top      = _StatusCard("最高普适性",  "-",       "#4caf50")
        for c in [self._card_status, self._card_phase, self._card_mapped,
                  self._card_transfer, self._card_scored, self._card_top]:
            layout.addWidget(c)
        return widget

    def _build_summary_table(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("市场结构映射摘要")
        layout = QtWidgets.QVBoxLayout(group)
        self._summary_table = QtWidgets.QTableWidget(0, 5)
        self._summary_table.setHorizontalHeaderLabels([
            "市场", "复杂度", "可交易性", "可迁移性先验", "数据来源",
        ])
        self._summary_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch)
        self._summary_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._summary_table.setAlternatingRowColors(True)
        layout.addWidget(self._summary_table)
        return group

    def _build_feasibility_matrix(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Alpha 迁移可行性矩阵（结构相似度）")
        layout = QtWidgets.QVBoxLayout(group)
        self._matrix_table = QtWidgets.QTableWidget(0, 0)
        self._matrix_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        note = QtWidgets.QLabel("绿色 ≥ 0.7  橙色 ≥ 0.4  红色 < 0.4")
        note.setStyleSheet("color:#888; font-size:10px;")
        layout.addWidget(self._matrix_table)
        layout.addWidget(note)
        return group

    def _build_universality_panel(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Alpha 普适性评分摘要")
        layout = QtWidgets.QHBoxLayout(group)
        layout.setSpacing(12)

        self._univ_table = QtWidgets.QTableWidget(0, 4)
        self._univ_table.setHorizontalHeaderLabels([
            "Alpha", "综合评分", "等级", "跨市场稳定性",
        ])
        self._univ_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch)
        self._univ_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._univ_table.setMaximumHeight(150)
        layout.addWidget(self._univ_table, stretch=1)

        stats = QtWidgets.QFrame()
        stats.setFrameShape(QtWidgets.QFrame.StyledPanel)
        stats.setFixedWidth(180)
        sl = QtWidgets.QVBoxLayout(stats)
        sl.setContentsMargins(8, 8, 8, 8)
        sl.setSpacing(6)
        lbl_t = QtWidgets.QLabel("等级分布")
        lbl_t.setStyleSheet("font-weight:bold; color:#aaa; font-size:11px;")
        sl.addWidget(lbl_t)
        self._grade_lbls: dict[str, QtWidgets.QLabel] = {}
        for grade, color in _GRADE_COLORS.items():
            rw = QtWidgets.QWidget()
            rl = QtWidgets.QHBoxLayout(rw)
            rl.setContentsMargins(0, 0, 0, 0)
            lg = QtWidgets.QLabel(grade)
            lg.setStyleSheet(f"color:{color}; font-size:10px; font-weight:bold;")
            lg.setFixedWidth(80)
            cnt = QtWidgets.QLabel("0")
            cnt.setStyleSheet("font-size:11px;")
            rl.addWidget(lg)
            rl.addWidget(cnt)
            sl.addWidget(rw)
            self._grade_lbls[grade] = cnt
        sl.addStretch()
        layout.addWidget(stats, stretch=0)
        return group

    # ���� �¼�ע�� ������������������������������������������������������������������������������������������������������������

    def _register_events(self) -> None:
        self.signal_mapped.connect(self._on_mapping_done)
        self.signal_scored.connect(self._on_scored_done)
        self._event_engine.register(
            EVENT_CROSS_MARKET_MAPPING_COMPLETED, self.signal_mapped.emit)
        self._event_engine.register(
            EVENT_UNIVERSALITY_SCORED, self.signal_scored.emit)

    # ���� �ۺ��� ����������������������������������������������������������������������������������������������������������������

    def _on_refresh(self) -> None:
        summary = self._cm_engine.get_summary()
        self._card_status.set_value(summary.get("status", "-").upper())
        self._card_phase.set_value(f"Phase {summary.get('phase', 4)}")
        self._card_mapped.set_value(str(summary.get("markets_mapped", 0)))
        self._card_transfer.set_value(str(summary.get("total_transfers", 0)))
        self._card_scored.set_value(str(summary.get("total_scored", 0)))
        top   = summary.get("top_alpha", "-") or "-"
        avg_u = summary.get("avg_univ_score", 0.0)
        self._card_top.set_value(f"{top} ({avg_u:.2f})")

        cached = self._cm_engine.get_cached_structures()
        if cached:
            self._refresh_summary_table(cached)
            self._refresh_feasibility_matrix(cached)

        univ_cached = self._cm_engine.get_cached_universality()
        if univ_cached:
            self._refresh_universality_table(univ_cached)

        us = self._cm_engine.get_universality_state()
        self._update_grade_counts(us)

    def _on_mapping_done(self, data: dict) -> None:
        if data.get("status") == "ok":
            self._on_refresh()

    def _on_scored_done(self, data: dict) -> None:
        if data.get("status") == "ok":
            univ_cached = self._cm_engine.get_cached_universality()
            if univ_cached:
                self._refresh_universality_table(univ_cached)
            us = self._cm_engine.get_universality_state()
            self._update_grade_counts(us)
            self._card_scored.set_value(str(us.get("total_scored", 0)))

    # ���� ˢ���߼� ������������������������������������������������������������������������������������������������������������

    def _refresh_summary_table(self, cached: dict) -> None:
        self._summary_table.setRowCount(0)
        for mid, vec in cached.items():
            row = self._summary_table.rowCount()
            self._summary_table.insertRow(row)
            complexity  = vec.get("complexity_score",  0.0)
            tradability = vec.get("tradability_score", 0.0)
            portability = vec.get("portability_score", 0.0)
            source      = vec.get("volatility", {}).get("source", "prior")
            self._summary_table.setItem(row, 0, _cell(mid))
            self._summary_table.setItem(row, 1, _ccell(f"{complexity:.4f}",  complexity, invert=True))
            self._summary_table.setItem(row, 2, _ccell(f"{tradability:.4f}", tradability))
            self._summary_table.setItem(row, 3, _ccell(f"{portability:.4f}", portability))
            src_i = _cell(source)
            src_i.setForeground(QtGui.QColor("#4caf50" if source == "live" else "#888"))
            self._summary_table.setItem(row, 4, src_i)

    def _refresh_feasibility_matrix(self, cached: dict) -> None:
        markets = list(cached.keys())
        n = len(markets)
        if n == 0:
            return
        self._matrix_table.setRowCount(n)
        self._matrix_table.setColumnCount(n)
        self._matrix_table.setHorizontalHeaderLabels(markets)
        self._matrix_table.setVerticalHeaderLabels(markets)

        from ..utils.cross_market_utils import compute_structural_similarity
        from ..model.structure_model import (
            MarketStructureVector, VolatilityStructure, LiquidityStructure,
            ParticipantStructure, MicrostructureNoise, RegimeDistribution,
        )

        def _d2v(d: dict) -> MarketStructureVector:
            vd = d.get("volatility",  {})
            ld = d.get("liquidity",   {})
            pd = d.get("participant", {})
            nd = d.get("noise",       {})
            rd = d.get("regime",      {})
            return MarketStructureVector(
                market_id   = d.get("market_id", ""),
                volatility  = VolatilityStructure(
                    annual_vol=vd.get("annual_vol", 0.), daily_vol=vd.get("daily_vol", 0.),
                    vol_of_vol=vd.get("vol_of_vol", 0.), skew=vd.get("skew", 0.),
                    excess_kurtosis=vd.get("excess_kurtosis", 0.),
                    jump_intensity=vd.get("jump_intensity", 0.)),
                liquidity   = LiquidityStructure(
                    bid_ask_spread_bps=ld.get("bid_ask_spread_bps", 0.),
                    depth_score=ld.get("depth_score", 0.),
                    turnover_ratio=ld.get("turnover_ratio", 0.),
                    market_impact_coeff=ld.get("market_impact_coeff", 0.)),
                participant = ParticipantStructure(
                    retail_ratio=pd.get("retail_ratio", 0.),
                    institutional_ratio=pd.get("institutional_ratio", 0.),
                    hft_ratio=pd.get("hft_ratio", 0.),
                    info_asymmetry=pd.get("info_asymmetry", 0.)),
                noise       = MicrostructureNoise(
                    noise_ratio=nd.get("noise_ratio", 0.),
                    autocorr_lag1=nd.get("autocorr_lag1", 0.),
                    price_discreteness=nd.get("price_discreteness", 0.),
                    adverse_selection=nd.get("adverse_selection", 0.),
                    limit_distortion=nd.get("limit_distortion", 0.)),
                regime      = RegimeDistribution(
                    distribution=rd.get("distribution", {}),
                    n_regimes=rd.get("n_regimes", 0),
                    dominant_regime=rd.get("dominant_regime", ""),
                    entropy=rd.get("entropy", 0.)),
                portability_score=d.get("portability_score", 0.),
            )

        vecs = {mid: _d2v(v) for mid, v in cached.items()}
        for r, m_row in enumerate(markets):
            for c, m_col in enumerate(markets):
                if r == c:
                    item = _cell("��")
                    item.setBackground(QtGui.QColor("#333"))
                else:
                    sim  = compute_structural_similarity(vecs[m_row], vecs[m_col])
                    item = _cell(f"{sim:.3f}")
                    item.setBackground(QtGui.QColor(
                        "#1b5e20" if sim >= 0.7 else
                        "#e65100" if sim >= 0.4 else "#b71c1c"
                    ))
                self._matrix_table.setItem(r, c, item)
        self._matrix_table.resizeColumnsToContents()

    def _refresh_universality_table(self, cached: dict) -> None:
        self._univ_table.setRowCount(0)
        records = sorted(cached.values(),
                         key=lambda r: r.get("score", 0.0), reverse=True)
        for rec in records:
            row   = self._univ_table.rowCount()
            self._univ_table.insertRow(row)
            score = rec.get("score", 0.0)
            grade = rec.get("grade", "")
            color = _GRADE_COLORS.get(grade, "#888")
            cs    = rec.get("dim_cross_market", {}).get("score", 0.0)
            self._univ_table.setItem(row, 0, _cell(rec.get("alpha_id", "")))
            sc_i = _cell(f"{score:.4f}")
            sc_i.setForeground(QtGui.QColor(color))
            self._univ_table.setItem(row, 1, sc_i)
            gr_i = _cell(grade)
            gr_i.setForeground(QtGui.QColor(color))
            self._univ_table.setItem(row, 2, gr_i)
            self._univ_table.setItem(row, 3, _cell(f"{cs:.4f}"))

    def _update_grade_counts(self, state: dict) -> None:
        for grade in _GRADE_COLORS:
            cnt = state.get(f"{grade.lower()}_count", 0)
            lbl = self._grade_lbls.get(grade)
            if lbl:
                lbl.setText(str(cnt))


# ���� ״̬��Ƭ ��������������������������������������������������������������������������������������������������������������������

class _StatusCard(QtWidgets.QFrame):
    def __init__(self, label: str, value: str, color: str) -> None:
        super().__init__()
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFixedHeight(72)
        self.setStyleSheet(f"border-left:4px solid {color}; padding-left:6px;")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        lbl = QtWidgets.QLabel(label)
        lbl.setStyleSheet("color:#888; font-size:10px;")
        layout.addWidget(lbl)
        self._val = QtWidgets.QLabel(value)
        self._val.setStyleSheet(f"color:{color}; font-size:16px; font-weight:bold;")
        layout.addWidget(self._val)

    def set_value(self, value: str) -> None:
        self._val.setText(value)


# ���� С���� ������������������������������������������������������������������������������������������������������������������������

def _cell(text: str) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(text)
    item.setTextAlignment(QtCore.Qt.AlignCenter)
    return item


def _ccell(text: str, score: float, invert: bool = False) -> QtWidgets.QTableWidgetItem:
    item = _cell(text)
    eff  = (1.0 - score) if invert else score
    color = "#4caf50" if eff >= 0.6 else "#ff9800" if eff >= 0.3 else "#f44336"
    item.setForeground(QtGui.QColor(color))
    return item
