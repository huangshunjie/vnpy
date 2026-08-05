"""
quant_research/ui/pipeline_tab.py  — Phase 9 完整实现
"""
from __future__ import annotations
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QPlainTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from vnpy.event import Event

from ..engine import ResearchEngine
from ..event import (
    EVENT_PIPELINE_CREATED, EVENT_PIPELINE_UPDATED,
    EVENT_PIPELINE_STARTED, EVENT_PIPELINE_COMPLETED, EVENT_PIPELINE_FAILED,
)
from ..constant import PipelineStatus
from ..model.pipeline_model import PipelineRecord, PipelineStepRecord, PipelineRun, STEP_TYPES

COL_ID     = 0
COL_NAME   = 1
COL_STATUS = 2
COL_STEPS  = 3
COL_RUNS   = 4
COL_OK     = 5
COL_FAIL   = 6
COL_SCHED  = 7
COL_LAST   = 8

HEADERS = ["流水线 ID", "名称", "状态", "步骤数",
           "执行次数", "成功", "失败", "调度", "最近执行"]

STATUS_COLORS = {
    PipelineStatus.IDLE:      QColor("#6c757d"),
    PipelineStatus.RUNNING:   QColor("#0d6efd"),
    PipelineStatus.COMPLETED: QColor("#198754"),
    PipelineStatus.FAILED:    QColor("#dc3545"),
    PipelineStatus.PAUSED:    QColor("#fd7e14"),
}


class PipelineCreateDialog(QDialog):
    def __init__(self, parent=None, record: Optional[PipelineRecord] = None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle("编辑流水线" if self._editing else "创建流水线")
        self.setMinimumWidth(500)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp = QGroupBox("流水线信息")
        form = QFormLayout(grp)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("流水线名称（必填）")
        form.addRow("名称 *", self._name_edit)
        self._author_edit = QLineEdit()
        form.addRow("作者", self._author_edit)
        self._schedule_edit = QLineEdit()
        self._schedule_edit.setPlaceholderText("Cron 表达式（可留空）")
        form.addRow("调度", self._schedule_edit)
        self._desc_edit = QPlainTextEdit(); self._desc_edit.setFixedHeight(52)
        form.addRow("描述", self._desc_edit)
        self._tags_edit = QLineEdit(); self._tags_edit.setPlaceholderText("逗号分隔标签")
        form.addRow("标签", self._tags_edit)
        root.addWidget(grp)
        rel_grp = QGroupBox("关联资源（ID）")
        rf = QFormLayout(rel_grp)
        self._exp_edit = QLineEdit(); rf.addRow("关联实验", self._exp_edit)
        self._st_edit  = QLineEdit(); rf.addRow("关联策略", self._st_edit)
        self._ds_edit  = QLineEdit(); self._ds_edit.setPlaceholderText("数据集 ID，逗号分隔")
        rf.addRow("关联数据集", self._ds_edit)
        self._ft_edit  = QLineEdit(); self._ft_edit.setPlaceholderText("因子 ID，逗号分隔")
        rf.addRow("关联因子", self._ft_edit)
        root.addWidget(rel_grp)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load(self):
        r = self._record
        self._name_edit.setText(r.name); self._author_edit.setText(r.author)
        self._schedule_edit.setText(r.schedule); self._desc_edit.setPlainText(r.description)
        self._tags_edit.setText(", ".join(r.tags))
        self._exp_edit.setText(r.experiment_id or ""); self._st_edit.setText(r.strategy_id or "")
        self._ds_edit.setText(", ".join(r.dataset_ids)); self._ft_edit.setText(", ".join(r.feature_ids))

    def _on_accept(self):
        if not self._name_edit.text().strip():
            self._name_edit.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]

    def get_name(self)          -> str:           return self._name_edit.text().strip()
    def get_author(self)        -> str:           return self._author_edit.text().strip()
    def get_schedule(self)      -> str:           return self._schedule_edit.text().strip()
    def get_description(self)   -> str:           return self._desc_edit.toPlainText().strip()
    def get_tags(self)          -> List[str]:     return self._split(self._tags_edit.text())
    def get_experiment_id(self) -> Optional[str]: return self._exp_edit.text().strip() or None
    def get_strategy_id(self)   -> Optional[str]: return self._st_edit.text().strip() or None
    def get_dataset_ids(self)   -> List[str]:     return self._split(self._ds_edit.text())
    def get_feature_ids(self)   -> List[str]:     return self._split(self._ft_edit.text())


class AddStepDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加步骤"); self.setMinimumWidth(420)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self); form = QFormLayout()
        self._name_edit = QLineEdit(); self._name_edit.setPlaceholderText("步骤名称（必填）")
        form.addRow("名称 *", self._name_edit)
        self._type_combo = QComboBox()
        for t in STEP_TYPES: self._type_combo.addItem(t, t)
        form.addRow("步骤类型", self._type_combo)
        self._timeout_edit = QLineEdit("3600"); form.addRow("超时(秒)", self._timeout_edit)
        self._deps_edit = QLineEdit(); self._deps_edit.setPlaceholderText("依赖步骤 ID，逗号分隔")
        form.addRow("依赖步骤", self._deps_edit)
        root.addLayout(form)
        root.addWidget(QLabel("参数（JSON格式）："))
        self._params_edit = QPlainTextEdit(); self._params_edit.setPlaceholderText("{}")
        self._params_edit.setFixedHeight(56); root.addWidget(self._params_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept); buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _on_accept(self):
        if not self._name_edit.text().strip():
            self._name_edit.setFocus(); return
        self.accept()

    def get_name(self)   -> str:       return self._name_edit.text().strip()
    def get_type(self)   -> str:       return self._type_combo.currentData()
    def get_timeout(self) -> int:
        try: return int(self._timeout_edit.text())
        except: return 3600
    def get_deps(self)   -> List[str]:
        return [x.strip() for x in self._deps_edit.text().split(",") if x.strip()]
    def get_params(self) -> dict:
        import json
        try: return json.loads(self._params_edit.toPlainText() or "{}")
        except: return {}


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
        self._rel_edit.setPlainText("\n".join(lines))

    def clear(self):
        self._current = None
        self._ov_table.setRowCount(0); self._step_table.setRowCount(0)
        self._run_table.setRowCount(0); self._rel_edit.clear()


