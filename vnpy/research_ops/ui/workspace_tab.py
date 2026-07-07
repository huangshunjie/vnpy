"""
research_ops/ui/workspace_tab.py  Phase 2
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


class WorkspaceDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\u7f16\u8f91\u5de5\u4f5c\u533a" if self._editing
            else "\u65b0\u5efa\u5de5\u4f5c\u533a")
        self.setMinimumWidth(460)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u5de5\u4f5c\u533a\u4fe1\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit()
        self._name.setPlaceholderText("\u5de5\u4f5c\u533a\u540d\u79f0")
        form.addRow("\u540d\u79f0 *", self._name)
        self._desc = QTextEdit()
        self._desc.setFixedHeight(60)
        form.addRow("\u63cf\u8ff0", self._desc)
        self._root = QLineEdit()
        form.addRow("\u6839\u76ee\u5f55", self._root)
        self._members = QLineEdit()
        self._members.setPlaceholderText("\u9017\u53f7\u5206\u9694")
        form.addRow("\u6210\u5458", self._members)
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
        self._root.setText(r.root_path)
        self._members.setText(", ".join(r.members))
        self._tags.setText(", ".join(r.tags))

    def _on_ok(self):
        if not self._name.text().strip():
            self._name.setFocus(); return
        self.accept()

    def _split(self, t):
        return [x.strip() for x in t.split(",") if x.strip()]

    def get_name(self)        -> str:       return self._name.text().strip()
    def get_description(self) -> str:       return self._desc.toPlainText().strip()
    def get_root_path(self)   -> str:       return self._root.text().strip()
    def get_members(self)     -> List[str]: return self._split(self._members.text())
    def get_tags(self)        -> List[str]: return self._split(self._tags.text())


class ProjectDialog(QDialog):
    def __init__(self, parent=None, record=None, workspace_id=""):
        super().__init__(parent)
        self._record       = record
        self._workspace_id = workspace_id
        self._editing      = record is not None
        self._color        = record.color if record else "#4a6cf7"
        self.setWindowTitle(
            "\u7f16\u8f91\u9879\u76ee" if self._editing
            else "\u65b0\u5efa\u9879\u76ee")
        self.setMinimumWidth(460)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u9879\u76ee\u4fe1\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit()
        self._name.setPlaceholderText("\u9879\u76ee\u540d\u79f0")
        form.addRow("\u540d\u79f0 *", self._name)
        self._desc = QTextEdit()
        self._desc.setFixedHeight(60)
        form.addRow("\u63cf\u8ff0", self._desc)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)
        cw = QWidget(); cl = QHBoxLayout(cw); cl.setContentsMargins(0,0,0,0)
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(32, 22)
        self._color_btn.setStyleSheet("background:" + self._color + "; border-radius:4px;")
        self._color_btn.clicked.connect(self._pick_color)
        self._color_lbl = QLabel(self._color)
        cl.addWidget(self._color_btn); cl.addWidget(self._color_lbl); cl.addStretch()
        form.addRow("\u989c\u8272", cw)
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
        self._tags.setText(", ".join(r.tags))
        self._set_color(r.color)

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self, "\u9009\u62e9\u989c\u8272")
        if c.isValid():
            self._set_color(c.name())

    def _set_color(self, h):
        self._color = h
        self._color_btn.setStyleSheet("background:" + h + "; border-radius:4px;")
        self._color_lbl.setText(h)

    def _on_ok(self):
        if not self._name.text().strip():
            self._name.setFocus(); return
        self.accept()

    def _split(self, t):
        return [x.strip() for x in t.split(",") if x.strip()]

    def get_name(self)         -> str:       return self._name.text().strip()
    def get_description(self)  -> str:       return self._desc.toPlainText().strip()
    def get_tags(self)         -> List[str]: return self._split(self._tags.text())
    def get_color(self)        -> str:       return self._color
    def get_workspace_id(self) -> str:       return self._workspace_id


class ProjectExplorer(QWidget):
    project_selected   = Signal(str)
    workspace_selected = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 0)
        root.setSpacing(4)
        ws_bar = QHBoxLayout()
        ws_bar.addWidget(QLabel("\u5de5\u4f5c\u533a:"))
        self._ws_combo = QComboBox()
        self._ws_combo.setMinimumWidth(140)
        ws_bar.addWidget(self._ws_combo, 1)
        root.addLayout(ws_bar)
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(18)
        self._tree.setAnimated(True)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        root.addWidget(self._tree)
        self._ws_combo.currentIndexChanged.connect(self._on_ws_changed)
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.itemDoubleClicked.connect(
            lambda item, _: item.setExpanded(not item.isExpanded()))

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in (EVENT_RO_WS_CREATED, EVENT_RO_WS_UPDATED,
                   EVENT_RO_WS_DELETED, EVENT_RO_WS_SWITCHED,
                   EVENT_RO_PRJ_CREATED, EVENT_RO_PRJ_UPDATED,
                   EVENT_RO_PRJ_DELETED, EVENT_RO_PRJ_STARRED,
                   EVENT_RO_PRJ_UNSTARRED):
            ee.register(ev, self._on_event)

    def _on_event(self, _ev):
        self._refresh()

    def _refresh(self):
        self._refresh_ws_combo()
        self._build_tree()

    def _refresh_ws_combo(self):
        self._ws_combo.blockSignals(True)
        self._ws_combo.clear()
        active = self._engine.get_active_workspace()
        for ws in self._engine.list_workspaces():
            self._ws_combo.addItem(ws.name, ws.workspace_id)
        if active:
            idx = self._ws_combo.findData(active.workspace_id)
            if idx >= 0:
                self._ws_combo.setCurrentIndex(idx)
        self._ws_combo.blockSignals(False)

    def _build_tree(self):
        self._tree.clear()
        self._add_starred_root()
        ws_id = self._ws_combo.currentData()
        if ws_id:
            self._add_workspace_node(ws_id)

    def _add_starred_root(self):
        ri = QTreeWidgetItem(["\u2b50  \u6536\u85cf\u5939"])
        ri.setData(0, ROLE_TYPE, NODE_STARRED)
        ri.setData(0, ROLE_ID, "starred")
        f = QFont(); f.setBold(True); ri.setFont(0, f)
        for proj in self._engine.get_starred_projects():
            ri.addChild(self._make_project_item(proj))
        self._tree.addTopLevelItem(ri)
        ri.setExpanded(True)

    def _add_workspace_node(self, workspace_id):
        ws = self._engine.get_workspace(workspace_id)
        if not ws:
            return
        wi = QTreeWidgetItem(["\U0001f5c2  " + ws.name])
        wi.setData(0, ROLE_TYPE, NODE_WS)
        wi.setData(0, ROLE_ID, workspace_id)
        f = QFont(); f.setBold(True); wi.setFont(0, f)
        active = self._engine.get_active_workspace()
        if active and active.workspace_id == workspace_id:
            wi.setForeground(0, QBrush(QColor("#4a6cf7")))
        for proj in self._engine.list_projects(workspace_id):
            pi = self._make_project_item(proj)
            self._add_folder_children(pi, proj)
            wi.addChild(pi)
        self._tree.addTopLevelItem(wi)
        wi.setExpanded(True)

    def _make_project_item(self, proj):
        icons = {"active": "\U0001f7e2", "paused": "\U0001f7e1",
                 "completed": "\U0001f535", "archived": "\u26ab"}
        icon  = icons.get(proj.status.value, "\u26aa")
        label = ("\u2b50 " if proj.starred else "") + icon + "  " + proj.name
        item  = QTreeWidgetItem([label])
        item.setData(0, ROLE_TYPE, NODE_PROJECT)
        item.setData(0, ROLE_ID, proj.project_id)
        item.setForeground(0, QBrush(QColor(proj.color or "#4a6cf7")))
        return item

    def _add_folder_children(self, parent, proj):
        folders = self._engine.workspace.list_folders(proj.project_id)
        for f in folders:
            if not f.parent_id:
                fi = self._make_folder_item(f)
                self._add_sub_folders(fi, f.folder_id, folders)
                parent.addChild(fi)

    def _make_folder_item(self, folder):
        item = QTreeWidgetItem(["\U0001f4c1  " + folder.name])
        item.setData(0, ROLE_TYPE, NODE_FOLDER)
        item.setData(0, ROLE_ID, folder.folder_id)
        item.setForeground(0, QBrush(QColor("#6c757d")))
        return item

    def _add_sub_folders(self, parent, pid, all_folders):
        for f in all_folders:
            if f.parent_id == pid:
                fi = self._make_folder_item(f)
                self._add_sub_folders(fi, f.folder_id, all_folders)
                parent.addChild(fi)

    def _on_ws_changed(self, idx):
        ws_id = self._ws_combo.itemData(idx)
        if ws_id:
            self._engine.switch_workspace(ws_id)
            self._build_tree()
            self.workspace_selected.emit(ws_id)

    def _on_item_clicked(self, item, _col):
        ntype = item.data(0, ROLE_TYPE)
        nid   = item.data(0, ROLE_ID)
        if ntype == NODE_PROJECT:
            self.project_selected.emit(nid)
        elif ntype == NODE_WS:
            self.workspace_selected.emit(nid)

    def _on_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        if not item:
            return
        ntype = item.data(0, ROLE_TYPE)
        nid   = item.data(0, ROLE_ID)
        menu  = QMenu(self)
        if ntype == NODE_PROJECT:
            proj = self._engine.get_project(nid)
            if not proj:
                return
            a_edit  = menu.addAction("\u270f  \u7f16\u8f91\u9879\u76ee")
            menu.addSeparator()
            star_txt = ("\u2606  \u53d6\u6d88\u6536\u85cf"
                        if proj.starred else "\u2b50  \u52a0\u5165\u6536\u85cf")
            a_star  = menu.addAction(star_txt)
            menu.addSeparator()
            sm          = menu.addMenu("\u8bbe\u7f6e\u72b6\u6001")
            a_active    = sm.addAction("\U0001f7e2  \u6d3b\u8dc3")
            a_paused    = sm.addAction("\U0001f7e1  \u6682\u505c")
            a_complete  = sm.addAction("\U0001f535  \u5df2\u5b8c\u6210")
            a_archive   = sm.addAction("\u26ab  \u5f52\u6863")
            menu.addSeparator()
            a_del = menu.addAction("\U0001f5d1  \u5220\u9664\u9879\u76ee")
            action = menu.exec(self._tree.viewport().mapToGlobal(pos))
            if action == a_edit:
                self.project_selected.emit(nid)
            elif action == a_star:
                (self._engine.unstar_project if proj.starred
                 else self._engine.star_project)(nid)
            elif action == a_active:
                self._engine.workspace.set_project_status(nid, ProjectStatus.ACTIVE)
                self._refresh()
            elif action == a_paused:
                self._engine.workspace.set_project_status(nid, ProjectStatus.PAUSED)
                self._refresh()
            elif action == a_complete:
                self._engine.workspace.set_project_status(nid, ProjectStatus.COMPLETED)
                self._refresh()
            elif action == a_archive:
                self._engine.workspace.set_project_status(nid, ProjectStatus.ARCHIVED)
                self._refresh()
            elif action == a_del:
                if QMessageBox.question(
                    self, "\u786e\u8ba4\u5220\u9664",
                    "\u786e\u8ba4\u5220\u9664\u9879\u76ee\u300c" + proj.name + "\u300d\uff1f",
                    QMessageBox.Yes | QMessageBox.No
                ) == QMessageBox.Yes:
                    self._engine.delete_project(nid)
        elif ntype == NODE_WS:
            a_sw = menu.addAction("\U0001f504  \u5207\u6362\u5230\u6b64\u5de5\u4f5c\u533a")
            a_ar = menu.addAction("\U0001f4e6  \u5f52\u6863\u5de5\u4f5c\u533a")
            action = menu.exec(self._tree.viewport().mapToGlobal(pos))
            if action == a_sw:
                self._engine.switch_workspace(nid)
                self._refresh()
            elif action == a_ar:
                self._engine.workspace.archive_workspace(nid)
                self._refresh()

    def selected_project_id(self):
        item = self._tree.currentItem()
        if item and item.data(0, ROLE_TYPE) == NODE_PROJECT:
            return item.data(0, ROLE_ID)
        return None

    def select_project(self, project_id):
        def _find(parent):
            for i in range(parent.childCount()):
                c = parent.child(i)
                if c.data(0, ROLE_TYPE) == NODE_PROJECT and c.data(0, ROLE_ID) == project_id:
                    self._tree.setCurrentItem(c)
                    return True
                if _find(c):
                    return True
            return False
        _find(self._tree.invisibleRootItem())


class ProjectDetailPanel(QTabWidget):
    edit_requested = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._proj_id = None
        self._init_ui()

    def _init_ui(self):
        self.setTabPosition(QTabWidget.North)
        self.setDocumentMode(True)

        # Tab1: overview
        ov_w = QWidget(); ov_l = QVBoxLayout(ov_w)
        title_bar = QHBoxLayout()
        self._title_lbl = QLabel("\u8bf7\u4ece\u5de6\u4fa7\u9009\u62e9\u9879\u76ee")
        self._title_lbl.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        title_bar.addWidget(self._title_lbl)
        title_bar.addStretch()
        self._status_badge = QLabel("")
        self._status_badge.setFixedHeight(22)
        self._status_badge.setStyleSheet("padding:2px 10px;border-radius:10px;font-size:12px;")
        title_bar.addWidget(self._status_badge)
        self._edit_btn = QPushButton("\u270f  \u7f16\u8f91")
        self._edit_btn.setFixedWidth(72)
        self._edit_btn.clicked.connect(self._on_edit)
        title_bar.addWidget(self._edit_btn)
        ov_l.addLayout(title_bar)
        self._color_bar = QFrame()
        self._color_bar.setFixedHeight(4)
        self._color_bar.setStyleSheet("background:#4a6cf7;border-radius:2px;")
        ov_l.addWidget(self._color_bar)
        self._ov_table = QTableWidget(0, 2)
        self._ov_table.setHorizontalHeaderLabels(["\u5c5e\u6027", "\u503c"])
        self._ov_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._ov_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ov_table.setAlternatingRowColors(True)
        self._ov_table.verticalHeader().setVisible(False)
        self._ov_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        ov_l.addWidget(self._ov_table)
        self.addTab(ov_w, "\U0001f4cb  \u6982\u89c8")

        # Tab2: resources
        res_w = QWidget(); res_l = QVBoxLayout(res_w)
        cards_bar = QHBoxLayout()
        self._cards = {}
        for key, icon, label in [
            ("experiments", "\U0001f9ea", "\u5b9e\u9a8c"),
            ("datasets",    "\U0001f4be", "\u6570\u636e\u96c6"),
            ("features",    "\U0001f4d0", "\u56e0\u5b50"),
            ("strategies",  "\U0001f4c8", "\u7b56\u7565"),
            ("models",      "\U0001f916", "\u6a21\u578b"),
        ]:
            card = self._make_stat_card(icon, label, "0")
            self._cards[key] = card
            cards_bar.addWidget(card)
        res_l.addLayout(cards_bar)
        res_lbl = QLabel("\u5173\u8054\u8d44\u6e90 ID \u5217\u8868\uff1a")
        res_lbl.setStyleSheet("color:#6c757d;font-size:12px;margin-top:8px;")
        res_l.addWidget(res_lbl)
        self._res_text = QTextEdit()
        self._res_text.setReadOnly(True)
        self._res_text.setFont(QFont("Consolas", 10))
        self._res_text.setStyleSheet(
            "background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;")
        res_l.addWidget(self._res_text)
        self.addTab(res_w, "\U0001f517  \u5173\u8054\u8d44\u6e90")

        # Tab3: folders
        fol_w = QWidget(); fol_l = QVBoxLayout(fol_w)
        fol_bar = QHBoxLayout()
        self._fol_add_btn = QPushButton("+ \u65b0\u5efa\u6587\u4ef6\u5939")
        self._fol_add_btn.setFixedWidth(110)
        self._fol_add_btn.clicked.connect(self._on_add_folder)
        fol_bar.addWidget(self._fol_add_btn)
        fol_bar.addStretch()
        fol_l.addLayout(fol_bar)
        self._fol_tree = QTreeWidget()
        self._fol_tree.setHeaderHidden(True)
        self._fol_tree.setIndentation(16)
        fol_l.addWidget(self._fol_tree)
        self.addTab(fol_w, "\U0001f4c1  \u6587\u4ef6\u5939")

    @staticmethod
    def _make_stat_card(icon, label, value):
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame{background:#fff;border:1px solid #dee2e6;"
            "border-radius:8px;padding:6px;}")
        lay = QVBoxLayout(card); lay.setSpacing(2)
        icon_lbl = QLabel(icon + "  " + label)
        icon_lbl.setStyleSheet("color:#6c757d;font-size:11px;")
        lay.addWidget(icon_lbl)
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet("font-size:20px;font-weight:bold;color:#1a1f36;")
        val_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(val_lbl)
        card._val_lbl = val_lbl
        return card

    def load(self, project_id):
        self._proj_id = project_id
        proj = self._engine.get_project(project_id)
        if not proj:
            self.clear_panel(); return
        self._load_overview(proj)
        self._load_resources(proj)
        self._load_folders(proj)

    def clear_panel(self):
        self._proj_id = None
        self._title_lbl.setText("\u8bf7\u4ece\u5de6\u4fa7\u9009\u62e9\u9879\u76ee")
        self._status_badge.setText("")
        self._status_badge.setStyleSheet("")
        self._color_bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        self._ov_table.setRowCount(0)
        for card in self._cards.values():
            card._val_lbl.setText("0")
        self._res_text.clear()
        self._fol_tree.clear()

    def _load_overview(self, proj):
        self._title_lbl.setText(proj.name)
        sc = STATUS_COLORS.get(proj.status, "#6c757d")
        sl = STATUS_LABELS.get(proj.status, proj.status.value)
        self._status_badge.setText(sl)
        self._status_badge.setStyleSheet(
            "padding:2px 10px;border-radius:10px;"
            "background:" + sc + "22;color:" + sc + ";"
            "font-size:12px;font-weight:bold;"
            "border:1px solid " + sc + "44;")
        color = proj.color or "#4a6cf7"
        self._color_bar.setStyleSheet("background:" + color + ";border-radius:2px;")
        self._ov_table.setRowCount(0)
        rows = [
            ("\u9879\u76ee ID",   proj.project_id),
            ("\u5de5\u4f5c\u533a ID", proj.workspace_id),
            ("\u540d\u79f0",      proj.name),
            ("\u72b6\u6001",      sl),
            ("\u662f\u5426\u6536\u85cf", "\u2b50 \u662f" if proj.starred else "\u5426"),
            ("\u6807\u7b7e",      ", ".join(proj.tags) if proj.tags else "\u2014"),
            ("\u989c\u8272",      proj.color or "\u2014"),
            ("\u63cf\u8ff0",      proj.description or "\u2014"),
            ("\u521b\u5efa\u8005", proj.created_by or "\u2014"),
            ("\u521b\u5efa\u65f6\u95f4", proj.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("\u66f4\u65b0\u65f6\u95f4", proj.updated_at.strftime("%Y-%m-%d %H:%M:%S")),
        ]
        for key, val in rows:
            r = self._ov_table.rowCount()
            self._ov_table.insertRow(r)
            k_item = QTableWidgetItem(key)
            k_item.setForeground(QBrush(QColor("#6c757d")))
            self._ov_table.setItem(r, 0, k_item)
            self._ov_table.setItem(r, 1, QTableWidgetItem(str(val)))

    def _load_resources(self, proj):
        counts = {
            "experiments": len(proj.experiment_ids),
            "datasets":    len(proj.dataset_ids),
            "features":    len(proj.feature_ids),
            "strategies":  len(proj.strategy_ids),
            "models":      len(proj.model_ids),
        }
        for key, card in self._cards.items():
            card._val_lbl.setText(str(counts.get(key, 0)))
        labels = {
            "experiments": "\U0001f9ea \u5b9e\u9a8c",
            "datasets":    "\U0001f4be \u6570\u636e\u96c6",
            "features":    "\U0001f4d0 \u56e0\u5b50",
            "strategies":  "\U0001f4c8 \u7b56\u7565",
            "models":      "\U0001f916 \u6a21\u578b",
        }
        id_attrs = {
            "experiments": "experiment_ids",
            "datasets":    "dataset_ids",
            "features":    "feature_ids",
            "strategies":  "strategy_ids",
            "models":      "model_ids",
        }
        lines = []
        for key in ("experiments", "datasets", "features", "strategies", "models"):
            ids = getattr(proj, id_attrs[key])
            lbl = labels[key]
            if ids:
                lines.append(lbl + "\uff08" + str(len(ids)) + "\uff09")
                lines.extend("  \u2022 " + i for i in ids)
            else:
                lines.append(lbl + "\uff080\uff09  \u2014")
        self._res_text.setPlainText("\n".join(lines))

    def _load_folders(self, proj):
        self._fol_tree.clear()
        folders = self._engine.workspace.list_folders(proj.project_id)
        def _add(parent, pid):
            for f in folders:
                if f.parent_id == pid:
                    item = QTreeWidgetItem(["\U0001f4c1  " + f.name])
                    item.setData(0, ROLE_ID, f.folder_id)
                    parent.addChild(item)
                    _add(item, f.folder_id)
        _add(self._fol_tree.invisibleRootItem(), "")
        self._fol_tree.expandAll()

    def _on_edit(self):
        if self._proj_id:
            self.edit_requested.emit(self._proj_id)

    def _on_add_folder(self):
        if not self._proj_id:
            return
        name, ok = QInputDialog.getText(
            self, "\u65b0\u5efa\u6587\u4ef6\u5939",
            "\u6587\u4ef6\u5939\u540d\u79f0\uff1a")
        if ok and name.strip():
            self._engine.workspace.create_folder(
                name.strip(), project_id=self._proj_id)
            proj = self._engine.get_project(self._proj_id)
            if proj:
                self._load_folders(proj)


def _sep():
    line = QFrame()
    line.setFrameShape(QFrame.VLine)
    line.setStyleSheet("color:#dee2e6;")
    return line


class WorkspaceTab(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # toolbar
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_new_ws    = QPushButton("+ \u65b0\u5efa\u5de5\u4f5c\u533a")
        self._btn_new_proj  = QPushButton("+ \u65b0\u5efa\u9879\u76ee")
        self._btn_edit_proj = QPushButton("\u270f  \u7f16\u8f91\u9879\u76ee")
        self._btn_del_proj  = QPushButton("\U0001f5d1  \u5220\u9664\u9879\u76ee")
        for btn in (self._btn_new_ws, self._btn_new_proj,
                    self._btn_edit_proj, self._btn_del_proj):
            btn.setFixedHeight(28); tb.addWidget(btn)
        tb.addWidget(_sep())
        self._btn_star = QPushButton("\u2b50  \u6536\u85cf / \u53d6\u6d88")
        self._btn_star.setFixedHeight(28); tb.addWidget(self._btn_star)
        tb.addStretch()
        tb.addWidget(QLabel("\u641c\u7d22:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("\u9879\u76ee\u540d\u79f0 / \u6807\u7b7e...")
        self._search_box.setFixedWidth(180); self._search_box.setFixedHeight(28)
        tb.addWidget(self._search_box)
        self._btn_search = QPushButton("\u641c\u7d22"); self._btn_search.setFixedSize(52, 28)
        self._btn_reset  = QPushButton("\u91cd\u7f6e"); self._btn_reset.setFixedSize(52, 28)
        tb.addWidget(self._btn_search); tb.addWidget(self._btn_reset)
        root.addLayout(tb)

        # ws info bar
        self._ws_info = QLabel("\u5f53\u524d\u5de5\u4f5c\u533a\uff1a\u2014")
        self._ws_info.setStyleSheet(
            "background:#f0f4ff;border:1px solid #c7d2fe;"
            "border-radius:4px;padding:4px 10px;"
            "color:#4a6cf7;font-size:12px;")
        root.addWidget(self._ws_info)

        # splitter
        sp = QSplitter(Qt.Horizontal)
        self._explorer = ProjectExplorer(self._engine)
        self._explorer.setMinimumWidth(200)
        sp.addWidget(self._explorer)
        self._detail = ProjectDetailPanel(self._engine)
        sp.addWidget(self._detail)
        sp.setSizes([260, 940])
        sp.setStretchFactor(0, 0); sp.setStretchFactor(1, 1)
        root.addWidget(sp)

        # status
        self._status = QLabel("\u5c31\u7eea")
        self._status.setStyleSheet("color:#6c757d;font-size:11px;")
        root.addWidget(self._status)

        # connect
        self._btn_new_ws.clicked.connect(self._on_new_ws)
        self._btn_new_proj.clicked.connect(self._on_new_proj)
        self._btn_edit_proj.clicked.connect(lambda: self._on_edit_proj())
        self._btn_del_proj.clicked.connect(self._on_del_proj)
        self._btn_star.clicked.connect(self._on_toggle_star)
        self._btn_search.clicked.connect(self._on_search)
        self._btn_reset.clicked.connect(self._on_reset)
        self._search_box.returnPressed.connect(self._on_search)
        self._explorer.project_selected.connect(self._on_project_selected)
        self._explorer.workspace_selected.connect(self._on_workspace_selected)
        self._detail.edit_requested.connect(self._on_edit_proj)

        for ev in (EVENT_RO_WS_CREATED, EVENT_RO_WS_SWITCHED,
                   EVENT_RO_WS_UPDATED, EVENT_RO_WS_DELETED):
            self._engine.event_engine.register(ev, self._on_ws_event)

        self._refresh_ws_info()

    # ------ workspace ops ------

    def _on_new_ws(self):
        dlg = WorkspaceDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            ws = self._engine.create_workspace(
                name=dlg.get_name(),
                description=dlg.get_description(),
                root_path=dlg.get_root_path(),
                members=dlg.get_members(),
                tags=dlg.get_tags(),
            )
            self._set_status("\u5de5\u4f5c\u533a\u300c" + ws.name + "\u300d\u5df2\u521b\u5efa")

    def _on_ws_event(self, _=None):
        self._refresh_ws_info()

    def _refresh_ws_info(self):
        ws = self._engine.get_active_workspace()
        if ws:
            members = "\u3001".join(ws.members) if ws.members else "\u65e0"
            info = ("\u5f53\u524d\u5de5\u4f5c\u533a\uff1a" + ws.name
                    + "    \u6839\u76ee\u5f55\uff1a" + (ws.root_path or "\u2014")
                    + "    \u6210\u5458\uff1a" + members
                    + "    \u9879\u76ee\u6570\uff1a" + str(len(ws.project_ids)))
            self._ws_info.setText(info)
        else:
            self._ws_info.setText(
                "\u5f53\u524d\u5de5\u4f5c\u533a\uff1a\u2014  \uff08\u8bf7\u5148\u65b0\u5efa\u5de5\u4f5c\u533a\uff09")

    # ------ project ops ------

    def _on_new_proj(self):
        ws = self._engine.get_active_workspace()
        if not ws:
            QMessageBox.warning(self, "\u63d0\u793a",
                                "\u8bf7\u5148\u521b\u5efa\u5e76\u5207\u6362\u5230\u4e00\u4e2a\u5de5\u4f5c\u533a\u3002")
            return
        dlg = ProjectDialog(parent=self, workspace_id=ws.workspace_id)
        if dlg.exec() == QDialog.Accepted:
            proj = self._engine.create_project(
                name=dlg.get_name(),
                workspace_id=ws.workspace_id,
                description=dlg.get_description(),
                tags=dlg.get_tags(),
            )
            proj.color = dlg.get_color()
            self._engine.update_project(proj)
            self._set_status("\u9879\u76ee\u300c" + proj.name + "\u300d\u5df2\u521b\u5efa")
            self._explorer.select_project(proj.project_id)
            self._detail.load(proj.project_id)

    def _on_edit_proj(self, project_id=""):
        pid = project_id or self._explorer.selected_project_id()
        if not pid:
            return
        proj = self._engine.get_project(pid)
        if not proj:
            return
        dlg = ProjectDialog(parent=self, record=proj,
                            workspace_id=proj.workspace_id)
        if dlg.exec() == QDialog.Accepted:
            proj.name        = dlg.get_name()
            proj.description = dlg.get_description()
            proj.tags        = dlg.get_tags()
            proj.color       = dlg.get_color()
            self._engine.update_project(proj)
            self._detail.load(pid)
            self._set_status("\u9879\u76ee\u300c" + proj.name + "\u300d\u5df2\u66f4\u65b0")

    def _on_del_proj(self):
        pid = self._explorer.selected_project_id()
        if not pid:
            return
        proj = self._engine.get_project(pid)
        if not proj:
            return
        if QMessageBox.question(
            self, "\u786e\u8ba4\u5220\u9664",
            "\u786e\u8ba4\u5220\u9664\u9879\u76ee\u300c" + proj.name + "\u300d\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self._engine.delete_project(pid)
            self._detail.clear_panel()
            self._set_status("\u9879\u76ee\u300c" + proj.name + "\u300d\u5df2\u5220\u9664")

    def _on_toggle_star(self):
        pid = self._explorer.selected_project_id()
        if not pid:
            return
        proj = self._engine.get_project(pid)
        if not proj:
            return
        if proj.starred:
            self._engine.unstar_project(pid)
            self._set_status("\u5df2\u53d6\u6d88\u6536\u85cf\u300c" + proj.name + "\u300d")
        else:
            self._engine.star_project(pid)
            self._set_status("\u5df2\u6536\u85cf\u300c" + proj.name + "\u300d")
        self._detail.load(pid)

    # ------ search ------

    def _on_search(self):
        kw = self._search_box.text().strip()
        if not kw:
            return
        results = self._engine.search_projects(kw)
        if results:
            self._detail.load(results[0].project_id)
            self._explorer.select_project(results[0].project_id)
            self._set_status("\u641c\u7d22\u300c" + kw + "\u300d\uff1a\u627e\u5230 "
                             + str(len(results)) + " \u4e2a\u9879\u76ee")
        else:
            self._set_status("\u641c\u7d22\u300c" + kw + "\u300d\uff1a\u672a\u627e\u5230\u5339\u914d\u9879\u76ee")

    def _on_reset(self):
        self._search_box.clear()
        self._detail.clear_panel()
        self._set_status("\u5c31\u7eea")

    # ------ tree callbacks ------

    def _on_project_selected(self, project_id):
        self._detail.load(project_id)
        proj = self._engine.get_project(project_id)
        if proj:
            self._set_status("\u5f53\u524d\u9879\u76ee\uff1a" + proj.name)

    def _on_workspace_selected(self, workspace_id):
        ws = self._engine.get_workspace(workspace_id)
        if ws:
            self._set_status("\u5de5\u4f5c\u533a\uff1a" + ws.name
                             + "  \u5171 " + str(len(ws.project_ids)) + " \u4e2a\u9879\u76ee")

    def _set_status(self, msg):
        self._status.setText(msg)
