"""
quant_research/ui/dataset_tab.py

DatasetTab — Phase 3 完整实现。
"""
from __future__ import annotations
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QProgressBar,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from vnpy.event import Event

from ..engine import ResearchEngine
from ..constant import DatasetStatus
from ..event import (
    EVENT_DATASET_CREATED,
    EVENT_DATASET_UPDATED,
    EVENT_DATASET_DELETED,
)
from ..model.dataset_model import DatasetRecord, DatasetSnapshot
from .dataset_dialogs import DatasetCreateDialog


STATUS_COLORS = {
    DatasetStatus.PENDING:  QColor("#6c757d"),
    DatasetStatus.READY:    QColor("#198754"),
    DatasetStatus.OUTDATED: QColor("#fd7e14"),
    DatasetStatus.ERROR:    QColor("#dc3545"),
}

COL_ID      = 0
COL_NAME    = 1
COL_VERSION = 2
COL_STATUS  = 3
COL_SOURCE  = 4
COL_ROWS    = 5
COL_QUALITY = 6
COL_TIME    = 7

HEADERS = ["数据集 ID", "名称", "版本", "状态", "来源", "行数", "质量", "更新时间"]


class DatasetDetailPanel(QTabWidget):
    """底部详情面板：概览 / 字段 / 快照 / 依赖血缘 / 质量。"""

    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._current: Optional[DatasetRecord] = None
        self._init_ui()

    def _init_ui(self):
        # ── 概览 ──────────────────────────────────────────────────────
        ov_w = QWidget()
        ov_l = QVBoxLayout(ov_w)
        self._overview_table = QTableWidget(0, 2)
        self._overview_table.setHorizontalHeaderLabels(["属性", "值"])
        self._overview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._overview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._overview_table.setAlternatingRowColors(True)
        ov_l.addWidget(self._overview_table)
        self.addTab(ov_w, "概览")

        # ── 字段 ──────────────────────────────────────────────────────
        fd_w = QWidget()
        fd_l = QVBoxLayout(fd_w)
        self._fields_table = QTableWidget(0, 2)
        self._fields_table.setHorizontalHeaderLabels(["序号", "字段名"])
        self._fields_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._fields_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._fields_table.setAlternatingRowColors(True)
        fd_l.addWidget(self._fields_table)
        self.addTab(fd_w, "字段")

        # ── 快照历史 ──────────────────────────────────────────────────
        sn_w = QWidget()
        sn_l = QVBoxLayout(sn_w)
        self._snap_table = QTableWidget(0, 5)
        self._snap_table.setHorizontalHeaderLabels(
            ["快照 ID", "版本", "行数", "质量", "时间"])
        self._snap_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._snap_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._snap_table.setAlternatingRowColors(True)
        sn_l.addWidget(self._snap_table)
        self.addTab(sn_w, "快照")

        # ── 依赖 & 血缘 ───────────────────────────────────────────────
        ln_w = QWidget()
        ln_l = QVBoxLayout(ln_w)
        self._lineage_edit = QTextEdit()
        self._lineage_edit.setReadOnly(True)
        self._lineage_edit.setPlaceholderText("选择数据集后显示血缘链路")
        self._lineage_edit.setFont(QFont("Consolas", 10))
        ln_l.addWidget(self._lineage_edit)
        self.addTab(ln_w, "依赖 & 血缘")

        # ── 质量 ──────────────────────────────────────────────────────
        ql_w = QWidget()
        ql_l = QVBoxLayout(ql_w)
        self._quality_label = QLabel("质量得分：—")
        self._quality_label.setFont(QFont("", 14))
        self._quality_bar = QProgressBar()
        self._quality_bar.setRange(0, 100)
        self._quality_bar.setTextVisible(True)
        self._quality_metrics_table = QTableWidget(0, 2)
        self._quality_metrics_table.setHorizontalHeaderLabels(["指标", "值"])
        self._quality_metrics_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._quality_metrics_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._quality_metrics_table.setAlternatingRowColors(True)
        ql_l.addWidget(self._quality_label)
        ql_l.addWidget(self._quality_bar)
        ql_l.addWidget(self._quality_metrics_table)
        self.addTab(ql_w, "质量")

    def load(self, record: DatasetRecord):
        self._current = record
        self._load_overview(record)
        self._load_fields(record)
        self._load_snapshots(record)
        self._load_lineage(record)
        self._load_quality(record)

    def _load_overview(self, r: DatasetRecord):
        self._overview_table.setRowCount(0)
        rows = [
            ("ID",       r.dataset_id),
            ("名称",     r.name),
            ("版本",     r.version),
            ("状态",     r.status.value),
            ("来源",     r.source),
            ("标的数",   str(len(r.symbols))),
            ("字段数",   str(len(r.fields))),
            ("行数",     f"{r.row_count:,}"),
            ("大小",     f"{r.size_mb:.2f} MB"),
            ("开始日期", r.start_date),
            ("结束日期", r.end_date),
            ("标签",     ", ".join(r.tags)),
            ("创建人",   r.created_by),
            ("创建时间", r.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("更新时间", r.updated_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("描述",     r.description),
        ]
        for k, v in rows:
            row = self._overview_table.rowCount()
            self._overview_table.insertRow(row)
            self._overview_table.setItem(row, 0, QTableWidgetItem(k))
            self._overview_table.setItem(row, 1, QTableWidgetItem(v))

    def _load_fields(self, r: DatasetRecord):
        self._fields_table.setRowCount(0)
        for i, f in enumerate(r.fields):
            self._fields_table.insertRow(i)
            self._fields_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self._fields_table.setItem(i, 1, QTableWidgetItem(f))

    def _load_snapshots(self, r: DatasetRecord):
        self._snap_table.setRowCount(0)
        for snap in reversed(r.snapshots):
            row = self._snap_table.rowCount()
            self._snap_table.insertRow(row)
            self._snap_table.setItem(row, 0, QTableWidgetItem(snap.snapshot_id))
            self._snap_table.setItem(row, 1, QTableWidgetItem(snap.version))
            self._snap_table.setItem(row, 2, QTableWidgetItem(f"{snap.row_count:,}"))
            self._snap_table.setItem(row, 3,
                QTableWidgetItem(f"{snap.quality_score:.2%}"))
            self._snap_table.setItem(row, 4,
                QTableWidgetItem(snap.taken_at.strftime("%Y-%m-%d %H:%M")))

    def _load_lineage(self, r: DatasetRecord):
        lineage = self._engine.get_lineage(r.dataset_id)
        dependents = self._engine.get_dependents(r.dataset_id)
        lines = []
        if lineage:
            lines.append("▲ 上游依赖（血缘追溯）：")
            for i, lid in enumerate(lineage):
                dep_rec = self._engine.get_dataset(lid)
                name = dep_rec.name if dep_rec else lid
                lines.append(f"  {'└─' if i == len(lineage)-1 else '├─'} {lid}  {name}")
        else:
            lines.append("▲ 无上游依赖")
        lines.append("")
        lines.append(f"■ 当前数据集：{r.dataset_id}  {r.name}")
        lines.append("")
        if dependents:
            lines.append("▼ 下游依赖（被以下数据集引用）：")
            for i, did in enumerate(dependents):
                dep_rec = self._engine.get_dataset(did)
                name = dep_rec.name if dep_rec else did
                lines.append(f"  {'└─' if i == len(dependents)-1 else '├─'} {did}  {name}")
        else:
            lines.append("▼ 无下游依赖")
        self._lineage_edit.setPlainText("\n".join(lines))

    def _load_quality(self, r: DatasetRecord):
        score_pct = int(r.quality_score * 100)
        self._quality_label.setText(f"质量得分：{r.quality_score:.2%}")
        self._quality_bar.setValue(score_pct)
        color = ("#198754" if score_pct >= 80
                 else "#fd7e14" if score_pct >= 50
                 else "#dc3545")
        self._quality_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background-color: {color}; }}")
        self._quality_metrics_table.setRowCount(0)
        for k, v in r.quality_metrics.items():
            row = self._quality_metrics_table.rowCount()
            self._quality_metrics_table.insertRow(row)
            self._quality_metrics_table.setItem(row, 0, QTableWidgetItem(k))
            self._quality_metrics_table.setItem(row, 1,
                QTableWidgetItem(f"{v:.4f}"))

    def clear(self):
        self._current = None
        self._overview_table.setRowCount(0)
        self._fields_table.setRowCount(0)
        self._snap_table.setRowCount(0)
        self._lineage_edit.clear()
        self._quality_label.setText("质量得分：—")
        self._quality_bar.setValue(0)
        self._quality_metrics_table.setRowCount(0)


