"""
platform_engineering/ui/api.py
ApiTab — Phase 7
路由列表 + 实时请求日志 + 统计面板 + 测试控制台
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox, QLineEdit,
    QGroupBox, QPlainTextEdit, QGridLayout,
    QFormLayout, QDialog, QDialogButtonBox,
    QTextEdit, QSplitter,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush, QFont

if TYPE_CHECKING:
    from ..engine_main import PlatformEngine

METHOD_COLOR = {
    "GET":    "#52c41a",
    "POST":   "#1890ff",
    "PUT":    "#faad14",
    "DELETE": "#ff4d4f",
    "PATCH":  "#722ed1",
}
STATUS_COLOR = {
    2: "#52c41a",   # 2xx
    4: "#faad14",   # 4xx
    5: "#ff4d4f",   # 5xx
}
ROLE_PATH = Qt.UserRole


class RegisterRouteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u6ce8\u518c\u8def\u7531")
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u8def\u7531\u4fe1\u606f")
        form = QFormLayout(grp)
        self._path = QLineEdit(); self._path.setPlaceholderText("/api/v1/xxx")
        form.addRow("\u8def\u5f84 *", self._path)
        self._methods = QLineEdit(); self._methods.setText("GET")
        self._methods.setPlaceholderText("GET,POST")
        form.addRow("\u65b9\u6cd5", self._methods)
        self._group = QLineEdit()
        form.addRow("\u5206\u7ec4", self._group)
        self._desc = QLineEdit()
        form.addRow("\u63cf\u8ff0", self._desc)
        self._rate = QLineEdit(); self._rate.setText("0")
        self._rate.setPlaceholderText("0 = \u65e0\u9650\u6d41")
        form.addRow("\u9650\u6d41 (\u6b21/\u5206)", self._rate)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u6ce8\u518c")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        if not self._path.text().strip(): self._path.setFocus(); return
        self.accept()

    def get_path(self)     -> str:       return self._path.text().strip()
    def get_methods(self)  -> list:
        return [m.strip().upper() for m in self._methods.text().split(",") if m.strip()]
    def get_group(self)    -> str:       return self._group.text().strip()
    def get_desc(self)     -> str:       return self._desc.text().strip()
    def get_rate_limit(self) -> int:
        try: return int(self._rate.text())
        except: return 0


def _status_color(code: int) -> str:
    return STATUS_COLOR.get(code // 100, "#8c8c8c")


class StatCard(QFrame):
    def __init__(self, label: str, color: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame{background:#fff;border-radius:8px;border:1px solid #f0f0f0;}")
        self.setFixedHeight(72)
        lay = QVBoxLayout(self); lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(2)
        self._val = QLabel("\u2014")
        self._val.setStyleSheet(
            f"font-size:22px;font-weight:bold;color:{color};"
            "background:transparent;border:none;")
        lay.addWidget(self._val)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size:11px;color:#8c8c8c;background:transparent;border:none;")
        lay.addWidget(lbl)

    def set_value(self, v): self._val.setText(str(v))


class StatPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        grid = QGridLayout(self); grid.setSpacing(8); grid.setContentsMargins(0,0,0,0)
        self._cards = {}
        defs = [
            ("routes",      "\u8def\u7531\u603b\u6570",   "#4a6cf7"),
            ("total_calls", "\u8bf7\u6c42\u603b\u6570",   "#1890ff"),
            ("total_errors","\u9519\u8bef\u603b\u6570",   "#ff4d4f"),
            ("avg_latency", "\u5e73\u5747\u5ef6\u8fdf(ms)","#faad14"),
            ("error_rate",  "\u9519\u8bef\u7387",          "#ff4d4f"),
            ("log_entries", "\u65e5\u5fd7\u6761\u6570",   "#52c41a"),
        ]
        for i, (key, label, color) in enumerate(defs):
            card = StatCard(label, color)
            self._cards[key] = card
            grid.addWidget(card, i // 3, i % 3)

    def refresh(self, stats: dict):
        self._cards["routes"].set_value(stats.get("routes", 0))
        self._cards["total_calls"].set_value(stats.get("total_calls", 0))
        self._cards["total_errors"].set_value(stats.get("total_errors", 0))
        self._cards["avg_latency"].set_value(
            f"{stats.get('avg_latency_ms', 0.0):.1f}")
        self._cards["error_rate"].set_value(
            f"{stats.get('error_rate', 0.0)*100:.2f}%")
        self._cards["log_entries"].set_value(stats.get("log_entries", 0))


class RouteList(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._on_select = None
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_reg = QPushButton("\u2795 \u6ce8\u518c\u8def\u7531")
        self._btn_reg.setFixedHeight(26)
        self._btn_reg.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_reg.clicked.connect(self._on_register)
        tb.addWidget(self._btn_reg)
        self._btn_del = QPushButton("\U0001f5d1 \u5220\u9664")
        self._btn_del.setFixedHeight(26)
        self._btn_del.setStyleSheet(
            "background:#ff4d4f;color:#fff;border-radius:4px;border:none;")
        self._btn_del.clicked.connect(self._on_delete)
        tb.addWidget(self._btn_del)
        self._group_combo = QComboBox(); self._group_combo.setFixedHeight(26)
        self._group_combo.addItem("\u5168\u90e8\u5206\u7ec4", None)
        self._group_combo.currentIndexChanged.connect(lambda _: self.refresh())
        tb.addWidget(self._group_combo, 1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("\u8fc7\u6ee4\u8def\u5f84...")
        self._search.setFixedHeight(26)
        self._search.textChanged.connect(lambda _: self.refresh())
        tb.addWidget(self._search)
        root.addLayout(tb)
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            "\u8def\u5f84","\u65b9\u6cd5","\u5206\u7ec4",
            "\u8c03\u7528\u6b21\u6570","\u5e73\u5747\u5ef6\u8fdf(ms)","\u63cf\u8ff0"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.itemClicked.connect(self._on_click)
        root.addWidget(self._table)

    def set_select_callback(self, cb): self._on_select = cb

    def refresh(self):
        if not self._engine: return
        grp  = self._group_combo.currentData()
        routes = self._engine.api.list_routes(group=grp)
        kw = self._search.text().strip().lower()
        if kw: routes = [r for r in routes if kw in r.path.lower()]
        # rebuild group combo (preserve selection)
        cur_grp = self._group_combo.currentData()
        self._group_combo.blockSignals(True)
        self._group_combo.clear()
        self._group_combo.addItem("\u5168\u90e8\u5206\u7ec4", None)
        all_groups = sorted({r.group for r in self._engine.api.list_routes() if r.group})
        for g in all_groups: self._group_combo.addItem(g, g)
        idx = self._group_combo.findData(cur_grp)
        if idx >= 0: self._group_combo.setCurrentIndex(idx)
        self._group_combo.blockSignals(False)

        self._table.setRowCount(0)
        for r in routes:
            row = self._table.rowCount(); self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(r.path))
            methods_str = ",".join(r.methods)
            mi = QTableWidgetItem(methods_str)
            color = METHOD_COLOR.get(r.methods[0] if r.methods else "GET", "#8c8c8c")
            mi.setForeground(QBrush(QColor(color)))
            self._table.setItem(row, 1, mi)
            self._table.setItem(row, 2, QTableWidgetItem(r.group or "\u2014"))
            self._table.setItem(row, 3, QTableWidgetItem(str(r.call_count)))
            self._table.setItem(row, 4,
                QTableWidgetItem(f"{r.avg_latency_ms:.1f}"))
            self._table.setItem(row, 5, QTableWidgetItem(r.description))
            for c in range(6):
                self._table.item(row, c).setData(ROLE_PATH, r.path)

    def _on_click(self, item):
        if self._on_select: self._on_select(item.data(ROLE_PATH))

    def _on_register(self):
        if not self._engine: return
        dlg = RegisterRouteDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._engine.api.register(
                path=dlg.get_path(),
                handler=lambda req: {"path": req.path, "ok": True},
                methods=dlg.get_methods(),
                group=dlg.get_group(),
                description=dlg.get_desc(),
                rate_limit=dlg.get_rate_limit(),
            )
            self.refresh()

    def _on_delete(self):
        items = self._table.selectedItems()
        if not items or not self._engine: return
        path = items[0].data(ROLE_PATH)
        self._engine.api.unregister(path)
        self.refresh()
        if self._on_select: self._on_select(None)


class RequestLog(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._method_combo = QComboBox(); self._method_combo.setFixedHeight(26)
        self._method_combo.addItem("\u5168\u90e8\u65b9\u6cd5", "")
        for m in ("GET","POST","PUT","DELETE"): self._method_combo.addItem(m, m)
        self._method_combo.currentIndexChanged.connect(self.refresh)
        tb.addWidget(self._method_combo)
        self._path_filter = QLineEdit()
        self._path_filter.setPlaceholderText("\u8def\u5f84\u8fc7\u6ee4...")
        self._path_filter.setFixedHeight(26)
        self._path_filter.textChanged.connect(self.refresh)
        tb.addWidget(self._path_filter)
        self._btn_clear = QPushButton("\U0001f5d1 \u6e05\u7a7a")
        self._btn_clear.setFixedHeight(26)
        self._btn_clear.setStyleSheet(
            "background:#ff4d4f;color:#fff;border-radius:4px;border:none;")
        self._btn_clear.clicked.connect(self._on_clear)
        tb.addWidget(self._btn_clear)
        tb.addStretch()
        self._count_lbl = QLabel("0 \u6761")
        self._count_lbl.setStyleSheet("font-size:11px;color:#8c8c8c;")
        tb.addWidget(self._count_lbl)
        root.addLayout(tb)
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            "\u65f6\u95f4","\u65b9\u6cd5","\u8def\u5f84",
            "\u72b6\u6001\u7801","\u5ef6\u8fdf(ms)","\u8c03\u7528\u4eba"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        root.addWidget(self._table)

    def refresh(self):
        if not self._engine: return
        method = self._method_combo.currentData()
        pf     = self._path_filter.text().strip()
        logs   = self._engine.api.list_logs(n=200,
                    path_filter=pf, method_filter=method)
        self._table.setRowCount(0)
        for log in logs:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0,
                QTableWidgetItem(log.timestamp.strftime("%H:%M:%S.%f")[:12]))
            mc = METHOD_COLOR.get(log.method, "#8c8c8c")
            mi = QTableWidgetItem(log.method)
            mi.setForeground(QBrush(QColor(mc)))
            self._table.setItem(r, 1, mi)
            self._table.setItem(r, 2, QTableWidgetItem(log.path))
            sc = _status_color(log.status_code)
            si = QTableWidgetItem(str(log.status_code))
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 3, si)
            self._table.setItem(r, 4,
                QTableWidgetItem(f"{log.latency_ms:.1f}"))
            self._table.setItem(r, 5, QTableWidgetItem(log.caller or "\u2014"))
        self._count_lbl.setText(f"{self._table.rowCount()} \u6761")

    def _on_clear(self):
        if not self._engine: return
        self._engine.api._log.clear()
        self.refresh()


class TestConsole(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(8)

        req_grp = QGroupBox("\u8bf7\u6c42\u914d\u7f6e")
        form    = QFormLayout(req_grp)
        method_row = QHBoxLayout()
        self._method_cb = QComboBox()
        for m in ("GET","POST","PUT","DELETE","PATCH"):
            self._method_cb.addItem(m)
        self._method_cb.setFixedWidth(90)
        method_row.addWidget(self._method_cb)
        self._path_in = QLineEdit(); self._path_in.setPlaceholderText("/api/v1/xxx")
        method_row.addWidget(self._path_in, 1)
        form.addRow("\u65b9\u6cd5 + \u8def\u5f84", method_row)
        self._caller_in = QLineEdit(); self._caller_in.setPlaceholderText("console")
        form.addRow("\u8c03\u7528\u6765\u6e90", self._caller_in)
        self._params_in = QPlainTextEdit()
        self._params_in.setPlaceholderText('{\"key\": \"value\"}')
        self._params_in.setFixedHeight(60)
        self._params_in.setFont(QFont("Consolas", 10))
        form.addRow("Params (JSON)", self._params_in)
        self._body_in = QPlainTextEdit()
        self._body_in.setPlaceholderText('{\"data\": ...}')
        self._body_in.setFixedHeight(60)
        self._body_in.setFont(QFont("Consolas", 10))
        form.addRow("Body (JSON)", self._body_in)
        root.addWidget(req_grp)

        btn_row = QHBoxLayout()
        self._btn_send = QPushButton("\u25b6  \u53d1\u9001\u8bf7\u6c42")
        self._btn_send.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;"
            "font-size:13px;padding:4px 16px;")
        self._btn_send.clicked.connect(self._on_send)
        btn_row.addWidget(self._btn_send)
        self._btn_clear = QPushButton("\u6e05\u7a7a")
        self._btn_clear.clicked.connect(self._on_clear_resp)
        btn_row.addWidget(self._btn_clear)
        btn_row.addStretch()
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("font-size:12px;font-weight:bold;")
        btn_row.addWidget(self._status_lbl)
        root.addLayout(btn_row)

        resp_grp = QGroupBox("\u54cd\u5e94")
        rl = QVBoxLayout(resp_grp)
        self._resp_view = QPlainTextEdit(); self._resp_view.setReadOnly(True)
        self._resp_view.setFont(QFont("Consolas", 10))
        rl.addWidget(self._resp_view)
        root.addWidget(resp_grp, 1)

    def set_path(self, path: str):
        if path: self._path_in.setText(path)

    def _on_send(self):
        if not self._engine: return
        import json
        path   = self._path_in.text().strip()
        method = self._method_cb.currentText()
        caller = self._caller_in.text().strip() or "console"
        try:
            params = json.loads(self._params_in.toPlainText() or "{}")
        except Exception:
            params = {}
        try:
            body = json.loads(self._body_in.toPlainText() or "null")
        except Exception:
            body = self._body_in.toPlainText() or None
        resp = self._engine.api.call(path, method, params=params,
                                     body=body, caller=caller)
        color = _status_color(resp.status_code)
        self._status_lbl.setText(f"HTTP {resp.status_code}  {resp.latency_ms:.1f}ms")
        self._status_lbl.setStyleSheet(f"font-size:12px;font-weight:bold;color:{color};")
        out_lines = [
            f"// HTTP {resp.status_code}  latency={resp.latency_ms:.1f}ms",
            f"// request_id={resp.request_id}",
            "",
        ]
        if resp.ok:
            try:
                out_lines.append(json.dumps(resp.data, ensure_ascii=False, indent=2))
            except Exception:
                out_lines.append(str(resp.data))
        else:
            out_lines.append(f"ERROR: {resp.error}")
        self._resp_view.setPlainText("\n".join(out_lines))

    def _on_clear_resp(self):
        self._resp_view.clear()
        self._status_lbl.setText("")


class ApiTab(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(3_000)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12); root.setSpacing(8)
        hdr = QHBoxLayout()
        title = QLabel("\U0001f310  API Gateway")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet("font-size:11px;color:#8c8c8c;")
        hdr.addWidget(self._stats_lbl)
        btn = QPushButton("\U0001f504 \u5237\u65b0")
        btn.setFixedSize(68, 26)
        btn.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;"
            "font-size:12px;border:none;")
        btn.clicked.connect(self._refresh)
        hdr.addWidget(btn)
        root.addLayout(hdr)

        self._stat_panel = StatPanel()
        root.addWidget(self._stat_panel)

        self._sub = QTabWidget(); self._sub.setDocumentMode(True)
        self._route_list  = RouteList(self._engine)
        self._request_log = RequestLog(self._engine)
        self._test_console = TestConsole(self._engine)
        self._route_list.set_select_callback(self._on_route_selected)
        self._sub.addTab(self._route_list,   "\U0001f4cb  \u8def\u7531\u5217\u8868")
        self._sub.addTab(self._request_log,  "\U0001f4dc  \u8bf7\u6c42\u65e5\u5fd7")
        self._sub.addTab(self._test_console, "\U0001f9ea  \u6d4b\u8bd5\u63a7\u5236\u53f0")
        root.addWidget(self._sub, 1)

        self._status = QLabel("\u5c31\u7eea")
        self._status.setStyleSheet("font-size:11px;color:#6c757d;")
        root.addWidget(self._status)

    def _on_route_selected(self, path):
        if path:
            self._test_console.set_path(path)
            self._sub.setCurrentIndex(2)

    def _refresh(self):
        self._route_list.refresh()
        self._request_log.refresh()
        if self._engine:
            s = self._engine.api.stats()
            self._stat_panel.refresh(s)
            self._stats_lbl.setText(
                f"\u8def\u7531: {s.get('routes',0)}"
                f"  \u8bf7\u6c42: {s.get('total_calls',0)}"
                f"  \u9519\u8bef: {s.get('total_errors',0)}")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
