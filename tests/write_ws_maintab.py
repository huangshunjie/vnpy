"""write_ws_maintab.py — WorkspaceTab main class + _sep helper"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\workspace_tab.py"
)

MAINTAB = """

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
        self._btn_new_ws    = QPushButton("+ \\u65b0\\u5efa\\u5de5\\u4f5c\\u533a")
        self._btn_new_proj  = QPushButton("+ \\u65b0\\u5efa\\u9879\\u76ee")
        self._btn_edit_proj = QPushButton("\\u270f  \\u7f16\\u8f91\\u9879\\u76ee")
        self._btn_del_proj  = QPushButton("\\U0001f5d1  \\u5220\\u9664\\u9879\\u76ee")
        for btn in (self._btn_new_ws, self._btn_new_proj,
                    self._btn_edit_proj, self._btn_del_proj):
            btn.setFixedHeight(28); tb.addWidget(btn)
        tb.addWidget(_sep())
        self._btn_star = QPushButton("\\u2b50  \\u6536\\u85cf / \\u53d6\\u6d88")
        self._btn_star.setFixedHeight(28); tb.addWidget(self._btn_star)
        tb.addStretch()
        tb.addWidget(QLabel("\\u641c\\u7d22:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("\\u9879\\u76ee\\u540d\\u79f0 / \\u6807\\u7b7e...")
        self._search_box.setFixedWidth(180); self._search_box.setFixedHeight(28)
        tb.addWidget(self._search_box)
        self._btn_search = QPushButton("\\u641c\\u7d22"); self._btn_search.setFixedSize(52, 28)
        self._btn_reset  = QPushButton("\\u91cd\\u7f6e"); self._btn_reset.setFixedSize(52, 28)
        tb.addWidget(self._btn_search); tb.addWidget(self._btn_reset)
        root.addLayout(tb)

        # ws info bar
        self._ws_info = QLabel("\\u5f53\\u524d\\u5de5\\u4f5c\\u533a\\uff1a\\u2014")
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
        self._status = QLabel("\\u5c31\\u7eea")
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
            self._set_status("\\u5de5\\u4f5c\\u533a\\u300c" + ws.name + "\\u300d\\u5df2\\u521b\\u5efa")

    def _on_ws_event(self, _=None):
        self._refresh_ws_info()

    def _refresh_ws_info(self):
        ws = self._engine.get_active_workspace()
        if ws:
            members = "\\u3001".join(ws.members) if ws.members else "\\u65e0"
            info = ("\\u5f53\\u524d\\u5de5\\u4f5c\\u533a\\uff1a" + ws.name
                    + "    \\u6839\\u76ee\\u5f55\\uff1a" + (ws.root_path or "\\u2014")
                    + "    \\u6210\\u5458\\uff1a" + members
                    + "    \\u9879\\u76ee\\u6570\\uff1a" + str(len(ws.project_ids)))
            self._ws_info.setText(info)
        else:
            self._ws_info.setText(
                "\\u5f53\\u524d\\u5de5\\u4f5c\\u533a\\uff1a\\u2014  \\uff08\\u8bf7\\u5148\\u65b0\\u5efa\\u5de5\\u4f5c\\u533a\\uff09")

    # ------ project ops ------

    def _on_new_proj(self):
        ws = self._engine.get_active_workspace()
        if not ws:
            QMessageBox.warning(self, "\\u63d0\\u793a",
                                "\\u8bf7\\u5148\\u521b\\u5efa\\u5e76\\u5207\\u6362\\u5230\\u4e00\\u4e2a\\u5de5\\u4f5c\\u533a\\u3002")
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
            self._set_status("\\u9879\\u76ee\\u300c" + proj.name + "\\u300d\\u5df2\\u521b\\u5efa")
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
            self._set_status("\\u9879\\u76ee\\u300c" + proj.name + "\\u300d\\u5df2\\u66f4\\u65b0")

    def _on_del_proj(self):
        pid = self._explorer.selected_project_id()
        if not pid:
            return
        proj = self._engine.get_project(pid)
        if not proj:
            return
        if QMessageBox.question(
            self, "\\u786e\\u8ba4\\u5220\\u9664",
            "\\u786e\\u8ba4\\u5220\\u9664\\u9879\\u76ee\\u300c" + proj.name + "\\u300d\\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self._engine.delete_project(pid)
            self._detail.clear_panel()
            self._set_status("\\u9879\\u76ee\\u300c" + proj.name + "\\u300d\\u5df2\\u5220\\u9664")

    def _on_toggle_star(self):
        pid = self._explorer.selected_project_id()
        if not pid:
            return
        proj = self._engine.get_project(pid)
        if not proj:
            return
        if proj.starred:
            self._engine.unstar_project(pid)
            self._set_status("\\u5df2\\u53d6\\u6d88\\u6536\\u85cf\\u300c" + proj.name + "\\u300d")
        else:
            self._engine.star_project(pid)
            self._set_status("\\u5df2\\u6536\\u85cf\\u300c" + proj.name + "\\u300d")
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
            self._set_status("\\u641c\\u7d22\\u300c" + kw + "\\u300d\\uff1a\\u627e\\u5230 "
                             + str(len(results)) + " \\u4e2a\\u9879\\u76ee")
        else:
            self._set_status("\\u641c\\u7d22\\u300c" + kw + "\\u300d\\uff1a\\u672a\\u627e\\u5230\\u5339\\u914d\\u9879\\u76ee")

    def _on_reset(self):
        self._search_box.clear()
        self._detail.clear_panel()
        self._set_status("\\u5c31\\u7eea")

    # ------ tree callbacks ------

    def _on_project_selected(self, project_id):
        self._detail.load(project_id)
        proj = self._engine.get_project(project_id)
        if proj:
            self._set_status("\\u5f53\\u524d\\u9879\\u76ee\\uff1a" + proj.name)

    def _on_workspace_selected(self, workspace_id):
        ws = self._engine.get_workspace(workspace_id)
        if ws:
            self._set_status("\\u5de5\\u4f5c\\u533a\\uff1a" + ws.name
                             + "  \\u5171 " + str(len(ws.project_ids)) + " \\u4e2a\\u9879\\u76ee")

    def _set_status(self, msg):
        self._status.setText(msg)
"""

ast.parse(MAINTAB)
with open(P, "a", encoding="utf-8") as f:
    f.write(MAINTAB)

# final full syntax check
import ast as _ast
full = P.read_text(encoding="utf-8")
_ast.parse(full)
print("WorkspaceTab main class appended OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
