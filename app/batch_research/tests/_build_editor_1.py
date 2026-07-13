from pathlib import Path

p = Path(r"C:\Users\11229\Documents\GitHub\vnpy\vnpy\app\batch_research\ui\stock_pool_editor.py")

chunk = r"""

class StockPoolEditor(QtWidgets.QWidget):
    """股票列表编辑器（可嵌入任意对话框）。

    Signals:
        symbols_changed: 列表变化时发出，携带最新 list[str]。
    """

    symbols_changed: QtCore.Signal = QtCore.Signal(list)

    def __init__(self, parent=None, name_resolver=None):
        super().__init__(parent)
        self._parser        = SymbolParser()
        self._name_resolver = name_resolver or (lambda _: "")
        self._init_ui()
        self._init_menu()

    # ── 公开接口 ────────────────────────────────

    def get_symbols(self) -> list:
        """返回当前股票列表（保持显示顺序）。"""
        result = []
        for row in range(self._table.rowCount()):
            item = self._table.item(row, _COL_SYMBOL)
            if item:
                result.append(item.text())
        return result

    def set_symbols(self, symbols: list) -> None:
        """整体替换股票列表（自动去重）。"""
        normalized = self._parser.parse("\n".join(symbols))
        self._load_rows(normalized)

    def add_symbols(self, symbols: list) -> int:
        """追加股票（自动过滤重复），返回实际新增数量。"""
        existing = set(self.get_symbols())
        new_ones = [s for s in symbols if s not in existing]
        if new_ones:
            self._load_rows(self.get_symbols() + new_ones)
        return len(new_ones)

    def clear(self) -> None:
        """清空全部股票。"""
        self._table.setRowCount(0)
        self._update_counter()
        self.symbols_changed.emit([])

    def count(self) -> int:
        """当前股票数量。"""
        return self._table.rowCount()
"""

current = p.read_text(encoding="utf-8")
p.write_text(current + chunk, encoding="utf-8")
print("chunk1 OK, lines =", len((current + chunk).splitlines()))
