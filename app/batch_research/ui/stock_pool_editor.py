"""
ui/stock_pool_editor.py

StockPoolEditor -- embeddable stock list editor widget.
"""
from __future__ import annotations
from typing import Callable
from vnpy.trader.ui import QtCore, QtGui, QtWidgets
from ..utils.symbol_parser import SymbolParser

_STYLE_TABLE = """
QTableWidget {
    background-color: #1E1E1E; gridline-color: #3A3A3A;
    color: #FFFFFF; font-size: 13px;
    selection-background-color: #2A5298; selection-color: #FFFFFF;
    border: 1px solid #3A3A3A;
}
QTableWidget::item { padding: 3px 8px; border-bottom: 1px solid #2A2A2A; }
QHeaderView::section {
    background-color: #1E3A5F; color: #FFFFFF;
    padding: 4px; border: 1px solid #2A4A7F; font-weight: bold;
}
"""
_STYLE_COUNTER = "color: #AAAAAA; font-size: 12px; padding: 2px 4px;"
_STYLE_HINT    = "color: #888888; font-size: 11px;"
_COL_IDX    = 0
_COL_SYMBOL = 1


class StockPoolEditor(QtWidgets.QWidget):
    """Embeddable stock-pool editor.

    Signals:
        symbols_changed(list[str]): emitted whenever the list changes.
    """

    symbols_changed: QtCore.Signal = QtCore.Signal(list)

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        name_resolver: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._parser        = SymbolParser()
        self._name_resolver = name_resolver or (lambda _: "")
        self._init_ui()
        self._init_menu()

    # ---- public API ----------------------------------------

    def get_symbols(self) -> list[str]:
        """Return current vt_symbol list (preserving display order)."""
        result: list[str] = []
        for row in range(self._table.rowCount()):
            item = self._table.item(row, _COL_SYMBOL)
            if item:
                result.append(item.text())
        return result

    def set_symbols(self, symbols: list[str]) -> None:
        """Replace the entire list (auto de-duplicates)."""
        normalized = self._parser.parse("\n".join(symbols))
        self._load_rows(normalized)

    def add_symbols(self, symbols: list[str]) -> int:
        """Append, skipping duplicates. Returns count added."""
        existing = set(self.get_symbols())
        new_ones = [s for s in symbols if s not in existing]
        if new_ones:
            self._load_rows(self.get_symbols() + new_ones)
        return len(new_ones)

    def clear(self) -> None:
        """Clear all symbols."""
        self._table.setRowCount(0)
        self._update_counter()
        self.symbols_changed.emit([])

    def count(self) -> int:
        """Current symbol count."""
        return self._table.rowCount()

    # ---- UI construction ----------------------------------

    def _init_ui(self) -> None:
        self._input_edit = QtWidgets.QLineEdit()
        self._input_edit.setPlaceholderText(
            "输入代码后按 Enter 添加，支持逗号/空格分隔多个"
        )
        self._input_edit.returnPressed.connect(self._on_input_enter)

        btn_paste = QtWidgets.QPushButton("粘贴")
        btn_sort  = QtWidgets.QPushButton("排序")
        btn_dedup = QtWidgets.QPushButton("去重")
        btn_clear = QtWidgets.QPushButton("清空")
        btn_paste.setToolTip("从剪贴板批量粘贴（Excel/CSV/同花顺/Tushare）")
        btn_paste.clicked.connect(self._on_paste_clipboard)
        btn_sort.clicked.connect(self._on_sort)
        btn_dedup.clicked.connect(self._on_dedup)
        btn_clear.clicked.connect(self._on_clear)

        toolbar = QtWidgets.QHBoxLayout()
        toolbar.setSpacing(6)
        toolbar.addWidget(self._input_edit, 1)
        for btn in (btn_paste, btn_sort, btn_dedup, btn_clear):
            toolbar.addWidget(btn)

        self._table = QtWidgets.QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["序号", "股票代码 (vt_symbol)"])
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(_COL_IDX,    QtWidgets.QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(_COL_SYMBOL, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(_COL_IDX, 52)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setStyleSheet(_STYLE_TABLE)
        self._table.setAlternatingRowColors(False)
        self._table.verticalHeader().setDefaultSectionSize(26)
        self._table.doubleClicked.connect(self._on_double_click)
        self._table.keyPressEvent = self._table_key_press  # type: ignore

        self._counter_label = QtWidgets.QLabel("共 0 只股票")
        self._counter_label.setStyleSheet(_STYLE_COUNTER)
        hint = QtWidgets.QLabel(
            "提示：可直接粘贴 Excel/CSV/同花顺/Tushare；双击行可删除"
        )
        hint.setStyleSheet(_STYLE_HINT)

        status_row = QtWidgets.QHBoxLayout()
        status_row.addWidget(self._counter_label)
        status_row.addStretch()
        status_row.addWidget(hint)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(6)
        vbox.addLayout(toolbar)
        vbox.addWidget(self._table, 1)
        vbox.addLayout(status_row)

    def _init_menu(self) -> None:
        self._table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._ctx_menu = QtWidgets.QMenu(self)
        for label, slot, sc in [
            ("删除选中",             self._delete_selected, "Delete"),
            ("复制选中代码", self._copy_selected,   "Ctrl+C"),
        ]:
            act = QtGui.QAction(label, self)
            if sc:
                act.setShortcut(sc)
            act.triggered.connect(slot)
            self._ctx_menu.addAction(act)
        self._ctx_menu.addSeparator()
        act_all = QtGui.QAction("全选", self)
        act_all.setShortcut("Ctrl+A")
        act_all.triggered.connect(self._table.selectAll)
        self._ctx_menu.addAction(act_all)
        self._ctx_menu.addSeparator()
        act_clr = QtGui.QAction("清空全部", self)
        act_clr.triggered.connect(self._on_clear)
        self._ctx_menu.addAction(act_clr)

    # ---- internal helpers ----------------------------------

    def _load_rows(self, symbols: list[str]) -> None:
        self._table.setRowCount(0)
        self._table.setRowCount(len(symbols))
        for row, sym in enumerate(symbols):
            idx_item = QtWidgets.QTableWidgetItem(str(row + 1))
            idx_item.setTextAlignment(
                QtCore.Qt.AlignmentFlag.AlignCenter
                | QtCore.Qt.AlignmentFlag.AlignVCenter)
            idx_item.setForeground(QtGui.QColor("#888888"))
            self._table.setItem(row, _COL_IDX, idx_item)
            sym_item = QtWidgets.QTableWidgetItem(sym)
            sym_item.setTextAlignment(
                QtCore.Qt.AlignmentFlag.AlignLeft
                | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, _COL_SYMBOL, sym_item)
        self._update_counter()
        self.symbols_changed.emit(self.get_symbols())

    def _renumber(self) -> None:
        for row in range(self._table.rowCount()):
            item = self._table.item(row, _COL_IDX)
            if item:
                item.setText(str(row + 1))

    def _update_counter(self) -> None:
        n = self._table.rowCount()
        self._counter_label.setText(f"共 {n} 只股票")

    # ---- event handlers -----------------------------------

    def _on_input_enter(self) -> None:
        text = self._input_edit.text().strip()
        if not text:
            return
        symbols = self._parser.parse(text)
        if symbols:
            added = self.add_symbols(symbols)
            if added:
                self._input_edit.clear()
            else:
                self._input_edit.selectAll()
        else:
            self._input_edit.setStyleSheet("border: 1px solid #FF5555;")
            QtCore.QTimer.singleShot(
                800, lambda: self._input_edit.setStyleSheet("")
            )

    def _on_paste_clipboard(self) -> None:
        text = QtWidgets.QApplication.clipboard().text()
        if not text.strip():
            return
        symbols = self._parser.parse(text)
        if not symbols:
            QtWidgets.QMessageBox.information(
                self,
                "粘贴结果",
                "未能识别到有效股票代码。\n\n"
                "支持：6位代码、vt_symbol、Tushare 格式",
            )
            return
        added   = self.add_symbols(symbols)
        skipped = len(symbols) - added
        msg = f"识别到 {len(symbols)} 个代码，新增 {added} 个"
        if skipped:
            msg += f"，跳过重复 {skipped} 个"
        self._counter_label.setText(msg)
        QtCore.QTimer.singleShot(3000, self._update_counter)

    def _on_sort(self) -> None:
        self._load_rows(sorted(self.get_symbols()))

    def _on_dedup(self) -> None:
        seen: set[str] = set()
        unique: list[str] = []
        for s in self.get_symbols():
            if s not in seen:
                seen.add(s)
                unique.append(s)
        self._load_rows(unique)

    def _on_clear(self) -> None:
        n = self._table.rowCount()
        if n == 0:
            return
        reply = QtWidgets.QMessageBox.question(
            self,
            "确认清空",
            f"确定要清空全部 {n} 只股票吗？",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.clear()

    def _on_double_click(self, index: QtCore.QModelIndex) -> None:
        row = index.row()
        self._table.removeRow(row)
        self._renumber()
        self._update_counter()
        self.symbols_changed.emit(self.get_symbols())

    def _table_key_press(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in (
            QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace
        ):
            self._delete_selected()
        else:
            QtWidgets.QTableWidget.keyPressEvent(self._table, event)

    def _delete_selected(self) -> None:
        rows = sorted(
            {idx.row() for idx in self._table.selectedIndexes()},
            reverse=True,
        )
        for row in rows:
            self._table.removeRow(row)
        if rows:
            self._renumber()
            self._update_counter()
            self.symbols_changed.emit(self.get_symbols())

    def _copy_selected(self) -> None:
        rows = sorted({idx.row() for idx in self._table.selectedIndexes()})
        lines: list[str] = []
        for row in rows:
            item = self._table.item(row, _COL_SYMBOL)
            if item:
                lines.append(item.text())
        if lines:
            QtWidgets.QApplication.clipboard().setText("\n".join(lines))

    def _show_context_menu(self, pos: QtCore.QPoint) -> None:
        self._ctx_menu.exec_(self._table.mapToGlobal(pos))

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
        if event.key() == QtCore.Qt.Key.Key_V and event.modifiers() == ctrl:
            self._on_paste_clipboard()
        elif event.key() == QtCore.Qt.Key.Key_A and event.modifiers() == ctrl:
            self._table.selectAll()
        else:
            super().keyPressEvent(event)
