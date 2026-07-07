"""
quant_research/ui/artifact_tab.py  — Phase 10 完整实现
"""
from __future__ import annotations
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QPlainTextEdit, QDoubleSpinBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from vnpy.event import Event

from ..engine import ResearchEngine
from ..event import EVENT_ARTIFACT_CREATED, EVENT_ARTIFACT_DELETED
from ..constant import ArtifactType
from ..model.artifact_model import ArtifactRecord, ARTIFACT_TYPE_LABELS

COL_ID      = 0
COL_NAME    = 1
COL_TYPE    = 2
COL_VERSION = 3
COL_AUTHOR  = 4
COL_SIZE    = 5
COL_DL      = 6
COL_ARCH    = 7
COL_TIME    = 8

HEADERS = ["成果 ID", "名称", "类型", "版本",
           "作者", "大小(KB)", "下载数", "归档", "创建时间"]

TYPE_COLORS = {
    ArtifactType.MODEL:  QColor("#0d6efd"),
    ArtifactType.REPORT: QColor("#6f42c1"),
    ArtifactType.CSV:    QColor("#198754"),
    ArtifactType.EXCEL:  QColor("#20c997"),
    ArtifactType.IMAGE:  QColor("#fd7e14"),
    ArtifactType.LOG:    QColor("#6c757d"),
    ArtifactType.CONFIG: QColor("#0dcaf0"),
    ArtifactType.OTHER:  QColor("#adb5bd"),
}


# ─────────────────────────────────────────────────────────────────────
# ArtifactCreateDialog
# ─────────────────────────────────────────────────────────────────────

class ArtifactCreateDialog(QDialog):
    def __init__(self, parent=None, record: Optional[ArtifactRecord] = None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle("编辑成果" if self._editing else "注册成果")
        self.setMinimumWidth(520)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp = QGroupBox("成果信息")
        form = QFormLayout(grp)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("成果名称（必填）")
        form.addRow("名称 *", self._name_edit)

        self._type_combo = QComboBox()
        for at in ArtifactType:
            self._type_combo.addItem(ARTIFACT_TYPE_LABELS.get(at, at.value), at)
        form.addRow("类型", self._type_combo)

        self._version_edit = QLineEdit("v1.0")
        form.addRow("版本", self._version_edit)

        self._author_edit = QLineEdit()
        form.addRow("作者", self._author_edit)

        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("文件路径（可选）")
        form.addRow("文件路径", self._path_edit)

        self._size_spin = QDoubleSpinBox()
        self._size_spin.setRange(0, 1e9)
        self._size_spin.setDecimals(2)
        self._size_spin.setSuffix("  KB")
        form.addRow("文件大小", self._size_spin)

        self._checksum_edit = QLineEdit()
        self._checksum_edit.setPlaceholderText("MD5 / SHA256（可选）")
        form.addRow("校验和", self._checksum_edit)

        self._desc_edit = QPlainTextEdit()
        self._desc_edit.setFixedHeight(52)
        form.addRow("描述", self._desc_edit)

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("逗号分隔标签")
        form.addRow("标签", self._tags_edit)
        root.addWidget(grp)

        rel_grp = QGroupBox("关联资源（ID）")
        rf = QFormLayout(rel_grp)
        self._exp_edit = QLineEdit(); rf.addRow("关联实验",   self._exp_edit)
        self._pl_edit  = QLineEdit(); rf.addRow("关联流水线", self._pl_edit)
        self._st_edit  = QLineEdit(); rf.addRow("关联策略",   self._st_edit)
        self._ml_edit  = QLineEdit(); rf.addRow("关联模型",   self._ml_edit)
        self._bt_edit  = QLineEdit(); rf.addRow("关联回测",   self._bt_edit)
        self._rpt_edit = QLineEdit(); rf.addRow("关联报告",   self._rpt_edit)
        root.addWidget(rel_grp)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load(self):
        r = self._record
        self._name_edit.setText(r.name)
        idx = self._type_combo.findData(r.artifact_type)
        if idx >= 0: self._type_combo.setCurrentIndex(idx)
        self._version_edit.setText(r.version)
        self._author_edit.setText(r.author)
        self._path_edit.setText(r.file_path)
        self._size_spin.setValue(r.file_size_kb)
        self._checksum_edit.setText(r.checksum)
        self._desc_edit.setPlainText(r.description)
        self._tags_edit.setText(", ".join(r.tags))
        self._exp_edit.setText(r.experiment_id or "")
        self._pl_edit.setText(r.pipeline_id or "")
        self._st_edit.setText(r.strategy_id or "")
        self._ml_edit.setText(r.model_id or "")
        self._bt_edit.setText(r.backtest_id or "")
        self._rpt_edit.setText(r.report_id or "")

    def _on_accept(self):
        if not self._name_edit.text().strip():
            self._name_edit.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]
    def _opt(self, t):   return t.strip() or None

    def get_name(self)         -> str:             return self._name_edit.text().strip()
    def get_type(self)         -> ArtifactType:    return self._type_combo.currentData()
    def get_version(self)      -> str:             return self._version_edit.text().strip() or "v1.0"
    def get_author(self)       -> str:             return self._author_edit.text().strip()
    def get_path(self)         -> str:             return self._path_edit.text().strip()
    def get_size(self)         -> float:           return self._size_spin.value()
    def get_checksum(self)     -> str:             return self._checksum_edit.text().strip()
    def get_description(self)  -> str:             return self._desc_edit.toPlainText().strip()
    def get_tags(self)         -> List[str]:       return self._split(self._tags_edit.text())
    def get_experiment_id(self) -> Optional[str]:  return self._opt(self._exp_edit.text())
    def get_pipeline_id(self)  -> Optional[str]:   return self._opt(self._pl_edit.text())
    def get_strategy_id(self)  -> Optional[str]:   return self._opt(self._st_edit.text())
    def get_model_id(self)     -> Optional[str]:   return self._opt(self._ml_edit.text())
    def get_backtest_id(self)  -> Optional[str]:   return self._opt(self._bt_edit.text())
    def get_report_id(self)    -> Optional[str]:   return self._opt(self._rpt_edit.text())


