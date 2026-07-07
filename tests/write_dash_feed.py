"""write_dash_feed.py — ActivityFeed + AlertPanel"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\dashboard_tab.py"
)

CODE = '''

# =================================================================
# ActivityItem  — single timeline row
# =================================================================

class ActivityItem(QFrame):
    def __init__(self, ts: str, icon: str, text: str,
                 color: str = C_BLUE, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(
            "ActivityItem{background:transparent;border:none;}"
            "ActivityItem:hover{background:#f8f9fa;border-radius:6px;}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(8)

        dot = QLabel("●")
        dot.setStyleSheet(
            "color:" + color + ";font-size:10px;"
            "background:transparent;border:none;")
        dot.setFixedWidth(14)
        lay.addWidget(dot)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            "font-size:14px;background:transparent;border:none;")
        icon_lbl.setFixedWidth(22)
        lay.addWidget(icon_lbl)

        text_lbl = QLabel(text)
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet(
            "font-size:12px;color:#1a1f36;"
            "background:transparent;border:none;")
        lay.addWidget(text_lbl, 1)

        ts_lbl = QLabel(ts)
        ts_lbl.setStyleSheet(
            "font-size:11px;color:#adb5bd;"
            "background:transparent;border:none;")
        ts_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        ts_lbl.setFixedWidth(60)
        lay.addWidget(ts_lbl)


# =================================================================
# ActivityFeed  — scrollable event timeline
# =================================================================

class ActivityFeed(QWidget):
    MAX_ITEMS = 60

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._items: List[Dict] = []   # {ts, icon, text, color}
        self._init_ui()
        self._register_events()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)

        hdr = QHBoxLayout()
        lbl = QLabel("\\U0001f4f0  \\u6700\\u8fd1\\u6d3b\\u52a8")
        lbl.setStyleSheet("font-size:14px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(lbl); hdr.addStretch()
        self._btn_clear = QPushButton("\\u6e05\\u7a7a")
        self._btn_clear.setFixedSize(52, 22)
        self._btn_clear.setStyleSheet("font-size:11px;")
        self._btn_clear.clicked.connect(self._clear)
        hdr.addWidget(self._btn_clear)
        root.addLayout(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#dee2e6;"); root.addWidget(sep)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._content = QWidget()
        self._content.setStyleSheet("background:#fff;")
        self._feed_lay = QVBoxLayout(self._content)
        self._feed_lay.setContentsMargins(4, 4, 4, 4)
        self._feed_lay.setSpacing(2)
        self._feed_lay.addStretch()
        self._scroll.setWidget(self._content)
        root.addWidget(self._scroll, 1)

        self._empty_lbl = QLabel("\\u6682\\u65e0\\u6d3b\\u52a8\\u8bb0\\u5f55")
        self._empty_lbl.setStyleSheet(
            "color:#adb5bd;font-size:13px;"
            "background:transparent;border:none;")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._feed_lay.insertWidget(0, self._empty_lbl)

    _EV_MAP = {
        EVENT_RO_EXP_CREATED:     ("🧪", "新实验创建",    C_BLUE),
        EVENT_RO_EXP_UPDATED:     ("🧪", "实验已更新",    C_BLUE),
        EVENT_RO_EXP_DELETED:     ("🧪", "实验已删除",    C_GRAY),
        EVENT_RO_RUN_STARTED:     ("▶",  "运行已启动",    C_GREEN),
        EVENT_RO_RUN_COMPLETED:   ("✅", "运行已完成",    C_GREEN),
        EVENT_RO_RUN_FAILED:      ("❌", "运行失败",      C_RED),
        EVENT_RO_PL_CREATED:      ("🔄", "Pipeline 创建", C_GOLD),
        EVENT_RO_PL_STARTED:      ("🔄", "Pipeline 启动", C_ORANGE),
        EVENT_RO_PL_COMPLETED:    ("✅", "Pipeline 完成", C_GREEN),
        EVENT_RO_PL_FAILED:       ("❌", "Pipeline 失败", C_RED),
        EVENT_RO_RPT_CREATED:     ("📝", "报告创建",      C_BLUE),
        EVENT_RO_RPT_PUBLISHED:   ("📤", "报告已发布",    C_GREEN),
        EVENT_RO_KB_CREATED:      ("🧠", "知识条目新增",  C_TEAL),
        EVENT_RO_KB_UPDATED:      ("🧠", "知识条目更新",  C_TEAL),
        EVENT_RO_DS_CREATED:      ("🗄",  "数据集创建",    C_PURPLE),
        EVENT_RO_DS_REGISTERED:   ("🗄",  "数据集注册",    C_PURPLE),
        EVENT_RO_MODEL_REGISTERED:("🤖", "模型注册",      C_PURPLE),
        EVENT_RO_MODEL_DEPLOYED:  ("🚀", "模型部署",      C_GREEN),
        EVENT_RO_FEAT_REGISTERED: ("📐", "特征注册",      C_TEAL),
        EVENT_RO_STRAT_REGISTERED:("📈", "策略注册",      C_GREEN),
    }

    def _register_events(self):
        ee = self._engine.event_engine
        for ev_type, (icon, text, color) in self._EV_MAP.items():
            def _make_cb(i=icon, t=text, c=color):
                def _cb(_=None):
                    self._push(i, t, c)
                return _cb
            ee.register(ev_type, _make_cb())

    def _push(self, icon: str, text: str, color: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._items.insert(0, {"ts": ts, "icon": icon,
                                "text": text, "color": color})
        if len(self._items) > self.MAX_ITEMS:
            self._items = self._items[:self.MAX_ITEMS]
        self._rebuild()

    def _rebuild(self):
        # remove all except stretch
        while self._feed_lay.count() > 0:
            item = self._feed_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._items:
            lbl = QLabel("\\u6682\\u65e0\\u6d3b\\u52a8\\u8bb0\\u5f55")
            lbl.setStyleSheet(
                "color:#adb5bd;font-size:13px;"
                "background:transparent;border:none;")
            lbl.setAlignment(Qt.AlignCenter)
            self._feed_lay.addWidget(lbl)
        else:
            for d in self._items:
                row = ActivityItem(d["ts"], d["icon"],
                                   d["text"], d["color"])
                self._feed_lay.addWidget(row)
        self._feed_lay.addStretch()
        # auto-scroll to top
        self._scroll.verticalScrollBar().setValue(0)

    def _clear(self):
        self._items.clear(); self._rebuild()

    def push_manual(self, icon: str, text: str, color: str = C_BLUE):
        self._push(icon, text, color)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("ActivityFeed OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
