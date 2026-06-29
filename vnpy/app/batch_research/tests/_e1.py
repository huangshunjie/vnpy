from pathlib import Path
import py_compile

p = Path(r"C:\Users\11229\Documents\GitHub\vnpy\vnpy\app\batch_research\ui\stock_pool_editor.py")

# Part 1: module header + constants
part1 = (
    '"""\n'
    'ui/stock_pool_editor.py\n'
    '\n'
    'StockPoolEditor -- embeddable stock list editor widget.\n'
    '"""\n'
    'from __future__ import annotations\n'
    'from typing import Callable\n'
    'from vnpy.trader.ui import QtCore, QtGui, QtWidgets\n'
    'from ..utils.symbol_parser import SymbolParser\n'
    '\n'
    '_STYLE_TABLE = """\n'
    'QTableWidget {\n'
    '    background-color: #1E1E1E; gridline-color: #3A3A3A;\n'
    '    color: #FFFFFF; font-size: 13px;\n'
    '    selection-background-color: #2A5298; selection-color: #FFFFFF;\n'
    '    border: 1px solid #3A3A3A;\n'
    '}\n'
    'QTableWidget::item { padding: 3px 8px; border-bottom: 1px solid #2A2A2A; }\n'
    'QHeaderView::section {\n'
    '    background-color: #1E3A5F; color: #FFFFFF;\n'
    '    padding: 4px; border: 1px solid #2A4A7F; font-weight: bold;\n'
    '}\n'
    '"""\n'
    '_STYLE_COUNTER = "color: #AAAAAA; font-size: 12px; padding: 2px 4px;"\n'
    '_STYLE_HINT    = "color: #888888; font-size: 11px;"\n'
    '_COL_IDX    = 0\n'
    '_COL_SYMBOL = 1\n'
    '\n'
)
p.write_text(part1, encoding="utf-8")
print("part1 ok:", len(part1.splitlines()), "lines")
