"""Append ProjectExplorer to workspace_tab.py"""
import pathlib
P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\workspace_tab.py"
)

CODE = '''

# ═══════════════════════════════════════════════════════════════════
# ProjectExplorer  左侧树形视图
# ═══════════════════════════════════════════════════════════════════

class ProjectExplorer(QWidget):
    """
    三级树：收藏夹 / 工作区 → 项目 → 文件夹
    发出信号：project_selected(project_id)
    """
    project_selected   = Signal(str)
    workspace_selected = Signal(str)

    def __init__(self, engine: ResearchOpsEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._register_events()
        self._refresh()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 0)
        root.setSpacing(4)

        # 工作区切换下拉
        ws_bar = QHBoxLayout()
        ws_bar.addWidget(QLabel("工作区:"))
        self._ws_combo = QComboBox()
        self._ws_combo.setMinimumWidth(140)
        ws_bar.addWidget(self._ws_combo, 1)
        root.addLayout(ws_bar)

        # 树
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(18)
        self._tree.setAnimated(True)
        self._tree.setAlternatingRowColors(False)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        root.addWidget(self._tree)

        # 信号
        self._ws_combo.currentIndexChanged.connect(self._on_ws_changed)
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)

    # ------------------------------------------------------------------
    # 事件注册
    # ------------------------------------------------------------------

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in (EVENT_RO_WS_CREATED, EVENT_RO_WS_UPDATED,
                   EVENT_RO_WS_DELETED, EVENT_RO_WS_SWITCHED,
                   EVENT_RO_PRJ_CREATED, EVENT_RO_PRJ_UPDATED,
                   EVENT_RO_PRJ_DELETED, EVENT_RO_PRJ_STARRED,
                   EVENT_RO_PRJ_UNSTARRED):
            ee.register(ev, self._on_event)

    def _on_event(self, event: Event):
        self._refresh()

    # ------------------------------------------------------------------
    # 刷新
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # 收藏夹节点
    # ------------------------------------------------------------------

    def _add_starred_root(self):
        starred = self._engine.get_starred_projects()
        root = QTreeWidgetItem(["⭐  收藏夹"])
        root.setData(0, ROLE_TYPE, NODE_STARRED)
        root.setData(0, ROLE_ID,   "starred")
        font = QFont(); font.setBold(True)
        root.setFont(0, font)
        for proj in starred:
            child = self._make_project_item(proj)
            root.addChild(child)
        self._tree.addTopLevelItem(root)
        root.setExpanded(True)

    # ------------------------------------------------------------------
    # 工作区节点
    # ------------------------------------------------------------------

    def _add_workspace_node(self, workspace_id: str):
        ws = self._engine.get_workspace(workspace_id)
        if not ws:
            return
        ws_item = QTreeWidgetItem([f"🗂  {ws.name}"])
        ws_item.setData(0, ROLE_TYPE, NODE_WS)
        ws_item.setData(0, ROLE_ID,   workspace_id)
        font = QFont(); font.setBold(True)
        ws_item.setFont(0, font)
        active = self._engine.get_active_workspace()
        if active and active.workspace_id == workspace_id:
            ws_item.setForeground(0, QBrush(QColor("#4a6cf7")))

        for proj in self._engine.list_projects(workspace_id):
            proj_item = self._make_project_item(proj)
            self._add_folder_children(proj_item, proj)
            ws_item.addChild(proj_item)

        self._tree.addTopLevelItem(ws_item)
        ws_item.setExpanded(True)

    def _make_project_item(self, proj: ProjectRecord) -> QTreeWidgetItem:
        status_icon = {"active": "🟢", "paused": "🟡",
                       "completed": "🔵", "archived": "⚫"}.get(
            proj.status.value, "⚪")
        item = QTreeWidgetItem([f"{status_icon}  {proj.name}"])
        item.setData(0, ROLE_TYPE, NODE_PROJECT)
        item.setData(0, ROLE_ID,   proj.project_id)
        color = QColor(proj.color if proj.color else "#4a6cf7")
        item.setForeground(0, QBrush(color))
        if proj.starred:
            item.setText(0, f"⭐ {status_icon}  {proj.name}")
        return item

    def _add_folder_children(
        self, parent: QTreeWidgetItem, proj: ProjectRecord
    ):
        folders = self._engine.workspace.list_folders(proj.project_id)
        top_folders = [f for f in folders if not f.parent_id]
        for folder in top_folders:
            fi = self._make_folder_item(folder)
            self._add_sub_folders(fi, folder.folder_id, folders)
            parent.addChild(fi)

    def _make_folder_item(self, folder: FolderRecord) -> QTreeWidgetItem:
        item = QTreeWidgetItem([f"📁  {folder.name}"])
        item.setData(0, ROLE_TYPE, NODE_FOLDER)
        item.setData(0, ROLE_ID,   folder.folder_id)
        item.setForeground(0, QBrush(QColor("#6c757d")))
        return item

    def _add_sub_folders(
        self,
        parent: QTreeWidgetItem,
        parent_folder_id: str,
        all_folders: list,
    ):
        for f in all_folders:
            if f.parent_id == parent_folder_id:
                fi = self._make_folder_item(f)
                self._add_sub_folders(fi, f.folder_id, all_folders)
                parent.addChild(fi)

    # ------------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------------

    def _on_ws_changed(self, idx: int):
        ws_id = self._ws_combo.itemData(idx)
        if ws_id:
            self._engine.switch_workspace(ws_id)
            self._build_tree()
            self.workspace_selected.emit(ws_id)

    def _on_item_clicked(self, item: QTreeWidgetItem, col: int):
        node_type = item.data(0, ROLE_TYPE)
        node_id   = item.data(0, ROLE_ID)
        if node_type == NODE_PROJECT:
            self.project_selected.emit(node_id)
        elif node_type == NODE_WS:
            self.workspace_selected.emit(node_id)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, col: int):
        item.setExpanded(not item.isExpanded())

    def _on_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        if not item:
            return
        node_type = item.data(0, ROLE_TYPE)
        node_id   = item.data(0, ROLE_ID)
        menu = QMenu(self)

        if node_type == NODE_PROJECT:
            proj = self._engine.get_project(node_id)
            if not proj:
                return
            act_edit = menu.addAction("✏  编辑项目")
            menu.addSeparator()
            if proj.starred:
                act_star = menu.addAction("☆  取消收藏")
            else:
                act_star = menu.addAction("⭐  加入收藏")
            menu.addSeparator()
            status_menu = menu.addMenu("📌  设置状态")
            act_active   = status_menu.addAction("🟢  活跃")
            act_paused   = status_menu.addAction("🟡  暂停")
            act_complete = status_menu.addAction("🔵  已完成")
            act_archive  = status_menu.addAction("⚫  归档")
            menu.addSeparator()
            act_del = menu.addAction("🗑  删除项目")

            action = menu.exec(self._tree.viewport().mapToGlobal(pos))
            if action == act_edit:
                self.project_selected.emit(node_id)
            elif action == act_star:
                if proj.starred:
                    self._engine.unstar_project(node_id)
                else:
                    self._engine.star_project(node_id)
            elif action == act_active:
                self._engine.workspace.set_project_status(
                    node_id, ProjectStatus.ACTIVE)
                self._refresh()
            elif action == act_paused:
                self._engine.workspace.set_project_status(
                    node_id, ProjectStatus.PAUSED)
                self._refresh()
            elif action == act_complete:
                self._engine.workspace.set_project_status(
                    node_id, ProjectStatus.COMPLETED)
                self._refresh()
            elif action == act_archive:
                self._engine.workspace.set_project_status(
                    node_id, ProjectStatus.ARCHIVED)
                self._refresh()
            elif action == act_del:
                if QMessageBox.question(
                    self, "确认删除",
                    f"确认删除项目「{proj.name}」？此操作不可撤销。",
                    QMessageBox.Yes | QMessageBox.No
                ) == QMessageBox.Yes:
                    self._engine.delete_project(node_id)

        elif node_type == NODE_WS:
            act_switch = menu.addAction("🔄  切换到此工作区")
            act_archive = menu.addAction("📦  归档工作区")
            action = menu.exec(self._tree.viewport().mapToGlobal(pos))
            if action == act_switch:
                self._engine.switch_workspace(node_id)
                self._refresh()
            elif action == act_archive:
                self._engine.workspace.archive_workspace(node_id)
                self._refresh()

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def selected_project_id(self) -> Optional[str]:
        item = self._tree.currentItem()
        if item and item.data(0, ROLE_TYPE) == NODE_PROJECT:
            return item.data(0, ROLE_ID)
        return None

    def select_project(self, project_id: str):
        """程序化选中指定项目节点。"""
        def _find(parent, pid):
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child.data(0, ROLE_TYPE) == NODE_PROJECT and \
                   child.data(0, ROLE_ID) == pid:
                    self._tree.setCurrentItem(child)
                    return True
                if _find(child, pid):
                    return True
            return False
        root = self._tree.invisibleRootItem()
        _find(root, project_id)
'''

with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
print("ProjectExplorer appended OK, size:", P.stat().st_size)
