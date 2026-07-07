"""write_kb_card1.py — CardList + CardDetail"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\knowledge_tab.py"
)

CODE = '''

class CardList(QWidget):
    selected = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._keyword = ""
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels([
            "\\u6807\\u9898","\\u4f5c\\u8005","\\u6807\\u7b7e"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.itemClicked.connect(self._on_click)
        self._table.customContextMenuRequested.connect(self._on_ctx)
        root.addWidget(self._table)

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in (EVENT_RO_KB_CREATED, EVENT_RO_KB_UPDATED,
                   EVENT_RO_KB_DELETED, EVENT_RO_KB_TAGGED):
            ee.register(ev, lambda _: self._refresh())

    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()

    def _refresh(self):
        items = self._engine.list_cards()
        if self._keyword:
            items = [c for c in items
                     if self._keyword in c.title.lower()
                     or self._keyword in (c.insight or "").lower()
                     or any(self._keyword in t for t in c.tags)]
        self._table.setRowCount(0)
        for cd in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(cd.title))
            self._table.setItem(r, 1, QTableWidgetItem(cd.author or ""))
            self._table.setItem(r, 2, QTableWidgetItem(", ".join(cd.tags)))
            for c in range(3):
                self._table.item(r, c).setData(ROLE_ID, cd.card_id)

    def _on_click(self, item): self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        cid = item.data(ROLE_ID)
        cd  = self._engine.get_card(cid)
        if not cd: return
        menu  = QMenu(self)
        a_del = menu.addAction("\\U0001f5d1  \\u5220\\u9664")
        if menu.exec(self._table.viewport().mapToGlobal(pos)) == a_del:
            if QMessageBox.question(
                self, "\\u786e\\u8ba4",
                "\\u5220\\u9664\\u5361\\u7247\\u300c" + cd.title + "\\u300d\\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_card(cid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class CardDetail(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        self._title = QLabel("\\u8bf7\\u9009\\u62e9\\u7ecf\\u9a8c\\u5361\\u7247")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        root.addWidget(self._title)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        root.addWidget(self._bar)
        for attr, label, color in [
            ("_context_view","\\U0001f4cc  \\u80cc\\u666f","#4a6cf7"),
            ("_insight_view","\\U0001f4a1  \\u6d1e\\u5bdf","#198754"),
            ("_lesson_view", "\\U0001f4d6  \\u6559\\u8bad","#fd7e14"),
        ]:
            grp = QGroupBox(label)
            grp.setStyleSheet("QGroupBox{font-weight:bold;color:"+color+";}")
            gl = QVBoxLayout(grp)
            te = QTextEdit(); te.setReadOnly(True)
            te.setFont(QFont("Consolas", 10)); te.setFixedHeight(90)
            gl.addWidget(te); setattr(self, attr, te); root.addWidget(grp)
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\\u5c5e\\u6027","\\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        root.addWidget(self._info)

    def load(self, card_id: str):
        self._id = card_id
        cd = self._engine.get_card(card_id)
        if not cd: return
        self._title.setText("\\U0001f4a1  " + cd.title)
        self._bar.setStyleSheet("background:#198754;border-radius:2px;")
        self._context_view.setPlainText(cd.context or "")
        self._insight_view.setPlainText(cd.insight or "")
        self._lesson_view.setPlainText(cd.lesson or "")
        self._info.setRowCount(0)
        for k, v in [
            ("ID", cd.card_id[:16]),("\\u4f5c\\u8005", cd.author or "\\u2014"),
            ("\\u6807\\u7b7e", ", ".join(cd.tags) if cd.tags else "\\u2014"),
            ("\\u9002\\u7528", ", ".join(cd.applicable_to) if cd.applicable_to else "\\u2014"),
            ("\\u521b\\u5efa", cd.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))

    def clear_panel(self):
        self._id = None
        self._title.setText("\\u8bf7\\u9009\\u62e9\\u7ecf\\u9a8c\\u5361\\u7247")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        for te in (self._context_view, self._insight_view, self._lesson_view):
            te.clear()
        self._info.setRowCount(0)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("CardList+Detail OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
