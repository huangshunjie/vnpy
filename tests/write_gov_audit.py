"""write_gov_audit.py — AuditLogPanel + GovernanceTab"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\governance_tab.py"
)

CODE = '''

class AuditLogPanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        fb = QHBoxLayout(); fb.setSpacing(6)
        self._actor_box = QLineEdit()
        self._actor_box.setPlaceholderText("\\u64cd\\u4f5c\\u4eba\\u8fc7\\u6ee4")
        self._actor_box.setFixedHeight(26)
        fb.addWidget(self._actor_box, 1)
        self._type_box = QLineEdit()
        self._type_box.setPlaceholderText("\\u8d44\\u4ea7\\u7c7b\\u578b\\u8fc7\\u6ee4")
        self._type_box.setFixedHeight(26)
        fb.addWidget(self._type_box, 1)
        self._btn_filter = QPushButton("\\u8fc7\\u6ee4")
        self._btn_filter.setFixedHeight(26)
        self._btn_filter.clicked.connect(self._refresh)
        fb.addWidget(self._btn_filter)
        self._btn_clear = QPushButton("\\u91cd\\u7f6e")
        self._btn_clear.setFixedHeight(26)
        self._btn_clear.clicked.connect(self._on_clear_filter)
        fb.addWidget(self._btn_clear)
        root.addLayout(fb)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "\\u65f6\\u95f4","\\u64cd\\u4f5c\\u4eba","\\u64cd\\u4f5c",
            "\\u8d44\\u4ea7\\u7c7b\\u578b","\\u8d44\\u4ea7\\u540d\\u79f0"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.itemClicked.connect(self._on_click)
        root.addWidget(self._table)

        dg = QGroupBox("\\u65e5\\u5fd7\\u8be6\\u60c5")
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

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in GOV_EVENTS:
            ee.register(ev, lambda _: self._refresh())

    def _on_clear_filter(self):
        self._actor_box.clear(); self._type_box.clear(); self._refresh()

    def _refresh(self):
        actor = self._actor_box.text().strip() or None
        ttype = self._type_box.text().strip() or None
        logs  = self._engine.list_audit_logs(
            actor=actor, target_type=ttype, limit=200)
        self._table.setRowCount(0)
        for lg in logs:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0,
                QTableWidgetItem(lg.timestamp.strftime("%Y-%m-%d %H:%M:%S")))
            self._table.setItem(r, 1, QTableWidgetItem(lg.actor or ""))
            ai = QTableWidgetItem(lg.action.value if hasattr(lg.action, "value")
                                  else str(lg.action))
            ai.setForeground(QBrush(QColor("#4a6cf7")))
            self._table.setItem(r, 2, ai)
            self._table.setItem(r, 3, QTableWidgetItem(lg.target_type or ""))
            self._table.setItem(r, 4, QTableWidgetItem(lg.target_name or ""))
            for c in range(5):
                self._table.item(r, c).setData(ROLE_ID, lg.log_id)

    def _on_click(self, item):
        lid  = item.data(ROLE_ID)
        logs = self._engine.list_audit_logs(limit=200)
        lg   = next((l for l in logs if l.log_id == lid), None)
        if not lg: return
        self._detail.setRowCount(0)
        for k, v in [
            ("ID", lg.log_id[:16]),
            ("\\u64cd\\u4f5c\\u4eba", lg.actor or "\\u2014"),
            ("\\u64cd\\u4f5c", lg.action.value if hasattr(lg.action,"value") else str(lg.action)),
            ("\\u8d44\\u4ea7\\u7c7b\\u578b", lg.target_type or "\\u2014"),
            ("\\u8d44\\u4ea7 ID", lg.target_id[:16] if lg.target_id else "\\u2014"),
            ("\\u8d44\\u4ea7\\u540d\\u79f0", lg.target_name or "\\u2014"),
            ("IP", lg.ip_address or "\\u2014"),
            ("\\u5907\\u6ce8", lg.note or "\\u2014"),
            ("\\u65f6\\u95f4", lg.timestamp.strftime("%Y-%m-%d %H:%M:%S")),
        ]:
            r = self._detail.rowCount(); self._detail.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._detail.setItem(r, 0, ki)
            self._detail.setItem(r, 1, QTableWidgetItem(str(v)))
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("AuditLogPanel OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
