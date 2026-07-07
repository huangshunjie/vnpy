"""write_ws_p2.py — WorkspaceDialog + ProjectDialog"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\workspace_tab.py"
)

PART2 = '''

# =================================================================
# WorkspaceDialog
# =================================================================

class WorkspaceDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        title = "\u7f16\u8f91\u5de5\u4f5c\u533a" if self._editing else "\u65b0\u5efa\u5de5\u4f5c\u533a"
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u5de5\u4f5c\u533a\u4fe1\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit()
        self._name.setPlaceholderText("\u5de5\u4f5c\u533a\u540d\u79f0\uff08\u5fc5\u586b\uff09")
        form.addRow("\u540d\u79f0 *", self._name)
        self._desc = QTextEdit()
        self._desc.setFixedHeight(60)
        form.addRow("\u63cf\u8ff0", self._desc)
        self._root = QLineEdit()
        self._root.setPlaceholderText("\u672c\u5730\u6839\u76ee\u5f55\u8def\u5f84\uff08\u53ef\u9009\uff09")
        form.addRow("\u6839\u76ee\u5f55", self._root)
        self._members = QLineEdit()
        self._members.setPlaceholderText("\u6210\u5458\uff0c\u9017\u53f7\u5206\u9694")
        form.addRow("\u6210\u5458", self._members)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\u6807\u7b7e\uff0c\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._name.setText(r.name)
        self._desc.setPlainText(r.description)
        self._root.setText(r.root_path)
        self._members.setText(", ".join(r.members))
        self._tags.setText(", ".join(r.tags))

    def _on_ok(self):
        if not self._name.text().strip():
            self._name.setFocus()
            return
        self.accept()

    def _split(self, t):
        return [x.strip() for x in t.split(",") if x.strip()]

    def get_name(self)        -> str:       return self._name.text().strip()
    def get_description(self) -> str:       return self._desc.toPlainText().strip()
    def get_root_path(self)   -> str:       return self._root.text().strip()
    def get_members(self)     -> List[str]: return self._split(self._members.text())
    def get_tags(self)        -> List[str]: return self._split(self._tags.text())


# =================================================================
# ProjectDialog
# =================================================================

class ProjectDialog(QDialog):
    def __init__(self, parent=None, record=None, workspace_id=""):
        super().__init__(parent)
        self._record       = record
        self._workspace_id = workspace_id
        self._editing      = record is not None
        self._color        = record.color if record else "#4a6cf7"
        title = "\u7f16\u8f91\u9879\u76ee" if self._editing else "\u65b0\u5efa\u9879\u76ee"
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u9879\u76ee\u4fe1\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit()
        self._name.setPlaceholderText("\u9879\u76ee\u540d\u79f0\uff08\u5fc5\u586b\uff09")
        form.addRow("\u540d\u79f0 *", self._name)
        self._desc = QTextEdit()
        self._desc.setFixedHeight(60)
        form.addRow("\u63cf\u8ff0", self._desc)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\u6807\u7b7e\uff0c\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)
        # color picker
        color_w = QWidget()
        color_l = QHBoxLayout(color_w)
        color_l.setContentsMargins(0, 0, 0, 0)
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(32, 22)
        self._color_btn.setStyleSheet(
            "background:" + self._color + "; border-radius:4px; border:1px solid #ccc;")
        self._color_btn.clicked.connect(self._pick_color)
        self._color_lbl = QLabel(self._color)
        color_l.addWidget(self._color_btn)
        color_l.addWidget(self._color_lbl)
        color_l.addStretch()
        form.addRow("\u989c\u8272", color_w)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._name.setText(r.name)
        self._desc.setPlainText(r.description)
        self._tags.setText(", ".join(r.tags))
        self._set_color(r.color)

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self,
                                  "\u9009\u62e9\u9879\u76ee\u989c\u8272")
        if c.isValid():
            self._set_color(c.name())

    def _set_color(self, hex_color):
        self._color = hex_color
        self._color_btn.setStyleSheet(
            "background:" + hex_color + "; border-radius:4px; border:1px solid #ccc;")
        self._color_lbl.setText(hex_color)

    def _on_ok(self):
        if not self._name.text().strip():
            self._name.setFocus()
            return
        self.accept()

    def _split(self, t):
        return [x.strip() for x in t.split(",") if x.strip()]

    def get_name(self)         -> str:       return self._name.text().strip()
    def get_description(self)  -> str:       return self._desc.toPlainText().strip()
    def get_tags(self)         -> List[str]: return self._split(self._tags.text())
    def get_color(self)        -> str:       return self._color
    def get_workspace_id(self) -> str:       return self._workspace_id
'''

ast.parse(PART2)
with open(P, "a", encoding="utf-8") as f:
    f.write(PART2)
print("PART2 written OK, total size:", P.stat().st_size)
