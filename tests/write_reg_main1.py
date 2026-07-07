"""write_reg_main1.py — RegistryTab part1: class + toolbar + sub-tabs"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\registry_tab.py"
)

CODE = """

class RegistryTab(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_new  = QPushButton("+ \\u6ce8\\u518c")
        self._btn_edit = QPushButton("\\u270f  \\u7f16\\u8f91")
        self._btn_del  = QPushButton("\\U0001f5d1  \\u5220\\u9664")
        for btn in (self._btn_new, self._btn_edit, self._btn_del):
            btn.setFixedHeight(28); tb.addWidget(btn)
        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#dee2e6;"); tb.addWidget(sep)
        tb.addStretch()
        tb.addWidget(QLabel("\\u641c\\u7d22:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("\\u540d\\u79f0 / \\u6807\\u7b7e...")
        self._search_box.setFixedWidth(160); self._search_box.setFixedHeight(28)
        tb.addWidget(self._search_box)
        self._btn_search = QPushButton("\\u641c\\u7d22")
        self._btn_search.setFixedSize(52, 28)
        self._btn_reset  = QPushButton("\\u91cd\\u7f6e")
        self._btn_reset.setFixedSize(52, 28)
        tb.addWidget(self._btn_search); tb.addWidget(self._btn_reset)
        root.addLayout(tb)

        self._stats_bar = QLabel("\\u52a0\\u8f7d\\u4e2d...")
        self._stats_bar.setStyleSheet(
            "background:#f0fff4;border:1px solid #a3cfbb;"
            "border-radius:4px;padding:4px 10px;"
            "color:#198754;font-size:12px;")
        root.addWidget(self._stats_bar)

        self._sub_tabs = QTabWidget()
        self._sub_tabs.setDocumentMode(True)

        def _make_split(list_w, detail_w):
            w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0)
            sp = QSplitter(Qt.Horizontal)
            sp.addWidget(list_w); sp.addWidget(detail_w)
            sp.setSizes([260, 740])
            sp.setStretchFactor(0, 0); sp.setStretchFactor(1, 1)
            l.addWidget(sp); return w

        self._ds_list   = DatasetList(self._engine)
        self._ds_detail = DatasetDetail(self._engine)
        self._sub_tabs.addTab(_make_split(self._ds_list, self._ds_detail),
                              "\\U0001f4be  Dataset")

        self._ft_list   = FeatureList(self._engine)
        self._ft_detail = FeatureDetail(self._engine)
        self._sub_tabs.addTab(_make_split(self._ft_list, self._ft_detail),
                              "\\U0001f4d0  Feature")

        self._st_list   = StrategyList(self._engine)
        self._st_detail = StrategyDetail(self._engine)
        self._sub_tabs.addTab(_make_split(self._st_list, self._st_detail),
                              "\\U0001f4c8  Strategy")

        self._ml_list   = ModelList(self._engine)
        self._ml_detail = ModelDetail(self._engine)
        self._sub_tabs.addTab(_make_split(self._ml_list, self._ml_detail),
                              "\\U0001f916  Model")

        root.addWidget(self._sub_tabs)

        self._status = QLabel("\\u5c31\\u7eea")
        self._status.setStyleSheet("color:#6c757d;font-size:11px;")
        root.addWidget(self._status)

        self._ds_list.selected.connect(self._ds_detail.load)
        self._ft_list.selected.connect(self._ft_detail.load)
        self._st_list.selected.connect(self._st_detail.load)
        self._ml_list.selected.connect(self._ml_detail.load)
        self._ds_list.selected.connect(lambda i: self._on_sel("Dataset", i))
        self._ft_list.selected.connect(lambda i: self._on_sel("Feature", i))
        self._st_list.selected.connect(lambda i: self._on_sel("Strategy", i))
        self._ml_list.selected.connect(lambda i: self._on_sel("Model", i))

        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_del.clicked.connect(self._on_delete)
        self._btn_search.clicked.connect(self._on_search)
        self._btn_reset.clicked.connect(self._on_reset)
        self._search_box.returnPressed.connect(self._on_search)

        for ev in (EVENT_RO_DS_CREATED, EVENT_RO_DS_UPDATED, EVENT_RO_DS_DELETED,
                   EVENT_RO_FT_CREATED, EVENT_RO_FT_UPDATED, EVENT_RO_FT_DELETED,
                   EVENT_RO_ST_CREATED, EVENT_RO_ST_UPDATED, EVENT_RO_ST_DELETED,
                   EVENT_RO_ML_CREATED, EVENT_RO_ML_UPDATED, EVENT_RO_ML_DELETED,
                   EVENT_RO_ML_DEPLOYED):
            self._engine.event_engine.register(ev, self._on_stats_event)

        self._refresh_stats()

    def _on_sel(self, label, item_id):
        getters = {
            "Dataset":  self._engine.get_dataset,
            "Feature":  self._engine.get_feature,
            "Strategy": self._engine.get_strategy,
            "Model":    self._engine.get_model,
        }
        obj = getters[label](item_id)
        name = obj.name if obj else item_id
        self._set_status(label + ": " + name)
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("RegistryTab part1 OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
