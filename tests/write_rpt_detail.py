"""write_rpt_detail.py — ReportDetail"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\report_tab.py"
)

CODE = """

class ReportDetail(QTabWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id: Optional[str] = None
        self._cur_sec_id: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        self.setDocumentMode(True)

        # ── Tab1: overview ────────────────────────────────────────
        ov = QWidget(); ov_l = QVBoxLayout(ov)
        hdr = QHBoxLayout()
        self._title = QLabel("\\u8bf7\\u9009\\u62e9\\u62a5\\u544a")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title); hdr.addStretch()
        self._pub_badge = QLabel("")
        self._pub_badge.setFixedHeight(22)
        self._pub_badge.setStyleSheet("padding:2px 10px;border-radius:10px;font-size:12px;")
        hdr.addWidget(self._pub_badge)
        ov_l.addLayout(hdr)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        ov_l.addWidget(self._bar)
        cr = QHBoxLayout()
        self._c_secs  = self._card("\\u7ae0\\u8282\\u6570","0")
        self._c_views = self._card("\\u6d4f\\u89c8\\u6570","0")
        self._c_type  = self._card("\\u7c7b\\u578b","\\u2014","#4a6cf7")
        for c in (self._c_secs, self._c_views, self._c_type):
            cr.addWidget(c)
        ov_l.addLayout(cr)
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\\u5c5e\\u6027","\\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        ov_l.addWidget(self._info)
        self.addTab(ov, "\\U0001f4cb  \\u6982\\u89c8")

        # ── Tab2: sections editor ─────────────────────────────────
        sec_w = QWidget(); sec_l = QVBoxLayout(sec_w)
        sec_tb = QHBoxLayout()
        self._btn_add_sec  = QPushButton("\\u2795 \\u7ae0\\u8282")
        self._btn_edit_sec = QPushButton("\\u270f \\u7f16\\u8f91")
        self._btn_del_sec  = QPushButton("\\U0001f5d1 \\u5220\\u9664")
        for b in (self._btn_add_sec, self._btn_edit_sec, self._btn_del_sec):
            b.setFixedHeight(26); sec_tb.addWidget(b)
        sec_tb.addStretch(); sec_l.addLayout(sec_tb)
        sec_sp = QSplitter(Qt.Vertical)
        self._sec_table = QTableWidget(0, 3)
        self._sec_table.setHorizontalHeaderLabels(
            ["\\u987a\\u5e8f","\\u6807\\u9898","\\u9884\\u89c8"])
        self._sec_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._sec_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._sec_table.setAlternatingRowColors(True)
        self._sec_table.verticalHeader().setVisible(False)
        self._sec_table.setFixedHeight(160)
        self._sec_table.itemClicked.connect(self._on_sec_click)
        sec_sp.addWidget(self._sec_table)
        self._sec_editor = MarkdownEditor()
        self._sec_editor.content_changed.connect(self._on_sec_content_change)
        sec_sp.addWidget(self._sec_editor)
        sec_sp.setSizes([160, 400])
        sec_l.addWidget(sec_sp, 1)
        self.addTab(sec_w, "\\U0001f4dd  \\u7ae0\\u8282")

        # ── Tab3: full preview ────────────────────────────────────
        pv_w = QWidget(); pv_l = QVBoxLayout(pv_w)
        pv_tb = QHBoxLayout()
        self._btn_refresh = QPushButton("\\U0001f504 \\u5237\\u65b0")
        self._btn_refresh.setFixedHeight(26)
        self._btn_refresh.clicked.connect(self._do_render)
        pv_tb.addWidget(self._btn_refresh); pv_tb.addStretch()
        pv_l.addLayout(pv_tb)
        self._browser = QTextBrowser()
        self._browser.setStyleSheet(
            "QTextBrowser{background:#fff;border:1px solid #dee2e6;"
            "border-radius:4px;padding:16px;}")
        self._browser.setOpenExternalLinks(True)
        pv_l.addWidget(self._browser, 1)
        self.addTab(pv_w, "\\U0001f5fa  \\u9884\\u89c8")

        self._btn_add_sec.clicked.connect(self._on_add_sec)
        self._btn_edit_sec.clicked.connect(self._on_edit_sec)
        self._btn_del_sec.clicked.connect(self._on_del_sec)

    @staticmethod
    def _card(label, value, color="#1a1f36"):
        card = QFrame(); card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame{background:#fff;border:1px solid #dee2e6;"
            "border-radius:8px;padding:6px;}")
        lay = QVBoxLayout(card); lay.setSpacing(2)
        lbl = QLabel(label); lbl.setStyleSheet("color:#6c757d;font-size:11px;")
        lay.addWidget(lbl)
        val = QLabel(value)
        val.setStyleSheet("font-size:20px;font-weight:bold;color:"+color+";")
        val.setAlignment(Qt.AlignCenter)
        lay.addWidget(val); card._val = val; return card

    def load(self, rpt_id: str):
        self._id = rpt_id
        rpt = self._engine.get_report(rpt_id)
        if not rpt: return
        self._load_overview(rpt)
        self._load_sections(rpt)
        self._do_render()

    def clear_panel(self):
        self._id = None; self._cur_sec_id = None
        self._title.setText("\\u8bf7\\u9009\\u62e9\\u62a5\\u544a")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        self._pub_badge.setText(""); self._pub_badge.setStyleSheet("")
        for c in (self._c_secs, self._c_views, self._c_type):
            c._val.setText("\\u2014")
        self._info.setRowCount(0)
        self._sec_table.setRowCount(0)
        self._sec_editor.clear(); self._browser.clear()

    def _load_overview(self, rpt: ReportRecord):
        self._title.setText(rpt.title)
        color = RPT_TYPE_COLOR.get(rpt.report_type, "#6c757d")
        self._bar.setStyleSheet("background:"+color+";border-radius:2px;")
        if rpt.is_published:
            self._pub_badge.setText("\\u2705 \\u5df2\\u53d1\\u5e03")
            self._pub_badge.setStyleSheet(
                "padding:2px 10px;border-radius:10px;"
                "background:#d1e7dd;color:#198754;"
                "font-size:12px;border:1px solid #a3cfbb;")
        else:
            self._pub_badge.setText("\\u270f \\u8349\\u7a3f")
            self._pub_badge.setStyleSheet(
                "padding:2px 10px;border-radius:10px;"
                "background:#f8f9fa;color:#6c757d;"
                "font-size:12px;border:1px solid #dee2e6;")
        icon = RPT_TYPE_ICON.get(rpt.report_type,"")
        self._c_secs._val.setText(str(len(rpt.sections)))
        self._c_views._val.setText(str(rpt.view_count or 0))
        self._c_type._val.setText(icon+" "+rpt.report_type.value)
        self._c_type._val.setStyleSheet(
            "font-size:14px;font-weight:bold;color:"+color+";")
        self._info.setRowCount(0)
        pub_at = rpt.published_at.strftime("%Y-%m-%d %H:%M") if rpt.published_at else "\\u2014"
        for k, v in [
            ("ID", rpt.report_id[:16]),("\\u6807\\u9898", rpt.title),
            ("\\u7c7b\\u578b", rpt.report_type.value),
            ("\\u4f5c\\u8005", rpt.author or "\\u2014"),
            ("\\u6458\\u8981", (rpt.summary or "\\u2014")[:80]),
            ("\\u6807\\u7b7e", ", ".join(rpt.tags) if rpt.tags else "\\u2014"),
            ("\\u53d1\\u5e03\\u65f6\\u95f4", pub_at),
            ("\\u521b\\u5efa", rpt.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))

    def _load_sections(self, rpt: ReportRecord):
        self._sec_table.setRowCount(0)
        for sec in sorted(rpt.sections, key=lambda s: s.order):
            r = self._sec_table.rowCount(); self._sec_table.insertRow(r)
            oi = QTableWidgetItem(str(sec.order)); oi.setTextAlignment(Qt.AlignCenter)
            self._sec_table.setItem(r, 0, oi)
            self._sec_table.setItem(r, 1, QTableWidgetItem(sec.title))
            prev = (sec.content or "")[:60].replace("\\n"," ")
            self._sec_table.setItem(r, 2, QTableWidgetItem(prev))
            for c in range(3):
                self._sec_table.item(r, c).setData(ROLE_ID, sec.section_id)

    def _on_sec_click(self, item):
        self._cur_sec_id = item.data(ROLE_ID)
        if not self._id: return
        rpt = self._engine.get_report(self._id)
        if not rpt: return
        sec = next((s for s in rpt.sections if s.section_id == self._cur_sec_id), None)
        if sec:
            self._sec_editor.content_changed.disconnect()
            self._sec_editor.set_content(sec.content or "")
            self._sec_editor.content_changed.connect(self._on_sec_content_change)

    def _on_sec_content_change(self, md: str):
        if not self._id or not self._cur_sec_id: return
        self._engine.update_section(self._id, self._cur_sec_id, content=md)

    def _on_add_sec(self):
        if not self._id: return
        dlg = SectionDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            sec = self._engine.add_section(
                self._id, title=dlg.get_title(),
                content=dlg.get_content(), order=dlg.get_order())
            if sec:
                rpt = self._engine.get_report(self._id)
                self._load_sections(rpt)
                self._c_secs._val.setText(str(len(rpt.sections)))

    def _on_edit_sec(self):
        if not self._id or not self._cur_sec_id: return
        rpt = self._engine.get_report(self._id)
        if not rpt: return
        sec = next((s for s in rpt.sections if s.section_id == self._cur_sec_id), None)
        if not sec: return
        dlg = SectionDialog(parent=self, record=sec)
        if dlg.exec() == QDialog.Accepted:
            self._engine.update_section(
                self._id, sec.section_id,
                title=dlg.get_title(), content=dlg.get_content())
            self._load_sections(self._engine.get_report(self._id))

    def _on_del_sec(self):
        if not self._id or not self._cur_sec_id: return
        rpt = self._engine.get_report(self._id)
        if not rpt: return
        sec = next((s for s in rpt.sections if s.section_id == self._cur_sec_id), None)
        if not sec: return
        if QMessageBox.question(
            self, "\\u786e\\u8ba4",
            "\\u5220\\u9664\\u7ae0\\u8282\\u300c"+sec.title+"\\u300d\\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self._engine.remove_section(self._id, sec.section_id)
            self._cur_sec_id = None
            self._load_sections(self._engine.get_report(self._id))
            self._sec_editor.clear()

    def _do_render(self):
        if not self._id: return
        md = self._engine.render_markdown(self._id)
        self._browser.setHtml(_md_to_html(md))
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("ReportDetail OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
