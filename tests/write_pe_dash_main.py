"""write_pe_dash_main.py — append DashboardTab main class"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\dashboard.py"
)

CHUNK2 = '''

class DashboardTab(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(5_000)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # header
        hdr = QHBoxLayout()
        title = QLabel("Platform Health Dashboard")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        self._last_update = QLabel("")
        self._last_update.setStyleSheet("font-size:11px;color:#8c8c8c;")
        hdr.addWidget(self._last_update)
        btn = QPushButton("\\U0001f504 \\u5237\\u65b0")
        btn.setFixedSize(68, 26)
        btn.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;"
            "font-size:12px;border:none;")
        btn.clicked.connect(self._refresh)
        hdr.addWidget(btn)
        root.addLayout(hdr)

        body = QHBoxLayout(); body.setSpacing(12)
        left = QVBoxLayout(); left.setSpacing(10)

        # ring + layer cards
        ring_row = QHBoxLayout(); ring_row.setSpacing(12)
        self._ring = HealthRingWidget()
        ring_row.addWidget(self._ring)
        ring_right = QVBoxLayout(); ring_right.setSpacing(6)
        self._layer_cards: dict = {}
        for layer in MetricLayer:
            card = LayerScoreCard(layer)
            self._layer_cards[layer] = card
            ring_right.addWidget(card)
        ring_row.addLayout(ring_right, 1)
        left.addLayout(ring_row)

        # stat cards grid
        sg = QGridLayout(); sg.setSpacing(8)
        self._stat_cards: dict = {}
        card_defs = [
            ("deploy_total", "\\u90e8\\u7f72\\u603b\\u6570", "\\U0001f680", "#4a6cf7"),
            ("deploy_live",  "\\u751f\\u4ea7\\u8fd0\\u884c", "\\u2705",     "#52c41a"),
            ("task_running", "\\u8fd0\\u884c\\u4efb\\u52a1", "\\u2699\\ufe0f","#faad14"),
            ("task_pending", "\\u5f85\\u5904\\u7406",        "\\u23f3",     "#8c8c8c"),
            ("task_failed",  "\\u5931\\u8d25\\u4efb\\u52a1", "\\u274c",     "#ff4d4f"),
            ("health_warn",  "\\u7b56\\u7565\\u544a\\u8b66", "\\U0001f493","#faad14"),
            ("configs",      "\\u914d\\u7f6e\\u9879",        "\\U0001f5c2\\ufe0f","#722ed1"),
            ("users",        "\\u7528\\u6237\\u6570",        "\\U0001f464", "#13c2c2"),
        ]
        for i, (key, label, icon, color) in enumerate(card_defs):
            card = StatCard(label, icon, color)
            self._stat_cards[key] = card
            sg.addWidget(card, i // 4, i % 4)
        left.addLayout(sg)
        body.addLayout(left, 3)

        # right: alert panel
        right = QVBoxLayout(); right.setSpacing(6)
        alert_hdr = QHBoxLayout()
        atitle = QLabel("\\U0001f514 \\u6d3b\\u8dc3\\u544a\\u8b66")
        atitle.setStyleSheet("font-size:13px;font-weight:bold;color:#1a1f36;")
        alert_hdr.addWidget(atitle); alert_hdr.addStretch()
        self._alert_count = QLabel("0")
        self._alert_count.setStyleSheet(
            "background:#52c41a;color:#fff;border-radius:8px;"
            "padding:1px 7px;font-size:11px;")
        alert_hdr.addWidget(self._alert_count)
        right.addLayout(alert_hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:#f8f9fa;border-radius:6px;")
        self._alert_container = QWidget()
        self._alert_layout    = QVBoxLayout(self._alert_container)
        self._alert_layout.setAlignment(Qt.AlignTop)
        self._alert_layout.setSpacing(0)
        scroll.setWidget(self._alert_container)
        right.addWidget(scroll, 1)

        self._no_alert_lbl = QLabel("\\u2705 \\u6240\\u6709\\u7cfb\\u7edf\\u8fd0\\u884c\\u6b63\\u5e38")
        self._no_alert_lbl.setAlignment(Qt.AlignCenter)
        self._no_alert_lbl.setStyleSheet(
            "font-size:13px;color:#52c41a;padding:20px;")
        self._alert_layout.addWidget(self._no_alert_lbl)

        body.addLayout(right, 2)
        root.addLayout(body, 1)

    def _refresh(self):
        if not self._engine:
            return
        try:
            oe = self._engine.observability
            sc = oe.get_health_score()
            self._ring.update_score(sc.score, sc.level)

            layer_map = {
                MetricLayer.DATA:     sc.data_score,
                MetricLayer.STRATEGY: sc.strategy_score,
                MetricLayer.TRADING:  sc.trading_score,
                MetricLayer.SYSTEM:   sc.system_score,
            }
            for layer, card in self._layer_cards.items():
                s = layer_map[layer]
                lv = (HealthLevel.GREEN if s >= 80 else
                      HealthLevel.YELLOW if s >= 50 else HealthLevel.RED)
                card.update_score(s, lv)

            ts  = self._engine.tasks.stats()
            ds  = self._engine.deployment.stats()
            hs  = self._engine.health.stats()
            cs  = self._engine.config.stats()
            ss  = self._engine.security.stats()
            by_stage = ds.get("by_stage", {})

            self._stat_cards["deploy_total"].set_value(ds.get("total", 0))
            self._stat_cards["deploy_live"].set_value(
                by_stage.get("production", 0))
            self._stat_cards["task_running"].set_value(ts.get("running", 0))
            self._stat_cards["task_pending"].set_value(ts.get("pending", 0))
            self._stat_cards["task_failed"].set_value(ts.get("failed", 0))
            self._stat_cards["health_warn"].set_value(
                hs.get("warning", 0) + hs.get("critical", 0))
            self._stat_cards["configs"].set_value(cs.get("total", 0))
            self._stat_cards["users"].set_value(ss.get("users", 0))

            alerts = oe.list_alerts(active_only=True)
            self._rebuild_alerts(alerts)
            self._last_update.setText(
                "\\u66f4\\u65b0: " + sc.updated_at.strftime("%H:%M:%S"))
        except Exception:
            pass

    def _rebuild_alerts(self, alerts):
        while self._alert_layout.count():
            item = self._alert_layout.takeAt(0)
            if item.widget() and item.widget() is not self._no_alert_lbl:
                item.widget().deleteLater()
        if not alerts:
            self._alert_count.setText("0")
            self._alert_count.setStyleSheet(
                "background:#52c41a;color:#fff;border-radius:8px;"
                "padding:1px 7px;font-size:11px;")
            self._alert_layout.addWidget(self._no_alert_lbl)
            self._no_alert_lbl.show()
        else:
            self._no_alert_lbl.hide()
            self._alert_count.setText(str(len(alerts)))
            self._alert_count.setStyleSheet(
                "background:#ff4d4f;color:#fff;border-radius:8px;"
                "padding:1px 7px;font-size:11px;")
            for alert in sorted(
                    alerts, key=lambda a: a.created_at, reverse=True)[:30]:
                row = AlertRow(alert)
                self._alert_layout.addWidget(row)

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
'''

ast.parse(CHUNK2)
with open(P, "a", encoding="utf-8") as f:
    f.write(CHUNK2)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("DashboardTab OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
