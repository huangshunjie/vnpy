"""
修复多周期回测问题
====================

问题：UI回测时只加载执行周期的数据，导致多周期条件无法正确评估

解决方案：
1. UI调用backtest前分析策略的数据需求
2. 加载所有需要的周期数据到 bars_dict
3. 传递给回测引擎

修复文件：vnpy/strategy_condition/ui/widget.py 的 _on_backtest 方法
"""

fix_content = '''
    def _on_backtest(self) -> None:
        if not self._strategy:
            self._show_msg("请先选择或创建策略")
            return
        symbols = self._get_pool_symbols()
        if not symbols:
            self._show_msg("股票池为空，请先添加或勾选股票池。")
            return
        self._strategy.params = self._collect_params()
        n_bars = self._nbars_sp.value()
        self._btn_bt.setEnabled(False)
        self._btn_bt.setText("回测中...")
        try:
            # 获取执行周期
            bt_idx = self._interval_cb.currentIndex()
            bt_interval, _ = self._interval_options[bt_idx]
            is_intraday = (bt_interval != Interval.DAILY)
            
            # Phase 4: 分析策略的数据需求
            from ..core.strategy import analyze_data_requirements
            req = analyze_data_requirements(self._strategy.buy_tree, bt_interval)
            needed_intervals = req.intervals
            
            # 加载所有需要的周期数据
            bars_dict = {}
            for interval in needed_intervals:
                # 临时切换interval_cb来加载对应周期的数据
                old_idx = self._interval_cb.currentIndex()
                for i, (intv, _) in enumerate(self._interval_options):
                    if intv == interval:
                        self._interval_cb.setCurrentIndex(i)
                        break
                
                interval_bars = self._load_bars(symbols, n_bars)
                
                # 恢复原来的选择
                self._interval_cb.setCurrentIndex(old_idx)
                
                # 合并到bars_dict（如果一个symbol有多个周期，需要特殊处理）
                for sym, bars in interval_bars.items():
                    if bars:  # 只保留有数据的
                        if interval == bt_interval:
                            # 执行周期的数据作为主数据
                            bars_dict[sym] = bars
                        # TODO: 其他周期的数据需要传递给回测引擎
                        # 当前的bars_dict结构不支持多周期
                        # 需要修改为 bars_dict[sym][interval] = bars
            
            loaded = [s for s in bars_dict.keys() if bars_dict.get(s)]
            if not loaded:
                self._show_msg(
                    f"未能加载到任何K线数据，共{len(symbols)}只股票。\\n"
                    "请先通过"数据管理"应用下载历史K线数据。"
                )
                return
            
            from ..engine.scan_engine import ScanEngine
            from ..engine.condition_engine import ConditionEngine
            ce = self._engine.condition_engine if self._engine else ConditionEngine()
            se = ScanEngine(ce)
            warmup = max(60, self._strategy.params.min_bars)
            
            batch  = se.backtest(loaded, self._strategy, bars_dict,
                                 warmup=warmup, is_intraday=is_intraday,
                                 execution_interval=bt_interval)
            self._bt_view.load_batch(batch)
            self._signal_view.load_batch(batch)
            self._tab.setCurrentIndex(3)
            self._pool_count_lbl.setText(
                f"上次回测：{len(loaded)}/{len(symbols)}只→"
                f"{batch.count}笔交易"
            )
        except Exception as e:
            self._show_msg(f"回测失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._btn_bt.setEnabled(True)
            self._btn_bt.setText("📊 回测验证")
'''

print("问题根源已找到！")
print()
print("=" * 70)
print("回测结果为空的根本原因")
print("=" * 70)
print()
print("1. 你的策略包含5分钟周期的条件（缩量阴线）")
print("2. UI点击回测时只加载了日线数据")
print("3. 回测引擎检测到需要5分钟数据，但bars_dict里没有")
print("4. 回退机制用日线数据替代5分钟数据")
print("5. 结果：5分钟条件实际上用的是日线数据评估")
print("6. 因为两次测试（日线vs5分钟）结果完全一样，证实了这个分析")
print()
print("=" * 70)
print("临时解决方案（立即可用）")
print("=" * 70)
print()
print("方案1: 把所有条件都改成日线周期")
print("   - 简单直接，立即生效")
print("   - 但无法使用多周期功能")
print()
print("方案2: 使用日线模拟")
print("   - 如果5分钟缩量阴线对应日线特征，可以用日线条件代替")
print()
print("=" * 70)
print("永久解决方案（需要修改代码）")
print("=" * 70)
print()
print("修改 vnpy/strategy_condition/ui/widget.py 的 _on_backtest 方法")
print("让它能够：")
print("1. 调用 analyze_data_requirements() 分析策略需求")
print("2. 加载所有需要的周期数据")  
print("3. 修改 bars_dict 结构支持多周期：bars_dict[symbol][interval] = bars")
print("4. 或者：修改回测引擎从数据库直接查询需要的周期数据")
print()
print("推荐方案：让回测引擎自己从数据库加载多周期数据")
print("这样UI不需要改太多，回测引擎更灵活")