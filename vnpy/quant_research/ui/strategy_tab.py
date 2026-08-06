"""
quant_research/ui/strategy_tab.py

StrategyTab — Phase 5 完整实现。
"""
from __future__ import annotations
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from vnpy.event import Event

from ..engine import ResearchEngine
from ..constant import StrategyStatus
from ..event import (
    EVENT_STRATEGY_CREATED,
    EVENT_STRATEGY_UPDATED,
    EVENT_STRATEGY_DELETED,
)
from ..model.strategy_model import StrategyRecord, StrategyVersion, STRATEGY_TYPES
from .strategy_dialogs import (
    StrategyCreateDialog,
    StrategyPerformanceDialog,
    StrategyVersionDialog,
)

STATUS_COLORS = {
    StrategyStatus.DRAFT:    QColor("#6c757d"),
    StrategyStatus.TESTING:  QColor("#0d6efd"),
    StrategyStatus.LIVE:     QColor("#198754"),
    StrategyStatus.RETIRED:  QColor("#adb5bd"),
}

COL_ID      = 0
COL_NAME    = 1
COL_VERSION = 2
COL_TYPE    = 3
COL_STATUS  = 4
COL_RETURN  = 5
COL_DD      = 6
COL_SHARPE  = 7
COL_AUTHOR  = 8
COL_TIME    = 9

HEADERS = ["策略 ID", "名称", "版本", "类型", "状态",
           "年化%", "最大回撤%", "Sharpe", "作者", "更新时间"]


# ─────────────────────────────────────────────────────────────────────
# 指标卡片辅助
# ─────────────────────────────────────────────────────────────────────

def _metric_card(title: str, value: str = "—") -> QWidget:
    card = QWidget()
    card.setStyleSheet(
        "background:#f8f9fa; border-radius:6px; padding:4px;")
    lyt = QVBoxLayout(card)
    lyt.setContentsMargins(8, 4, 8, 4)
    t = QLabel(title)
    t.setAlignment(Qt.AlignCenter)
    t.setStyleSheet("color:#666; font-size:11px;")
    v = QLabel(value)
    v.setAlignment(Qt.AlignCenter)
    v.setStyleSheet("font-size:16px; font-weight:bold;")
    v.setObjectName("val")
    lyt.addWidget(t)
    lyt.addWidget(v)
    return card


def _set_card(card: QWidget, value: float,
              fmt: str = ".2%", positive_good: bool = True):
    lbl = card.findChild(QLabel, "val")
    if not lbl:
        return
    lbl.setText(f"{value:{fmt}}")
    if positive_good:
        color = "#198754" if value > 0 else "#dc3545" if value < 0 else "#333"
    else:
        color = "#dc3545" if value < 0 else "#198754" if value == 0 else "#fd7e14"
    lbl.setStyleSheet(f"font-size:16px; font-weight:bold; color:{color};")


# ─────────────────────────────────────────────────────────────────────
# StrategyDetailPanel
# ─────────────────────────────────────────────────────────────────────

