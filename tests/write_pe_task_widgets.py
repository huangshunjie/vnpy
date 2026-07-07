"""write_pe_task_widgets.py — append TaskTab components"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\task.py"
)

CHUNK1 = '''

class CreateTaskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\\u521b\\u5efa\\u4efb\\u52a1")
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u4efb\\u52a1\\u4fe1\\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit(); self._name.setPlaceholderText("\\u4efb\\u52a1\\u540d\\u79f0")
        form.addRow("\\u540d\\u79f0 *", self._name)
        self._type = QComboBox()
        for t in TaskType: self._type.addItem(t.value, t)
        form.addRow("\\u7c7b\\u578b", self._type)
        self._priority = QComboBox()
        for p in TaskPriority: self._priority.addItem(p.name, p)
        self._priority.setCurrentIndex(1)
        form.addRow("\\u4f18\\u5148\\u7ea7", self._priority)
        self._timeout = QSpinBox(); self._timeout.setRange(10, 86400)
        self._timeout.setValue(3600); self._timeout.setSuffix(" \\u79d2")
        form.addRow("\\u8d85\\u65f6", self._timeout)
        self._retries = QSpinBox(); self._retries.setRange(0, 10)
        self._retries.setValue(3)
        form.addRow("\\u6700\\u5927\\u91cd\\u8bd5", self._retries)
        self._created_by = QLineEdit()
        form.addRow("\\u521b\\u5efa\\u4eba", self._created_by)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u521b\\u5efa")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        if not self._name.text().strip(): self._name.setFocus(); return
        self.accept()

    def get_name(self)       -> str:          return self._name.text().strip()
    def get_type(self)       -> TaskType:     return self._type.currentData()
    def get_priority(self)   -> TaskPriority: return self._priority.currentData()
    def get_timeout(self)    -> int:          return self._timeout.value()
    def get_retries(self)    -> int:          return self._retries.value()
    def get_created_by(self) -> str:          return self._created_by.text().strip()


class AddJobDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\\u6dfb\\u52a0\\u8c03\\u5ea6\\u4efb\\u52a1")
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u8c03\\u5ea6\\u914d\\u7f6e")
        form = QFormLayout(grp)
        self._name = QLineEdit(); self._name.setPlaceholderText("\\u4efb\\u52a1\\u540d\\u79f0")
        form.addRow("\\u540d\\u79f0 *", self._name)
        self._cron = QLineEdit(); self._cron.setPlaceholderText("*/30 * * * *")
        form.addRow("Cron \\u8868\\u8fbe\\u5f0f *", self._cron)
        self._type = QComboBox()
        for t in TaskType: self._type.addItem(t.value, t)
        form.addRow("\\u7c7b\\u578b", self._type)
        self._priority = QComboBox()
        for p in TaskPriority: self._priority.addItem(p.name, p)
        self._priority.setCurrentIndex(1)
        form.addRow("\\u4f18\\u5148\\u7ea7", self._priority)
        self._created_by = QLineEdit()
        form.addRow("\\u521b\\u5efa\\u4eba", self._created_by)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u6dfb\\u52a0")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        for w in (self._name, self._cron):
            if not w.text().strip(): w.setFocus(); return
        self.accept()

    def get_name(self)       -> str:          return self._name.text().strip()
    def get_cron(self)       -> str:          return self._cron.text().strip()
    def get_type(self)       -> TaskType:     return self._type.currentData()
    def get_priority(self)   -> TaskPriority: return self._priority.currentData()
    def get_created_by(self) -> str:          return self._created_by.text().strip()
'''

ast.parse(CHUNK1)
with open(P, "a", encoding="utf-8") as f:
    f.write(CHUNK1)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("CHUNK1 OK, lines:", len(full.splitlines()))
