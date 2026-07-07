"""write_pe_dash_widgets.py — append widgets to dashboard.py"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\dashboard.py"
)

CHUNK1 = '''

class HealthRingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._score = 100.0
        self._level = HealthLevel.GREEN
        self.setMinimumSize(160, 160)
        self.setMaximumSize(200, 200)

    def update_score(self, score: float, level: HealthLevel) -> None:
        self._score = score; self._level = level; self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin = 16
        rect = QRectF(margin, margin, w - 2*margin, h - 2*margin)
        pen_bg = QPen(QColor("#e8e8e8"), 14, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen_bg); painter.drawArc(rect, 0, 360 * 16)
        color = LEVEL_COLOR.get(self._level, "#52c41a")
        span  = int(self._score / 100.0 * 360 * 16)
        pen_fg = QPen(QColor(color), 14, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen_fg); painter.drawArc(rect, 90 * 16, -span)
        painter.setPen(QColor(color))
        font = QFont(); font.setPointSize(22); font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, f"{self._score:.0f}")
        painter.end()


class LayerScoreCard(QFrame):
    def __init__(self, layer: MetricLayer, parent=None):
        super().__init__(parent)
        self._layer = layer
        color = LAYER_COLOR[layer]
        self.setStyleSheet(
            f"QFrame{{background:#fff;border-radius:8px;"
            f"border-left:4px solid {color};"
            f"border-top:1px solid #f0f0f0;"
            f"border-right:1px solid #f0f0f0;"
            f"border-bottom:1px solid #f0f0f0;}}")
        self.setFixedHeight(68)
        lay = QHBoxLayout(self); lay.setContentsMargins(12, 6, 12, 6)
        icon = QLabel(LAYER_ICON[layer])
        icon.setStyleSheet("font-size:22px;background:transparent;border:none;")
        lay.addWidget(icon)
        texts = QVBoxLayout(); texts.setSpacing(2)
        self._score_lbl = QLabel("100")
        self._score_lbl.setStyleSheet(
            f"font-size:20px;font-weight:bold;color:{color};"
            "background:transparent;border:none;")
        self._name_lbl = QLabel(layer.value.upper())
        self._name_lbl.setStyleSheet(
            "font-size:10px;color:#8c8c8c;background:transparent;border:none;")
        texts.addWidget(self._score_lbl); texts.addWidget(self._name_lbl)
        lay.addLayout(texts); lay.addStretch()
        self._badge = QLabel("GREEN")
        self._badge.setStyleSheet(
            "font-size:10px;padding:2px 6px;border-radius:8px;"
            "background:#f6ffed;color:#52c41a;border:none;")
        lay.addWidget(self._badge)

    def update_score(self, score: float, level: HealthLevel) -> None:
        color = LEVEL_COLOR.get(level, "#52c41a")
        lc    = LAYER_COLOR[self._layer]
        self._score_lbl.setText(f"{score:.0f}")
        self._score_lbl.setStyleSheet(
            f"font-size:20px;font-weight:bold;color:{lc};"
            "background:transparent;border:none;")
        self._badge.setText(level.value.upper())
        bg_map = {
            HealthLevel.GREEN:  "#f6ffed",
            HealthLevel.YELLOW: "#fffbe6",
            HealthLevel.RED:    "#fff2f0",
        }
        self._badge.setStyleSheet(
            f"font-size:10px;padding:2px 6px;border-radius:8px;"
            f"background:{bg_map.get(level,'#f6ffed')};color:{color};border:none;")


class StatCard(QFrame):
    def __init__(self, label: str, icon: str, color: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame{background:#fff;border-radius:8px;border:1px solid #f0f0f0;}")
        self.setFixedHeight(80)
        lay = QVBoxLayout(self); lay.setContentsMargins(14, 8, 14, 8); lay.setSpacing(2)
        top = QHBoxLayout()
        ilbl = QLabel(icon)
        ilbl.setStyleSheet(
            f"font-size:18px;color:{color};background:transparent;border:none;")
        top.addWidget(ilbl); top.addStretch()
        lay.addLayout(top)
        self._val = QLabel("\\u2014")
        self._val.setStyleSheet(
            f"font-size:22px;font-weight:bold;color:{color};"
            "background:transparent;border:none;")
        lay.addWidget(self._val)
        lbl = QLabel(label)
        lbl.setStyleSheet(
            "font-size:11px;color:#8c8c8c;background:transparent;border:none;")
        lay.addWidget(lbl)

    def set_value(self, v) -> None:
        self._val.setText(str(v))


class AlertRow(QFrame):
    def __init__(self, alert: AlertRecord, parent=None):
        super().__init__(parent)
        color = SEV_COLOR.get(alert.severity, "#faad14")
        self.setStyleSheet(
            f"QFrame{{background:#fff;border-radius:6px;"
            f"border-left:3px solid {color};"
            f"border-top:1px solid #f5f5f5;"
            f"border-right:1px solid #f5f5f5;"
            f"border-bottom:1px solid #f5f5f5;margin-bottom:3px;}}")
        lay = QHBoxLayout(self); lay.setContentsMargins(10, 6, 10, 6)
        sev = QLabel(alert.severity.value.upper())
        sev.setStyleSheet(
            f"font-size:10px;font-weight:bold;color:{color};"
            f"background:{color}1a;padding:1px 6px;border-radius:6px;border:none;")
        sev.setFixedWidth(64); lay.addWidget(sev)
        msg = QLabel(alert.message)
        msg.setStyleSheet(
            "font-size:12px;color:#262626;background:transparent;border:none;")
        msg.setWordWrap(True); lay.addWidget(msg, 1)
        ts = QLabel(alert.created_at.strftime("%H:%M:%S"))
        ts.setStyleSheet(
            "font-size:10px;color:#bfbfbf;background:transparent;border:none;")
        lay.addWidget(ts)
'''

ast.parse(CHUNK1)
with open(P, "a", encoding="utf-8") as f:
    f.write(CHUNK1)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("CHUNK1 OK, lines:", len(full.splitlines()))
