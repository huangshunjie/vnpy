"""
live_production/ui/order_tab.py

OrderTab — 订单同步面板（Phase 4）。

布局：
  顶部：KPI 栏（总订单 / 已同步 / 不一致 / 未修复）
  中部：左侧本地订单快照表 / 右侧不一致记录表
  底部：操作按钮栏
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import OrderSyncState
from ..utils.sync_utils import SyncAction

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_ORG      = "#fab387"

_SYNC_COLOR = {
    OrderSyncState.SYNCED.value:    _GRN,
    OrderSyncState.PENDING.value:   _YLW,
    OrderSyncState.MISMATCH.value:  _RED,
    OrderSyncState.REPAIRING.value: _BLU,
}

_ACTION_COLOR = {
    SyncAction.NONE.value:            _MUT,
    SyncAction.FLAG_PENDING.value:    _YLW,
    SyncAction.MARK_CANCEL.value:     _ORG,
    SyncAction.MARK_FILL.value:       _GRN,
    SyncAction.ALERT_MISMATCH.value:  _RED,
}

_ORDER_COLS = [
    ("订单ID",        90),
    ("品种 Symbol",   80),
    ("方向",          60),
    ("数量",          60),
    ("成交",          60),
    ("本地状态",      90),
    ("同步状态",      80),
    ("更新时间",     130),
]

_MISMATCH_COLS = [
    ("订单ID",           90),
    ("本地状态",          80),
    ("交易所状态",        80),
    ("建议动作",         110),
    ("已修复",            60),
    ("发现时间",         130),
    ("详情 Detail",      200),
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


class OrderTab(QtWidgets.QWidget):
    """订单同步面板（Phase 4）。"""

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
        mid.addWidget(self._build_orders_panel())
        mid.addWidget(self._build_mismatch_panel())
        mid.setSizes([600, 600])
        root.addWidget(mid, stretch=1)

        root.addWidget(self._build_action_bar())

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(66)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(20, 6, 20, 6)
        h.setSpacing(32)

        kpis = [
            ("总订单 Total",    "0", _FG),
            ("已同步 Synced",   "0", _GRN),
            ("待确认 Pending",  "0", _YLW),
            ("不一致 Mismatch", "0", _RED),
            ("未修复 Open",     "0", _RED),
            ("历史不一致",      "0", _ORG),
        ]
        self._kpi: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in kpis:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(1)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(
                f"color: {color}; font-size: 14px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._kpi[name] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_orders_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        lbl = QtWidgets.QLabel("本地订单快照  Local Orders")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._tbl_orders = QtWidgets.QTableWidget(0, len(_ORDER_COLS))
        self._tbl_orders.setHorizontalHeaderLabels([c[0] for c in _ORDER_COLS])
        for i, (_, w_) in enumerate(_ORDER_COLS):
            self._tbl_orders.setColumnWidth(i, w_)
        self._tbl_orders.horizontalHeader().setStretchLastSection(True)
        self._tbl_orders.verticalHeader().setVisible(False)
        self._tbl_orders.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_orders.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_orders.setStyleSheet("font-size: 11px;")
        v.addWidget(self._tbl_orders, stretch=1)
        return w

    def _build_mismatch_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        top = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel("不一致记录  Mismatch Records")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        top.addWidget(lbl)
        top.addStretch()

        self._chk_unresolved = QtWidgets.QCheckBox("仅显示未修复")
        self._chk_unresolved.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        self._chk_unresolved.stateChanged.connect(lambda _: self.refresh())
        top.addWidget(self._chk_unresolved)
        v.addLayout(top)

        self._tbl_mm = QtWidgets.QTableWidget(0, len(_MISMATCH_COLS))
        self._tbl_mm.setHorizontalHeaderLabels([c[0] for c in _MISMATCH_COLS])
        for i, (_, w_) in enumerate(_MISMATCH_COLS):
            self._tbl_mm.setColumnWidth(i, w_)
        self._tbl_mm.horizontalHeader().setStretchLastSection(True)
        self._tbl_mm.verticalHeader().setVisible(False)
        self._tbl_mm.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_mm.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_mm.setStyleSheet("font-size: 11px;")
        v.addWidget(self._tbl_mm, stretch=1)
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
                f" padding: 4px 12px; font-size: 12px; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            b.clicked.connect(slot)
            return b

        h.addWidget(_btn("标记选中已修复 Mark Resolved", _GRN, self._on_mark_resolved))
        h.addStretch()

        btn_r = QtWidgets.QPushButton("刷新 Refresh")
        btn_r.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUT};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 4px 12px; font-size: 12px; }}"
        )
        btn_r.clicked.connect(self.refresh)
        h.addWidget(btn_r)
        return bar

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        if self._engine is None:
            return
        oe   = self._engine.order_sync_engine
        summ = oe.summary()

        self._kpi["总订单 Total"   ].setText(str(summ["total_orders"]))
        self._kpi["已同步 Synced"  ].setText(str(summ["synced"]))
        self._kpi["待确认 Pending" ].setText(str(summ["pending"]))
        self._kpi["不一致 Mismatch"].setText(str(summ["mismatch"]))
        self._kpi["未修复 Open"    ].setText(str(summ["unresolved"]))
        self._kpi["历史不一致"      ].setText(str(summ["total_mismatch_records"]))

        unresolved_only = self._chk_unresolved.isChecked()
        self._refresh_orders(oe.get_all_orders())
        self._refresh_mismatches(oe.get_mismatches(limit=200,
                                                    unresolved_only=unresolved_only))

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _on_mark_resolved(self) -> None:
        if self._engine is None:
            return
        rows = self._tbl_mm.selectedItems()
        if not rows:
            return
        selected_row = self._tbl_mm.currentRow()
        order_id = self._tbl_mm.item(selected_row, 0)
        if order_id:
            self._engine.mark_order_resolved(order_id.text())
            self.refresh()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _refresh_orders(self, orders: list) -> None:
        self._tbl_orders.setRowCount(0)
        for snap in orders:
            row = self._tbl_orders.rowCount()
            self._tbl_orders.insertRow(row)
            sc = _SYNC_COLOR.get(snap.sync_state.value, _MUT)
            self._tbl_orders.setItem(row, 0, _item(snap.order_id,         _MUT))
            self._tbl_orders.setItem(row, 1, _item(snap.symbol,           _FG))
            self._tbl_orders.setItem(row, 2, _item(snap.direction,        _FG))
            self._tbl_orders.setItem(row, 3, _item(snap.volume,           _FG))
            self._tbl_orders.setItem(row, 4, _item(snap.traded,           _FG))
            self._tbl_orders.setItem(row, 5, _item(snap.local_status,     _BLU))
            self._tbl_orders.setItem(row, 6, _item(snap.sync_state.value, sc))
            self._tbl_orders.setItem(row, 7, _item(str(snap.updated_at)[:19], _MUT))

    def _refresh_mismatches(self, records: list) -> None:
        self._tbl_mm.setRowCount(0)
        for rec in reversed(records):
            row = self._tbl_mm.rowCount()
            self._tbl_mm.insertRow(row)
            ac    = _ACTION_COLOR.get(rec.action.value, _MUT)
            res_c = _GRN if rec.resolved else _RED
            self._tbl_mm.setItem(row, 0, _item(rec.order_id,         _MUT))
            self._tbl_mm.setItem(row, 1, _item(rec.local_status,     _BLU))
            self._tbl_mm.setItem(row, 2, _item(rec.exchange_status,  _ORG))
            self._tbl_mm.setItem(row, 3, _item(rec.action.value,     ac))
            self._tbl_mm.setItem(row, 4, _item("YES" if rec.resolved else "NO", res_c))
            self._tbl_mm.setItem(row, 5, _item(str(rec.detected_at)[:19], _MUT))
            self._tbl_mm.setItem(row, 6, _item_left(rec.detail or "---",  _MUT))
