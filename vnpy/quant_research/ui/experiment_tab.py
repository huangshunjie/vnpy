"""
quant_research/ui/experiment_tab.py

ExperimentTab — Phase 2 完整实现。
"""
from __future__ import annotations

import csv
import io
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QCheckBox, QApplication,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from vnpy.event import Event

from ..engine import ResearchEngine
from ..constant import ExperimentStatus
from ..event import (
    EVENT_EXPERIMENT_CREATED,
    EVENT_EXPERIMENT_UPDATED,
    EVENT_EXPERIMENT_DELETED,
)
from ..model.experiment_model import ExperimentRecord
from .experiment_dialogs import ExperimentCreateDialog, ExperimentCompareDialog


STATUS_COLORS = {
    ExperimentStatus.DRAFT:     QColor("#6c757d"),
    ExperimentStatus.RUNNING:   QColor("#0d6efd"),
    ExperimentStatus.COMPLETED: QColor("#198754"),
    ExperimentStatus.FAILED:    QColor("#dc3545"),
    ExperimentStatus.ARCHIVED:  QColor("#adb5bd"),
}

COL_STAR   = 0
COL_ID     = 1
COL_NAME   = 2
COL_STATUS = 3
COL_TAGS   = 4
COL_AUTHOR = 5
COL_TIME   = 6

HEADERS = ["☆", "实验 ID", "名称", "状态", "标签", "创建人", "创建时间"]


