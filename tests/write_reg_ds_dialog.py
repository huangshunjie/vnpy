"""write_reg_ds_dialog.py — DatasetDialog only"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\registry_tab.py"
)

CODE = """

class DatasetDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\\u7f16\\u8f91\\u6570\\u636e\\u96c6" if self._editing
            else "\\u6ce8\\u518c\\u6570\\u636e\\u96c6")
        self.setMinimumWidth(480)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u6570\\u636e\\u96c6\\u4fe1\\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit()
        self._name.setPlaceholderText("\\u6570\\u636e\\u96c6\\u540d\\u79f0")
        form.addRow("\\u540d\\u79f0 *", self._name)
        self._desc = QTextEdit(); self._desc.setFixedHeight(52)
        form.addRow("\\u63cf\\u8ff0", self._desc)
        self._source = QLineEdit()
        self._source.setPlaceholderText("tushare / wind / akshare")
        form.addRow("\\u6570\\u636e\\u6e90", self._source)
        self._start = QLineEdit(); self._start.setPlaceholderText("2015-01-01")
        form.addRow("\\u5f00\\u59cb\\u65e5\\u671f", self._start)
        self._end = QLineEdit(); self._end.setPlaceholderText("2024-12-31")
        form.addRow("\\u7ed3\\u675f\\u65e5\\u671f", self._end)
        self._row_count = QSpinBox()
        self._row_count.setRange(0, 999_999_999)
        form.addRow("\\u884c\\u6570", self._row_count)
        self._tags = QLineEdit(); self._tags.setPlaceholderText("\\u9017\\u53f7\\u5206\\u9694")
        form.addRow("\\u6807\\u7b7e", self._tags)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u786e\\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._name.setText(r.name); self._desc.setPlainText(r.description)
        self._source.setText(r.source)
        self._start.setText(r.start_date or ""); self._end.setText(r.end_date or "")
        self._row_count.setValue(r.row_count or 0)
        self._tags.setText(", ".join(r.tags))

    def _on_ok(self):
        if not self._name.text().strip(): self._name.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]
    def get_name(self)        -> str:       return self._name.text().strip()
    def get_description(self) -> str:       return self._desc.toPlainText().strip()
    def get_source(self)      -> str:       return self._source.text().strip()
    def get_start_date(self)  -> str:       return self._start.text().strip()
    def get_end_date(self)    -> str:       return self._end.text().strip()
    def get_row_count(self)   -> int:       return self._row_count.value()
    def get_tags(self)        -> List[str]: return self._split(self._tags.text())
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("DatasetDialog OK, size:", P.stat().st_size)
