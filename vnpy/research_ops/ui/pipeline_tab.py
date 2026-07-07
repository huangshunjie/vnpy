"""
research_ops/ui/pipeline_tab.py  Phase 5 - Pipeline System
"""
from __future__ import annotations
from typing import List, Optional, Dict, Tuple
import math

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QMenu, QMessageBox, QFrame,
    QTableWidget, QTableWidgetItem, QScrollArea,
    QSizePolicy, QSpinBox,
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QSize, QRectF
from PySide6.QtGui import (
    QColor, QFont, QBrush, QPainter, QPen,
    QPainterPath, QMouseEvent,
)

from vnpy.event import Event
from ..main_engine import ResearchOpsEngine
from ..model.pipeline_model import PipelineRecord, DAGNode, PipelineRunRecord
from ..constant import PipelineStatus, NodeStatus, NodeType, TriggerType
from ..event import (
    EVENT_RO_PL_CREATED, EVENT_RO_PL_UPDATED,
    EVENT_RO_PL_DELETED, EVENT_RO_PL_STARTED,
    EVENT_RO_PL_COMPLETED, EVENT_RO_PL_FAILED,
    EVENT_RO_PL_PAUSED, EVENT_RO_PL_RESET,
    EVENT_RO_NODE_STARTED, EVENT_RO_NODE_COMPLETED,
    EVENT_RO_NODE_FAILED, EVENT_RO_NODE_SKIPPED,
)

# ── palettes ──────────────────────────────────────────────────────
PL_STATUS_COLOR = {
    PipelineStatus.IDLE:      "#6c757d",
    PipelineStatus.RUNNING:   "#198754",
    PipelineStatus.COMPLETED: "#0d6efd",
    PipelineStatus.FAILED:    "#dc3545",
    PipelineStatus.PAUSED:    "#fd7e14",
}
NODE_STATUS_COLOR = {
    NodeStatus.IDLE:      "#adb5bd",
    NodeStatus.PENDING:   "#6c757d",
    NodeStatus.RUNNING:   "#198754",
    NodeStatus.COMPLETED: "#0d6efd",
    NodeStatus.FAILED:    "#dc3545",
    NodeStatus.SKIPPED:   "#fd7e14",
}
NODE_TYPE_COLOR = {
    NodeType.DATA_LOAD:    "#4a6cf7",
    NodeType.FEATURE_CALC: "#198754",
    NodeType.MODEL_TRAIN:  "#9c27b0",
    NodeType.BACKTEST:     "#fd7e14",
    NodeType.VALIDATION:   "#0d6efd",
    NodeType.REPORT:       "#17a2b8",
    NodeType.NOTIFY:       "#6f42c1",
    NodeType.CUSTOM:       "#6c757d",
}
NODE_TYPE_ICON = {
    NodeType.DATA_LOAD:    "\U0001f4be",
    NodeType.FEATURE_CALC: "\U0001f4d0",
    NodeType.MODEL_TRAIN:  "\U0001f916",
    NodeType.BACKTEST:     "\U0001f4c8",
    NodeType.VALIDATION:   "\u2705",
    NodeType.REPORT:       "\U0001f4dd",
    NodeType.NOTIFY:       "\U0001f514",
    NodeType.CUSTOM:       "\u2699",
}
ROLE_ID   = Qt.UserRole
ROLE_TYPE = Qt.UserRole + 1


# =================================================================
# PipelineDialog
# =================================================================

class PipelineDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\u7f16\u8f91 Pipeline" if self._editing
            else "\u65b0\u5efa Pipeline")
        self.setMinimumWidth(460)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("Pipeline \u4fe1\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit()
        self._name.setPlaceholderText("Pipeline \u540d\u79f0")
        form.addRow("\u540d\u79f0 *", self._name)
        self._desc = QTextEdit(); self._desc.setFixedHeight(52)
        form.addRow("\u63cf\u8ff0", self._desc)
        self._author = QLineEdit()
        form.addRow("\u4f5c\u8005", self._author)
        self._schedule = QLineEdit()
        self._schedule.setPlaceholderText("cron \u8868\u8fbe\u5f0f\uff0c\u5982 0 9 * * 1-5")
        form.addRow("\u8c03\u5ea6", self._schedule)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\u9017\u53f7\u5206\u9694")
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
        self._author.setText(r.author or "")
        self._schedule.setText(r.schedule or "")
        self._tags.setText(", ".join(r.tags))

    def _on_ok(self):
        if not self._name.text().strip():
            self._name.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]
    def get_name(self)        -> str:       return self._name.text().strip()
    def get_description(self) -> str:       return self._desc.toPlainText().strip()
    def get_author(self)      -> str:       return self._author.text().strip()
    def get_schedule(self)    -> str:       return self._schedule.text().strip()
    def get_tags(self)        -> List[str]: return self._split(self._tags.text())


# =================================================================
# NodeDialog
# =================================================================

class NodeDialog(QDialog):
    def __init__(self, parent=None, pipeline_id: str = "",
                 existing_nodes: Optional[List[DAGNode]] = None):
        super().__init__(parent)
        self._pipeline_id  = pipeline_id
        self._existing     = existing_nodes or []
        self.setWindowTitle("\u6dfb\u52a0\u8282\u70b9")
        self.setMinimumWidth(460)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u8282\u70b9\u4fe1\u606f")
        form = QFormLayout(grp)

        self._name = QLineEdit()
        self._name.setPlaceholderText("\u8282\u70b9\u540d\u79f0")
        form.addRow("\u540d\u79f0 *", self._name)

        self._type = QComboBox()
        for nt in NodeType:
            icon = NODE_TYPE_ICON.get(nt, "")
            self._type.addItem(icon + "  " + nt.value, nt)
        form.addRow("\u7c7b\u578b", self._type)

        self._timeout = QSpinBox()
        self._timeout.setRange(1, 86400)
        self._timeout.setValue(3600)
        self._timeout.setSuffix(" \u79d2")
        form.addRow("\u8d85\u65f6", self._timeout)

        self._retries = QSpinBox()
        self._retries.setRange(0, 10)
        self._retries.setValue(3)
        form.addRow("\u6700\u5927\u91cd\u8bd5", self._retries)

        # depends_on checkboxes built from existing nodes
        if self._existing:
            dep_grp = QGroupBox("\u524d\u7f6e\u8282\u70b9\uff08\u4f9d\u8d56\uff09")
            dep_l   = QVBoxLayout(dep_grp)
            from PySide6.QtWidgets import QCheckBox
            self._dep_checks: List[Tuple[str, object]] = []
            for nd in self._existing:
                cb = QCheckBox(NODE_TYPE_ICON.get(nd.node_type, "") + "  " + nd.name)
                dep_l.addWidget(cb)
                self._dep_checks.append((nd.node_id, cb))
            root.addWidget(grp)
            root.addWidget(dep_grp)
        else:
            self._dep_checks = []
            root.addWidget(grp)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u6dfb\u52a0")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _on_ok(self):
        if not self._name.text().strip():
            self._name.setFocus(); return
        self.accept()

    def get_name(self)        -> str:        return self._name.text().strip()
    def get_node_type(self)   -> NodeType:   return self._type.currentData()
    def get_timeout(self)     -> int:        return self._timeout.value()
    def get_max_retries(self) -> int:        return self._retries.value()
    def get_depends_on(self)  -> List[str]:
        return [nid for nid, cb in self._dep_checks if cb.isChecked()]


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


