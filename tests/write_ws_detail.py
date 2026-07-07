"""write_ws_detail.py — ProjectDetailPanel"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\workspace_tab.py"
)

DETAIL = """

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
        self._title_lbl = QLabel("\\u8bf7\\u4ece\\u5de6\\u4fa7\\u9009\\u62e9\\u9879\\u76ee")
        self._title_lbl.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        title_bar.addWidget(self._title_lbl)
        title_bar.addStretch()
        self._status_badge = QLabel("")
        self._status_badge.setFixedHeight(22)
        self._status_badge.setStyleSheet("padding:2px 10px;border-radius:10px;font-size:12px;")
        title_bar.addWidget(self._status_badge)
        self._edit_btn = QPushButton("\\u270f  \\u7f16\\u8f91")
        self._edit_btn.setFixedWidth(72)
        self._edit_btn.clicked.connect(self._on_edit)
        title_bar.addWidget(self._edit_btn)
        ov_l.addLayout(title_bar)
        self._color_bar = QFrame()
        self._color_bar.setFixedHeight(4)
        self._color_bar.setStyleSheet("background:#4a6cf7;border-radius:2px;")
        ov_l.addWidget(self._color_bar)
        self._ov_table = QTableWidget(0, 2)
        self._ov_table.setHorizontalHeaderLabels(["\\u5c5e\\u6027", "\\u503c"])
        self._ov_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._ov_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ov_table.setAlternatingRowColors(True)
        self._ov_table.verticalHeader().setVisible(False)
        self._ov_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        ov_l.addWidget(self._ov_table)
        self.addTab(ov_w, "\\U0001f4cb  \\u6982\\u89c8")

        # Tab2: resources
        res_w = QWidget(); res_l = QVBoxLayout(res_w)
        cards_bar = QHBoxLayout()
        self._cards = {}
        for key, icon, label in [
            ("experiments", "\\U0001f9ea", "\\u5b9e\\u9a8c"),
            ("datasets",    "\\U0001f4be", "\\u6570\\u636e\\u96c6"),
            ("features",    "\\U0001f4d0", "\\u56e0\\u5b50"),
            ("strategies",  "\\U0001f4c8", "\\u7b56\\u7565"),
            ("models",      "\\U0001f916", "\\u6a21\\u578b"),
        ]:
            card = self._make_stat_card(icon, label, "0")
            self._cards[key] = card
            cards_bar.addWidget(card)
        res_l.addLayout(cards_bar)
        res_lbl = QLabel("\\u5173\\u8054\\u8d44\\u6e90 ID \\u5217\\u8868\\uff1a")
        res_lbl.setStyleSheet("color:#6c757d;font-size:12px;margin-top:8px;")
        res_l.addWidget(res_lbl)
        self._res_text = QTextEdit()
        self._res_text.setReadOnly(True)
        self._res_text.setFont(QFont("Consolas", 10))
        self._res_text.setStyleSheet(
            "background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;")
        res_l.addWidget(self._res_text)
        self.addTab(res_w, "\\U0001f517  \\u5173\\u8054\\u8d44\\u6e90")

        # Tab3: folders
        fol_w = QWidget(); fol_l = QVBoxLayout(fol_w)
        fol_bar = QHBoxLayout()
        self._fol_add_btn = QPushButton("+ \\u65b0\\u5efa\\u6587\\u4ef6\\u5939")
        self._fol_add_btn.setFixedWidth(110)
        self._fol_add_btn.clicked.connect(self._on_add_folder)
        fol_bar.addWidget(self._fol_add_btn)
        fol_bar.addStretch()
        fol_l.addLayout(fol_bar)
        self._fol_tree = QTreeWidget()
        self._fol_tree.setHeaderHidden(True)
        self._fol_tree.setIndentation(16)
        fol_l.addWidget(self._fol_tree)
        self.addTab(fol_w, "\\U0001f4c1  \\u6587\\u4ef6\\u5939")

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
        self._title_lbl.setText("\\u8bf7\\u4ece\\u5de6\\u4fa7\\u9009\\u62e9\\u9879\\u76ee")
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
            ("\\u9879\\u76ee ID",   proj.project_id),
            ("\\u5de5\\u4f5c\\u533a ID", proj.workspace_id),
            ("\\u540d\\u79f0",      proj.name),
            ("\\u72b6\\u6001",      sl),
            ("\\u662f\\u5426\\u6536\\u85cf", "\\u2b50 \\u662f" if proj.starred else "\\u5426"),
            ("\\u6807\\u7b7e",      ", ".join(proj.tags) if proj.tags else "\\u2014"),
            ("\\u989c\\u8272",      proj.color or "\\u2014"),
            ("\\u63cf\\u8ff0",      proj.description or "\\u2014"),
            ("\\u521b\\u5efa\\u8005", proj.created_by or "\\u2014"),
            ("\\u521b\\u5efa\\u65f6\\u95f4", proj.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("\\u66f4\\u65b0\\u65f6\\u95f4", proj.updated_at.strftime("%Y-%m-%d %H:%M:%S")),
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
            "experiments": "\\U0001f9ea \\u5b9e\\u9a8c",
            "datasets":    "\\U0001f4be \\u6570\\u636e\\u96c6",
            "features":    "\\U0001f4d0 \\u56e0\\u5b50",
            "strategies":  "\\U0001f4c8 \\u7b56\\u7565",
            "models":      "\\U0001f916 \\u6a21\\u578b",
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
                lines.append(lbl + "\\uff08" + str(len(ids)) + "\\uff09")
                lines.extend("  \\u2022 " + i for i in ids)
            else:
                lines.append(lbl + "\\uff080\\uff09  \\u2014")
        self._res_text.setPlainText("\\n".join(lines))

    def _load_folders(self, proj):
        self._fol_tree.clear()
        folders = self._engine.workspace.list_folders(proj.project_id)
        def _add(parent, pid):
            for f in folders:
                if f.parent_id == pid:
                    item = QTreeWidgetItem(["\\U0001f4c1  " + f.name])
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
            self, "\\u65b0\\u5efa\\u6587\\u4ef6\\u5939",
            "\\u6587\\u4ef6\\u5939\\u540d\\u79f0\\uff1a")
        if ok and name.strip():
            self._engine.workspace.create_folder(
                name.strip(), project_id=self._proj_id)
            proj = self._engine.get_project(self._proj_id)
            if proj:
                self._load_folders(proj)
"""

ast.parse(DETAIL)
with open(P, "a", encoding="utf-8") as f:
    f.write(DETAIL)
print("ProjectDetailPanel appended OK, size:", P.stat().st_size)
