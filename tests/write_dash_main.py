"""write_dash_main.py — DashboardTab main class"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\dashboard_tab.py"
)

CODE = '''

# =================================================================
# DashboardTab  — main widget
# =================================================================

class DashboardTab(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._register_events()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ── top bar ───────────────────────────────────────────────
        top = QHBoxLayout()
        title = QLabel("\\U0001f4ca  ResearchOps Dashboard")
        title.setStyleSheet(
            "font-size:16px;font-weight:bold;color:#1a1f36;")
        top.addWidget(title)
        top.addStretch()
        self._btn_refresh = QPushButton("\\U0001f504  \\u5237\\u65b0")
        self._btn_refresh.setFixedHeight(28)
        self._btn_refresh.clicked.connect(self._do_refresh)
        top.addWidget(self._btn_refresh)
        self._auto_lbl = QLabel("\\u81ea\\u52a8\\u5237\\u65b0: 30s")
        self._auto_lbl.setStyleSheet("color:#6c757d;font-size:11px;")
        top.addWidget(self._auto_lbl)
        root.addLayout(top)

        # ── header stat strip ─────────────────────────────────────
        strip = QHBoxLayout(); strip.setSpacing(6)
        self._strip_cards: List[KpiCard] = []
        for icon, label, color in [
            ("🧪", "实验",     C_BLUE),
            ("▶",  "运行",     C_GREEN),
            ("🤖", "模型",     C_PURPLE),
            ("📈", "策略",     C_GREEN),
            ("🔄", "Pipeline", C_GOLD),
            ("📝", "报告",     C_BLUE),
        ]:
            c = KpiCard(icon, label, "0", color)
            c.setFixedHeight(90)
            strip.addWidget(c)
            self._strip_cards.append(c)
        root.addLayout(strip)

        # ── main body: left=grid+alerts, right=feed ───────────────
        sp = QSplitter(Qt.Horizontal)
        sp.setChildrenCollapsible(False)

        left = QWidget()
        left_l = QVBoxLayout(left); left_l.setContentsMargins(0,0,0,0)
        left_l.setSpacing(8)

        self._grid = StatGrid(self._engine)
        left_l.addWidget(self._grid)

        self._alerts = AlertPanel(self._engine)
        self._alerts.setMinimumHeight(160)
        left_l.addWidget(self._alerts, 1)

        sp.addWidget(left)

        right = QWidget()
        right_l = QVBoxLayout(right); right_l.setContentsMargins(0,0,0,0)
        self._feed = ActivityFeed(self._engine)
        right_l.addWidget(self._feed, 1)
        sp.addWidget(right)

        sp.setSizes([640, 320])
        sp.setStretchFactor(0, 2)
        sp.setStretchFactor(1, 1)
        root.addWidget(sp, 1)

        # ── status bar ────────────────────────────────────────────
        self._status = QLabel("\\u5c31\\u7eea")
        self._status.setStyleSheet("color:#6c757d;font-size:11px;")
        root.addWidget(self._status)

        # ── auto-refresh timer ────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.setInterval(30_000)
        self._timer.timeout.connect(self._do_refresh)
        self._timer.start()

        self._do_refresh()

    # ── event wiring ──────────────────────────────────────────────

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in EVENT_ALL:
            ee.register(ev, self._on_any_event)

    def _on_any_event(self, _=None):
        self._do_refresh()

    # ── refresh ───────────────────────────────────────────────────

    def _do_refresh(self):
        try:
            s = self._engine.get_platform_stats()
        except Exception:
            self._set_status("\\u83b7\\u53d6\\u7edf\\u8ba1\\u5931\\u8d25")
            return

        # strip cards
        strip_map = [
            ("experiment", "experiments"),
            ("experiment", "runs"),
            ("registry",   "models"),
            ("registry",   "strategies"),
            ("pipeline",   "pipelines"),
            ("report",     "reports"),
        ]
        for card, (sec, key) in zip(self._strip_cards, strip_map):
            card.update_value(str(s.get(sec, {}).get(key, 0)))

        # grid + alerts
        self._grid.refresh()
        self._alerts.refresh()

        self._set_status(
            "\\u4e0a\\u6b21\\u5237\\u65b0: " + datetime.now().strftime("%H:%M:%S"))

    def _set_status(self, msg: str):
        self._status.setText(msg)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("DashboardTab main OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
