"""write_exp_list.py — ExperimentList only"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\experiment_tab.py"
)

CODE = """

class ExperimentList(QWidget):
    experiment_selected = Signal(str)
    run_selected        = Signal(str)
    runs_for_compare    = Signal(list)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._filter_status = None
        self._keyword = ""
        self._checked_runs: List[str] = []
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)
        fb = QHBoxLayout()
        self._status_filter = QComboBox()
        self._status_filter.addItem("\\u5168\\u90e8\\u72b6\\u6001", None)
        for st in ExperimentStatus:
            self._status_filter.addItem(EXP_STATUS_ICON.get(st,"") + " " + st.value, st)
        self._status_filter.setFixedHeight(26)
        self._status_filter.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._status_filter, 1)
        root.addLayout(fb)
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(16)
        self._tree.setAnimated(True)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        root.addWidget(self._tree)
        self._cmp_btn = QPushButton("\\u5bf9\\u6bd4\\u9009\\u4e2d Run")
        self._cmp_btn.setFixedHeight(26)
        self._cmp_btn.clicked.connect(self._on_compare)
        root.addWidget(self._cmp_btn)
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.itemDoubleClicked.connect(
            lambda item, _: item.setExpanded(not item.isExpanded()))

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in (EVENT_RO_EXP_CREATED, EVENT_RO_EXP_UPDATED,
                   EVENT_RO_EXP_DELETED, EVENT_RO_EXP_COMPLETED,
                   EVENT_RO_EXP_FAILED,  EVENT_RO_RUN_CREATED,
                   EVENT_RO_RUN_COMPLETED, EVENT_RO_RUN_FAILED,
                   EVENT_RO_RUN_KILLED,  EVENT_RO_METRIC_LOGGED):
            ee.register(ev, self._on_event)

    def _on_event(self, _ev): self._refresh()
    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()
    def _on_filter(self, _): self._filter_status = self._status_filter.currentData(); self._refresh()

    def _refresh(self):
        expanded = set()
        root_inv = self._tree.invisibleRootItem()
        for i in range(root_inv.childCount()):
            item = root_inv.child(i)
            if item.isExpanded():
                expanded.add(item.data(0, ROLE_EXP_ID))
        self._tree.clear()
        exps = self._engine.list_experiments()
        if self._filter_status:
            exps = [e for e in exps if e.status == self._filter_status]
        if self._keyword:
            exps = [e for e in exps if self._keyword in e.name.lower()
                    or any(self._keyword in t.lower() for t in e.tags)]
        for exp in exps:
            ei = self._make_exp_item(exp)
            for run in self._engine.list_runs(exp.experiment_id):
                ei.addChild(self._make_run_item(run, exp))
            self._tree.addTopLevelItem(ei)
            if exp.experiment_id in expanded:
                ei.setExpanded(True)

    def _make_exp_item(self, exp):
        icon  = EXP_STATUS_ICON.get(exp.status, "\\u25cb")
        color = EXP_STATUS_COLOR.get(exp.status, "#6c757d")
        runs  = self._engine.list_runs(exp.experiment_id)
        label = icon + "  " + exp.name + "  (" + str(len(runs)) + " runs)"
        item  = QTreeWidgetItem([label])
        item.setData(0, ROLE_EXP_ID, exp.experiment_id)
        item.setData(0, ROLE_TYPE, NODE_EXP)
        item.setForeground(0, QBrush(QColor(color)))
        f = QFont(); f.setBold(True); item.setFont(0, f)
        return item

    def _make_run_item(self, run, exp):
        icon  = RUN_STATUS_ICON.get(run.status, "\\u25cb")
        pm    = exp.primary_metric
        pv    = ("  " + pm + "=" + str(round(run.metrics[pm], 4))
                 if pm and pm in run.metrics else "")
        best  = "  \\u2b50" if exp.best_run_id == run.run_id else ""
        dur   = ("  " + str(round(run.duration_sec, 1)) + "s"
                 if run.duration_sec else "")
        item  = QTreeWidgetItem([icon + "  " + run.name + pv + dur + best])
        item.setData(0, ROLE_RUN_ID, run.run_id)
        item.setData(0, ROLE_EXP_ID, run.experiment_id)
        item.setData(0, ROLE_TYPE, NODE_RUN)
        if run.status == RunStatus.FAILED:
            item.setForeground(0, QBrush(QColor("#dc3545")))
        elif run.status == RunStatus.COMPLETED:
            item.setForeground(0, QBrush(QColor("#0d6efd")))
        elif exp.best_run_id == run.run_id:
            item.setForeground(0, QBrush(QColor("#198754")))
        return item

    def _on_item_clicked(self, item, _col):
        ntype = item.data(0, ROLE_TYPE)
        if ntype == NODE_EXP:
            self.experiment_selected.emit(item.data(0, ROLE_EXP_ID))
        elif ntype == NODE_RUN:
            rid = item.data(0, ROLE_RUN_ID)
            self.run_selected.emit(rid)
            if rid in self._checked_runs:
                self._checked_runs.remove(rid)
            else:
                self._checked_runs.append(rid)

    def _on_compare(self):
        if self._checked_runs:
            self.runs_for_compare.emit(list(self._checked_runs))

    def _on_context_menu(self, pos):
        item  = self._tree.itemAt(pos)
        if not item: return
        ntype = item.data(0, ROLE_TYPE)
        menu  = QMenu(self)
        if ntype == NODE_EXP:
            eid = item.data(0, ROLE_EXP_ID)
            exp = self._engine.get_experiment(eid)
            if not exp: return
            a_edit  = menu.addAction("\\u270f  \\u7f16\\u8f91\\u5b9e\\u9a8c")
            menu.addSeparator()
            sm         = menu.addMenu("\\u8bbe\\u7f6e\\u72b6\\u6001")
            a_running  = sm.addAction("\\U0001f7e2  Running")
            a_complete = sm.addAction("\\U0001f535  Completed")
            a_archive  = sm.addAction("\\u26ab  Archived")
            menu.addSeparator()
            a_del = menu.addAction("\\U0001f5d1  \\u5220\\u9664")
            action = menu.exec(self._tree.viewport().mapToGlobal(pos))
            if action == a_edit:
                self.experiment_selected.emit(eid)
            elif action == a_running:
                self._engine.experiment.set_experiment_status(
                    eid, ExperimentStatus.RUNNING); self._refresh()
            elif action == a_complete:
                self._engine.experiment.set_experiment_status(
                    eid, ExperimentStatus.COMPLETED); self._refresh()
            elif action == a_archive:
                self._engine.experiment.set_experiment_status(
                    eid, ExperimentStatus.ARCHIVED); self._refresh()
            elif action == a_del:
                if QMessageBox.question(
                    self, "\\u786e\\u8ba4\\u5220\\u9664",
                    "\\u786e\\u8ba4\\u5220\\u9664\\u5b9e\\u9a8c\\u300c" + exp.name + "\\u300d\\uff1f",
                    QMessageBox.Yes | QMessageBox.No
                ) == QMessageBox.Yes:
                    self._engine.delete_experiment(eid)
        elif ntype == NODE_RUN:
            rid = item.data(0, ROLE_RUN_ID)
            run = self._engine.get_run(rid)
            if not run: return
            a_best = menu.addAction("\\u2b50  \\u6807\\u4e3a\\u6700\\u4f73 Run")
            a_kill = menu.addAction("\\u23f9  \\u7ec8\\u6b62 Run")
            a_cmp  = menu.addAction("\\U0001f4ca  \\u52a0\\u5165\\u5bf9\\u6bd4")
            action = menu.exec(self._tree.viewport().mapToGlobal(pos))
            if action == a_best:
                exp = self._engine.get_experiment(run.experiment_id)
                if exp:
                    exp.best_run_id = rid
                    self._engine.update_experiment(exp)
                    self._refresh()
            elif action == a_kill:
                self._engine.fail_run(rid, "\\u624b\\u52a8\\u7ec8\\u6b62")
                self._refresh()
            elif action == a_cmp:
                if rid not in self._checked_runs:
                    self._checked_runs.append(rid)
                self.runs_for_compare.emit(list(self._checked_runs))

    def selected_exp_id(self):
        item = self._tree.currentItem()
        return item.data(0, ROLE_EXP_ID) if item and item.data(0, ROLE_TYPE) == NODE_EXP else None

    def selected_run_id(self):
        item = self._tree.currentItem()
        return item.data(0, ROLE_RUN_ID) if item and item.data(0, ROLE_TYPE) == NODE_RUN else None

    def get_current_exp_id(self):
        item = self._tree.currentItem()
        return item.data(0, ROLE_EXP_ID) if item else None
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("ExperimentList OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