class PipelineTab(QWidget):
    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._all_records: List[PipelineRecord] = []
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(6,6,6,6)
        bar1 = QHBoxLayout()
        self._btn_new    = QPushButton("+ 创建流水线")
        self._btn_edit   = QPushButton("编辑")
        self._btn_delete = QPushButton("删除")
        self._btn_run    = QPushButton("▶ 执行")
        self._btn_done   = QPushButton("标记完成")
        self._btn_fail   = QPushButton("标记失败")
        self._btn_pause  = QPushButton("暂停")
        self._btn_reset  = QPushButton("重置")
        self._btn_step   = QPushButton("+ 添加步骤")
        for btn in (self._btn_new, self._btn_edit, self._btn_delete,
                    self._btn_run, self._btn_done, self._btn_fail,
                    self._btn_pause, self._btn_reset, self._btn_step):
            bar1.addWidget(btn)
        bar1.addStretch(); root.addLayout(bar1)
        bar2 = QHBoxLayout()
        bar2.addWidget(QLabel("状态:"))
        self._status_filter = QComboBox()
        self._status_filter.addItem("全部", None)
        for s in PipelineStatus: self._status_filter.addItem(s.value, s)
        self._status_filter.setFixedWidth(110); bar2.addWidget(self._status_filter)
        bar2.addWidget(QLabel("搜索:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("名称 / 作者")
        self._search_box.setFixedWidth(180); bar2.addWidget(self._search_box)
        self._btn_search2 = QPushButton("搜索"); self._btn_search2.setFixedWidth(52)
        bar2.addWidget(self._btn_search2)
        self._btn_reset2 = QPushButton("重置"); self._btn_reset2.setFixedWidth(52)
        bar2.addWidget(self._btn_reset2)
        bar2.addStretch(); root.addLayout(bar2)
        splitter = QSplitter(Qt.Vertical)
        self._table = QTableWidget(0, len(HEADERS))
        self._table.setHorizontalHeaderLabels(HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(COL_ID, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        splitter.addWidget(self._table)
        self._detail = PipelineDetailPanel(self._engine)
        self._detail.setMinimumHeight(240)
        splitter.addWidget(self._detail)
        splitter.setSizes([320, 280]); root.addWidget(splitter)
        self._status_bar = QLabel("共 0 条流水线"); root.addWidget(self._status_bar)
        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_run.clicked.connect(self._on_run)
        self._btn_done.clicked.connect(self._on_complete)
        self._btn_fail.clicked.connect(self._on_fail)
        self._btn_pause.clicked.connect(self._on_pause)
        self._btn_reset.clicked.connect(self._on_reset)
        self._btn_step.clicked.connect(self._on_add_step)
        self._btn_search2.clicked.connect(self._apply_filter)
        self._btn_reset2.clicked.connect(self._reset_filter)
        self._search_box.returnPressed.connect(self._apply_filter)
        self._status_filter.currentIndexChanged.connect(self._apply_filter)
        self._table.currentCellChanged.connect(self._on_row_changed)
        self._table.doubleClicked.connect(self._on_edit)

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in (EVENT_PIPELINE_CREATED, EVENT_PIPELINE_UPDATED,
                   EVENT_PIPELINE_STARTED, EVENT_PIPELINE_COMPLETED,
                   EVENT_PIPELINE_FAILED):
            ee.register(ev, self._on_event)

    def _on_event(self, event: Event):
        # 使用定时器延迟刷新，避免阻塞UI
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._refresh)

    def _refresh(self):
        self._all_records = self._engine.list_pipelines()
        self._apply_filter()

    def _apply_filter(self):
        status  = self._status_filter.currentData()
        keyword = self._search_box.text().strip()
        records = (self._engine.search_pipelines(keyword) if keyword
                   else self._engine.list_pipelines(status=status))
        self._populate_table(records)

    def _reset_filter(self):
        self._status_filter.setCurrentIndex(0); self._search_box.clear()
        self._populate_table(self._all_records)

    def _populate_table(self, records):
        self._table.setSortingEnabled(False); self._table.setRowCount(0)
        for rec in records:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._set_row(r, rec)
        self._table.setSortingEnabled(True)
        self._status_bar.setText(f"共 {len(records)} 条流水线")

    def _set_row(self, row: int, rec: PipelineRecord):
        id_item = QTableWidgetItem(rec.pipeline_id)
        id_item.setData(Qt.UserRole, rec.pipeline_id)
        self._table.setItem(row, COL_ID, id_item)
        self._table.setItem(row, COL_NAME, QTableWidgetItem(rec.name))
        st_item = QTableWidgetItem(rec.status.value)
        st_item.setForeground(STATUS_COLORS.get(rec.status, QColor("#333")))
        f = QFont(); f.setBold(True); st_item.setFont(f)
        self._table.setItem(row, COL_STATUS, st_item)
        self._table.setItem(row, COL_STEPS, QTableWidgetItem(str(len(rec.steps))))
        self._table.setItem(row, COL_RUNS,  QTableWidgetItem(str(rec.run_count)))
        ok_item = QTableWidgetItem(str(rec.success_count))
        ok_item.setForeground(QColor("#198754") if rec.success_count else QColor("#333"))
        self._table.setItem(row, COL_OK, ok_item)
        fail_item = QTableWidgetItem(str(rec.fail_count))
        fail_item.setForeground(QColor("#dc3545") if rec.fail_count else QColor("#333"))
        self._table.setItem(row, COL_FAIL, fail_item)
        self._table.setItem(row, COL_SCHED, QTableWidgetItem(rec.schedule or "—"))
        last = rec.last_run_at.strftime("%Y-%m-%d %H:%M") if rec.last_run_at else "—"
        self._table.setItem(row, COL_LAST, QTableWidgetItem(last))

    def _on_row_changed(self, cur_row, *_):
        rec = self._get_record_at(cur_row)
        if rec: self._detail.load(rec)
        else:   self._detail.clear()

    def _on_new(self):
        dlg = PipelineCreateDialog(parent=self)
        if dlg.exec() == PipelineCreateDialog.Accepted:
            self._engine.create_pipeline(
                name=dlg.get_name(), description=dlg.get_description(),
                author=dlg.get_author(), schedule=dlg.get_schedule(),
                experiment_id=dlg.get_experiment_id(),
                strategy_id=dlg.get_strategy_id(),
                dataset_ids=dlg.get_dataset_ids(),
                feature_ids=dlg.get_feature_ids(),
                tags=dlg.get_tags(),
            )

    def _on_edit(self):
        rec = self._get_selected_record()
        if not rec: return
        dlg = PipelineCreateDialog(parent=self, record=rec)
        if dlg.exec() == PipelineCreateDialog.Accepted:
            rec.name          = dlg.get_name()
            rec.description   = dlg.get_description()
            rec.author        = dlg.get_author()
            rec.schedule      = dlg.get_schedule()
            rec.experiment_id = dlg.get_experiment_id()
            rec.strategy_id   = dlg.get_strategy_id()
            rec.dataset_ids   = dlg.get_dataset_ids()
            rec.feature_ids   = dlg.get_feature_ids()
            rec.tags          = dlg.get_tags()
            self._engine.update_pipeline(rec)

    def _on_delete(self):
        rec = self._get_selected_record()
        if rec: self._engine.delete_pipeline(rec.pipeline_id)

    def _on_run(self):
        rec = self._get_selected_record()
        if rec: self._engine.run_pipeline(rec.pipeline_id)

    def _on_complete(self):
        rec = self._get_selected_record()
        if rec: self._engine.complete_pipeline(rec.pipeline_id, duration_sec=0.0)

    def _on_fail(self):
        rec = self._get_selected_record()
        if not rec: return
        from PySide6.QtWidgets import QInputDialog
        msg, ok = QInputDialog.getText(self, "标记失败", "错误信息（可留空）：")
        if ok: self._engine.fail_pipeline(rec.pipeline_id, error_msg=msg)

    def _on_pause(self):
        rec = self._get_selected_record()
        if rec: self._engine.pause_pipeline(rec.pipeline_id)

    def _on_reset(self):
        rec = self._get_selected_record()
        if rec: self._engine.reset_pipeline(rec.pipeline_id)

    def _on_add_step(self):
        rec = self._get_selected_record()
        if not rec: return
        dlg = AddStepDialog(parent=self)
        if dlg.exec() == AddStepDialog.Accepted:
            self._engine.add_pipeline_step(
                rec.pipeline_id, name=dlg.get_name(),
                step_type=dlg.get_type(), params=dlg.get_params(),
                depends_on=dlg.get_deps(), timeout_sec=dlg.get_timeout(),
            )

    def _get_record_at(self, row):
        item = self._table.item(row, COL_ID)
        if item is None: return None
        return self._engine.get_pipeline(item.data(Qt.UserRole))

    def _get_selected_record(self):
        return self._get_record_at(self._table.currentRow())


