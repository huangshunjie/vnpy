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
                 warmup: int = 60) -> SignalBatch:
        """
        对每个 symbol 的全量 K 线做逐日滚动回测。
        卖出阈值统一来自 strategy.params。
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
            signals = self._backtest_symbol(sym, bars, strategy, warmup)
            batch.signals.extend(signals)
        self._log(f"[ScanEngine] backtest {strategy.name}: "
                  f"{len(symbols)} 股 → {batch.count} 信号")
        return batch

    def _backtest_symbol(self, symbol: str, all_bars: list,
                         strategy: Strategy, warmup: int) -> List[SignalRecord]:
        """
        逐日滚动回测单只股票。
        所有止损/止盈/追踪/持仓上限阈值统一从 strategy.params 读取，
        并透传给 eval_exit，彻底消除双参数体系的不一致。
        冷却期机制：卖出后 cooldown_days 交易日内禁止重新买入同一股票。
        同日冲突规则：买入条件和卖出条件同时满足时，不执行任何操作（空仓）或只卖不买（持仓）。
        """
        signals: List[SignalRecord] = []
        eval_fn = self._ce.eval_condition
        sp      = strategy.params          # 唯一参数源
        cost    = sp.commission_rate + sp.stamp_duty_rate + sp.slippage_rate
        
        # 冷却期追踪：记录最近一次卖出的K线索引
        last_exit_idx = -999  # 初始值确保不会误触发冷却

        i = warmup
        while i < len(all_bars) - 1:
            #冷却期检查：如果距离上次卖出不足 cooldown_days 根K线，跳过买入判断
            if i - last_exit_idx <= sp.cooldown_days:
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
            # 持仓上限：不管什么周期，都是按K线根数算最大持仓
            # 日线：max_hold_days = N → 持仓N根 = N天
            # 分钟线：max_hold_days = N → 持仓N根K线
            max_j       = min(i + sp.max_hold_days, len(all_bars) - 1)
            exit_bar    = max_j
            exit_price  = all_bars[max_j].close
            exit_reason = "max_hold"
            
            # A股T+1规则：不能在买入日当天卖出，必须跳过买入日同日内剩余K线
            # 找到第一个日期晚于买入日的K线作为可以卖出的起始点
            entry_date = entry_bar.dt.date()
            start_j = i + 1
            if entry_bar.dt.hour != 0:  # 不是日线，才需要处理T+1
                for j in range(i + 1, max_j + 1):
                    j_date = all_bars[j].dt.date()
                    if j_date > entry_date:
                        start_j = j
                        break
                else:
                    # 整个持仓剩余都在同一天，只能持有到最后一根K线平仓
                    start_j = max_j
            
            # 现在从start_j开始检查卖出条件
            hold_bars_count = 0
            for j in range(start_j, max_j + 1):
                cur_price = all_bars[j].close
                hold_bars_count = j - i
                if cur_price > peak_price:
                    peak_price = cur_price

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
            
            # 更新冷却期追踪：记录本次卖出位置，后续 cooldown_days 根K线内禁止重新买入
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

    # ── 数据获取 ──────────────────────────────────────────────────────

    def _get_bars(self, symbol: str, n: int) -> list:
        if self._buf is None:
            return []
        try:
            return self._buf.get(symbol, n) or []
        except Exception:
            return []
