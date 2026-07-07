"""write_pe_task_sched.py — append SchedulerPanel + TaskTab"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\task.py"
)

CODE = '''

class SchedulerPanel(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout()
        self._btn_add = QPushButton("\\u2795 \\u6dfb\\u52a0\\u8c03\\u5ea6\\u4efb\\u52a1")
        self._btn_add.setFixedHeight(26)
        self._btn_add.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_add.clicked.connect(self._on_add)
        tb.addWidget(self._btn_add)
        self._btn_trigger = QPushButton("\\u25b6 \\u7acb\\u5373\\u89e6\\u53d1")
        self._btn_trigger.setFixedHeight(26)
        self._btn_trigger.clicked.connect(self._on_trigger)
        tb.addWidget(self._btn_trigger)
        self._btn_remove = QPushButton("\\U0001f5d1 \\u5220\\u9664")
        self._btn_remove.setFixedHeight(26)
        self._btn_remove.setStyleSheet(
            "background:#ff4d4f;color:#fff;border-radius:4px;border:none;")
        self._btn_remove.clicked.connect(self._on_remove)
        tb.addWidget(self._btn_remove)
        tb.addStretch()
        root.addLayout(tb)
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            "\\u540d\\u79f0","Cron","\\u7c7b\\u578b","\\u4e0b\\u6b21\\u8fd0\\u884c",
            "\\u5df2\\u8fd0\\u884c\\u6b21\\u6570","\\u72b6\\u6001"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        root.addWidget(self._table)

    def refresh(self):
        if not self._engine: return
        jobs = self._engine.tasks.list_scheduled_jobs()
        self._table.setRowCount(0)
        for j in jobs:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(j.name))
            self._table.setItem(r, 1, QTableWidgetItem(j.cron_expr))
            self._table.setItem(r, 2, QTableWidgetItem(j.task_type.value))
            nxt = j.next_run.strftime("%m-%d %H:%M") if j.next_run else "\\u2014"
            self._table.setItem(r, 3, QTableWidgetItem(nxt))
            self._table.setItem(r, 4, QTableWidgetItem(str(j.run_count)))
            ei = QTableWidgetItem("\\u542f\\u7528" if j.enabled else "\\u7981\\u7528")
            ei.setForeground(QBrush(QColor("#52c41a" if j.enabled else "#ff4d4f")))
            self._table.setItem(r, 5, ei)
            for c in range(6):
                self._table.item(r, c).setData(ROLE_ID, j.job_id)

    def _selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None

    def _on_add(self):
        if not self._engine: return
        dlg = AddJobDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._engine.tasks.add_scheduled_job(
                name=dlg.get_name(), cron_expr=dlg.get_cron(),
                task_type=dlg.get_type(), priority=dlg.get_priority(),
                created_by=dlg.get_created_by())
            self.refresh()

    def _on_trigger(self):
        jid = self._selected_id()
        if jid and self._engine:
            self._engine.tasks.trigger_job(jid)

    def _on_remove(self):
        jid = self._selected_id()
        if jid and self._engine:
            self._engine.tasks.remove_scheduled_job(jid); self.refresh()


class TaskTab(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(3_000)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()
        if engine and not engine.tasks._started:
            engine.tasks.start()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12); root.setSpacing(8)
        hdr = QHBoxLayout()
        title = QLabel("\\u2699\\ufe0f  Distributed Task Execution")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet("font-size:11px;color:#8c8c8c;")
        hdr.addWidget(self._stats_lbl)
        btn = QPushButton("\\U0001f504 \\u5237\\u65b0")
        btn.setFixedSize(68, 26)
        btn.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;"
            "font-size:12px;border:none;")
        btn.clicked.connect(self._refresh)
        hdr.addWidget(btn)
        root.addLayout(hdr)
        self._sub = QTabWidget(); self._sub.setDocumentMode(True)
        self._task_list    = TaskList(self._engine)
        self._worker_panel = WorkerPanel(self._engine)
        self._sched_panel  = SchedulerPanel(self._engine)
        self._sub.addTab(self._task_list,    "\\U0001f4cb  \\u4efb\\u52a1\\u961f\\u5217")
        self._sub.addTab(self._worker_panel, "\\U0001f527  Worker \\u72b6\\u6001")
        self._sub.addTab(self._sched_panel,  "\\U0001f551  \\u8c03\\u5ea6\\u7ba1\\u7406")
        root.addWidget(self._sub, 1)
        self._status = QLabel("\\u5c31\\u7eea")
        self._status.setStyleSheet("font-size:11px;color:#6c757d;")
        root.addWidget(self._status)

    def _refresh(self):
        self._task_list.refresh()
        self._worker_panel.refresh()
        self._sched_panel.refresh()
        if self._engine:
            s = self._engine.tasks.stats()
            self._stats_lbl.setText(
                f"\\u961f\\u5217: {s.get('queue_size',0)}  "
                f"\\u8fd0\\u884c: {s.get('running',0)}  "
                f"Worker: {s.get('busy_workers',0)}/{s.get('total_workers',0)}")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("TaskTab OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
