"""write_exp_maintab.py — ExperimentTab main class"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\experiment_tab.py"
)

CODE = """

def _sep():
    line = QFrame()
    line.setFrameShape(QFrame.VLine)
    line.setStyleSheet("color:#dee2e6;")
    return line


class ExperimentTab(QWidget):
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
        self._btn_new_exp  = QPushButton("+ \\u65b0\\u5efa\\u5b9e\\u9a8c")
        self._btn_new_run  = QPushButton("\\u25b6 \\u65b0\\u5efa Run")
        self._btn_cmp      = QPushButton("\\U0001f4ca \\u5bf9\\u6bd4\\u9009\\u4e2d")
        self._btn_del      = QPushButton("\\U0001f5d1 \\u5220\\u9664")
        for btn in (self._btn_new_exp, self._btn_new_run,
                    self._btn_cmp, self._btn_del):
            btn.setFixedHeight(28); tb.addWidget(btn)
        tb.addWidget(_sep())
        tb.addStretch()
        tb.addWidget(QLabel("\\u641c\\u7d22:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("\\u5b9e\\u9a8c\\u540d / \\u6807\\u7b7e...")
        self._search_box.setFixedWidth(160); self._search_box.setFixedHeight(28)
        tb.addWidget(self._search_box)
        self._btn_search = QPushButton("\\u641c\\u7d22"); self._btn_search.setFixedSize(52, 28)
        self._btn_reset  = QPushButton("\\u91cd\\u7f6e"); self._btn_reset.setFixedSize(52, 28)
        tb.addWidget(self._btn_search); tb.addWidget(self._btn_reset)
        root.addLayout(tb)

        # ── stats bar ─────────────────────────────────────────────
        self._stats_bar = QLabel("\\u52a0\\u8f7d\\u4e2d...")
        self._stats_bar.setStyleSheet(
            "background:#f0f4ff;border:1px solid #c7d2fe;"
            "border-radius:4px;padding:4px 10px;"
            "color:#4a6cf7;font-size:12px;")
        root.addWidget(self._stats_bar)

        # ── main splitter (left | center | right) ─────────────────
        sp = QSplitter(Qt.Horizontal)

        self._exp_list = ExperimentList(self._engine)
        self._exp_list.setMinimumWidth(180)
        sp.addWidget(self._exp_list)

        self._detail = RunDetailPanel(self._engine)
        sp.addWidget(self._detail)

        self._compare = ComparePanel(self._engine)
        self._compare.setMinimumWidth(160)
        sp.addWidget(self._compare)

        sp.setSizes([220, 560, 360])
        sp.setStretchFactor(0, 0)
        sp.setStretchFactor(1, 1)
        sp.setStretchFactor(2, 0)
        root.addWidget(sp)

        # ── status bar ────────────────────────────────────────────
        self._status = QLabel("\\u5c31\\u7eea")
        self._status.setStyleSheet("color:#6c757d;font-size:11px;")
        root.addWidget(self._status)

        # ── signals ───────────────────────────────────────────────
        self._btn_new_exp.clicked.connect(self._on_new_exp)
        self._btn_new_run.clicked.connect(self._on_new_run)
        self._btn_cmp.clicked.connect(self._on_compare_checked)
        self._btn_del.clicked.connect(self._on_delete)
        self._btn_search.clicked.connect(self._on_search)
        self._btn_reset.clicked.connect(self._on_reset)
        self._search_box.returnPressed.connect(self._on_search)

        self._exp_list.experiment_selected.connect(self._on_exp_selected)
        self._exp_list.run_selected.connect(self._on_run_selected)
        self._exp_list.runs_for_compare.connect(self._compare.load_runs)

        for ev in (EVENT_RO_EXP_CREATED, EVENT_RO_EXP_UPDATED,
                   EVENT_RO_EXP_DELETED, EVENT_RO_EXP_COMPLETED,
                   EVENT_RO_EXP_FAILED,  EVENT_RO_RUN_CREATED,
                   EVENT_RO_RUN_COMPLETED, EVENT_RO_RUN_FAILED,
                   EVENT_RO_RUN_KILLED):
            self._engine.event_engine.register(ev, self._on_stats_event)

        self._refresh_stats()

    # ── experiment ops ────────────────────────────────────────────

    def _on_new_exp(self):
        dlg = ExperimentDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            exp = self._engine.create_experiment(
                name           = dlg.get_name(),
                description    = dlg.get_description(),
                hypothesis     = dlg.get_hypothesis(),
                objective      = dlg.get_objective(),
                primary_metric = dlg.get_primary_metric(),
                tags           = dlg.get_tags(),
            )
            self._set_status("\\u5b9e\\u9a8c\\u300c" + exp.name + "\\u300d\\u5df2\\u521b\\u5efa")
            self._refresh_stats()

    def _on_new_run(self):
        exp_id = self._exp_list.get_current_exp_id()
        if not exp_id:
            QMessageBox.warning(self, "\\u63d0\\u793a",
                                "\\u8bf7\\u5148\\u9009\\u62e9\\u4e00\\u4e2a\\u5b9e\\u9a8c\\u3002")
            return
        dlg = RunDialog(parent=self, experiment_id=exp_id)
        if dlg.exec() == QDialog.Accepted:
            params  = dlg.get_params()
            metrics = dlg.get_metrics()
            run = self._engine.start_run(
                experiment_id = exp_id,
                params        = params,
                git_commit    = dlg.get_git_commit(),
                data_version  = dlg.get_data_version(),
                tags          = dlg.get_tags(),
            )
            if run.name != dlg.get_name() and dlg.get_name():
                run.name = dlg.get_name()
                self._engine.experiment._run_repo.save(run)
            if metrics:
                for k, v in metrics.items():
                    self._engine.log_metric(run.run_id, k, v)
                self._engine.complete_run(run.run_id, metrics=metrics)
            self._detail.load(run.run_id)
            self._set_status("Run \\u300c" + run.name + "\\u300d\\u5df2\\u521b\\u5efa")
            self._refresh_stats()

    def _on_compare_checked(self):
        checked = self._exp_list._checked_runs
        if checked:
            self._compare.load_runs(list(checked))
            self._set_status("\\u5bf9\\u6bd4 " + str(len(checked)) + " \\u4e2a Run")
        else:
            self._set_status("\\u8bf7\\u5148\\u5728\\u5de6\\u4fa7\\u70b9\\u51fb Run \\u8282\\u70b9\\u52a0\\u5165\\u5bf9\\u6bd4")

    def _on_delete(self):
        exp_id = self._exp_list.selected_exp_id()
        if not exp_id:
            self._set_status("\\u8bf7\\u9009\\u62e9\\u4e00\\u4e2a\\u5b9e\\u9a8c\\u8282\\u70b9")
            return
        exp = self._engine.get_experiment(exp_id)
        if not exp:
            return
        if QMessageBox.question(
            self, "\\u786e\\u8ba4\\u5220\\u9664",
            "\\u786e\\u8ba4\\u5220\\u9664\\u5b9e\\u9a8c\\u300c" + exp.name + "\\u300d\\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self._engine.delete_experiment(exp_id)
            self._detail.clear_panel()
            self._set_status("\\u5b9e\\u9a8c\\u300c" + exp.name + "\\u300d\\u5df2\\u5220\\u9664")
            self._refresh_stats()

    # ── search ────────────────────────────────────────────────────

    def _on_search(self):
        kw = self._search_box.text().strip()
        if not kw:
            return
        self._exp_list.set_keyword(kw)
        results = self._engine.search_experiments(kw)
        self._set_status("\\u641c\\u7d22\\u300c" + kw + "\\u300d\\uff1a\\u627e\\u5230 "
                         + str(len(results)) + " \\u4e2a\\u5b9e\\u9a8c")

    def _on_reset(self):
        self._search_box.clear()
        self._exp_list.set_keyword("")
        self._detail.clear_panel()
        self._set_status("\\u5c31\\u7eea")

    # ── tree callbacks ────────────────────────────────────────────

    def _on_exp_selected(self, exp_id: str):
        exp = self._engine.get_experiment(exp_id)
        if exp:
            runs = self._engine.list_runs(exp_id)
            self._set_status(
                "\\u5b9e\\u9a8c\\uff1a" + exp.name
                + "  Runs: " + str(len(runs))
                + ("  \\u6700\\u4f73: " + exp.best_run_id[:8]
                   if exp.best_run_id else ""))

    def _on_run_selected(self, run_id: str):
        self._detail.load(run_id)
        run = self._engine.get_run(run_id)
        if run:
            self._set_status("Run: " + run.name + "  \\u72b6\\u6001: " + run.status.value)

    # ── stats ─────────────────────────────────────────────────────

    def _on_stats_event(self, _=None):
        self._refresh_stats()

    def _refresh_stats(self):
        s = self._engine.stats()
        exps  = s.get("experiments", 0)
        runs  = s.get("runs", 0)
        comp  = s.get("completed", 0)
        fail  = s.get("failed", 0)
        run_  = s.get("running", 0)
        self._stats_bar.setText(
            "\\u5b9e\\u9a8c: " + str(exps)
            + "    Runs: " + str(runs)
            + "    \\u8fd0\\u884c\\u4e2d: " + str(run_)
            + "    \\u5df2\\u5b8c\\u6210: " + str(comp)
            + "    \\u5931\\u8d25: " + str(fail))

    def _set_status(self, msg: str):
        self._status.setText(msg)
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("ExperimentTab OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
