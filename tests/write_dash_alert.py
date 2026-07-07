"""write_dash_alert.py — AlertPanel"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\dashboard_tab.py"
)

CODE = '''

# =================================================================
# AlertRow  — single alert item
# =================================================================

class AlertRow(QFrame):
    def __init__(self, level: str, icon: str, title: str,
                 detail: str, color: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "AlertRow{background:#fff8f8;border-left:4px solid " + color + ";"
            "border-radius:4px;margin:2px 0;}"
        )
        lay = QHBoxLayout(self); lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(8)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            "font-size:18px;background:transparent;border:none;")
        icon_lbl.setFixedWidth(26)
        lay.addWidget(icon_lbl)

        text_lay = QVBoxLayout(); text_lay.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "font-size:13px;font-weight:bold;color:#1a1f36;"
            "background:transparent;border:none;")
        text_lay.addWidget(title_lbl)
        detail_lbl = QLabel(detail)
        detail_lbl.setStyleSheet(
            "font-size:11px;color:#6c757d;"
            "background:transparent;border:none;")
        text_lay.addWidget(detail_lbl)
        lay.addLayout(text_lay, 1)

        badge = QLabel(level)
        badge.setFixedHeight(20)
        badge.setStyleSheet(
            "padding:1px 8px;border-radius:9px;"
            "background:" + color + "22;color:" + color + ";"
            "font-size:11px;border:1px solid " + color + "44;"
            "background:transparent;"
        )
        lay.addWidget(badge)


# =================================================================
# AlertPanel  — collects alerts from engine stats
# =================================================================

class AlertPanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        hdr = QHBoxLayout()
        lbl = QLabel("\\u26a0\\ufe0f  \\u544a\\u8b66 & \\u5f85\\u529e")
        lbl.setStyleSheet("font-size:14px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(lbl); hdr.addStretch()
        self._count_lbl = QLabel("0")
        self._count_lbl.setStyleSheet(
            "padding:1px 8px;border-radius:9px;"
            "background:#dc354522;color:#dc3545;"
            "font-size:12px;border:1px solid #dc354544;")
        hdr.addWidget(self._count_lbl)
        root.addLayout(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#dee2e6;"); root.addWidget(sep)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._inner = QWidget()
        self._inner.setStyleSheet("background:#f8f9fa;")
        self._inner_lay = QVBoxLayout(self._inner)
        self._inner_lay.setContentsMargins(4, 4, 4, 4)
        self._inner_lay.setSpacing(4)
        self._inner_lay.addStretch()
        self._scroll.setWidget(self._inner)
        root.addWidget(self._scroll, 1)

    def refresh(self):
        # remove everything except trailing stretch
        while self._inner_lay.count() > 0:
            item = self._inner_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        alerts: List[Dict] = []
        try:
            s = self._engine.get_platform_stats()
        except Exception:
            self._inner_lay.addStretch(); return

        pl = s.get("pipeline", {})
        if pl.get("failed", 0):
            alerts.append({
                "level": "ERROR", "icon": "\\u274c",
                "title": "Pipeline \\u5931\\u8d25",
                "detail": str(pl["failed"]) + " \\u4e2a Pipeline \\u5904\\u4e8e\\u5931\\u8d25\\u72b6\\u6001",
                "color": C_RED,
            })
        if pl.get("running", 0):
            alerts.append({
                "level": "INFO", "icon": "\\u26a1",
                "title": "Pipeline \\u8fd0\\u884c\\u4e2d",
                "detail": str(pl["running"]) + " \\u4e2a Pipeline \\u6b63\\u5728\\u6267\\u884c",
                "color": C_ORANGE,
            })

        kb = s.get("knowledge", {})
        if kb.get("unresolved_cases", 0):
            alerts.append({
                "level": "WARN", "icon": "\\u26a0",
                "title": "\\u672a\\u89e3\\u51b3\\u5931\\u8d25\\u6848\\u4f8b",
                "detail": str(kb["unresolved_cases"]) + " \\u4e2a\\u6848\\u4f8b\\u5f85\\u5904\\u7406",
                "color": C_GOLD,
            })

        rpt = s.get("report", {})
        drafts = rpt.get("reports", 0) - rpt.get("published", 0)
        if drafts > 0:
            alerts.append({
                "level": "INFO", "icon": "\\u270f",
                "title": "\\u8349\\u7a3f\\u62a5\\u544a",
                "detail": str(drafts) + " \\u4e2a\\u62a5\\u544a\\u5c1a\\u672a\\u53d1\\u5e03",
                "color": C_BLUE,
            })

        exp = s.get("experiment", {})
        if exp.get("running", 0):
            alerts.append({
                "level": "INFO", "icon": "\\U0001f9ea",
                "title": "\\u5b9e\\u9a8c\\u8fd0\\u884c\\u4e2d",
                "detail": str(exp["running"]) + " \\u6b21\\u8fd0\\u884c\\u6b63\\u5728\\u8fdb\\u884c",
                "color": C_BLUE,
            })

        if not alerts:
            ok = QLabel("\\u2705  \\u6240\\u6709\\u7cfb\\u7edf\\u8fd0\\u884c\\u6b63\\u5e38")
            ok.setStyleSheet(
                "color:#198754;font-size:13px;"
                "background:transparent;border:none;")
            ok.setAlignment(Qt.AlignCenter)
            self._inner_lay.addWidget(ok)
        else:
            for a in alerts:
                row = AlertRow(a["level"], a["icon"],
                               a["title"], a["detail"], a["color"])
                self._inner_lay.addWidget(row)

        self._inner_lay.addStretch()
        self._count_lbl.setText(str(len(alerts)))
        if alerts:
            self._count_lbl.setStyleSheet(
                "padding:1px 8px;border-radius:9px;"
                "background:#dc354522;color:#dc3545;"
                "font-size:12px;border:1px solid #dc354544;")
        else:
            self._count_lbl.setStyleSheet(
                "padding:1px 8px;border-radius:9px;"
                "background:#19875422;color:#198754;"
                "font-size:12px;border:1px solid #19875444;")
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("AlertPanel OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
