"""write_ws_explorer.py"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\workspace_tab.py"
)

EXPLORER = """

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
        ws_bar.addWidget(QLabel("\\u5de5\\u4f5c\\u533a:"))
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
        ri = QTreeWidgetItem(["\\u2b50  \\u6536\\u85cf\\u5939"])
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
        wi = QTreeWidgetItem(["\\U0001f5c2  " + ws.name])
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
        icons = {"active": "\\U0001f7e2", "paused": "\\U0001f7e1",
                 "completed": "\\U0001f535", "archived": "\\u26ab"}
        icon  = icons.get(proj.status.value, "\\u26aa")
        label = ("\\u2b50 " if proj.starred else "") + icon + "  " + proj.name
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
        item = QTreeWidgetItem(["\\U0001f4c1  " + folder.name])
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
            a_edit  = menu.addAction("\\u270f  \\u7f16\\u8f91\\u9879\\u76ee")
            menu.addSeparator()
            star_txt = ("\\u2606  \\u53d6\\u6d88\\u6536\\u85cf"
                        if proj.starred else "\\u2b50  \\u52a0\\u5165\\u6536\\u85cf")
            a_star  = menu.addAction(star_txt)
            menu.addSeparator()
            sm          = menu.addMenu("\\u8bbe\\u7f6e\\u72b6\\u6001")
            a_active    = sm.addAction("\\U0001f7e2  \\u6d3b\\u8dc3")
            a_paused    = sm.addAction("\\U0001f7e1  \\u6682\\u505c")
            a_complete  = sm.addAction("\\U0001f535  \\u5df2\\u5b8c\\u6210")
            a_archive   = sm.addAction("\\u26ab  \\u5f52\\u6863")
            menu.addSeparator()
            a_del = menu.addAction("\\U0001f5d1  \\u5220\\u9664\\u9879\\u76ee")
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
                    self, "\\u786e\\u8ba4\\u5220\\u9664",
                    "\\u786e\\u8ba4\\u5220\\u9664\\u9879\\u76ee\\u300c" + proj.name + "\\u300d\\uff1f",
                    QMessageBox.Yes | QMessageBox.No
                ) == QMessageBox.Yes:
                    self._engine.delete_project(nid)
        elif ntype == NODE_WS:
            a_sw = menu.addAction("\\U0001f504  \\u5207\\u6362\\u5230\\u6b64\\u5de5\\u4f5c\\u533a")
            a_ar = menu.addAction("\\U0001f4e6  \\u5f52\\u6863\\u5de5\\u4f5c\\u533a")
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
"""

# validate before writing
ast.parse(EXPLORER)
with open(P, "a", encoding="utf-8") as f:
    f.write(EXPLORER)
print("ProjectExplorer appended OK, size:", P.stat().st_size)
