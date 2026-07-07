"""write_dash_grid.py — StatGrid"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\dashboard_tab.py"
)

CODE = '''

# =================================================================
# StatGrid  — 3×3 KPI grid
# =================================================================

class StatGrid(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._cards: List[KpiCard] = []
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        hdr = QHBoxLayout()
        lbl = QLabel("\\U0001f4ca  \\u5e73\\u53f0\\u6982\\u89c8")
        lbl.setStyleSheet("font-size:14px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(lbl); hdr.addStretch()
        self._ts = QLabel("")
        self._ts.setStyleSheet("font-size:11px;color:#adb5bd;")
        hdr.addWidget(self._ts)
        root.addLayout(hdr)

        grid = QGridLayout(); grid.setSpacing(10)
        for i, d in enumerate(CARD_DEFS):
            card = KpiCard(d["icon"], d["label"], "0", d["color"])
            grid.addWidget(card, i // 3, i % 3)
            self._cards.append(card)
        root.addLayout(grid)
        self.refresh()

    def refresh(self):
        try:
            s = self._engine.get_platform_stats()
        except Exception:
            return
        for card, d in zip(self._cards, CARD_DEFS):
            sec  = s.get(d["sec"], {})
            val  = sec.get(d["key"], 0)
            card.update_value(str(val))
        self._ts.setText(
            "\\u66f4\\u65b0: " + datetime.now().strftime("%H:%M:%S"))
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("StatGrid OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
