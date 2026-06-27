"""
ui/result_table.py

回测结果表格 Widget — 实时接收 EVENT_BATCH_RESULT 事件，
逐行追加结果，支持点击列头排序、右键菜单导出 CSV。
"""

from __future__ import annotations

from typing import Any

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtCore, QtGui, QtWidgets

from ..base import EVENT_BATCH_RESULT
from ..task import BacktestResult, TaskStatus

_COLUMNS: list[tuple[str, str, int, Any]] = [
    ("股票代码",  "vt_symbol",        110, str),
    ("状态",      "status",            60, lambda v: v.value if hasattr(v, "value") else str(v)),
    ("总收益%",   "total_return",      80, lambda v: f"{v:.2f}"),
    ("年化收益%", "annual_return",     80, lambda v: f"{v:.2f}"),
    ("夏普比率",  "sharpe_ratio",      80, lambda v: f"{v:.3f}"),
    ("最大回撤%", "max_ddpercent",     80, lambda v: f"{v:.2f}"),
    ("卡玛比率",  "calmar_ratio",      80, lambda v: f"{v:.3f}"),
    ("交易次数",  "total_trade_count", 70, lambda v: str(int(v)) if v else "0"),
    ("耗时(s)",   "elapsed_seconds",   70, lambda v: f"{v:.2f}" if v else "-"),
]

COLOR_SUCCESS = QtGui.QColor("#d6f5d6")
COLOR_FAILED  = QtGui.QColor("#ffd6d6")
COLOR_SKIPPED = QtGui.QColor("#f5f5d6")
COLOR_DEFAULT = QtGui.QColor("white")


class ResultTableWidget(QtWidgets.QTableWidget):
    """
    Live-updating result table.

    插入行时始终关闭排序（setSortingEnabled(False)），
    回测全部完成后由外部调用 enable_sorting() 重新开启。
    这样避免了 PySide6 里 setSortingEnabled(True) 触发
    _SortableItem.__lt__ 递归的问题。
    """

    signal_result: QtCore.Signal = QtCore.Signal(Event)

    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__()

        self.main_engine = main_engine
        self.event_engine = event_engine
        self._results: list[BacktestResult] = []

        self._init_table()
        self._init_menu()
        self._register_event()

    # ------------------------------------------------------------------ #
    #  Initialisation
    # ------------------------------------------------------------------ #

    def _init_table(self) -> None:
        self.setColumnCount(len(_COLUMNS))
        self.setHorizontalHeaderLabels([c[0] for c in _COLUMNS])

        for col, (_, _, width, _) in enumerate(_COLUMNS):
            self.setColumnWidth(col, width)

        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(False)
        # Keep sorting OFF during live insertion; user can click header to sort
        # after run finishes, or call enable_sorting() explicitly.
        self.setSortingEnabled(False)
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)
        self.horizontalHeader().setStretchLastSection(True)

    def _init_menu(self) -> None:
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._menu = QtWidgets.QMenu(self)

        copy_action = QtGui.QAction("复制选中行", self)
        copy_action.triggered.connect(self._copy_selected)
        self._menu.addAction(copy_action)

        save_action = QtGui.QAction("导出 CSV…", self)
        save_action.triggered.connect(self._save_csv)
        self._menu.addAction(save_action)

    def _register_event(self) -> None:
        self.signal_result.connect(self._on_result_event)
        self.event_engine.register(EVENT_BATCH_RESULT, self.signal_result.emit)

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def clear_results(self) -> None:
        self.setSortingEnabled(False)
        self.setRowCount(0)
        self._results.clear()

    def enable_sorting(self) -> None:
        """Call this after all rows have been inserted to enable header sorting."""
        self.setSortingEnabled(True)

    def get_results(self) -> list[BacktestResult]:
        return list(self._results)

    def get_selected_result(self) -> BacktestResult | None:
        row = self.currentRow()
        sym_item = self.item(row, 0)
        if sym_item:
            sym = sym_item.text()
            for r in self._results:
                if r.vt_symbol == sym:
                    return r
        return None

    # ------------------------------------------------------------------ #
    #  Event handling
    # ------------------------------------------------------------------ #

    def _on_result_event(self, event: Event) -> None:
        self._insert_row(event.data)

    def _insert_row(self, result: BacktestResult) -> None:
        self._results.append(result)

        # Sorting must stay OFF while inserting rows.
        # Never call setSortingEnabled(True) here — that triggers a full
        # table re-sort which calls _SortableItem.__lt__, and in PySide6
        # that causes infinite recursion via the C++ override mechanism.
        row = self.rowCount()
        self.insertRow(row)

        if result.status == TaskStatus.SUCCESS:
            bg = COLOR_SUCCESS
        elif result.status == TaskStatus.FAILED:
            bg = COLOR_FAILED
        elif result.status == TaskStatus.SKIPPED:
            bg = COLOR_SKIPPED
        else:
            bg = COLOR_DEFAULT

        for col, (_, attr, _, fmt_fn) in enumerate(_COLUMNS):
            raw_val = getattr(result, attr, None)

            if raw_val is None and result.statistics:
                raw_val = result.statistics.get(attr, None)

            if attr == "calmar_ratio" and result.statistics:
                mdd = abs(result.max_ddpercent)
                raw_val = result.annual_return / mdd if mdd > 0 else 0.0

            display = fmt_fn(raw_val) if raw_val is not None else "-"

            item = _SortableItem(display, raw_val)
            item.setBackground(bg)
            self.setItem(row, col, item)

        self.scrollToBottom()

    # ------------------------------------------------------------------ #
    #  Context menu actions
    # ------------------------------------------------------------------ #

    def _show_context_menu(self, pos: QtCore.QPoint) -> None:
        self._menu.exec_(self.mapToGlobal(pos))

    def _copy_selected(self) -> None:
        rows = self.selectionModel().selectedRows()
        if not rows:
            return
        lines: list[str] = []
        lines.append("\t".join(c[0] for c in _COLUMNS))
        for index in rows:
            r = index.row()
            lines.append("\t".join(
                self.item(r, c).text() if self.item(r, c) else ""
                for c in range(self.columnCount())
            ))
        QtWidgets.QApplication.clipboard().setText("\n".join(lines))

    def _save_csv(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出结果 CSV", "", "CSV 文件 (*.csv)"
        )
        if not path:
            return
        try:
            import csv
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([c[0] for c in _COLUMNS])
                for row in range(self.rowCount()):
                    writer.writerow(
                        self.item(row, c).text() if self.item(row, c) else ""
                        for c in range(self.columnCount())
                    )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "导出失败", str(e))


class _SortableItem(QtWidgets.QTableWidgetItem):
    """
    Numeric-aware sortable table item.

    __lt__ compares raw numeric values when available, falls back to
    plain text comparison. Never calls super().__lt__() because in
    PySide6 that re-enters the Python override and causes recursion.
    """

    def __init__(self, display: str, raw_val: Any) -> None:
        super().__init__(display)
        self.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._raw: Any = raw_val

    def __lt__(self, other: "QtWidgets.QTableWidgetItem") -> bool:
        if isinstance(other, _SortableItem):
            try:
                return float(self._raw or 0) < float(other._raw or 0)
            except (TypeError, ValueError):
                pass
        # Plain text fallback — no super().__lt__() to avoid PySide6 recursion
        return (self.text() or "") < (other.text() or "")
