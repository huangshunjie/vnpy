"""write_kb_main.py — KnowledgeTab main class"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\knowledge_tab.py"
)

CODE = '''

class KnowledgeTab(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # ── toolbar ───────────────────────────────────────────────
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_new  = QPushButton("+ \\u65b0\\u5efa")
        self._btn_edit = QPushButton("\\u270f  \\u7f16\\u8f91")
        self._btn_del  = QPushButton("\\U0001f5d1  \\u5220\\u9664")
        for btn in (self._btn_new, self._btn_edit, self._btn_del):
            btn.setFixedHeight(28); tb.addWidget(btn)
        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#dee2e6;"); tb.addWidget(sep)
        tb.addStretch()
        tb.addWidget(QLabel("\\u641c\\u7d22:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("\\u6807\\u9898 / \\u5185\\u5bb9 / \\u6807\\u7b7e...")
        self._search_box.setFixedWidth(180); self._search_box.setFixedHeight(28)
        tb.addWidget(self._search_box)
        self._btn_search = QPushButton("\\u641c\\u7d22")
        self._btn_search.setFixedSize(52, 28)
        self._btn_reset_s = QPushButton("\\u91cd\\u7f6e")
        self._btn_reset_s.setFixedSize(52, 28)
        tb.addWidget(self._btn_search); tb.addWidget(self._btn_reset_s)
        root.addLayout(tb)

        # ── stats bar ─────────────────────────────────────────────
        self._stats_bar = QLabel("\\u52a0\\u8f7d\\u4e2d...")
        self._stats_bar.setStyleSheet(
            "background:#f0f4ff;border:1px solid #b0c4f8;"
            "border-radius:4px;padding:4px 10px;"
            "color:#4a6cf7;font-size:12px;")
        root.addWidget(self._stats_bar)

        # ── sub-tabs ──────────────────────────────────────────────
        self._sub = QTabWidget(); self._sub.setDocumentMode(True)

        def _make_split(lst, det):
            w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0)
            sp = QSplitter(Qt.Horizontal)
            sp.addWidget(lst); sp.addWidget(det)
            sp.setSizes([240, 960])
            sp.setStretchFactor(0,0); sp.setStretchFactor(1,1)
            l.addWidget(sp); return w

        self._note_list   = NoteList(self._engine)
        self._note_detail = NoteDetail(self._engine)
        self._sub.addTab(
            _make_split(self._note_list, self._note_detail),
            "\\U0001f9ea  \\u7b14\\u8bb0")

        self._card_list   = CardList(self._engine)
        self._card_detail = CardDetail(self._engine)
        self._sub.addTab(
            _make_split(self._card_list, self._card_detail),
            "\\U0001f4a1  \\u7ecf\\u9a8c\\u5361")

        self._fc_list   = FailureCaseList(self._engine)
        self._fc_detail = FailureCaseDetail(self._engine)
        self._sub.addTab(
            _make_split(self._fc_list, self._fc_detail),
            "\\u274c  \\u5931\\u8d25\\u6848\\u4f8b")

        self._search_panel = SearchPanel(self._engine)
        self._sub.addTab(self._search_panel, "\\U0001f50d  \\u641c\\u7d22")

        root.addWidget(self._sub)

        # ── status bar ────────────────────────────────────────────
        self._status = QLabel("\\u5c31\\u7eea")
        self._status.setStyleSheet("color:#6c757d;font-size:11px;")
        root.addWidget(self._status)

        # ── connect ───────────────────────────────────────────────
        self._note_list.selected.connect(self._note_detail.load)
        self._note_list.selected.connect(
            lambda i: self._set_status("\\u7b14\\u8bb0: " + (
                self._engine.get_note(i).title
                if self._engine.get_note(i) else i)))
        self._card_list.selected.connect(self._card_detail.load)
        self._card_list.selected.connect(
            lambda i: self._set_status("\\u7ecf\\u9a8c\\u5361: " + (
                self._engine.get_card(i).title
                if self._engine.get_card(i) else i)))
        self._fc_list.selected.connect(self._fc_detail.load)
        self._fc_list.selected.connect(
            lambda i: self._set_status("\\u6848\\u4f8b: " + (
                self._engine.get_failure_case(i).title
                if self._engine.get_failure_case(i) else i)))

        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_del.clicked.connect(self._on_delete)
        self._btn_search.clicked.connect(self._on_search)
        self._btn_reset_s.clicked.connect(self._on_reset_search)
        self._search_box.returnPressed.connect(self._on_search)

        for ev in (EVENT_RO_KB_CREATED, EVENT_RO_KB_UPDATED,
                   EVENT_RO_KB_DELETED, EVENT_RO_KB_TAGGED):
            self._engine.event_engine.register(ev, self._on_stats_event)

        self._refresh_stats()

    # ── helpers ───────────────────────────────────────────────────

    def _current_tab(self) -> int:
        return self._sub.currentIndex()

    def _selected_id(self):
        idx = self._current_tab()
        if idx == 0: return self._note_list.selected_id()
        if idx == 1: return self._card_list.selected_id()
        if idx == 2: return self._fc_list.selected_id()
        return None

    # ── CRUD ──────────────────────────────────────────────────────

    def _on_new(self):
        idx = self._current_tab()
        if idx == 0:
            dlg = NoteDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                nt = self._engine.create_note(
                    title=dlg.get_title(), content=dlg.get_content(),
                    note_type=dlg.get_note_type(), priority=dlg.get_priority(),
                    author=dlg.get_author(), tags=dlg.get_tags())
                self._set_status("\\u7b14\\u8bb0\\u300c" + nt.title + "\\u300d\\u5df2\\u521b\\u5efa")
                self._refresh_stats()
        elif idx == 1:
            dlg = CardDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                cd = self._engine.create_card(
                    title=dlg.get_title(), context=dlg.get_context(),
                    insight=dlg.get_insight(), lesson=dlg.get_lesson(),
                    author=dlg.get_author(), tags=dlg.get_tags())
                self._set_status("\\u7ecf\\u9a8c\\u5361\\u300c" + cd.title + "\\u300d\\u5df2\\u521b\\u5efa")
                self._refresh_stats()
        elif idx == 2:
            dlg = FailureCaseDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                fc = self._engine.create_failure_case(
                    title=dlg.get_title(),
                    symptom=dlg.get_symptom(),
                    root_cause=dlg.get_root_cause(),
                    impact=dlg.get_impact(),
                    resolution=dlg.get_resolution(),
                    prevention=dlg.get_prevention(),
                    severity=dlg.get_severity(),
                    author=dlg.get_author(),
                    tags=dlg.get_tags())
                self._set_status("\\u6848\\u4f8b\\u300c" + fc.title + "\\u300d\\u5df2\\u521b\\u5efa")
                self._refresh_stats()
        else:
            self._set_status("\\u8bf7\\u5207\\u6362\\u5230\\u5177\\u4f53\\u7c7b\\u522b\\u518d\\u65b0\\u5efa")

    def _on_edit(self):
        idx = self._current_tab()
        sel = self._selected_id()
        if not sel:
            self._set_status("\\u8bf7\\u5148\\u9009\\u62e9\\u8981\\u7f16\\u8f91\\u7684\\u6761\\u76ee")
            return
        if idx == 0:
            nt = self._engine.get_note(sel)
            if not nt: return
            dlg = NoteDialog(parent=self, record=nt)
            if dlg.exec() == QDialog.Accepted:
                nt.title     = dlg.get_title()
                nt.note_type = dlg.get_note_type()
                nt.priority  = dlg.get_priority()
                nt.author    = dlg.get_author()
                nt.tags      = dlg.get_tags()
                nt.content   = dlg.get_content()
                self._engine.update_note(nt)
                self._note_detail.load(sel)
                self._set_status("\\u7b14\\u8bb0\\u300c" + nt.title + "\\u300d\\u5df2\\u66f4\\u65b0")
        elif idx == 1:
            cd = self._engine.get_card(sel)
            if not cd: return
            dlg = CardDialog(parent=self, record=cd)
            if dlg.exec() == QDialog.Accepted:
                cd.title   = dlg.get_title(); cd.author  = dlg.get_author()
                cd.tags    = dlg.get_tags()
                cd.context = dlg.get_context(); cd.insight = dlg.get_insight()
                cd.lesson  = dlg.get_lesson()
                self._engine.update_card(cd)
                self._card_detail.load(sel)
                self._set_status("\\u7ecf\\u9a8c\\u5361\\u300c" + cd.title + "\\u300d\\u5df2\\u66f4\\u65b0")
        elif idx == 2:
            fc = self._engine.get_failure_case(sel)
            if not fc: return
            dlg = FailureCaseDialog(parent=self, record=fc)
            if dlg.exec() == QDialog.Accepted:
                fc.title      = dlg.get_title(); fc.severity    = dlg.get_severity()
                fc.author     = dlg.get_author(); fc.tags       = dlg.get_tags()
                fc.symptom    = dlg.get_symptom(); fc.root_cause = dlg.get_root_cause()
                fc.impact     = dlg.get_impact(); fc.resolution  = dlg.get_resolution()
                fc.prevention = dlg.get_prevention()
                self._engine.update_failure_case(fc)
                self._fc_detail.load(sel)
                self._set_status("\\u6848\\u4f8b\\u300c" + fc.title + "\\u300d\\u5df2\\u66f4\\u65b0")

    def _on_delete(self):
        idx = self._current_tab()
        sel = self._selected_id()
        if not sel: return
        labels   = {0:"\\u7b14\\u8bb0", 1:"\\u7ecf\\u9a8c\\u5361", 2:"\\u5931\\u8d25\\u6848\\u4f8b"}
        getters  = {0:self._engine.get_note, 1:self._engine.get_card,
                    2:self._engine.get_failure_case}
        deleters = {0:self._engine.delete_note, 1:self._engine.delete_card,
                    2:self._engine.delete_failure_case}
        clears   = {0:self._note_detail.clear_panel,
                    1:self._card_detail.clear_panel,
                    2:self._fc_detail.clear_panel}
        if idx not in labels: return
        obj = getters[idx](sel)
        if not obj: return
        if QMessageBox.question(
            self, "\\u786e\\u8ba4\\u5220\\u9664",
            "\\u5220\\u9664" + labels[idx] + "\\u300c" + obj.title + "\\u300d\\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            deleters[idx](sel)
            clears[idx]()
            self._set_status(labels[idx] + "\\u300c" + obj.title + "\\u300d\\u5df2\\u5220\\u9664")
            self._refresh_stats()

    # ── search ────────────────────────────────────────────────────

    def _on_search(self):
        kw = self._search_box.text().strip()
        if not kw: return
        idx = self._current_tab()
        if idx == 0:   self._note_list.set_keyword(kw)
        elif idx == 1: self._card_list.set_keyword(kw)
        elif idx == 2: self._fc_list.set_keyword(kw)
        elif idx == 3:
            self._search_panel._box.setText(kw)
            self._search_panel._do_search()
        self._set_status("\\u641c\\u7d22\\u300c" + kw + "\\u300d")

    def _on_reset_search(self):
        self._search_box.clear()
        for lst in (self._note_list, self._card_list, self._fc_list):
            lst.set_keyword("")
        self._set_status("\\u5c31\\u7eea")

    # ── stats ─────────────────────────────────────────────────────

    def _on_stats_event(self, _=None):
        self._refresh_stats()

    def _refresh_stats(self):
        s = self._engine.stats()
        self._stats_bar.setText(
            "\\u7b14\\u8bb0: " + str(s.get("notes", 0))
            + "    \\u5df2\\u5f52\\u6863: " + str(s.get("archived_notes", 0))
            + "    \\u7ecf\\u9a8c\\u5361: " + str(s.get("cards", 0))
            + "    \\u5931\\u8d25\\u6848\\u4f8b: " + str(s.get("failure_cases", 0))
            + "    \\u672a\\u89e3\\u51b3: " + str(s.get("open_cases", 0)))

    def _set_status(self, msg: str):
        self._status.setText(msg)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("KnowledgeTab main OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
