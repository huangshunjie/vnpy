"""write_exp_compare.py — ComparePanel + ExperimentTab main class"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\experiment_tab.py"
)

CODE = """

class ComparePanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._run_ids: List[str] = []
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        hdr = QHBoxLayout()
        lbl = QLabel("\\u591a Run \\u5bf9\\u6bd4")
        lbl.setStyleSheet("font-weight:bold;color:#1a1f36;font-size:13px;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        self._clear_btn = QPushButton("\\u6e05\\u7a7a")
        self._clear_btn.setFixedSize(52, 24)
        self._clear_btn.clicked.connect(self.clear_panel)
        hdr.addWidget(self._clear_btn)
        root.addLayout(hdr)

        self._hint = QLabel(
            "\\u5728\\u5de6\\u4fa7\\u70b9\\u51fb Run \\u8282\\u70b9\\u5c06\\u5176\\u52a0\\u5165\\u5bf9\\u6bd4\\uff0c"
            "\\u7136\\u540e\\u70b9\\u51fb\\u300e\\u5bf9\\u6bd4\\u9009\\u4e2d Run\\u300f")
        self._hint.setStyleSheet("color:#6c757d;font-size:11px;")
        self._hint.setWordWrap(True)
        root.addWidget(self._hint)

        self._table = QTableWidget(0, 0)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        root.addWidget(self._table, 1)

        # multi-metric chart
        chart_lbl = QLabel("\\u5bf9\\u6bd4\\u6307\\u6807\\u8d70\\u52bf")
        chart_lbl.setStyleSheet(
            "font-weight:bold;color:#495057;margin-top:4px;")
        root.addWidget(chart_lbl)
        self._chart = MetricChart()
        self._chart.setFixedHeight(180)
        root.addWidget(self._chart)

    def load_runs(self, run_ids: List[str]):
        self._run_ids = run_ids
        self._rebuild()

    def clear_panel(self):
        self._run_ids = []
        self._table.setRowCount(0)
        self._table.setColumnCount(0)
        self._chart.clear()

    def _rebuild(self):
        if not self._run_ids:
            return
        runs = [self._engine.get_run(rid) for rid in self._run_ids]
        runs = [r for r in runs if r]
        if not runs:
            return

        # collect all metric keys
        all_keys = sorted({k for r in runs for k in (r.metrics or {})})

        # build table: rows=metrics, cols=params header + run names
        n_runs = len(runs)
        self._table.setRowCount(len(all_keys) + len(runs[0].params or {}))
        self._table.setColumnCount(n_runs + 1)

        headers = ["\\u6307\\u6807 / \\u53c2\\u6570"] + [r.name for r in runs]
        self._table.setHorizontalHeaderLabels(headers)

        # find best values per metric (higher = better heuristic: just find max)
        best_vals: Dict[str, float] = {}
        worst_vals: Dict[str, float] = {}
        for key in all_keys:
            vals = [r.metrics[key] for r in runs if key in (r.metrics or {})]
            if vals:
                best_vals[key]  = max(vals)
                worst_vals[key] = min(vals)

        row = 0
        # metrics section
        sec_lbl = QTableWidgetItem("\\u2014 \\u6307\\u6807 \\u2014")
        sec_lbl.setBackground(QBrush(QColor("#f0f4ff")))
        sec_lbl.setForeground(QBrush(QColor("#4a6cf7")))
        f = QFont(); f.setBold(True); sec_lbl.setFont(f)
        self._table.setItem(row, 0, sec_lbl)
        for c in range(1, n_runs + 1):
            self._table.setItem(row, c, QTableWidgetItem(""))
        row += 1

        for key in all_keys:
            k_item = QTableWidgetItem(key)
            k_item.setForeground(QBrush(QColor("#495057")))
            self._table.setItem(row, 0, k_item)
            for c, run in enumerate(runs, 1):
                val = (run.metrics or {}).get(key)
                if val is None:
                    self._table.setItem(row, c, QTableWidgetItem("\\u2014"))
                else:
                    cell = QTableWidgetItem(str(round(val, 6)))
                    cell.setTextAlignment(Qt.AlignCenter)
                    if val == best_vals.get(key):
                        cell.setBackground(QBrush(QColor("#d1e7dd")))
                        cell.setForeground(QBrush(QColor("#0a3622")))
                    elif val == worst_vals.get(key):
                        cell.setBackground(QBrush(QColor("#f8d7da")))
                        cell.setForeground(QBrush(QColor("#58151c")))
                    self._table.setItem(row, c, cell)
            row += 1

        # params section
        if runs[0].params:
            sec_lbl2 = QTableWidgetItem("\\u2014 \\u53c2\\u6570 \\u2014")
            sec_lbl2.setBackground(QBrush(QColor("#f0f4ff")))
            sec_lbl2.setForeground(QBrush(QColor("#4a6cf7")))
            sec_lbl2.setFont(f)
            self._table.setItem(row, 0, sec_lbl2)
            for c in range(1, n_runs + 1):
                self._table.setItem(row, c, QTableWidgetItem(""))
            row += 1
            all_param_keys = sorted({k for r in runs for k in (r.params or {})})
            for pk in all_param_keys:
                self._table.setItem(row, 0, QTableWidgetItem(pk))
                for c, run in enumerate(runs, 1):
                    pv = (run.params or {}).get(pk, "\\u2014")
                    cell = QTableWidgetItem(str(pv))
                    cell.setTextAlignment(Qt.AlignCenter)
                    self._table.setItem(row, c, cell)
                row += 1

        self._table.setRowCount(row)

        # update chart: show primary metric history across runs
        exp_id = runs[0].experiment_id
        exp    = self._engine.get_experiment(exp_id)
        pm     = exp.primary_metric if exp else ""
        if pm:
            series = {}
            for run in runs:
                pts = [pt for pt in (run.metric_history or []) if pt.key == pm]
                if pts:
                    series[run.name] = pts
            if series:
                self._chart.set_series(series, title=pm + " \\u5bf9\\u6bd4")
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("ComparePanel OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
