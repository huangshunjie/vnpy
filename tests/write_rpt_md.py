"""write_rpt_md.py — MarkdownEditor"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\report_tab.py"
)

CODE = """

class MarkdownEditor(QWidget):
    content_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        tb = QHBoxLayout(); tb.setSpacing(4); tb.setContentsMargins(4,4,4,4)
        for label, ins in [("H1","# "),("H2","## "),("H3","### "),
                            ("**B**","**"),("*I*","*"),("`C`","`"),
                            ("---","\\n---\\n"),("List","- ")]:
            btn = QPushButton(label); btn.setFixedSize(36,22)
            btn.setStyleSheet("font-size:11px;")
            btn.clicked.connect(lambda _, i=ins: self._insert(i))
            tb.addWidget(btn)
        tb.addStretch()
        root.addLayout(tb)
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#dee2e6;"); root.addWidget(sep)
        sp = QSplitter(Qt.Horizontal)
        self._editor = QTextEdit()
        self._editor.setFont(QFont("Consolas", 10))
        self._editor.setStyleSheet(
            "QTextEdit{background:#1e1e2e;color:#cdd6f4;border:none;padding:8px;}")
        self._editor.textChanged.connect(self._on_change)
        sp.addWidget(self._editor)
        self._preview = QTextBrowser()
        self._preview.setStyleSheet("QTextBrowser{background:#fff;border:none;padding:12px;}")
        self._preview.setOpenExternalLinks(True)
        sp.addWidget(self._preview)
        sp.setSizes([500, 500])
        root.addWidget(sp, 1)

    def _insert(self, text: str):
        cur = self._editor.textCursor(); cur.insertText(text)
        self._editor.setTextCursor(cur); self._editor.setFocus()

    def _on_change(self):
        md = self._editor.toPlainText()
        self._preview.setHtml(_md_to_html(md))
        self.content_changed.emit(md)

    def set_content(self, md: str):
        self._editor.blockSignals(True)
        self._editor.setPlainText(md)
        self._editor.blockSignals(False)
        self._preview.setHtml(_md_to_html(md))

    def get_content(self) -> str:
        return self._editor.toPlainText()

    def clear(self):
        self._editor.clear(); self._preview.clear()
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("MarkdownEditor OK, size:", P.stat().st_size)
