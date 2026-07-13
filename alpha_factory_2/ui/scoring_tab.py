"""
alpha_factory_2/ui/scoring_tab.py

ScoringTab — Alpha 评分面板（Phase 3）。

布局：
  顶部：5 个 KPI 卡片（平均分/最高分/已评分数/平均IC/平均IR）
  中部：评分排行表（可排序）
  底部：操作栏（批量评分 / 刷新）
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

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

_SCORE_COLS = [
    ("排名",         50),
    ("Alpha ID",    110),
    ("总分 Total",   80),
    ("IC",           70),
    ("RankIC",       70),
    ("稳定性 IR",    80),
    ("半衰期 HL",    70),
    ("换手率 TO",    70),
    ("状态",         80),
    ("因子数",       60),
    ("表达式",      200),
]


def _score_color(score: float) -> str:
    if score >= 0.7:
        return _GRN
    if score >= 0.4:
        return _YLW
    return _RED


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
        self.setFixedHeight(66)
        self.setStyleSheet(
            f"background: #11111b; border-radius: 6px;"
            f" border: 1px solid {_BORDER};"
        )
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(12, 6, 12, 6)
        v.setSpacing(2)
        self._lbl_t = QtWidgets.QLabel(title)
        self._lbl_t.setStyleSheet(
            f"color: {_MUT}; font-size: 12px; border: none;")
        self._lbl_v = QtWidgets.QLabel("---")
        self._lbl_v.setStyleSheet(
            f"color: {_FG}; font-size: 18px; font-weight: bold; border: none;")
        v.addWidget(self._lbl_t)
        v.addWidget(self._lbl_v)

    def update(self, value: str, color: str = _FG) -> None:
        self._lbl_v.setText(value)
        self._lbl_v.setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: bold; border: none;")


class ScoringTab(QtWidgets.QWidget):
    """Alpha 评分面板（Phase 3）。"""

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
        root.addWidget(self._build_ranking_table(), stretch=1)
        root.addWidget(self._build_action_bar())

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(82)
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)

        self._kpi_scored  = _KpiCard("已评分  Scored")
        self._kpi_mean    = _KpiCard("平均分  Mean Score")
        self._kpi_top     = _KpiCard("最高分  Top Score")
        self._kpi_mean_ic = _KpiCard("平均 IC")
        self._kpi_mean_ir = _KpiCard("平均稳定性 IR")

        for card in (self._kpi_scored, self._kpi_mean, self._kpi_top,
                     self._kpi_mean_ic, self._kpi_mean_ir):
            h.addWidget(card, stretch=1)
        return w

    def _build_ranking_table(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        lbl = QtWidgets.QLabel("评分排行  Score Ranking")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 12px;")
        v.addWidget(lbl)

        self._tbl = QtWidgets.QTableWidget(0, len(_SCORE_COLS))
        self._tbl.setHorizontalHeaderLabels([c[0] for c in _SCORE_COLS])
        for i, (_, w_) in enumerate(_SCORE_COLS):
            self._tbl.setColumnWidth(i, w_)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.horizontalHeader().setSortIndicatorShown(True)
        self._tbl.setSortingEnabled(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl.setStyleSheet("font-size: 13px;")
        v.addWidget(self._tbl, stretch=1)
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
                f" padding: 4px 14px; font-size: 14px; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            b.clicked.connect(slot)
            return b

        h.addWidget(_btn("★ 批量评分  Batch Score", _MAV, self._on_batch_score))
        h.addStretch()
        h.addWidget(_btn("刷新 Refresh", _MUT, self.refresh))
        return bar

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        if self._engine is None:
            return
        summ   = self._engine.scoring_engine.summary()
        scores = self._engine.get_score_ranking(top_n=500)
        self._update_kpis(summ, scores)
        self._render_table(scores)

    # ------------------------------------------------------------------ #
    #  回调
    # ------------------------------------------------------------------ #

    def _on_batch_score(self) -> None:
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "未初始化", "请先启动 Alpha Factory 引擎。")
            return
        self._engine.batch_score()
        self.refresh()

    # ------------------------------------------------------------------ #
    #  渲染
    # ------------------------------------------------------------------ #

    def _update_kpis(self, summ: dict, scores: list) -> None:
        n = summ.get("scored", 0)
        self._kpi_scored.update(str(n), _MAV)

        mean_s = summ.get("mean_score", 0.0)
        self._kpi_mean.update(f"{mean_s:.3f}", _score_color(mean_s))

        top_s = summ.get("max_score", 0.0)
        self._kpi_top.update(f"{top_s:.3f}", _score_color(top_s))

        if scores:
            mean_ic = sum(s.ic for s in scores) / len(scores)
            mean_ir = sum(s.stability for s in scores) / len(scores)
        else:
            mean_ic = mean_ir = 0.0

        ic_color = _GRN if mean_ic > 0.03 else (_YLW if mean_ic > 0 else _RED)
        self._kpi_mean_ic.update(f"{mean_ic:.4f}", ic_color)

        ir_color = _GRN if mean_ir > 0.5 else (_YLW if mean_ir > 0 else _RED)
        self._kpi_mean_ir.update(f"{mean_ir:.3f}", ir_color)

    def _render_table(self, scores: list) -> None:
        self._tbl.setSortingEnabled(False)
        self._tbl.setRowCount(0)

        alphas = getattr(self._engine, '_alphas', {})

        for rank, sc in enumerate(scores, start=1):
            row = self._tbl.rowCount()
            self._tbl.insertRow(row)
            sc_color = _score_color(sc.total_score)
            ic_color = _GRN if sc.ic > 0.03 else (_YLW if sc.ic > 0 else _RED)
            ir_color = _GRN if sc.stability > 0.5 else (
                _YLW if sc.stability > 0 else _RED)

            alpha = alphas.get(sc.alpha_id)
            status = alpha.status.value if alpha else "---"
            n_factors = len(alpha.factors) if alpha else 0
            expr = (alpha.expression[:60] + "…"
                    if alpha and len(alpha.expression) > 60
                    else (alpha.expression if alpha else "---"))

            self._tbl.setItem(row, 0,  _item(rank,                      _MUT))
            self._tbl.setItem(row, 1,  _item(sc.alpha_id,               _MAV))
            self._tbl.setItem(row, 2,  _item(f"{sc.total_score:.4f}",   sc_color))
            self._tbl.setItem(row, 3,  _item(f"{sc.ic:.4f}",            ic_color))
            self._tbl.setItem(row, 4,  _item(f"{sc.rank_ic:.4f}",       ic_color))
            self._tbl.setItem(row, 5,  _item(f"{sc.stability:.3f}",     ir_color))
            self._tbl.setItem(row, 6,  _item(f"{sc.decay:.1f}",         _BLU))
            self._tbl.setItem(row, 7,  _item(f"{sc.turnover:.3f}",      _ORG))
            self._tbl.setItem(row, 8,  _item(status,                    _FG))
            self._tbl.setItem(row, 9,  _item(n_factors,                 _FG))
            self._tbl.setItem(row, 10, _item_left(expr,                 _MUT))

        self._tbl.setSortingEnabled(True)
