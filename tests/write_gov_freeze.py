"""write_gov_freeze.py — FreezePanel"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\governance_tab.py"
)

CODE = '''

class FreezePanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._show_all = False
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_freeze   = QPushButton("\\U0001f512  \\u51bb\\u7ed3\\u8d44\\u4ea7")
        self._btn_unfreeze = QPushButton("\\U0001f513  \\u89e3\\u51bb\\u7ed3")
        self._chk_all      = QPushButton("\\u663e\\u793a\\u5df2\\u91ca\\u653e")
        self._chk_all.setCheckable(True)
        for b in (self._btn_freeze, self._btn_unfreeze, self._chk_all):
            b.setFixedHeight(26); tb.addWidget(b)
        tb.addStretch(); root.addLayout(tb)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            "\\u8d44\\u4ea7\\u7c7b\\u578b","\\u8d44\\u4ea7\\u540d\\u79f0","\\u7248\\u672c",
            "\\u51bb\\u7ed3\\u4eba","\\u51bb\\u7ed3\\u65f6\\u95f4","\\u72b6\\u6001"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_ctx)
        root.addWidget(self._table)

        # detail panel
        dg = QGroupBox("\\u51bb\\u7ed3\\u8be6\\u60c5")
        dl = QVBoxLayout(dg)
        self._detail = QTableWidget(0, 2)
        self._detail.setHorizontalHeaderLabels(["\\u5c5e\\u6027","\\u503c"])
        self._detail.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._detail.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._detail.setAlternatingRowColors(True)
        self._detail.verticalHeader().setVisible(False)
        self._detail.setFixedHeight(140)
        dl.addWidget(self._detail)
        root.addWidget(dg)

        self._table.itemClicked.connect(self._on_click)
        self._btn_freeze.clicked.connect(self._on_freeze)
        self._btn_unfreeze.clicked.connect(self._on_unfreeze)
        self._chk_all.toggled.connect(self._on_toggle_all)

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in GOV_EVENTS:
            ee.register(ev, lambda _: self._refresh())

    def _on_toggle_all(self, checked): self._show_all = checked; self._refresh()

    def _refresh(self):
        items = self._engine.list_freezes(active_only=not self._show_all)
        self._table.setRowCount(0)
        for fr in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(fr.target_type))
            self._table.setItem(r, 1, QTableWidgetItem(fr.target_name or fr.target_id[:12]))
            self._table.setItem(r, 2, QTableWidgetItem(fr.version or "\\u2014"))
            self._table.setItem(r, 3, QTableWidgetItem(fr.frozen_by or "\\u2014"))
            self._table.setItem(r, 4,
                QTableWidgetItem(fr.frozen_at.strftime("%Y-%m-%d %H:%M")))
            if fr.is_active:
                si = QTableWidgetItem("\\U0001f512 \\u5df2\\u51bb\\u7ed3")
                si.setForeground(QBrush(QColor("#4a6cf7")))
            else:
                si = QTableWidgetItem("\\U0001f513 \\u5df2\\u91ca\\u653e")
                si.setForeground(QBrush(QColor("#6c757d")))
            self._table.setItem(r, 5, si)
            for c in range(6):
                self._table.item(r, c).setData(ROLE_ID, fr.freeze_id)

    def _on_click(self, item):
        fid = item.data(ROLE_ID)
        frs = self._engine.list_freezes(active_only=False)
        fr  = next((f for f in frs if f.freeze_id == fid), None)
        if not fr: return
        self._detail.setRowCount(0)
        rel_at = fr.released_at.strftime("%Y-%m-%d %H:%M") if fr.released_at else "\\u2014"
        for k, v in [
            ("ID", fr.freeze_id[:16]),
            ("\\u8d44\\u4ea7\\u7c7b\\u578b", fr.target_type),
            ("\\u8d44\\u4ea7 ID",    fr.target_id[:16]),
            ("\\u51bb\\u7ed3\\u4eba", fr.frozen_by or "\\u2014"),
            ("\\u51bb\\u7ed3\\u65f6\\u95f4", fr.frozen_at.strftime("%Y-%m-%d %H:%M")),
            ("\\u91ca\\u653e\\u4eba", fr.released_by or "\\u2014"),
            ("\\u91ca\\u653e\\u65f6\\u95f4", rel_at),
            ("\\u51bb\\u7ed3\\u539f\\u56e0", fr.reason or "\\u2014"),
        ]:
            r = self._detail.rowCount(); self._detail.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._detail.setItem(r, 0, ki)
            self._detail.setItem(r, 1, QTableWidgetItem(str(v)))

    def _selected_freeze_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None

    def _on_freeze(self):
        dlg = FreezeDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._engine.freeze(
                target_type=dlg.get_target_type(),
                target_id=dlg.get_target_id(),
                target_name=dlg.get_target_name(),
                version=dlg.get_version(),
                reason=dlg.get_reason(),
                frozen_by=dlg.get_frozen_by())
            self._refresh()

    def _on_unfreeze(self):
        fid = self._selected_freeze_id()
        if not fid:
            QMessageBox.information(
                self, "\\u63d0\\u793a", "\\u8bf7\\u5148\\u9009\\u62e9\\u8981\\u89e3\\u51bb\\u7ed3\\u7684\\u8bb0\\u5f55")
            return
        released_by, ok = self._prompt_user("\\u89e3\\u51bb\\u7ed3\\u64cd\\u4f5c\\u4eba:")
        if ok and released_by:
            self._engine.unfreeze(fid, released_by=released_by)
            self._refresh()

    @staticmethod
    def _prompt_user(prompt: str):
        from PySide6.QtWidgets import QInputDialog
        return QInputDialog.getText(None, "\\u8f93\\u5165", prompt)

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        fid = item.data(ROLE_ID)
        menu    = QMenu(self)
        a_thaw  = menu.addAction("\\U0001f513  \\u89e3\\u51bb\\u7ed3")
        if menu.exec(self._table.viewport().mapToGlobal(pos)) == a_thaw:
            released_by, ok = self._prompt_user("\\u89e3\\u51bb\\u7ed3\\u64cd\\u4f5c\\u4eba:")
            if ok and released_by:
                self._engine.unfreeze(fid, released_by=released_by)
                self._refresh()
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("FreezePanel OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
