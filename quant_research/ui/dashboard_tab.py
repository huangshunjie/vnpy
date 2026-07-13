"""
quant_research/ui/dashboard_tab.py  — Phase 8 完整实现
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QSplitter, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from vnpy.event import Event

from ..engine import ResearchEngine
from ..constant import (
    BacktestStatus, FeatureStatus, ModelStatus,
    StrategyStatus, DatasetStatus,
)
from ..event import (
    EVENT_EXPERIMENT_CREATED, EVENT_EXPERIMENT_UPDATED,
    EVENT_DATASET_CREATED,    EVENT_DATASET_UPDATED,
    EVENT_FEATURE_CREATED,    EVENT_FEATURE_UPDATED,
    EVENT_STRATEGY_CREATED,   EVENT_STRATEGY_UPDATED,
    EVENT_MODEL_CREATED,      EVENT_MODEL_UPDATED,
    EVENT_BACKTEST_CREATED,   EVENT_BACKTEST_UPDATED,
)


def _stat_card(title: str, value: str = "0",
               subtitle: str = "", color: str = "#0d6efd") -> QWidget:
    card = QWidget()
    card.setStyleSheet(
        f"background:#fff; border:1px solid #dee2e6; border-radius:8px;"
        f"border-left:4px solid {color};")
    lyt = QVBoxLayout(card)
    lyt.setContentsMargins(12, 10, 12, 10)
    title_lbl = QLabel(title)
    title_lbl.setStyleSheet("color:#6c757d; font-size:12px;")
    lyt.addWidget(title_lbl)
    val_lbl = QLabel(value)
    val_lbl.setObjectName("val")
    val_lbl.setStyleSheet(f"color:{color}; font-size:28px; font-weight:bold;")
    lyt.addWidget(val_lbl)
    if subtitle:
        sub_lbl = QLabel(subtitle)
        sub_lbl.setObjectName("sub")
        sub_lbl.setStyleSheet("color:#adb5bd; font-size:11px;")
        lyt.addWidget(sub_lbl)
    return card


def _set_stat_card(card: QWidget, value: str, subtitle: str = ""):
    val = card.findChild(QLabel, "val")
    sub = card.findChild(QLabel, "sub")
    if val:
        val.setText(value)
    if sub and subtitle:
        sub.setText(subtitle)


def _make_top_table(headers: list) -> QTableWidget:
    tbl = QTableWidget(0, len(headers))
    tbl.setHorizontalHeaderLabels(headers)
    tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
    tbl.setAlternatingRowColors(True)
    tbl.verticalHeader().setVisible(False)
    tbl.setMaximumHeight(130)
    return tbl


class DashboardTab(QWidget):
    """量化研究平台 Dashboard — 全局汇总统计面板。"""

    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # 顶部标题 + 刷新按钮
        header = QHBoxLayout()
        title = QLabel("量化研究平台  Dashboard")
        title.setStyleSheet("font-size:20px; font-weight:bold; color:#212529;")
        header.addWidget(title)
        header.addStretch()
        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.setFixedWidth(60)
        self._refresh_btn.clicked.connect(self._refresh)
        header.addWidget(self._refresh_btn)
        root.addLayout(header)

        # 第一行：6 个统计卡片
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self._c_exp      = _stat_card("实验总数",   "0", "", "#0d6efd")
        self._c_dataset  = _stat_card("数据集",     "0", "", "#198754")
        self._c_feature  = _stat_card("因子",       "0", "", "#6f42c1")
        self._c_strategy = _stat_card("策略",       "0", "", "#fd7e14")
        self._c_model    = _stat_card("模型",       "0", "", "#20c997")
        self._c_backtest = _stat_card("回测",       "0", "", "#dc3545")
        for c in (self._c_exp, self._c_dataset, self._c_feature,
                  self._c_strategy, self._c_model, self._c_backtest):
            row1.addWidget(c)
        root.addLayout(row1)

        # 第二行：最新动态 + Top 排行
        splitter = QSplitter(Qt.Horizontal)

        recent_grp = QGroupBox("最新动态（最近 10 条）")
        recent_lyt = QVBoxLayout(recent_grp)
        self._recent_table = QTableWidget(0, 4)
        self._recent_table.setHorizontalHeaderLabels(["类型", "ID", "名称", "时间"])
        self._recent_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._recent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._recent_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._recent_table.setAlternatingRowColors(True)
        self._recent_table.verticalHeader().setVisible(False)
        recent_lyt.addWidget(self._recent_table)
        splitter.addWidget(recent_grp)

        top_grp = QGroupBox("绩效排行榜")
        top_lyt = QVBoxLayout(top_grp)
        top_lyt.addWidget(QLabel("Top 回测（Sharpe）："))
        self._top_bt_table = _make_top_table(["回测 ID", "名称", "Sharpe", "年化%"])
        top_lyt.addWidget(self._top_bt_table)
        top_lyt.addWidget(QLabel("Top 策略（Sharpe）："))
        self._top_st_table = _make_top_table(["策略 ID", "名称", "Sharpe", "年化%"])
        top_lyt.addWidget(self._top_st_table)
        top_lyt.addWidget(QLabel("Top 因子（|IC|）："))
        self._top_ft_table = _make_top_table(["因子 ID", "名称", "|IC|", "RankIC"])
        top_lyt.addWidget(self._top_ft_table)
        splitter.addWidget(top_grp)
        splitter.setSizes([500, 400])
        root.addWidget(splitter, 1)

        # 底部状态分布
        dist_grp = QGroupBox("状态分布")
        dist_lyt = QHBoxLayout(dist_grp)
        self._dist_tables: dict = {}
        for title_str, statuses in [
            ("策略", StrategyStatus), ("模型", ModelStatus),
            ("回测", BacktestStatus), ("因子", FeatureStatus),
        ]:
            tbl = QTableWidget(len(list(statuses)), 2)
            tbl.setHorizontalHeaderLabels(["状态", "数量"])
            tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
            tbl.verticalHeader().setVisible(False)
            tbl.setMaximumHeight(160)
            for i, s in enumerate(statuses):
                tbl.setItem(i, 0, QTableWidgetItem(s.value))
                tbl.setItem(i, 1, QTableWidgetItem("0"))
            w = QGroupBox(title_str)
            wl = QVBoxLayout(w)
            wl.addWidget(tbl)
            dist_lyt.addWidget(w)
            self._dist_tables[title_str] = (tbl, statuses)
        root.addWidget(dist_grp)

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in (EVENT_EXPERIMENT_CREATED, EVENT_EXPERIMENT_UPDATED,
                   EVENT_DATASET_CREATED,    EVENT_DATASET_UPDATED,
                   EVENT_FEATURE_CREATED,    EVENT_FEATURE_UPDATED,
                   EVENT_STRATEGY_CREATED,   EVENT_STRATEGY_UPDATED,
                   EVENT_MODEL_CREATED,      EVENT_MODEL_UPDATED,
                   EVENT_BACKTEST_CREATED,   EVENT_BACKTEST_UPDATED):
            ee.register(ev, self._on_event)

    def _on_event(self, event: Event):
        self._refresh()

    def _refresh(self):
        self._update_stat_cards()
        self._update_recent()
        self._update_top_tables()
        self._update_dist_tables()

    def _update_stat_cards(self):
        exps       = self._engine.list_experiments()
        datasets   = self._engine.list_datasets()
        features   = self._engine.list_features()
        strategies = self._engine.list_strategies()
        models     = self._engine.list_models()
        backtests  = self._engine.list_backtests()

        ready_ds    = sum(1 for d in datasets   if d.status == DatasetStatus.READY)
        stable_ft   = sum(1 for f in features   if f.status == FeatureStatus.STABLE)
        live_st     = sum(1 for s in strategies if s.status == StrategyStatus.LIVE)
        deployed_ml = sum(1 for m in models     if m.status == ModelStatus.DEPLOYED)
        done_bt     = sum(1 for b in backtests  if b.status == BacktestStatus.COMPLETED)

        _set_stat_card(self._c_exp,      str(len(exps)),       f"共 {len(exps)} 个实验")
        _set_stat_card(self._c_dataset,  str(len(datasets)),   f"{ready_ds} 个已就绪")
        _set_stat_card(self._c_feature,  str(len(features)),   f"{stable_ft} 个稳定")
        _set_stat_card(self._c_strategy, str(len(strategies)), f"{live_st} 个线上")
        _set_stat_card(self._c_model,    str(len(models)),     f"{deployed_ml} 个已部署")
        _set_stat_card(self._c_backtest, str(len(backtests)),  f"{done_bt} 个已完成")

    def _update_recent(self):
        TYPE_COLORS = {
            "实验": "#0d6efd", "数据集": "#198754",
            "因子": "#6f42c1", "策略":   "#fd7e14",
            "模型": "#20c997", "回测":   "#dc3545",
        }
        items = []
        for rec in self._engine.list_experiments()[-5:]:
            items.append(("实验",   rec.experiment_id, rec.name, rec.updated_at))
        for rec in self._engine.list_datasets()[-3:]:
            items.append(("数据集", rec.dataset_id,    rec.name, rec.updated_at))
        for rec in self._engine.list_features()[-3:]:
            items.append(("因子",   rec.feature_id,    rec.name, rec.updated_at))
        for rec in self._engine.list_strategies()[-3:]:
            items.append(("策略",   rec.strategy_id,   rec.name, rec.updated_at))
        for rec in self._engine.list_models()[-3:]:
            items.append(("模型",   rec.model_id,      rec.name, rec.updated_at))
        for rec in self._engine.list_backtests()[-3:]:
            items.append(("回测",   rec.backtest_id,   rec.name, rec.updated_at))

        items.sort(key=lambda x: x[3], reverse=True)
        items = items[:10]

        self._recent_table.setRowCount(0)
        for type_name, rid, name, dt in items:
            row = self._recent_table.rowCount()
            self._recent_table.insertRow(row)
            t_item = QTableWidgetItem(type_name)
            t_item.setForeground(QColor(TYPE_COLORS.get(type_name, "#333")))
            f = QFont(); f.setBold(True); t_item.setFont(f)
            self._recent_table.setItem(row, 0, t_item)
            self._recent_table.setItem(row, 1, QTableWidgetItem(rid))
            self._recent_table.setItem(row, 2, QTableWidgetItem(name))
            self._recent_table.setItem(row, 3,
                QTableWidgetItem(dt.strftime("%m-%d %H:%M")))

    def _update_top_tables(self):
        self._top_bt_table.setRowCount(0)
        for rec in self._engine.top_backtests_by_sharpe(5):
            r = self._top_bt_table.rowCount()
            self._top_bt_table.insertRow(r)
            for col, v in enumerate([rec.backtest_id, rec.name,
                    f"{rec.sharpe:.4f}", f"{rec.annual_return:.2%}"]):
                self._top_bt_table.setItem(r, col, QTableWidgetItem(v))

        self._top_st_table.setRowCount(0)
        for rec in self._engine.top_strategies_by_sharpe(5):
            r = self._top_st_table.rowCount()
            self._top_st_table.insertRow(r)
            for col, v in enumerate([rec.strategy_id, rec.name,
                    f"{rec.sharpe:.4f}", f"{rec.annual_return:.2%}"]):
                self._top_st_table.setItem(r, col, QTableWidgetItem(v))

        self._top_ft_table.setRowCount(0)
        for rec in self._engine.top_features_by_ic(5):
            r = self._top_ft_table.rowCount()
            self._top_ft_table.insertRow(r)
            for col, v in enumerate([rec.feature_id, rec.name,
                    f"{abs(rec.ic):.4f}", f"{rec.rank_ic:.4f}"]):
                self._top_ft_table.setItem(r, col, QTableWidgetItem(v))

    def _update_dist_tables(self):
        counts = {
            "策略": {s: 0 for s in StrategyStatus},
            "模型": {s: 0 for s in ModelStatus},
            "回测": {s: 0 for s in BacktestStatus},
            "因子": {s: 0 for s in FeatureStatus},
        }
        for r in self._engine.list_strategies():
            counts["策略"][r.status] = counts["策略"].get(r.status, 0) + 1
        for r in self._engine.list_models():
            counts["模型"][r.status] = counts["模型"].get(r.status, 0) + 1
        for r in self._engine.list_backtests():
            counts["回测"][r.status] = counts["回测"].get(r.status, 0) + 1
        for r in self._engine.list_features():
            counts["因子"][r.status] = counts["因子"].get(r.status, 0) + 1

        for title_str, (tbl, statuses) in self._dist_tables.items():
            for i, s in enumerate(statuses):
                cnt = counts[title_str].get(s, 0)
                item = QTableWidgetItem(str(cnt))
                item.setTextAlignment(Qt.AlignCenter)
                if cnt > 0:
                    item.setForeground(QColor("#198754"))
                    ff = QFont(); ff.setBold(True); item.setFont(ff)
                tbl.setItem(i, 1, item)

