"""write_rpt_maintab.py — ReportTab main class"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\report_tab.py"
)

CODE = """

class ReportTab(QWidget):
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
        self._btn_new    = QPushButton("+ \\u65b0\\u5efa")
        self._btn_edit   = QPushButton("\\u270f  \\u7f16\\u8f91")
        self._btn_pub    = QPushButton("\\U0001f4e4  \\u53d1\\u5e03")
        self._btn_del    = QPushButton("\\U0001f5d1  \\u5220\\u9664")
        for btn in (self._btn_new, self._btn_edit,
                    self._btn_pub, self._btn_del):
            btn.setFixedHeight(28); tb.addWidget(btn)
        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#dee2e6;"); tb.addWidget(sep)
        tb.addStretch()
        tb.addWidget(QLabel("\\u641c\\u7d22:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("\\u6807\\u9898 / \\u4f5c\\u8005 / \\u6807\\u7b7e...")
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
            "background:#e8f4fd;border:1px solid #9ec5fe;"
            "border-radius:4px;padding:4px 10px;"
            "color:#0d6efd;font-size:12px;")
        root.addWidget(self._stats_bar)

        # ── main area: sub-tabs (报告 / 模板) ─────────────────────
        self._sub = QTabWidget(); self._sub.setDocumentMode(True)

        # Tab1: 报告列表 + 详情
        rpt_w = QWidget(); rpt_l = QHBoxLayout(rpt_w)
        rpt_l.setContentsMargins(0,0,0,0)
        sp = QSplitter(Qt.Horizontal)
        self._rpt_list   = ReportList(self._engine)
        self._rpt_detail = ReportDetail(self._engine)
        sp.addWidget(self._rpt_list); sp.addWidget(self._rpt_detail)
        sp.setSizes([240, 960])
        sp.setStretchFactor(0,0); sp.setStretchFactor(1,1)
        rpt_l.addWidget(sp)
        self._sub.addTab(rpt_w, "\\U0001f4dd  \\u62a5\\u544a")

        # Tab2: 模板管理
        self._tmpl_panel = TemplatePanel(self._engine)
        self._sub.addTab(self._tmpl_panel, "\\U0001f4c4  \\u6a21\\u677f")

        root.addWidget(self._sub)

        # ── status bar ────────────────────────────────────────────
        self._status = QLabel("\\u5c31\\u7eea")
        self._status.setStyleSheet("color:#6c757d;font-size:11px;")
        root.addWidget(self._status)

        # ── connect ───────────────────────────────────────────────
        self._rpt_list.selected.connect(self._on_rpt_selected)
        self._tmpl_panel.apply_requested.connect(self._on_apply_template)

        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_pub.clicked.connect(self._on_publish)
        self._btn_del.clicked.connect(self._on_delete)
        self._btn_search.clicked.connect(self._on_search)
        self._btn_reset_s.clicked.connect(self._on_reset_search)
        self._search_box.returnPressed.connect(self._on_search)

        for ev in (EVENT_RO_RPT_CREATED, EVENT_RO_RPT_UPDATED,
                   EVENT_RO_RPT_DELETED, EVENT_RO_RPT_PUBLISHED,
                   EVENT_RO_RPT_RENDERED):
            self._engine.event_engine.register(ev, self._on_stats_event)

        self._refresh_stats()

    # ── helpers ───────────────────────────────────────────────────

    def _current_rpt_id(self) -> Optional[str]:
        return self._rpt_list.selected_id()

    # ── CRUD ──────────────────────────────────────────────────────

    def _on_new(self):
        dlg = ReportDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            rpt = self._engine.create_report(
                title       = dlg.get_title(),
                report_type = dlg.get_report_type(),
                author      = dlg.get_author(),
                summary     = dlg.get_summary(),
                tags        = dlg.get_tags(),
            )
            self._set_status("\\u62a5\\u544a\\u300c" + rpt.title + "\\u300d\\u5df2\\u521b\\u5efa")
            self._refresh_stats()

    def _on_edit(self):
        rid = self._current_rpt_id()
        if not rid:
            self._set_status("\\u8bf7\\u5148\\u9009\\u62e9\\u62a5\\u544a"); return
        rpt = self._engine.get_report(rid)
        if not rpt: return
        dlg = ReportDialog(parent=self, record=rpt)
        if dlg.exec() == QDialog.Accepted:
            rpt.title       = dlg.get_title()
            rpt.report_type = dlg.get_report_type()
            rpt.author      = dlg.get_author()
            rpt.summary     = dlg.get_summary()
            rpt.tags        = dlg.get_tags()
            self._engine.update_report(rpt)
            self._rpt_detail.load(rid)
            self._set_status("\\u62a5\\u544a\\u300c" + rpt.title + "\\u300d\\u5df2\\u66f4\\u65b0")

    def _on_publish(self):
        rid = self._current_rpt_id()
        if not rid:
            self._set_status("\\u8bf7\\u5148\\u9009\\u62e9\\u62a5\\u544a"); return
        rpt = self._engine.get_report(rid)
        if not rpt: return
        if rpt.is_published:
            self._engine.unpublish_report(rid)
            self._set_status("\\u62a5\\u544a\\u300c" + rpt.title + "\\u300d\\u5df2\\u53d6\\u6d88\\u53d1\\u5e03")
        else:
            self._engine.publish_report(rid)
            self._set_status("\\u62a5\\u544a\\u300c" + rpt.title + "\\u300d\\u5df2\\u53d1\\u5e03")
        self._rpt_detail.load(rid)
        self._refresh_stats()

    def _on_delete(self):
        rid = self._current_rpt_id()
        if not rid: return
        rpt = self._engine.get_report(rid)
        if not rpt: return
        if QMessageBox.question(
            self, "\\u786e\\u8ba4\\u5220\\u9664",
            "\\u5220\\u9664\\u62a5\\u544a\\u300c" + rpt.title + "\\u300d\\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self._engine.delete_report(rid)
            self._rpt_detail.clear_panel()
            self._set_status("\\u62a5\\u544a\\u300c" + rpt.title + "\\u300d\\u5df2\\u5220\\u9664")
            self._refresh_stats()

    # ── template apply ────────────────────────────────────────────

    def _on_apply_template(self, tid: str):
        rid = self._current_rpt_id()
        if not rid:
            QMessageBox.information(
                self, "\\u63d0\\u793a",
                "\\u8bf7\\u5148\\u5728\\u300e\\u62a5\\u544a\\u300f\\u9875\\u9009\\u4e2d\\u76ee\\u6807\\u62a5\\u544a")
            return
        self._engine.apply_template(tid, rid)
        self._rpt_detail.load(rid)
        tmpl = self._engine.get_template(tid)
        tname = tmpl.name if tmpl else tid[:8]
        self._set_status("\\u6a21\\u677f\\u300c" + tname + "\\u300d\\u5df2\\u5e94\\u7528")

    # ── search ────────────────────────────────────────────────────

    def _on_search(self):
        kw = self._search_box.text().strip()
        if not kw: return
        self._rpt_list.set_keyword(kw)
        results = self._engine.search_reports(kw)
        self._set_status(
            "\\u641c\\u7d22\\u300c" + kw + "\\u300d\\uff1a\\u627e\\u5230 "
            + str(len(results)) + " \\u4e2a\\u62a5\\u544a")

    def _on_reset_search(self):
        self._search_box.clear()
        self._rpt_list.set_keyword("")
        self._set_status("\\u5c31\\u7eea")

    # ── selection ─────────────────────────────────────────────────

    def _on_rpt_selected(self, rpt_id: str):
        self._rpt_detail.load(rpt_id)
        rpt = self._engine.get_report(rpt_id)
        if rpt:
            pub = " [\\u5df2\\u53d1\\u5e03]" if rpt.is_published else " [\\u8349\\u7a3f]"
            self._set_status("\\u62a5\\u544a: " + rpt.title + pub)

    # ── stats ─────────────────────────────────────────────────────

    def _on_stats_event(self, _=None):
        self._refresh_stats()
        rid = self._current_rpt_id()
        if rid:
            self._rpt_detail.load(rid)

    def _refresh_stats(self):
        s = self._engine.stats()
        self._stats_bar.setText(
            "\\u62a5\\u544a\\u603b\\u6570: " + str(s.get("reports", 0))
            + "    \\u5df2\\u53d1\\u5e03: " + str(s.get("published", 0))
            + "    \\u8349\\u7a3f: "         + str(s.get("drafts", 0))
            + "    \\u6a21\\u677f: "         + str(s.get("templates", 0)))

    def _set_status(self, msg: str):
        self._status.setText(msg)
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("ReportTab main OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
