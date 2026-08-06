"""
quant_research/ui/report_tab.py  — Phase 9 完整实现
"""
from __future__ import annotations
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QPlainTextEdit, QCheckBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from vnpy.event import Event

from ..engine import ResearchEngine
from ..event import EVENT_REPORT_CREATED, EVENT_REPORT_UPDATED
from ..model.report_model import ReportRecord, ReportSection, REPORT_TYPES

COL_ID      = 0
COL_TITLE   = 1
COL_TYPE    = 2
COL_AUTHOR  = 3
COL_PUB     = 4
COL_VIEWS   = 5
COL_TIME    = 6

HEADERS = ["报告 ID", "标题", "类型", "作者", "已发布", "浏览数", "更新时间"]

PUB_COLOR   = QColor("#198754")
UNPUB_COLOR = QColor("#adb5bd")


# ─────────────────────────────────────────────────────────────────────
# ReportCreateDialog
# ─────────────────────────────────────────────────────────────────────

class ReportCreateDialog(QDialog):
    def __init__(self, parent=None, record: Optional[ReportRecord] = None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle("编辑报告" if self._editing else "新建报告")
        self.setMinimumWidth(520)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp = QGroupBox("报告信息")
        form = QFormLayout(grp)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("报告标题（必填）")
        form.addRow("标题 *", self._title_edit)

        self._type_combo = QComboBox()
        for t in REPORT_TYPES:
            self._type_combo.addItem(t, t)
        form.addRow("类型", self._type_combo)

        self._author_edit = QLineEdit()
        form.addRow("作者", self._author_edit)

        self._desc_edit = QPlainTextEdit()
        self._desc_edit.setFixedHeight(52)
        form.addRow("描述", self._desc_edit)

        self._summary_edit = QPlainTextEdit()
        self._summary_edit.setFixedHeight(80)
        self._summary_edit.setPlaceholderText("摘要（支持 Markdown）")
        form.addRow("摘要", self._summary_edit)

        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("输出路径（可选）")
        form.addRow("输出路径", self._path_edit)

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("逗号分隔标签")
        form.addRow("标签", self._tags_edit)

        root.addWidget(grp)

        rel_grp = QGroupBox("关联资源（ID）")
        rf = QFormLayout(rel_grp)
        self._exp_edit    = QLineEdit(); rf.addRow("关联实验",   self._exp_edit)
        self._st_edit     = QLineEdit(); rf.addRow("关联策略",   self._st_edit)
        self._bt_edit     = QLineEdit(); rf.addRow("关联回测",   self._bt_edit)
        self._ft_edit     = QLineEdit()
        self._ft_edit.setPlaceholderText("因子 ID，逗号分隔")
        rf.addRow("关联因子", self._ft_edit)
        self._ml_edit     = QLineEdit()
        self._ml_edit.setPlaceholderText("模型 ID，逗号分隔")
        rf.addRow("关联模型", self._ml_edit)
        root.addWidget(rel_grp)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load(self):
        r = self._record
        self._title_edit.setText(r.title)
        idx = self._type_combo.findData(r.report_type)
        if idx >= 0: self._type_combo.setCurrentIndex(idx)
        self._author_edit.setText(r.author)
        self._desc_edit.setPlainText(r.description)
        self._summary_edit.setPlainText(r.summary)
        self._path_edit.setText(r.output_path)
        self._tags_edit.setText(", ".join(r.tags))
        self._exp_edit.setText(r.experiment_id or "")
        self._st_edit.setText(r.strategy_id or "")
        self._bt_edit.setText(r.backtest_id or "")
        self._ft_edit.setText(", ".join(r.feature_ids))
        self._ml_edit.setText(", ".join(r.model_ids))

    def _on_accept(self):
        if not self._title_edit.text().strip():
            self._title_edit.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]

    def get_title(self)       -> str:       return self._title_edit.text().strip()
    def get_type(self)        -> str:       return self._type_combo.currentData()
    def get_author(self)      -> str:       return self._author_edit.text().strip()
    def get_description(self) -> str:       return self._desc_edit.toPlainText().strip()
    def get_summary(self)     -> str:       return self._summary_edit.toPlainText().strip()
    def get_output_path(self) -> str:       return self._path_edit.text().strip()
    def get_tags(self)        -> List[str]: return self._split(self._tags_edit.text())
    def get_experiment_id(self) -> Optional[str]: return self._exp_edit.text().strip() or None
    def get_strategy_id(self)   -> Optional[str]: return self._st_edit.text().strip() or None
    def get_backtest_id(self)   -> Optional[str]: return self._bt_edit.text().strip() or None
    def get_feature_ids(self)   -> List[str]:     return self._split(self._ft_edit.text())
    def get_model_ids(self)     -> List[str]:     return self._split(self._ml_edit.text())


