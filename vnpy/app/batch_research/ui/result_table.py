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
    ("股票代码",  "vt_symbol",        120, str),
    ("状态",      "status",            70, lambda v: v.value if hasattr(v, "value") else str(v)),
    ("总收益%",   "total_return",      90, lambda v: f"{v:.2f}"),
    ("年化收益%", "annual_return",     90, lambda v: f"{v:.2f}"),
    ("夏普比率",  "sharpe_ratio",      90, lambda v: f"{v:.3f}"),
    ("最大回撤%", "max_ddpercent",     90, lambda v: f"{v:.2f}"),
    ("卡玛比率",  "calmar_ratio",      90, lambda v: f"{v:.3f}"),
    ("交易次数",  "total_trade_count", 80, lambda v: str(int(v)) if v else "0"),
    ("耗时(s)",   "elapsed_seconds",   80, lambda v: f"{v:.2f}" if v else "-"),
]

# ------------------------------------------------------------------ #
#  行颜色方案：深色文字 + 高对比度背景，在深色主题下清晰可读
# ------------------------------------------------------------------ #
# 每种状态：(背景色, 前景文字色)
_TEXT_COLOR   = QtGui.QColor("#FFFFFF")         # 白色文字
_BG_SUCCESS   = QtGui.QColor("#1A6B3A")         # 深绿
_BG_FAILED    = QtGui.QColor("#7A1F1F")         # 深红
_BG_SKIPPED   = QtGui.QColor("#5A5A20")         # 深黄
_BG_DEFAULT   = QtGui.QColor("#2D2D2D")         # 深灰（兜底）

# 盈亏高亮：正值用亮绿色文字，负值用亮红色文字
_COLOR_POS    = QtGui.QColor("#4CFF82")         # 亮绿
_COLOR_NEG    = QtGui.QColor("#FF5555")         # 亮红
_COLOR_NORMAL = QtGui.QColor("#FFFFFF")         # 普通白


def _pnl_color(val: Any) -> QtGui.QColor:
    """Return green/red/white for positive/negative/zero numeric values."""
    try:
        f = float(val)
        if f > 0:
            return _COLOR_POS
        if f < 0:
            return _COLOR_NEG
    except (TypeError, ValueError):
        pass
    return _COLOR_NORMAL


# Columns where we want positive=green / negative=red colouring
_PNL_COLS = {"total_return", "annual_return", "sharpe_ratio",
             "calmar_ratio", "return_drawdown_ratio"}
# max_ddpercent is negative-is-bad but value itself is already negative
_NEG_COLS = {"max_ddpercent"}


class ResultTableWidget(QtWidgets.QTableWidget):
    """
    Live-updating result table.

    Sorting stays OFF during live insertion (avoids PySide6 recursion bug).
    Call enable_sorting() after all rows are inserted.
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
        self.setSortingEnabled(False)
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)
        self.horizontalHeader().setStretchLastSection(True)

        # Row height
        self.verticalHeader().setDefaultSectionSize(28)

        # Table-level font
        font = QtGui.QFont("Microsoft YaHei", 10)
        self.setFont(font)

        # Header style: bold, larger, high-contrast
        hdr_font = QtGui.QFont("Microsoft YaHei", 10, QtGui.QFont.Weight.Bold)
        self.horizontalHeader().setFont(hdr_font)
        self.horizontalHeader().setStyleSheet(
            "QHeaderView::section {"
            "  background-color: #1E3A5F;"   # 深蓝
            "  color: #FFFFFF;"
            "  padding: 4px;"
            "  border: 1px solid #2A4A7F;"
            "  font-weight: bold;"
            "}"
        )

        # Overall table stylesheet: grid lines visible, selection highlight
        self.setStyleSheet(
            "QTableWidget {"
            "  background-color: #1E1E1E;"
            "  gridline-color: #3A3A3A;"
            "  color: #FFFFFF;"
            "  selection-background-color: #2A5298;"
            "  selection-color: #FFFFFF;"
            "}"
            "QTableWidget::item {"
            "  padding: 2px 6px;"
            "  border-bottom: 1px solid #2A2A2A;"
            "}"
        )

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

        row = self.rowCount()
        self.insertRow(row)
        self.setRowHeight(row, 28)

        # Background colour by status
        if result.status == TaskStatus.SUCCESS:
            bg = _BG_SUCCESS
        elif result.status == TaskStatus.FAILED:
            bg = _BG_FAILED
        elif result.status == TaskStatus.SKIPPED:
            bg = _BG_SKIPPED
        else:
            bg = _BG_DEFAULT

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

            # Text colour: P&L columns get green/red, others white
            if attr in _PNL_COLS:
                item.setForeground(_pnl_color(raw_val))
            elif attr in _NEG_COLS:
                # max_ddpercent: negative value = bad (red), near-zero = ok
                item.setForeground(_pnl_color(-(raw_val or 0)))
            else:
                item.setForeground(_TEXT_COLOR)

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
    Numeric-aware sortable item. Never calls super().__lt__() to
    avoid PySide6 C++ override recursion.
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
        return (self.text() or "") < (other.text() or "")
