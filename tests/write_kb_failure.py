"""write_kb_failure.py — FailureCaseList + FailureCaseDetail"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\knowledge_tab.py"
)

CODE = '''

class FailureCaseList(QWidget):
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
        fb = QHBoxLayout()
        self._combo = QComboBox()
        self._combo.addItem("\\u5168\\u90e8", "all")
        self._combo.addItem("\\u672a\\u89e3\\u51b3", "open")
        self._combo.addItem("\\u5df2\\u89e3\\u51b3", "resolved")
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(lambda _: self._refresh())
        fb.addWidget(self._combo, 1); root.addLayout(fb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\\u6807\\u9898","\\u4e25\\u91cd\\u7a0b\\u5ea6","\\u4f5c\\u8005","\\u72b6\\u6001"])
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
        filt  = self._combo.currentData()
        items = self._engine.list_failure_cases()
        if filt == "open":     items = [c for c in items if not c.is_resolved]
        elif filt == "resolved": items = [c for c in items if c.is_resolved]
        if self._keyword:
            items = [c for c in items
                     if self._keyword in c.title.lower()
                     or self._keyword in (c.symptom or "").lower()]
        self._table.setRowCount(0)
        for fc in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(fc.title))
            sc = SEVERITY_COLOR.get(fc.severity, "#6c757d")
            si = QTableWidgetItem(fc.severity)
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 1, si)
            self._table.setItem(r, 2, QTableWidgetItem(fc.author or ""))
            if fc.is_resolved:
                ri = QTableWidgetItem("\\u2705 \\u5df2\\u89e3\\u51b3")
                ri.setForeground(QBrush(QColor("#198754")))
            else:
                ri = QTableWidgetItem("\\u274c \\u672a\\u89e3\\u51b3")
                ri.setForeground(QBrush(QColor("#dc3545")))
            self._table.setItem(r, 3, ri)
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, fc.case_id)

    def _on_click(self, item): self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        cid = item.data(ROLE_ID)
        fc  = self._engine.get_failure_case(cid)
        if not fc: return
        menu   = QMenu(self)
        a_res  = menu.addAction("\\u2705  \\u6807\\u8bb0\\u5df2\\u89e3\\u51b3")
        menu.addSeparator()
        a_del  = menu.addAction("\\U0001f5d1  \\u5220\\u9664")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == a_res:
            self._engine.resolve_case(cid); self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\\u786e\\u8ba4",
                "\\u5220\\u9664\\u6848\\u4f8b\\u300c" + fc.title + "\\u300d\\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_failure_case(cid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class FailureCaseDetail(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        hdr  = QHBoxLayout()
        self._title = QLabel("\\u8bf7\\u9009\\u62e9\\u5931\\u8d25\\u6848\\u4f8b")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title); hdr.addStretch()
        self._res_badge = QLabel("")
        self._res_badge.setFixedHeight(22)
        self._res_badge.setStyleSheet(
            "padding:2px 10px;border-radius:10px;font-size:12px;")
        hdr.addWidget(self._res_badge); root.addLayout(hdr)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        root.addWidget(self._bar)
        for attr, label, color in [
            ("_symp_v",  "\\U0001f6a8  \\u73b0\\u8c61",      "#dc3545"),
            ("_root_v",  "\\U0001f50d  \\u6839\\u56e0",      "#fd7e14"),
            ("_imp_v",   "\\U0001f4a5  \\u5f71\\u54cd",      "#9c27b0"),
            ("_res_v",   "\\u2705  \\u89e3\\u51b3\\u65b9\\u6848","#198754"),
            ("_prev_v",  "\\U0001f6e1  \\u9884\\u9632\\u63aa\\u65bd","#0d6efd"),
        ]:
            grp = QGroupBox(label)
            grp.setStyleSheet("QGroupBox{font-weight:bold;color:"+color+";}")
            gl  = QVBoxLayout(grp)
            te  = QTextEdit(); te.setReadOnly(True)
            te.setFont(QFont("Consolas", 10)); te.setFixedHeight(66)
            gl.addWidget(te); setattr(self, attr, te); root.addWidget(grp)
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\\u5c5e\\u6027","\\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        root.addWidget(self._info)

    def load(self, case_id: str):
        self._id = case_id
        fc = self._engine.get_failure_case(case_id)
        if not fc: return
        self._title.setText("\\u274c  " + fc.title)
        sc = SEVERITY_COLOR.get(fc.severity, "#6c757d")
        self._bar.setStyleSheet("background:" + sc + ";border-radius:2px;")
        if fc.is_resolved:
            self._res_badge.setText("\\u2705 \\u5df2\\u89e3\\u51b3")
            self._res_badge.setStyleSheet(
                "padding:2px 10px;border-radius:10px;"
                "background:#d1e7dd;color:#198754;"
                "font-size:12px;border:1px solid #a3cfbb;")
        else:
            self._res_badge.setText("\\u274c \\u672a\\u89e3\\u51b3")
            self._res_badge.setStyleSheet(
                "padding:2px 10px;border-radius:10px;"
                "background:#f8d7da;color:#dc3545;"
                "font-size:12px;border:1px solid #f1aeb5;")
        self._symp_v.setPlainText(fc.symptom or "")
        self._root_v.setPlainText(fc.root_cause or "")
        self._imp_v.setPlainText(fc.impact or "")
        self._res_v.setPlainText(fc.resolution or "")
        self._prev_v.setPlainText(fc.prevention or "")
        self._info.setRowCount(0)
        res_at = fc.resolved_at.strftime("%Y-%m-%d") if fc.resolved_at else "\\u2014"
        for k, v in [
            ("ID", fc.case_id[:16]),
            ("\\u4e25\\u91cd\\u7a0b\\u5ea6", fc.severity),
            ("\\u4f5c\\u8005", fc.author or "\\u2014"),
            ("\\u6807\\u7b7e", ", ".join(fc.tags) if fc.tags else "\\u2014"),
            ("\\u89e3\\u51b3\\u65f6\\u95f4", res_at),
            ("\\u521b\\u5efa", fc.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))

    def clear_panel(self):
        self._id = None
        self._title.setText("\\u8bf7\\u9009\\u62e9\\u5931\\u8d25\\u6848\\u4f8b")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        self._res_badge.setText(""); self._res_badge.setStyleSheet("")
        for te in (self._symp_v, self._root_v, self._imp_v,
                   self._res_v, self._prev_v):
            te.clear()
        self._info.setRowCount(0)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("FailureCase subsystem OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
