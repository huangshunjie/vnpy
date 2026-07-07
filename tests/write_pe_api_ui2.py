"""write_pe_api_ui2.py — append RequestLog + TestConsole + ApiTab"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\api.py"
)

CODE = '''

class RequestLog(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._method_combo = QComboBox(); self._method_combo.setFixedHeight(26)
        self._method_combo.addItem("\\u5168\\u90e8\\u65b9\\u6cd5", "")
        for m in ("GET","POST","PUT","DELETE"): self._method_combo.addItem(m, m)
        self._method_combo.currentIndexChanged.connect(self.refresh)
        tb.addWidget(self._method_combo)
        self._path_filter = QLineEdit()
        self._path_filter.setPlaceholderText("\\u8def\\u5f84\\u8fc7\\u6ee4...")
        self._path_filter.setFixedHeight(26)
        self._path_filter.textChanged.connect(self.refresh)
        tb.addWidget(self._path_filter)
        self._btn_clear = QPushButton("\\U0001f5d1 \\u6e05\\u7a7a")
        self._btn_clear.setFixedHeight(26)
        self._btn_clear.setStyleSheet(
            "background:#ff4d4f;color:#fff;border-radius:4px;border:none;")
        self._btn_clear.clicked.connect(self._on_clear)
        tb.addWidget(self._btn_clear)
        tb.addStretch()
        self._count_lbl = QLabel("0 \\u6761")
        self._count_lbl.setStyleSheet("font-size:11px;color:#8c8c8c;")
        tb.addWidget(self._count_lbl)
        root.addLayout(tb)
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            "\\u65f6\\u95f4","\\u65b9\\u6cd5","\\u8def\\u5f84",
            "\\u72b6\\u6001\\u7801","\\u5ef6\\u8fdf(ms)","\\u8c03\\u7528\\u4eba"])
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
            self._table.setItem(r, 5, QTableWidgetItem(log.caller or "\\u2014"))
        self._count_lbl.setText(f"{self._table.rowCount()} \\u6761")

    def _on_clear(self):
        if not self._engine: return
        self._engine.api._log.clear()
        self.refresh()


class TestConsole(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(8)

        req_grp = QGroupBox("\\u8bf7\\u6c42\\u914d\\u7f6e")
        form    = QFormLayout(req_grp)
        method_row = QHBoxLayout()
        self._method_cb = QComboBox()
        for m in ("GET","POST","PUT","DELETE","PATCH"):
            self._method_cb.addItem(m)
        self._method_cb.setFixedWidth(90)
        method_row.addWidget(self._method_cb)
        self._path_in = QLineEdit(); self._path_in.setPlaceholderText("/api/v1/xxx")
        method_row.addWidget(self._path_in, 1)
        form.addRow("\\u65b9\\u6cd5 + \\u8def\\u5f84", method_row)
        self._caller_in = QLineEdit(); self._caller_in.setPlaceholderText("console")
        form.addRow("\\u8c03\\u7528\\u6765\\u6e90", self._caller_in)
        self._params_in = QPlainTextEdit()
        self._params_in.setPlaceholderText(\'{\\"key\\": \\"value\\"}\')
        self._params_in.setFixedHeight(60)
        self._params_in.setFont(QFont("Consolas", 10))
        form.addRow("Params (JSON)", self._params_in)
        self._body_in = QPlainTextEdit()
        self._body_in.setPlaceholderText(\'{\\"data\\": ...}\')
        self._body_in.setFixedHeight(60)
        self._body_in.setFont(QFont("Consolas", 10))
        form.addRow("Body (JSON)", self._body_in)
        root.addWidget(req_grp)

        btn_row = QHBoxLayout()
        self._btn_send = QPushButton("\\u25b6  \\u53d1\\u9001\\u8bf7\\u6c42")
        self._btn_send.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;"
            "font-size:13px;padding:4px 16px;")
        self._btn_send.clicked.connect(self._on_send)
        btn_row.addWidget(self._btn_send)
        self._btn_clear = QPushButton("\\u6e05\\u7a7a")
        self._btn_clear.clicked.connect(self._on_clear_resp)
        btn_row.addWidget(self._btn_clear)
        btn_row.addStretch()
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("font-size:12px;font-weight:bold;")
        btn_row.addWidget(self._status_lbl)
        root.addLayout(btn_row)

        resp_grp = QGroupBox("\\u54cd\\u5e94")
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
        self._resp_view.setPlainText("\\n".join(out_lines))

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
        title = QLabel("\\U0001f310  API Gateway")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet("font-size:11px;color:#8c8c8c;")
        hdr.addWidget(self._stats_lbl)
        btn = QPushButton("\\U0001f504 \\u5237\\u65b0")
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
        self._sub.addTab(self._route_list,   "\\U0001f4cb  \\u8def\\u7531\\u5217\\u8868")
        self._sub.addTab(self._request_log,  "\\U0001f4dc  \\u8bf7\\u6c42\\u65e5\\u5fd7")
        self._sub.addTab(self._test_console, "\\U0001f9ea  \\u6d4b\\u8bd5\\u63a7\\u5236\\u53f0")
        root.addWidget(self._sub, 1)

        self._status = QLabel("\\u5c31\\u7eea")
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
                f"\\u8def\\u7531: {s.get('routes',0)}"
                f"  \\u8bf7\\u6c42: {s.get('total_calls',0)}"
                f"  \\u9519\\u8bef: {s.get('total_errors',0)}")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("ApiTab OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
