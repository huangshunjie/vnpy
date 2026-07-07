"""write_pe_deploy_list1.py — append DeployList"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\deployment.py"
)

CODE = '''

class DeployList(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._stage_filter = None
        self._on_select_cb = None
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_new = QPushButton("\\u2795 \\u65b0\\u5efa\\u90e8\\u7f72")
        self._btn_new.setFixedHeight(26)
        self._btn_new.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_new.clicked.connect(self._on_new)
        tb.addWidget(self._btn_new)
        self._stage_combo = QComboBox(); self._stage_combo.setFixedHeight(26)
        self._stage_combo.addItem("\\u5168\\u90e8\\u9636\\u6bb5", None)
        for s in DeployStage:
            self._stage_combo.addItem(STAGE_ICON.get(s,"")+" "+s.value, s)
        self._stage_combo.currentIndexChanged.connect(self._on_filter)
        tb.addWidget(self._stage_combo, 1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("\\u641c\\u7d22\\u7b56\\u7565\\u540d")
        self._search.setFixedHeight(26)
        self._search.textChanged.connect(lambda _: self.refresh())
        tb.addWidget(self._search)
        root.addLayout(tb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\\u7b56\\u7565\\u540d\\u79f0","\\u9636\\u6bb5","\\u7248\\u672c","\\u66f4\\u65b0\\u65f6\\u95f4"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.itemClicked.connect(self._on_click)
        self._table.customContextMenuRequested.connect(self._on_ctx)
        root.addWidget(self._table)

    def set_select_callback(self, cb): self._on_select_cb = cb

    def refresh(self):
        if not self._engine: return
        kw    = self._search.text().strip().lower()
        items = self._engine.deployment.list_deployments(stage=self._stage_filter)
        if kw:
            items = [d for d in items
                     if kw in d.strategy_name.lower()
                     or kw in d.strategy_id.lower()]
        self._table.setRowCount(0)
        for d in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(d.strategy_name))
            color = STAGE_COLOR.get(d.current_stage, "#8c8c8c")
            icon  = STAGE_ICON.get(d.current_stage, "")
            si = QTableWidgetItem(icon+" "+d.current_stage.value)
            si.setForeground(QBrush(QColor(color)))
            self._table.setItem(r, 1, si)
            frozen_lbl = " \\U0001f512" if d.is_frozen else ""
            self._table.setItem(r, 2,
                QTableWidgetItem(d.current_version[:8]+frozen_lbl))
            self._table.setItem(r, 3,
                QTableWidgetItem(d.updated_at.strftime("%m-%d %H:%M")))
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, d.deploy_id)

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None

    def _on_filter(self, _):
        self._stage_filter = self._stage_combo.currentData(); self.refresh()

    def _on_click(self, item):
        if self._on_select_cb:
            self._on_select_cb(item.data(ROLE_ID))

    def _on_new(self):
        if not self._engine: return
        dlg = CreateDeployDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._engine.deployment.create_deployment(
                strategy_id=dlg.get_strategy_id(),
                strategy_name=dlg.get_strategy_name(),
                created_by=dlg.get_created_by(),
                tags=dlg.get_tags(), note=dlg.get_note())
            self.refresh()

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        did = item.data(ROLE_ID)
        rec = self._engine.deployment.get_deployment(did)
        if not rec: return
        menu = QMenu(self)
        a_sub  = menu.addAction("\\U0001f4e4  \\u63d0\\u4ea4\\u5ba1\\u6279")
        a_app  = menu.addAction("\\u2705  \\u5ba1\\u6279\\u901a\\u8fc7")
        a_rej  = menu.addAction("\\u274c  \\u62d2\\u7edd\\u5ba1\\u6279")
        menu.addSeparator()
        a_frz  = menu.addAction(
            "\\U0001f513  \\u89e3\\u51bb\\u7ed3" if rec.is_frozen
            else "\\U0001f512  \\u51bb\\u7ed3")
        act = menu.exec(self._table.viewport().mapToGlobal(pos))
        de = self._engine.deployment
        try:
            if act == a_sub:
                de.submit_for_approval(did)
            elif act == a_app:
                dlg = ApproveDialog(True, self)
                if dlg.exec() == QDialog.Accepted:
                    de.approve(did, dlg.get_approver(), dlg.get_note())
            elif act == a_rej:
                dlg = ApproveDialog(False, self)
                if dlg.exec() == QDialog.Accepted:
                    de.reject(did, dlg.get_approver(), dlg.get_note())
            elif act == a_frz:
                de.unfreeze(did) if rec.is_frozen else de.freeze(did)
        except (ValueError, KeyError) as e:
            QMessageBox.warning(self, "\\u9519\\u8bef", str(e))
        self.refresh()
        if self._on_select_cb: self._on_select_cb(did)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("DeployList OK, lines:", len(full.splitlines()))
