"""
quant_research/ui/backtest_tab.py

BacktestTab — Phase 7 完整实现。
"""
from __future__ import annotations
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from vnpy.event import Event

from ..engine import ResearchEngine
from ..constant import BacktestStatus
from ..event import (
    EVENT_BACKTEST_CREATED,
    EVENT_BACKTEST_UPDATED,
    EVENT_BACKTEST_DELETED,
)
from ..model.backtest_model import BacktestRecord, DailyEquity
from .backtest_dialogs import BacktestSubmitDialog, BacktestCompleteDialog

STATUS_COLORS = {
    BacktestStatus.PENDING:   QColor("#6c757d"),
    BacktestStatus.RUNNING:   QColor("#0d6efd"),
    BacktestStatus.COMPLETED: QColor("#198754"),
    BacktestStatus.FAILED:    QColor("#dc3545"),
}

COL_ID       = 0
COL_NAME     = 1
COL_STATUS   = 2
COL_STRATEGY = 3
COL_RETURN   = 4
COL_DD       = 5
COL_SHARPE   = 6
COL_DATES    = 7
COL_TIME     = 8

HEADERS = ["回测 ID", "名称", "状态", "策略",
           "年化%", "最大回撤%", "Sharpe",
           "回测区间", "提交时间"]


def _card(title: str) -> QWidget:
    w = QWidget()
    w.setStyleSheet("background:#f8f9fa; border-radius:6px;")
    lyt = QVBoxLayout(w)
    lyt.setContentsMargins(8, 4, 8, 4)
    t = QLabel(title)
    t.setAlignment(Qt.AlignCenter)
    t.setStyleSheet("color:#666; font-size:11px;")
    v = QLabel("—")
    v.setAlignment(Qt.AlignCenter)
    v.setStyleSheet("font-size:15px; font-weight:bold;")
    v.setObjectName("val")
    lyt.addWidget(t)
    lyt.addWidget(v)
    return w


def _set_card(card: QWidget, value: float,
              fmt: str = ".4f", positive_good: bool = True):
    lbl = card.findChild(QLabel, "val")
    if not lbl:
        return
    lbl.setText(f"{value:{fmt}}")
    if positive_good:
        color = "#198754" if value > 0 else "#dc3545" if value < 0 else "#333"
    else:
        color = "#dc3545" if value < 0 else "#fd7e14" if value != 0 else "#333"
    lbl.setStyleSheet(f"font-size:15px; font-weight:bold; color:{color};")


