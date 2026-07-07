"""write_pl_canvas.py — DAGCanvas"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\pipeline_tab.py"
)

CODE = """

# =================================================================
# DAGCanvas  QPainter DAG 画布
# =================================================================

NODE_W, NODE_H = 140, 44
NODE_RADIUS    = 8
GRID           = 20


class DAGCanvas(QWidget):
    node_clicked  = Signal(str)   # node_id
    node_added    = Signal(str)   # node_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nodes:    List[DAGNode] = []
        self._pos:      Dict[str, QPoint] = {}
        self._drag_id:  Optional[str] = None
        self._drag_off: QPoint = QPoint(0, 0)
        self._selected: Optional[str] = None
        self.setMinimumSize(600, 360)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setStyleSheet("background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;")

    # ── public API ────────────────────────────────────────────────

    def load(self, nodes: List[DAGNode]):
        self._nodes = nodes
        self._auto_layout()
        self.update()

    def clear(self):
        self._nodes = []
        self._pos   = {}
        self._selected = None
        self.update()

    def selected_node_id(self) -> Optional[str]:
        return self._selected

    # ── layout ────────────────────────────────────────────────────

    def _auto_layout(self):
        if not self._nodes:
            return
        # topological sort by depends_on
        order = self._topo_sort()
        # assign columns by level
        levels: Dict[str, int] = {}
        for nid in order:
            nd = self._node_by_id(nid)
            if nd is None:
                continue
            lvl = 0
            for dep in nd.depends_on:
                lvl = max(lvl, levels.get(dep, 0) + 1)
            levels[nid] = lvl

        cols: Dict[int, List[str]] = {}
        for nid, lvl in levels.items():
            cols.setdefault(lvl, []).append(nid)

        PAD_X, PAD_Y = 60, 40
        COL_W = NODE_W + 80
        ROW_H = NODE_H + 36

        for col_idx, col_nodes in cols.items():
            total_h = len(col_nodes) * ROW_H
            start_y = max(PAD_Y, (self.height() - total_h) // 2)
            for row_idx, nid in enumerate(col_nodes):
                x = PAD_X + col_idx * COL_W
                y = start_y + row_idx * ROW_H
                self._pos[nid] = QPoint(x, y)

        # fill any missing
        for nd in self._nodes:
            if nd.node_id not in self._pos:
                self._pos[nd.node_id] = QPoint(PAD_X, PAD_Y)

    def _topo_sort(self) -> List[str]:
        in_deg: Dict[str, int] = {nd.node_id: 0 for nd in self._nodes}
        adj:    Dict[str, List[str]] = {nd.node_id: [] for nd in self._nodes}
        for nd in self._nodes:
            for dep in nd.depends_on:
                if dep in adj:
                    adj[dep].append(nd.node_id)
                    in_deg[nd.node_id] += 1
        queue = [nid for nid, d in in_deg.items() if d == 0]
        result = []
        while queue:
            cur = queue.pop(0)
            result.append(cur)
            for nxt in adj.get(cur, []):
                in_deg[nxt] -= 1
                if in_deg[nxt] == 0:
                    queue.append(nxt)
        # add any remaining (cycle fallback)
        for nd in self._nodes:
            if nd.node_id not in result:
                result.append(nd.node_id)
        return result

    def _node_by_id(self, nid: str) -> Optional[DAGNode]:
        for nd in self._nodes:
            if nd.node_id == nid:
                return nd
        return None

    def _node_rect(self, nid: str) -> QRect:
        pos = self._pos.get(nid, QPoint(0, 0))
        return QRect(pos.x(), pos.y(), NODE_W, NODE_H)

    def _node_at(self, pt: QPoint) -> Optional[str]:
        for nd in reversed(self._nodes):
            if self._node_rect(nd.node_id).contains(pt):
                return nd.node_id
        return None

    # ── mouse ─────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        nid = self._node_at(event.position().toPoint())
        if nid:
            self._selected = nid
            self._drag_id  = nid
            rect = self._node_rect(nid)
            self._drag_off = event.position().toPoint() - rect.topLeft()
            self.node_clicked.emit(nid)
        else:
            self._selected = None
            self._drag_id  = None
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_id:
            new_pos = event.position().toPoint() - self._drag_off
            # snap to grid
            new_pos = QPoint(
                round(new_pos.x() / GRID) * GRID,
                round(new_pos.y() / GRID) * GRID,
            )
            new_pos = QPoint(max(4, new_pos.x()), max(4, new_pos.y()))
            self._pos[self._drag_id] = new_pos
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_id = None

    # ── paint ─────────────────────────────────────────────────────

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._draw_grid(p)
        self._draw_edges(p)
        self._draw_nodes(p)
        p.end()

    def _draw_grid(self, p: QPainter):
        p.setPen(QPen(QColor("#e9ecef"), 1))
        W, H = self.width(), self.height()
        for x in range(0, W, GRID):
            p.drawLine(x, 0, x, H)
        for y in range(0, H, GRID):
            p.drawLine(0, y, W, y)

    def _draw_edges(self, p: QPainter):
        p.setPen(QPen(QColor("#adb5bd"), 2))
        for nd in self._nodes:
            for dep_id in nd.depends_on:
                src_rect = self._node_rect(dep_id)
                dst_rect = self._node_rect(nd.node_id)
                if src_rect.isNull() or dst_rect.isNull():
                    continue
                sx = src_rect.right()
                sy = src_rect.center().y()
                dx = dst_rect.left()
                dy = dst_rect.center().y()
                mid_x = (sx + dx) // 2
                path  = QPainterPath()
                path.moveTo(sx, sy)
                path.cubicTo(mid_x, sy, mid_x, dy, dx, dy)
                p.drawPath(path)
                # arrowhead
                angle = math.atan2(dy - sy, dx - sx)
                AL = 8
                p.setBrush(QColor("#adb5bd"))
                arr = QPainterPath()
                arr.moveTo(dx, dy)
                arr.lineTo(
                    dx - AL * math.cos(angle - 0.4),
                    dy - AL * math.sin(angle - 0.4))
                arr.lineTo(
                    dx - AL * math.cos(angle + 0.4),
                    dy - AL * math.sin(angle + 0.4))
                arr.closeSubpath()
                p.drawPath(arr)
                p.setBrush(Qt.NoBrush)

    def _draw_nodes(self, p: QPainter):
        for nd in self._nodes:
            rect    = self._node_rect(nd.node_id)
            is_sel  = (nd.node_id == self._selected)
            bg_col  = QColor(NODE_TYPE_COLOR.get(nd.node_type, "#6c757d"))
            sc_col  = QColor(NODE_STATUS_COLOR.get(nd.status, "#adb5bd"))

            # shadow
            shadow = QRect(rect.x()+3, rect.y()+3, rect.width(), rect.height())
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 30))
            p.drawRoundedRect(shadow, NODE_RADIUS, NODE_RADIUS)

            # background
            p.setBrush(bg_col if is_sel else QColor(255, 255, 255))
            pen_col = bg_col if is_sel else QColor("#dee2e6")
            pen_w   = 3 if is_sel else 1
            p.setPen(QPen(pen_col, pen_w))
            p.drawRoundedRect(rect, NODE_RADIUS, NODE_RADIUS)

            # left status strip
            strip = QRect(rect.x(), rect.y(), 6, rect.height())
            p.setPen(Qt.NoPen)
            p.setBrush(sc_col)
            # draw only left side rounded
            p.drawRect(strip)

            # icon + name
            icon = NODE_TYPE_ICON.get(nd.node_type, "")
            p.setFont(QFont("Arial", 9))
            text_color = QColor("white") if is_sel else QColor("#1a1f36")
            p.setPen(text_color)
            p.drawText(
                QRect(rect.x()+12, rect.y(), rect.width()-16, rect.height()//2 + 4),
                Qt.AlignVCenter | Qt.AlignLeft,
                icon + "  " + nd.name)

            # status text
            p.setFont(QFont("Arial", 7))
            p.setPen(sc_col if not is_sel else QColor("white"))
            p.drawText(
                QRect(rect.x()+12, rect.y()+rect.height()//2, rect.width()-16, rect.height()//2),
                Qt.AlignVCenter | Qt.AlignLeft,
                nd.status.value)

            # retry badge
            if nd.retries > 0:
                bx = rect.right() - 18
                by = rect.y() - 6
                p.setBrush(QColor("#fd7e14"))
                p.setPen(Qt.NoPen)
                p.drawEllipse(bx, by, 16, 16)
                p.setFont(QFont("Arial", 7))
                p.setPen(QColor("white"))
                p.drawText(QRect(bx, by, 16, 16),
                            Qt.AlignCenter, str(nd.retries))
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("DAGCanvas OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