class DatasetTab(QWidget):
    """数据集注册中心主 Tab。"""

    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._all_records: List[DatasetRecord] = []
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        bar1 = QHBoxLayout()
        self._btn_new      = QPushButton('+ 注册数据集')
        self._btn_edit     = QPushButton('编辑')
        self._btn_delete   = QPushButton('删除')
        self._btn_snapshot = QPushButton('拍摄快照')
        for btn in (self._btn_new, self._btn_edit,
                    self._btn_delete, self._btn_snapshot):
            bar1.addWidget(btn)
        bar1.addStretch()
        root.addLayout(bar1)

        bar2 = QHBoxLayout()
        bar2.addWidget(QLabel('状态:'))
        self._status_filter = QComboBox()
        self._status_filter.addItem('全部', None)
        for s in DatasetStatus:
            self._status_filter.addItem(s.value, s)
        self._status_filter.setFixedWidth(120)
        bar2.addWidget(self._status_filter)
        bar2.addWidget(QLabel('来源:'))
        self._source_filter = QLineEdit()
        self._source_filter.setPlaceholderText('来源关键词')
        self._source_filter.setFixedWidth(140)
        bar2.addWidget(self._source_filter)
        bar2.addWidget(QLabel('搜索:'))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText('名称 / 标签 / 标的')
        self._search_box.setFixedWidth(180)
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
        self._table.horizontalHeader().setSectionResizeMode(COL_ID, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        splitter.addWidget(self._table)

        self._detail = DatasetDetailPanel(self._engine)
        self._detail.setMinimumHeight(200)
        splitter.addWidget(self._detail)
        splitter.setSizes([380, 240])
        root.addWidget(splitter)

        self._status_bar = QLabel('共 0 条数据集')
        root.addWidget(self._status_bar)

        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_snapshot.clicked.connect(self._on_snapshot)
        self._btn_search.clicked.connect(self._apply_filter)
        self._btn_reset.clicked.connect(self._reset_filter)
        self._search_box.returnPressed.connect(self._apply_filter)
        self._status_filter.currentIndexChanged.connect(self._apply_filter)
        self._source_filter.returnPressed.connect(self._apply_filter)
        self._table.currentCellChanged.connect(self._on_row_changed)
        self._table.doubleClicked.connect(self._on_edit)

    def _register_events(self):
        ee = self._engine.event_engine
        ee.register(EVENT_DATASET_CREATED, self._on_event)
        ee.register(EVENT_DATASET_UPDATED, self._on_event)
        ee.register(EVENT_DATASET_DELETED, self._on_event)

    def _on_event(self, event: Event):
        # 使用定时器延迟刷新，避免阻塞UI
        from PySide6.QtCore import QTimer
        QTimer.singleShot(10, self._refresh)  # 减少延迟到10ms

    def _refresh(self):
        self._all_records = self._engine.list_datasets()
        self._apply_filter()

    def _apply_filter(self):
        status  = self._status_filter.currentData()
        source  = self._source_filter.text().strip() or None
        keyword = self._search_box.text().strip()
        if keyword:
            records = self._engine.search_datasets(keyword)
        else:
            records = self._engine.list_datasets(status=status, source=source)
        self._populate_table(records)

    def _reset_filter(self):
        self._status_filter.setCurrentIndex(0)
        self._source_filter.clear()
        self._search_box.clear()
        self._populate_table(self._all_records)

    def _populate_table(self, records: List[DatasetRecord]):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        for rec in records:
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._set_row(r, rec)
        self._table.setSortingEnabled(True)
        self._status_bar.setText(f'共 {len(records)} 条数据集')

    def _set_row(self, row: int, rec: DatasetRecord):
        id_item = QTableWidgetItem(rec.dataset_id)
        id_item.setData(Qt.UserRole, rec.dataset_id)
        self._table.setItem(row, COL_ID, id_item)
        self._table.setItem(row, COL_NAME, QTableWidgetItem(rec.name))
        self._table.setItem(row, COL_VERSION, QTableWidgetItem(rec.version))
        status_item = QTableWidgetItem(rec.status.value)
        status_item.setForeground(STATUS_COLORS.get(rec.status, QColor('#333')))
        f = QFont(); f.setBold(True); status_item.setFont(f)
        self._table.setItem(row, COL_STATUS, status_item)
        self._table.setItem(row, COL_SOURCE, QTableWidgetItem(rec.source))
        rows_item = QTableWidgetItem(f'{rec.row_count:,}')
        rows_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._table.setItem(row, COL_ROWS, rows_item)
        score_pct = int(rec.quality_score * 100)
        q_item = QTableWidgetItem(f'{score_pct}%')
        q_item.setTextAlignment(Qt.AlignCenter)
        q_color = (QColor('#d4edda') if score_pct >= 80
                   else QColor('#fff3cd') if score_pct >= 50
                   else QColor('#f8d7da') if score_pct > 0
                   else QColor('#f8f9fa'))
        q_item.setBackground(q_color)
        self._table.setItem(row, COL_QUALITY, q_item)
        self._table.setItem(row, COL_TIME,
            QTableWidgetItem(rec.updated_at.strftime('%Y-%m-%d %H:%M')))

    def _on_row_changed(self, cur_row, *_):
        rec = self._get_record_at(cur_row)
        if rec:
            self._detail.load(rec)
        else:
            self._detail.clear()

    def _on_new(self):
        dlg = DatasetCreateDialog(parent=self)
        if dlg.exec() == DatasetCreateDialog.Accepted:
            self._engine.register_dataset(
                name=dlg.get_name(), version=dlg.get_version(),
                description=dlg.get_description(), source=dlg.get_source(),
                symbols=dlg.get_symbols(), start_date=dlg.get_start_date(),
                end_date=dlg.get_end_date(), fields=dlg.get_fields(),
                row_count=dlg.get_row_count(), size_mb=dlg.get_size_mb(),
                tags=dlg.get_tags(), created_by=dlg.get_author(),
            )

    def _on_edit(self):
        rec = self._get_selected_record()
        if not rec:
            return
        dlg = DatasetCreateDialog(parent=self, record=rec)
        if dlg.exec() == DatasetCreateDialog.Accepted:
            rec.name        = dlg.get_name()
            rec.version     = dlg.get_version()
            rec.description = dlg.get_description()
            rec.source      = dlg.get_source()
            rec.status      = dlg.get_status()
            rec.symbols     = dlg.get_symbols()
            rec.start_date  = dlg.get_start_date()
            rec.end_date    = dlg.get_end_date()
            rec.fields      = dlg.get_fields()
            rec.row_count   = dlg.get_row_count()
            rec.size_mb     = dlg.get_size_mb()
            rec.tags        = dlg.get_tags()
            rec.created_by  = dlg.get_author()
            self._engine.update_dataset(rec)

    def _on_delete(self):
        rec = self._get_selected_record()
        if rec:
            self._engine.delete_dataset(rec.dataset_id)

    def _on_snapshot(self):
        rec = self._get_selected_record()
        if rec:
            self._engine.take_snapshot(rec.dataset_id)

    def _get_record_at(self, row: int) -> Optional[DatasetRecord]:
        item = self._table.item(row, COL_ID)
        if item is None:
            return None
        return self._engine.get_dataset(item.data(Qt.UserRole))

    def _get_selected_record(self) -> Optional[DatasetRecord]:
        return self._get_record_at(self._table.currentRow())
