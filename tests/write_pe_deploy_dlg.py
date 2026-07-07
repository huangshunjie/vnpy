"""write_pe_deploy_dlg.py — append dialogs to deployment.py"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\deployment.py"
)

CODE = '''

class CreateDeployDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\\u521b\\u5efa\\u90e8\\u7f72")
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u90e8\\u7f72\\u4fe1\\u606f")
        form = QFormLayout(grp)
        self._sid  = QLineEdit(); self._sid.setPlaceholderText("STR-001")
        form.addRow("\\u7b56\\u7565 ID *", self._sid)
        self._name = QLineEdit(); self._name.setPlaceholderText("\\u7b56\\u7565\\u540d\\u79f0")
        form.addRow("\\u7b56\\u7565\\u540d\\u79f0 *", self._name)
        self._creator = QLineEdit()
        form.addRow("\\u521b\\u5efa\\u4eba", self._creator)
        self._tags = QLineEdit(); self._tags.setPlaceholderText("tag1,tag2")
        form.addRow("\\u6807\\u7b7e", self._tags)
        root.addWidget(grp)
        ng = QGroupBox("\\u5907\\u6ce8")
        nl = QVBoxLayout(ng)
        self._note = QTextEdit(); self._note.setFixedHeight(60)
        nl.addWidget(self._note)
        root.addWidget(ng)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u521b\\u5efa")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        if not self._sid.text().strip():  self._sid.setFocus();  return
        if not self._name.text().strip(): self._name.setFocus(); return
        self.accept()

    def get_strategy_id(self)   -> str: return self._sid.text().strip()
    def get_strategy_name(self) -> str: return self._name.text().strip()
    def get_created_by(self)    -> str: return self._creator.text().strip()
    def get_tags(self):
        raw = self._tags.text().strip()
        return [t.strip() for t in raw.split(",") if t.strip()] if raw else []
    def get_note(self) -> str: return self._note.toPlainText().strip()


class AdvanceStageDialog(QDialog):
    def __init__(self, current: DeployStage, allowed, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\\u63a8\\u8fdb\\u9636\\u6bb5")
        self.setMinimumWidth(380)
        root = QVBoxLayout(self)
        form = QFormLayout()
        lbl = QLabel(current.value.upper())
        lbl.setStyleSheet(
            f"color:{STAGE_COLOR.get(current,'#1890ff')};"
            "font-weight:bold;")
        form.addRow("\\u5f53\\u524d\\u9636\\u6bb5:", lbl)
        self._combo = QComboBox()
        for s in allowed:
            self._combo.addItem(
                STAGE_ICON.get(s,"") + "  " + s.value.upper(), s)
        form.addRow("\\u76ee\\u6807\\u9636\\u6bb5 *", self._combo)
        self._operator = QLineEdit()
        form.addRow("\\u64cd\\u4f5c\\u4eba", self._operator)
        root.addLayout(form)
        ng = QGroupBox("\\u5907\\u6ce8")
        nl = QVBoxLayout(ng)
        self._note = QTextEdit(); self._note.setFixedHeight(60)
        nl.addWidget(self._note)
        root.addWidget(ng)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u786e\\u8ba4\\u63a8\\u8fdb")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def get_stage(self)    -> DeployStage: return self._combo.currentData()
    def get_operator(self) -> str:         return self._operator.text().strip()
    def get_note(self)     -> str:         return self._note.toPlainText().strip()


class ApproveDialog(QDialog):
    def __init__(self, approve: bool = True, parent=None):
        super().__init__(parent)
        self._approve = approve
        self.setWindowTitle(
            "\\u5ba1\\u6279\\u901a\\u8fc7" if approve else "\\u62d2\\u7edd\\u5ba1\\u6279")
        self.setMinimumWidth(380)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._approver = QLineEdit()
        form.addRow("\\u5ba1\\u6279\\u4eba *", self._approver)
        root.addLayout(form)
        ng = QGroupBox("\\u5907\\u6ce8" + ("" if approve else " (\\u62d2\\u7edd\\u539f\\u56e0)"))
        nl = QVBoxLayout(ng)
        self._note = QTextEdit(); self._note.setFixedHeight(60)
        nl.addWidget(self._note)
        root.addWidget(ng)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_lbl = "\\u786e\\u8ba4\\u901a\\u8fc7" if approve else "\\u786e\\u8ba4\\u62d2\\u7edd"
        btns.button(QDialogButtonBox.Ok).setText(ok_lbl)
        if not approve:
            btns.button(QDialogButtonBox.Ok).setStyleSheet(
                "background:#ff4d4f;color:#fff;border-radius:4px;")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        if not self._approver.text().strip():
            self._approver.setFocus(); return
        self.accept()

    def get_approver(self) -> str: return self._approver.text().strip()
    def get_note(self)     -> str: return self._note.toPlainText().strip()
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("dialogs OK, lines:", len(full.splitlines()))
