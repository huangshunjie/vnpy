"""
execution_engine/ui/execution_tab.py

ExecutionTab — 执行监控 Tab（Phase 2 实现）。

显示每笔完整执行记录（ExecutionRecord）：
  信号价 / 成交价 / 滑点 / 成交率 / 状态 / 耗时 / 来源

顶部展示汇总统计卡片（ExecutionStats）。
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..model.execution_model import ExecutionRecord, ExecutionStats

_BG  = "#1e1e2e"
_FG  = "#cdd6f4"
_MUT = "#6c7086"
_GRN = "#a6e3a1"
_RED = "#f38ba8"
_YLW = "#f9e2af"

_COLS = [
    ("记录ID",   80),
    ("合约",    120),
    ("方向",     60),
    ("信号价",   90),
    ("成交价",   90),
    ("滑点",     80),
    ("滑点%",    70),
    ("成交率",   65),
    ("状态",    110),
    ("成交笔数",  70),
    ("来源",     80),
    ("耗时(ms)", 80),
]


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    item = QtWidgets.QTableWidgetItem(str(text))
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    item.setForeground(QtGui.QColor(color))
    return item


class ExecutionTab(QtWidgets.QWidget):
    """执行监控 Tab（Phase 2 实现）。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._records: list[ExecutionRecord] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        layout.addWidget(self._build_stats_bar())
        layout.addWidget(self._build_table())

    def _build_stats_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setStyleSheet("background: #181825; border-radius: 4px;")
        bar.setFixedHeight(64)
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(24)

        metrics = [
            ("总执行", "0",    _FG),
            ("完全成交", "0",  _GRN),
            ("部分成交", "0",  _YLW),
            ("平均成交率", "—", _FG),
            ("平均滑点%", "—", _YLW),
            ("总滑点成本", "—", _RED),
            ("平均耗时ms", "—", _FG),
        ]
        self._stat_lbls: dict[str, QtWidgets.QLabel] = {}
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
            self._stat_lbls[label] = lv
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

    def refresh_all(self, records: list[ExecutionRecord]) -> None:
        """全量刷新（引擎启动后初始化）。"""
        self._table.setRowCount(0)
        self._records = list(records)
        for rec in sorted(records, key=lambda r: r.created_at, reverse=True):
            self._append_row(rec)

    def update_stats(self, stats: ExecutionStats) -> None:
        """刷新顶部统计卡片。"""
        self._stat_lbls["总执行"].setText(str(stats.total_orders))
        self._stat_lbls["完全成交"].setText(str(stats.filled_orders))
        self._stat_lbls["部分成交"].setText(str(stats.partial_orders))
        self._stat_lbls["平均成交率"].setText(
            f"{stats.avg_fill_rate:.1%}" if stats.total_orders else "—"
        )
        self._stat_lbls["平均滑点%"].setText(
            f"{stats.avg_slippage_pct:.3%}" if stats.total_orders else "—"
        )
        self._stat_lbls["总滑点成本"].setText(
            f"{stats.total_slippage_cost:.4f}" if stats.total_orders else "—"
        )
        self._stat_lbls["平均耗时ms"].setText(
            f"{stats.avg_delay_ms:.1f}" if stats.total_orders else "—"
        )

    def clear(self) -> None:
        self._records.clear()
        self._table.setRowCount(0)

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _append_row(self, rec: ExecutionRecord) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        dir_color = "#4fc3f7" if rec.direction == "LONG" else "#f38ba8"
        slip_color = _RED if rec.slippage > 0 else _GRN

        delay = rec.execution_delay_ms
        delay_str = f"{delay:.1f}" if delay == delay else "—"  # NaN check

        self._table.setItem(row,  0, _item(rec.record_id, _MUT))
        self._table.setItem(row,  1, _item(rec.symbol, _FG))
        self._table.setItem(row,  2, _item(rec.direction, dir_color))
        self._table.setItem(row,  3, _item(f"{rec.signal_price:.4f}", _FG))
        self._table.setItem(row,  4, _item(f"{rec.avg_fill_price:.4f}", _FG))
        self._table.setItem(row,  5, _item(f"{rec.slippage:.4f}", slip_color))
        self._table.setItem(row,  6, _item(f"{rec.slippage_pct:.3%}", slip_color))
        self._table.setItem(row,  7, _item(f"{rec.fill_rate:.1%}", _GRN if rec.is_complete else _YLW))
        self._table.setItem(row,  8, _item(rec.final_status, _GRN if rec.final_status == "filled" else _MUT))
        self._table.setItem(row,  9, _item(str(rec.fill_count), _FG))
        self._table.setItem(row, 10, _item(rec.source, _MUT))
        self._table.setItem(row, 11, _item(delay_str, _FG))

        self._table.scrollToBottom()
