"""
portfolio_engine/ui/rebalance_tab.py

RebalanceTab — 调仓历史 Tab。

Phase 2 实现：
  - 调仓记录表格（时间 / 槽位 / 调仓前权重 / 调仓后权重 / Delta）
  - 顶部统计摘要（总调仓次数 / 调仓频率）
"""

from __future__ import annotations

from pyqtgraph.Qt import QtCore, QtWidgets

_FG = "#cdd6f4"


class RebalanceTab(QtWidgets.QWidget):
    """调仓历史 Tab（Phase 2 实现）。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # 摘要行
        self._lbl_summary = QtWidgets.QLabel("尚无调仓记录")
        self._lbl_summary.setStyleSheet("color: #6c7086; font-size: 12px;")
        root.addWidget(self._lbl_summary)

        # 主表格
        self._table = QtWidgets.QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["调仓时间", "槽位", "调仓前权重", "调仓后权重", "Delta"]
        )
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet("font-size: 12px;")
        root.addWidget(self._table, stretch=1)

        # 占位提示
        self._placeholder = QtWidgets.QLabel("运行分析后将在此显示调仓历史")
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #6c7086; font-size: 13px;")
        root.addWidget(self._placeholder)

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_rebalance(self, records: list) -> None:
        """
        接收 list[RebalanceRecord]，展开为每槽位一行。
        """
        self._table.setRowCount(0)
        self._placeholder.hide()
        self._table.show()

        total = len(records)
        self._lbl_summary.setText(f"共 {total} 次调仓记录")

        for rec in records:
            all_slots = sorted(
                set(list(rec.prev_weights.keys()) | list(rec.new_weights.keys()))
            )
            dt_str = rec.triggered_at.strftime("%Y-%m-%d")

            for slot_name in all_slots:
                prev = rec.prev_weights.get(slot_name, 0.0)
                new  = rec.new_weights.get(slot_name, 0.0)
                delta = rec.delta.get(slot_name, new - prev)

                row = self._table.rowCount()
                self._table.insertRow(row)
                self._table.setItem(row, 0, _item(dt_str))
                self._table.setItem(row, 1, _item(slot_name))
                self._table.setItem(row, 2, _item(f"{prev:.2%}"))
                self._table.setItem(row, 3, _item(f"{new:.2%}"))

                delta_item = _item(f"{delta:+.2%}")
                if delta > 1e-6:
                    delta_item.setForeground(
                        QtCore.Qt.GlobalColor.green
                    )
                elif delta < -1e-6:
                    delta_item.setForeground(
                        QtCore.Qt.GlobalColor.red
                    )
                self._table.setItem(row, 4, delta_item)

    def clear(self) -> None:
        self._table.setRowCount(0)
        self._lbl_summary.setText("尚无调仓记录")
        self._table.hide()
        self._placeholder.show()


def _item(text: str) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(str(text))
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    return item