# ─────────────────────────────────────────────────────────────────────
# ArtifactDetailPanel
# ─────────────────────────────────────────────────────────────────────

class ArtifactDetailPanel(QTabWidget):
    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._current: Optional[ArtifactRecord] = None
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

        rel_w = QWidget(); rel_l = QVBoxLayout(rel_w)
        self._rel_edit = QTextEdit()
        self._rel_edit.setReadOnly(True)
        self._rel_edit.setFont(QFont("Consolas", 10))
        rel_l.addWidget(self._rel_edit)
        self.addTab(rel_w, "关联资源")

    def load(self, record: ArtifactRecord):
        self._current = record
        self._load_ov(record)
        self._load_relations(record)

    def _load_ov(self, r: ArtifactRecord):
        self._ov_table.setRowCount(0)
        rows = [
            ("ID",       r.artifact_id),
            ("名称",     r.name),
            ("类型",     ARTIFACT_TYPE_LABELS.get(r.artifact_type, r.artifact_type.value)),
            ("版本",     r.version),
            ("作者",     r.author),
            ("文件路径", r.file_path),
            ("文件大小", f"{r.file_size_kb:.2f} KB"),
            ("校验和",   r.checksum),
            ("下载次数", str(r.download_count)),
            ("已归档",   "是" if r.is_archived else "否"),
            ("标签",     ", ".join(r.tags)),
            ("创建时间", r.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("描述",     r.description),
        ]
        for k, v in rows:
            row = self._ov_table.rowCount()
            self._ov_table.insertRow(row)
            self._ov_table.setItem(row, 0, QTableWidgetItem(k))
            self._ov_table.setItem(row, 1, QTableWidgetItem(str(v)))

    def _load_relations(self, r: ArtifactRecord):
        lines = []
        for label, rid, getter in [
            ("■ 关联实验",   r.experiment_id, self._engine.get_experiment),
            ("■ 关联流水线", r.pipeline_id,   self._engine.get_pipeline),
            ("■ 关联策略",   r.strategy_id,   self._engine.get_strategy),
            ("■ 关联模型",   r.model_id,      self._engine.get_model),
            ("■ 关联回测",   r.backtest_id,   self._engine.get_backtest),
            ("■ 关联报告",   r.report_id,     self._engine.get_report),
        ]:
            if rid:
                obj = getter(rid)
                name = getattr(obj, "name", None) or getattr(obj, "title", rid)
                lines.append(f"{label}：{rid}  {name}")
            else:
                lines.append(f"{label}：无")
        self._rel_edit.setPlainText("\n".join(lines))

    def clear(self):
        self._current = None
        self._ov_table.setRowCount(0)
        self._rel_edit.clear()


class ArtifactTab(QWidget):
    """成果中心主 Tab。"""
    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._all_records: List[ArtifactRecord] = []
        self._init_ui()
        self._register_events()
        self._refresh()
    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(6,6,6,6)
        bar1 = QHBoxLayout()
        self._btn_new      = QPushButton('+ 注册成果')
        self._btn_edit     = QPushButton('编辑')
        self._btn_delete   = QPushButton('删除')
        self._btn_archive  = QPushButton('归档')
        self._btn_unarch   = QPushButton('取消归档')
        self._btn_download = QPushButton('记录下载')
        for btn in (self._btn_new, self._btn_edit, self._btn_delete,
                    self._btn_archive, self._btn_unarch, self._btn_download):
            bar1.addWidget(btn)
        bar1.addStretch()
        self._size_lbl = QLabel('总大小：0 KB')
        self._size_lbl.setStyleSheet('color:#6c757d; padding:2px 8px;')
        bar1.addWidget(self._size_lbl)
        root.addLayout(bar1)
        bar2 = QHBoxLayout()
        bar2.addWidget(QLabel('类型:'))
        self._type_filter = QComboBox()
        self._type_filter.addItem('全部', None)
        for at in ArtifactType:
            self._type_filter.addItem(ARTIFACT_TYPE_LABELS.get(at, at.value), at)
        self._type_filter.setFixedWidth(100); bar2.addWidget(self._type_filter)
        bar2.addWidget(QLabel('归档:'))
        self._arch_filter = QComboBox()
        self._arch_filter.addItem('全部', None)
        self._arch_filter.addItem('活跃', False)
        self._arch_filter.addItem('已归档', True)
        self._arch_filter.setFixedWidth(80); bar2.addWidget(self._arch_filter)
        bar2.addWidget(QLabel('搜索:'))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText('名称 / 作者 / 路径')
        self._search_box.setFixedWidth(180); bar2.addWidget(self._search_box)
        self._btn_search = QPushButton('搜索'); self._btn_search.setFixedWidth(52)
        bar2.addWidget(self._btn_search)
        self._btn_reset = QPushButton('重置'); self._btn_reset.setFixedWidth(52)
        bar2.addWidget(self._btn_reset)
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
        self._detail = ArtifactDetailPanel(self._engine)
        self._detail.setMinimumHeight(200)
        splitter.addWidget(self._detail)
        splitter.setSizes([340, 220]); root.addWidget(splitter)
        self._status_bar = QLabel('共 0 个成果'); root.addWidget(self._status_bar)
        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_archive.clicked.connect(self._on_archive)
        self._btn_unarch.clicked.connect(self._on_unarchive)
        self._btn_download.clicked.connect(self._on_download)
        self._btn_search.clicked.connect(self._apply_filter)
        self._btn_reset.clicked.connect(self._reset_filter)
        self._search_box.returnPressed.connect(self._apply_filter)
        self._type_filter.currentIndexChanged.connect(self._apply_filter)
        self._arch_filter.currentIndexChanged.connect(self._apply_filter)
        self._table.currentCellChanged.connect(self._on_row_changed)
        self._table.doubleClicked.connect(self._on_edit)
    def _register_events(self):
        ee = self._engine.event_engine
        ee.register(EVENT_ARTIFACT_CREATED, self._on_event)
        ee.register(EVENT_ARTIFACT_DELETED, self._on_event)
    def _on_event(self, event: Event): self._refresh()
    def _refresh(self):
        self._all_records = self._engine.list_artifacts()
        total_kb = self._engine.artifact_total_size_kb()
        self._size_lbl.setText(f'总大小：{total_kb:.1f} KB')
        self._apply_filter()
    def _apply_filter(self):
        atype    = self._type_filter.currentData()
        archived = self._arch_filter.currentData()
        keyword  = self._search_box.text().strip()
        if keyword:
            records = self._engine.search_artifacts(keyword)
        else:
            records = self._engine.list_artifacts(artifact_type=atype, archived=archived)
        self._populate_table(records)
    def _reset_filter(self):
        self._type_filter.setCurrentIndex(0)
        self._arch_filter.setCurrentIndex(0)
        self._search_box.clear()
        self._populate_table(self._all_records)
    def _populate_table(self, records):
        self._table.setSortingEnabled(False); self._table.setRowCount(0)
        for rec in records:
            r = self._table.rowCount(); self._table.insertRow(r); self._set_row(r, rec)
        self._table.setSortingEnabled(True)
        self._status_bar.setText(f'共 {len(records)} 个成果')
    def _set_row(self, row: int, rec: ArtifactRecord):
        id_item = QTableWidgetItem(rec.artifact_id)
        id_item.setData(Qt.UserRole, rec.artifact_id)
        self._table.setItem(row, COL_ID, id_item)
        self._table.setItem(row, COL_NAME, QTableWidgetItem(rec.name))
        type_lbl = ARTIFACT_TYPE_LABELS.get(rec.artifact_type, rec.artifact_type.value)
        t_item = QTableWidgetItem(type_lbl)
        t_item.setForeground(TYPE_COLORS.get(rec.artifact_type, QColor('#333')))
        f = QFont(); f.setBold(True); t_item.setFont(f)
        self._table.setItem(row, COL_TYPE, t_item)
        self._table.setItem(row, COL_VERSION, QTableWidgetItem(rec.version))
        self._table.setItem(row, COL_AUTHOR, QTableWidgetItem(rec.author))
        sz_item = QTableWidgetItem(f'{rec.file_size_kb:.1f}')
        sz_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._table.setItem(row, COL_SIZE, sz_item)
        dl_item = QTableWidgetItem(str(rec.download_count))
        dl_item.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(row, COL_DL, dl_item)
        arch_item = QTableWidgetItem('✓' if rec.is_archived else '—')
        arch_item.setTextAlignment(Qt.AlignCenter)
        arch_item.setForeground(QColor('#6c757d') if rec.is_archived else QColor('#198754'))
        self._table.setItem(row, COL_ARCH, arch_item)
        self._table.setItem(row, COL_TIME, QTableWidgetItem(rec.created_at.strftime('%Y-%m-%d %H:%M')))
    def _on_row_changed(self, cur_row, *_):
        rec = self._get_record_at(cur_row)
        if rec: self._detail.load(rec)
        else:   self._detail.clear()
    def _on_new(self):
        dlg = ArtifactCreateDialog(parent=self)
        if dlg.exec() == ArtifactCreateDialog.Accepted:
            self._engine.register_artifact(
                name=dlg.get_name(), artifact_type=dlg.get_type(),
                description=dlg.get_description(), author=dlg.get_author(),
                file_path=dlg.get_path(), file_size_kb=dlg.get_size(),
                checksum=dlg.get_checksum(), version=dlg.get_version(),
                experiment_id=dlg.get_experiment_id(),
                pipeline_id=dlg.get_pipeline_id(),
                strategy_id=dlg.get_strategy_id(),
                model_id=dlg.get_model_id(),
                backtest_id=dlg.get_backtest_id(),
                report_id=dlg.get_report_id(),
                tags=dlg.get_tags(),
            )
    def _on_edit(self):
        rec = self._get_selected_record()
        if not rec: return
        dlg = ArtifactCreateDialog(parent=self, record=rec)
        if dlg.exec() == ArtifactCreateDialog.Accepted:
            rec.name          = dlg.get_name()
            rec.artifact_type = dlg.get_type()
            rec.description   = dlg.get_description()
            rec.author        = dlg.get_author()
            rec.file_path     = dlg.get_path()
            rec.file_size_kb  = dlg.get_size()
            rec.checksum      = dlg.get_checksum()
            rec.version       = dlg.get_version()
            rec.experiment_id = dlg.get_experiment_id()
            rec.pipeline_id   = dlg.get_pipeline_id()
            rec.strategy_id   = dlg.get_strategy_id()
            rec.model_id      = dlg.get_model_id()
            rec.backtest_id   = dlg.get_backtest_id()
            rec.report_id     = dlg.get_report_id()
            rec.tags          = dlg.get_tags()
            self._engine.update_artifact(rec)
            self._refresh()
    def _on_delete(self):
        rec = self._get_selected_record()
        if rec: self._engine.delete_artifact(rec.artifact_id)
    def _on_archive(self):
        rec = self._get_selected_record()
        if rec: self._engine.archive_artifact(rec.artifact_id); self._refresh()
    def _on_unarchive(self):
        rec = self._get_selected_record()
        if rec: self._engine.unarchive_artifact(rec.artifact_id); self._refresh()
    def _on_download(self):
        rec = self._get_selected_record()
        if rec: self._engine.download_artifact(rec.artifact_id); self._refresh()
    def _get_record_at(self, row):
        item = self._table.item(row, COL_ID)
        if item is None: return None
        return self._engine.get_artifact(item.data(Qt.UserRole))
    def _get_selected_record(self):
        return self._get_record_at(self._table.currentRow())
