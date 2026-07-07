"""write_pl_detail.py — PipelineDetail"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\pipeline_tab.py"
)

CODE = """

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
        self._title = QLabel("\\u8bf7\\u9009\\u62e9 Pipeline")
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
        self._c_nodes   = self._card("\\u8282\\u70b9\\u6570",   "0")
        self._c_runs    = self._card("\\u8fd0\\u884c\\u6b21\\u6570", "0")
        self._c_success = self._card("\\u6210\\u529f",     "0", "#198754")
        self._c_fail    = self._card("\\u5931\\u8d25",     "0", "#dc3545")
        for c in (self._c_nodes, self._c_runs, self._c_success, self._c_fail):
            cr.addWidget(c)
        ov_l.addLayout(cr)

        # info table
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\\u5c5e\\u6027","\\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        self._info.setFixedHeight(130)
        ov_l.addWidget(self._info)

        # DAG canvas
        canvas_lbl = QLabel("DAG \\u753b\\u5e03\\uff08\\u53ef\\u62d6\\u62fd\\u8282\\u70b9\\uff09")
        canvas_lbl.setStyleSheet("font-weight:bold;color:#495057;margin-top:4px;")
        ov_l.addWidget(canvas_lbl)
        self._canvas = DAGCanvas()
        self._canvas.node_clicked.connect(self._on_node_click)
        ov_l.addWidget(self._canvas, 1)
        self.addTab(ov, "\\U0001f5fa  \\u6982\\u89c8")

        # ── Tab2: execution runs ───────────────────────────────────
        ex = QWidget(); ex_l = QVBoxLayout(ex)
        self._run_table = QTableWidget(0, 4)
        self._run_table.setHorizontalHeaderLabels([
            "Run ID", "\\u72b6\\u6001", "\\u65f6\\u957f(s)", "\\u5f00\\u59cb\\u65f6\\u95f4"])
        self._run_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._run_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._run_table.setAlternatingRowColors(True)
        self._run_table.verticalHeader().setVisible(False)
        ex_l.addWidget(self._run_table)
        self.addTab(ex, "\\u25b6  \\u6267\\u884c\\u5386\\u53f2")

        # ── Tab3: node detail ─────────────────────────────────────
        nd_w = QWidget(); nd_l = QVBoxLayout(nd_w)
        self._nd_title = QLabel("\\u70b9\\u51fb DAG \\u4e2d\\u7684\\u8282\\u70b9\\u67e5\\u770b\\u8be6\\u60c5")
        self._nd_title.setStyleSheet("font-size:13px;font-weight:bold;color:#495057;")
        nd_l.addWidget(self._nd_title)
        self._nd_table = QTableWidget(0, 2)
        self._nd_table.setHorizontalHeaderLabels(["\\u5c5e\\u6027","\\u503c"])
        self._nd_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._nd_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._nd_table.setAlternatingRowColors(True)
        self._nd_table.verticalHeader().setVisible(False)
        self._nd_table.setFixedHeight(150)
        nd_l.addWidget(self._nd_table)
        log_lbl = QLabel("\\u8282\\u70b9\\u65e5\\u5fd7")
        log_lbl.setStyleSheet("font-weight:bold;color:#495057;margin-top:4px;")
        nd_l.addWidget(log_lbl)
        self._nd_log = QTextEdit()
        self._nd_log.setReadOnly(True)
        self._nd_log.setFont(QFont("Consolas", 9))
        self._nd_log.setStyleSheet(
            "background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;")
        nd_l.addWidget(self._nd_log, 1)
        self.addTab(nd_w, "\\U0001f4cb  \\u8282\\u70b9\\u8be6\\u60c5")

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
        self._title.setText("\\u8bf7\\u9009\\u62e9 Pipeline")
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
        self._nd_title.setText("\\u70b9\\u51fb DAG \\u4e2d\\u7684\\u8282\\u70b9\\u67e5\\u770b\\u8be6\\u60c5")

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
        lr = pl.last_run_at.strftime("%Y-%m-%d %H:%M") if pl.last_run_at else "\\u2014"
        for k, v in [
            ("ID", pl.pipeline_id), ("\\u540d\\u79f0", pl.name),
            ("\\u4f5c\\u8005", pl.author or "\\u2014"),
            ("\\u8c03\\u5ea6", pl.schedule or "\\u2014"),
            ("\\u6807\\u7b7e", ", ".join(pl.tags) if pl.tags else "\\u2014"),
            ("\\u4e0a\\u6b21\\u8fd0\\u884c", lr),
            ("\\u521b\\u5efa", pl.created_at.strftime("%Y-%m-%d %H:%M")),
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
            ("\\u7c7b\\u578b",   nd.node_type.value),
            ("\\u72b6\\u6001",   nd.status.value),
            ("\\u524d\\u7f6e",   ", ".join(nd.depends_on) if nd.depends_on else "\\u2014"),
            ("\\u8d85\\u65f6",   str(nd.timeout_sec) + "s"),
            ("\\u91cd\\u8bd5",   str(nd.retries) + "/" + str(nd.max_retries)),
            ("\\u5f00\\u59cb", nd.started_at.strftime("%H:%M:%S") if nd.started_at else "\\u2014"),
            ("\\u7ed3\\u675f", nd.finished_at.strftime("%H:%M:%S") if nd.finished_at else "\\u2014"),
        ]:
            r = self._nd_table.rowCount(); self._nd_table.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._nd_table.setItem(r, 0, ki)
            vi = QTableWidgetItem(str(v))
            if k == "\\u72b6\\u6001":
                vi.setForeground(QBrush(QColor(sc)))
            self._nd_table.setItem(r, 1, vi)
        self._nd_log.setPlainText(nd.log or "(\\u65e0\\u65e5\\u5fd7)")
        if nd.error_msg:
            self._nd_log.append("\\n[ERROR] " + nd.error_msg)
        self.setCurrentIndex(2)
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("PipelineDetail OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
