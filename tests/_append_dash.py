"""Append DashboardTab methods"""
import pathlib

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\ui\dashboard_tab.py"
)

METHODS = """
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
"""

txt = P.read_text(encoding="utf-8")
txt = txt.replace("# PLACEHOLDER_DASH_METHODS", METHODS)
P.write_text(txt, encoding="utf-8")
print("DashboardTab methods appended OK, size:", P.stat().st_size)
