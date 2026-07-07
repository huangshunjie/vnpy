"""Append PipelineDetailPanel to pipeline_tab.py"""
import pathlib
P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\ui\pipeline_tab.py"
)

DETAIL = """

class PipelineDetailPanel(QTabWidget):
    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._current = None
        self._init_ui()

    def _init_ui(self):
        ov_w = QWidget(); ov_l = QVBoxLayout(ov_w)
        self._ov_table = QTableWidget(0, 2)
        self._ov_table.setHorizontalHeaderLabels(["属性", "值"])
        self._ov_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._ov_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ov_table.setAlternatingRowColors(True)
        ov_l.addWidget(self._ov_table)
        self.addTab(ov_w, "概览")

        step_w = QWidget(); step_l = QVBoxLayout(step_w)
        self._step_table = QTableWidget(0, 6)
        self._step_table.setHorizontalHeaderLabels(
            ["步骤 ID","名称","类型","顺序","状态","依赖"])
        self._step_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._step_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._step_table.setAlternatingRowColors(True)
        step_l.addWidget(self._step_table)
        self.addTab(step_w, "步骤")

        run_w = QWidget(); run_l = QVBoxLayout(run_w)
        self._run_table = QTableWidget(0, 6)
        self._run_table.setHorizontalHeaderLabels(
            ["Run ID","状态","触发方式","耗时(s)","开始时间","错误信息"])
        self._run_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self._run_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._run_table.setAlternatingRowColors(True)
        run_l.addWidget(self._run_table)
        self.addTab(run_w, "执行历史")

        rel_w = QWidget(); rel_l = QVBoxLayout(rel_w)
        self._rel_edit = QTextEdit()
        self._rel_edit.setReadOnly(True)
        self._rel_edit.setFont(QFont("Consolas", 10))
        rel_l.addWidget(self._rel_edit)
        self.addTab(rel_w, "关联资源")

    def load(self, record):
        self._current = record
        self._load_ov(record); self._load_steps(record)
        self._load_runs(record); self._load_relations(record)

    def _load_ov(self, r):
        self._ov_table.setRowCount(0)
        rows = [
            ("ID", r.pipeline_id), ("名称", r.name), ("状态", r.status.value),
            ("作者", r.author), ("步骤数", str(len(r.steps))),
            ("执行次数", str(r.run_count)), ("成功", str(r.success_count)),
            ("失败", str(r.fail_count)), ("调度", r.schedule or "手动"),
            ("标签", ", ".join(r.tags)),
            ("创建时间", r.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("更新时间", r.updated_at.strftime("%Y-%m-%d %H:%M:%S")),
        ]
        if r.last_run_at:
            rows.append(("最近执行", r.last_run_at.strftime("%Y-%m-%d %H:%M")))
        rows.append(("描述", r.description))
        for k, v in rows:
            row = self._ov_table.rowCount(); self._ov_table.insertRow(row)
            self._ov_table.setItem(row, 0, QTableWidgetItem(k))
            self._ov_table.setItem(row, 1, QTableWidgetItem(str(v)))

    def _load_steps(self, r):
        self._step_table.setRowCount(0)
        SC = {"idle":"#6c757d","running":"#0d6efd","completed":"#198754","failed":"#dc3545"}
        for step in sorted(r.steps, key=lambda s: s.order):
            row = self._step_table.rowCount(); self._step_table.insertRow(row)
            self._step_table.setItem(row, 0, QTableWidgetItem(step.step_id))
            self._step_table.setItem(row, 1, QTableWidgetItem(step.name))
            self._step_table.setItem(row, 2, QTableWidgetItem(step.step_type))
            self._step_table.setItem(row, 3, QTableWidgetItem(str(step.order)))
            st = QTableWidgetItem(step.status)
            st.setForeground(QColor(SC.get(step.status, "#333")))
            self._step_table.setItem(row, 4, st)
            self._step_table.setItem(row, 5, QTableWidgetItem(", ".join(step.depends_on)))

    def _load_runs(self, r):
        self._run_table.setRowCount(0)
        RC = {"completed":"#198754","failed":"#dc3545","running":"#0d6efd"}
        for run in reversed(r.runs):
            row = self._run_table.rowCount(); self._run_table.insertRow(row)
            st = QTableWidgetItem(run.status)
            st.setForeground(QColor(RC.get(run.status, "#333")))
            self._run_table.setItem(row, 0, QTableWidgetItem(run.run_id))
            self._run_table.setItem(row, 1, st)
            self._run_table.setItem(row, 2, QTableWidgetItem(run.trigger))
            self._run_table.setItem(row, 3, QTableWidgetItem(f"{run.duration_sec:.1f}"))
            self._run_table.setItem(row, 4, QTableWidgetItem(run.started_at.strftime("%Y-%m-%d %H:%M")))
            self._run_table.setItem(row, 5, QTableWidgetItem(run.error_msg))

    def _load_relations(self, r):
        lines = []
        for label, rid, getter in [
            ("■ 关联实验", r.experiment_id, self._engine.get_experiment),
            ("■ 关联策略", r.strategy_id,   self._engine.get_strategy),
        ]:
            obj = getter(rid) if rid else None
            name = obj.name if obj else (rid or "无")
            lines.append(f"{label}：{rid + '  ' + name if rid else '无'}")
        lines.append("")
        for label, ids, getter in [
            ("■ 关联数据集", r.dataset_ids, self._engine.get_dataset),
            ("■ 关联因子",   r.feature_ids, self._engine.get_feature),
        ]:
            lines.append(f"{label}：" + ("" if ids else "无"))
            for rid in ids:
                obj = getter(rid); name = obj.name if obj else rid
                lines.append(f"  ├─ {rid}  {name}")
            lines.append("")
        self._rel_edit.setPlainText("\\n".join(lines))

    def clear(self):
        self._current = None
        self._ov_table.setRowCount(0); self._step_table.setRowCount(0)
        self._run_table.setRowCount(0); self._rel_edit.clear()
# PLACEHOLDER_PL_MAIN
"""

txt = P.read_text(encoding="utf-8")
txt = txt.replace("# PLACEHOLDER_PL_DETAIL", DETAIL)
P.write_text(txt, encoding="utf-8")
print("PipelineDetailPanel appended OK, size:", P.stat().st_size)
