"""write_exp_detail.py — RunDetailPanel"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\experiment_tab.py"
)

CODE = """

class RunDetailPanel(QTabWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._run_id  = None
        self._init_ui()

    def _init_ui(self):
        self.setTabPosition(QTabWidget.North)
        self.setDocumentMode(True)

        # ── Tab1: overview ────────────────────────────────────────
        ov_w = QWidget(); ov_l = QVBoxLayout(ov_w)

        # title bar
        tb = QHBoxLayout()
        self._run_title = QLabel("\\u8bf7\\u9009\\u62e9\\u4e00\\u4e2a Run")
        self._run_title.setStyleSheet(
            "font-size:15px;font-weight:bold;color:#1a1f36;")
        tb.addWidget(self._run_title)
        tb.addStretch()
        self._status_badge = QLabel("")
        self._status_badge.setFixedHeight(22)
        self._status_badge.setStyleSheet(
            "padding:2px 10px;border-radius:10px;font-size:12px;")
        tb.addWidget(self._status_badge)
        ov_l.addLayout(tb)

        self._color_bar = QFrame()
        self._color_bar.setFixedHeight(4)
        self._color_bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        ov_l.addWidget(self._color_bar)

        # info table
        self._info_table = QTableWidget(0, 2)
        self._info_table.setHorizontalHeaderLabels(
            ["\\u5c5e\\u6027", "\\u503c"])
        self._info_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._info_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info_table.setAlternatingRowColors(True)
        self._info_table.verticalHeader().setVisible(False)
        self._info_table.setFixedHeight(180)
        ov_l.addWidget(self._info_table)

        # params table
        params_lbl = QLabel("\\u8d85\\u53c2\\u6570")
        params_lbl.setStyleSheet(
            "font-weight:bold;color:#495057;margin-top:6px;")
        ov_l.addWidget(params_lbl)
        self._params_table = QTableWidget(0, 2)
        self._params_table.setHorizontalHeaderLabels(
            ["\\u53c2\\u6570\\u540d", "\\u503c"])
        self._params_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._params_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._params_table.setAlternatingRowColors(True)
        self._params_table.verticalHeader().setVisible(False)
        ov_l.addWidget(self._params_table)
        self.addTab(ov_w, "\\U0001f4cb  \\u6982\\u89c8")

        # ── Tab2: metrics ─────────────────────────────────────────
        mt_w = QWidget(); mt_l = QVBoxLayout(mt_w)

        # summary table (top)
        self._metrics_table = QTableWidget(0, 3)
        self._metrics_table.setHorizontalHeaderLabels(
            ["\\u6307\\u6807", "\\u5f53\\u524d\\u503c", "\\u5386\\u53f2\\u70b9\\u6570"])
        self._metrics_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._metrics_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._metrics_table.setAlternatingRowColors(True)
        self._metrics_table.verticalHeader().setVisible(False)
        self._metrics_table.setFixedHeight(140)
        self._metrics_table.itemClicked.connect(self._on_metric_clicked)
        mt_l.addWidget(self._metrics_table)

        # chart
        chart_lbl = QLabel("\\u6307\\u6807\\u8d70\\u52bf")
        chart_lbl.setStyleSheet(
            "font-weight:bold;color:#495057;margin-top:4px;")
        mt_l.addWidget(chart_lbl)
        self._chart = MetricChart()
        mt_l.addWidget(self._chart, 1)
        self.addTab(mt_w, "\\U0001f4c8  \\u6307\\u6807")

        # ── Tab3: log ─────────────────────────────────────────────
        lg_w = QWidget(); lg_l = QVBoxLayout(lg_w)

        note_lbl = QLabel("\\u5907\\u6ce8")
        note_lbl.setStyleSheet(
            "font-weight:bold;color:#495057;")
        lg_l.addWidget(note_lbl)
        self._note_text = QTextEdit()
        self._note_text.setReadOnly(True)
        self._note_text.setFixedHeight(80)
        lg_l.addWidget(self._note_text)

        err_lbl = QLabel("\\u9519\\u8bef\\u4fe1\\u606f")
        err_lbl.setStyleSheet("font-weight:bold;color:#dc3545;margin-top:6px;")
        lg_l.addWidget(err_lbl)
        self._err_text = QTextEdit()
        self._err_text.setReadOnly(True)
        self._err_text.setFixedHeight(60)
        self._err_text.setStyleSheet(
            "background:#fff5f5;border:1px solid #f5c6cb;border-radius:4px;")
        lg_l.addWidget(self._err_text)

        art_lbl = QLabel("Artifacts")
        art_lbl.setStyleSheet(
            "font-weight:bold;color:#495057;margin-top:6px;")
        lg_l.addWidget(art_lbl)
        self._art_text = QTextEdit()
        self._art_text.setReadOnly(True)
        self._art_text.setFont(QFont("Consolas", 9))
        lg_l.addWidget(self._art_text, 1)
        self.addTab(lg_w, "\\U0001f4cb  \\u65e5\\u5fd7")

    # ── load / clear ──────────────────────────────────────────────

    def load(self, run_id: str):
        self._run_id = run_id
        run = self._engine.get_run(run_id)
        if not run:
            self.clear_panel(); return
        exp = self._engine.get_experiment(run.experiment_id)
        self._load_overview(run, exp)
        self._load_metrics(run, exp)
        self._load_log(run)

    def clear_panel(self):
        self._run_id = None
        self._run_title.setText("\\u8bf7\\u9009\\u62e9\\u4e00\\u4e2a Run")
        self._status_badge.setText("")
        self._status_badge.setStyleSheet("")
        self._color_bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        self._info_table.setRowCount(0)
        self._params_table.setRowCount(0)
        self._metrics_table.setRowCount(0)
        self._chart.clear()
        self._note_text.clear()
        self._err_text.clear()
        self._art_text.clear()

    # ── overview ──────────────────────────────────────────────────

    def _load_overview(self, run: RunRecord, exp):
        self._run_title.setText(run.name)
        sc_map = {
            RunStatus.PENDING:   ("#adb5bd", "Pending"),
            RunStatus.RUNNING:   ("#198754", "Running"),
            RunStatus.COMPLETED: ("#0d6efd", "Completed"),
            RunStatus.FAILED:    ("#dc3545", "Failed"),
            RunStatus.KILLED:    ("#6c757d", "Killed"),
        }
        sc, sl = sc_map.get(run.status, ("#6c757d", run.status.value))
        self._status_badge.setText(sl)
        self._status_badge.setStyleSheet(
            "padding:2px 10px;border-radius:10px;"
            "background:" + sc + "22;color:" + sc + ";"
            "font-size:12px;font-weight:bold;"
            "border:1px solid " + sc + "44;")
        self._color_bar.setStyleSheet("background:" + sc + ";border-radius:2px;")

        self._info_table.setRowCount(0)
        is_best = exp and exp.best_run_id == run.run_id
        dur_str = (str(round(run.duration_sec, 2)) + "s"
                   if run.duration_sec else "\\u2014")
        rows = [
            ("Run ID",          run.run_id),
            ("\\u5b9e\\u9a8c ID", run.experiment_id),
            ("\\u540d\\u79f0",   run.name),
            ("\\u72b6\\u6001",   sl),
            ("\\u6700\\u4f73 Run", "\\u2b50 \\u662f" if is_best else "\\u5426"),
            ("\\u65f6\\u957f",   dur_str),
            ("Git Commit",       run.git_commit or "\\u2014"),
            ("\\u6570\\u636e\\u7248\\u672c", run.data_version or "\\u2014"),
            ("\\u5f00\\u59cb\\u65f6\\u95f4", run.started_at.strftime("%Y-%m-%d %H:%M:%S")
             if run.started_at else "\\u2014"),
            ("\\u7ed3\\u675f\\u65f6\\u95f4", run.finished_at.strftime("%Y-%m-%d %H:%M:%S")
             if run.finished_at else "\\u2014"),
        ]
        for key, val in rows:
            r = self._info_table.rowCount()
            self._info_table.insertRow(r)
            k = QTableWidgetItem(key)
            k.setForeground(QBrush(QColor("#6c757d")))
            self._info_table.setItem(r, 0, k)
            self._info_table.setItem(r, 1, QTableWidgetItem(str(val)))

        self._params_table.setRowCount(0)
        for k, v in (run.params or {}).items():
            r = self._params_table.rowCount()
            self._params_table.insertRow(r)
            self._params_table.setItem(r, 0, QTableWidgetItem(str(k)))
            self._params_table.setItem(r, 1, QTableWidgetItem(str(v)))

    # ── metrics ───────────────────────────────────────────────────

    def _load_metrics(self, run: RunRecord, exp):
        self._metrics_table.setRowCount(0)
        pm = exp.primary_metric if exp else ""
        for key, val in sorted((run.metrics or {}).items()):
            hist = [pt for pt in (run.metric_history or [])
                    if pt.key == key]
            r = self._metrics_table.rowCount()
            self._metrics_table.insertRow(r)
            k_item = QTableWidgetItem(("\\u2b50 " if key == pm else "") + key)
            if key == pm:
                k_item.setForeground(QBrush(QColor("#198754")))
            self._metrics_table.setItem(r, 0, k_item)
            v_item = QTableWidgetItem(str(round(val, 6)))
            self._metrics_table.setItem(r, 1, v_item)
            h_item = QTableWidgetItem(str(len(hist)))
            h_item.setTextAlignment(Qt.AlignCenter)
            self._metrics_table.setItem(r, 2, h_item)

        # auto-show primary metric chart
        if pm and run.metric_history:
            self._show_chart(pm, run)

    def _on_metric_clicked(self, item):
        run = self._engine.get_run(self._run_id) if self._run_id else None
        if not run:
            return
        row = item.row()
        key_item = self._metrics_table.item(row, 0)
        if not key_item:
            return
        key = key_item.text().lstrip("\\u2b50 ").strip()
        self._show_chart(key, run)

    def _show_chart(self, key: str, run: RunRecord):
        pts = [pt for pt in (run.metric_history or []) if pt.key == key]
        if pts:
            self._chart.set_series({key: pts}, title=key)
        else:
            self._chart.set_series(
                {key: [MetricPoint(key=key, value=run.metrics.get(key, 0),
                                   step=1)]},
                title=key + " (\\u65e0\\u5386\\u53f2)")

    # ── log ───────────────────────────────────────────────────────

    def _load_log(self, run: RunRecord):
        self._note_text.setPlainText(run.note or "")
        self._err_text.setPlainText(run.error_msg or "")
        arts = run.artifacts or {}
        lines = []
        for k, v in arts.items():
            lines.append(k + ": " + str(v))
        self._art_text.setPlainText("\\n".join(lines) if lines else "\\u65e0 Artifacts")
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("RunDetailPanel OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
