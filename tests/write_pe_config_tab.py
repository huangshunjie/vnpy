"""write_pe_config_tab.py — append ConfigTab main class"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\config.py"
)

CODE = '''

class ConfigTab(QWidget):
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
        root.setContentsMargins(12, 12, 12, 12); root.setSpacing(8)
        hdr = QHBoxLayout()
        title = QLabel("\\U0001f5c2\\ufe0f  Configuration Management")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet("font-size:11px;color:#8c8c8c;")
        hdr.addWidget(self._stats_lbl)
        btn = QPushButton("\\U0001f504 \\u5237\\u65b0")
        btn.setFixedSize(68, 26)
        btn.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;"
            "font-size:12px;border:none;")
        btn.clicked.connect(self._refresh)
        hdr.addWidget(btn)
        root.addLayout(hdr)

        sp = QSplitter(Qt.Horizontal)
        self._config_list  = ConfigList(self._engine)
        self._detail_panel = DetailPanel(self._engine)
        self._config_list.set_select_callback(self._on_selected)
        sp.addWidget(self._config_list)
        sp.addWidget(self._detail_panel)
        sp.setSizes([280, 920])
        sp.setStretchFactor(0, 0); sp.setStretchFactor(1, 1)
        root.addWidget(sp, 1)

        self._status = QLabel("\\u5c31\\u7eea")
        self._status.setStyleSheet("font-size:11px;color:#6c757d;")
        root.addWidget(self._status)

    def _on_selected(self, config_id):
        self._detail_panel.load(config_id)

    def _refresh(self):
        self._config_list.refresh()
        if self._engine:
            s = self._engine.config.stats()
            self._stats_lbl.setText(
                f"\\u603b\\u8ba1: {s.get('total',0)}"
                f"  \\u5df2\\u9501\\u5b9a: {s.get('locked',0)}"
                f"  \\u7248\\u672c\\u6570: {s.get('total_versions',0)}")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("ConfigTab OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
