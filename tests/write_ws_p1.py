"""workspace_tab_writer.py"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\workspace_tab.py"
)

# 用 unicode 转义写所有中文，彻底规避 PowerShell GBK 截断
PART1 = '''\
"""
research_ops/ui/workspace_tab.py  - Phase 2
"""
from __future__ import annotations
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QMenu, QMessageBox, QColorDialog,
    QFrame, QTableWidget, QTableWidgetItem, QInputDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QBrush

from vnpy.event import Event
from ..main_engine import ResearchOpsEngine
from ..model.workspace_model import WorkspaceRecord, ProjectRecord, FolderRecord
from ..constant import ProjectStatus, WorkspaceStatus
from ..event import (
    EVENT_RO_WS_CREATED, EVENT_RO_WS_UPDATED,
    EVENT_RO_WS_DELETED, EVENT_RO_WS_SWITCHED,
    EVENT_RO_PRJ_CREATED, EVENT_RO_PRJ_UPDATED,
    EVENT_RO_PRJ_DELETED, EVENT_RO_PRJ_STARRED,
    EVENT_RO_PRJ_UNSTARRED,
)

STATUS_COLORS = {
    ProjectStatus.ACTIVE:    "#198754",
    ProjectStatus.PAUSED:    "#fd7e14",
    ProjectStatus.COMPLETED: "#0d6efd",
    ProjectStatus.ARCHIVED:  "#6c757d",
}
STATUS_LABELS = {
    ProjectStatus.ACTIVE:    "\u6d3b\u8dc3",
    ProjectStatus.PAUSED:    "\u6682\u505c",
    ProjectStatus.COMPLETED: "\u5df2\u5b8c\u6210",
    ProjectStatus.ARCHIVED:  "\u5df2\u5f52\u6863",
}
NODE_WS      = "workspace"
NODE_PROJECT = "project"
NODE_FOLDER  = "folder"
NODE_STARRED = "starred_root"
ROLE_ID   = Qt.UserRole
ROLE_TYPE = Qt.UserRole + 1
'''

ast.parse(PART1)
P.write_text(PART1, encoding="utf-8")
print("PART1 written OK, lines:", len(PART1.splitlines()))
