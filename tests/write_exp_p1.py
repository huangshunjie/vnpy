"""write_exp_p1.py — experiment_tab.py Part1: imports + constants + ExperimentDialog"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\experiment_tab.py"
)

PART1 = """\
\"\"\"
research_ops/ui/experiment_tab.py  Phase 3 - Experiment Tracking System
\"\"\"
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
    ExperimentStatus.DRAFT:     "\\u25cb",
    ExperimentStatus.RUNNING:   "\\U0001f7e2",
    ExperimentStatus.COMPLETED: "\\U0001f535",
    ExperimentStatus.FAILED:    "\\U0001f534",
    ExperimentStatus.ARCHIVED:  "\\u26ab",
}
RUN_STATUS_ICON = {
    RunStatus.PENDING:   "\\u23f3",
    RunStatus.RUNNING:   "\\U0001f7e1",
    RunStatus.COMPLETED: "\\U0001f535",
    RunStatus.FAILED:    "\\U0001f534",
    RunStatus.KILLED:    "\\u26ab",
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
            "\\u7f16\\u8f91\\u5b9e\\u9a8c" if self._editing
            else "\\u65b0\\u5efa\\u5b9e\\u9a8c")
        self.setMinimumWidth(500)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u5b9e\\u9a8c\\u4fe1\\u606f")
        form = QFormLayout(grp)

        self._name = QLineEdit()
        self._name.setPlaceholderText("\\u5b9e\\u9a8c\\u540d\\u79f0")
        form.addRow("\\u540d\\u79f0 *", self._name)

        self._desc = QTextEdit(); self._desc.setFixedHeight(56)
        form.addRow("\\u63cf\\u8ff0", self._desc)

        self._hypothesis = QTextEdit(); self._hypothesis.setFixedHeight(56)
        self._hypothesis.setPlaceholderText("\\u7814\\u7a76\\u5047\\u8bbe")
        form.addRow("\\u5047\\u8bbe", self._hypothesis)

        self._objective = QLineEdit()
        self._objective.setPlaceholderText("\\u5b9e\\u9a8c\\u76ee\\u6807")
        form.addRow("\\u76ee\\u6807", self._objective)

        self._primary_metric = QLineEdit()
        self._primary_metric.setPlaceholderText("\\u4e3b\\u8981\\u6307\\u6807\\uff0c\\u5982 sharpe / ic")
        form.addRow("\\u4e3b\\u8981\\u6307\\u6807", self._primary_metric)

        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\\u9017\\u53f7\\u5206\\u9694")
        form.addRow("\\u6807\\u7b7e", self._tags)

        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u786e\\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
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
        self.setWindowTitle("\\u65b0\\u5efa Run")
        self.setMinimumWidth(500)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)

        grp = QGroupBox("Run \\u4fe1\\u606f")
        form = QFormLayout(grp)

        self._name = QLineEdit()
        self._name.setPlaceholderText("Run \\u540d\\u79f0\\uff08\\u53ef\\u7559\\u7a7a\\u81ea\\u52a8\\u751f\\u6210\\uff09")
        form.addRow("\\u540d\\u79f0", self._name)

        self._git = QLineEdit()
        self._git.setPlaceholderText("Git commit hash")
        form.addRow("Git Commit", self._git)

        self._data_ver = QLineEdit()
        self._data_ver.setPlaceholderText("\\u6570\\u636e\\u7248\\u672c\\uff0c\\u5982 v2024Q1")
        form.addRow("\\u6570\\u636e\\u7248\\u672c", self._data_ver)

        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\\u9017\\u53f7\\u5206\\u9694")
        form.addRow("\\u6807\\u7b7e", self._tags)

        root.addWidget(grp)

        # params
        params_grp = QGroupBox("\\u8d85\\u53c2\\u6570\\uff08key=value \\u6bcf\\u884c\\u4e00\\u4e2a\\uff09")
        pl = QVBoxLayout(params_grp)
        self._params_edit = QTextEdit()
        self._params_edit.setFixedHeight(80)
        self._params_edit.setPlaceholderText(
            "lookback=20\\nthreshold=0.05\\nuniverse=HS300")
        pl.addWidget(self._params_edit)
        root.addWidget(params_grp)

        # metrics
        metrics_grp = QGroupBox(
            "\\u521d\\u59cb\\u6307\\u6807\\uff08\\u53ef\\u7559\\u7a7a\\uff0c\\u8fd0\\u884c\\u540e\\u624b\\u52a8\\u8bb0\\u5f55\\uff09")
        ml = QVBoxLayout(metrics_grp)
        self._metrics_edit = QTextEdit()
        self._metrics_edit.setFixedHeight(80)
        self._metrics_edit.setPlaceholderText(
            "sharpe=1.85\\nic=0.046\\nmax_drawdown=-0.12")
        ml.addWidget(self._metrics_edit)
        root.addWidget(metrics_grp)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u521b\\u5efa Run")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
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
"""

ast.parse(PART1)
P.write_text(PART1, encoding="utf-8")
print("PART1 written OK, lines:", len(PART1.splitlines()), "size:", P.stat().st_size)
