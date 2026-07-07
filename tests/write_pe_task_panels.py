"""write_pe_task_panels.py — append TaskList + WorkerPanel"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\task.py"
)

CODE = '''

class TaskList(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._status_filter = None
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_create = QPushButton("\\u2795 \\u521b\\u5efa\\u4efb\\u52a1")
        self._btn_create.setFixedHeight(26)
        self._btn_create.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_create.clicked.connect(self._on_create)
        tb.addWidget(self._btn_create)
        self._btn_cancel = QPushButton("\\u274c \\u53d6\\u6d88")
        self._btn_cancel.setFixedHeight(26)
        self._btn_cancel.setStyleSheet(
            "background:#ff4d4f;color:#fff;border-radius:4px;border:none;")
        self._btn_cancel.clicked.connect(self._on_cancel)
        tb.addWidget(self._btn_cancel)
        self._btn_retry = QPushButton("\\U0001f504 \\u91cd\\u8bd5")
        self._btn_retry.setFixedHeight(26)
        self._btn_retry.clicked.connect(self._on_retry)
        tb.addWidget(self._btn_retry)
        self._filter_combo = QComboBox(); self._filter_combo.setFixedHeight(26)
        self._filter_combo.addItem("\\u5168\\u90e8\\u4efb\\u52a1", None)
        for s in TaskStatus: self._filter_combo.addItem(s.value, s)
        self._filter_combo.currentIndexChanged.connect(self._on_filter)
        tb.addWidget(self._filter_combo)
        self._search = QLineEdit()
        self._search.setPlaceholderText("\\u641c\\u7d22...")
        self._search.setFixedHeight(26); self._search.setFixedWidth(140)
        self._search.textChanged.connect(self._on_search)
        tb.addWidget(self._search)
        tb.addStretch()
        self._count_lbl = QLabel("0 \\u6761")
        self._count_lbl.setStyleSheet("font-size:11px;color:#8c8c8c;")
        tb.addWidget(self._count_lbl)
        root.addLayout(tb)
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels([
            "\\u4efb\\u52a1\\u540d\\u79f0","\\u7c7b\\u578b","\\u4f18\\u5148\\u7ea7",
            "\\u72b6\\u6001","\\u8fdb\\u5ea6","Worker","\\u521b\\u5efa\\u65f6\\u95f4"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_ctx)
        root.addWidget(self._table)

    def refresh(self):
        if not self._engine: return
        kw = self._search.text().strip()
        tasks = (self._engine.tasks.search_tasks(kw) if kw
                 else self._engine.tasks.list_tasks(status=self._status_filter))
        self._table.setRowCount(0)
        for t in tasks:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(t.name))
            self._table.setItem(r, 1, QTableWidgetItem(t.task_type.value))
            pc = PRIORITY_COLOR.get(t.priority, "#1890ff")
            pi = QTableWidgetItem(t.priority.name)
            pi.setForeground(QBrush(QColor(pc)))
            self._table.setItem(r, 2, pi)
            sc = STATUS_COLOR.get(t.status, "#8c8c8c")
            si = QTableWidgetItem(t.status.value)
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 3, si)
            self._table.setItem(r, 4, QTableWidgetItem(f"{t.progress*100:.0f}%"))
            self._table.setItem(r, 5,
                QTableWidgetItem(t.worker_id[:8] if t.worker_id else "\\u2014"))
            self._table.setItem(r, 6,
                QTableWidgetItem(t.created_at.strftime("%m-%d %H:%M")))
            for c in range(7):
                self._table.item(r, c).setData(ROLE_ID, t.task_id)
        self._count_lbl.setText(f"{self._table.rowCount()} \\u6761")

    def _selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None

    def _on_filter(self, _):
        self._status_filter = self._filter_combo.currentData(); self.refresh()

    def _on_search(self, _): self.refresh()

    def _on_create(self):
        if not self._engine: return
        dlg = CreateTaskDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._engine.tasks.create_task(
                name=dlg.get_name(), task_type=dlg.get_type(),
                priority=dlg.get_priority(), timeout_secs=dlg.get_timeout(),
                max_retries=dlg.get_retries(), created_by=dlg.get_created_by())
            self.refresh()

    def _on_cancel(self):
        tid = self._selected_id()
        if tid and self._engine: self._engine.tasks.cancel_task(tid); self.refresh()

    def _on_retry(self):
        tid = self._selected_id()
        if tid and self._engine: self._engine.tasks.retry_task(tid); self.refresh()

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        tid  = item.data(ROLE_ID)
        menu = QMenu(self)
        a_cancel = menu.addAction("\\u274c  \\u53d6\\u6d88\\u4efb\\u52a1")
        a_retry  = menu.addAction("\\U0001f504  \\u91cd\\u8bd5\\u4efb\\u52a1")
        act = menu.exec(self._table.viewport().mapToGlobal(pos))
        if act == a_cancel and self._engine:
            self._engine.tasks.cancel_task(tid); self.refresh()
        elif act == a_retry and self._engine:
            self._engine.tasks.retry_task(tid); self.refresh()


class WorkerPanel(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout()
        self._btn_add = QPushButton("\\u2795 \\u6dfb\\u52a0 Worker")
        self._btn_add.setFixedHeight(26)
        self._btn_add.setStyleSheet(
            "background:#52c41a;color:#fff;border-radius:4px;border:none;")
        self._btn_add.clicked.connect(self._on_add)
        tb.addWidget(self._btn_add); tb.addStretch()
        root.addLayout(tb)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "Worker ID","\\u540d\\u79f0","\\u72b6\\u6001",
            "\\u5df2\\u5b8c\\u6210","\\u5f53\\u524d\\u4efb\\u52a1"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        root.addWidget(self._table)

    def refresh(self):
        if not self._engine: return
        workers = self._engine.tasks.list_workers()
        self._table.setRowCount(0)
        for w in workers:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(w.worker_id[:12]))
            self._table.setItem(r, 1, QTableWidgetItem(w.name))
            sc = WORKER_COLOR.get(w.status, "#8c8c8c")
            si = QTableWidgetItem(w.status.value.upper())
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 2, si)
            self._table.setItem(r, 3, QTableWidgetItem(str(w.task_count)))
            self._table.setItem(r, 4,
                QTableWidgetItem(w.current_task[:12] if w.current_task else "\\u2014"))

    def _on_add(self):
        if self._engine: self._engine.tasks.add_worker(); self.refresh()
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("panels OK, lines:", len(full.splitlines()))