class BacktestDetailPanel(QTabWidget):
    """底部详情：概览 / 绩效指标 / 净值曲线 / 月度收益 / 关联资源。"""

    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._current: Optional[BacktestRecord] = None
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
        self._c_ann    = _card("年化收益")
        self._c_tot    = _card("总收益")
        self._c_dd     = _card("最大回撤")
        self._c_sharpe = _card("Sharpe")
        self._c_sortino= _card("Sortino")
        self._c_calmar = _card("Calmar")
        for c in (self._c_ann, self._c_tot, self._c_dd,
                  self._c_sharpe, self._c_sortino, self._c_calmar):
            row1.addWidget(c)
        perf_l.addLayout(row1)

        row2 = QHBoxLayout()
        self._c_wr     = _card("胜率")
        self._c_turn   = _card("换手率")
        self._c_pf     = _card("盈亏比")
        self._c_alpha  = _card("Alpha")
        self._c_beta   = _card("Beta")
        self._c_ir     = _card("信息比率")
        for c in (self._c_wr, self._c_turn, self._c_pf,
                  self._c_alpha, self._c_beta, self._c_ir):
            row2.addWidget(c)
        perf_l.addLayout(row2)

        stats_lyt = QHBoxLayout()
        self._lbl_trades = QLabel("总交易次数：—")
        self._lbl_ahd    = QLabel("平均持仓：—")
        self._lbl_mpc    = QLabel("最大集中度：—")
        for lbl in (self._lbl_trades, self._lbl_ahd, self._lbl_mpc):
            lbl.setStyleSheet("color:#555; padding:4px;")
            stats_lyt.addWidget(lbl)
        stats_lyt.addStretch()
        perf_l.addLayout(stats_lyt)
        perf_l.addStretch()
        self.addTab(perf_w, "绩效指标")

        # ── 净值曲线 ──────────────────────────────────────────────────
        eq_w = QWidget()
        eq_l = QVBoxLayout(eq_w)
        self._equity_table = QTableWidget(0, 5)
        self._equity_table.setHorizontalHeaderLabels(
            ["日期", "净值", "日收益%", "回撤%", "基准%"])
        self._equity_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._equity_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._equity_table.setAlternatingRowColors(True)
        eq_l.addWidget(self._equity_table)
        self.addTab(eq_w, "净值曲线")

        # ── 月度收益 ──────────────────────────────────────────────────
        mo_w = QWidget()
        mo_l = QVBoxLayout(mo_w)
        self._monthly_table = QTableWidget(0, 2)
        self._monthly_table.setHorizontalHeaderLabels(["月份", "收益%"])
        self._monthly_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self._monthly_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._monthly_table.setAlternatingRowColors(True)
        mo_l.addWidget(self._monthly_table)
        self.addTab(mo_w, "月度收益")

        # ── 关联资源 ──────────────────────────────────────────────────
        rel_w = QWidget()
        rel_l = QVBoxLayout(rel_w)
        self._rel_edit = QTextEdit()
        self._rel_edit.setReadOnly(True)
        self._rel_edit.setFont(QFont("Consolas", 10))
        rel_l.addWidget(self._rel_edit)
        self.addTab(rel_w, "关联资源")

    def load(self, record: BacktestRecord):
        self._current = record
        self._load_overview(record)
        self._load_perf(record)
        self._load_equity(record)
        self._load_monthly(record)
        self._load_relations(record)

    def _load_overview(self, r: BacktestRecord):
        self._overview_table.setRowCount(0)
        rows = [
            ("ID",       r.backtest_id),
            ("名称",     r.name),
            ("状态",     r.status.value),
            ("策略 ID",  r.strategy_id),
            ("策略名称", r.strategy_name),
            ("标的池",   r.universe),
            ("回测区间", f"{r.start_date} ~ {r.end_date}"),
            ("初始资金", f"{r.initial_capital:,.0f}"),
            ("手续费率", f"{r.commission:.4%}"),
            ("滑点",     f"{r.slippage:.4%}"),
            ("标签",     ", ".join(r.tags)),
            ("提交人",   r.created_by),
            ("提交时间", r.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("更新时间", r.updated_at.strftime("%Y-%m-%d %H:%M:%S")),
        ]
        if r.completed_at:
            rows.append(("完成时间", r.completed_at.strftime("%Y-%m-%d %H:%M")))
        if r.error_msg:
            rows.append(("错误信息", r.error_msg))
        rows.append(("描述", r.description))
        for k, v in rows:
            row = self._overview_table.rowCount()
            self._overview_table.insertRow(row)
            self._overview_table.setItem(row, 0, QTableWidgetItem(k))
            self._overview_table.setItem(row, 1, QTableWidgetItem(str(v)))

    def _load_perf(self, r: BacktestRecord):
        _set_card(self._c_ann,    r.annual_return,     ".2%",  True)
        _set_card(self._c_tot,    r.total_return,      ".2%",  True)
        _set_card(self._c_dd,     r.max_drawdown,      ".2%",  False)
        _set_card(self._c_sharpe, r.sharpe,            ".4f",  True)
        _set_card(self._c_sortino,r.sortino,           ".4f",  True)
        _set_card(self._c_calmar, r.calmar,            ".4f",  True)
        _set_card(self._c_wr,     r.win_rate,          ".2%",  True)
        _set_card(self._c_turn,   r.turnover,          ".2f",  False)
        _set_card(self._c_pf,     r.profit_factor,     ".4f",  True)
        _set_card(self._c_alpha,  r.alpha,             ".4f",  True)
        _set_card(self._c_beta,   r.beta,              ".4f",  True)
        _set_card(self._c_ir,     r.information_ratio, ".4f",  True)
        self._lbl_trades.setText(f"总交易次数：{r.total_trades:,}")
        self._lbl_ahd.setText(f"平均持仓：{r.avg_holding_days:.1f} 天")
        self._lbl_mpc.setText(f"最大集中度：{r.max_position_conc:.2%}")

    def _load_equity(self, r: BacktestRecord):
        self._equity_table.setRowCount(0)
        for eq in r.equity_curve:
            row = self._equity_table.rowCount()
            self._equity_table.insertRow(row)
            vals = [eq.date, f"{eq.equity:.4f}",
                    f"{eq.returns:.2%}", f"{eq.drawdown:.2%}",
                    f"{eq.benchmark:.2%}"]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignCenter)
                if col == 2:
                    item.setForeground(QColor(
                        "#198754" if eq.returns > 0
                        else "#dc3545" if eq.returns < 0
                        else "#333"))
                self._equity_table.setItem(row, col, item)

    def _load_monthly(self, r: BacktestRecord):
        self._monthly_table.setRowCount(0)
        for month in sorted(r.monthly_returns):
            v = r.monthly_returns[month]
            row = self._monthly_table.rowCount()
            self._monthly_table.insertRow(row)
            self._monthly_table.setItem(row, 0, QTableWidgetItem(month))
            val_item = QTableWidgetItem(f"{v:.2%}")
            val_item.setTextAlignment(Qt.AlignCenter)
            bg = (QColor("#d4edda") if v > 0.01
                  else QColor("#f8d7da") if v < -0.01
                  else QColor("#fff3cd"))
            val_item.setBackground(bg)
            self._monthly_table.setItem(row, 1, val_item)

    def _load_relations(self, r: BacktestRecord):
        lines = []
        for label, ids, getter in [
            ("■ 依赖模型",   r.model_ids,   self._engine.get_model),
            ("■ 依赖因子",   r.feature_ids, self._engine.get_feature),
            ("■ 依赖数据集", r.dataset_ids, self._engine.get_dataset),
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
        self._overview_table.setRowCount(0)
        self._equity_table.setRowCount(0)
        self._monthly_table.setRowCount(0)
        self._rel_edit.clear()


class BacktestTab(QWidget):
    """回测注册中心主 Tab。"""
    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._all_records: List[BacktestRecord] = []
        self._init_ui()
        self._register_events()
        self._refresh()
    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        bar1 = QHBoxLayout()
        self._btn_new      = QPushButton('+ 提交回测')
        self._btn_edit     = QPushButton('编辑')
        self._btn_delete   = QPushButton('删除')
        self._btn_run      = QPushButton('标记运行中')
        self._btn_complete = QPushButton('填入结果')
        self._btn_fail     = QPushButton('标记失败')
        self._btn_compare  = QPushButton('对比选中')
        for btn in (self._btn_new, self._btn_edit, self._btn_delete,
                    self._btn_run, self._btn_complete,
                    self._btn_fail, self._btn_compare):
            bar1.addWidget(btn)
        bar1.addStretch()
        root.addLayout(bar1)
        bar2 = QHBoxLayout()
        bar2.addWidget(QLabel('状态:'))
        self._status_filter = QComboBox()
        self._status_filter.addItem('全部', None)
        for s in BacktestStatus:
            self._status_filter.addItem(s.value, s)
        self._status_filter.setFixedWidth(120)
        bar2.addWidget(self._status_filter)
        bar2.addWidget(QLabel('搜索:'))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText('名称 / 策略 / 标的池')
        self._search_box.setFixedWidth(200)
        bar2.addWidget(self._search_box)
        self._btn_search = QPushButton('搜索'); self._btn_search.setFixedWidth(52)
        bar2.addWidget(self._btn_search)
        self._btn_reset = QPushButton('重置'); self._btn_reset.setFixedWidth(52)
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
        self._table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        splitter.addWidget(self._table)
        self._detail = BacktestDetailPanel(self._engine)
        self._detail.setMinimumHeight(260)
        splitter.addWidget(self._detail)
        splitter.setSizes([360, 300])
        root.addWidget(splitter)
        self._status_bar = QLabel('共 0 条回测')
        root.addWidget(self._status_bar)
        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_run.clicked.connect(self._on_run)
        self._btn_complete.clicked.connect(self._on_complete)
        self._btn_fail.clicked.connect(self._on_fail)
        self._btn_compare.clicked.connect(self._on_compare)
        self._btn_search.clicked.connect(self._apply_filter)
        self._btn_reset.clicked.connect(self._reset_filter)
        self._search_box.returnPressed.connect(self._apply_filter)
        self._status_filter.currentIndexChanged.connect(self._apply_filter)
        self._table.currentCellChanged.connect(self._on_row_changed)
        self._table.doubleClicked.connect(self._on_edit)
    def _register_events(self):
        ee = self._engine.event_engine
        ee.register(EVENT_BACKTEST_CREATED, self._on_event)
        ee.register(EVENT_BACKTEST_UPDATED, self._on_event)
        ee.register(EVENT_BACKTEST_DELETED, self._on_event)
    def _on_event(self, event: Event): self._refresh()
    def _refresh(self):
        self._all_records = self._engine.list_backtests()
        self._apply_filter()
    def _apply_filter(self):
        status  = self._status_filter.currentData()
        keyword = self._search_box.text().strip()
        records = self._engine.search_backtests(keyword) if keyword else self._engine.list_backtests(status=status)
        self._populate_table(records)
    def _reset_filter(self):
        self._status_filter.setCurrentIndex(0)
        self._search_box.clear()
        self._populate_table(self._all_records)
    def _populate_table(self, records):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        for rec in records:
            r = self._table.rowCount(); self._table.insertRow(r); self._set_row(r, rec)
        self._table.setSortingEnabled(True)
        self._status_bar.setText(f'共 {len(records)} 条回测')
    def _set_row(self, row: int, rec: BacktestRecord):
        id_item = QTableWidgetItem(rec.backtest_id)
        id_item.setData(Qt.UserRole, rec.backtest_id)
        self._table.setItem(row, COL_ID, id_item)
        self._table.setItem(row, COL_NAME, QTableWidgetItem(rec.name))
        st_item = QTableWidgetItem(rec.status.value)
        st_item.setForeground(STATUS_COLORS.get(rec.status, QColor('#333')))
        f = QFont(); f.setBold(True); st_item.setFont(f)
        self._table.setItem(row, COL_STATUS, st_item)
        self._table.setItem(row, COL_STRATEGY, QTableWidgetItem(rec.strategy_name or rec.strategy_id))
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
        self._table.setItem(row, COL_DATES, QTableWidgetItem(f'{rec.start_date} ~ {rec.end_date}'))
        self._table.setItem(row, COL_TIME, QTableWidgetItem(rec.created_at.strftime('%Y-%m-%d %H:%M')))
    def _on_row_changed(self, cur_row, *_):
        rec = self._get_record_at(cur_row)
        if rec: self._detail.load(rec)
        else:   self._detail.clear()
    def _on_new(self):
        dlg = BacktestSubmitDialog(parent=self)
        if dlg.exec() == BacktestSubmitDialog.Accepted:
            self._engine.submit_backtest(
                name=dlg.get_name(), strategy_id=dlg.get_strategy_id(),
                strategy_name=dlg.get_strategy_name(),
                description=dlg.get_description(),
                start_date=dlg.get_start_date(), end_date=dlg.get_end_date(),
                initial_capital=dlg.get_initial_capital(),
                commission=dlg.get_commission(), slippage=dlg.get_slippage(),
                universe=dlg.get_universe(), tags=dlg.get_tags(),
                feature_ids=dlg.get_feature_ids(),
                dataset_ids=dlg.get_dataset_ids(),
                model_ids=dlg.get_model_ids(),
                created_by=dlg.get_author(),
            )
    def _on_edit(self):
        rec = self._get_selected_record()
        if not rec: return
        dlg = BacktestSubmitDialog(parent=self, record=rec)
        if dlg.exec() == BacktestSubmitDialog.Accepted:
            rec.name            = dlg.get_name()
            rec.strategy_id     = dlg.get_strategy_id()
            rec.strategy_name   = dlg.get_strategy_name()
            rec.description     = dlg.get_description()
            rec.start_date      = dlg.get_start_date()
            rec.end_date        = dlg.get_end_date()
            rec.initial_capital = dlg.get_initial_capital()
            rec.commission      = dlg.get_commission()
            rec.slippage        = dlg.get_slippage()
            rec.universe        = dlg.get_universe()
            rec.tags            = dlg.get_tags()
            rec.feature_ids     = dlg.get_feature_ids()
            rec.dataset_ids     = dlg.get_dataset_ids()
            rec.model_ids       = dlg.get_model_ids()
            self._engine.update_backtest(rec)
    def _on_delete(self):
        rec = self._get_selected_record()
        if rec: self._engine.delete_backtest(rec.backtest_id)
    def _on_run(self):
        rec = self._get_selected_record()
        if rec: self._engine.run_backtest(rec.backtest_id)
    def _on_complete(self):
        rec = self._get_selected_record()
        if not rec: return
        dlg = BacktestCompleteDialog(rec.name, parent=self)
        if dlg.exec() == BacktestCompleteDialog.Accepted:
            self._engine.complete_backtest(
                rec.backtest_id,
                annual_return=dlg.get_annual_return(),
                max_drawdown=dlg.get_max_drawdown(),
                sharpe=dlg.get_sharpe(), sortino=dlg.get_sortino(),
                calmar=dlg.get_calmar(), win_rate=dlg.get_win_rate(),
                turnover=dlg.get_turnover(),
                profit_factor=dlg.get_profit_factor(),
                total_return=dlg.get_total_return(),
                alpha=dlg.get_alpha(), beta=dlg.get_beta(),
                information_ratio=dlg.get_information_ratio(),
                total_trades=dlg.get_total_trades(),
                avg_holding_days=dlg.get_avg_holding_days(),
                max_position_conc=dlg.get_max_position_conc(),
                monthly_returns=dlg.get_monthly_returns(),
            )
    def _on_fail(self):
        rec = self._get_selected_record()
        if not rec: return
        from PySide6.QtWidgets import QInputDialog
        msg, ok = QInputDialog.getText(self, '标记失败', '错误信息（可留空）：')
        if ok: self._engine.fail_backtest(rec.backtest_id, msg)
    def _on_compare(self):
        rows = {idx.row() for idx in self._table.selectedIndexes()}
        ids = []
        for r in rows:
            item = self._table.item(r, COL_ID)
            if item: ids.append(item.data(Qt.UserRole))
        if len(ids) < 2: return
        records = self._engine.compare_backtests(ids)
        self._show_compare(records)
    def _show_compare(self, records):
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle(f'对比 {len(records)} 条回测')
        dlg.setMinimumSize(820, 400)
        lyt = QVBoxLayout(dlg)
        cols = ['名称','年化%','最大回撤%','Sharpe','Sortino','胜率%','换手率','总收益%']
        tbl = QTableWidget(len(records), len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for i, rec in enumerate(records):
            vals = [rec.name, f'{rec.annual_return:.2%}',
                    f'{rec.max_drawdown:.2%}', f'{rec.sharpe:.4f}',
                    f'{rec.sortino:.4f}', f'{rec.win_rate:.2%}',
                    f'{rec.turnover:.2f}', f'{rec.total_return:.2%}']
            for j, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignCenter)
                tbl.setItem(i, j, item)
        lyt.addWidget(tbl)
        dlg.exec()
    def _get_record_at(self, row):
        item = self._table.item(row, COL_ID)
        if item is None: return None
        return self._engine.get_backtest(item.data(Qt.UserRole))
    def _get_selected_record(self):
        return self._get_record_at(self._table.currentRow())