class PipelineList(QWidget):
    selected = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._filter  = None
        self._keyword = ""
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        fb = QHBoxLayout()
        self._combo = QComboBox()
        self._combo.addItem("\u5168\u90e8", None)
        for st in PipelineStatus:
            self._combo.addItem(st.value, st)
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1)
        root.addLayout(fb)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\u540d\u79f0", "\u72b6\u6001", "\u8282\u70b9", "\u8fd0\u884c\u6b21\u6570"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.itemClicked.connect(self._on_click)
        self._table.customContextMenuRequested.connect(self._on_ctx)
        root.addWidget(self._table)

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in (EVENT_RO_PL_CREATED, EVENT_RO_PL_UPDATED,
                   EVENT_RO_PL_DELETED, EVENT_RO_PL_STARTED,
                   EVENT_RO_PL_COMPLETED, EVENT_RO_PL_FAILED,
                   EVENT_RO_PL_PAUSED,   EVENT_RO_PL_RESET):
            ee.register(ev, lambda _: self._refresh())

    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()
    def _on_filter(self, _):   self._filter = self._combo.currentData(); self._refresh()

    def _refresh(self):
        items = self._engine.list_pipelines()
        if self._filter:
            items = [p for p in items if p.status == self._filter]
        if self._keyword:
            items = [p for p in items if self._keyword in p.name.lower()
                     or any(self._keyword in t for t in p.tags)]
        self._table.setRowCount(0)
        for pl in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(pl.name))
            sc  = PL_STATUS_COLOR.get(pl.status, "#6c757d")
            si  = QTableWidgetItem(pl.status.value)
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 1, si)
            ni  = QTableWidgetItem(str(len(pl.nodes)))
            ni.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(r, 2, ni)
            ri  = QTableWidgetItem(str(pl.run_count))
            ri.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(r, 3, ri)
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, pl.pipeline_id)

    def _on_click(self, item):
        self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        pid = item.data(ROLE_ID)
        pl  = self._engine.get_pipeline(pid)
        if not pl: return
        menu = QMenu(self)
        a_start  = menu.addAction("\u25b6  \u8fd0\u884c")
        a_pause  = menu.addAction("\u23f8  \u6682\u505c")
        a_reset  = menu.addAction("\U0001f504  \u91cd\u7f6e")
        menu.addSeparator()
        a_del    = menu.addAction("\U0001f5d1  \u5220\u9664")
        action   = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == a_start:
            self._engine.start_pipeline(pid); self._refresh()
        elif action == a_pause:
            self._engine.pause_pipeline(pid); self._refresh()
        elif action == a_reset:
            self._engine.reset_pipeline(pid); self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\u786e\u8ba4",
                "\u5220\u9664 Pipeline \u300c" + pl.name + "\u300d\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_pipeline(pid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class PipelineDetail(QTabWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._pl_id: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        self.setDocumentMode(True)

        # ── Tab1: overview + DAG canvas ───────────────────────────
        ov = QWidget(); ov_l = QVBoxLayout(ov)
        hdr = QHBoxLayout()
        self._title = QLabel("\u8bf7\u9009\u62e9 Pipeline")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title)
        hdr.addStretch()
        self._status_badge = QLabel("")
        self._status_badge.setFixedHeight(22)
        self._status_badge.setStyleSheet("padding:2px 10px;border-radius:10px;font-size:12px;")
        hdr.addWidget(self._status_badge)
        ov_l.addLayout(hdr)

        self._color_bar = QFrame()
        self._color_bar.setFixedHeight(4)
        self._color_bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        ov_l.addWidget(self._color_bar)

        # stat cards
        cr = QHBoxLayout()
        self._c_nodes   = self._card("\u8282\u70b9\u6570",   "0")
        self._c_runs    = self._card("\u8fd0\u884c\u6b21\u6570", "0")
        self._c_success = self._card("\u6210\u529f",     "0", "#198754")
        self._c_fail    = self._card("\u5931\u8d25",     "0", "#dc3545")
        for c in (self._c_nodes, self._c_runs, self._c_success, self._c_fail):
            cr.addWidget(c)
        ov_l.addLayout(cr)

        # info table
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\u5c5e\u6027","\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        self._info.setFixedHeight(130)
        ov_l.addWidget(self._info)

        # DAG canvas
        canvas_lbl = QLabel("DAG \u753b\u5e03\uff08\u53ef\u62d6\u62fd\u8282\u70b9\uff09")
        canvas_lbl.setStyleSheet("font-weight:bold;color:#495057;margin-top:4px;")
        ov_l.addWidget(canvas_lbl)
        self._canvas = DAGCanvas()
        self._canvas.node_clicked.connect(self._on_node_click)
        ov_l.addWidget(self._canvas, 1)
        self.addTab(ov, "\U0001f5fa  \u6982\u89c8")

        # ── Tab2: execution runs ───────────────────────────────────
        ex = QWidget(); ex_l = QVBoxLayout(ex)
        self._run_table = QTableWidget(0, 4)
        self._run_table.setHorizontalHeaderLabels([
            "Run ID", "\u72b6\u6001", "\u65f6\u957f(s)", "\u5f00\u59cb\u65f6\u95f4"])
        self._run_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._run_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._run_table.setAlternatingRowColors(True)
        self._run_table.verticalHeader().setVisible(False)
        ex_l.addWidget(self._run_table)
        self.addTab(ex, "\u25b6  \u6267\u884c\u5386\u53f2")

        # ── Tab3: node detail ─────────────────────────────────────
        nd_w = QWidget(); nd_l = QVBoxLayout(nd_w)
        self._nd_title = QLabel("\u70b9\u51fb DAG \u4e2d\u7684\u8282\u70b9\u67e5\u770b\u8be6\u60c5")
        self._nd_title.setStyleSheet("font-size:13px;font-weight:bold;color:#495057;")
        nd_l.addWidget(self._nd_title)
        self._nd_table = QTableWidget(0, 2)
        self._nd_table.setHorizontalHeaderLabels(["\u5c5e\u6027","\u503c"])
        self._nd_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._nd_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._nd_table.setAlternatingRowColors(True)
        self._nd_table.verticalHeader().setVisible(False)
        self._nd_table.setFixedHeight(150)
        nd_l.addWidget(self._nd_table)
        log_lbl = QLabel("\u8282\u70b9\u65e5\u5fd7")
        log_lbl.setStyleSheet("font-weight:bold;color:#495057;margin-top:4px;")
        nd_l.addWidget(log_lbl)
        self._nd_log = QTextEdit()
        self._nd_log.setReadOnly(True)
        self._nd_log.setFont(QFont("Consolas", 9))
        self._nd_log.setStyleSheet(
            "background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;")
        nd_l.addWidget(self._nd_log, 1)
        self.addTab(nd_w, "\U0001f4cb  \u8282\u70b9\u8be6\u60c5")

    @staticmethod
    def _card(label, value, color="#1a1f36"):
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame{background:#fff;border:1px solid #dee2e6;"
            "border-radius:8px;padding:6px;}")
        lay = QVBoxLayout(card); lay.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet("color:#6c757d;font-size:11px;")
        lay.addWidget(lbl)
        val = QLabel(value)
        val.setStyleSheet(
            "font-size:20px;font-weight:bold;color:" + color + ";")
        val.setAlignment(Qt.AlignCenter)
        lay.addWidget(val)
        card._val = val
        return card

    # ── load / clear ──────────────────────────────────────────────

    def load(self, pl_id: str):
        self._pl_id = pl_id
        pl = self._engine.get_pipeline(pl_id)
        if not pl:
            self.clear_panel(); return
        self._load_overview(pl)
        self._load_runs(pl)

    def clear_panel(self):
        self._pl_id = None
        self._title.setText("\u8bf7\u9009\u62e9 Pipeline")
        self._status_badge.setText("")
        self._status_badge.setStyleSheet("")
        self._color_bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        for c in (self._c_nodes, self._c_runs, self._c_success, self._c_fail):
            c._val.setText("0")
        self._info.setRowCount(0)
        self._canvas.clear()
        self._run_table.setRowCount(0)
        self._nd_table.setRowCount(0)
        self._nd_log.clear()
        self._nd_title.setText("\u70b9\u51fb DAG \u4e2d\u7684\u8282\u70b9\u67e5\u770b\u8be6\u60c5")

    def _load_overview(self, pl: PipelineRecord):
        self._title.setText(pl.name)
        sc = PL_STATUS_COLOR.get(pl.status, "#6c757d")
        self._status_badge.setText(pl.status.value)
        self._status_badge.setStyleSheet(
            "padding:2px 10px;border-radius:10px;"
            "background:" + sc + "22;color:" + sc + ";"
            "font-size:12px;font-weight:bold;"
            "border:1px solid " + sc + "44;")
        self._color_bar.setStyleSheet("background:" + sc + ";border-radius:2px;")
        self._c_nodes._val.setText(str(len(pl.nodes)))
        self._c_runs._val.setText(str(pl.run_count))
        self._c_success._val.setText(str(pl.success_count))
        self._c_fail._val.setText(str(pl.fail_count))
        self._info.setRowCount(0)
        lr = pl.last_run_at.strftime("%Y-%m-%d %H:%M") if pl.last_run_at else "\u2014"
        for k, v in [
            ("ID", pl.pipeline_id), ("\u540d\u79f0", pl.name),
            ("\u4f5c\u8005", pl.author or "\u2014"),
            ("\u8c03\u5ea6", pl.schedule or "\u2014"),
            ("\u6807\u7b7e", ", ".join(pl.tags) if pl.tags else "\u2014"),
            ("\u4e0a\u6b21\u8fd0\u884c", lr),
            ("\u521b\u5efa", pl.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))
        self._canvas.load(pl.nodes)

    def _load_runs(self, pl: PipelineRecord):
        self._run_table.setRowCount(0)
        for run in reversed(pl.runs):
            r = self._run_table.rowCount(); self._run_table.insertRow(r)
            self._run_table.setItem(r, 0, QTableWidgetItem(run.run_id[:12]))
            st_item = QTableWidgetItem(run.status)
            col = "#198754" if run.status == "completed" else (
                  "#dc3545" if run.status == "failed" else "#fd7e14")
            st_item.setForeground(QBrush(QColor(col)))
            self._run_table.setItem(r, 1, st_item)
            self._run_table.setItem(r, 2, QTableWidgetItem(str(round(run.duration_sec, 1))))
            ts = run.started_at.strftime("%Y-%m-%d %H:%M:%S")
            self._run_table.setItem(r, 3, QTableWidgetItem(ts))

    def _on_node_click(self, node_id: str):
        if not self._pl_id: return
        pl = self._engine.get_pipeline(self._pl_id)
        if not pl: return
        nd = next((n for n in pl.nodes if n.node_id == node_id), None)
        if not nd: return
        self._nd_title.setText(
            NODE_TYPE_ICON.get(nd.node_type,"") + "  " + nd.name)
        self._nd_table.setRowCount(0)
        sc = NODE_STATUS_COLOR.get(nd.status, "#6c757d")
        for k, v in [
            ("Node ID",     nd.node_id[:12]),
            ("\u7c7b\u578b",   nd.node_type.value),
            ("\u72b6\u6001",   nd.status.value),
            ("\u524d\u7f6e",   ", ".join(nd.depends_on) if nd.depends_on else "\u2014"),
            ("\u8d85\u65f6",   str(nd.timeout_sec) + "s"),
            ("\u91cd\u8bd5",   str(nd.retries) + "/" + str(nd.max_retries)),
            ("\u5f00\u59cb", nd.started_at.strftime("%H:%M:%S") if nd.started_at else "\u2014"),
            ("\u7ed3\u675f", nd.finished_at.strftime("%H:%M:%S") if nd.finished_at else "\u2014"),
        ]:
            r = self._nd_table.rowCount(); self._nd_table.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._nd_table.setItem(r, 0, ki)
            vi = QTableWidgetItem(str(v))
            if k == "\u72b6\u6001":
                vi.setForeground(QBrush(QColor(sc)))
            self._nd_table.setItem(r, 1, vi)
        self._nd_log.setPlainText(nd.log or "(\u65e0\u65e5\u5fd7)")
        if nd.error_msg:
            self._nd_log.append("\n[ERROR] " + nd.error_msg)
        self.setCurrentIndex(2)


