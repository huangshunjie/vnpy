"""
research_ops/ui/experiment_tab.py  Phase 3 - Experiment Tracking System
"""
from __future__ import annotations
from typing import List, Optional, Dict
import math

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QMenu, QMessageBox, QFrame,
    QTableWidget, QTableWidgetItem, QCheckBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QRect, QPoint, QSize
from PySide6.QtGui import (
    QColor, QFont, QBrush, QPainter, QPen,
    QLinearGradient, QPainterPath,
)

from vnpy.event import Event
from ..main_engine import ResearchOpsEngine
from ..model.experiment_model import ExperimentRecord, RunRecord, MetricPoint
from ..constant import ExperimentStatus, RunStatus
from ..event import (
    EVENT_RO_EXP_CREATED, EVENT_RO_EXP_UPDATED,
    EVENT_RO_EXP_DELETED, EVENT_RO_EXP_COMPLETED,
    EVENT_RO_EXP_FAILED,
    EVENT_RO_RUN_CREATED, EVENT_RO_RUN_COMPLETED,
    EVENT_RO_RUN_FAILED, EVENT_RO_RUN_KILLED,
    EVENT_RO_METRIC_LOGGED,
)

EXP_STATUS_ICON = {
    ExperimentStatus.DRAFT:     "\u25cb",
    ExperimentStatus.RUNNING:   "\U0001f7e2",
    ExperimentStatus.COMPLETED: "\U0001f535",
    ExperimentStatus.FAILED:    "\U0001f534",
    ExperimentStatus.ARCHIVED:  "\u26ab",
}
RUN_STATUS_ICON = {
    RunStatus.PENDING:   "\u23f3",
    RunStatus.RUNNING:   "\U0001f7e1",
    RunStatus.COMPLETED: "\U0001f535",
    RunStatus.FAILED:    "\U0001f534",
    RunStatus.KILLED:    "\u26ab",
}
EXP_STATUS_COLOR = {
    ExperimentStatus.DRAFT:     "#6c757d",
    ExperimentStatus.RUNNING:   "#198754",
    ExperimentStatus.COMPLETED: "#0d6efd",
    ExperimentStatus.FAILED:    "#dc3545",
    ExperimentStatus.ARCHIVED:  "#adb5bd",
}

ROLE_EXP_ID = Qt.UserRole
ROLE_RUN_ID = Qt.UserRole + 1
ROLE_TYPE   = Qt.UserRole + 2
NODE_EXP    = "exp"
NODE_RUN    = "run"

# chart colors for up to 8 series
CHART_COLORS = [
    "#4a6cf7", "#198754", "#dc3545", "#fd7e14",
    "#6f42c1", "#0dcaf0", "#ffc107", "#6c757d",
]


# =================================================================
# ExperimentDialog
# =================================================================

class ExperimentDialog(QDialog):
    def __init__(self, parent=None, record: Optional[ExperimentRecord] = None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\u7f16\u8f91\u5b9e\u9a8c" if self._editing
            else "\u65b0\u5efa\u5b9e\u9a8c")
        self.setMinimumWidth(500)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u5b9e\u9a8c\u4fe1\u606f")
        form = QFormLayout(grp)

        self._name = QLineEdit()
        self._name.setPlaceholderText("\u5b9e\u9a8c\u540d\u79f0")
        form.addRow("\u540d\u79f0 *", self._name)

        self._desc = QTextEdit(); self._desc.setFixedHeight(56)
        form.addRow("\u63cf\u8ff0", self._desc)

        self._hypothesis = QTextEdit(); self._hypothesis.setFixedHeight(56)
        self._hypothesis.setPlaceholderText("\u7814\u7a76\u5047\u8bbe")
        form.addRow("\u5047\u8bbe", self._hypothesis)

        self._objective = QLineEdit()
        self._objective.setPlaceholderText("\u5b9e\u9a8c\u76ee\u6807")
        form.addRow("\u76ee\u6807", self._objective)

        self._primary_metric = QLineEdit()
        self._primary_metric.setPlaceholderText("\u4e3b\u8981\u6307\u6807\uff0c\u5982 sharpe / ic")
        form.addRow("\u4e3b\u8981\u6307\u6807", self._primary_metric)

        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)

        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._name.setText(r.name)
        self._desc.setPlainText(r.description)
        self._hypothesis.setPlainText(r.hypothesis)
        self._objective.setText(r.objective)
        self._primary_metric.setText(r.primary_metric)
        self._tags.setText(", ".join(r.tags))

    def _on_ok(self):
        if not self._name.text().strip():
            self._name.setFocus(); return
        self.accept()

    def _split(self, t):
        return [x.strip() for x in t.split(",") if x.strip()]

    def get_name(self)           -> str:       return self._name.text().strip()
    def get_description(self)    -> str:       return self._desc.toPlainText().strip()
    def get_hypothesis(self)     -> str:       return self._hypothesis.toPlainText().strip()
    def get_objective(self)      -> str:       return self._objective.text().strip()
    def get_primary_metric(self) -> str:       return self._primary_metric.text().strip()
    def get_tags(self)           -> List[str]: return self._split(self._tags.text())


