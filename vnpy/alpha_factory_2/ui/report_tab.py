"""
alpha_factory_2/ui/report_tab.py  (Phase 5)

ReportTab — Alpha 全局报告面板。

布局：
  顶部：6 个全局 KPI（总Alpha / LIVE数 / 平均分 / 最高分 / 总退役 / 通过率）
  中部：左侧生命周期分布饼图（用文字卡片模拟）/ 右侧 LIVE Alpha 排行表
  底部：系统摘要文本
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import AlphaStatus

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_MAV      = "#cba6f7"
_ORG      = "#fab387"

_STATUS_COLOR = {
    AlphaStatus.GENERATED.value: _MUT,
    AlphaStatus.SCORED.value:    _BLU,
    AlphaStatus.SCREENED.value:  _YLW,
    AlphaStatus.LIVE.value:      _GRN,
    AlphaStatus.DEGRADED.value:  _ORG,
    AlphaStatus.REJECTED.value:  _RED,
    AlphaStatus.RETIRED.value:   "#6c6c7a",
}

_LIVE_COLS = [
    ("排名",      50),
    ("Alpha ID", 110),
    ("总分",      70),
    ("IC",        65),
    ("IR",        65),
    ("半衰期",    65),
    ("换手率",    65),
    ("表达式",   200),
]


def _item(text, color=_FG):
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    it.setForeground(QtGui.QColor(color))
    return it


def _item_left(text, color=_FG):
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
    it.setForeground(QtGui.QColor(color))
    return it


class _KpiCard(QtWidgets.QWidget):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(70)
        self.setStyleSheet(
            f"background: #11111b; border-radius: 6px;"
            f" border: 1px solid {_BORDER};"
        )
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(12, 6, 12, 6)
        v.setSpacing(2)
        self._lt = QtWidgets.QLabel(title)
        self._lt.setStyleSheet(f"color: {_MUT}; font-size: 10px; border: none;")
        self._lv = QtWidgets.QLabel("---")
        self._lv.setStyleSheet(
            f"color: {_FG}; font-size: 18px; font-weight: bold; border: none;")
        v.addWidget(self._lt)
        v.addWidget(self._lv)

    def update(self, value: str, color: str = _FG) -> None:
        self._lv.setText(value)
        self._lv.setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: bold; border: none;")


class ReportTab(QtWidgets.QWidget):
    """Alpha 全局报告面板（Phase 5）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self._build_kpi_bar())

        mid = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        mid.addWidget(self._build_distribution_panel())
        mid.addWidget(self._build_live_table())
        mid.setSizes([280, 920])
        root.addWidget(mid, stretch=1)

        root.addWidget(self._build_summary_panel())
        root.addWidget(self._build_action_bar())

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(86)
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        self._kpi_total   = _KpiCard("总 Alpha  Total")
        self._kpi_live    = _KpiCard("存活  LIVE")
        self._kpi_mean    = _KpiCard("平均分  Mean Score")
        self._kpi_top     = _KpiCard("最高分  Top Score")
        self._kpi_retired = _KpiCard("退役  Retired")
        self._kpi_rate    = _KpiCard("通过率  Pass Rate")
        for c in (self._kpi_total, self._kpi_live, self._kpi_mean,
                  self._kpi_top, self._kpi_retired, self._kpi_rate):
            h.addWidget(c, stretch=1)
        return w

    def _build_distribution_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(6)
        lbl = QtWidgets.QLabel("状态分布  Status Distribution")
        lbl.setStyleSheet(
            f"color: {_MUT}; font-size: 10px; font-weight: bold;")
        v.addWidget(lbl)

        self._dist_rows: dict[str, QtWidgets.QLabel] = {}
        for s in AlphaStatus:
            row = QtWidgets.QWidget()
            row.setStyleSheet("border: none;")
            rh = QtWidgets.QHBoxLayout(row)
            rh.setContentsMargins(0, 0, 0, 0)
            color = _STATUS_COLOR.get(s.value, _MUT)
            name_lbl = QtWidgets.QLabel(s.value.upper())
            name_lbl.setStyleSheet(
                f"color: {color}; font-size: 11px; min-width: 90px;")
            cnt_lbl = QtWidgets.QLabel("0")
            cnt_lbl.setStyleSheet(
                f"color: {color}; font-size: 13px; font-weight: bold;")
            cnt_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            self._dist_rows[s.value] = cnt_lbl
            rh.addWidget(name_lbl)
            rh.addStretch()
            rh.addWidget(cnt_lbl)
            v.addWidget(row)

        v.addStretch()
        return w

    def _build_live_table(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("存活 Alpha 排行  Live Alpha Ranking")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._tbl_live = QtWidgets.QTableWidget(0, len(_LIVE_COLS))
        self._tbl_live.setHorizontalHeaderLabels([c[0] for c in _LIVE_COLS])
        for i, (_, w_) in enumerate(_LIVE_COLS):
            self._tbl_live.setColumnWidth(i, w_)
        self._tbl_live.horizontalHeader().setStretchLastSection(True)
        self._tbl_live.verticalHeader().setVisible(False)
        self._tbl_live.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_live.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_live.setStyleSheet("font-size: 11px;")
        v.addWidget(self._tbl_live, stretch=1)
        return w

    def _build_summary_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(56)
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(12, 6, 12, 6)
        self._txt_summary = QtWidgets.QLabel("系统尚未启动，点击刷新获取报告。")
        self._txt_summary.setStyleSheet(
            f"color: {_MUT}; font-size: 11px;")
        self._txt_summary.setWordWrap(True)
        v.addWidget(self._txt_summary)
        return w

    def _build_action_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(46)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(8)

        def _btn(label, color, slot):
            b = QtWidgets.QPushButton(label)
            b.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {color};"
                f" border: 1px solid {color}; border-radius: 3px;"
                f" padding: 4px 14px; font-size: 12px; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            b.clicked.connect(slot)
            return b

        h.addWidget(_btn("▶▶ 五阶段流水线  Full Pipeline V2", _MAV,
                         self._on_pipeline_v2))
        h.addStretch()
        h.addWidget(_btn("刷新 Refresh", _MUT, self.refresh))
        return bar

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        if self._engine is None:
            return
        summ  = self._engine.get_summary()
        lc_s  = summ.get("lifecycle", {})
        sc_s  = summ.get("scoring",   {})
        sr_s  = summ.get("screening", {})
        by_s  = lc_s.get("by_status", {})

        # KPI
        total   = lc_s.get("total", 0)
        live    = lc_s.get("live",  0)
        mean_s  = sc_s.get("mean_score", 0.0)
        top_s   = sc_s.get("max_score",  0.0)
        retired = by_s.get(AlphaStatus.RETIRED.value,  0)
        rate    = sr_s.get("pass_rate", 0.0)

        self._kpi_total.update(str(total), _FG)
        self._kpi_live.update(str(live),
            _GRN if live > 0 else _MUT)
        self._kpi_mean.update(f"{mean_s:.3f}",
            _GRN if mean_s >= 0.4 else (_YLW if mean_s >= 0.2 else _RED))
        self._kpi_top.update(f"{top_s:.3f}",
            _GRN if top_s >= 0.5 else _YLW)
        self._kpi_retired.update(str(retired),
            _ORG if retired > 0 else _MUT)
        self._kpi_rate.update(f"{rate:.1%}",
            _GRN if rate >= 0.5 else (_YLW if rate >= 0.3 else _RED))

        # 状态分布
        for s_val, lbl in self._dist_rows.items():
            lbl.setText(str(by_s.get(s_val, 0)))

        # LIVE Alpha 排行
        live_lcs = self._engine.lifecycle_engine.list_by_status(
            AlphaStatus.LIVE)
        alphas   = self._engine._alphas
        scores   = self._engine._scores
        live_scores = [
            scores[lc.alpha_id]
            for lc in live_lcs
            if lc.alpha_id in scores
        ]
        live_scores.sort(key=lambda s: s.total_score, reverse=True)
        self._render_live(live_scores, alphas)

        # 摘要文本
        uptime = summ.get("uptime", 0)
        gen_s  = summ.get("generator", {})
        self._txt_summary.setText(
            f"运行时长 {uptime:.0f}s  |  "
            f"已生成 {total} 个 Alpha  |  "
            f"存活 {live} 个  |  "
            f"退役 {retired} 个  |  "
            f"因子池 {gen_s.get('available_factors', 0)} 个  |  "
            f"平均分 {mean_s:.3f}  |  "
            f"通过率 {rate:.1%}"
        )

    # ------------------------------------------------------------------ #
    #  回调
    # ------------------------------------------------------------------ #

    def _on_pipeline_v2(self) -> None:
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "未初始化", "请先启动 Alpha Factory 引擎。")
            return
        self._engine.run_full_pipeline_v2(n=10)
        self.refresh()

    # ------------------------------------------------------------------ #
    #  渲染
    # ------------------------------------------------------------------ #

    def _render_live(self, scores: list, alphas: dict) -> None:
        self._tbl_live.setRowCount(0)
        for rank, sc in enumerate(scores, start=1):
            row = self._tbl_live.rowCount()
            self._tbl_live.insertRow(row)
            alpha = alphas.get(sc.alpha_id)
            expr  = (alpha.expression[:60] + "…"
                     if alpha and len(alpha.expression) > 60
                     else (alpha.expression if alpha else "---"))
            sc_c  = (_GRN if sc.total_score >= 0.5
                     else _YLW if sc.total_score >= 0.3 else _RED)
            self._tbl_live.setItem(row, 0, _item(rank,                    _MUT))
            self._tbl_live.setItem(row, 1, _item(sc.alpha_id,             _MAV))
            self._tbl_live.setItem(row, 2, _item(f"{sc.total_score:.4f}", sc_c))
            self._tbl_live.setItem(row, 3, _item(f"{sc.ic:.4f}",         _FG))
            self._tbl_live.setItem(row, 4, _item(f"{sc.stability:.3f}",  _FG))
            self._tbl_live.setItem(row, 5, _item(f"{sc.decay:.1f}",      _BLU))
            self._tbl_live.setItem(row, 6, _item(f"{sc.turnover:.3f}",   _ORG))
            self._tbl_live.setItem(row, 7, _item_left(expr,              _MUT))