class StrategyDetailPanel(QTabWidget):
    """底部详情：概览 / 绩效指标 / 版本历史 / 关联资源。"""

    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._current: Optional[StrategyRecord] = None
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

        # ── 绩效指标 ──────────────────────────────────────────────────
        perf_w = QWidget()
        perf_l = QVBoxLayout(perf_w)

        row1 = QHBoxLayout()
        self._c_annual  = _metric_card("年化收益")
        self._c_dd      = _metric_card("最大回撤")
        self._c_sharpe  = _metric_card("Sharpe")
        self._c_sortino = _metric_card("Sortino")
        for c in (self._c_annual, self._c_dd, self._c_sharpe, self._c_sortino):
            row1.addWidget(c)
        perf_l.addLayout(row1)

        row2 = QHBoxLayout()
        self._c_calmar  = _metric_card("Calmar")
        self._c_winrate = _metric_card("胜率")
        self._c_turn    = _metric_card("换手率")
        self._c_pf      = _metric_card("盈亏比")
        for c in (self._c_calmar, self._c_winrate, self._c_turn, self._c_pf):
            row2.addWidget(c)
        perf_l.addLayout(row2)
        perf_l.addStretch()
        self.addTab(perf_w, "绩效指标")

        # ── 版本历史 ──────────────────────────────────────────────────
        ver_w = QWidget()
        ver_l = QVBoxLayout(ver_w)
        self._ver_table = QTableWidget(0, 4)
        self._ver_table.setHorizontalHeaderLabels(
            ["版本 ID", "版本号", "变更说明", "时间"])
        self._ver_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._ver_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ver_table.setAlternatingRowColors(True)
        ver_l.addWidget(self._ver_table)
        self.addTab(ver_w, "版本历史")

        # ── 关联资源 ──────────────────────────────────────────────────
        rel_w = QWidget()
        rel_l = QVBoxLayout(rel_w)
        self._rel_edit = QTextEdit()
        self._rel_edit.setReadOnly(True)
        self._rel_edit.setFont(QFont("Consolas", 10))
        rel_l.addWidget(self._rel_edit)
        self.addTab(rel_w, "关联资源")

    def load(self, record: StrategyRecord):
        self._current = record
        self._load_overview(record)
        self._load_performance(record)
        self._load_versions(record)
        self._load_relations(record)

    def _load_overview(self, r: StrategyRecord):
        self._overview_table.setRowCount(0)
        rows = [
            ("ID",       r.strategy_id),
            ("名称",     r.name),
            ("版本",     r.version),
            ("状态",     r.status.value),
            ("类型",     r.strategy_type),
            ("作者",     r.author),
            ("交易标的", r.universe),
            ("代码路径", r.code_path),
            ("标签",     ", ".join(r.tags)),
            ("创建时间", r.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("更新时间", r.updated_at.strftime("%Y-%m-%d %H:%M:%S")),
        ]
        if r.published_at:
            rows.append(("发布时间", r.published_at.strftime("%Y-%m-%d %H:%M")))
        if r.retired_at:
            rows.append(("下线时间", r.retired_at.strftime("%Y-%m-%d %H:%M")))
        rows.append(("描述", r.description))
        for k, v in rows:
            row = self._overview_table.rowCount()
            self._overview_table.insertRow(row)
            self._overview_table.setItem(row, 0, QTableWidgetItem(k))
            self._overview_table.setItem(row, 1, QTableWidgetItem(str(v)))

    def _load_performance(self, r: StrategyRecord):
        _set_card(self._c_annual,  r.annual_return,  ".2%",  True)
        _set_card(self._c_dd,      r.max_drawdown,   ".2%",  False)
        _set_card(self._c_sharpe,  r.sharpe,         ".4f",  True)
        _set_card(self._c_sortino, r.sortino,        ".4f",  True)
        _set_card(self._c_calmar,  r.calmar,         ".4f",  True)
        _set_card(self._c_winrate, r.win_rate,       ".2%",  True)
        _set_card(self._c_turn,    r.turnover,       ".2f",  False)
        _set_card(self._c_pf,      r.profit_factor,  ".4f",  True)

    def _load_versions(self, r: StrategyRecord):
        self._ver_table.setRowCount(0)
        for ver in reversed(r.versions):
            row = self._ver_table.rowCount()
            self._ver_table.insertRow(row)
            self._ver_table.setItem(row, 0, QTableWidgetItem(ver.version_id))
            self._ver_table.setItem(row, 1, QTableWidgetItem(ver.version))
            self._ver_table.setItem(row, 2, QTableWidgetItem(ver.note))
            self._ver_table.setItem(row, 3,
                QTableWidgetItem(ver.created_at.strftime("%Y-%m-%d %H:%M")))

    def _load_relations(self, r: StrategyRecord):
        lines = []
        if r.feature_ids:
            lines.append("■ 依赖因子：")
            for fid in r.feature_ids:
                ft = self._engine.get_feature(fid)
                name = ft.name if ft else fid
                lines.append(f"  ├─ {fid}  {name}")
        else:
            lines.append("■ 无关联因子")
        lines.append("")
        if r.dataset_ids:
            lines.append("■ 依赖数据集：")
            for did in r.dataset_ids:
                ds = self._engine.get_dataset(did)
                name = ds.name if ds else did
                lines.append(f"  ├─ {did}  {name}")
        else:
            lines.append("■ 无关联数据集")
        lines.append("")
        if r.backtest_ids:
            lines.append("■ 关联回测：")
            for bid in r.backtest_ids:
                lines.append(f"  ├─ {bid}")
        else:
            lines.append("■ 无关联回测")
        self._rel_edit.setPlainText("\n".join(lines))

    def clear(self):
        self._current = None
        self._overview_table.setRowCount(0)
        self._ver_table.setRowCount(0)
        self._rel_edit.clear()


class StrategyTab(QWidget):
    """策略注册中心主 Tab。"""

    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._all_records: List[StrategyRecord] = []
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        bar1 = QHBoxLayout()
        self._btn_new     = QPushButton('+ 注册策略')
        self._btn_edit    = QPushButton('编辑')
        self._btn_delete  = QPushButton('删除')
        self._btn_perf    = QPushButton('录入绩效')
        self._btn_version = QPushButton('新增版本快照')
        self._btn_publish = QPushButton('发布上线')
        self._btn_testing = QPushButton('移入测试')
        self._btn_retire  = QPushButton('下线')
        for btn in (self._btn_new, self._btn_edit, self._btn_delete,
                    self._btn_perf, self._btn_version,
                    self._btn_publish, self._btn_testing, self._btn_retire):
            bar1.addWidget(btn)
        bar1.addStretch()
        root.addLayout(bar1)
        bar2 = QHBoxLayout()
        bar2.addWidget(QLabel('状态:'))
        self._status_filter = QComboBox()
        self._status_filter.addItem('全部', None)
        for s in StrategyStatus:
            self._status_filter.addItem(s.value, s)
        self._status_filter.setFixedWidth(110)
        bar2.addWidget(self._status_filter)
        bar2.addWidget(QLabel('类型:'))
        self._type_filter = QComboBox()
        self._type_filter.addItem('全部', None)
        for t in STRATEGY_TYPES:
            self._type_filter.addItem(t, t)
        self._type_filter.setFixedWidth(130)
        bar2.addWidget(self._type_filter)
        bar2.addWidget(QLabel('搜索:'))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText('名称 / 类型 / 作者')
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
        self._detail = StrategyDetailPanel(self._engine)
        self._detail.setMinimumHeight(220)
        splitter.addWidget(self._detail)
        splitter.setSizes([380, 260])
        root.addWidget(splitter)
        self._status_bar = QLabel('共 0 条策略')
        root.addWidget(self._status_bar)
        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_perf.clicked.connect(self._on_perf)
        self._btn_version.clicked.connect(self._on_version)
        self._btn_publish.clicked.connect(self._on_publish)
        self._btn_testing.clicked.connect(self._on_testing)
        self._btn_retire.clicked.connect(self._on_retire)
        self._btn_search.clicked.connect(self._apply_filter)
        self._btn_reset.clicked.connect(self._reset_filter)
        self._search_box.returnPressed.connect(self._apply_filter)
        self._status_filter.currentIndexChanged.connect(self._apply_filter)
        self._type_filter.currentIndexChanged.connect(self._apply_filter)
        self._table.currentCellChanged.connect(self._on_row_changed)
        self._table.doubleClicked.connect(self._on_edit)

    def _register_events(self):
        ee = self._engine.event_engine
        ee.register(EVENT_STRATEGY_CREATED, self._on_event)
        ee.register(EVENT_STRATEGY_UPDATED, self._on_event)
        ee.register(EVENT_STRATEGY_DELETED, self._on_event)

    def _on_event(self, event: Event):
        # 使用定时器延迟刷新，避免阻塞UI
        from PySide6.QtCore import QTimer
        QTimer.singleShot(10, self._refresh)  # 减少延迟到10ms

    def _refresh(self):
        self._all_records = self._engine.list_strategies()
        self._apply_filter()

    def _apply_filter(self):
        status  = self._status_filter.currentData()
        stype   = self._type_filter.currentData()
        keyword = self._search_box.text().strip()
        if keyword:
            records = self._engine.search_strategies(keyword)
        else:
            records = self._engine.list_strategies(status=status, strategy_type=stype)
        self._populate_table(records)

    def _reset_filter(self):
        self._status_filter.setCurrentIndex(0)
        self._type_filter.setCurrentIndex(0)
        self._search_box.clear()
        self._populate_table(self._all_records)

    def _populate_table(self, records):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        for rec in records:
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._set_row(r, rec)
        self._table.setSortingEnabled(True)
        self._status_bar.setText(f'共 {len(records)} 条策略')

    def _set_row(self, row: int, rec: StrategyRecord):
        id_item = QTableWidgetItem(rec.strategy_id)
        id_item.setData(Qt.UserRole, rec.strategy_id)
        self._table.setItem(row, COL_ID, id_item)
        name_item = QTableWidgetItem(rec.name)
        if rec.status == StrategyStatus.RETIRED:
            f = QFont(); f.setStrikeOut(True); name_item.setFont(f)
            name_item.setForeground(QColor('#adb5bd'))
        self._table.setItem(row, COL_NAME, name_item)
        self._table.setItem(row, COL_VERSION, QTableWidgetItem(rec.version))
        self._table.setItem(row, COL_TYPE, QTableWidgetItem(rec.strategy_type))
        st_item = QTableWidgetItem(rec.status.value)
        st_item.setForeground(STATUS_COLORS.get(rec.status, QColor('#333')))
        f2 = QFont(); f2.setBold(True); st_item.setFont(f2)
        self._table.setItem(row, COL_STATUS, st_item)
        def _pct(v, good=True):
            item = QTableWidgetItem(f'{v:.2%}')
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item.setForeground(QColor('#198754' if (v > 0) == good else '#dc3545'))
            return item
        def _num(v):
            item = QTableWidgetItem(f'{v:.4f}')
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item.setForeground(QColor('#198754' if v > 0 else '#dc3545' if v < 0 else '#333'))
            return item
        self._table.setItem(row, COL_RETURN, _pct(rec.annual_return, True))
        self._table.setItem(row, COL_DD,     _pct(rec.max_drawdown, False))
        self._table.setItem(row, COL_SHARPE, _num(rec.sharpe))
        self._table.setItem(row, COL_AUTHOR, QTableWidgetItem(rec.author))
        self._table.setItem(row, COL_TIME,
            QTableWidgetItem(rec.updated_at.strftime('%Y-%m-%d %H:%M')))

    def _on_row_changed(self, cur_row, *_):
        rec = self._get_record_at(cur_row)
        if rec: self._detail.load(rec)
        else:   self._detail.clear()

    def _on_new(self):
        dlg = StrategyCreateDialog(parent=self)
        if dlg.exec() == StrategyCreateDialog.Accepted:
            self._engine.register_strategy(
                name=dlg.get_name(), version=dlg.get_version(),
                description=dlg.get_description(),
                strategy_type=dlg.get_strategy_type(),
                author=dlg.get_author(), universe=dlg.get_universe(),
                code_path=dlg.get_code_path(), params=dlg.get_params(),
                tags=dlg.get_tags(), feature_ids=dlg.get_feature_ids(),
                dataset_ids=dlg.get_dataset_ids(),
            )
            self._refresh()

    def _on_edit(self):
        rec = self._get_selected_record()
        if not rec: return
        dlg = StrategyCreateDialog(parent=self, record=rec)
        if dlg.exec() == StrategyCreateDialog.Accepted:
            rec.name          = dlg.get_name()
            rec.version       = dlg.get_version()
            rec.description   = dlg.get_description()
            rec.strategy_type = dlg.get_strategy_type()
            rec.author        = dlg.get_author()
            rec.status        = dlg.get_status()
            rec.universe      = dlg.get_universe()
            rec.code_path     = dlg.get_code_path()
            rec.params        = dlg.get_params()
            rec.tags          = dlg.get_tags()
            rec.feature_ids   = dlg.get_feature_ids()
            rec.dataset_ids   = dlg.get_dataset_ids()
            self._engine.update_strategy(rec)
            self._refresh()

    def _on_delete(self):
        rec = self._get_selected_record()
        if rec:
            self._engine.delete_strategy(rec.strategy_id)
            self._refresh()

    def _on_perf(self):
        rec = self._get_selected_record()
        if not rec: return
        dlg = StrategyPerformanceDialog(rec.name, parent=self)
        if dlg.exec() == StrategyPerformanceDialog.Accepted:
            self._engine.update_performance(
                rec.strategy_id,
                annual_return=dlg.get_annual_return(),
                max_drawdown=dlg.get_max_drawdown(),
                sharpe=dlg.get_sharpe(), sortino=dlg.get_sortino(),
                calmar=dlg.get_calmar(), win_rate=dlg.get_win_rate(),
                turnover=dlg.get_turnover(),
                profit_factor=dlg.get_profit_factor(),
            )
            self._refresh()

    def _on_version(self):
        rec = self._get_selected_record()
        if not rec: return
        dlg = StrategyVersionDialog(rec.name, parent=self)
        if dlg.exec() == StrategyVersionDialog.Accepted:
            self._engine.add_strategy_version(
                rec.strategy_id,
                note=dlg.get_note(), created_by=dlg.get_author(),
            )
            self._refresh()

    def _on_publish(self):
        rec = self._get_selected_record()
        if rec:
            self._engine.publish_strategy(rec.strategy_id)
            self._refresh()

    def _on_testing(self):
        rec = self._get_selected_record()
        if rec:
            self._engine.set_strategy_testing(rec.strategy_id)
            self._refresh()

    def _on_retire(self):
        rec = self._get_selected_record()
        if rec:
            self._engine.retire_strategy(rec.strategy_id)
            self._refresh()

    def _get_record_at(self, row):
        item = self._table.item(row, COL_ID)
        if item is None: return None
        return self._engine.get_strategy(item.data(Qt.UserRole))

    def _get_selected_record(self):
        return self._get_record_at(self._table.currentRow())
