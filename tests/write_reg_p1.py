"""write_reg_p1.py — registry_tab.py Part1: imports + common components"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\registry_tab.py"
)

PART1 = """\
\"\"\"
research_ops/ui/registry_tab.py  Phase 4 - Registry System
\"\"\"
from __future__ import annotations
from typing import List, Optional, Dict
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QMenu, QMessageBox, QFrame,
    QTableWidget, QTableWidgetItem, QDoubleSpinBox,
    QSpinBox, QCheckBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QBrush

from vnpy.event import Event
from ..main_engine import ResearchOpsEngine
from ..model.registry_model import (
    DatasetEntry, FeatureEntry, StrategyEntry, ModelEntry,
)
from ..constant import (
    DatasetStatus, FeatureStatus, StrategyStatus, ModelStatus,
)
from ..event import (
    EVENT_RO_DS_CREATED,  EVENT_RO_DS_UPDATED,  EVENT_RO_DS_DELETED,
    EVENT_RO_FT_CREATED,  EVENT_RO_FT_UPDATED,  EVENT_RO_FT_DELETED,
    EVENT_RO_ST_CREATED,  EVENT_RO_ST_UPDATED,  EVENT_RO_ST_DELETED,
    EVENT_RO_ML_CREATED,  EVENT_RO_ML_UPDATED,  EVENT_RO_ML_DELETED,
    EVENT_RO_ML_DEPLOYED,
)
from .experiment_tab import MetricChart
from ..model.experiment_model import MetricPoint

# ── status palettes ────────────────────────────────────────────────
DS_STATUS_COLOR = {
    DatasetStatus.DRAFT:       "#6c757d",
    DatasetStatus.READY:       "#198754",
    DatasetStatus.DEPRECATED:  "#dc3545",
    DatasetStatus.ARCHIVED:    "#adb5bd",
}
FT_STATUS_COLOR = {
    FeatureStatus.DRAFT:       "#6c757d",
    FeatureStatus.VALIDATED:   "#198754",
    FeatureStatus.DEPRECATED:  "#dc3545",
    FeatureStatus.ARCHIVED:    "#adb5bd",
}
ST_STATUS_COLOR = {
    StrategyStatus.DRAFT:      "#6c757d",
    StrategyStatus.BACKTESTED: "#fd7e14",
    StrategyStatus.VALIDATED:  "#0d6efd",
    StrategyStatus.LIVE:       "#198754",
    StrategyStatus.RETIRED:    "#adb5bd",
}
ML_STATUS_COLOR = {
    ModelStatus.DRAFT:       "#6c757d",
    ModelStatus.TRAINED:     "#fd7e14",
    ModelStatus.EVALUATED:   "#0d6efd",
    ModelStatus.DEPLOYED:    "#198754",
    ModelStatus.RETIRED:     "#adb5bd",
}

NODE_TYPE_ICON = {
    "dataset":  "\\U0001f4be",
    "feature":  "\\U0001f4d0",
    "strategy": "\\U0001f4c8",
    "model":    "\\U0001f916",
}

ROLE_ID   = Qt.UserRole
ROLE_TYPE = Qt.UserRole + 1


# =================================================================
# _StatCard  通用指标卡片
# =================================================================

def _make_stat_card(label: str, value: str,
                    color: str = "#1a1f36",
                    bg: str = "#ffffff") -> QFrame:
    card = QFrame()
    card.setFrameShape(QFrame.StyledPanel)
    card.setStyleSheet(
        "QFrame{background:" + bg + ";border:1px solid #dee2e6;"
        "border-radius:8px;padding:6px;}")
    lay = QVBoxLayout(card); lay.setSpacing(2)
    lbl = QLabel(label)
    lbl.setStyleSheet("color:#6c757d;font-size:11px;")
    lay.addWidget(lbl)
    val = QLabel(value)
    val.setStyleSheet(
        "font-size:18px;font-weight:bold;color:" + color + ";")
    val.setAlignment(Qt.AlignCenter)
    lay.addWidget(val)
    card._val_lbl = val
    card._lbl_lbl = lbl
    return card


def _sep_v() -> QFrame:
    f = QFrame(); f.setFrameShape(QFrame.VLine)
    f.setStyleSheet("color:#dee2e6;"); return f


# =================================================================
# LineageTreeWidget  血缘关系树
# =================================================================

class LineageTreeWidget(QTreeWidget):
    def __init__(self, engine: ResearchOpsEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self.setHeaderHidden(True)
        self.setIndentation(16)
        self.setAnimated(True)

    def load(self, node_id: str):
        self.clear()
        if not node_id:
            return
        lg = self._engine.registry.lineage

        # upstream section
        up_root = QTreeWidgetItem([
            "\\u2191 \\u4e0a\\u6e38\\u8840\\u7f18 (ancestors)"])
        up_root.setForeground(0, QBrush(QColor("#0d6efd")))
        f = QFont(); f.setBold(True); up_root.setFont(0, f)
        for anc_id in sorted(lg.ancestors(node_id)):
            info = lg._graph.get(anc_id, {})
            ntype = info.get("node_type", "")
            icon  = NODE_TYPE_ICON.get(ntype, "\\u25cb")
            label = info.get("label", anc_id)
            item  = QTreeWidgetItem([icon + "  " + label + "  [" + anc_id[:8] + "]"])
            item.setData(0, ROLE_ID, anc_id)
            item.setData(0, ROLE_TYPE, ntype)
            item.setForeground(0, QBrush(QColor("#0d6efd")))
            up_root.addChild(item)
        self.addTopLevelItem(up_root)
        up_root.setExpanded(True)

        # current node
        cur_info = lg._graph.get(node_id, {})
        cur_type = cur_info.get("node_type", "")
        cur_lbl  = cur_info.get("label", node_id)
        cur_item = QTreeWidgetItem([
            "\\u25cf  " + NODE_TYPE_ICON.get(cur_type,"") + "  " + cur_lbl
            + "  \\u2190 \\u5f53\\u524d"])
        cur_item.setData(0, ROLE_ID, node_id)
        f2 = QFont(); f2.setBold(True); cur_item.setFont(0, f2)
        cur_item.setForeground(0, QBrush(QColor("#1a1f36")))
        self.addTopLevelItem(cur_item)

        # downstream section
        dn_root = QTreeWidgetItem([
            "\\u2193 \\u4e0b\\u6e38\\u8840\\u7f18 (descendants)"])
        dn_root.setForeground(0, QBrush(QColor("#198754")))
        dn_root.setFont(0, f)
        for desc_id in sorted(lg.descendants(node_id)):
            info  = lg._graph.get(desc_id, {})
            ntype = info.get("node_type", "")
            icon  = NODE_TYPE_ICON.get(ntype, "\\u25cb")
            label = info.get("label", desc_id)
            item  = QTreeWidgetItem([icon + "  " + label + "  [" + desc_id[:8] + "]"])
            item.setData(0, ROLE_ID, desc_id)
            item.setData(0, ROLE_TYPE, ntype)
            item.setForeground(0, QBrush(QColor("#198754")))
            dn_root.addChild(item)
        self.addTopLevelItem(dn_root)
        dn_root.setExpanded(True)
"""

ast.parse(PART1)
P.write_text(PART1, encoding="utf-8")
print("PART1 written OK, lines:", len(PART1.splitlines()), "size:", P.stat().st_size)
