"""write_kb_note.py — NoteList + NoteDetail"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\knowledge_tab.py"
)

CODE = '''

class NoteList(QWidget):
    selected = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._filter  = None
        self._keyword = ""
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        fb = QHBoxLayout()
        self._combo = QComboBox()
        self._combo.addItem("\\u5168\\u90e8", None)
        for nt in NoteType:
            self._combo.addItem(NOTE_TYPE_ICON.get(nt,"")+" "+nt.value, nt)
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1)
        root.addLayout(fb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\\u6807\\u9898","\\u7c7b\\u578b","\\u4f18\\u5148\\u7ea7","\\u72b6\\u6001"])
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
    def _on_filter(self, _):   self._filter = self._combo.currentData(); self._refresh()

    def _refresh(self):
        items = self._engine.list_notes()
        if self._filter:
            items = [n for n in items if n.note_type == self._filter]
        if self._keyword:
            items = [n for n in items
                     if self._keyword in n.title.lower()
                     or self._keyword in (n.content or "").lower()
                     or any(self._keyword in t for t in n.tags)]
        self._table.setRowCount(0)
        for nt in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(nt.title))
            tc = NOTE_TYPE_COLOR.get(nt.note_type, "#6c757d")
            ti = QTableWidgetItem(
                NOTE_TYPE_ICON.get(nt.note_type,"") + " " + nt.note_type.value)
            ti.setForeground(QBrush(QColor(tc)))
            self._table.setItem(r, 1, ti)
            pc = PRIORITY_COLOR.get(nt.priority, "#6c757d")
            pi = QTableWidgetItem(nt.priority.value)
            pi.setForeground(QBrush(QColor(pc)))
            self._table.setItem(r, 2, pi)
            if nt.is_archived:
                si = QTableWidgetItem("\\U0001f4e6 \\u5df2\\u5f52\\u6863")
                si.setForeground(QBrush(QColor("#adb5bd")))
            else:
                si = QTableWidgetItem("\\u270f \\u6d3b\\u8dc3")
                si.setForeground(QBrush(QColor("#198754")))
            self._table.setItem(r, 3, si)
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, nt.note_id)

    def _on_click(self, item): self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        nid = item.data(ROLE_ID)
        nt  = self._engine.get_note(nid)
        if not nt: return
        menu = QMenu(self)
        a_arch = menu.addAction("\\U0001f4e6  \\u5f52\\u6863" if not nt.is_archived
                                else "\\u21a9  \\u53d6\\u6d88\\u5f52\\u6863")
        menu.addSeparator()
        a_del  = menu.addAction("\\U0001f5d1  \\u5220\\u9664")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == a_arch:
            self._engine.archive_note(nid); self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\\u786e\\u8ba4",
                "\\u5220\\u9664\\u7b14\\u8bb0\\u300c" + nt.title + "\\u300d\\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_note(nid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class NoteDetail(QTabWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        self.setDocumentMode(True)

        # Tab1: info table
        ov = QWidget(); ov_l = QVBoxLayout(ov)
        hdr = QHBoxLayout()
        self._title = QLabel("\\u8bf7\\u9009\\u62e9\\u7b14\\u8bb0")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title); hdr.addStretch()
        self._badge = QLabel("")
        self._badge.setFixedHeight(22)
        self._badge.setStyleSheet("padding:2px 10px;border-radius:10px;font-size:12px;")
        hdr.addWidget(self._badge)
        ov_l.addLayout(hdr)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        ov_l.addWidget(self._bar)
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\\u5c5e\\u6027","\\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        self._info.setFixedHeight(180)
        ov_l.addWidget(self._info)
        self.addTab(ov, "\\U0001f4cb  \\u6982\\u89c8")

        # Tab2: markdown editor
        ed = QWidget(); ed_l = QVBoxLayout(ed)
        self._editor = MarkdownEditor()
        self._editor.content_changed.connect(self._on_content_change)
        ed_l.addWidget(self._editor, 1)
        self.addTab(ed, "\\U0001f4dd  \\u7f16\\u8f91")

        # Tab3: rendered preview
        pv = QWidget(); pv_l = QVBoxLayout(pv)
        self._browser = QTextBrowser()
        self._browser.setStyleSheet(
            "QTextBrowser{background:#fff;border:1px solid #dee2e6;"
            "border-radius:4px;padding:16px;}")
        self._browser.setOpenExternalLinks(True)
        pv_l.addWidget(self._browser, 1)
        self.addTab(pv, "\\U0001f5fa  \\u9884\\u89c8")

    def load(self, note_id: str):
        self._id = note_id
        nt = self._engine.get_note(note_id)
        if not nt: return
        self._title.setText(nt.title)
        tc = NOTE_TYPE_COLOR.get(nt.note_type, "#6c757d")
        self._bar.setStyleSheet("background:" + tc + ";border-radius:2px;")
        pc = PRIORITY_COLOR.get(nt.priority, "#6c757d")
        self._badge.setText(nt.priority.value)
        self._badge.setStyleSheet(
            "padding:2px 10px;border-radius:10px;"
            "background:" + pc + "22;color:" + pc + ";"
            "font-size:12px;border:1px solid " + pc + "44;")
        self._info.setRowCount(0)
        for k, v in [
            ("ID", nt.note_id[:16]),("\\u6807\\u9898", nt.title),
            ("\\u7c7b\\u578b", nt.note_type.value),
            ("\\u4f18\\u5148\\u7ea7", nt.priority.value),
            ("\\u4f5c\\u8005", nt.author or "\\u2014"),
            ("\\u6807\\u7b7e", ", ".join(nt.tags) if nt.tags else "\\u2014"),
            ("\\u5df2\\u5f52\\u6863", "\\u662f" if nt.is_archived else "\\u5426"),
            ("\\u521b\\u5efa", nt.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))
        self._editor.content_changed.disconnect()
        self._editor.set_content(nt.content or "")
        self._editor.content_changed.connect(self._on_content_change)
        self._browser.setHtml(_md_to_html(nt.content or ""))

    def clear_panel(self):
        self._id = None
        self._title.setText("\\u8bf7\\u9009\\u62e9\\u7b14\\u8bb0")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        self._badge.setText(""); self._badge.setStyleSheet("")
        self._info.setRowCount(0)
        self._editor.clear(); self._browser.clear()

    def _on_content_change(self, md: str):
        if not self._id: return
        nt = self._engine.get_note(self._id)
        if not nt: return
        nt.content = md
        self._engine.update_note(nt)
        self._browser.setHtml(_md_to_html(md))
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("NoteList+Detail OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
