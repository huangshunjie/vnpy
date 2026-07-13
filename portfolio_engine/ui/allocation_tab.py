"""
portfolio_engine/ui/allocation_tab.py

AllocationTab — 权重分配 Tab。

Phase 2 实现：
  - 左侧：权重分配条形图（各槽位）
  - 右侧：权重明细表格（槽位 / 方法 / 权重 / 波动率 / 风险贡献）
"""

from __future__ import annotations

import math

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

_BG     = "#1e1e2e"
_FG     = "#cdd6f4"
_COLORS = [
    "#4fc3f7", "#a6e3a1", "#f38ba8", "#fab387",
    "#cba6f7", "#f9e2af", "#89dceb", "#b4befe",
]


class AllocationTab(QtWidgets.QWidget):
    """权重分配 Tab（Phase 2 实现）。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(6)

        # 左：条形图
        self._glw = pg.GraphicsLayoutWidget()
        self._glw.setBackground(_BG)
        root.addWidget(self._glw, stretch=3)

        self._bar_plot = self._glw.addPlot(title="策略槽位权重")
        self._bar_plot.setLabel("left", "权重")
        self._bar_plot.showGrid(y=True, alpha=0.2)
        self._bar_plot.setYRange(0, 1)

        # 右：明细表格
        right = QtWidgets.QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)

        title = QtWidgets.QLabel("权重明细")
        title.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: bold;")
        right.addWidget(title)

        self._table = QtWidgets.QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["槽位", "权重", "方法", "波动率", "风险贡献"]
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.setStyleSheet("font-size: 12px;")
        right.addWidget(self._table, stretch=1)

        root.addLayout(right, stretch=2)

        # 占位
        self._placeholder = QtWidgets.QLabel("运行分析后将在此显示权重分配")
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #6c7086; font-size: 13px;")
        root.addWidget(self._placeholder)

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_allocation(self, result) -> None:
        """接收 AllocationResult，刷新图表和表格。"""
        self._placeholder.hide()

        weights    = result.weights
        vols       = getattr(result, "volatilities",  {}) or {}
        risk_contribs = getattr(result, "risk_contribs", {}) or {}
        method_str = result.method.value

        names   = list(weights.keys())
        values  = [weights[n] for n in names]
        n       = len(names)

        # ── 条形图 ─────────────────────────────────────────────────────
        self._bar_plot.clear()
        bar_colors = [_COLORS[i % len(_COLORS)] for i in range(n)]

        bar_item = pg.BarGraphItem(
            x=list(range(n)),
            height=values,
            width=0.6,
            brushes=[pg.mkBrush(c) for c in bar_colors],
        )
        self._bar_plot.addItem(bar_item)

        ax = self._bar_plot.getAxis("bottom")
        ax.setTicks([[(i, names[i]) for i in range(n)]])
        self._bar_plot.setXRange(-0.5, n - 0.5)
        self._bar_plot.setYRange(0, max(values) * 1.2 if values else 1)

        # ── 表格 ───────────────────────────────────────────────────────
        self._table.setRowCount(0)
        for i, name in enumerate(names):
            row = self._table.rowCount()
            self._table.insertRow(row)

            w   = weights.get(name, 0.0)
            vol = vols.get(name, float("nan"))
            rc  = risk_contribs.get(name, float("nan"))

            self._table.setItem(row, 0, _item(name))
            self._table.setItem(row, 1, _item(f"{w:.2%}"))
            self._table.setItem(row, 2, _item(method_str))
            self._table.setItem(row, 3, _item(
                f"{vol:.2%}" if not math.isnan(vol) else "—"
            ))
            self._table.setItem(row, 4, _item(
                f"{rc:.4f}" if not math.isnan(rc) else "—"
            ))

        self._glw.show()
        self._table.show()

    def clear(self) -> None:
        self._bar_plot.clear()
        self._table.setRowCount(0)
        self._glw.hide()
        self._table.hide()
        self._placeholder.show()


def _item(text: str) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(str(text))
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    return item
