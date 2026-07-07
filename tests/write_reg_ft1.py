"""write_reg_ft1.py — FeatureDialog + IcMetricDialog"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\registry_tab.py"
)

CODE = """

class FeatureDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\\u7f16\\u8f91\\u56e0\\u5b50" if self._editing else "\\u6ce8\\u518c\\u56e0\\u5b50")
        self.setMinimumWidth(480)
        self._init_ui()
        if self._editing: self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u56e0\\u5b50\\u4fe1\\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit()
        form.addRow("\\u540d\\u79f0 *", self._name)
        self._desc = QTextEdit(); self._desc.setFixedHeight(52)
        form.addRow("\\u63cf\\u8ff0", self._desc)
        self._category = QLineEdit()
        self._category.setPlaceholderText("momentum / reversal / quality")
        form.addRow("\\u5206\\u7c7b", self._category)
        self._author = QLineEdit()
        form.addRow("\\u4f5c\\u8005", self._author)
        self._formula = QTextEdit(); self._formula.setFixedHeight(52)
        form.addRow("\\u516c\\u5f0f", self._formula)
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
        self._category.setText(r.category or ""); self._author.setText(r.author or "")
        self._formula.setPlainText(r.formula or "")
        self._tags.setText(", ".join(r.tags))

    def _on_ok(self):
        if not self._name.text().strip(): self._name.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]
    def get_name(self)        -> str:       return self._name.text().strip()
    def get_description(self) -> str:       return self._desc.toPlainText().strip()
    def get_category(self)    -> str:       return self._category.text().strip()
    def get_author(self)      -> str:       return self._author.text().strip()
    def get_formula(self)     -> str:       return self._formula.toPlainText().strip()
    def get_tags(self)        -> List[str]: return self._split(self._tags.text())


class IcMetricDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\\u66f4\\u65b0 IC \\u6307\\u6807")
        self.setMinimumWidth(360)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("IC \\u6307\\u6807")
        form = QFormLayout(grp)

        def _spin(lo=-1.0, hi=1.0, dec=4, step=0.001):
            s = QDoubleSpinBox()
            s.setRange(lo, hi); s.setDecimals(dec); s.setSingleStep(step)
            return s

        self._ic   = _spin(); form.addRow("IC", self._ic)
        self._rank = _spin(); form.addRow("Rank IC", self._rank)
        self._ir   = _spin(-10, 10, 3, 0.01); form.addRow("IR", self._ir)
        self._icir = _spin(-10, 10, 3, 0.01); form.addRow("ICIR", self._icir)
        self._cov  = _spin(0.0, 1.0, 3, 0.01); form.addRow("Coverage", self._cov)
        self._period = QLineEdit(); self._period.setPlaceholderText("2024 / 2024Q1")
        form.addRow("\\u671f\\u95f4", self._period)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u786e\\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def get_ic(self)      -> float: return self._ic.value()
    def get_rank_ic(self) -> float: return self._rank.value()
    def get_ir(self)      -> float: return self._ir.value()
    def get_icir(self)    -> float: return self._icir.value()
    def get_coverage(self)-> float: return self._cov.value()
    def get_period(self)  -> str:   return self._period.text().strip()
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("FeatureDialog+IcDialog OK, size:", P.stat().st_size)
