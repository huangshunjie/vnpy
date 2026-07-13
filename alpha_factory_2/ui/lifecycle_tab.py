"""
alpha_factory_2/ui/lifecycle_tab.py  (Phase 5)

LifecycleTab — Alpha 生命周期面板。

布局：
  顶部：状态分布卡片（7 个状态计数）
  中部：左侧 Alpha 列表（按状态过滤）/ 右侧迁移时间轴
  底部：操作栏（promote_to_live / auto_evaluate / 全流水线V2 / 刷新）
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

_ALPHA_COLS = [
    ("Alpha ID",   110),
    ("状态",        80),
    ("总分",        70),
    ("IC",          60),
    ("半衰期",       60),
    ("迁移次数",     60),
    ("生成时间",    130),
]

_TL_COLS = [
    ("从 From",   90),
    ("到 To",     90),
    ("原因",      200),
    ("时间",      130),
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


class _StatusCard(QtWidgets.QWidget):
    def __init__(self, status_val: str, parent=None) -> None:
        super().__init__(parent)
        color = _STATUS_COLOR.get(status_val, _MUT)
        self.setFixedHeight(66)
        self.setStyleSheet(
            f"background: #11111b; border-radius: 6px;"
            f" border: 1px solid {color}44;"
        )
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(10, 6, 10, 6)
        v.setSpacing(2)
        self._lbl_t = QtWidgets.QLabel(status_val.upper())
        self._lbl_t.setStyleSheet(
            f"color: {color}; font-size: 12px; border: none;")
        self._lbl_v = QtWidgets.QLabel("0")
        self._lbl_v.setStyleSheet(
            f"color: {color}; font-size: 20px; font-weight: bold; border: none;")
        v.addWidget(self._lbl_t)
        v.addWidget(self._lbl_v)

    def update(self, n: int) -> None:
        self._lbl_v.setText(str(n))


class LifecycleTab(QtWidgets.QWidget):
    """Alpha 生命周期面板（Phase 5）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._selected_id: str | None = None
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self._build_status_cards())

        mid = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        mid.addWidget(self._build_alpha_panel())
        mid.addWidget(self._build_timeline_panel())
        mid.setSizes([700, 500])
        root.addWidget(mid, stretch=1)
        root.addWidget(self._build_action_bar())

    def _build_status_cards(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(82)
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        self._cards: dict[str, _StatusCard] = {}
        for s in AlphaStatus:
            card = _StatusCard(s.value)
            self._cards[s.value] = card
            h.addWidget(card, stretch=1)
        return w

    def _build_alpha_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        top = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel("Alpha 列表  Alpha List")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 12px;")
        top.addWidget(lbl)
        top.addStretch()

        self._cmb_filter = QtWidgets.QComboBox()
        self._cmb_filter.addItem("全部  All", "all")
        for s in AlphaStatus:
            self._cmb_filter.addItem(s.value.upper(), s.value)
        self._cmb_filter.setStyleSheet(
            f"QComboBox {{ background: #11111b; color: {_FG};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 2px 8px; font-size: 12px; }}"
            f"QComboBox QAbstractItemView {{ background: #11111b; color: {_FG}; }}"
        )
        self._cmb_filter.currentIndexChanged.connect(lambda _: self.refresh())
        top.addWidget(self._cmb_filter)
        v.addLayout(top)

        self._tbl_alpha = QtWidgets.QTableWidget(0, len(_ALPHA_COLS))
        self._tbl_alpha.setHorizontalHeaderLabels([c[0] for c in _ALPHA_COLS])
        for i, (_, w_) in enumerate(_ALPHA_COLS):
            self._tbl_alpha.setColumnWidth(i, w_)
        self._tbl_alpha.horizontalHeader().setStretchLastSection(True)
        self._tbl_alpha.verticalHeader().setVisible(False)
        self._tbl_alpha.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_alpha.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_alpha.setStyleSheet("font-size: 13px;")
        self._tbl_alpha.cellClicked.connect(self._on_alpha_selected)
        v.addWidget(self._tbl_alpha, stretch=1)
        return w

    def _build_timeline_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        self._lbl_timeline_title = QtWidgets.QLabel("迁移时间轴  Timeline  —  选择左侧 Alpha")
        self._lbl_timeline_title.setStyleSheet(f"color: {_MUT}; font-size: 12px;")
        v.addWidget(self._lbl_timeline_title)

        self._tbl_tl = QtWidgets.QTableWidget(0, len(_TL_COLS))
        self._tbl_tl.setHorizontalHeaderLabels([c[0] for c in _TL_COLS])
        for i, (_, w_) in enumerate(_TL_COLS):
            self._tbl_tl.setColumnWidth(i, w_)
        self._tbl_tl.horizontalHeader().setStretchLastSection(True)
        self._tbl_tl.verticalHeader().setVisible(False)
        self._tbl_tl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_tl.setStyleSheet("font-size: 13px;")
        v.addWidget(self._tbl_tl, stretch=1)
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

        h.addWidget(_btn("▶ 推进 LIVE",      _GRN, self._on_promote))
        h.addWidget(_btn("⟳ 自动评估",        _BLU, self._on_auto_eval))
        h.addWidget(_btn("▶▶ 五阶段流水线",   _MAV, self._on_pipeline_v2))
        h.addStretch()
        h.addWidget(_btn("刷新 Refresh",      _MUT, self.refresh))
        return bar

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        if self._engine is None:
            return
        lc_summ = self._engine.lifecycle_engine.summary()
        by_s    = lc_summ.get("by_status", {})
        for s_val, card in self._cards.items():
            card.update(by_s.get(s_val, 0))

        filter_val = self._cmb_filter.currentData()
        all_lcs    = self._engine.lifecycle_engine.get_all()
        if filter_val and filter_val != "all":
            all_lcs = [lc for lc in all_lcs if lc.status.value == filter_val]

        self._render_alphas(all_lcs)

        if self._selected_id:
            self._render_timeline(self._selected_id)

    # ------------------------------------------------------------------ #
    #  回调
    # ------------------------------------------------------------------ #

    def _on_promote(self) -> None:
        if self._engine:
            self._engine.promote_to_live()
            self.refresh()

    def _on_auto_eval(self) -> None:
        if self._engine:
            self._engine.auto_evaluate_all()
            self.refresh()

    def _on_pipeline_v2(self) -> None:
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "未初始化", "请先启动 Alpha Factory 引擎。")
            return
        self._engine.run_full_pipeline_v2(n=10)
        self.refresh()

    def _on_alpha_selected(self, row: int, _col: int) -> None:
        item = self._tbl_alpha.item(row, 0)
        if item:
            self._selected_id = item.text()
            self._render_timeline(self._selected_id)

    # ------------------------------------------------------------------ #
    #  渲染
    # ------------------------------------------------------------------ #

    def _render_alphas(self, lcs: list) -> None:
        self._tbl_alpha.setRowCount(0)
        alphas  = getattr(self._engine, '_alphas', {})
        scores  = getattr(self._engine, '_scores', {})
        for lc in lcs:
            row = self._tbl_alpha.rowCount()
            self._tbl_alpha.insertRow(row)
            s_val  = lc.status.value
            color  = _STATUS_COLOR.get(s_val, _MUT)
            sc     = scores.get(lc.alpha_id)
            alpha  = alphas.get(lc.alpha_id)
            total  = f"{sc.total_score:.4f}" if sc else "---"
            ic_v   = f"{sc.ic:.4f}"          if sc else "---"
            hl_v   = f"{sc.decay:.1f}"       if sc else "---"
            cr_at  = str(alpha.created_at)[:19] if alpha else "---"
            self._tbl_alpha.setItem(row, 0, _item(lc.alpha_id,    _MAV))
            self._tbl_alpha.setItem(row, 1, _item(s_val,          color))
            self._tbl_alpha.setItem(row, 2, _item(total,          color))
            self._tbl_alpha.setItem(row, 3, _item(ic_v,           _FG))
            self._tbl_alpha.setItem(row, 4, _item(hl_v,           _BLU))
            self._tbl_alpha.setItem(row, 5, _item(len(lc.events), _MUT))
            self._tbl_alpha.setItem(row, 6, _item(cr_at,          _MUT))

    def _render_timeline(self, alpha_id: str) -> None:
        self._lbl_timeline_title.setText(
            f"迁移时间轴  Timeline  —  {alpha_id}")
        timeline = self._engine.get_alpha_timeline(alpha_id)
        self._tbl_tl.setRowCount(0)
        for ev in timeline:
            row = self._tbl_tl.rowCount()
            self._tbl_tl.insertRow(row)
            fc = _STATUS_COLOR.get(ev["from"], _MUT)
            tc = _STATUS_COLOR.get(ev["to"],   _GRN)
            self._tbl_tl.setItem(row, 0, _item(ev["from"],   fc))
            self._tbl_tl.setItem(row, 1, _item(ev["to"],     tc))
            self._tbl_tl.setItem(row, 2, _item_left(ev["reason"], _MUT))
            self._tbl_tl.setItem(row, 3, _item(ev["ts"],     _MUT))