# =================================================================
# RunDialog
# =================================================================

class RunDialog(QDialog):
    def __init__(self, parent=None, experiment_id: str = ""):
        super().__init__(parent)
        self._experiment_id = experiment_id
        self.setWindowTitle("\u65b0\u5efa Run")
        self.setMinimumWidth(500)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)

        grp = QGroupBox("Run \u4fe1\u606f")
        form = QFormLayout(grp)

        self._name = QLineEdit()
        self._name.setPlaceholderText("Run \u540d\u79f0\uff08\u53ef\u7559\u7a7a\u81ea\u52a8\u751f\u6210\uff09")
        form.addRow("\u540d\u79f0", self._name)

        self._git = QLineEdit()
        self._git.setPlaceholderText("Git commit hash")
        form.addRow("Git Commit", self._git)

        self._data_ver = QLineEdit()
        self._data_ver.setPlaceholderText("\u6570\u636e\u7248\u672c\uff0c\u5982 v2024Q1")
        form.addRow("\u6570\u636e\u7248\u672c", self._data_ver)

        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)

        root.addWidget(grp)

        # params
        params_grp = QGroupBox("\u8d85\u53c2\u6570\uff08key=value \u6bcf\u884c\u4e00\u4e2a\uff09")
        pl = QVBoxLayout(params_grp)
        self._params_edit = QTextEdit()
        self._params_edit.setFixedHeight(80)
        self._params_edit.setPlaceholderText(
            "lookback=20\nthreshold=0.05\nuniverse=HS300")
        pl.addWidget(self._params_edit)
        root.addWidget(params_grp)

        # metrics
        metrics_grp = QGroupBox(
            "\u521d\u59cb\u6307\u6807\uff08\u53ef\u7559\u7a7a\uff0c\u8fd0\u884c\u540e\u624b\u52a8\u8bb0\u5f55\uff09")
        ml = QVBoxLayout(metrics_grp)
        self._metrics_edit = QTextEdit()
        self._metrics_edit.setFixedHeight(80)
        self._metrics_edit.setPlaceholderText(
            "sharpe=1.85\nic=0.046\nmax_drawdown=-0.12")
        ml.addWidget(self._metrics_edit)
        root.addWidget(metrics_grp)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u521b\u5efa Run")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _parse_kv(self, text: str) -> dict:
        result = {}
        for line in text.strip().splitlines():
            line = line.strip()
            if "=" in line:
                k, _, v = line.partition("=")
                k = k.strip(); v = v.strip()
                if k:
                    try:
                        result[k] = float(v) if "." in v else int(v)
                    except ValueError:
                        result[k] = v
        return result

    def _split(self, t):
        return [x.strip() for x in t.split(",") if x.strip()]

    def get_name(self)         -> str:        return self._name.text().strip()
    def get_git_commit(self)   -> str:        return self._git.text().strip()
    def get_data_version(self) -> str:        return self._data_ver.text().strip()
    def get_tags(self)         -> List[str]:  return self._split(self._tags.text())
    def get_params(self)       -> dict:       return self._parse_kv(self._params_edit.toPlainText())
    def get_metrics(self)      -> dict:
        raw = self._parse_kv(self._metrics_edit.toPlainText())
        return {k: float(v) for k, v in raw.items() if isinstance(v, (int, float))}
    def get_experiment_id(self) -> str:       return self._experiment_id


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
        self._status_filter.addItem("\u5168\u90e8\u72b6\u6001", None)
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
        self._cmp_btn = QPushButton("\u5bf9\u6bd4\u9009\u4e2d Run")
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
        icon  = EXP_STATUS_ICON.get(exp.status, "\u25cb")
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
        icon  = RUN_STATUS_ICON.get(run.status, "\u25cb")
        pm    = exp.primary_metric
        pv    = ("  " + pm + "=" + str(round(run.metrics[pm], 4))
                 if pm and pm in run.metrics else "")
        best  = "  \u2b50" if exp.best_run_id == run.run_id else ""
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
            a_edit  = menu.addAction("\u270f  \u7f16\u8f91\u5b9e\u9a8c")
            menu.addSeparator()
            sm         = menu.addMenu("\u8bbe\u7f6e\u72b6\u6001")
            a_running  = sm.addAction("\U0001f7e2  Running")
            a_complete = sm.addAction("\U0001f535  Completed")
            a_archive  = sm.addAction("\u26ab  Archived")
            menu.addSeparator()
            a_del = menu.addAction("\U0001f5d1  \u5220\u9664")
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
                    self, "\u786e\u8ba4\u5220\u9664",
                    "\u786e\u8ba4\u5220\u9664\u5b9e\u9a8c\u300c" + exp.name + "\u300d\uff1f",
                    QMessageBox.Yes | QMessageBox.No
                ) == QMessageBox.Yes:
                    self._engine.delete_experiment(eid)
        elif ntype == NODE_RUN:
            rid = item.data(0, ROLE_RUN_ID)
            run = self._engine.get_run(rid)
            if not run: return
            a_best = menu.addAction("\u2b50  \u6807\u4e3a\u6700\u4f73 Run")
            a_kill = menu.addAction("\u23f9  \u7ec8\u6b62 Run")
            a_cmp  = menu.addAction("\U0001f4ca  \u52a0\u5165\u5bf9\u6bd4")
            action = menu.exec(self._tree.viewport().mapToGlobal(pos))
            if action == a_best:
                exp = self._engine.get_experiment(run.experiment_id)
                if exp:
                    exp.best_run_id = rid
                    self._engine.update_experiment(exp)
                    self._refresh()
            elif action == a_kill:
                self._engine.fail_run(rid, "\u624b\u52a8\u7ec8\u6b62")
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


class MetricChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._series: Dict[str, List[MetricPoint]] = {}
        self._title  = ""
        self.setMinimumHeight(160)
        self.setStyleSheet(
            "background:#fafafa;border:1px solid #dee2e6;border-radius:4px;")
        self._hover_pos = None
        self.setMouseTracking(True)

    def set_series(self, series: Dict[str, List[MetricPoint]], title: str = ""):
        self._series = series
        self._title  = title
        self.update()

    def clear(self):
        self._series = {}; self._title = ""; self.update()

    def mouseMoveEvent(self, event):
        self._hover_pos = event.position().toPoint(); self.update()

    def leaveEvent(self, _ev):
        self._hover_pos = None; self.update()

    def paintEvent(self, _ev):
        if not self._series:
            p = QPainter(self)
            p.setPen(QColor("#adb5bd"))
            p.setFont(QFont("Arial", 11))
            p.drawText(self.rect(), Qt.AlignCenter, "\u6682\u65e0\u6307\u6807\u6570\u636e")
            p.end(); return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._draw(p); p.end()

    def _draw(self, p: QPainter):
        W, H = self.width(), self.height()
        PL, PR, PT, PB = 52, 16, 28, 36

        all_vals = [pt.value for pts in self._series.values() for pt in pts]
        all_steps = [pt.step for pts in self._series.values() for pt in pts]
        if not all_vals:
            return

        y_min, y_max = min(all_vals), max(all_vals)
        x_min, x_max = min(all_steps), max(all_steps)
        yr = y_max - y_min or 1e-9
        xr = x_max - x_min or 1

        def tx(s):  return PL + (s - x_min) / xr * (W - PL - PR)
        def ty(v):  return PT + (1 - (v - y_min) / yr) * (H - PT - PB)

        # grid
        p.setPen(QPen(QColor("#dee2e6"), 1, Qt.DashLine))
        for i in range(5):
            y = PT + i * (H - PT - PB) / 4
            p.drawLine(int(PL), int(y), int(W - PR), int(y))

        # axes
        p.setPen(QPen(QColor("#adb5bd"), 1))
        p.drawLine(int(PL), PT, int(PL), H - PB)
        p.drawLine(int(PL), H - PB, W - PR, H - PB)

        # y labels
        p.setFont(QFont("Consolas", 8))
        p.setPen(QColor("#6c757d"))
        for i in range(5):
            v = y_min + (1 - i / 4) * yr
            y = PT + i * (H - PT - PB) / 4
            p.drawText(QRect(0, int(y) - 8, PL - 4, 16),
                       Qt.AlignRight | Qt.AlignVCenter, "{:.4g}".format(v))

        # title
        if self._title:
            p.setFont(QFont("Arial", 9))
            p.setPen(QColor("#495057"))
            p.drawText(QRect(PL, 4, W - PL - PR, 18), Qt.AlignCenter, self._title)

        # series
        legend_x = PL + 8
        nearest_pt = None; nearest_dist = 1e9; nearest_name = ""
        for idx, (name, pts) in enumerate(self._series.items()):
            if not pts: continue
            color = QColor(CHART_COLORS[idx % len(CHART_COLORS)])
            p.setPen(QPen(color, 2))
            sorted_pts = sorted(pts, key=lambda x: x.step)
            path = QPainterPath()
            for i, pt in enumerate(sorted_pts):
                x, y = tx(pt.step), ty(pt.value)
                if i == 0: path.moveTo(x, y)
                else:       path.lineTo(x, y)
            p.drawPath(path)
            p.setBrush(color)
            for pt in sorted_pts:
                p.drawEllipse(QPoint(int(tx(pt.step)), int(ty(pt.value))), 3, 3)
            p.setBrush(Qt.NoBrush)
            # legend row
            ly = H - PB + 6 + (idx // 3) * 14
            p.fillRect(int(legend_x), int(ly), 10, 8, color)
            p.setFont(QFont("Arial", 8))
            p.setPen(QColor("#495057"))
            p.drawText(int(legend_x + 13), int(ly + 8), name)
            legend_x += max(len(name) * 6 + 20, 80)
            # hover nearest
            if self._hover_pos:
                for pt in sorted_pts:
                    d = abs(tx(pt.step) - self._hover_pos.x())
                    if d < nearest_dist:
                        nearest_dist = d; nearest_pt = pt; nearest_name = name

        # tooltip
        if self._hover_pos and nearest_pt and nearest_dist < 20:
            tip = nearest_name + " step=" + str(nearest_pt.step) + " val=" + "{:.6g}".format(nearest_pt.value)
            p.setFont(QFont("Arial", 8))
            fm  = p.fontMetrics()
            tw  = fm.horizontalAdvance(tip)
            ttx = min(int(tx(nearest_pt.step)) + 6, W - tw - 8)
            tty = max(int(ty(nearest_pt.value)) - 20, 4)
            p.fillRect(ttx, tty, tw + 8, 16, QColor(255, 255, 255, 210))
            p.setPen(QColor("#495057"))
            p.drawText(ttx + 4, tty + 12, tip)


class RunDetailPanel(QTabWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._run_id  = None
        self._init_ui()

    def _init_ui(self):
        self.setTabPosition(QTabWidget.North)
        self.setDocumentMode(True)

        # ── Tab1: overview ────────────────────────────────────────
        ov_w = QWidget(); ov_l = QVBoxLayout(ov_w)

        # title bar
        tb = QHBoxLayout()
        self._run_title = QLabel("\u8bf7\u9009\u62e9\u4e00\u4e2a Run")
        self._run_title.setStyleSheet(
            "font-size:15px;font-weight:bold;color:#1a1f36;")
        tb.addWidget(self._run_title)
        tb.addStretch()
        self._status_badge = QLabel("")
        self._status_badge.setFixedHeight(22)
        self._status_badge.setStyleSheet(
            "padding:2px 10px;border-radius:10px;font-size:12px;")
        tb.addWidget(self._status_badge)
        ov_l.addLayout(tb)

        self._color_bar = QFrame()
        self._color_bar.setFixedHeight(4)
        self._color_bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        ov_l.addWidget(self._color_bar)

        # info table
        self._info_table = QTableWidget(0, 2)
        self._info_table.setHorizontalHeaderLabels(
            ["\u5c5e\u6027", "\u503c"])
        self._info_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._info_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info_table.setAlternatingRowColors(True)
        self._info_table.verticalHeader().setVisible(False)
        self._info_table.setFixedHeight(180)
        ov_l.addWidget(self._info_table)

        # params table
        params_lbl = QLabel("\u8d85\u53c2\u6570")
        params_lbl.setStyleSheet(
            "font-weight:bold;color:#495057;margin-top:6px;")
        ov_l.addWidget(params_lbl)
        self._params_table = QTableWidget(0, 2)
        self._params_table.setHorizontalHeaderLabels(
            ["\u53c2\u6570\u540d", "\u503c"])
        self._params_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._params_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._params_table.setAlternatingRowColors(True)
        self._params_table.verticalHeader().setVisible(False)
        ov_l.addWidget(self._params_table)
        self.addTab(ov_w, "\U0001f4cb  \u6982\u89c8")

        # ── Tab2: metrics ─────────────────────────────────────────
        mt_w = QWidget(); mt_l = QVBoxLayout(mt_w)

        # summary table (top)
        self._metrics_table = QTableWidget(0, 3)
        self._metrics_table.setHorizontalHeaderLabels(
            ["\u6307\u6807", "\u5f53\u524d\u503c", "\u5386\u53f2\u70b9\u6570"])
        self._metrics_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._metrics_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._metrics_table.setAlternatingRowColors(True)
        self._metrics_table.verticalHeader().setVisible(False)
        self._metrics_table.setFixedHeight(140)
        self._metrics_table.itemClicked.connect(self._on_metric_clicked)
        mt_l.addWidget(self._metrics_table)

        # chart
        chart_lbl = QLabel("\u6307\u6807\u8d70\u52bf")
        chart_lbl.setStyleSheet(
            "font-weight:bold;color:#495057;margin-top:4px;")
        mt_l.addWidget(chart_lbl)
        self._chart = MetricChart()
        mt_l.addWidget(self._chart, 1)
        self.addTab(mt_w, "\U0001f4c8  \u6307\u6807")

        # ── Tab3: log ─────────────────────────────────────────────
        lg_w = QWidget(); lg_l = QVBoxLayout(lg_w)

        note_lbl = QLabel("\u5907\u6ce8")
        note_lbl.setStyleSheet(
            "font-weight:bold;color:#495057;")
        lg_l.addWidget(note_lbl)
        self._note_text = QTextEdit()
        self._note_text.setReadOnly(True)
        self._note_text.setFixedHeight(80)
        lg_l.addWidget(self._note_text)

        err_lbl = QLabel("\u9519\u8bef\u4fe1\u606f")
        err_lbl.setStyleSheet("font-weight:bold;color:#dc3545;margin-top:6px;")
        lg_l.addWidget(err_lbl)
        self._err_text = QTextEdit()
        self._err_text.setReadOnly(True)
        self._err_text.setFixedHeight(60)
        self._err_text.setStyleSheet(
            "background:#fff5f5;border:1px solid #f5c6cb;border-radius:4px;")
        lg_l.addWidget(self._err_text)

        art_lbl = QLabel("Artifacts")
        art_lbl.setStyleSheet(
            "font-weight:bold;color:#495057;margin-top:6px;")
        lg_l.addWidget(art_lbl)
        self._art_text = QTextEdit()
        self._art_text.setReadOnly(True)
        self._art_text.setFont(QFont("Consolas", 9))
        lg_l.addWidget(self._art_text, 1)
        self.addTab(lg_w, "\U0001f4cb  \u65e5\u5fd7")

    # ── load / clear ──────────────────────────────────────────────

    def load(self, run_id: str):
        self._run_id = run_id
        run = self._engine.get_run(run_id)
        if not run:
            self.clear_panel(); return
        exp = self._engine.get_experiment(run.experiment_id)
        self._load_overview(run, exp)
        self._load_metrics(run, exp)
        self._load_log(run)

    def clear_panel(self):
        self._run_id = None
        self._run_title.setText("\u8bf7\u9009\u62e9\u4e00\u4e2a Run")
        self._status_badge.setText("")
        self._status_badge.setStyleSheet("")
        self._color_bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        self._info_table.setRowCount(0)
        self._params_table.setRowCount(0)
        self._metrics_table.setRowCount(0)
        self._chart.clear()
        self._note_text.clear()
        self._err_text.clear()
        self._art_text.clear()

    # ── overview ──────────────────────────────────────────────────

    def _load_overview(self, run: RunRecord, exp):
        self._run_title.setText(run.name)
        sc_map = {
            RunStatus.PENDING:   ("#adb5bd", "Pending"),
            RunStatus.RUNNING:   ("#198754", "Running"),
            RunStatus.COMPLETED: ("#0d6efd", "Completed"),
            RunStatus.FAILED:    ("#dc3545", "Failed"),
            RunStatus.KILLED:    ("#6c757d", "Killed"),
        }
        sc, sl = sc_map.get(run.status, ("#6c757d", run.status.value))
        self._status_badge.setText(sl)
        self._status_badge.setStyleSheet(
            "padding:2px 10px;border-radius:10px;"
            "background:" + sc + "22;color:" + sc + ";"
            "font-size:12px;font-weight:bold;"
            "border:1px solid " + sc + "44;")
        self._color_bar.setStyleSheet("background:" + sc + ";border-radius:2px;")

        self._info_table.setRowCount(0)
        is_best = exp and exp.best_run_id == run.run_id
        dur_str = (str(round(run.duration_sec, 2)) + "s"
                   if run.duration_sec else "\u2014")
        rows = [
            ("Run ID",          run.run_id),
            ("\u5b9e\u9a8c ID", run.experiment_id),
            ("\u540d\u79f0",   run.name),
            ("\u72b6\u6001",   sl),
            ("\u6700\u4f73 Run", "\u2b50 \u662f" if is_best else "\u5426"),
            ("\u65f6\u957f",   dur_str),
            ("Git Commit",       run.git_commit or "\u2014"),
            ("\u6570\u636e\u7248\u672c", run.data_version or "\u2014"),
            ("\u5f00\u59cb\u65f6\u95f4", run.started_at.strftime("%Y-%m-%d %H:%M:%S")
             if run.started_at else "\u2014"),
            ("\u7ed3\u675f\u65f6\u95f4", run.finished_at.strftime("%Y-%m-%d %H:%M:%S")
             if run.finished_at else "\u2014"),
        ]
        for key, val in rows:
            r = self._info_table.rowCount()
            self._info_table.insertRow(r)
            k = QTableWidgetItem(key)
            k.setForeground(QBrush(QColor("#6c757d")))
            self._info_table.setItem(r, 0, k)
            self._info_table.setItem(r, 1, QTableWidgetItem(str(val)))

        self._params_table.setRowCount(0)
        for k, v in (run.params or {}).items():
            r = self._params_table.rowCount()
            self._params_table.insertRow(r)
            self._params_table.setItem(r, 0, QTableWidgetItem(str(k)))
            self._params_table.setItem(r, 1, QTableWidgetItem(str(v)))

    # ── metrics ───────────────────────────────────────────────────

    def _load_metrics(self, run: RunRecord, exp):
        self._metrics_table.setRowCount(0)
        pm = exp.primary_metric if exp else ""
        for key, val in sorted((run.metrics or {}).items()):
            hist = [pt for pt in (run.metric_history or [])
                    if pt.key == key]
            r = self._metrics_table.rowCount()
            self._metrics_table.insertRow(r)
            k_item = QTableWidgetItem(("\u2b50 " if key == pm else "") + key)
            if key == pm:
                k_item.setForeground(QBrush(QColor("#198754")))
            self._metrics_table.setItem(r, 0, k_item)
            v_item = QTableWidgetItem(str(round(val, 6)))
            self._metrics_table.setItem(r, 1, v_item)
            h_item = QTableWidgetItem(str(len(hist)))
            h_item.setTextAlignment(Qt.AlignCenter)
            self._metrics_table.setItem(r, 2, h_item)

        # auto-show primary metric chart
        if pm and run.metric_history:
            self._show_chart(pm, run)

    def _on_metric_clicked(self, item):
        run = self._engine.get_run(self._run_id) if self._run_id else None
        if not run:
            return
        row = item.row()
        key_item = self._metrics_table.item(row, 0)
        if not key_item:
            return
        key = key_item.text().lstrip("\u2b50 ").strip()
        self._show_chart(key, run)

    def _show_chart(self, key: str, run: RunRecord):
        pts = [pt for pt in (run.metric_history or []) if pt.key == key]
        if pts:
            self._chart.set_series({key: pts}, title=key)
        else:
            self._chart.set_series(
                {key: [MetricPoint(key=key, value=run.metrics.get(key, 0),
                                   step=1)]},
                title=key + " (\u65e0\u5386\u53f2)")

    # ── log ───────────────────────────────────────────────────────

    def _load_log(self, run: RunRecord):
        self._note_text.setPlainText(run.note or "")
        self._err_text.setPlainText(run.error_msg or "")
        arts = run.artifacts or {}
        lines = []
        for k, v in arts.items():
            lines.append(k + ": " + str(v))
        self._art_text.setPlainText("\n".join(lines) if lines else "\u65e0 Artifacts")


class ComparePanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._run_ids: List[str] = []
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        hdr = QHBoxLayout()
        lbl = QLabel("\u591a Run \u5bf9\u6bd4")
        lbl.setStyleSheet("font-weight:bold;color:#1a1f36;font-size:13px;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        self._clear_btn = QPushButton("\u6e05\u7a7a")
        self._clear_btn.setFixedSize(52, 24)
        self._clear_btn.clicked.connect(self.clear_panel)
        hdr.addWidget(self._clear_btn)
        root.addLayout(hdr)

        self._hint = QLabel(
            "\u5728\u5de6\u4fa7\u70b9\u51fb Run \u8282\u70b9\u5c06\u5176\u52a0\u5165\u5bf9\u6bd4\uff0c"
            "\u7136\u540e\u70b9\u51fb\u300e\u5bf9\u6bd4\u9009\u4e2d Run\u300f")
        self._hint.setStyleSheet("color:#6c757d;font-size:11px;")
        self._hint.setWordWrap(True)
        root.addWidget(self._hint)

        self._table = QTableWidget(0, 0)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        root.addWidget(self._table, 1)

        # multi-metric chart
        chart_lbl = QLabel("\u5bf9\u6bd4\u6307\u6807\u8d70\u52bf")
        chart_lbl.setStyleSheet(
            "font-weight:bold;color:#495057;margin-top:4px;")
        root.addWidget(chart_lbl)
        self._chart = MetricChart()
        self._chart.setFixedHeight(180)
        root.addWidget(self._chart)

    def load_runs(self, run_ids: List[str]):
        self._run_ids = run_ids
        self._rebuild()

    def clear_panel(self):
        self._run_ids = []
        self._table.setRowCount(0)
        self._table.setColumnCount(0)
        self._chart.clear()

    def _rebuild(self):
        if not self._run_ids:
            return
        runs = [self._engine.get_run(rid) for rid in self._run_ids]
        runs = [r for r in runs if r]
        if not runs:
            return

        # collect all metric keys
        all_keys = sorted({k for r in runs for k in (r.metrics or {})})

        # build table: rows=metrics, cols=params header + run names
        n_runs = len(runs)
        self._table.setRowCount(len(all_keys) + len(runs[0].params or {}))
        self._table.setColumnCount(n_runs + 1)

        headers = ["\u6307\u6807 / \u53c2\u6570"] + [r.name for r in runs]
        self._table.setHorizontalHeaderLabels(headers)

        # find best values per metric (higher = better heuristic: just find max)
        best_vals: Dict[str, float] = {}
        worst_vals: Dict[str, float] = {}
        for key in all_keys:
            vals = [r.metrics[key] for r in runs if key in (r.metrics or {})]
            if vals:
                best_vals[key]  = max(vals)
                worst_vals[key] = min(vals)

        row = 0
        # metrics section
        sec_lbl = QTableWidgetItem("\u2014 \u6307\u6807 \u2014")
        sec_lbl.setBackground(QBrush(QColor("#f0f4ff")))
        sec_lbl.setForeground(QBrush(QColor("#4a6cf7")))
        f = QFont(); f.setBold(True); sec_lbl.setFont(f)
        self._table.setItem(row, 0, sec_lbl)
        for c in range(1, n_runs + 1):
            self._table.setItem(row, c, QTableWidgetItem(""))
        row += 1

        for key in all_keys:
            k_item = QTableWidgetItem(key)
            k_item.setForeground(QBrush(QColor("#495057")))
            self._table.setItem(row, 0, k_item)
            for c, run in enumerate(runs, 1):
                val = (run.metrics or {}).get(key)
                if val is None:
                    self._table.setItem(row, c, QTableWidgetItem("\u2014"))
                else:
                    cell = QTableWidgetItem(str(round(val, 6)))
                    cell.setTextAlignment(Qt.AlignCenter)
                    if val == best_vals.get(key):
                        cell.setBackground(QBrush(QColor("#d1e7dd")))
                        cell.setForeground(QBrush(QColor("#0a3622")))
                    elif val == worst_vals.get(key):
                        cell.setBackground(QBrush(QColor("#f8d7da")))
                        cell.setForeground(QBrush(QColor("#58151c")))
                    self._table.setItem(row, c, cell)
            row += 1

        # params section
        if runs[0].params:
            sec_lbl2 = QTableWidgetItem("\u2014 \u53c2\u6570 \u2014")
            sec_lbl2.setBackground(QBrush(QColor("#f0f4ff")))
            sec_lbl2.setForeground(QBrush(QColor("#4a6cf7")))
            sec_lbl2.setFont(f)
            self._table.setItem(row, 0, sec_lbl2)
            for c in range(1, n_runs + 1):
                self._table.setItem(row, c, QTableWidgetItem(""))
            row += 1
            all_param_keys = sorted({k for r in runs for k in (r.params or {})})
            for pk in all_param_keys:
                self._table.setItem(row, 0, QTableWidgetItem(pk))
                for c, run in enumerate(runs, 1):
                    pv = (run.params or {}).get(pk, "\u2014")
                    cell = QTableWidgetItem(str(pv))
                    cell.setTextAlignment(Qt.AlignCenter)
                    self._table.setItem(row, c, cell)
                row += 1

        self._table.setRowCount(row)

        # update chart: show primary metric history across runs
        exp_id = runs[0].experiment_id
        exp    = self._engine.get_experiment(exp_id)
        pm     = exp.primary_metric if exp else ""
        if pm:
            series = {}
            for run in runs:
                pts = [pt for pt in (run.metric_history or []) if pt.key == pm]
                if pts:
                    series[run.name] = pts
            if series:
                self._chart.set_series(series, title=pm + " \u5bf9\u6bd4")


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
        self._btn_new_exp  = QPushButton("+ \u65b0\u5efa\u5b9e\u9a8c")
        self._btn_new_run  = QPushButton("\u25b6 \u65b0\u5efa Run")
        self._btn_cmp      = QPushButton("\U0001f4ca \u5bf9\u6bd4\u9009\u4e2d")
        self._btn_del      = QPushButton("\U0001f5d1 \u5220\u9664")
        for btn in (self._btn_new_exp, self._btn_new_run,
                    self._btn_cmp, self._btn_del):
            btn.setFixedHeight(28); tb.addWidget(btn)
        tb.addWidget(_sep())
        tb.addStretch()
        tb.addWidget(QLabel("\u641c\u7d22:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("\u5b9e\u9a8c\u540d / \u6807\u7b7e...")
        self._search_box.setFixedWidth(160); self._search_box.setFixedHeight(28)
        tb.addWidget(self._search_box)
        self._btn_search = QPushButton("\u641c\u7d22"); self._btn_search.setFixedSize(52, 28)
        self._btn_reset  = QPushButton("\u91cd\u7f6e"); self._btn_reset.setFixedSize(52, 28)
        tb.addWidget(self._btn_search); tb.addWidget(self._btn_reset)
        root.addLayout(tb)

        # ── stats bar ─────────────────────────────────────────────
        self._stats_bar = QLabel("\u52a0\u8f7d\u4e2d...")
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
        self._status = QLabel("\u5c31\u7eea")
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
            self._set_status("\u5b9e\u9a8c\u300c" + exp.name + "\u300d\u5df2\u521b\u5efa")
            self._refresh_stats()

    def _on_new_run(self):
        exp_id = self._exp_list.get_current_exp_id()
        if not exp_id:
            QMessageBox.warning(self, "\u63d0\u793a",
                                "\u8bf7\u5148\u9009\u62e9\u4e00\u4e2a\u5b9e\u9a8c\u3002")
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
                self._engine.update_run(run)
            if metrics:
                for k, v in metrics.items():
                    self._engine.log_metric(run.run_id, k, v)
                self._engine.complete_run(run.run_id, metrics=metrics)
            self._detail.load(run.run_id)
            self._set_status("Run \u300c" + run.name + "\u300d\u5df2\u521b\u5efa")
            self._refresh_stats()

    def _on_compare_checked(self):
        checked = self._exp_list._checked_runs
        if checked:
            self._compare.load_runs(list(checked))
            self._set_status("\u5bf9\u6bd4 " + str(len(checked)) + " \u4e2a Run")
        else:
            self._set_status("\u8bf7\u5148\u5728\u5de6\u4fa7\u70b9\u51fb Run \u8282\u70b9\u52a0\u5165\u5bf9\u6bd4")

    def _on_delete(self):
        exp_id = self._exp_list.selected_exp_id()
        if not exp_id:
            self._set_status("\u8bf7\u9009\u62e9\u4e00\u4e2a\u5b9e\u9a8c\u8282\u70b9")
            return
        exp = self._engine.get_experiment(exp_id)
        if not exp:
            return
        if QMessageBox.question(
            self, "\u786e\u8ba4\u5220\u9664",
            "\u786e\u8ba4\u5220\u9664\u5b9e\u9a8c\u300c" + exp.name + "\u300d\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self._engine.delete_experiment(exp_id)
            self._detail.clear_panel()
            self._set_status("\u5b9e\u9a8c\u300c" + exp.name + "\u300d\u5df2\u5220\u9664")
            self._refresh_stats()

    # ── search ────────────────────────────────────────────────────

    def _on_search(self):
        kw = self._search_box.text().strip()
        if not kw:
            return
        self._exp_list.set_keyword(kw)
        results = self._engine.search_experiments(kw)
        self._set_status("\u641c\u7d22\u300c" + kw + "\u300d\uff1a\u627e\u5230 "
                         + str(len(results)) + " \u4e2a\u5b9e\u9a8c")

    def _on_reset(self):
        self._search_box.clear()
        self._exp_list.set_keyword("")
        self._detail.clear_panel()
        self._set_status("\u5c31\u7eea")

    # ── tree callbacks ────────────────────────────────────────────

    def _on_exp_selected(self, exp_id: str):
        exp = self._engine.get_experiment(exp_id)
        if exp:
            runs = self._engine.list_runs(exp_id)
            self._set_status(
                "\u5b9e\u9a8c\uff1a" + exp.name
                + "  Runs: " + str(len(runs))
                + ("  \u6700\u4f73: " + exp.best_run_id[:8]
                   if exp.best_run_id else ""))

    def _on_run_selected(self, run_id: str):
        self._detail.load(run_id)
        run = self._engine.get_run(run_id)
        if run:
            self._set_status("Run: " + run.name + "  \u72b6\u6001: " + run.status.value)

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
            "\u5b9e\u9a8c: " + str(exps)
            + "    Runs: " + str(runs)
            + "    \u8fd0\u884c\u4e2d: " + str(run_)
            + "    \u5df2\u5b8c\u6210: " + str(comp)
            + "    \u5931\u8d25: " + str(fail))

    def _set_status(self, msg: str):
        self._status.setText(msg)