class PipelineTab(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # ── toolbar ───────────────────────────────────────────────
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_new    = QPushButton("+ \u65b0\u5efa")
        self._btn_node   = QPushButton("\u2295 \u6dfb\u52a0\u8282\u70b9")
        self._btn_start  = QPushButton("\u25b6 \u8fd0\u884c")
        self._btn_pause  = QPushButton("\u23f8 \u6682\u505c")
        self._btn_reset  = QPushButton("\U0001f504 \u91cd\u7f6e")
        self._btn_del    = QPushButton("\U0001f5d1 \u5220\u9664")
        for btn in (self._btn_new, self._btn_node, self._btn_start,
                    self._btn_pause, self._btn_reset, self._btn_del):
            btn.setFixedHeight(28); tb.addWidget(btn)
        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#dee2e6;"); tb.addWidget(sep)
        tb.addStretch()
        tb.addWidget(QLabel("\u641c\u7d22:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Pipeline \u540d\u79f0...")
        self._search_box.setFixedWidth(160); self._search_box.setFixedHeight(28)
        tb.addWidget(self._search_box)
        self._btn_search = QPushButton("\u641c\u7d22")
        self._btn_search.setFixedSize(52, 28)
        self._btn_reset_s = QPushButton("\u91cd\u7f6e")
        self._btn_reset_s.setFixedSize(52, 28)
        tb.addWidget(self._btn_search); tb.addWidget(self._btn_reset_s)
        root.addLayout(tb)

        # ── stats bar ─────────────────────────────────────────────
        self._stats_bar = QLabel("\u52a0\u8f7d\u4e2d...")
        self._stats_bar.setStyleSheet(
            "background:#fff3e0;border:1px solid #ffcc80;"
            "border-radius:4px;padding:4px 10px;"
            "color:#e65100;font-size:12px;")
        root.addWidget(self._stats_bar)

        # ── splitter ──────────────────────────────────────────────
        sp = QSplitter(Qt.Horizontal)
        self._pl_list = PipelineList(self._engine)
        self._pl_list.setMinimumWidth(200)
        sp.addWidget(self._pl_list)
        self._detail = PipelineDetail(self._engine)
        sp.addWidget(self._detail)
        sp.setSizes([240, 960])
        sp.setStretchFactor(0, 0); sp.setStretchFactor(1, 1)
        root.addWidget(sp)

        # ── status bar ────────────────────────────────────────────
        self._status = QLabel("\u5c31\u7eea")
        self._status.setStyleSheet("color:#6c757d;font-size:11px;")
        root.addWidget(self._status)

        # ── connect ───────────────────────────────────────────────
        self._pl_list.selected.connect(self._on_pl_selected)
        self._btn_new.clicked.connect(self._on_new)
        self._btn_node.clicked.connect(self._on_add_node)
        self._btn_start.clicked.connect(self._on_start)
        self._btn_pause.clicked.connect(self._on_pause)
        self._btn_reset.clicked.connect(self._on_reset_pl)
        self._btn_del.clicked.connect(self._on_delete)
        self._btn_search.clicked.connect(self._on_search)
        self._btn_reset_s.clicked.connect(self._on_reset_search)
        self._search_box.returnPressed.connect(self._on_search)

        for ev in (EVENT_RO_PL_CREATED, EVENT_RO_PL_UPDATED,
                   EVENT_RO_PL_DELETED, EVENT_RO_PL_STARTED,
                   EVENT_RO_PL_COMPLETED, EVENT_RO_PL_FAILED,
                   EVENT_RO_PL_PAUSED,   EVENT_RO_PL_RESET,
                   EVENT_RO_NODE_STARTED, EVENT_RO_NODE_COMPLETED,
                   EVENT_RO_NODE_FAILED,  EVENT_RO_NODE_SKIPPED):
            self._engine.event_engine.register(ev, self._on_stats_event)

        self._refresh_stats()

    # ── current pipeline ──────────────────────────────────────────

    def _current_pl_id(self) -> Optional[str]:
        return self._pl_list.selected_id()

    # ── ops ───────────────────────────────────────────────────────

    def _on_new(self):
        dlg = PipelineDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            pl = self._engine.create_pipeline(
                name        = dlg.get_name(),
                description = dlg.get_description(),
                author      = dlg.get_author(),
                schedule    = dlg.get_schedule(),
                tags        = dlg.get_tags(),
            )
            self._set_status("Pipeline \u300c" + pl.name + "\u300d\u5df2\u521b\u5efa")
            self._refresh_stats()

    def _on_add_node(self):
        pid = self._current_pl_id()
        if not pid:
            self._set_status("\u8bf7\u5148\u9009\u62e9\u4e00\u4e2a Pipeline")
            return
        pl = self._engine.get_pipeline(pid)
        if not pl: return
        dlg = NodeDialog(parent=self, pipeline_id=pid,
                         existing_nodes=pl.nodes)
        if dlg.exec() == QDialog.Accepted:
            nd = self._engine.add_node(
                pipeline_id = pid,
                name        = dlg.get_name(),
                node_type   = dlg.get_node_type(),
                depends_on  = dlg.get_depends_on(),
                timeout_sec = dlg.get_timeout(),
                max_retries = dlg.get_max_retries(),
            )
            if nd:
                self._detail.load(pid)
                self._set_status(
                    "\u8282\u70b9\u300c" + nd.name + "\u300d\u5df2\u6dfb\u52a0")

    def _on_start(self):
        pid = self._current_pl_id()
        if not pid:
            self._set_status("\u8bf7\u5148\u9009\u62e9 Pipeline"); return
        run = self._engine.start_pipeline(pid)
        if run:
            self._detail.load(pid)
            self._set_status("Pipeline \u5df2\u542f\u52a8\uff0cRun: " + run.run_id[:12])
        self._refresh_stats()

    def _on_pause(self):
        pid = self._current_pl_id()
        if not pid: return
        self._engine.pause_pipeline(pid)
        self._detail.load(pid)
        self._set_status("Pipeline \u5df2\u6682\u505c")
        self._refresh_stats()

    def _on_reset_pl(self):
        pid = self._current_pl_id()
        if not pid: return
        self._engine.reset_pipeline(pid)
        self._detail.load(pid)
        self._set_status("Pipeline \u5df2\u91cd\u7f6e")
        self._refresh_stats()

    def _on_delete(self):
        pid = self._current_pl_id()
        if not pid: return
        pl = self._engine.get_pipeline(pid)
        if not pl: return
        if QMessageBox.question(
            self, "\u786e\u8ba4\u5220\u9664",
            "\u5220\u9664 Pipeline \u300c" + pl.name + "\u300d\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self._engine.delete_pipeline(pid)
            self._detail.clear_panel()
            self._set_status("Pipeline \u300c" + pl.name + "\u300d\u5df2\u5220\u9664")
            self._refresh_stats()

    # ── search ────────────────────────────────────────────────────

    def _on_search(self):
        kw = self._search_box.text().strip()
        if not kw: return
        self._pl_list.set_keyword(kw)
        results = self._engine.search_pipelines(kw)
        self._set_status("\u641c\u7d22\u300c" + kw + "\u300d\uff1a\u627e\u5230 "
                         + str(len(results)) + " \u4e2a Pipeline")

    def _on_reset_search(self):
        self._search_box.clear()
        self._pl_list.set_keyword("")
        self._set_status("\u5c31\u7eea")

    # ── selection ─────────────────────────────────────────────────

    def _on_pl_selected(self, pl_id: str):
        self._detail.load(pl_id)
        pl = self._engine.get_pipeline(pl_id)
        if pl:
            self._set_status(
                "Pipeline: " + pl.name
                + "  \u8282\u70b9: " + str(len(pl.nodes))
                + "  \u72b6\u6001: " + pl.status.value)

    # ── stats ─────────────────────────────────────────────────────

    def _on_stats_event(self, _=None):
        self._refresh_stats()
        pid = self._current_pl_id()
        if pid:
            self._detail.load(pid)

    def _refresh_stats(self):
        s = self._engine.stats()
        self._stats_bar.setText(
            "Pipeline: " + str(s.get("pipelines", 0))
            + "    \u8fd0\u884c\u4e2d: " + str(s.get("running", 0))
            + "    \u5df2\u5b8c\u6210: " + str(s.get("completed", 0))
            + "    \u5931\u8d25: "     + str(s.get("failed", 0))
            + "    \u8282\u70b9\u603b\u6570: " + str(s.get("total_nodes", 0)))

    def _set_status(self, msg: str):
        self._status.setText(msg)
