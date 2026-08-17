#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 7: ScanEngine 多周期优化
将 ScanEngine 的多周期实现优化为与 Monitor Engine 一致的模式
"""


def optimize_scan_engine():
    """
    优化 scan() 方法，使用标准的 eval_condition_mtf() 调用
    """
    path = 'vnpy/strategy_condition/engine/scan_engine.py'
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换 _evaluate_multi_timeframe 方法为更优化的版本
    old_method = '''    def _evaluate_multi_timeframe(self, symbol: str, buy_tree: ConditionNode,
                                   req, eval_fn, n_bars: int,
                                   _bars_dict: Optional[Dict[str, list]] = None) -> Tuple[bool, float]:
        """
        Phase 4: 多周期评估辅助方法。

        Args:
            symbol: 股票代码
            buy_tree: 买入条件树
            req: DataRequirement 对象
            eval_fn: 评估函数
            n_bars: K线数量
            _bars_dict: 预加载的K线数据（可选）
        
        Returns:
            (passed, score)
        """
        # 构造 MultiTimeframeContext
        ctx = MultiTimeframeContext(symbol=symbol, evaluation_time=datetime.now())

        # 加载所有需要的周期数据
        for interval in req.intervals:
            if _bars_dict and interval in _bars_dict:
                bars = _bars_dict[interval]
            else:
                bars = self._get_bars(symbol, n_bars, interval)
            
            if bars:
                ctx.set_bars(interval, bars)

        # 检查是否所有周期的数据都加载成功
        if not all(ctx.has_interval(i) for i in req.intervals):
            # 数据不足，不通过
            return False, 0.0

        # 使用多周期上下文评估
        # 创建包装的评估函数，传递 MTF 上下文
        def mtf_eval_fn(cond, sym, bars):
            return self._ce.eval_condition(cond, sym, bars, _mtf_context=ctx)

        # 注意：这里传递的 bars 参数在多周期模式下会被 mtf_eval_fn 中的 _mtf_context 覆盖
        # 我们传递执行周期的数据作为默认值
        default_bars = ctx.get_bars(req.strategy_execution_interval)
        return buy_tree.evaluate(symbol, default_bars, mtf_eval_fn)'''
    
    new_method = '''    def _evaluate_multi_timeframe(self, symbol: str, buy_tree: ConditionNode,
                                   req, eval_fn, n_bars: int,
                                   _bars_dict: Optional[Dict[str, list]] = None) -> Tuple[bool, float]:
        """
        Phase 7: 多周期评估辅助方法（优化版）。
        
        与 Phase 6 Monitor Engine 保持一致的模式：
        - 构造 MultiTimeframeContext
        - 使用条件级路由（检查 data_interval 属性）
        - 调用 eval_condition_mtf() 或 eval_condition()

        Args:
            symbol: 股票代码
            buy_tree: 买入条件树
            req: DataRequirement 对象
            eval_fn: 评估函数（保留用于兼容性）
            n_bars: K线数量
            _bars_dict: 预加载的K线数据（可选）
        
        Returns:
            (passed, score)
        """
        # 构造 MultiTimeframeContext
        eval_time = datetime.now()
        ctx = MultiTimeframeContext(symbol=symbol, evaluation_time=eval_time)

        # 加载所有需要的周期数据
        for interval in req.intervals:
            if _bars_dict and interval in _bars_dict:
                bars = _bars_dict[interval]
            else:
                bars = self._get_bars(symbol, n_bars, interval)
            
            if bars:
                ctx.set_bars(interval, bars)

        # 检查是否所有周期的数据都加载成功
        if not all(ctx.has_interval(i) for i in req.intervals):
            # 数据不足，不通过
            return False, 0.0

        # Phase 7: 使用条件级路由的评估函数
        def mtf_eval_fn(cond, sym, bars):
            """条件级路由：根据 data_interval 决定使用哪个评估路径"""
            if hasattr(cond, 'data_interval') and cond.data_interval is not None:
                # 多周期条件：使用 eval_condition_mtf
                return self._ce.eval_condition_mtf(cond, sym, bars, ctx)
            else:
                # 单周期条件：使用普通 eval_condition
                return self._ce.eval_condition(cond, sym, bars)

        # 传递执行周期的数据作为默认值
        default_bars = ctx.get_bars(req.strategy_execution_interval)
        return buy_tree.evaluate(symbol, default_bars, mtf_eval_fn)'''
    
    if old_method in content:
        content = content.replace(old_method, new_method)
        print("✓ 优化 _evaluate_multi_timeframe() 方法")
    else:
        print("⚠ 未找到 _evaluate_multi_timeframe() 方法（可能已被修改）")
    
    # 优化 _backtest_symbol 中的多周期评估部分
    old_backtest_mtf = '''            # Phase 4: 多周期评估
            if is_multi_timeframe and req:
                # 构造当前时间点的 MTFContext
                eval_time = getattr(bars_so_far[-1], 'dt', None)
                ctx = MultiTimeframeContext(symbol=symbol, evaluation_time=eval_time)
                for interval in req.intervals:
                    # Phase 5: 使用 As-of Time 对齐，防止未来函数
                    interval_bars = self._get_bars_as_of(
                        symbol, len(bars_so_far), interval, eval_time
                    )
                    if interval_bars:
                        ctx.set_bars(interval, interval_bars)
                    else:
                        # 回退：无独立数据源时使用执行周期数据
                        ctx.set_bars(interval, bars_so_far)

                def mtf_eval_fn(cond, sym, bars):
                    return self._ce.eval_condition(cond, sym, bars, _mtf_context=ctx)

                passed, score = strategy.buy_tree.evaluate(symbol, bars_so_far, mtf_eval_fn)'''
    
    new_backtest_mtf = '''            # Phase 7: 多周期评估（优化版）
            if is_multi_timeframe and req:
                # 构造当前时间点的 MTFContext
                eval_time = getattr(bars_so_far[-1], 'dt', None)
                ctx = MultiTimeframeContext(symbol=symbol, evaluation_time=eval_time)
                for interval in req.intervals:
                    # Phase 5: 使用 As-of Time 对齐，防止未来函数
                    interval_bars = self._get_bars_as_of(
                        symbol, len(bars_so_far), interval, eval_time
                    )
                    if interval_bars:
                        ctx.set_bars(interval, interval_bars)
                    else:
                        # 回退：无独立数据源时使用执行周期数据
                        ctx.set_bars(interval, bars_so_far)

                # Phase 7: 使用条件级路由
                def mtf_eval_fn(cond, sym, bars):
                    """条件级路由：根据 data_interval 决定使用哪个评估路径"""
                    if hasattr(cond, 'data_interval') and cond.data_interval is not None:
                        # 多周期条件：使用 eval_condition_mtf
                        return self._ce.eval_condition_mtf(cond, sym, bars, ctx)
                    else:
                        # 单周期条件：使用普通 eval_condition
                        return self._ce.eval_condition(cond, sym, bars)

                passed, score = strategy.buy_tree.evaluate(symbol, bars_so_far, mtf_eval_fn)'''
    
    if old_backtest_mtf in content:
        content = content.replace(old_backtest_mtf, new_backtest_mtf)
        print("✓ 优化 _backtest_symbol() 中的多周期评估")
    else:
        print("⚠ 未找到 _backtest_symbol 多周期评估代码块")
    
    # 更新文件头部注释
    old_header = '''Phase 4 多周期改造：
- 使用 analyze_data_requirements 分析策略的数据需求
- 根据需求加载多个周期的数据
- 构造 MultiTimeframeContext 传递给评估引擎
- 保持向后兼容：单周期策略继续正常工作'''
    
    new_header = '''Phase 4-7 多周期改造：
- 使用 analyze_data_requirements 分析策略的数据需求
- 根据需求加载多个周期的数据
- 构造 MultiTimeframeContext 传递给评估引擎
- Phase 7: 使用条件级路由（与 Monitor Engine 一致）
- 保持向后兼容：单周期策略继续正常工作'''
    
    content = content.replace(old_header, new_header)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ 已更新 {path}")


if __name__ == '__main__':
    print("=== Phase 7: ScanEngine 多周期优化 ===\n")
    optimize_scan_engine()
    print("\n=== 优化完成 ===")