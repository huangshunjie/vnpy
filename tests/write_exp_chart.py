"""write_exp_chart.py — MetricChart"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\experiment_tab.py"
)

CODE = """

class MetricChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._series: Dict[str, List[MetricPoint]] = {}
        self._title  = ""
        self.setMinimumHeight(160)
        self.setStyleSheet(
            "background:#fafafa;border:1px solid #dee2e6;border-radius:4px;")
        self._hover_pos = None
        self.setMouseTracking(True)

    def set_series(self, series: Dict[str, List[MetricPoint]], title: str = ""):
        self._series = series
        self._title  = title
        self.update()

    def clear(self):
        self._series = {}; self._title = ""; self.update()

    def mouseMoveEvent(self, event):
        self._hover_pos = event.position().toPoint(); self.update()

    def leaveEvent(self, _ev):
        self._hover_pos = None; self.update()

    def paintEvent(self, _ev):
        if not self._series:
            p = QPainter(self)
            p.setPen(QColor("#adb5bd"))
            p.setFont(QFont("Arial", 11))
            p.drawText(self.rect(), Qt.AlignCenter, "\\u6682\\u65e0\\u6307\\u6807\\u6570\\u636e")
            p.end(); return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._draw(p); p.end()

    def _draw(self, p: QPainter):
        W, H = self.width(), self.height()
        PL, PR, PT, PB = 52, 16, 28, 36

        all_vals = [pt.value for pts in self._series.values() for pt in pts]
        all_steps = [pt.step for pts in self._series.values() for pt in pts]
        if not all_vals:
            return

        y_min, y_max = min(all_vals), max(all_vals)
        x_min, x_max = min(all_steps), max(all_steps)
        yr = y_max - y_min or 1e-9
        xr = x_max - x_min or 1

        def tx(s):  return PL + (s - x_min) / xr * (W - PL - PR)
        def ty(v):  return PT + (1 - (v - y_min) / yr) * (H - PT - PB)

        # grid
        p.setPen(QPen(QColor("#dee2e6"), 1, Qt.DashLine))
        for i in range(5):
            y = PT + i * (H - PT - PB) / 4
            p.drawLine(int(PL), int(y), int(W - PR), int(y))

        # axes
        p.setPen(QPen(QColor("#adb5bd"), 1))
        p.drawLine(int(PL), PT, int(PL), H - PB)
        p.drawLine(int(PL), H - PB, W - PR, H - PB)

        # y labels
        p.setFont(QFont("Consolas", 8))
        p.setPen(QColor("#6c757d"))
        for i in range(5):
            v = y_min + (1 - i / 4) * yr
            y = PT + i * (H - PT - PB) / 4
            p.drawText(QRect(0, int(y) - 8, PL - 4, 16),
                       Qt.AlignRight | Qt.AlignVCenter, "{:.4g}".format(v))

        # title
        if self._title:
            p.setFont(QFont("Arial", 9))
            p.setPen(QColor("#495057"))
            p.drawText(QRect(PL, 4, W - PL - PR, 18), Qt.AlignCenter, self._title)

        # series
        legend_x = PL + 8
        nearest_pt = None; nearest_dist = 1e9; nearest_name = ""
        for idx, (name, pts) in enumerate(self._series.items()):
            if not pts: continue
            color = QColor(CHART_COLORS[idx % len(CHART_COLORS)])
            p.setPen(QPen(color, 2))
            sorted_pts = sorted(pts, key=lambda x: x.step)
            path = QPainterPath()
            for i, pt in enumerate(sorted_pts):
                x, y = tx(pt.step), ty(pt.value)
                if i == 0: path.moveTo(x, y)
                else:       path.lineTo(x, y)
            p.drawPath(path)
            p.setBrush(color)
            for pt in sorted_pts:
                p.drawEllipse(QPoint(int(tx(pt.step)), int(ty(pt.value))), 3, 3)
            p.setBrush(Qt.NoBrush)
            # legend row
            ly = H - PB + 6 + (idx // 3) * 14
            p.fillRect(int(legend_x), int(ly), 10, 8, color)
            p.setFont(QFont("Arial", 8))
            p.setPen(QColor("#495057"))
            p.drawText(int(legend_x + 13), int(ly + 8), name)
            legend_x += max(len(name) * 6 + 20, 80)
            # hover nearest
            if self._hover_pos:
                for pt in sorted_pts:
                    d = abs(tx(pt.step) - self._hover_pos.x())
                    if d < nearest_dist:
                        nearest_dist = d; nearest_pt = pt; nearest_name = name

        # tooltip
        if self._hover_pos and nearest_pt and nearest_dist < 20:
            tip = nearest_name + " step=" + str(nearest_pt.step) + " val=" + "{:.6g}".format(nearest_pt.value)
            p.setFont(QFont("Arial", 8))
            fm  = p.fontMetrics()
            tw  = fm.horizontalAdvance(tip)
            ttx = min(int(tx(nearest_pt.step)) + 6, W - tw - 8)
            tty = max(int(ty(nearest_pt.value)) - 20, 4)
            p.fillRect(ttx, tty, tw + 8, 16, QColor(255, 255, 255, 210))
            p.setPen(QColor("#495057"))
            p.drawText(ttx + 4, tty + 12, tip)
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("MetricChart OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
