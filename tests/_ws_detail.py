"""Append ProjectDetailPanel to workspace_tab.py"""
import pathlib
P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\workspace_tab.py"
)

CODE = '''

# ═══════════════════════════════════════════════════════════════════
# ProjectDetailPanel  右侧详情面板（3 个子 Tab）
# ═══════════════════════════════════════════════════════════════════

class ProjectDetailPanel(QTabWidget):
    """
    概览 / 关联资源 / 文件夹结构
    """
    # 请求外部编辑项目
    edit_requested = Signal(str)

    def __init__(self, engine: ResearchOpsEngine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._proj_id: Optional[str] = None
        self._init_ui()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _init_ui(self):
        self.setTabPosition(QTabWidget.North)
        self.setDocumentMode(True)

        # ── Tab 1：概览 ─────────────────────────────────────────────
        ov_w = QWidget()
        ov_l = QVBoxLayout(ov_w)

        # 顶部：项目名 + 状态 + 编辑按钮
        title_bar = QHBoxLayout()
        self._title_lbl = QLabel("请从左侧选择项目")
        self._title_lbl.setStyleSheet(
            "font-size:16px; font-weight:bold; color:#1a1f36;")
        title_bar.addWidget(self._title_lbl)
        title_bar.addStretch()
        self._status_badge = QLabel("")
        self._status_badge.setFixedHeight(22)
        self._status_badge.setStyleSheet(
            "padding:2px 10px; border-radius:10px;"
            "font-size:12px; font-weight:bold;")
        title_bar.addWidget(self._status_badge)
        self._edit_btn = QPushButton("✏  编辑")
        self._edit_btn.setFixedWidth(72)
        self._edit_btn.clicked.connect(self._on_edit)
        title_bar.addWidget(self._edit_btn)
        ov_l.addLayout(title_bar)

        # 色条
        self._color_bar = QFrame()
        self._color_bar.setFixedHeight(4)
        self._color_bar.setStyleSheet("background:#4a6cf7; border-radius:2px;")
        ov_l.addWidget(self._color_bar)

        # 属性表格
        self._ov_table = QTableWidget(0, 2)
        self._ov_table.setHorizontalHeaderLabels(["属性", "值"])
        self._ov_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._ov_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ov_table.setAlternatingRowColors(True)
        self._ov_table.verticalHeader().setVisible(False)
        self._ov_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        ov_l.addWidget(self._ov_table)

        self.addTab(ov_w, "📋  概览")

        # ── Tab 2：关联资源 ──────────────────────────────────────────
        res_w = QWidget()
        res_l = QVBoxLayout(res_w)

        # 统计卡片行
        cards_bar = QHBoxLayout()
        self._cards: dict = {}
        for key, icon, label in [
            ("experiments", "🧪", "实验"),
            ("datasets",    "💾", "数据集"),
            ("features",    "📐", "因子"),
            ("strategies",  "📈", "策略"),
            ("models",      "🤖", "模型"),
        ]:
            card = self._make_stat_card(icon, label, "0")
            self._cards[key] = card
            cards_bar.addWidget(card)
        res_l.addLayout(cards_bar)

        # 资源列表（简单 QTextEdit 显示）
        res_lbl = QLabel("关联资源 ID 列表：")
        res_lbl.setStyleSheet("color:#6c757d; font-size:12px; margin-top:8px;")
        res_l.addWidget(res_lbl)
        self._res_text = QTextEdit()
        self._res_text.setReadOnly(True)
        self._res_text.setFont(QFont("Consolas", 10))
        self._res_text.setStyleSheet(
            "background:#f8f9fa; border:1px solid #dee2e6; border-radius:4px;")
        res_l.addWidget(self._res_text)

        self.addTab(res_w, "🔗  关联资源")

        # ── Tab 3：文件夹结构 ────────────────────────────────────────
        fol_w = QWidget()
        fol_l = QVBoxLayout(fol_w)

        fol_bar = QHBoxLayout()
        self._fol_add_btn = QPushButton("+ 新建文件夹")
        self._fol_add_btn.setFixedWidth(110)
        self._fol_add_btn.clicked.connect(self._on_add_folder)
        fol_bar.addWidget(self._fol_add_btn)
        fol_bar.addStretch()
        fol_l.addLayout(fol_bar)

        self._fol_tree = QTreeWidget()
        self._fol_tree.setHeaderHidden(True)
        self._fol_tree.setIndentation(16)
        fol_l.addWidget(self._fol_tree)

        self.addTab(fol_w, "📁  文件夹")

    @staticmethod
    def _make_stat_card(icon: str, label: str, value: str) -> QWidget:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame{background:#fff; border:1px solid #dee2e6;"
            "border-radius:8px; padding:6px;}")
        lay = QVBoxLayout(card)
        lay.setSpacing(2)
        icon_lbl = QLabel(f"{icon}  {label}")
        icon_lbl.setStyleSheet("color:#6c757d; font-size:11px;")
        lay.addWidget(icon_lbl)
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(
            "font-size:20px; font-weight:bold; color:#1a1f36;")
        val_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(val_lbl)
        # 把数值 label 附在 card 上，方便后续更新
        card._val_lbl = val_lbl
        return card

    # ------------------------------------------------------------------
    # 加载 / 清空
    # ------------------------------------------------------------------

    def load(self, project_id: str):
        self._proj_id = project_id
        proj = self._engine.get_project(project_id)
        if not proj:
            self.clear_panel()
            return
        self._load_overview(proj)
        self._load_resources(proj)
        self._load_folders(proj)

    def clear_panel(self):
        self._proj_id = None
        self._title_lbl.setText("请从左侧选择项目")
        self._status_badge.setText("")
        self._status_badge.setStyleSheet("")
        self._color_bar.setStyleSheet("background:#dee2e6; border-radius:2px;")
        self._ov_table.setRowCount(0)
        for card in self._cards.values():
            card._val_lbl.setText("0")
        self._res_text.clear()
        self._fol_tree.clear()

    # ------------------------------------------------------------------
    # 概览 Tab
    # ------------------------------------------------------------------

    def _load_overview(self, proj: ProjectRecord):
        self._title_lbl.setText(proj.name)

        status_color = STATUS_COLORS.get(proj.status, "#6c757d")
        status_label = STATUS_LABELS.get(proj.status, proj.status.value)
        self._status_badge.setText(status_label)
        self._status_badge.setStyleSheet(
            f"padding:2px 10px; border-radius:10px;"
            f"background:{status_color}22; color:{status_color};"
            f"font-size:12px; font-weight:bold;"
            f"border:1px solid {status_color}44;")

        color = proj.color or "#4a6cf7"
        self._color_bar.setStyleSheet(
            f"background:{color}; border-radius:2px;")

        self._ov_table.setRowCount(0)
        rows = [
            ("项目 ID",   proj.project_id),
            ("工作区 ID", proj.workspace_id),
            ("名称",      proj.name),
            ("状态",      status_label),
            ("是否收藏",  "⭐ 是" if proj.starred else "否"),
            ("标签",      ", ".join(proj.tags) if proj.tags else "—"),
            ("颜色",      proj.color or "—"),
            ("描述",      proj.description or "—"),
            ("创建者",    proj.created_by or "—"),
            ("创建时间",  proj.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("更新时间",  proj.updated_at.strftime("%Y-%m-%d %H:%M:%S")),
        ]
        for key, val in rows:
            r = self._ov_table.rowCount()
            self._ov_table.insertRow(r)
            k_item = QTableWidgetItem(key)
            k_item.setForeground(QBrush(QColor("#6c757d")))
            self._ov_table.setItem(r, 0, k_item)
            self._ov_table.setItem(r, 1, QTableWidgetItem(str(val)))

    # ------------------------------------------------------------------
    # 关联资源 Tab
    # ------------------------------------------------------------------

    def _load_resources(self, proj: ProjectRecord):
        counts = {
            "experiments": len(proj.experiment_ids),
            "datasets":    len(proj.dataset_ids),
            "features":    len(proj.feature_ids),
            "strategies":  len(proj.strategy_ids),
            "models":      len(proj.model_ids),
        }
        for key, card in self._cards.items():
            card._val_lbl.setText(str(counts.get(key, 0)))

        lines = []
        for label, ids in [
            ("🧪 实验",  proj.experiment_ids),
            ("💾 数据集", proj.dataset_ids),
            ("📐 因子",  proj.feature_ids),
            ("📈 策略",  proj.strategy_ids),
            ("🤖 模型",  proj.model_ids),
        ]:
            if ids:
                lines.append(f"\n{label}（{len(ids)}）")
                lines.extend(f"  • {i}" for i in ids)
            else:
                lines.append(f"\n{label}（0）  —")
        self._res_text.setPlainText("\n".join(lines).strip())

    # ------------------------------------------------------------------
    # 文件夹 Tab
    # ------------------------------------------------------------------

    def _load_folders(self, proj: ProjectRecord):
        self._fol_tree.clear()
        folders = self._engine.workspace.list_folders(proj.project_id)

        def _add(parent, parent_id):
            for f in folders:
                if f.parent_id == parent_id:
                    item = QTreeWidgetItem([f"📁  {f.name}"])
                    item.setData(0, ROLE_ID, f.folder_id)
                    parent.addChild(item)
                    _add(item, f.folder_id)

        root = self._fol_tree.invisibleRootItem()
        _add(root, "")
        self._fol_tree.expandAll()

    # ------------------------------------------------------------------
    # 操作
    # ------------------------------------------------------------------

    def _on_edit(self):
        if self._proj_id:
            self.edit_requested.emit(self._proj_id)

    def _on_add_folder(self):
        if not self._proj_id:
            return
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "新建文件夹", "文件夹名称：")
        if ok and name.strip():
            self._engine.workspace.create_folder(
                name.strip(), project_id=self._proj_id)
            proj = self._engine.get_project(self._proj_id)
            if proj:
                self._load_folders(proj)
'''

with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
print("ProjectDetailPanel appended OK, size:", P.stat().st_size)
