"""
strategy_condition/engine/scan_engine.py

选股引擎 + 逐日持仓模拟（止盈止损）。
复用 market_behavior 的 CandleBuffer / DatabaseLoader，不重复拉取数据。

Phase 4-7 多周期改造：
- 使用 analyze_data_requirements 分析策略的数据需求
- 根据需求加载多个周期的数据
- 构造 MultiTimeframeContext 传递给评估引擎
- Phase 7: 使用条件级路由（与 Monitor Engine 一致）
- 保持向后兼容：单周期策略继续正常工作

参数统一原则：
  卖出阈值（止损 / 止盈 / 追踪 / 最大持仓）统一使用 strategy.params，
  条件树节点自身的 params 仅作备用（当 strategy_params=None 时）。

多进程并行：
  backtest() 使用 multiprocessing.Pool 将股票列表分配给多个进程并行回测，
  显著提升大批量回测性能（38 股× 10000 根 K 线从串行变并行）。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from vnpy.trader.constant import Interval

from ..constant import SignalType, SignalSource
from ..core.condition_tree import ConditionNode
from ..core.signal import SignalRecord, SignalBatch
from ..core.strategy import Strategy, StrategyParams
from ..core.mtf_context import MultiTimeframeContext, analyze_data_requirements
from ..data.mtf_candle_buffer import MultiTimeframeCandleBuffer
from .condition_engine import ConditionEngine

# 并行回测的最小股票数阈值：低于此值不值得开线程池
_PARALLEL_THRESHOLD = 4


class ScanEngine:

    def __init__(self, condition_engine: ConditionEngine,
                 candle_buffer=None, log_fn=None):
        self._ce  = condition_engine
        self._buf = candle_buffer
        self._log = log_fn or print
        # Phase 5: 多周期数据缓存（MTFCandleBuffer）
        self._mtf_buffer: Optional[MultiTimeframeCandleBuffer] = None

    def set_candle_buffer(self, buf) -> None:
        self._buf = buf
        self._ce.set_candle_buffer(buf)

    def set_mtf_buffer(self, mtf_buffer: MultiTimeframeCandleBuffer) -> None:
        """Phase 5: 设置多周期数据缓存"""
        self._mtf_buffer = mtf_buffer

    def get_mtf_buffer(self) -> Optional[MultiTimeframeCandleBuffer]:
        """Phase 5: 获取多周期数据缓存"""
        return self._mtf_buffer

    # ── 截面扫描（实时选股） ──────────────────────────────────────────

    def _group_conditions_by_scope(self, node: ConditionNode) -> Dict[str, list]:
        groups = {"all": [], "daily": [], "minute": []}
        for cond in node.all_conditions():
            scope = getattr(cond, "interval_scope", "all") or "all"
            if scope not in groups:
                scope = "all"
            groups[scope].append(cond)
        return groups

    def _is_layered_strategy(self, strategy: Strategy) -> bool:
        buy_groups = self._group_conditions_by_scope(strategy.buy_tree)
        sell_groups = self._group_conditions_by_scope(strategy.sell_tree)
        return bool(buy_groups["daily"] or buy_groups["minute"] or sell_groups["daily"] or sell_groups["minute"])

    def scan(self, symbols: List[str], strategy: Strategy,
             n_bars: int = 300,
             execution_interval: Interval = Interval.DAILY,
             _bars_dict: Optional[Dict[str, list]] = None) -> SignalBatch:
        """
        实时截面选股。

        Phase 4 多周期改造：
        - 分析策略的数据需求
        - 如果是多周期策略，构造 MultiTimeframeContext
        - 否则使用传统单周期评估（向后兼容）

        Args:
            symbols: 股票列表
            strategy: 策略定义
            n_bars: 每个股票加载的K线数量
            execution_interval: 策略执行周期（默认日线）
            _bars_dict: 预加载的K线数据字典（可选）
        """
        batch = SignalBatch(
            batch_id=uuid.uuid4().hex[:10],
            strategy_name=strategy.name,
            source=SignalSource.SCAN,
            run_dt=datetime.now(),
            params={"n_bars": n_bars, "symbols": len(symbols)},
        )

        # Phase 4: 分析数据需求
        req = analyze_data_requirements(strategy.buy_tree, execution_interval)
        is_multi_timeframe = len(req.intervals) > 1

        if is_multi_timeframe:
            self._log(f"[ScanEngine] 多周期策略检测到，需要周期: {[i.value for i in req.intervals]}")

        eval_fn = self._ce.eval_condition
        for sym in symbols:
            if is_multi_timeframe:
                # 多周期评估
                passed, score = self._evaluate_multi_timeframe(
                    sym, strategy.buy_tree, req, eval_fn, n_bars, _bars_dict
                )
            else:
                # 单周期评估（向后兼容）
                bars = _bars_dict.get(sym, []) if _bars_dict is not None \
                       else self._get_bars(sym, n_bars, execution_interval)
                if len(bars) < strategy.params.min_bars:
                    continue
                passed, score = strategy.buy_tree.evaluate(sym, bars, eval_fn)

            if not passed:
                continue

            # 获取最后一根K线用于记录信号
            bars = _bars_dict.get(sym, []) if _bars_dict is not None \
                   else self._get_bars(sym, n_bars, execution_interval)
            if not bars:
                continue

            batch.signals.append(SignalRecord(
                signal_id=uuid.uuid4().hex[:10],
                signal_type=SignalType.BUY,
                source=SignalSource.SCAN,
                symbol=sym,
                dt=getattr(bars[-1], "dt", datetime.now()),
                price=bars[-1].close,
                score=round(score, 4),
                strategy_name=strategy.name,
            ))

        batch.signals.sort(key=lambda s: s.score, reverse=True)
        self._log(f"[ScanEngine] {strategy.name}: {len(symbols)} 股 → {batch.count} 信号")
        return batch

    def _evaluate_multi_timeframe(self, symbol: str, buy_tree: ConditionNode,
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
        return buy_tree.evaluate(symbol, default_bars, mtf_eval_fn)

    # ── 历史回测 ──────────────────────────────────────────────────────

    def backtest(self, symbols: List[str], strategy: Strategy,
                 all_bars_dict: Dict[str, list],
                 warmup: int = 60,
                 is_intraday: bool = False,
                 execution_interval: Interval = Interval.DAILY) -> SignalBatch:
        """
        对每个 symbol 的全量 K 线做逐日滚动回测。
        卖出阈值统一来自 strategy.params。

        Phase 4 多周期改造：
        - 支持多周期策略的回测
        - 在每个时间点构造正确的 MultiTimeframeContext

        性能优化：
          - 当股票数 >= _PARALLEL_THRESHOLD 时，使用 ThreadPoolExecutor 并行
            （释放 GIL 的 numpy 计算 + I/O 可以重叠）
          - 每只股票独立回测，互不依赖

        Args:
            symbols: 股票列表
            strategy: 策略定义
            all_bars_dict: 股票代码 -> K线列表的字典
            warmup: 预热期K线数量
            is_intraday: 是否为分钟线回测（True时启用T+1规则）
            execution_interval: 策略执行周期（Phase 4新增）
        """
        import time
        t0 = time.perf_counter()

        batch = SignalBatch(
            batch_id=uuid.uuid4().hex[:10],
            strategy_name=strategy.name,
            source=SignalSource.BACKTEST,
            run_dt=datetime.now(),
            params={"warmup": warmup, "symbols": len(symbols)},
        )

        # Phase 4: 分析数据需求
        req = analyze_data_requirements(strategy.buy_tree, execution_interval)
        is_multi_timeframe = len(req.intervals) > 1

        if is_multi_timeframe:
            self._log(f"[ScanEngine] 多周期回测，需要周期: {[i.value for i in req.intervals]}")

        # 筛选有效股票
        valid_items = []
        for sym in symbols:
            bars = all_bars_dict.get(sym, [])
            if len(bars) >= warmup + 2:
                valid_items.append((sym, bars))

        if not valid_items:
            return batch

        # 并行回测
        if len(valid_items) >= _PARALLEL_THRESHOLD:
            import os
            # 线程数 = min(股票数, CPU核心数, 16)
            max_workers = min(len(valid_items), os.cpu_count() or 4, 16)

            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(
                        self._backtest_symbol, sym, bars, strategy,
                        warmup, is_intraday, is_multi_timeframe, req
                    ): sym
                    for sym, bars in valid_items
                }
                for fut in as_completed(futures):
                    try:
                        signals = fut.result()
                        batch.signals.extend(signals)
                    except Exception as e:
                        sym = futures[fut]
                        self._log(f"[ScanEngine] {sym} backtest error: {e}")
        else:
            # 少量股票直接串行
            for sym, bars in valid_items:
                signals = self._backtest_symbol(sym, bars, strategy, warmup,
                                                is_intraday, is_multi_timeframe, req)
                batch.signals.extend(signals)

        elapsed = time.perf_counter() - t0
        self._log(f"[ScanEngine] backtest {strategy.name}: "
                  f"{len(valid_items)} 股 → {batch.count} 信号 "
                  f"({elapsed:.2f}s)")
        return batch

    def _backtest_symbol(self, symbol: str, all_bars: list,
                         strategy: Strategy, warmup: int,
                         is_intraday: bool = False,
                         is_multi_timeframe: bool = False,
                         req = None) -> List[SignalRecord]:
        """
        逐日滚动回测单只股票。
        
        Phase 4 多周期改造：
        - 如果是多周期策略，在每个时间点构造 MTFContext
        - 否则使用传统单周期评估

        所有止损/止盈/追踪/持仓上限阈值统一从 strategy.params 读取，
        并透传给 eval_exit，彻底消除双参数体系的不一致。
        冷却期机制：卖出后 cooldown_days 交易日内禁止重新买入同一股票。
        同日冲突规则：买入条件和卖出条件同时满足时，不执行任何操作（空仓）或只卖不买（持仓）。
        A股T+1：分钟线模式下，买入当天不可卖出，需等到下一个交易日。

        性能优化：
          - 预计算全量 numpy 数组（closes/highs/lows/volumes），
            使用 numpy 切片（O(1) view）替代 list comprehension（O(n)）
          - 买入条件评估使用 _precomputed 参数跳过重复数组提取
        """
        import numpy as np

        signals: List[SignalRecord] = []
        eval_fn = self._ce.eval_condition
        sp      = strategy.params          # 唯一参数源
        cost    = sp.commission_rate + sp.stamp_duty_rate + sp.slippage_rate
        n_bars  = len(all_bars)

        # ── 预计算全量 numpy 数组（一次性 O(n)，后续切片 O(1)） ──
        _all_closes  = np.array([b.close for b in all_bars], dtype=np.float64)
        _all_highs   = np.array([b.high for b in all_bars], dtype=np.float64)
        _all_lows    = np.array([b.low for b in all_bars], dtype=np.float64)
        _all_volumes = np.array([float(b.volume) for b in all_bars], dtype=np.float64)

        _all_opens   = np.array([b.open for b in all_bars], dtype=np.float64)

        def _make_precomputed(end: int) -> dict:
            """构造截至 end（不含）的预计算数组字典，numpy 切片 = O(1) view"""
            return {
                "closes": _all_closes[:end],
                "opens": _all_opens[:end],
                "highs": _all_highs[:end],
                "lows": _all_lows[:end],
                "volumes": _all_volumes[:end],
            }

        def _eval_fn_fast(cond, sym, bars):
            """带预计算的 eval_condition 闭包"""
            if is_multi_timeframe:
                # 多周期模式：需要构造 MTFContext（在外层已构造）
                return eval_fn(cond, sym, bars)
            else:
                # 单周期模式：使用预计算
                return eval_fn(cond, sym, bars, _precomputed=_make_precomputed(len(bars)))

        # 冷却期追踪：记录最近一次卖出的日期（按交易日计算冷却期）
        last_exit_date = None  # 分钟线模式下记录卖出日期
        last_exit_idx: int = -9999  # 日线模式下记录卖出索引

        # ── 实时日线合成（多周期优化）──────────────────────────────────
        # 当执行周期是分钟线且存在日线条件时，使用分钟close实时合成虚拟日线
        # 逻辑：遍历分钟线时维护"虚拟当天日线"，用当前分钟close作为日线close
        needs_realtime_daily = False
        historical_daily_bars: list = []

        if is_multi_timeframe and req:
            exec_interval = req.strategy_execution_interval
            _minute_intervals = {
                Interval.MINUTE, Interval.MINUTE_5, Interval.MINUTE_15,
                Interval.MINUTE_30, Interval.HOUR
            }
            is_minute_exec = exec_interval in _minute_intervals
            has_daily_condition = Interval.DAILY in req.intervals

            if is_minute_exec and has_daily_condition:
                needs_realtime_daily = True
                if self._mtf_buffer is not None:
                    historical_daily_bars = self._mtf_buffer.get(symbol, 0, Interval.DAILY) or []

        # ── 实时日线合成（优化版：缓存 cutoff_idx，避免每次线性扫描）──
        # 虚拟当天日线追踪变量
        _rt_today_open = 0.0
        _rt_today_high = float('-inf')
        _rt_today_low = float('inf')
        _rt_today_volume = 0.0
        _rt_today_date = None
        _rt_prev_date = None
        _rt_cutoff_idx = 0  # 缓存：历史日线的截断位置（只增不减）

        # 预解析 Exchange（只做一次）
        from vnpy.trader.object import BarData as _BarData
        from vnpy.trader.constant import Exchange as _Exchange
        _exchange = _Exchange.SSE
        if '.' in symbol:
            _suffix = symbol.split('.')[-1].upper()
            if _suffix in ('SZ', 'SZSE'):
                _exchange = _Exchange.SZSE
        _symbol_code = symbol.split('.')[0] if '.' in symbol else symbol

        def _build_realtime_daily_bars_fast(cur_bar_idx: int) -> list:
            """
            构造实时日线序列 = 历史完整日线（截至昨天） + 虚拟当天日线。
            优化：cutoff_idx 只增不减，避免每次从头扫描。
            """
            nonlocal _rt_today_open, _rt_today_high, _rt_today_low
            nonlocal _rt_today_volume, _rt_today_date, _rt_prev_date
            nonlocal _rt_cutoff_idx

            cur_bar = all_bars[cur_bar_idx]
            cur_date = cur_bar.dt.date() if hasattr(cur_bar, 'dt') and cur_bar.dt else None

            if cur_date is None:
                return historical_daily_bars[:_rt_cutoff_idx] if _rt_cutoff_idx else historical_daily_bars

            # 检测新的一天 → 重置统计 + 更新 cutoff
            if cur_date != _rt_prev_date:
                _rt_today_open = cur_bar.open
                _rt_today_high = cur_bar.high
                _rt_today_low = cur_bar.low
                _rt_today_volume = float(cur_bar.volume)
                _rt_today_date = cur_bar.dt
                _rt_prev_date = cur_date
                # 从上次 cutoff 位置继续扫描（只增不减）
                while _rt_cutoff_idx < len(historical_daily_bars):
                    d_bar = historical_daily_bars[_rt_cutoff_idx]
                    d_date = d_bar.dt.date() if hasattr(d_bar, 'dt') and d_bar.dt else None
                    if d_date and d_date >= cur_date:
                        break
                    _rt_cutoff_idx += 1
            else:
                # 同一天，累积统计
                if cur_bar.high > _rt_today_high:
                    _rt_today_high = cur_bar.high
                if cur_bar.low < _rt_today_low:
                    _rt_today_low = cur_bar.low
                _rt_today_volume += float(cur_bar.volume)

            # 构造虚拟当天日线 BarData
            virtual_bar = _BarData(
                symbol=_symbol_code,
                exchange=_exchange,
                datetime=_rt_today_date,
                interval=Interval.DAILY,
                open_price=_rt_today_open,
                high_price=_rt_today_high,
                low_price=_rt_today_low,
                close_price=cur_bar.close,
                volume=_rt_today_volume,
                gateway_name="backtest_virtual"
            )
            if not hasattr(virtual_bar, 'dt'):
                virtual_bar.dt = _rt_today_date

            # 历史日线[:cutoff] + 虚拟当天（使用缓存的 cutoff，O(1)）
            result = historical_daily_bars[:_rt_cutoff_idx]
            # 注意：这里不用 list() 拷贝，直接 slice + append
            return list(result) + [virtual_bar]

        # 添加进度日志变量
        import time as _time_mod
        _last_log_time = _time_mod.perf_counter()
        _log_interval = 2.0  # 每2秒打印一次进度

        # 确定执行周期（用于判断 bars_so_far 是否就是该周期的数据）
        _exec_interval = req.strategy_execution_interval if (is_multi_timeframe and req) else None

        i = warmup
        while i < n_bars - 1:
            # 定期打印进度（避免看起来卡死）
            _now = _time_mod.perf_counter()
            if _now - _last_log_time >= _log_interval:
                progress = (i - warmup) / max(n_bars - warmup - 1, 1) * 100
                print(f"  [{symbol}] 进度: {progress:.1f}% ({i}/{n_bars})", end='\r')
                _last_log_time = _now

            # 冷却期检查：统一对应交易日天数
            if sp.cooldown_days > 0:
                if is_intraday:
                    # 分钟线：按实际交易日天数判断
                    if last_exit_date is not None:
                        cur_date = all_bars[i].dt.date() if hasattr(all_bars[i], 'dt') else None
                        if cur_date:
                            days_since_exit = (cur_date - last_exit_date).days
                            if days_since_exit <= sp.cooldown_days:
                                i += 1
                                continue
                else:
                    # 日线：按K线根数判断（1根 = 1天）
                    bars_since_exit = i - last_exit_idx
                    if bars_since_exit <= sp.cooldown_days:
                        i += 1
                        continue

            # 使用 slice view 而非拷贝（Python list slice 仍然 O(n)，但不可避免）
            bars_so_far = all_bars[:i + 1]

            # Phase 7: 多周期评估（优化版 + 实时日线合成）
            if is_multi_timeframe and req:
                # 构造当前时间点的 MTFContext
                eval_time = getattr(all_bars[i], 'dt', None)
                ctx = MultiTimeframeContext(symbol=symbol, evaluation_time=eval_time)

                for interval in req.intervals:
                    if needs_realtime_daily and interval == Interval.DAILY:
                        # 日线条件：使用实时合成的日线序列（优化版）
                        realtime_daily = _build_realtime_daily_bars_fast(i)
                        if realtime_daily:
                            ctx.set_bars(interval, realtime_daily)
                        else:
                            ctx.set_bars(interval, bars_so_far)
                    elif interval == _exec_interval:
                        # 执行周期就是主循环的周期，直接用 bars_so_far（O(1)，无需查 buffer）
                        ctx.set_bars(interval, bars_so_far)
                    else:
                        # 其他周期：从 MTF buffer 获取
                        interval_bars = self._get_bars_as_of(
                            symbol, len(bars_so_far), interval, eval_time
                        )
                        if interval_bars:
                            ctx.set_bars(interval, interval_bars)
                        else:
                            ctx.set_bars(interval, bars_so_far)

                # Phase 7: 使用条件级路由
                def mtf_eval_fn(cond, sym, bars):
                    """条件级路由：根据 data_interval 决定使用哪个评估路径"""
                    # 优先从属性读取，否则从 params 读取（兼容UI保存的条件）
                    interval_val = None
                    if hasattr(cond, 'data_interval') and cond.data_interval is not None:
                        interval_val = cond.data_interval
                    elif "_data_interval" in cond.params:
                        interval_val = cond.params["_data_interval"]

                    if interval_val is not None:
                        # 多周期条件：使用 eval_condition_mtf
                        return self._ce.eval_condition_mtf(cond, sym, bars, ctx)
                    else:
                        # 单周期条件：使用普通 eval_condition
                        return self._ce.eval_condition(cond, sym, bars)

                passed, score = strategy.buy_tree.evaluate(symbol, bars_so_far, mtf_eval_fn)
            else:
                # 单周期评估（纯日线策略，不变）
                passed, score = strategy.buy_tree.evaluate(symbol, bars_so_far, _eval_fn_fast)

            if not passed:
                i += 1
                continue

            # 同日冲突检查：买入条件满足时，也检查卖出条件是否同时满足
            # 如果卖出条件也满足（空仓状态下），说明信号矛盾，不买入
            sell_triggered, _ = self._eval_sell_tree(
                strategy.sell_tree, symbol,
                entry_price=all_bars[i].close,
                cur_price=all_bars[i].close,
                peak_price=all_bars[i].close,
                hold_days=0,
                bars=bars_so_far,
                sp=sp,
            )
            if sell_triggered:
                i += 1
                continue

            entry_bar   = all_bars[i]
            entry_price = entry_bar.close
            rec = SignalRecord(
                signal_id=uuid.uuid4().hex[:10],
                signal_type=SignalType.BUY,
                source=SignalSource.BACKTEST,
                symbol=symbol,
                dt=getattr(entry_bar, "dt", datetime.now()),
                price=entry_price,
                score=round(score, 4),
                strategy_name=strategy.name,
            )

            peak_price  = entry_price
            # 持仓上限：统一对应日线周期（交易日天数）
            if is_intraday:
                # 分钟线回测：将 max_hold_days（交易日）转换为实际 bar 索引
                max_j = self._find_nth_trading_day(all_bars, i, sp.max_hold_days)
            else:
                # 日线回测：1根K线 = 1天，直接相加
                max_j = min(i + sp.max_hold_days, n_bars - 1)
            exit_bar    = max_j
            exit_price  = all_bars[max_j].close
            exit_reason = "max_hold"

            # A股T+1规则
            entry_date = entry_bar.dt.date() if hasattr(entry_bar, 'dt') else None
            start_j = i + 1
            if is_intraday and entry_date:
                for j in range(i + 1, max_j + 1):
                    j_bar = all_bars[j]
                    j_date = j_bar.dt.date() if hasattr(j_bar, 'dt') else None
                    if j_date and j_date > entry_date:
                        start_j = j
                        break
                else:
                    start_j = max_j

            # 现在从start_j开始检查卖出条件
            for j in range(start_j, max_j + 1):
                cur_price = _all_closes[j]
                if cur_price > peak_price:
                    peak_price = cur_price

                # 持仓天数：统一对应日线周期（实际自然日天数）
                if is_intraday:
                    # 分钟线：根据日期差计算实际持仓天数
                    j_dt = getattr(all_bars[j], 'dt', None)
                    if j_dt and entry_date:
                        hold_bars_count = (j_dt.date() - entry_date).days
                    else:
                        hold_bars_count = j - i
                else:
                    hold_bars_count = j - i

                triggered, _ = self._eval_sell_tree(
                    strategy.sell_tree, symbol, entry_price,
                    cur_price, peak_price, hold_bars_count,
                    all_bars[:j + 1], sp,
                )
                if triggered:
                    exit_bar    = j
                    exit_price  = cur_price
                    exit_reason = self._exit_reason(
                        strategy.sell_tree, entry_price,
                        cur_price, peak_price, hold_bars_count,
                        all_bars[:j + 1], sp,
                    )
                    break

            hold_bars = exit_bar - i
            raw_ret         = (exit_price - entry_price) / entry_price if entry_price > 0 else 0.0
            
            # 计算真实日历持仓天数
            exit_dt = getattr(all_bars[exit_bar], "dt", None)
            if exit_dt and hasattr(entry_bar, 'dt'):
                entry_date = entry_bar.dt.date()
                exit_date = exit_dt.date()
                hold_days = (exit_date - entry_date).days
            else:
                hold_days = hold_bars  # 无法获取日期的fallback
            
            rec.exit_price  = exit_price
            rec.exit_dt     = exit_dt
            rec.exit_reason = exit_reason
            rec.hold_days   = hold_days
            rec.pnl_pct     = raw_ret - cost

            signals.append(rec)
            
            # 更新冷却期追踪
            last_exit_idx = exit_bar
            if is_intraday:
                # 分钟线：记录卖出日期（用于按交易日计算冷却期）
                exit_bar_dt = getattr(all_bars[exit_bar], 'dt', None)
                if exit_bar_dt:
                    last_exit_date = exit_bar_dt.date()
            i = exit_bar + 1

        return signals

    def _eval_sell_tree(self, sell_tree: ConditionNode, symbol: str,
                        entry_price: float, cur_price: float,
                        peak_price: float, hold_days: int,
                        bars: list,
                        sp: Optional[StrategyParams] = None) -> Tuple[bool, float]:
        """
        评估卖出条件树（OR 语义）。
        sp: strategy.params — 透传给 eval_exit 作为阈值参数源。
        """
        return sell_tree.evaluate(
            symbol, bars,
            lambda cond, sym, b: self._ce.eval_exit(
                cond, entry_price, cur_price, peak_price, hold_days, b, sp),
        )

    def _exit_reason(self, sell_tree: ConditionNode, entry_price: float,
                     cur_price: float, peak_price: float,
                     hold_days: int, bars: list,
                     sp: Optional[StrategyParams] = None) -> str:
        for cond in sell_tree.all_conditions():
            passed, _ = self._ce.eval_exit(
                cond, entry_price, cur_price, peak_price, hold_days, bars, sp)
            if passed:
                return cond.indicator.value.lower()
        return "sell_tree"

    # ── 辅助方法 ──────────────────────────────────────────────────────

    @staticmethod
    def _find_nth_trading_day(all_bars: list, start_idx: int, n_days: int) -> int:
        """
        从 start_idx 开始，找到第 n_days 个交易日结束时的 bar 索引。
        用于分钟线下将 max_hold_days（交易日）转换为实际的 bar 索引上限。

        例：start_idx 在第1天的 10:30，n_days=3
        → 返回第4天（第1天+3天后）的最后一根K线索引
        """
        if n_days <= 0:
            return min(start_idx + 1, len(all_bars) - 1)

        start_date = all_bars[start_idx].dt.date() if hasattr(all_bars[start_idx], 'dt') else None
        if not start_date:
            return min(start_idx + n_days, len(all_bars) - 1)

        days_passed = 0
        last_valid_idx = start_idx

        for j in range(start_idx + 1, len(all_bars)):
            cur_bar = all_bars[j]
            if not hasattr(cur_bar, 'dt'):
                continue
            cur_date = cur_bar.dt.date()
            new_days = (cur_date - start_date).days
            if new_days > days_passed:
                days_passed = new_days
                if days_passed > n_days:
                    # 超过了 n_days 天，返回前一根K线（上一个交易日最后一根）
                    return last_valid_idx
            last_valid_idx = j

        # 没有足够的数据，返回最后一根
        return len(all_bars) - 1

    # ── 数据获取 ──────────────────────────────────────────────────────

    def _get_bars_as_of(self, symbol: str, n: int, interval: Interval,
                        as_of_time) -> list:
        """
        Phase 5: 获取截至指定时间点的K线（防止未来函数）。

        优先级：
        1. MTFCandleBuffer.get_bars_as_of()（支持时间过滤）
        2. 传统 CandleBuffer（向后兼容，无时间过滤）

        Args:
            symbol: 股票代码
            n: K线数量
            interval: 周期
            as_of_time: 评估时间点（datetime）

        Returns:
            符合时间约束的K线列表
        """
        if as_of_time is None:
            return self._get_bars(symbol, n, interval)

        if self._mtf_buffer is not None:
            bars = self._mtf_buffer.get_bars_as_of(symbol, n, interval, as_of_time)
            if bars:
                return bars

        # 回退到传统 buffer（无时间过滤）
        return self._get_bars(symbol, n, interval)

    def _get_bars(self, symbol: str, n: int, interval: Interval = Interval.DAILY) -> list:
        """
        Phase 5: 使用 MTFCandleBuffer 加载多周期数据。

        优先级：
        1. MTFCandleBuffer（多周期缓存，支持自动转换）
        2. 传统 CandleBuffer（向后兼容）

        Args:
            symbol: 股票代码
            n: K线数量
            interval: 周期

        Returns:
            K线列表
        """
        # Phase 5: 优先使用多周期缓存
        if self._mtf_buffer is not None:
            bars = self._mtf_buffer.get(symbol, n, interval)
            if bars:
                return bars

        # 回退到传统 buffer
        if self._buf is None:
            return []
        try:
            return self._buf.get(symbol, n) or []
        except Exception:
            return []
