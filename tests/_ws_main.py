"""Append WorkspaceTab main class to workspace_tab.py"""
import pathlib
P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\workspace_tab.py"
)

CODE = '''

# ═══════════════════════════════════════════════════════════════════
# WorkspaceTab  主 Tab
# ═══════════════════════════════════════════════════════════════════

class WorkspaceTab(QWidget):
    """
    Phase 2 完整 Workspace System Tab。
    左：ProjectExplorer（3:10 分栏）  右：ProjectDetailPanel
    """

    def __init__(self, engine: ResearchOpsEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # ── 顶部工具栏 ───────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self._btn_new_ws   = QPushButton("＋ 新建工作区")
        self._btn_new_proj = QPushButton("＋ 新建项目")
        self._btn_edit_proj= QPushButton("✏  编辑项目")
        self._btn_del_proj = QPushButton("🗑  删除项目")

        for btn in (self._btn_new_ws, self._btn_new_proj,
                    self._btn_edit_proj, self._btn_del_proj):
            btn.setFixedHeight(28)
            toolbar.addWidget(btn)

        toolbar.addWidget(_sep())

        self._btn_star   = QPushButton("⭐  收藏 / 取消")
        self._btn_star.setFixedHeight(28)
        toolbar.addWidget(self._btn_star)

        toolbar.addStretch()

        toolbar.addWidget(QLabel("搜索:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("项目名称 / 标签…")
        self._search_box.setFixedWidth(180)
        self._search_box.setFixedHeight(28)
        toolbar.addWidget(self._search_box)

        self._btn_search = QPushButton("搜索")
        self._btn_search.setFixedSize(52, 28)
        toolbar.addWidget(self._btn_search)

        self._btn_reset = QPushButton("重置")
        self._btn_reset.setFixedSize(52, 28)
        toolbar.addWidget(self._btn_reset)

        root.addLayout(toolbar)

        # ── 活跃工作区信息栏 ─────────────────────────────────────────
        self._ws_info_bar = QLabel("当前工作区：—")
        self._ws_info_bar.setStyleSheet(
            "background:#f0f4ff; border:1px solid #c7d2fe;"
            "border-radius:4px; padding:4px 10px;"
            "color:#4a6cf7; font-size:12px;")
        root.addWidget(self._ws_info_bar)

        # ── 主区域：左右分栏 ─────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)

        self._explorer = ProjectExplorer(self._engine)
        self._explorer.setMinimumWidth(200)
        splitter.addWidget(self._explorer)

        self._detail = ProjectDetailPanel(self._engine)
        splitter.addWidget(self._detail)
        splitter.setSizes([260, 940])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter)

        # ── 状态栏 ───────────────────────────────────────────────────
        self._status = QLabel("就绪")
        self._status.setStyleSheet("color:#6c757d; font-size:11px;")
        root.addWidget(self._status)

        # ── 信号连接 ─────────────────────────────────────────────────
        self._btn_new_ws.clicked.connect(self._on_new_ws)
        self._btn_new_proj.clicked.connect(self._on_new_proj)
        self._btn_edit_proj.clicked.connect(self._on_edit_proj)
        self._btn_del_proj.clicked.connect(self._on_del_proj)
        self._btn_star.clicked.connect(self._on_toggle_star)
        self._btn_search.clicked.connect(self._on_search)
        self._btn_reset.clicked.connect(self._on_reset)
        self._search_box.returnPressed.connect(self._on_search)

        self._explorer.project_selected.connect(self._on_project_selected)
        self._explorer.workspace_selected.connect(self._on_workspace_selected)
        self._detail.edit_requested.connect(self._on_edit_proj)

        # 注册事件更新工作区信息栏
        for ev in (EVENT_RO_WS_CREATED, EVENT_RO_WS_SWITCHED,
                   EVENT_RO_WS_UPDATED, EVENT_RO_WS_DELETED):
            self._engine.event_engine.register(ev, self._on_ws_event)

        self._refresh_ws_info()

    # ------------------------------------------------------------------
    # 工作区操作
    # ------------------------------------------------------------------

    def _on_new_ws(self):
        dlg = WorkspaceDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            ws = self._engine.create_workspace(
                name        = dlg.get_name(),
                description = dlg.get_description(),
                root_path   = dlg.get_root_path(),
                members     = dlg.get_members(),
                tags        = dlg.get_tags(),
            )
            self._set_status(f"工作区「{ws.name}」已创建")

    def _on_ws_event(self, _=None):
        self._refresh_ws_info()

    def _refresh_ws_info(self):
        ws = self._engine.get_active_workspace()
        if ws:
            members = "、".join(ws.members) if ws.members else "无"
            self._ws_info_bar.setText(
                f"当前工作区：{ws.name}    "
                f"根目录：{ws.root_path or '—'}    "
                f"成员：{members}    "
                f"项目数：{len(ws.project_ids)}")
        else:
            self._ws_info_bar.setText("当前工作区：—  （请先新建工作区）")

    # ------------------------------------------------------------------
    # 项目操作
    # ------------------------------------------------------------------

    def _on_new_proj(self):
        ws = self._engine.get_active_workspace()
        if not ws:
            QMessageBox.warning(self, "提示", "请先创建并切换到一个工作区。")
            return
        dlg = ProjectDialog(parent=self, workspace_id=ws.workspace_id)
        if dlg.exec() == QDialog.Accepted:
            proj = self._engine.create_project(
                name         = dlg.get_name(),
                workspace_id = ws.workspace_id,
                description  = dlg.get_description(),
                tags         = dlg.get_tags(),
            )
            # 更新颜色
            proj.color    = dlg.get_color()
            proj.created_by = ""
            self._engine.update_project(proj)
            self._set_status(f"项目「{proj.name}」已创建")
            self._explorer.select_project(proj.project_id)
            self._detail.load(proj.project_id)

    def _on_edit_proj(self, project_id: str = ""):
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
            self._set_status(f"项目「{proj.name}」已更新")

    def _on_del_proj(self):
        pid = self._explorer.selected_project_id()
        if not pid:
            return
        proj = self._engine.get_project(pid)
        if not proj:
            return
        if QMessageBox.question(
            self, "确认删除",
            f"确认删除项目「{proj.name}」？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self._engine.delete_project(pid)
            self._detail.clear_panel()
            self._set_status(f"项目「{proj.name}」已删除")

    def _on_toggle_star(self):
        pid = self._explorer.selected_project_id()
        if not pid:
            return
        proj = self._engine.get_project(pid)
        if not proj:
            return
        if proj.starred:
            self._engine.unstar_project(pid)
            self._set_status(f"已取消收藏「{proj.name}」")
        else:
            self._engine.star_project(pid)
            self._set_status(f"已收藏「{proj.name}」")
        self._detail.load(pid)

    # ------------------------------------------------------------------
    # 搜索
    # ------------------------------------------------------------------

    def _on_search(self):
        kw = self._search_box.text().strip()
        if not kw:
            return
        results = self._engine.search_projects(kw)
        if results:
            self._detail.load(results[0].project_id)
            self._explorer.select_project(results[0].project_id)
            self._set_status(
                f"搜索「{kw}」：找到 {len(results)} 个项目，显示第一个")
        else:
            self._set_status(f"搜索「{kw}」：未找到匹配项目")

    def _on_reset(self):
        self._search_box.clear()
        self._detail.clear_panel()
        self._set_status("就绪")

    # ------------------------------------------------------------------
    # 树选中回调
    # ------------------------------------------------------------------

    def _on_project_selected(self, project_id: str):
        self._detail.load(project_id)
        proj = self._engine.get_project(project_id)
        if proj:
            self._set_status(f"当前项目：{proj.name}")

    def _on_workspace_selected(self, workspace_id: str):
        ws = self._engine.get_workspace(workspace_id)
        if ws:
            self._set_status(f"工作区：{ws.name}  共 {len(ws.project_ids)} 个项目")

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _set_status(self, msg: str):
        self._status.setText(msg)


def _sep() -> QFrame:
    """竖分割线辅助函数。"""
    line = QFrame()
    line.setFrameShape(QFrame.VLine)
    line.setStyleSheet("color:#dee2e6;")
    return line
'''

with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
print("WorkspaceTab main class appended OK, size:", P.stat().st_size)