# ─────────────────────────────────────────────────────────────────────
# ReportDetailPanel
# ─────────────────────────────────────────────────────────────────────

class ReportDetailPanel(QTabWidget):
    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._current: Optional[ReportRecord] = None
        self._init_ui()

    def _init_ui(self):
        # 概览
        ov_w = QWidget(); ov_l = QVBoxLayout(ov_w)
        self._ov_table = QTableWidget(0, 2)
        self._ov_table.setHorizontalHeaderLabels(["属性", "值"])
        self._ov_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._ov_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ov_table.setAlternatingRowColors(True)
        ov_l.addWidget(self._ov_table)
        self.addTab(ov_w, "概览")

        # 摘要
        sum_w = QWidget(); sum_l = QVBoxLayout(sum_w)
        self._summary_edit = QTextEdit()
        self._summary_edit.setReadOnly(True)
        self._summary_edit.setFont(QFont("Consolas", 10))
        sum_l.addWidget(self._summary_edit)
        self.addTab(sum_w, "摘要")

        # 章节
        sec_w = QWidget(); sec_l = QVBoxLayout(sec_w)
        self._sec_table = QTableWidget(0, 4)
        self._sec_table.setHorizontalHeaderLabels(["章节 ID", "标题", "顺序", "内容预览"])
        self._sec_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._sec_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._sec_table.setAlternatingRowColors(True)
        sec_l.addWidget(self._sec_table)
        self.addTab(sec_w, "章节")

        # 关联资源
        rel_w = QWidget(); rel_l = QVBoxLayout(rel_w)
        self._rel_edit = QTextEdit()
        self._rel_edit.setReadOnly(True)
        self._rel_edit.setFont(QFont("Consolas", 10))
        rel_l.addWidget(self._rel_edit)
        self.addTab(rel_w, "关联资源")

    def load(self, record: ReportRecord):
        self._current = record
        self._load_ov(record)
        self._summary_edit.setPlainText(record.summary)
        self._load_sections(record)
        self._load_relations(record)

    def _load_ov(self, r: ReportRecord):
        self._ov_table.setRowCount(0)
        rows = [
            ("ID", r.report_id), ("标题", r.title), ("类型", r.report_type),
            ("作者", r.author),
            ("发布状态", "已发布" if r.is_published else "草稿"),
            ("浏览次数", str(r.view_count)),
            ("输出路径", r.output_path),
            ("标签", ", ".join(r.tags)),
            ("创建时间", r.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("更新时间", r.updated_at.strftime("%Y-%m-%d %H:%M:%S")),
        ]
        if r.published_at:
            rows.append(("发布时间", r.published_at.strftime("%Y-%m-%d %H:%M")))
        rows.append(("描述", r.description))
        for k, v in rows:
            row = self._ov_table.rowCount()
            self._ov_table.insertRow(row)
            self._ov_table.setItem(row, 0, QTableWidgetItem(k))
            self._ov_table.setItem(row, 1, QTableWidgetItem(str(v)))

    def _load_sections(self, r: ReportRecord):
        self._sec_table.setRowCount(0)
        for sec in sorted(r.sections, key=lambda s: s.order):
            row = self._sec_table.rowCount()
            self._sec_table.insertRow(row)
            preview = sec.content[:60].replace("\n", " ") + ("…" if len(sec.content) > 60 else "")
            for col, v in enumerate([sec.section_id, sec.title, str(sec.order), preview]):
                self._sec_table.setItem(row, col, QTableWidgetItem(v))

    def _load_relations(self, r: ReportRecord):
        lines = []
        for label, rid, getter in [
            ("■ 关联实验",   r.experiment_id, self._engine.get_experiment),
            ("■ 关联策略",   r.strategy_id,   self._engine.get_strategy),
            ("■ 关联回测",   r.backtest_id,   self._engine.get_backtest),
        ]:
            if rid:
                obj = getter(rid)
                name = obj.name if obj else rid
                lines.append(f"{label}：{rid}  {name}")
            else:
                lines.append(f"{label}：无")
        lines.append("")
        for label, ids, getter in [
            ("■ 关联因子", r.feature_ids, self._engine.get_feature),
            ("■ 关联模型", r.model_ids,   self._engine.get_model),
        ]:
            if ids:
                lines.append(f"{label}：")
                for rid in ids:
                    obj = getter(rid)
                    name = obj.name if obj else rid
                    lines.append(f"  ├─ {rid}  {name}")
            else:
                lines.append(f"{label}：无")
            lines.append("")
        self._rel_edit.setPlainText("\n".join(lines))

    def clear(self):
        self._current = None
        self._ov_table.setRowCount(0)
        self._summary_edit.clear()
        self._sec_table.setRowCount(0)
        self._rel_edit.clear()


class ReportTab(QWidget):
    """报告中心主 Tab。"""
    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._all_records: List[ReportRecord] = []
        self._init_ui()
        self._register_events()
        self._refresh()
    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(6,6,6,6)
        bar1 = QHBoxLayout()
        self._btn_new     = QPushButton('+ 新建报告')
        self._btn_edit    = QPushButton('编辑')
        self._btn_delete  = QPushButton('删除')
        self._btn_publish = QPushButton('发布')
        self._btn_unpub   = QPushButton('取消发布')
        self._btn_section = QPushButton('添加章节')
        for btn in (self._btn_new, self._btn_edit, self._btn_delete,
                    self._btn_publish, self._btn_unpub, self._btn_section):
            bar1.addWidget(btn)
        bar1.addStretch(); root.addLayout(bar1)
        bar2 = QHBoxLayout()
        bar2.addWidget(QLabel('类型:'))
        self._type_filter = QComboBox()
        self._type_filter.addItem('全部', None)
        for t in REPORT_TYPES: self._type_filter.addItem(t, t)
        self._type_filter.setFixedWidth(110); bar2.addWidget(self._type_filter)
        bar2.addWidget(QLabel('搜索:'))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText('标题 / 作者 / 摘要')
        self._search_box.setFixedWidth(180); bar2.addWidget(self._search_box)
        self._btn_search = QPushButton('搜索'); self._btn_search.setFixedWidth(52)
        bar2.addWidget(self._btn_search)
        self._btn_reset = QPushButton('重置'); self._btn_reset.setFixedWidth(52)
        bar2.addWidget(self._btn_reset)
        bar2.addStretch(); root.addLayout(bar2)
        splitter = QSplitter(Qt.Vertical)
        self._table = QTableWidget(0, len(HEADERS))
        self._table.setHorizontalHeaderLabels(HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(COL_TITLE, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(COL_ID, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        splitter.addWidget(self._table)
        self._detail = ReportDetailPanel(self._engine)
        self._detail.setMinimumHeight(220)
        splitter.addWidget(self._detail)
        splitter.setSizes([340, 260]); root.addWidget(splitter)
        self._status_bar = QLabel('共 0 条报告'); root.addWidget(self._status_bar)
        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_publish.clicked.connect(self._on_publish)
        self._btn_unpub.clicked.connect(self._on_unpublish)
        self._btn_section.clicked.connect(self._on_add_section)
        self._btn_search.clicked.connect(self._apply_filter)
        self._btn_reset.clicked.connect(self._reset_filter)
        self._search_box.returnPressed.connect(self._apply_filter)
        self._type_filter.currentIndexChanged.connect(self._apply_filter)
        self._table.currentCellChanged.connect(self._on_row_changed)
        self._table.doubleClicked.connect(self._on_edit)
    def _register_events(self):
        ee = self._engine.event_engine
        ee.register(EVENT_REPORT_CREATED, self._on_event)
        ee.register(EVENT_REPORT_UPDATED, self._on_event)
    def _on_event(self, event: Event):
        # 使用定时器延迟刷新，避免阻塞UI
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._refresh)
    def _refresh(self):
        self._all_records = self._engine.list_reports()
        self._apply_filter()
    def _apply_filter(self):
        rtype   = self._type_filter.currentData()
        keyword = self._search_box.text().strip()
        records = self._engine.search_reports(keyword) if keyword else self._engine.list_reports(report_type=rtype)
        self._populate_table(records)
    def _reset_filter(self):
        self._type_filter.setCurrentIndex(0); self._search_box.clear()
        self._populate_table(self._all_records)
    def _populate_table(self, records):
        self._table.setSortingEnabled(False); self._table.setRowCount(0)
        for rec in records:
            r = self._table.rowCount(); self._table.insertRow(r); self._set_row(r, rec)
        self._table.setSortingEnabled(True)
        self._status_bar.setText(f'共 {len(records)} 条报告')
    def _set_row(self, row: int, rec: ReportRecord):
        id_item = QTableWidgetItem(rec.report_id)
        id_item.setData(Qt.UserRole, rec.report_id)
        self._table.setItem(row, COL_ID, id_item)
        self._table.setItem(row, COL_TITLE,  QTableWidgetItem(rec.title))
        self._table.setItem(row, COL_TYPE,   QTableWidgetItem(rec.report_type))
        self._table.setItem(row, COL_AUTHOR, QTableWidgetItem(rec.author))
        pub_item = QTableWidgetItem('✓' if rec.is_published else '—')
        pub_item.setTextAlignment(Qt.AlignCenter)
        pub_item.setForeground(PUB_COLOR if rec.is_published else UNPUB_COLOR)
        self._table.setItem(row, COL_PUB, pub_item)
        v_item = QTableWidgetItem(str(rec.view_count))
        v_item.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(row, COL_VIEWS, v_item)
        self._table.setItem(row, COL_TIME,
            QTableWidgetItem(rec.updated_at.strftime('%Y-%m-%d %H:%M')))
    def _on_row_changed(self, cur_row, *_):
        rec = self._get_record_at(cur_row)
        if rec: self._detail.load(rec)
        else:   self._detail.clear()
    def _on_new(self):
        dlg = ReportCreateDialog(parent=self)
        if dlg.exec() == ReportCreateDialog.Accepted:
            self._engine.create_report(
                title=dlg.get_title(), report_type=dlg.get_type(),
                description=dlg.get_description(), author=dlg.get_author(),
                summary=dlg.get_summary(), output_path=dlg.get_output_path(),
                experiment_id=dlg.get_experiment_id(),
                strategy_id=dlg.get_strategy_id(),
                backtest_id=dlg.get_backtest_id(),
                feature_ids=dlg.get_feature_ids(),
                model_ids=dlg.get_model_ids(),
                tags=dlg.get_tags(),
            )
            self._refresh()
    def _on_edit(self):
        rec = self._get_selected_record()
        if not rec: return
        dlg = ReportCreateDialog(parent=self, record=rec)
        if dlg.exec() == ReportCreateDialog.Accepted:
            rec.title         = dlg.get_title()
            rec.report_type   = dlg.get_type()
            rec.description   = dlg.get_description()
            rec.author        = dlg.get_author()
            rec.summary       = dlg.get_summary()
            rec.output_path   = dlg.get_output_path()
            rec.experiment_id = dlg.get_experiment_id()
            rec.strategy_id   = dlg.get_strategy_id()
            rec.backtest_id   = dlg.get_backtest_id()
            rec.feature_ids   = dlg.get_feature_ids()
            rec.model_ids     = dlg.get_model_ids()
            rec.tags          = dlg.get_tags()
            self._engine.update_report(rec)
            self._refresh()
    def _on_delete(self):
        rec = self._get_selected_record()
        if rec: self._engine.delete_report(rec.report_id)
    def _on_publish(self):
        rec = self._get_selected_record()
        if rec:
            self._engine.publish_report(rec.report_id)
            self._refresh()
            # 刷新详情面板
            updated = self._engine.get_report(rec.report_id)
            if updated:
                self._detail.load(updated)
    def _on_unpublish(self):
        rec = self._get_selected_record()
        if rec:
            self._engine.unpublish_report(rec.report_id)
            self._refresh()
            updated = self._engine.get_report(rec.report_id)
            if updated:
                self._detail.load(updated)
    def _on_add_section(self):
        rec = self._get_selected_record()
        if not rec: return
        from PySide6.QtWidgets import QInputDialog
        title, ok = QInputDialog.getText(self, '添加章节', '章节标题：')
        if ok and title.strip():
            self._engine.add_report_section(rec.report_id, title.strip())
            # 重新加载详情面板以显示新章节
            updated = self._engine.get_report(rec.report_id)
            if updated:
                self._detail.load(updated)
                self._detail.setCurrentIndex(2)  # 切换到"章节"tab
    def _get_record_at(self, row):
        item = self._table.item(row, COL_ID)
        if item is None: return None
        return self._engine.get_report(item.data(Qt.UserRole))
    def _get_selected_record(self):
        return self._get_record_at(self._table.currentRow())
