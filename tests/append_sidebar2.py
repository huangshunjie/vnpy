"""append_sidebar_part2.py"""
import pathlib, ast

P = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\trader\ui\sidebar.py")

PART2 = '''

class GroupBox(QtWidgets.QWidget):
    def __init__(self, label: str, emoji: str, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 16); lay.setSpacing(8)
        hdr = QtWidgets.QLabel(f"  {emoji}  {label}")
        hdr.setFixedHeight(30)
        hdr.setStyleSheet(
            f"color:{color};font-size:12px;font-weight:bold;"
            f"background:{_rgba(color,18)};"
            f"border-left:3px solid {color};"
            f"border-radius:2px;padding-left:6px;")
        lay.addWidget(hdr)
        self._flow_w = QtWidgets.QWidget()
        self._flow   = FlowLayout(self._flow_w, hs=10, vs=8)
        lay.addWidget(self._flow_w)

    def add_app(self, display_name: str, func: Callable):
        self._flow.addWidget(AppCard(display_name, func, self._color))


class VeighNaAppsWindow(QtWidgets.QDialog):
    def __init__(self, app_funcs: Dict[str, tuple], parent=None):
        super().__init__(parent)
        self.setWindowTitle("VeighNa Apps  —  量化平台应用中心")
        self.setMinimumSize(880, 560)
        self.resize(1040, 660)
        self.setWindowFlags(
            self.windowFlags() |
            QtCore.Qt.WindowType.WindowMaximizeButtonHint)
        self.setStyleSheet("background:#0d1117;")
        self._build(app_funcs)

    def _build(self, app_funcs):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # 标题栏
        hdr = QtWidgets.QWidget()
        hdr.setFixedHeight(54)
        hdr.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #0d1117,stop:1 #1a1f36);")
        hl = QtWidgets.QHBoxLayout(hdr)
        hl.setContentsMargins(24, 0, 24, 0)
        for text, style in [
            ("⚡", "font-size:20px;color:#58a6ff;background:transparent;"),
            ("VeighNa Apps",
             "color:#fff;font-size:17px;font-weight:bold;"
             "background:transparent;margin-left:6px;"),
            ("量化平台应用中心",
             "color:rgba(255,255,255,0.4);font-size:11px;"
             "background:transparent;margin-left:10px;"),
        ]:
            lbl = QtWidgets.QLabel(text); lbl.setStyleSheet(style)
            hl.addWidget(lbl)
        hl.addStretch()
        total = sum(len(ns) for _,_,_,ns in APP_GROUPS)
        cnt = QtWidgets.QLabel(f"{total} 个应用")
        cnt.setStyleSheet("color:#58a6ff;font-size:11px;background:transparent;")
        hl.addWidget(cnt)
        root.addWidget(hdr)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet("color:#21262d;")
        root.addWidget(sep)

        # 滚动区
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea{background:#0d1117;}"
            "QScrollBar:vertical{background:#161b22;width:6px;margin:0;}"
            "QScrollBar::handle:vertical{background:#30363d;"
            "border-radius:3px;min-height:24px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}")

        body = QtWidgets.QWidget()
        body.setStyleSheet("background:#0d1117;")
        bl = QtWidgets.QVBoxLayout(body)
        bl.setContentsMargins(24, 18, 24, 24); bl.setSpacing(4)

        for label, emoji, color, app_names in APP_GROUPS:
            items = [(n,)+app_funcs[n] for n in app_names if n in app_funcs]
            if not items: continue
            grp = GroupBox(label, emoji, color)
            for _, dname, func in items:
                grp.add_app(dname, func)
            bl.addWidget(grp)

        ungrouped = [(n,)+v for n,v in app_funcs.items() if n not in _GROUPED]
        if ungrouped:
            grp = GroupBox("其他", "📎", "#8c8c8c")
            for _, dname, func in ungrouped:
                grp.add_app(dname, func)
            bl.addWidget(grp)

        bl.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

    def closeEvent(self, event):
        self.hide(); event.ignore()
'''

with open(P, "a", encoding="utf-8") as f:
    f.write(PART2)

src = P.read_text(encoding="utf-8")
ast.parse(src)
print("Part2 OK, lines:", len(src.splitlines()))
