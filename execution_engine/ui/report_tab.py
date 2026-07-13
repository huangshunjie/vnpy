"""
execution_engine/ui/report_tab.py

ReportTab — 执行报告 Tab（Phase 3 实现）。

每笔执行明细：信号价 / 成交价 / 滑点 / 手续费 / 冲击 / 总成本 / 净影响 / 成交率
顶部汇总：执行 PnL 分析卡片
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..model.execution_model import ExecutionRecord, ExecutionStats

_FG  = "#cdd6f4"
_MUT = "#6c7086"
_GRN = "#a6e3a1"
_RED = "#f38ba8"
_YLW = "#f9e2af"
_BLU = "#89b4fa"

_COLS = [
    ("记录ID",    80),
    ("合约",     120),
    ("方向",      55),
    ("信号价",    90),
    ("成交价",    90),
    ("滑点",      80),
    ("滑点%",     70),
    ("手续费",    80),
    ("冲击成本",  80),
    ("总成本",    80),
    ("成本率",    70),
    ("净PnL影响", 90),
    ("成交率",    65),
    ("来源",      70),
]


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    item = QtWidgets.QTableWidgetItem(str(text))
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    item.setForeground(QtGui.QColor(color))
    return item


class ReportTab(QtWidgets.QWidget):
    """执行报告 Tab（Phase 3 实现）。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._records: list[ExecutionRecord] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        layout.addWidget(self._build_pnl_bar())
        layout.addWidget(self._build_table(), stretch=1)

    # ------------------------------------------------------------------ #
    #  构建子区域
    # ------------------------------------------------------------------ #

    def _build_pnl_bar(self) -> QtWidgets.QWidget:
        """顶部执行 PnL 分析卡片。"""
        bar = QtWidgets.QWidget()
        bar.setStyleSheet("background: #181825; border-radius: 4px;")
        bar.setFixedHeight(72)
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(24)

        metrics = [
            ("总执行笔数",  "0",  _FG),
            ("完全成交率",  "—",  _GRN),
            ("平均滑点%",   "—",  _YLW),
            ("平均成本率",  "—",  _RED),
            ("总滑点成本",  "—",  _YLW),
            ("总交易成本",  "—",  _RED),
            ("净PnL影响",   "—",  _RED),
        ]
        self._pnl_lbls: dict[str, QtWidgets.QLabel] = {}
        for label, val, color in metrics:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(1)
            ln = QtWidgets.QLabel(label)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._pnl_lbls[label] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_table(self) -> QtWidgets.QTableWidget:
        self._table = QtWidgets.QTableWidget(0, len(_COLS))
        self._table.setHorizontalHeaderLabels([c[0] for c in _COLS])
        for i, (_, w) in enumerate(_COLS):
            self._table.setColumnWidth(i, w)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setStyleSheet("font-size: 12px;")
        return self._table

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def add_record(self, record: ExecutionRecord) -> None:
        """追加一条执行记录（实时模式）。"""
        self._records.append(record)
        self._append_row(record)
        self._refresh_pnl_bar()

    def refresh_all(
        self,
        records: list[ExecutionRecord],
        stats:   ExecutionStats | None = None,
    ) -> None:
        """全量刷新。"""
        self._table.setRowCount(0)
        self._records = list(records)
        for rec in sorted(records, key=lambda r: r.created_at, reverse=True):
            self._append_row(rec)
        if stats:
            self._update_pnl_from_stats(stats)
        else:
            self._refresh_pnl_bar()

    def clear(self) -> None:
        self._records.clear()
        self._table.setRowCount(0)
        for lbl in self._pnl_lbls.values():
            lbl.setText("—")
        self._pnl_lbls["总执行笔数"].setText("0")

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _append_row(self, rec: ExecutionRecord) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        dir_color  = "#4fc3f7" if rec.direction == "LONG" else "#f38ba8"
        slip_color = _RED if rec.slippage > 0 else _GRN
        net_color  = _RED if rec.net_pnl_impact < 0 else _GRN

        self._table.setItem(row,  0, _item(rec.record_id,                   _MUT))
        self._table.setItem(row,  1, _item(rec.symbol,                       _FG))
        self._table.setItem(row,  2, _item(rec.direction,               dir_color))
        self._table.setItem(row,  3, _item(f"{rec.signal_price:.4f}",        _FG))
        self._table.setItem(row,  4, _item(f"{rec.avg_fill_price:.4f}",      _FG))
        self._table.setItem(row,  5, _item(f"{rec.slippage:.4f}",       slip_color))
        self._table.setItem(row,  6, _item(f"{rec.slippage_pct:.3%}",   slip_color))
        self._table.setItem(row,  7, _item(f"{rec.commission:.4f}",         _BLU))
        self._table.setItem(row,  8, _item(f"{rec.impact_cost:.4f}",        _RED))
        self._table.setItem(row,  9, _item(f"{rec.total_cost:.4f}",         _RED))
        self._table.setItem(row, 10, _item(f"{rec.total_cost_pct:.4%}",     _RED))
        self._table.setItem(row, 11, _item(f"{rec.net_pnl_impact:.4f}", net_color))
        fill_color = _GRN if rec.is_complete else _YLW
        self._table.setItem(row, 12, _item(f"{rec.fill_rate:.1%}",     fill_color))
        self._table.setItem(row, 13, _item(rec.source,                      _MUT))
        self._table.scrollToBottom()

    def _refresh_pnl_bar(self) -> None:
        """从 _records 重新计算顶部 PnL 统计。"""
        recs = self._records
        n = len(recs)
        if n == 0:
            for k, lbl in self._pnl_lbls.items():
                lbl.setText("0" if k == "总执行笔数" else "—")
            return

        filled   = [r for r in recs if r.is_complete]
        avg_slip = sum(r.slippage_pct  for r in recs) / n
        avg_cost = sum(r.total_cost_pct for r in recs) / n
        total_slip_cost = sum(r.slippage_cost for r in recs)
        total_cost      = sum(r.total_cost    for r in recs)
        net_pnl         = sum(r.net_pnl_impact for r in recs)

        self._pnl_lbls["总执行笔数"].setText(str(n))
        self._pnl_lbls["完全成交率"].setText(f"{len(filled)/n:.1%}")
        self._pnl_lbls["平均滑点%" ].setText(f"{avg_slip:.4%}")
        self._pnl_lbls["平均成本率"].setText(f"{avg_cost:.4%}")
        self._pnl_lbls["总滑点成本"].setText(f"{total_slip_cost:.4f}")
        self._pnl_lbls["总交易成本"].setText(f"{total_cost:.4f}")
        self._pnl_lbls["净PnL影响" ].setText(f"{net_pnl:.4f}")

    def _update_pnl_from_stats(self, stats: ExecutionStats) -> None:
        n = stats.total_orders
        if n == 0:
            return
        self._pnl_lbls["总执行笔数"].setText(str(n))
        self._pnl_lbls["完全成交率"].setText(
            f"{stats.filled_orders/n:.1%}" if n else "—"
        )
        self._pnl_lbls["平均滑点%"].setText(f"{stats.avg_slippage_pct:.4%}")
        self._pnl_lbls["总滑点成本"].setText(f"{stats.total_slippage_cost:.4f}")
