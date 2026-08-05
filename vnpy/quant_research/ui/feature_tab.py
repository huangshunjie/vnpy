"""
quant_research/ui/feature_tab.py

FeatureTab — Phase 4 完整实现。
"""
from __future__ import annotations
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QCheckBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from vnpy.event import Event

from ..engine import ResearchEngine
from ..constant import FeatureStatus
from ..event import (
    EVENT_FEATURE_CREATED,
    EVENT_FEATURE_UPDATED,
    EVENT_FEATURE_DELETED,
)
from ..model.feature_model import FeatureRecord, ICRecord
from .feature_dialogs import (
    FeatureCreateDialog,
    FeatureICDialog,
    FeatureDeprecateDialog,
)

CATEGORIES = [
    "", "momentum", "reversal", "value", "quality",
    "growth", "technical", "alternative", "macro", "other",
]

STATUS_COLORS = {
    FeatureStatus.EXPERIMENTAL: QColor("#0d6efd"),
    FeatureStatus.STABLE:       QColor("#198754"),
    FeatureStatus.DEPRECATED:   QColor("#adb5bd"),
    FeatureStatus.REVIEW:       QColor("#fd7e14"),
}

COL_ID       = 0
COL_NAME     = 1
COL_VERSION  = 2
COL_STATUS   = 3
COL_CATEGORY = 4
COL_AUTHOR   = 5
COL_IC       = 6
COL_RANK_IC  = 7
COL_ICIR     = 8
COL_TIME     = 9

HEADERS = ["因子 ID", "名称", "版本", "状态", "分类", "作者",
           "IC", "RankIC", "ICIR", "更新时间"]


