"""
execution_engine/ui/order_tab.py

OrderTab — 订单列表 Tab（Phase 2 实现）。

显示所有订单（活跃 + 历史），实时接收 EVENT_ORDER_UPDATE 刷新。
列：订单ID / 合约 / 方向 / 目标量 / 成交量 / 成交率 / 均价 / 状态 / 来源 / 时间
"""

from __future__ import annotations

import math
from datetime import datetime

from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import OrderStatus
from ..model.order_model import Order

_BG  = "#1e1e2e"
_FG  = "#cdd6f4"
_MUT = "#6c7086"

_STATUS_COLORS: dict[str, str] = {
    OrderStatus.CREATED.value:          "#6c7086",
    OrderStatus.SUBMITTED.value:        "#4fc3f7",
    OrderStatus.PARTIALLY_FILLED.value: "#f9e2af",
    OrderStatus.FILLED.value:           "#a6e3a1",
    OrderStatus.CANCELED.value:         "#f38ba8",
    OrderStatus.REJECTED.value:         "#f38ba8",
}

_COLS = [
    ("订单ID",  80),
    ("合约",    120),
    ("方向",    60),
    ("目标量",  70),
    ("成交量",  70),
    ("成交率",  65),
    ("均价",    90),
    ("状态",    110),
    ("来源",    80),
    ("时间",    140),
]


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(str(text))
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    item.setForeground(QtWidgets.QApplication.palette().text())
    from pyqtgraph.Qt import QtGui
    item.setForeground(QtGui.QColor(color))
    return item


class OrderTab(QtWidgets.QWidget):
    """订单列表 Tab（Phase 2 实现）。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._orders: dict[str, Order] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 顶部统计行
        layout.addWidget(self._build_summary_bar())

        # 订单表格
        self._table = QtWidgets.QTableWidget(0, len(_COLS))
        self._table.setHorizontalHeaderLabels([c[0] for c in _COLS])
        hdr = self._table.horizontalHeader()
        for i, (_, w) in enumerate(_COLS):
            self._table.setColumnWidth(i, w)
        hdr.setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setStyleSheet("font-size: 12px;")
        layout.addWidget(self._table)

    def _build_summary_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setStyleSheet("background: #181825; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(8, 4, 8, 4)
        h.setSpacing(16)

        self._lbl_total    = self._metric_lbl("总计", "0")
        self._lbl_active   = self._metric_lbl("活跃", "0")
        self._lbl_filled   = self._metric_lbl("已成交", "0")
        self._lbl_canceled = self._metric_lbl("已取消", "0")

        for col in (self._lbl_total, self._lbl_active,
                    self._lbl_filled, self._lbl_canceled):
            h.addLayout(col[0])
        h.addStretch()

        btn_clear = QtWidgets.QPushButton("清空历史")
        btn_clear.setFixedWidth(80)
        btn_clear.setStyleSheet(
            "QPushButton { background: #313244; color: #cdd6f4;"
            " border-radius: 4px; padding: 3px 8px; font-size: 11px; }"
            "QPushButton:hover { background: #45475a; }"
        )
        btn_clear.clicked.connect(self.clear_history)
        h.addWidget(btn_clear)
        return bar

    @staticmethod
    def _metric_lbl(label: str, value: str):
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(0)
        ln = QtWidgets.QLabel(label)
        ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        lv = QtWidgets.QLabel(value)
        lv.setStyleSheet(f"color: {_FG}; font-size: 14px; font-weight: bold;")
        lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        col.addWidget(ln)
        col.addWidget(lv)
        return col, lv

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_order(self, order: Order) -> None:
        """接收单个订单更新，刷新对应行。"""
        self._orders[order.order_id] = order
        self._refresh_row(order)
        self._refresh_summary()

    def refresh_all(self, orders: list[Order]) -> None:
        """全量刷新（引擎启动后初始化）。"""
        self._table.setRowCount(0)
        self._orders.clear()
        for o in orders:
            self._orders[o.order_id] = o
        for o in sorted(orders, key=lambda x: x.created_at, reverse=True):
            self._append_row(o)
        self._refresh_summary()

    def clear_history(self) -> None:
        """清空历史（终态）订单显示。"""
        to_remove = [
            oid for oid, o in self._orders.items() if o.is_terminal
        ]
        for oid in to_remove:
            del self._orders[oid]
        self._rebuild_table()
        self._refresh_summary()

    def clear(self) -> None:
        self._orders.clear()
        self._table.setRowCount(0)
        self._refresh_summary()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _refresh_row(self, order: Order) -> None:
        """找到已有行更新，或追加新行。"""
        for row in range(self._table.rowCount()):
            if self._table.item(row, 0) and \
               self._table.item(row, 0).text() == order.order_id:
                self._fill_row(row, order)
                return
        self._append_row(order)

    def _append_row(self, order: Order) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._fill_row(row, order)

    def _fill_row(self, row: int, order: Order) -> None:
        color = _STATUS_COLORS.get(order.status.value, _FG)
        dir_color = "#4fc3f7" if order.direction == "LONG" else "#f38ba8"
        fill_rate = order.fill_rate
        self._table.setItem(row, 0, _item(order.order_id, _MUT))
        self._table.setItem(row, 1, _item(order.symbol, _FG))
        self._table.setItem(row, 2, _item(order.direction, dir_color))
        self._table.setItem(row, 3, _item(f"{order.volume:.2f}", _FG))
        self._table.setItem(row, 4, _item(f"{order.filled_volume:.2f}", _FG))
        self._table.setItem(row, 5, _item(f"{fill_rate:.1%}", color))
        avg_px = f"{order.avg_fill_price:.4f}" if order.avg_fill_price > 0 else "—"
        self._table.setItem(row, 6, _item(avg_px, _FG))
        self._table.setItem(row, 7, _item(order.status.value, color))
        self._table.setItem(row, 8, _item(order.source, _MUT))
        ts = order.created_at.strftime("%Y-%m-%d %H:%M:%S")
        self._table.setItem(row, 9, _item(ts, _MUT))

    def _rebuild_table(self) -> None:
        self._table.setRowCount(0)
        for o in sorted(self._orders.values(),
                        key=lambda x: x.created_at, reverse=True):
            self._append_row(o)

    def _refresh_summary(self) -> None:
        orders = list(self._orders.values())
        total    = len(orders)
        active   = sum(1 for o in orders if o.is_active)
        filled   = sum(1 for o in orders if o.status == OrderStatus.FILLED)
        canceled = sum(1 for o in orders
                       if o.status in (OrderStatus.CANCELED, OrderStatus.REJECTED))
        self._lbl_total[1].setText(str(total))
        self._lbl_active[1].setText(str(active))
        self._lbl_filled[1].setText(str(filled))
        self._lbl_canceled[1].setText(str(canceled))