class ExperimentDetailPanel(QTabWidget):
    """底部详情面板：概览 / 参数 / 备注。"""

    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._current: Optional[ExperimentRecord] = None
        self._init_ui()

    def _init_ui(self):
        overview_w = QWidget()
        ov = QVBoxLayout(overview_w)
        self._overview_table = QTableWidget(0, 2)
        self._overview_table.setHorizontalHeaderLabels(["指标", "值"])
        self._overview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._overview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._overview_table.setAlternatingRowColors(True)
        ov.addWidget(self._overview_table)
        self.addTab(overview_w, "概览")

        params_w = QWidget()
        pm = QVBoxLayout(params_w)
        self._params_table = QTableWidget(0, 2)
        self._params_table.setHorizontalHeaderLabels(["参数名", "值"])
        self._params_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._params_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._params_table.setAlternatingRowColors(True)
        pm.addWidget(self._params_table)
        self.addTab(params_w, "参数")

        notes_w = QWidget()
        nt = QVBoxLayout(notes_w)
        self._notes_edit = QTextEdit()
        self._notes_edit.setPlaceholderText("暂无备注")
        nt.addWidget(self._notes_edit)
        save_btn = QPushButton("保存备注")
        save_btn.clicked.connect(self._save_note)
        nt.addWidget(save_btn)
        self.addTab(notes_w, "备注")

    def load(self, record: ExperimentRecord):
        self._current = record
        self._overview_table.setRowCount(0)
        rows = [
            ("ID",       record.experiment_id),
            ("名称",     record.name),
            ("状态",     record.status.value),
            ("标签",     ", ".join(record.tags)),
            ("创建人",   record.created_by),
            ("创建时间", record.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("更新时间", record.updated_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("描述",     record.description),
        ]
        for k, v in record.metrics.items():
            rows.append((f"[metric] {k}", f"{v:.6g}"))
        for k_row, v_row in rows:
            r = self._overview_table.rowCount()
            self._overview_table.insertRow(r)
            self._overview_table.setItem(r, 0, QTableWidgetItem(str(k_row)))
            self._overview_table.setItem(r, 1, QTableWidgetItem(str(v_row)))

        self._params_table.setRowCount(0)
        for k, v in record.params.items():
            r = self._params_table.rowCount()
            self._params_table.insertRow(r)
            self._params_table.setItem(r, 0, QTableWidgetItem(str(k)))
            self._params_table.setItem(r, 1, QTableWidgetItem(str(v)))

        self._notes_edit.setPlainText(record.notes)

    def clear(self):
        self._current = None
        self._overview_table.setRowCount(0)
        self._params_table.setRowCount(0)
        self._notes_edit.clear()

    def _save_note(self):
        if self._current:
            self._engine.add_note(
                self._current.experiment_id,
                self._notes_edit.toPlainText()
            )


class ExperimentTab(QWidget):
    """实验中心主 Tab。"""

    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._all_records: List[ExperimentRecord] = []
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        bar1 = QHBoxLayout()
        self._btn_new     = QPushButton('+ 新建实验')
        self._btn_edit    = QPushButton('编辑')
        self._btn_delete  = QPushButton('删除')
        self._btn_star    = QPushButton('收藏/取消')
        self._btn_compare = QPushButton('对比选中')
        self._btn_export  = QPushButton('导出 CSV')
        for btn in (self._btn_new, self._btn_edit, self._btn_delete,
                    self._btn_star, self._btn_compare, self._btn_export):
            bar1.addWidget(btn)
        bar1.addStretch()
        root.addLayout(bar1)

        bar2 = QHBoxLayout()
        bar2.addWidget(QLabel('状态:'))
        self._status_filter = QComboBox()
        self._status_filter.addItem('全部', None)
        for s in ExperimentStatus:
            self._status_filter.addItem(s.value, s)
        self._status_filter.setFixedWidth(120)
        bar2.addWidget(self._status_filter)
        self._starred_filter = QCheckBox('仅显示收藏')
        bar2.addWidget(self._starred_filter)
        bar2.addWidget(QLabel('搜索:'))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText('名称 / 标签 / 描述')
        self._search_box.setFixedWidth(200)
        bar2.addWidget(self._search_box)
        self._btn_search = QPushButton('搜索')
        self._btn_search.setFixedWidth(52)
        bar2.addWidget(self._btn_search)
        self._btn_reset = QPushButton('重置')
        self._btn_reset.setFixedWidth(52)
        bar2.addWidget(self._btn_reset)
        bar2.addStretch()
        root.addLayout(bar2)

        splitter = QSplitter(Qt.Vertical)

        self._table = QTableWidget(0, len(HEADERS))
        self._table.setHorizontalHeaderLabels(HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(COL_ID,   QHeaderView.ResizeToContents)
        self._table.setColumnWidth(COL_STAR, 32)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        splitter.addWidget(self._table)

        self._detail = ExperimentDetailPanel(self._engine)
        self._detail.setMinimumHeight(180)
        splitter.addWidget(self._detail)
        splitter.setSizes([420, 220])
        root.addWidget(splitter)

        self._status_bar = QLabel('共 0 条实验')
        root.addWidget(self._status_bar)

        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_star.clicked.connect(self._on_star)
        self._btn_compare.clicked.connect(self._on_compare)
        self._btn_export.clicked.connect(self._on_export)
        self._btn_search.clicked.connect(self._apply_filter)
        self._btn_reset.clicked.connect(self._reset_filter)
        self._search_box.returnPressed.connect(self._apply_filter)
        self._status_filter.currentIndexChanged.connect(self._apply_filter)
        self._starred_filter.stateChanged.connect(self._apply_filter)
        self._table.currentCellChanged.connect(self._on_row_changed)
        self._table.doubleClicked.connect(self._on_edit)

    def _register_events(self):
        ee = self._engine.event_engine
        ee.register(EVENT_EXPERIMENT_CREATED, self._on_event)
        ee.register(EVENT_EXPERIMENT_UPDATED, self._on_event)
        ee.register(EVENT_EXPERIMENT_DELETED, self._on_event)

    def _on_event(self, event: Event):
        self._refresh()

    def _refresh(self):
        self._all_records = self._engine.list_experiments()
        self._apply_filter()

    def _apply_filter(self):
        status  = self._status_filter.currentData()
        starred = True if self._starred_filter.isChecked() else None
        keyword = self._search_box.text().strip()
        if keyword:
            records = self._engine.search_experiments(keyword)
        else:
            records = self._engine.list_experiments(status=status, starred=starred)
        self._populate_table(records)

    def _reset_filter(self):
        self._status_filter.setCurrentIndex(0)
        self._starred_filter.setChecked(False)
        self._search_box.clear()
        self._populate_table(self._all_records)

    def _populate_table(self, records: List[ExperimentRecord]):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        for rec in records:
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._set_row(r, rec)
        self._table.setSortingEnabled(True)
        self._status_bar.setText(f'共 {len(records)} 条实验')

    def _set_row(self, row: int, rec: ExperimentRecord):
        star_item = QTableWidgetItem('★' if rec.starred else '☆')
        star_item.setTextAlignment(Qt.AlignCenter)
        star_item.setForeground(QColor('#f5a623') if rec.starred else QColor('#888'))
        star_item.setData(Qt.UserRole, rec.experiment_id)
        self._table.setItem(row, COL_STAR, star_item)
        self._table.setItem(row, COL_ID,   QTableWidgetItem(rec.experiment_id))
        self._table.setItem(row, COL_NAME, QTableWidgetItem(rec.name))
        status_item = QTableWidgetItem(rec.status.value)
        status_item.setForeground(STATUS_COLORS.get(rec.status, QColor('#333')))
        f = QFont(); f.setBold(True); status_item.setFont(f)
        self._table.setItem(row, COL_STATUS, status_item)
        self._table.setItem(row, COL_TAGS,   QTableWidgetItem(', '.join(rec.tags)))
        self._table.setItem(row, COL_AUTHOR, QTableWidgetItem(rec.created_by))
        self._table.setItem(row, COL_TIME,
            QTableWidgetItem(rec.created_at.strftime('%Y-%m-%d %H:%M')))

    def _on_row_changed(self, cur_row, *_):
        rec = self._get_record_at(cur_row)
        if rec:
            self._detail.load(rec)
        else:
            self._detail.clear()

    def _on_new(self):
        dlg = ExperimentCreateDialog(parent=self)
        if dlg.exec() == ExperimentCreateDialog.Accepted:
            self._engine.create_experiment(
                name=dlg.get_name(), description=dlg.get_description(),
                tags=dlg.get_tags(), params=dlg.get_params(),
                created_by=dlg.get_author(), parent_id=dlg.get_parent_id(),
            )

    def _on_edit(self):
        rec = self._get_selected_record()
        if not rec:
            return
        dlg = ExperimentCreateDialog(parent=self, record=rec)
        if dlg.exec() == ExperimentCreateDialog.Accepted:
            rec.name = dlg.get_name()
            rec.description = dlg.get_description()
            rec.status = dlg.get_status()
            rec.tags = dlg.get_tags()
            rec.params = dlg.get_params()
            rec.notes = dlg.get_notes()
            rec.created_by = dlg.get_author()
            rec.parent_id = dlg.get_parent_id()
            self._engine.update_experiment(rec)

    def _on_delete(self):
        rec = self._get_selected_record()
        if rec:
            self._engine.delete_experiment(rec.experiment_id)

    def _on_star(self):
        rec = self._get_selected_record()
        if rec:
            self._engine.star_experiment(rec.experiment_id, not rec.starred)

    def _on_compare(self):
        records = self._get_selected_records()
        if len(records) >= 2:
            ExperimentCompareDialog(records, parent=self).exec()

    def _on_export(self):
        records = self._all_records
        if not records:
            return
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=[
            'experiment_id', 'name', 'status', 'tags',
            'created_by', 'created_at', 'metrics'])
        writer.writeheader()
        for r in records:
            writer.writerow({
                'experiment_id': r.experiment_id,
                'name':          r.name,
                'status':        r.status.value,
                'tags':          '|'.join(r.tags),
                'created_by':    r.created_by,
                'created_at':    r.created_at.isoformat(),
                'metrics':       str(r.metrics),
            })
        QApplication.clipboard().setText(buf.getvalue())

    def _get_record_at(self, row: int) -> Optional[ExperimentRecord]:
        item = self._table.item(row, COL_STAR)
        if item is None:
            return None
        return self._engine.get_experiment(item.data(Qt.UserRole))

    def _get_selected_record(self) -> Optional[ExperimentRecord]:
        return self._get_record_at(self._table.currentRow())

    def _get_selected_records(self) -> List[ExperimentRecord]:
        rows = {idx.row() for idx in self._table.selectedIndexes()}
        result = []
        for r in rows:
            rec = self._get_record_at(r)
            if rec:
                result.append(rec)
        return result
