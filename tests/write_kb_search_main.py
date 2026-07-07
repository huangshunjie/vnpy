"""write_kb_search_main.py — SearchPanel + KnowledgeTab"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\knowledge_tab.py"
)

CODE = '''

class SearchPanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)

        # search bar
        sb = QHBoxLayout()
        self._box = QLineEdit()
        self._box.setPlaceholderText(
            "\\u5168\\u6587\\u641c\\u7d22\\u7b14\\u8bb0 / \\u5361\\u7247 / \\u6848\\u4f8b...")
        self._box.setFixedHeight(30)
        self._btn = QPushButton("\\U0001f50d  \\u641c\\u7d22")
        self._btn.setFixedHeight(30)
        self._btn.clicked.connect(self._do_search)
        self._box.returnPressed.connect(self._do_search)
        sb.addWidget(self._box, 1); sb.addWidget(self._btn)
        root.addLayout(sb)

        # results label
        self._lbl = QLabel("\\u8f93\\u5165\\u5173\\u952e\\u8bcd\\u5f00\\u59cb\\u641c\\u7d22")
        self._lbl.setStyleSheet("color:#6c757d;font-size:12px;margin:4px 0;")
        root.addWidget(self._lbl)

        # results tabs
        self._tabs = QTabWidget(); self._tabs.setDocumentMode(True)

        self._note_tbl = self._make_table(
            ["\\u6807\\u9898","\\u7c7b\\u578b","\\u4f5c\\u8005","\\u65e5\\u671f"])
        self._tabs.addTab(self._note_tbl, "\\U0001f9ea  \\u7b14\\u8bb0")

        self._card_tbl = self._make_table(
            ["\\u6807\\u9898","\\u4f5c\\u8005","\\u6807\\u7b7e"])
        self._tabs.addTab(self._card_tbl, "\\U0001f4a1  \\u7ecf\\u9a8c\\u5361")

        self._case_tbl = self._make_table(
            ["\\u6807\\u9898","\\u4e25\\u91cd\\u7a0b\\u5ea6","\\u4f5c\\u8005","\\u72b6\\u6001"])
        self._tabs.addTab(self._case_tbl, "\\u274c  \\u5931\\u8d25\\u6848\\u4f8b")

        root.addWidget(self._tabs, 1)

    @staticmethod
    def _make_table(headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.verticalHeader().setVisible(False)
        return t

    def _do_search(self):
        kw = self._box.text().strip()
        if not kw: return
        results = self._engine.search_all(kw)
        notes = results.get("notes", [])
        cards = results.get("cards", [])
        cases = results.get("failure_cases", [])
        total = len(notes) + len(cards) + len(cases)
        self._lbl.setText(
            "\\u300c" + kw + "\\u300d\\u5171\\u627e\\u5230 " + str(total)
            + " \\u6761\\u8bb0\\u5f55\\uff08\\u7b14\\u8bb0 " + str(len(notes))
            + " + \\u5361\\u7247 " + str(len(cards))
            + " + \\u6848\\u4f8b " + str(len(cases)) + "\\uff09")

        self._note_tbl.setRowCount(0)
        for nt in notes:
            r = self._note_tbl.rowCount(); self._note_tbl.insertRow(r)
            self._note_tbl.setItem(r, 0, QTableWidgetItem(nt.title))
            tc = NOTE_TYPE_COLOR.get(nt.note_type, "#6c757d")
            ti = QTableWidgetItem(NOTE_TYPE_ICON.get(nt.note_type,"")+" "+nt.note_type.value)
            ti.setForeground(QBrush(QColor(tc)))
            self._note_tbl.setItem(r, 1, ti)
            self._note_tbl.setItem(r, 2, QTableWidgetItem(nt.author or ""))
            self._note_tbl.setItem(r, 3,
                QTableWidgetItem(nt.created_at.strftime("%Y-%m-%d")))

        self._card_tbl.setRowCount(0)
        for cd in cards:
            r = self._card_tbl.rowCount(); self._card_tbl.insertRow(r)
            self._card_tbl.setItem(r, 0, QTableWidgetItem(cd.title))
            self._card_tbl.setItem(r, 1, QTableWidgetItem(cd.author or ""))
            self._card_tbl.setItem(r, 2, QTableWidgetItem(", ".join(cd.tags)))

        self._case_tbl.setRowCount(0)
        for fc in cases:
            r = self._case_tbl.rowCount(); self._case_tbl.insertRow(r)
            self._case_tbl.setItem(r, 0, QTableWidgetItem(fc.title))
            sc = SEVERITY_COLOR.get(fc.severity, "#6c757d")
            si = QTableWidgetItem(fc.severity)
            si.setForeground(QBrush(QColor(sc)))
            self._case_tbl.setItem(r, 1, si)
            self._case_tbl.setItem(r, 2, QTableWidgetItem(fc.author or ""))
            ri = QTableWidgetItem(
                "\\u2705 \\u5df2\\u89e3\\u51b3" if fc.is_resolved
                else "\\u274c \\u672a\\u89e3\\u51b3")
            ri.setForeground(QBrush(QColor(
                "#198754" if fc.is_resolved else "#dc3545")))
            self._case_tbl.setItem(r, 3, ri)

        idx = (0 if notes else 1 if cards else 2)
        self._tabs.setCurrentIndex(idx)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("SearchPanel OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
