"""
ui/result_table.py

ResultTableWidget  —  批量回测结果表格（ColumnManager 驱动）

设计约定：
- 所有列定义来自 ColumnManager.get_visible_columns()，动态响应用户配置
- 接收 BatchBacktestResult（强类型），不再接收 BacktestResult
- 颜色规则由 ColumnDefinition.color_rule 驱动，_render_cell() 统一处理
- 预留字段（值为 None）显示 "-"
- 右键菜单导出 CSV 使用 ExportScope.VISIBLE，与当前显示列完全一致
- 新增列：只需在 COLUMN_REGISTRY 加一行，此文件无需修改
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtCore, QtGui, QtWidgets

from ..base import EVENT_BATCH_RESULT
from ..batch_result import BatchBacktestResult

if TYPE_CHECKING:
    from ..column_manager import ColumnManager
    from ..column_definition import ColumnDefinition


# ──────────────────────────────────────────────────── #
#  颜色常量
# ──────────────────────────────────────────────────── #

_TEXT_WHITE  = QtGui.QColor("#FFFFFF")
_COLOR_POS   = QtGui.QColor("#4CFF82")
_COLOR_NEG   = QtGui.QColor("#FF5555")
_COLOR_WARN  = QtGui.QColor("#FFA500")

_BG_SUCCESS  = QtGui.QColor("#1A6B3A")
_BG_FAILED   = QtGui.QColor("#7A1F1F")
_BG_SKIPPED  = QtGui.QColor("#5A5A20")
_BG_DEFAULT  = QtGui.QColor("#2D2D2D")

_NEG_BAD_RED  = {"max_ddpercent": -20.0, "annual_volatility": 40.0}
_NEG_BAD_WARN = {"max_ddpercent": -10.0, "annual_volatility": 20.0}


def _row_bg(status: str) -> QtGui.QColor:
    if status == "success": return _BG_SUCCESS
    if status == "failed":  return _BG_FAILED
    if status == "skipped": return _BG_SKIPPED
    return _BG_DEFAULT


def _pnl_fg(val: Any) -> QtGui.QColor:
    try:
        f = float(val)
        if f > 0: return _COLOR_POS
        if f < 0: return _COLOR_NEG
    except (TypeError, ValueError):
        pass
    return _TEXT_WHITE


def _neg_bad_fg(field: str, val: Any) -> QtGui.QColor:
    try:
        f = float(val)
        red_thresh  = _NEG_BAD_RED.get(field, -20.0)
        warn_thresh = _NEG_BAD_WARN.get(field, -10.0)
        if field == "annual_volatility":
            if f >= abs(red_thresh):  return _COLOR_NEG
            if f >= abs(warn_thresh): return _COLOR_WARN
        else:
            if f <= red_thresh:  return _COLOR_NEG
            if f <= warn_thresh: return _COLOR_WARN
    except (TypeError, ValueError):
        pass
    return _TEXT_WHITE


def _format_val(val: Any, col: "ColumnDefinition") -> str:
    """把原始值按列 fmt 格式化为显示字符串。None → '-'。"""
    if val is None:
        return "-"
    try:
        fmt = col.fmt
        if fmt == "pct":    return f"{float(val):.2f}"
        if fmt == "float1": return f"{float(val):.1f}"
        if fmt == "float2": return f"{float(val):.2f}"
        if fmt == "float3": return f"{float(val):.3f}"
        if fmt == "int":    return str(int(float(val)))
        if fmt == "money":  return f"{float(val):,.0f}"
        return str(val)
    except (TypeError, ValueError):
        return str(val)


# ──────────────────────────────────────────────────── #
#  _SortableItem
# ──────────────────────────────────────────────────── #

class _SortableItem(QtWidgets.QTableWidgetItem):
    """数值感知排序单元格，"-" 排末尾。"""

    def __init__(self, display: str, raw: Any) -> None:
        super().__init__(display)
        self._raw = raw

    def __lt__(self, other: QtWidgets.QTableWidgetItem) -> bool:
        if self.text() == "-": return False
        if isinstance(other, _SortableItem) and other.text() == "-": return True
        if isinstance(other, _SortableItem):
            try:
                return float(self._raw or 0) < float(other._raw or 0)
            except (TypeError, ValueError):
                pass
        return (self.text() or "") < (other.text() or "")


# ──────────────────────────────────────────────────── #
#  ResultTableWidget
# ──────────────────────────────────────────────────── #

class ResultTableWidget(QtWidgets.QTableWidget):
    """
    实时更新的批量回测结果表格。

    列定义动态来自 ColumnManager，用户通过列设置对话框调整后，
    表格自动重建列头并用已有结果重新渲染。
    """

    signal_result: QtCore.Signal = QtCore.Signal(Event)

    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
        column_manager: "ColumnManager",
    ) -> None:
        super().__init__()
        self.main_engine    = main_engine
        self.event_engine   = event_engine
        self._column_manager = column_manager
        self._results: list[BatchBacktestResult] = []

        self._init_table()
        self._init_menu()
        self._register_event()

        # 监听列管理变更，自动重建
        self._column_manager.register_on_change(self._on_columns_changed)

    # ── 初始化 ────────────────────────────────────── #

    def _init_table(self) -> None:
        cols = self._column_manager.get_visible_columns()
        self.setColumnCount(len(cols))
        self.setHorizontalHeaderLabels([c.header for c in cols])
        for i, col in enumerate(cols):
            self.setColumnWidth(i, col.width)
            hdr = self.horizontalHeaderItem(i)
            if hdr and col.tooltip:
                hdr.setToolTip(col.tooltip)

        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(False)
        self.setSortingEnabled(False)
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setDefaultSectionSize(28)

        # 表头右键菜单
        self.horizontalHeader().setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.horizontalHeader().customContextMenuRequested.connect(
            self._show_header_menu
        )

        font = QtGui.QFont("Microsoft YaHei", 10)
        self.setFont(font)
        hdr_font = QtGui.QFont("Microsoft YaHei", 10, QtGui.QFont.Weight.Bold)
        self.horizontalHeader().setFont(hdr_font)
        self.horizontalHeader().setStyleSheet(
            "QHeaderView::section {"
            "  background-color: #1E3A5F;"
            "  color: #FFFFFF;"
            "  padding: 4px;"
            "  border: 1px solid #2A4A7F;"
            "  font-weight: bold;"
            "}"
        )
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
        self.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._menu = QtWidgets.QMenu(self)

        copy_action = QtGui.QAction("复制选中行", self)
        copy_action.triggered.connect(self._copy_selected)
        self._menu.addAction(copy_action)

        save_action = QtGui.QAction("导出 CSV（当前显示列）…", self)
        save_action.triggered.connect(self._save_csv)
        self._menu.addAction(save_action)

    def _register_event(self) -> None:
        self.signal_result.connect(self._on_result_event)
        self.event_engine.register(EVENT_BATCH_RESULT, self.signal_result.emit)

    # ── 公开 API ─────────────────────────────────── #

    def clear_results(self) -> None:
        self.setSortingEnabled(False)
        self.setRowCount(0)
        self._results.clear()

    def enable_sorting(self) -> None:
        self.setSortingEnabled(True)

    def get_results(self) -> list[BatchBacktestResult]:
        return list(self._results)

    def get_selected_result(self) -> BatchBacktestResult | None:
        row = self.currentRow()
        sym_item = self.item(row, 0)
        if sym_item:
            sym = sym_item.text()
            for r in self._results:
                if r.vt_symbol == sym:
                    return r
        return None

    def refresh_all_rows(self) -> None:
        """重新渲染所有行（因子分析写回字段后调用）。"""
        current_results = list(self._results)
        self.clear_results()
        for r in current_results:
            self._insert_row(r)

    # ── 列管理变更回调 ───────────────────────────── #

    def _on_columns_changed(self) -> None:
        """ColumnManager 发出变更通知时重建列头并重绘所有行。"""
        self.setSortingEnabled(False)
        cols = self._column_manager.get_visible_columns()
        self.setColumnCount(len(cols))
        self.setHorizontalHeaderLabels([c.header for c in cols])
        for i, col in enumerate(cols):
            self.setColumnWidth(i, col.width)
            hdr = self.horizontalHeaderItem(i)
            if hdr and col.tooltip:
                hdr.setToolTip(col.tooltip)
        # 重绘所有行
        self.setRowCount(0)
        for r in self._results:
            self._insert_row_internal(r)

    # ── 事件处理 ─────────────────────────────────── #

    def _on_result_event(self, event: Event) -> None:
        result = event.data
        if isinstance(result, BatchBacktestResult):
            self._insert_row(result)

    def _insert_row(self, result: BatchBacktestResult) -> None:
        self._results.append(result)
        self._insert_row_internal(result)
        self.scrollToBottom()

    def _insert_row_internal(self, result: BatchBacktestResult) -> None:
        """把 BatchBacktestResult 插入到表格末尾（不追加到 _results）。"""
        cols = self._column_manager.get_visible_columns()
        row  = self.rowCount()
        self.insertRow(row)
        self.setRowHeight(row, 28)
        bg = _row_bg(result.status)

        for col_idx, col in enumerate(cols):
            raw     = getattr(result, col.key, None)
            display = _format_val(raw, col)

            item = _SortableItem(display, raw)
            item.setBackground(bg)
            item.setForeground(self._fg_color(col, raw, result.status))

            align_flag = (
                QtCore.Qt.AlignmentFlag.AlignRight  if col.align == "right"  else
                QtCore.Qt.AlignmentFlag.AlignLeft   if col.align == "left"   else
                QtCore.Qt.AlignmentFlag.AlignCenter
            )
            item.setTextAlignment(align_flag | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.setItem(row, col_idx, item)

    @staticmethod
    def _fg_color(
        col: "ColumnDefinition",
        raw: Any,
        status: str,
    ) -> QtGui.QColor:
        rule = col.color_rule
        if rule == "pnl":      return _pnl_fg(raw)
        if rule == "neg_bad":  return _neg_bad_fg(col.key, raw)
        if rule == "status":   return _TEXT_WHITE
        return _TEXT_WHITE

    # ── 右键菜单 ─────────────────────────────────── #

    def _show_context_menu(self, pos: QtCore.QPoint) -> None:
        self._menu.exec_(self.mapToGlobal(pos))

    def _show_header_menu(self, pos: QtCore.QPoint) -> None:
        """表头右键：显示列管理菜单。"""
        menu = self._column_manager.build_header_menu(self)
        menu.exec_(self.horizontalHeader().mapToGlobal(pos))

    def _copy_selected(self) -> None:
        rows = self.selectionModel().selectedRows()
        if not rows:
            return
        cols = self._column_manager.get_visible_columns()
        lines = ["\t".join(c.header for c in cols)]
        for index in rows:
            r = index.row()
            lines.append("\t".join(
                self.item(r, c).text() if self.item(r, c) else ""
                for c in range(self.columnCount())
            ))
        QtWidgets.QApplication.clipboard().setText("\n".join(lines))

    def _save_csv(self) -> None:
        """右键导出 CSV：scope=VISIBLE，与当前显示列完全一致。"""
        if not self._results:
            QtWidgets.QMessageBox.information(self, "提示", "暂无结果可导出")
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出结果 CSV", "", "CSV 文件 (*.csv)"
        )
        if not path:
            return

        from ..output.csv_exporter import CSVExporter
        from ..output.exporter import ExportScope
        result = CSVExporter().export(
            self._results, path,
            column_manager=self._column_manager,
            scope=ExportScope.VISIBLE,
            include_summary=False,
        )
        if result.success:
            QtWidgets.QMessageBox.information(self, "导出成功", str(result))
        else:
            QtWidgets.QMessageBox.critical(self, "导出失败", result.error_msg)