class FeatureDetailPanel(QTabWidget):
    """底部详情面板：概览 / IC 分析 / 依赖 / 废弃信息。"""

    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._current: Optional[FeatureRecord] = None
        self._init_ui()

    def _init_ui(self):
        # ── 概览 ──────────────────────────────────────────────────────
        ov_w = QWidget()
        ov_l = QVBoxLayout(ov_w)
        self._overview_table = QTableWidget(0, 2)
        self._overview_table.setHorizontalHeaderLabels(["属性", "值"])
        self._overview_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._overview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._overview_table.setAlternatingRowColors(True)
        ov_l.addWidget(self._overview_table)
        self.addTab(ov_w, "概览")

        # ── IC 分析 ────────────────────────────────────────────────────
        ic_w = QWidget()
        ic_l = QVBoxLayout(ic_w)

        # 当前指标横幅
        banner = QHBoxLayout()
        self._ic_lbl    = self._metric_label("IC",     "—")
        self._rankic_lbl= self._metric_label("RankIC", "—")
        self._ir_lbl    = self._metric_label("IR",     "—")
        self._icir_lbl  = self._metric_label("ICIR",   "—")
        self._cov_lbl   = self._metric_label("Coverage","—")
        for w in (self._ic_lbl, self._rankic_lbl, self._ir_lbl,
                  self._icir_lbl, self._cov_lbl):
            banner.addWidget(w)
        ic_l.addLayout(banner)

        # 历史评估表
        self._ic_hist_table = QTableWidget(0, 7)
        self._ic_hist_table.setHorizontalHeaderLabels(
            ["评估 ID", "IC", "Rank IC", "IR", "ICIR", "Coverage", "评估时间"])
        self._ic_hist_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._ic_hist_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ic_hist_table.setAlternatingRowColors(True)
        ic_l.addWidget(self._ic_hist_table)
        self.addTab(ic_w, "IC 分析")

        # ── 依赖关系 ───────────────────────────────────────────────────
        dep_w = QWidget()
        dep_l = QVBoxLayout(dep_w)
        self._dep_edit = QTextEdit()
        self._dep_edit.setReadOnly(True)
        self._dep_edit.setFont(QFont("Consolas", 10))
        dep_l.addWidget(self._dep_edit)
        self.addTab(dep_w, "依赖关系")

        # ── 废弃信息 ───────────────────────────────────────────────────
        dep2_w = QWidget()
        dep2_l = QVBoxLayout(dep2_w)
        self._deprecated_edit = QTextEdit()
        self._deprecated_edit.setReadOnly(True)
        dep2_l.addWidget(self._deprecated_edit)
        self.addTab(dep2_w, "废弃信息")

    @staticmethod
    def _metric_label(title: str, value: str) -> QWidget:
        w = QWidget()
        lyt = QVBoxLayout(w)
        lyt.setContentsMargins(8, 4, 8, 4)
        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("color:#666; font-size:11px;")
        val_lbl = QLabel(value)
        val_lbl.setAlignment(Qt.AlignCenter)
        val_lbl.setStyleSheet("font-size:18px; font-weight:bold;")
        val_lbl.setObjectName("val")
        lyt.addWidget(title_lbl)
        lyt.addWidget(val_lbl)
        w.setStyleSheet("background:#f8f9fa; border-radius:6px;")
        return w

    def _set_metric(self, widget: QWidget, value: float, fmt: str = ".4f"):
        lbl = widget.findChild(QLabel, "val")
        if lbl:
            lbl.setText(f"{value:{fmt}}")
            color = "#198754" if value > 0 else "#dc3545" if value < 0 else "#333"
            lbl.setStyleSheet(f"font-size:18px; font-weight:bold; color:{color};")

    def load(self, record: FeatureRecord):
        self._current = record
        self._load_overview(record)
        self._load_ic(record)
        self._load_deps(record)
        self._load_deprecated(record)

    def _load_overview(self, r: FeatureRecord):
        self._overview_table.setRowCount(0)
        rows = [
            ("ID",       r.feature_id),
            ("名称",     r.name),
            ("版本",     r.version),
            ("状态",     r.status.value),
            ("分类",     r.category),
            ("作者",     r.author),
            ("标签",     ", ".join(r.tags)),
            ("创建时间", r.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("更新时间", r.updated_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("描述",     r.description),
            ("公式",     r.formula),
        ]
        if r.published_at:
            rows.append(("发布时间", r.published_at.strftime("%Y-%m-%d %H:%M")))
        for k, v in rows:
            row = self._overview_table.rowCount()
            self._overview_table.insertRow(row)
            self._overview_table.setItem(row, 0, QTableWidgetItem(k))
            self._overview_table.setItem(row, 1, QTableWidgetItem(str(v)))

    def _load_ic(self, r: FeatureRecord):
        self._set_metric(self._ic_lbl,     r.ic)
        self._set_metric(self._rankic_lbl, r.rank_ic)
        self._set_metric(self._ir_lbl,     r.ir)
        self._set_metric(self._icir_lbl,   r.icir)
        self._set_metric(self._cov_lbl,    r.coverage, ".2%")

        self._ic_hist_table.setRowCount(0)
        for rec in reversed(r.ic_history):
            row = self._ic_hist_table.rowCount()
            self._ic_hist_table.insertRow(row)
            vals = [rec.eval_id,
                    f"{rec.ic:.6f}", f"{rec.rank_ic:.6f}",
                    f"{rec.ir:.4f}",  f"{rec.icir:.4f}",
                    f"{rec.coverage:.2%}",
                    rec.evaluated_at.strftime("%Y-%m-%d %H:%M")]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignCenter)
                self._ic_hist_table.setItem(row, col, item)

    def _load_deps(self, r: FeatureRecord):
        lines = []
        if r.dependencies:
            lines.append("▲ 依赖上游因子：")
            for fid in r.dependencies:
                dep = self._engine.get_feature(fid)
                name = dep.name if dep else fid
                lines.append(f"  ├─ {fid}  {name}")
        else:
            lines.append("▲ 无上游因子依赖")
        lines.append("")
        if r.dataset_ids:
            lines.append("■ 依赖数据集：")
            for did in r.dataset_ids:
                ds = self._engine.get_dataset(did)
                name = ds.name if ds else did
                lines.append(f"  ├─ {did}  {name}")
        else:
            lines.append("■ 无数据集依赖")
        lines.append("")
        dependents = self._engine.get_feature_dependents(r.feature_id)
        if dependents:
            lines.append("▼ 被以下因子依赖：")
            for fid in dependents:
                dep = self._engine.get_feature(fid)
                name = dep.name if dep else fid
                lines.append(f"  ├─ {fid}  {name}")
        else:
            lines.append("▼ 无下游因子依赖")
        self._dep_edit.setPlainText("\n".join(lines))

    def _load_deprecated(self, r: FeatureRecord):
        if r.deprecated_at:
            text = (
                f"状态：已废弃\n"
                f"废弃时间：{r.deprecated_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"废弃原因：\n{r.deprecated_reason or '（未填写）'}"
            )
        else:
            text = "状态：正常（未废弃）"
        self._deprecated_edit.setPlainText(text)

    def clear(self):
        self._current = None
        self._overview_table.setRowCount(0)
        self._ic_hist_table.setRowCount(0)
        self._dep_edit.clear()
        self._deprecated_edit.clear()


class FeatureTab(QWidget):
    """因子注册中心主 Tab。"""

    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._all_records: List[FeatureRecord] = []
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        bar1 = QHBoxLayout()
        self._btn_new       = QPushButton('+ 注册因子')
        self._btn_edit      = QPushButton('编辑')
        self._btn_delete    = QPushButton('删除')
        self._btn_ic        = QPushButton('录入 IC')
        self._btn_deprecate = QPushButton('废弃')
        self._btn_restore   = QPushButton('恢复')
        for btn in (self._btn_new, self._btn_edit, self._btn_delete,
                    self._btn_ic, self._btn_deprecate, self._btn_restore):
            bar1.addWidget(btn)
        bar1.addStretch()
        root.addLayout(bar1)

        bar2 = QHBoxLayout()
        bar2.addWidget(QLabel('状态:'))
        self._status_filter = QComboBox()
        self._status_filter.addItem('全部', None)
        for s in FeatureStatus:
            self._status_filter.addItem(s.value, s)
        self._status_filter.setFixedWidth(130)
        bar2.addWidget(self._status_filter)
        bar2.addWidget(QLabel('分类:'))
        self._category_filter = QComboBox()
        for c in CATEGORIES:
            self._category_filter.addItem(c if c else '全部', c if c else None)
        self._category_filter.setFixedWidth(120)
        bar2.addWidget(self._category_filter)
        self._active_only_cb = QCheckBox('隐藏已废弃')
        bar2.addWidget(self._active_only_cb)
        bar2.addWidget(QLabel('搜索:'))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText('名称 / 分类 / 作者 / 公式')
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
        self._table.horizontalHeader().setSectionResizeMode(COL_ID, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        splitter.addWidget(self._table)

        self._detail = FeatureDetailPanel(self._engine)
        self._detail.setMinimumHeight(200)
        splitter.addWidget(self._detail)
        splitter.setSizes([380, 240])
        root.addWidget(splitter)

        self._status_bar = QLabel('共 0 条因子')
        root.addWidget(self._status_bar)

        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_ic.clicked.connect(self._on_ic)
        self._btn_deprecate.clicked.connect(self._on_deprecate)
        self._btn_restore.clicked.connect(self._on_restore)
        self._btn_search.clicked.connect(self._apply_filter)
        self._btn_reset.clicked.connect(self._reset_filter)
        self._search_box.returnPressed.connect(self._apply_filter)
        self._status_filter.currentIndexChanged.connect(self._apply_filter)
        self._category_filter.currentIndexChanged.connect(self._apply_filter)
        self._active_only_cb.stateChanged.connect(self._apply_filter)
        self._table.currentCellChanged.connect(self._on_row_changed)
        self._table.doubleClicked.connect(self._on_edit)

    def _register_events(self):
        ee = self._engine.event_engine
        ee.register(EVENT_FEATURE_CREATED, self._on_event)
        ee.register(EVENT_FEATURE_UPDATED, self._on_event)
        ee.register(EVENT_FEATURE_DELETED, self._on_event)

    def _on_event(self, event: Event):
        # 使用定时器延迟刷新，避免阻塞UI
        from PySide6.QtCore import QTimer
        QTimer.singleShot(10, self._refresh)  # 减少延迟到10ms

    def _refresh(self):
        self._all_records = self._engine.list_features()
        self._apply_filter()

    def _apply_filter(self):
        status      = self._status_filter.currentData()
        category    = self._category_filter.currentData()
        active_only = self._active_only_cb.isChecked()
        keyword     = self._search_box.text().strip()
        if keyword:
            records = self._engine.search_features(keyword)
        else:
            records = self._engine.list_features(
                status=status, category=category, active_only=active_only)
        self._populate_table(records)

    def _reset_filter(self):
        self._status_filter.setCurrentIndex(0)
        self._category_filter.setCurrentIndex(0)
        self._active_only_cb.setChecked(False)
        self._search_box.clear()
        self._populate_table(self._all_records)

    def _populate_table(self, records: List[FeatureRecord]):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        for rec in records:
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._set_row(r, rec)
        self._table.setSortingEnabled(True)
        self._status_bar.setText(f'共 {len(records)} 条因子')

    def _set_row(self, row: int, rec: FeatureRecord):
        id_item = QTableWidgetItem(rec.feature_id)
        id_item.setData(Qt.UserRole, rec.feature_id)
        self._table.setItem(row, COL_ID, id_item)
        name_item = QTableWidgetItem(rec.name)
        if rec.deprecated_at:
            font = QFont()
            font.setStrikeOut(True)
            name_item.setFont(font)
            name_item.setForeground(QColor('#adb5bd'))
        self._table.setItem(row, COL_NAME, name_item)
        self._table.setItem(row, COL_VERSION, QTableWidgetItem(rec.version))
        status_item = QTableWidgetItem(rec.status.value)
        status_item.setForeground(STATUS_COLORS.get(rec.status, QColor('#333')))
        f = QFont(); f.setBold(True); status_item.setFont(f)
        self._table.setItem(row, COL_STATUS, status_item)
        self._table.setItem(row, COL_CATEGORY, QTableWidgetItem(rec.category))
        self._table.setItem(row, COL_AUTHOR,   QTableWidgetItem(rec.author))
        def _num_item(val, fmt='.4f'):
            item = QTableWidgetItem(f'{val:{fmt}}')
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if val > 0: item.setForeground(QColor('#198754'))
            elif val < 0: item.setForeground(QColor('#dc3545'))
            return item
        self._table.setItem(row, COL_IC,      _num_item(rec.ic))
        self._table.setItem(row, COL_RANK_IC, _num_item(rec.rank_ic))
        self._table.setItem(row, COL_ICIR,    _num_item(rec.icir))
        self._table.setItem(row, COL_TIME,
            QTableWidgetItem(rec.updated_at.strftime('%Y-%m-%d %H:%M')))

    def _on_row_changed(self, cur_row, *_):
        rec = self._get_record_at(cur_row)
        if rec:
            self._detail.load(rec)
        else:
            self._detail.clear()

    def _on_new(self):
        dlg = FeatureCreateDialog(parent=self)
        if dlg.exec() == FeatureCreateDialog.Accepted:
            self._engine.register_feature(
                name=dlg.get_name(), version=dlg.get_version(),
                description=dlg.get_description(), category=dlg.get_category(),
                formula=dlg.get_formula(), author=dlg.get_author(),
                tags=dlg.get_tags(), dependencies=dlg.get_dependencies(),
                dataset_ids=dlg.get_dataset_ids(),
            )

    def _on_edit(self):
        rec = self._get_selected_record()
        if not rec:
            return
        dlg = FeatureCreateDialog(parent=self, record=rec)
        if dlg.exec() == FeatureCreateDialog.Accepted:
            rec.name         = dlg.get_name()
            rec.version      = dlg.get_version()
            rec.description  = dlg.get_description()
            rec.category     = dlg.get_category()
            rec.formula      = dlg.get_formula()
            rec.author       = dlg.get_author()
            rec.status       = dlg.get_status()
            rec.tags         = dlg.get_tags()
            rec.dependencies = dlg.get_dependencies()
            rec.dataset_ids  = dlg.get_dataset_ids()
            self._engine.update_feature(rec)

    def _on_delete(self):
        rec = self._get_selected_record()
        if rec:
            self._engine.delete_feature(rec.feature_id)

    def _on_ic(self):
        rec = self._get_selected_record()
        if not rec:
            return
        dlg = FeatureICDialog(rec.name, parent=self)
        if dlg.exec() == FeatureICDialog.Accepted:
            self._engine.update_ic_metrics(
                rec.feature_id,
                ic=dlg.get_ic(), rank_ic=dlg.get_rank_ic(),
                ir=dlg.get_ir(), icir=dlg.get_icir(),
                coverage=dlg.get_coverage(),
                period=dlg.get_period(), dataset_id=dlg.get_dataset_id(),
            )

    def _on_deprecate(self):
        rec = self._get_selected_record()
        if not rec or rec.deprecated_at is not None:
            return
        dlg = FeatureDeprecateDialog(rec.name, parent=self)
        if dlg.exec() == FeatureDeprecateDialog.Accepted:
            self._engine.deprecate_feature(rec.feature_id, dlg.get_reason())

    def _on_restore(self):
        rec = self._get_selected_record()
        if rec and rec.deprecated_at is not None:
            self._engine.restore_feature(rec.feature_id)

    def _get_record_at(self, row: int) -> Optional[FeatureRecord]:
        item = self._table.item(row, COL_ID)
        if item is None:
            return None
        return self._engine.get_feature(item.data(Qt.UserRole))

    def _get_selected_record(self) -> Optional[FeatureRecord]:
        return self._get_record_at(self._table.currentRow())
