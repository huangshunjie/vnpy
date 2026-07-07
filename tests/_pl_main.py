"""Append PipelineTab main class"""
import pathlib
P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\ui\pipeline_tab.py"
)

MAIN_TAB = """

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

    def _on_event(self, event: Event): self._refresh()

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
"""

txt = P.read_text(encoding="utf-8")
txt = txt.replace("# PLACEHOLDER_PL_MAIN", MAIN_TAB)
P.write_text(txt, encoding="utf-8")
print("PipelineTab main appended OK, size:", P.stat().st_size)
