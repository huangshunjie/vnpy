"""write_pl_maintab.py — PipelineTab main class"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\pipeline_tab.py"
)

CODE = """

class PipelineTab(QWidget):
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
        self._btn_node   = QPushButton("\\u2295 \\u6dfb\\u52a0\\u8282\\u70b9")
        self._btn_start  = QPushButton("\\u25b6 \\u8fd0\\u884c")
        self._btn_pause  = QPushButton("\\u23f8 \\u6682\\u505c")
        self._btn_reset  = QPushButton("\\U0001f504 \\u91cd\\u7f6e")
        self._btn_del    = QPushButton("\\U0001f5d1 \\u5220\\u9664")
        for btn in (self._btn_new, self._btn_node, self._btn_start,
                    self._btn_pause, self._btn_reset, self._btn_del):
            btn.setFixedHeight(28); tb.addWidget(btn)
        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#dee2e6;"); tb.addWidget(sep)
        tb.addStretch()
        tb.addWidget(QLabel("\\u641c\\u7d22:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Pipeline \\u540d\\u79f0...")
        self._search_box.setFixedWidth(160); self._search_box.setFixedHeight(28)
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
            "background:#fff3e0;border:1px solid #ffcc80;"
            "border-radius:4px;padding:4px 10px;"
            "color:#e65100;font-size:12px;")
        root.addWidget(self._stats_bar)

        # ── splitter ──────────────────────────────────────────────
        sp = QSplitter(Qt.Horizontal)
        self._pl_list = PipelineList(self._engine)
        self._pl_list.setMinimumWidth(200)
        sp.addWidget(self._pl_list)
        self._detail = PipelineDetail(self._engine)
        sp.addWidget(self._detail)
        sp.setSizes([240, 960])
        sp.setStretchFactor(0, 0); sp.setStretchFactor(1, 1)
        root.addWidget(sp)

        # ── status bar ────────────────────────────────────────────
        self._status = QLabel("\\u5c31\\u7eea")
        self._status.setStyleSheet("color:#6c757d;font-size:11px;")
        root.addWidget(self._status)

        # ── connect ───────────────────────────────────────────────
        self._pl_list.selected.connect(self._on_pl_selected)
        self._btn_new.clicked.connect(self._on_new)
        self._btn_node.clicked.connect(self._on_add_node)
        self._btn_start.clicked.connect(self._on_start)
        self._btn_pause.clicked.connect(self._on_pause)
        self._btn_reset.clicked.connect(self._on_reset_pl)
        self._btn_del.clicked.connect(self._on_delete)
        self._btn_search.clicked.connect(self._on_search)
        self._btn_reset_s.clicked.connect(self._on_reset_search)
        self._search_box.returnPressed.connect(self._on_search)

        for ev in (EVENT_RO_PL_CREATED, EVENT_RO_PL_UPDATED,
                   EVENT_RO_PL_DELETED, EVENT_RO_PL_STARTED,
                   EVENT_RO_PL_COMPLETED, EVENT_RO_PL_FAILED,
                   EVENT_RO_PL_PAUSED,   EVENT_RO_PL_RESET,
                   EVENT_RO_NODE_STARTED, EVENT_RO_NODE_COMPLETED,
                   EVENT_RO_NODE_FAILED,  EVENT_RO_NODE_SKIPPED):
            self._engine.event_engine.register(ev, self._on_stats_event)

        self._refresh_stats()

    # ── current pipeline ──────────────────────────────────────────

    def _current_pl_id(self) -> Optional[str]:
        return self._pl_list.selected_id()

    # ── ops ───────────────────────────────────────────────────────

    def _on_new(self):
        dlg = PipelineDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            pl = self._engine.create_pipeline(
                name        = dlg.get_name(),
                description = dlg.get_description(),
                author      = dlg.get_author(),
                schedule    = dlg.get_schedule(),
                tags        = dlg.get_tags(),
            )
            self._set_status("Pipeline \\u300c" + pl.name + "\\u300d\\u5df2\\u521b\\u5efa")
            self._refresh_stats()

    def _on_add_node(self):
        pid = self._current_pl_id()
        if not pid:
            self._set_status("\\u8bf7\\u5148\\u9009\\u62e9\\u4e00\\u4e2a Pipeline")
            return
        pl = self._engine.get_pipeline(pid)
        if not pl: return
        dlg = NodeDialog(parent=self, pipeline_id=pid,
                         existing_nodes=pl.nodes)
        if dlg.exec() == QDialog.Accepted:
            nd = self._engine.add_node(
                pipeline_id = pid,
                name        = dlg.get_name(),
                node_type   = dlg.get_node_type(),
                depends_on  = dlg.get_depends_on(),
                timeout_sec = dlg.get_timeout(),
                max_retries = dlg.get_max_retries(),
            )
            if nd:
                self._detail.load(pid)
                self._set_status(
                    "\\u8282\\u70b9\\u300c" + nd.name + "\\u300d\\u5df2\\u6dfb\\u52a0")

    def _on_start(self):
        pid = self._current_pl_id()
        if not pid:
            self._set_status("\\u8bf7\\u5148\\u9009\\u62e9 Pipeline"); return
        run = self._engine.start_pipeline(pid)
        if run:
            self._detail.load(pid)
            self._set_status("Pipeline \\u5df2\\u542f\\u52a8\\uff0cRun: " + run.run_id[:12])
        self._refresh_stats()

    def _on_pause(self):
        pid = self._current_pl_id()
        if not pid: return
        self._engine.pause_pipeline(pid)
        self._detail.load(pid)
        self._set_status("Pipeline \\u5df2\\u6682\\u505c")
        self._refresh_stats()

    def _on_reset_pl(self):
        pid = self._current_pl_id()
        if not pid: return
        self._engine.reset_pipeline(pid)
        self._detail.load(pid)
        self._set_status("Pipeline \\u5df2\\u91cd\\u7f6e")
        self._refresh_stats()

    def _on_delete(self):
        pid = self._current_pl_id()
        if not pid: return
        pl = self._engine.get_pipeline(pid)
        if not pl: return
        if QMessageBox.question(
            self, "\\u786e\\u8ba4\\u5220\\u9664",
            "\\u5220\\u9664 Pipeline \\u300c" + pl.name + "\\u300d\\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self._engine.delete_pipeline(pid)
            self._detail.clear_panel()
            self._set_status("Pipeline \\u300c" + pl.name + "\\u300d\\u5df2\\u5220\\u9664")
            self._refresh_stats()

    # ── search ────────────────────────────────────────────────────

    def _on_search(self):
        kw = self._search_box.text().strip()
        if not kw: return
        self._pl_list.set_keyword(kw)
        results = self._engine.search_pipelines(kw)
        self._set_status("\\u641c\\u7d22\\u300c" + kw + "\\u300d\\uff1a\\u627e\\u5230 "
                         + str(len(results)) + " \\u4e2a Pipeline")

    def _on_reset_search(self):
        self._search_box.clear()
        self._pl_list.set_keyword("")
        self._set_status("\\u5c31\\u7eea")

    # ── selection ─────────────────────────────────────────────────

    def _on_pl_selected(self, pl_id: str):
        self._detail.load(pl_id)
        pl = self._engine.get_pipeline(pl_id)
        if pl:
            self._set_status(
                "Pipeline: " + pl.name
                + "  \\u8282\\u70b9: " + str(len(pl.nodes))
                + "  \\u72b6\\u6001: " + pl.status.value)

    # ── stats ─────────────────────────────────────────────────────

    def _on_stats_event(self, _=None):
        self._refresh_stats()
        pid = self._current_pl_id()
        if pid:
            self._detail.load(pid)

    def _refresh_stats(self):
        s = self._engine.stats()
        self._stats_bar.setText(
            "Pipeline: " + str(s.get("pipelines", 0))
            + "    \\u8fd0\\u884c\\u4e2d: " + str(s.get("running", 0))
            + "    \\u5df2\\u5b8c\\u6210: " + str(s.get("completed", 0))
            + "    \\u5931\\u8d25: "     + str(s.get("failed", 0))
            + "    \\u8282\\u70b9\\u603b\\u6570: " + str(s.get("total_nodes", 0)))

    def _set_status(self, msg: str):
        self._status.setText(msg)
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("PipelineTab main OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
