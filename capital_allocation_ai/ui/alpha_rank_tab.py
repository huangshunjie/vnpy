"""
capital_allocation_ai/ui/alpha_rank_tab.py  (Phase 2)

AlphaRankTab — Alpha 资本评分排行面板。

布局：
  顶部：5 个 KPI 卡片（已评分数 / 平均资本分 / 最高分 / 平均 IC / 平均 IR）
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

_RANK_COLS = [
    ("排名",          50),
    ("Alpha ID",     110),
    ("资本评分",       80),
    ("IC Mean",       75),
    ("稳定性 IR",      75),
    ("容量 Cap",       75),
    ("衰减 Decay",     75),
    ("半衰期 HL",      75),
    ("Sharpe",        75),
    ("波动率",         70),
    ("IC 期数",        65),
    ("状态",           70),
]


def _score_color(s: float) -> str:
    if s >= 0.6: return _GRN
    if s >= 0.35: return _YLW
    return _RED


def _item(text, color=_FG):
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
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


class AlphaRankTab(QtWidgets.QWidget):
    """Alpha 资本评分排行面板（Phase 2）。"""

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
        root.addWidget(self._build_rank_table(), stretch=1)
        root.addWidget(self._build_action_bar())

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(82)
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        self._kpi_scored   = _KpiCard("已评分  Scored")
        self._kpi_mean     = _KpiCard("平均资本分  Mean")
        self._kpi_top      = _KpiCard("最高分  Top Score")
        self._kpi_mean_ic  = _KpiCard("平均 IC")
        self._kpi_mean_ir  = _KpiCard("平均稳定性 IR")
        for c in (self._kpi_scored, self._kpi_mean, self._kpi_top,
                  self._kpi_mean_ic, self._kpi_mean_ir):
            h.addWidget(c, stretch=1)
        return w

    def _build_rank_table(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("Alpha 资本评分排行  Capital Score Ranking")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._tbl = QtWidgets.QTableWidget(0, len(_RANK_COLS))
        self._tbl.setHorizontalHeaderLabels([c[0] for c in _RANK_COLS])
        for i, (_, w_) in enumerate(_RANK_COLS):
            self._tbl.setColumnWidth(i, w_)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.horizontalHeader().setSortIndicatorShown(True)
        self._tbl.setSortingEnabled(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl.setStyleSheet("font-size: 11px;")
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
                f" padding: 4px 14px; font-size: 12px; }}"
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
        ranking = self._engine.scoring_engine.get_ranking(top_n=500)
        summ    = self._engine.scoring_engine.summary()
        self._update_kpis(ranking, summ)
        self._render_table(ranking)

    # ------------------------------------------------------------------ #
    #  回调
    # ------------------------------------------------------------------ #

    def _on_batch_score(self) -> None:
        if self._engine is None:
            QtWidgets.QMessageBox.warning(
                self, "未初始化", "请先启动 Capital Allocation AI 引擎。")
            return
        self._engine.batch_score_alphas()
        self.refresh()

    # ------------------------------------------------------------------ #
    #  渲染
    # ------------------------------------------------------------------ #

    def _update_kpis(self, ranking: list, summ: dict) -> None:
        n = summ.get("scored", 0)
        self._kpi_scored.update(str(n), _MAV)

        mean_s = summ.get("mean_score", 0.0)
        self._kpi_mean.update(f"{mean_s:.3f}", _score_color(mean_s))

        top_s = summ.get("max_score", 0.0)
        self._kpi_top.update(f"{top_s:.3f}", _score_color(top_s))

        if ranking:
            mean_ic = sum(s.ic_mean    for s in ranking) / len(ranking)
            mean_ir = sum(s.stability  for s in ranking) / len(ranking)
        else:
            mean_ic = mean_ir = 0.0

        ic_c = _GRN if mean_ic > 0.03 else (_YLW if mean_ic > 0 else _RED)
        self._kpi_mean_ic.update(f"{mean_ic:.4f}", ic_c)

        ir_c = _GRN if mean_ir > 0.5 else (_YLW if mean_ir > 0 else _RED)
        self._kpi_mean_ir.update(f"{mean_ir:.3f}", ir_c)

    def _render_table(self, ranking: list) -> None:
        self._tbl.setSortingEnabled(False)
        self._tbl.setRowCount(0)

        for rank, sc in enumerate(ranking, start=1):
            row = self._tbl.rowCount()
            self._tbl.insertRow(row)
            sc_c = _score_color(sc.capital_score)
            ic_c = _GRN if sc.ic_mean > 0.03 else (
                _YLW if sc.ic_mean > 0 else _RED)
            ir_c = _GRN if sc.stability > 0.5 else (
                _YLW if sc.stability > 0 else _RED)

            self._tbl.setItem(row,  0, _item(rank,                        _MUT))
            self._tbl.setItem(row,  1, _item(sc.alpha_id,                 _MAV))
            self._tbl.setItem(row,  2, _item(f"{sc.capital_score:.4f}",   sc_c))
            self._tbl.setItem(row,  3, _item(f"{sc.ic_mean:.4f}",         ic_c))
            self._tbl.setItem(row,  4, _item(f"{sc.stability:.3f}",       ir_c))
            self._tbl.setItem(row,  5, _item(f"{sc.capacity:.3f}",        _BLU))
            self._tbl.setItem(row,  6, _item(f"{sc.decay:.3f}",           _BLU))
            self._tbl.setItem(row,  7, _item(f"{sc.half_life:.1f}",       _FG))
            self._tbl.setItem(row,  8, _item(f"{sc.sharpe:.3f}",          _ORG))
            self._tbl.setItem(row,  9, _item(f"{sc.volatility:.3f}",      _MUT))
            self._tbl.setItem(row, 10, _item(sc.ic_series_len,             _MUT))
            self._tbl.setItem(row, 11, _item(sc.status.value,             _GRN))

        self._tbl.setSortingEnabled(True)
