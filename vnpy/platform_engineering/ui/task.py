"""
platform_engineering/ui/task.py
TaskTab — Phase 3
任务队列列表 + Worker 状态面板 + 调度管理
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox, QLineEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QSpinBox, QMenu, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush

if TYPE_CHECKING:
    from ..engine_main import PlatformEngine

from ..constant import TaskStatus, TaskType, TaskPriority, WorkerStatus

STATUS_COLOR = {
    TaskStatus.PENDING:   "#8c8c8c",
    TaskStatus.QUEUED:    "#1890ff",
    TaskStatus.RUNNING:   "#52c41a",
    TaskStatus.COMPLETED: "#52c41a",
    TaskStatus.FAILED:    "#ff4d4f",
    TaskStatus.CANCELLED: "#d9d9d9",
    TaskStatus.TIMEOUT:   "#faad14",
    TaskStatus.RETRYING:  "#fa8c16",
}
WORKER_COLOR = {
    WorkerStatus.IDLE:    "#52c41a",
    WorkerStatus.BUSY:    "#1890ff",
    WorkerStatus.OFFLINE: "#d9d9d9",
    WorkerStatus.ERROR:   "#ff4d4f",
}
PRIORITY_COLOR = {
    TaskPriority.LOW:    "#8c8c8c",
    TaskPriority.NORMAL: "#1890ff",
    TaskPriority.HIGH:   "#faad14",
    TaskPriority.URGENT: "#ff4d4f",
}
ROLE_ID = Qt.UserRole


class CreateTaskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u521b\u5efa\u4efb\u52a1")
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u4efb\u52a1\u4fe1\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit(); self._name.setPlaceholderText("\u4efb\u52a1\u540d\u79f0")
        form.addRow("\u540d\u79f0 *", self._name)
        self._type = QComboBox()
        for t in TaskType: self._type.addItem(t.value, t)
        form.addRow("\u7c7b\u578b", self._type)
        self._priority = QComboBox()
        for p in TaskPriority: self._priority.addItem(p.name, p)
        self._priority.setCurrentIndex(1)
        form.addRow("\u4f18\u5148\u7ea7", self._priority)
        self._timeout = QSpinBox(); self._timeout.setRange(10, 86400)
        self._timeout.setValue(3600); self._timeout.setSuffix(" \u79d2")
        form.addRow("\u8d85\u65f6", self._timeout)
        self._retries = QSpinBox(); self._retries.setRange(0, 10)
        self._retries.setValue(3)
        form.addRow("\u6700\u5927\u91cd\u8bd5", self._retries)
        self._created_by = QLineEdit()
        form.addRow("\u521b\u5efa\u4eba", self._created_by)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u521b\u5efa")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        if not self._name.text().strip(): self._name.setFocus(); return
        self.accept()

    def get_name(self)       -> str:          return self._name.text().strip()
    def get_type(self)       -> TaskType:     return self._type.currentData()
    def get_priority(self)   -> TaskPriority: return self._priority.currentData()
    def get_timeout(self)    -> int:          return self._timeout.value()
    def get_retries(self)    -> int:          return self._retries.value()
    def get_created_by(self) -> str:          return self._created_by.text().strip()


class AddJobDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u6dfb\u52a0\u8c03\u5ea6\u4efb\u52a1")
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u8c03\u5ea6\u914d\u7f6e")
        form = QFormLayout(grp)
        self._name = QLineEdit(); self._name.setPlaceholderText("\u4efb\u52a1\u540d\u79f0")
        form.addRow("\u540d\u79f0 *", self._name)
        self._cron = QLineEdit(); self._cron.setPlaceholderText("*/30 * * * *")
        form.addRow("Cron \u8868\u8fbe\u5f0f *", self._cron)
        self._type = QComboBox()
        for t in TaskType: self._type.addItem(t.value, t)
        form.addRow("\u7c7b\u578b", self._type)
        self._priority = QComboBox()
        for p in TaskPriority: self._priority.addItem(p.name, p)
        self._priority.setCurrentIndex(1)
        form.addRow("\u4f18\u5148\u7ea7", self._priority)
        self._created_by = QLineEdit()
        form.addRow("\u521b\u5efa\u4eba", self._created_by)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u6dfb\u52a0")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        for w in (self._name, self._cron):
            if not w.text().strip(): w.setFocus(); return
        self.accept()

    def get_name(self)       -> str:          return self._name.text().strip()
    def get_cron(self)       -> str:          return self._cron.text().strip()
    def get_type(self)       -> TaskType:     return self._type.currentData()
    def get_priority(self)   -> TaskPriority: return self._priority.currentData()
    def get_created_by(self) -> str:          return self._created_by.text().strip()


class TaskList(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._status_filter = None
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_create = QPushButton("\u2795 \u521b\u5efa\u4efb\u52a1")
        self._btn_create.setFixedHeight(26)
        self._btn_create.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_create.clicked.connect(self._on_create)
        tb.addWidget(self._btn_create)
        self._btn_cancel = QPushButton("\u274c \u53d6\u6d88")
        self._btn_cancel.setFixedHeight(26)
        self._btn_cancel.setStyleSheet(
            "background:#ff4d4f;color:#fff;border-radius:4px;border:none;")
        self._btn_cancel.clicked.connect(self._on_cancel)
        tb.addWidget(self._btn_cancel)
        self._btn_retry = QPushButton("\U0001f504 \u91cd\u8bd5")
        self._btn_retry.setFixedHeight(26)
        self._btn_retry.clicked.connect(self._on_retry)
        tb.addWidget(self._btn_retry)
        self._filter_combo = QComboBox(); self._filter_combo.setFixedHeight(26)
        self._filter_combo.addItem("\u5168\u90e8\u4efb\u52a1", None)
        for s in TaskStatus: self._filter_combo.addItem(s.value, s)
        self._filter_combo.currentIndexChanged.connect(self._on_filter)
        tb.addWidget(self._filter_combo)
        self._search = QLineEdit()
        self._search.setPlaceholderText("\u641c\u7d22...")
        self._search.setFixedHeight(26); self._search.setFixedWidth(140)
        self._search.textChanged.connect(self._on_search)
        tb.addWidget(self._search)
        tb.addStretch()
        self._count_lbl = QLabel("0 \u6761")
        self._count_lbl.setStyleSheet("font-size:14px;color:#8c8c8c;")
        tb.addWidget(self._count_lbl)
        root.addLayout(tb)
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels([
            "\u4efb\u52a1\u540d\u79f0","\u7c7b\u578b","\u4f18\u5148\u7ea7",
            "\u72b6\u6001","\u8fdb\u5ea6","Worker","\u521b\u5efa\u65f6\u95f4"])
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
                QTableWidgetItem(t.worker_id[:8] if t.worker_id else "\u2014"))
            self._table.setItem(r, 6,
                QTableWidgetItem(t.created_at.strftime("%m-%d %H:%M")))
            for c in range(7):
                self._table.item(r, c).setData(ROLE_ID, t.task_id)
        self._count_lbl.setText(f"{self._table.rowCount()} \u6761")

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
        a_cancel = menu.addAction("\u274c  \u53d6\u6d88\u4efb\u52a1")
        a_retry  = menu.addAction("\U0001f504  \u91cd\u8bd5\u4efb\u52a1")
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
        self._btn_add = QPushButton("\u2795 \u6dfb\u52a0 Worker")
        self._btn_add.setFixedHeight(26)
        self._btn_add.setStyleSheet(
            "background:#52c41a;color:#fff;border-radius:4px;border:none;")
        self._btn_add.clicked.connect(self._on_add)
        tb.addWidget(self._btn_add); tb.addStretch()
        root.addLayout(tb)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "Worker ID","\u540d\u79f0","\u72b6\u6001",
            "\u5df2\u5b8c\u6210","\u5f53\u524d\u4efb\u52a1"])
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
                QTableWidgetItem(w.current_task[:12] if w.current_task else "\u2014"))

    def _on_add(self):
        if self._engine: self._engine.tasks.add_worker(); self.refresh()


class SchedulerPanel(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout()
        self._btn_add = QPushButton("\u2795 \u6dfb\u52a0\u8c03\u5ea6\u4efb\u52a1")
        self._btn_add.setFixedHeight(26)
        self._btn_add.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_add.clicked.connect(self._on_add)
        tb.addWidget(self._btn_add)
        self._btn_trigger = QPushButton("\u25b6 \u7acb\u5373\u89e6\u53d1")
        self._btn_trigger.setFixedHeight(26)
        self._btn_trigger.clicked.connect(self._on_trigger)
        tb.addWidget(self._btn_trigger)
        self._btn_remove = QPushButton("\U0001f5d1 \u5220\u9664")
        self._btn_remove.setFixedHeight(26)
        self._btn_remove.setStyleSheet(
            "background:#ff4d4f;color:#fff;border-radius:4px;border:none;")
        self._btn_remove.clicked.connect(self._on_remove)
        tb.addWidget(self._btn_remove)
        tb.addStretch()
        root.addLayout(tb)
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            "\u540d\u79f0","Cron","\u7c7b\u578b","\u4e0b\u6b21\u8fd0\u884c",
            "\u5df2\u8fd0\u884c\u6b21\u6570","\u72b6\u6001"])
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
            nxt = j.next_run.strftime("%m-%d %H:%M") if j.next_run else "\u2014"
            self._table.setItem(r, 3, QTableWidgetItem(nxt))
            self._table.setItem(r, 4, QTableWidgetItem(str(j.run_count)))
            ei = QTableWidgetItem("\u542f\u7528" if j.enabled else "\u7981\u7528")
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
        title = QLabel("\u2699\ufe0f  Distributed Task Execution")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet("font-size:14px;color:#8c8c8c;")
        hdr.addWidget(self._stats_lbl)
        btn = QPushButton("\U0001f504 \u5237\u65b0")
        btn.setFixedSize(68, 26)
        btn.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;"
            "font-size:14px;border:none;")
        btn.clicked.connect(self._refresh)
        hdr.addWidget(btn)
        root.addLayout(hdr)
        self._sub = QTabWidget(); self._sub.setDocumentMode(True)
        self._task_list    = TaskList(self._engine)
        self._worker_panel = WorkerPanel(self._engine)
        self._sched_panel  = SchedulerPanel(self._engine)
        self._sub.addTab(self._task_list,    "\U0001f4cb  \u4efb\u52a1\u961f\u5217")
        self._sub.addTab(self._worker_panel, "\U0001f527  Worker \u72b6\u6001")
        self._sub.addTab(self._sched_panel,  "\U0001f551  \u8c03\u5ea6\u7ba1\u7406")
        root.addWidget(self._sub, 1)
        self._status = QLabel("\u5c31\u7eea")
        self._status.setStyleSheet("font-size:14px;color:#6c757d;")
        root.addWidget(self._status)

    def _refresh(self):
        self._task_list.refresh()
        self._worker_panel.refresh()
        self._sched_panel.refresh()
        if self._engine:
            s = self._engine.tasks.stats()
            self._stats_lbl.setText(
                f"\u961f\u5217: {s.get('queue_size',0)}  "
                f"\u8fd0\u884c: {s.get('running',0)}  "
                f"Worker: {s.get('busy_workers',0)}/{s.get('total_workers',0)}")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
