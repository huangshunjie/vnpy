"""write_pe_config_detail.py — append DetailPanel"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\config.py"
)

CODE = '''

class DetailPanel(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine; self._cid = None
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 0, 0, 0); root.setSpacing(8)
        hdr = QHBoxLayout()
        self._title = QLabel("\\u8bf7\\u9009\\u62e9\\u914d\\u7f6e\\u9879")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title); hdr.addStretch()
        self._badge = QLabel("")
        self._badge.setStyleSheet("font-size:12px;padding:2px 10px;border-radius:10px;")
        hdr.addWidget(self._badge)
        root.addLayout(hdr)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        root.addWidget(self._bar)

        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_save = QPushButton("\\U0001f4be  \\u4fdd\\u5b58")
        self._btn_save.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_save.setFixedHeight(28); self._btn_save.clicked.connect(self._on_save)
        tb.addWidget(self._btn_save)
        self._btn_fmt = QPushButton("\\u2728  \\u683c\\u5f0f\\u5316")
        self._btn_fmt.setFixedHeight(28); self._btn_fmt.clicked.connect(self._on_fmt)
        tb.addWidget(self._btn_fmt)
        self._btn_lock = QPushButton("\\U0001f512  \\u9501\\u5b9a")
        self._btn_lock.setFixedHeight(28); self._btn_lock.clicked.connect(self._on_lock)
        tb.addWidget(self._btn_lock)
        self._btn_export = QPushButton("\\U0001f4e4  \\u5bfc\\u51fa")
        self._btn_export.setFixedHeight(28); self._btn_export.clicked.connect(self._on_export)
        tb.addWidget(self._btn_export)
        tb.addStretch()
        self._meta = QLabel("")
        self._meta.setStyleSheet("font-size:11px;color:#8c8c8c;")
        tb.addWidget(self._meta)
        root.addLayout(tb)

        self._sub = QTabWidget(); self._sub.setDocumentMode(True)
        # editor tab
        ew = QWidget(); el = QVBoxLayout(ew); el.setContentsMargins(0,4,0,0)
        self._note_in = QLineEdit()
        self._note_in.setPlaceholderText("\\u4fee\\u6539\\u5907\\u6ce8...")
        self._note_in.setFixedHeight(26); el.addWidget(self._note_in)
        self._editor = QPlainTextEdit()
        f = QFont("Consolas", 10); self._editor.setFont(f)
        _JsonHighlighter(self._editor.document())
        el.addWidget(self._editor)
        self._sub.addTab(ew, "\\U0001f4dd  \\u7f16\\u8f91\\u5668")
        # version tab
        vw = QWidget(); vl = QVBoxLayout(vw); vl.setContentsMargins(0,4,0,0)
        self._ver_tbl = QTableWidget(0, 4)
        self._ver_tbl.setHorizontalHeaderLabels(["\\u7248\\u672c","\\u5907\\u6ce8","\\u4f5c\\u8005","\\u65f6\\u95f4"])
        self._ver_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._ver_tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ver_tbl.setAlternatingRowColors(True)
        self._ver_tbl.verticalHeader().setVisible(False)
        self._ver_tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._ver_tbl.setContextMenuPolicy(Qt.CustomContextMenu)
        self._ver_tbl.customContextMenuRequested.connect(self._on_ver_ctx)
        vl.addWidget(self._ver_tbl)
        self._sub.addTab(vw, "\\U0001f553  \\u7248\\u672c\\u5386\\u53f2")
        # diff tab
        dw = QWidget(); dl = QVBoxLayout(dw); dl.setContentsMargins(0,4,0,0)
        dh = QHBoxLayout()
        dh.addWidget(QLabel("A:"))
        self._da = QComboBox(); dh.addWidget(self._da, 1)
        dh.addWidget(QLabel("B:"))
        self._db = QComboBox(); dh.addWidget(self._db, 1)
        bdf = QPushButton("\\u5bf9\\u6bd4")
        bdf.setFixedHeight(26)
        bdf.setStyleSheet("background:#722ed1;color:#fff;border-radius:4px;border:none;")
        bdf.clicked.connect(self._on_diff); dh.addWidget(bdf)
        dl.addLayout(dh)
        self._diff_view = QPlainTextEdit(); self._diff_view.setReadOnly(True)
        df = QFont("Consolas", 10); self._diff_view.setFont(df)
        dl.addWidget(self._diff_view)
        self._sub.addTab(dw, "\\U0001f50d  Diff")
        root.addWidget(self._sub, 1)

    def load(self, cid):
        self._cid = cid
        if not cid:
            self._title.setText("\\u8bf7\\u9009\\u62e9\\u914d\\u7f6e\\u9879"); return
        rec = self._engine.config.get_config(cid)
        if rec: self._render(rec)

    def _render(self, rec):
        import json
        color = TYPE_COLOR.get(rec.config_type, "#4a6cf7")
        self._title.setText(rec.name + (" \\U0001f512" if rec.is_locked else ""))
        self._bar.setStyleSheet(f"background:{color};border-radius:2px;")
        self._badge.setText(rec.config_type.value)
        self._badge.setStyleSheet(
            f"font-size:12px;padding:2px 10px;border-radius:10px;"
            f"background:{color}22;color:{color};border:1px solid {color}44;")
        self._btn_save.setEnabled(not rec.is_locked)
        self._btn_lock.setText("\\U0001f513  \\u89e3\\u9501" if rec.is_locked
                               else "\\U0001f512  \\u9501\\u5b9a")
        self._meta.setText(
            f"\\u8d23\\u4efb\\u4eba: {rec.owner or '\\u2014'}"
            f"  \\u7248\\u672c: {len(rec.versions)}"
            f"  \\u66f4\\u65b0: {rec.updated_at.strftime('%H:%M:%S')}")
        self._editor.setPlainText(
            json.dumps(rec.current_data, ensure_ascii=False, indent=2))
        self._ver_tbl.setRowCount(0)
        self._da.clear(); self._db.clear()
        for ver in reversed(rec.versions):
            r = self._ver_tbl.rowCount(); self._ver_tbl.insertRow(r)
            self._ver_tbl.setItem(r, 0, QTableWidgetItem(ver.version_tag))
            self._ver_tbl.setItem(r, 1, QTableWidgetItem(ver.note))
            self._ver_tbl.setItem(r, 2, QTableWidgetItem(ver.created_by or "\\u2014"))
            self._ver_tbl.setItem(r, 3,
                QTableWidgetItem(ver.created_at.strftime("%m-%d %H:%M")))
            for c in range(4):
                self._ver_tbl.item(r, c).setData(ROLE_VER, ver.version_id)
            lbl = f"{ver.version_tag} ({ver.created_at.strftime('%m-%d')})"
            self._da.addItem(lbl, ver.version_id)
            self._db.addItem(lbl, ver.version_id)
        if self._db.count() >= 2:
            self._da.setCurrentIndex(min(1, self._da.count()-1))
            self._db.setCurrentIndex(0)

    def _on_ver_ctx(self, pos):
        item = self._ver_tbl.itemAt(pos)
        if not item or not self._cid: return
        vid  = item.data(ROLE_VER)
        menu = QMenu(self)
        a_rb   = menu.addAction("\\u21a9  \\u56de\\u6eda\\u5230\\u6b64\\u7248\\u672c")
        a_diff = menu.addAction("\\U0001f50d  \\u4e0e\\u5f53\\u524d\\u7248\\u672c Diff")
        act = menu.exec(self._ver_tbl.viewport().mapToGlobal(pos))
        try:
            if act == a_rb:
                self._engine.config.rollback_config(self._cid, vid)
                self.load(self._cid)
            elif act == a_diff:
                entries, summary = self._engine.config.diff_with_current(self._cid, vid)
                self._show_diff(entries, summary); self._sub.setCurrentIndex(2)
        except Exception as e:
            QMessageBox.warning(self, "\\u9519\\u8bef", str(e))

    def _on_save(self):
        if not self._cid: return
        import json
        try: data = json.loads(self._editor.toPlainText())
        except Exception as e:
            QMessageBox.warning(self, "JSON \\u9519\\u8bef", str(e)); return
        note = self._note_in.text().strip() or "\\u66f4\\u65b0\\u914d\\u7f6e"
        try:
            self._engine.config.update_config(self._cid, data, note=note)
            self._note_in.clear(); self.load(self._cid)
        except (ValueError, KeyError) as e:
            QMessageBox.warning(self, "\\u9519\\u8bef", str(e))

    def _on_fmt(self):
        import json
        try:
            obj = json.loads(self._editor.toPlainText())
            self._editor.setPlainText(json.dumps(obj, ensure_ascii=False, indent=2))
        except Exception: pass

    def _on_lock(self):
        if not self._cid: return
        rec = self._engine.config.get_config(self._cid)
        try:
            self._engine.config.unlock(self._cid) if rec.is_locked \
                else self._engine.config.lock(self._cid)
            self.load(self._cid)
        except Exception as e:
            QMessageBox.warning(self, "\\u9519\\u8bef", str(e))

    def _on_export(self):
        if not self._cid: return
        try:
            js = self._engine.config.export_config(self._cid)
            dlg = QDialog(self); dlg.setWindowTitle("\\u5bfc\\u51fa JSON")
            dlg.setMinimumSize(500, 360)
            vl = QVBoxLayout(dlg)
            te = QPlainTextEdit(js); te.setReadOnly(True)
            te.setFont(QFont("Consolas", 10)); vl.addWidget(te)
            btns = QDialogButtonBox(QDialogButtonBox.Close)
            btns.rejected.connect(dlg.reject); vl.addWidget(btns)
            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "\\u9519\\u8bef", str(e))

    def _on_diff(self):
        if not self._cid: return
        va = self._da.currentData(); vb = self._db.currentData()
        if not va or not vb or va == vb:
            self._diff_view.setPlainText("\\u8bf7\\u9009\\u62e9\\u4e0d\\u540c\\u7248\\u672c"); return
        entries, summary = self._engine.config.diff_versions(self._cid, va, vb)
        self._show_diff(entries, summary)

    def _show_diff(self, entries, summary):
        lines = [f"\\u5dee\\u5f02\\u6c47\\u603b: {summary}", ""]
        lines += [str(e) for e in entries]
        self._diff_view.setPlainText("\\n".join(lines) if entries else "\\u65e0\\u5dee\\u5f02")
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("DetailPanel OK, lines:", len(full.splitlines()))
