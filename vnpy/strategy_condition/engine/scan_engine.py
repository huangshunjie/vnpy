"""
strategy_condition/engine/scan_engine.py

选股引擎 + 逐日持仓模拟（止盈止损）。
复用 market_behavior 的 CandleBuffer / DatabaseLoader，不重复拉取数据。

参数统一原则：
  卖出阈值（止损 / 止盈 / 追踪 / 最大持仓）统一使用 strategy.params，
  条件树节点自身的 params 仅作备用（当 strategy_params=None 时）。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ..constant import SignalType, SignalSource
from ..core.condition_tree import ConditionNode
from ..core.signal import SignalRecord, SignalBatch
from ..core.strategy import Strategy, StrategyParams
from .condition_engine import ConditionEngine


class ScanEngine:

    def __init__(self, condition_engine: ConditionEngine,
                 candle_buffer=None, log_fn=None):
        self._ce  = condition_engine
        self._buf = candle_buffer
        self._log = log_fn or print

    def set_candle_buffer(self, buf) -> None:
        self._buf = buf
        self._ce.set_candle_buffer(buf)

    # ── 截面扫描（实时选股） ──────────────────────────────────────────

    def scan(self, symbols: List[str], strategy: Strategy,
             n_bars: int = 300,
             _bars_dict: Optional[Dict[str, list]] = None) -> SignalBatch:
        batch = SignalBatch(
            batch_id=uuid.uuid4().hex[:10],
            strategy_name=strategy.name,
            source=SignalSource.SCAN,
            run_dt=datetime.now(),
            params={"n_bars": n_bars, "symbols": len(symbols)},
        )
        eval_fn = self._ce.eval_condition
        for sym in symbols:
            bars = _bars_dict.get(sym, []) if _bars_dict is not None \
                   else self._get_bars(sym, n_bars)
            if len(bars) < strategy.params.min_bars:
                continue
            passed, score = strategy.buy_tree.evaluate(sym, bars, eval_fn)
            if not passed:
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

    # ── 历史回测 ──────────────────────────────────────────────────────

    def backtest(self, symbols: List[str], strategy: Strategy,
                 all_bars_dict: Dict[str, list],
                 warmup: int = 60,
                 is_intraday: bool = False) -> SignalBatch:
        """
        对每个 symbol 的全量 K 线做逐日滚动回测。
        卖出阈值统一来自 strategy.params。

        Args:
            is_intraday: 是否为分钟线回测（True时启用T+1规则）
        """
        batch = SignalBatch(
            batch_id=uuid.uuid4().hex[:10],
            strategy_name=strategy.name,
            source=SignalSource.BACKTEST,
            run_dt=datetime.now(),
            params={"warmup": warmup, "symbols": len(symbols)},
        )
        for sym in symbols:
            bars = all_bars_dict.get(sym, [])
            if len(bars) < warmup + 2:
                continue
            signals = self._backtest_symbol(sym, bars, strategy, warmup,
                                            is_intraday=is_intraday)
            batch.signals.extend(signals)
        self._log(f"[ScanEngine] backtest {strategy.name}: "
                  f"{len(symbols)} 股 → {batch.count} 信号")
        return batch

    def _backtest_symbol(self, symbol: str, all_bars: list,
                         strategy: Strategy, warmup: int,
                         is_intraday: bool = False) -> List[SignalRecord]:
        """
        逐日滚动回测单只股票。
        所有止损/止盈/追踪/持仓上限阈值统一从 strategy.params 读取，
        并透传给 eval_exit，彻底消除双参数体系的不一致。
        冷却期机制：卖出后 cooldown_days 交易日内禁止重新买入同一股票。
        同日冲突规则：买入条件和卖出条件同时满足时，不执行任何操作（空仓）或只卖不买（持仓）。
        A股T+1：分钟线模式下，买入当天不可卖出，需等到下一个交易日。
        """
        signals: List[SignalRecord] = []
        eval_fn = self._ce.eval_condition
        sp      = strategy.params          # 唯一参数源
        cost    = sp.commission_rate + sp.stamp_duty_rate + sp.slippage_rate
        
        # 冷却期追踪：记录最近一次卖出的 bar 索引（按 K 线根数计算冷却期）
        last_exit_idx: int = -9999

        i = warmup
        while i < len(all_bars) - 1:
            # 冷却期检查：距离上次卖出不足 cooldown_days 根K线，跳过买入
            if sp.cooldown_days > 0:
                bars_since_exit = i - last_exit_idx
                if bars_since_exit <= sp.cooldown_days:
                    i += 1
                    continue
            
            bars_so_far = all_bars[:i + 1]
            passed, score = strategy.buy_tree.evaluate(symbol, bars_so_far, eval_fn)
            if not passed:
                i += 1
                continue
            
            # 同日冲突检查：买入条件满足时，也检查卖出条件是否同时满足
            # 如果卖出条件也满足（空仓状态下），说明信号矛盾，不买入
            sell_triggered, _ = self._eval_sell_tree(
                strategy.sell_tree, symbol, 
                entry_price=all_bars[i].close,  # 假设买入价
                cur_price=all_bars[i].close, 
                peak_price=all_bars[i].close,
                hold_days=0,
                bars=bars_so_far, 
                sp=sp,
            )
            if sell_triggered:
                # 同一根K线买入和卖出条件都满足 → 信号冲突，跳过
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
            # 持仓上限：统一按 K 线根数计算（用户自行根据周期设置合理值）
            max_j = min(i + sp.max_hold_days, len(all_bars) - 1)
            exit_bar    = max_j
            exit_price  = all_bars[max_j].close
            exit_reason = "max_hold"
            
            # A股T+1规则：买入当天不可卖出
            # 日线模式：买入日就是当日，下一根K线就是下一个交易日，start_j = i+1 即可
            # 分钟线模式：买入当天剩余的K线都不能卖出，需跳到下一个交易日
            entry_date = entry_bar.dt.date()
            start_j = i + 1
            if is_intraday:
                for j in range(i + 1, max_j + 1):
                    j_date = all_bars[j].dt.date()
                    if j_date > entry_date:
                        start_j = j
                        break
                else:
                    # 整个持仓剩余都在同一天，只能持有到最后一根K线平仓
                    start_j = max_j
            
            # 现在从start_j开始检查卖出条件
            for j in range(start_j, max_j + 1):
                cur_price = all_bars[j].close
                if cur_price > peak_price:
                    peak_price = cur_price

                # hold_bars: 持仓K线根数（与 max_hold_days 同单位）
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
            if exit_dt:
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
            
            # 更新冷却期追踪：记录本次卖出的 bar 索引
            last_exit_idx = exit_bar
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

        start_date = all_bars[start_idx].dt.date()
        days_passed = 0
        last_valid_idx = start_idx

        for j in range(start_idx + 1, len(all_bars)):
            cur_date = all_bars[j].dt.date()
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

    def _get_bars(self, symbol: str, n: int) -> list:
        if self._buf is None:
            return []
        try:
            return self._buf.get(symbol, n) or []
        except Exception:
            return []
