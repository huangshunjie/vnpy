"""
backtest_bridge/engine/bridge_engine.py

BridgeEngine — 核心回测引擎。

职责：
  - 封装 BacktestingEngine（vnpy_ctastrategy）
  - 注入 SignalFeed 到 BridgeCtaStrategy
  - 运行单次 / 批量回测
  - 解析 calculate_statistics() 结果 → BacktestResult
  - 支持多策略对比（同一信号集 + 不同参数）
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable, Type
import uuid
import traceback

from ..constant import (
    BridgeMode, SignalSource, PositionSizing, RunStatus, SignalDirection,
)
from ..model.signal_model import (
    SignalRecord, BacktestConfig, BacktestResult, BatchResult,
)
from ..strategy.signal_feed import SignalFeed
from ..strategy.bridge_strategy  import BridgeCtaStrategy
from ..strategy.alpha_strategy   import AlphaSignalStrategy
from ..strategy.fusion_strategy  import FusionSignalStrategy

# ── strategy class registry ───────────────────────────────────────────
_STRATEGY_MAP: dict[BridgeMode, type] = {
    BridgeMode.SIGNAL_DRIVEN: BridgeCtaStrategy,
    BridgeMode.FUSION_DRIVEN: FusionSignalStrategy,
    BridgeMode.FACTOR_DRIVEN: AlphaSignalStrategy,
    BridgeMode.HYBRID:        BridgeCtaStrategy,
}


def _parse_stats(stats: dict, result: BacktestResult) -> None:
    """从 BacktestingEngine.calculate_statistics() 输出解析关键指标。"""
    result.total_return  = float(stats.get("total_return",  0) or 0)
    result.annual_return = float(stats.get("annual_return", 0) or 0)
    result.max_drawdown  = abs(float(stats.get("max_ddpercent", 0) or 0)) / 100.0
    result.sharpe_ratio  = float(stats.get("sharpe_ratio",  0) or 0)
    result.end_balance   = float(stats.get("end_balance",   0) or 0)

    # calmar = annual_return / max_drawdown
    if result.max_drawdown > 1e-6:
        result.calmar_ratio = round(result.annual_return / result.max_drawdown, 4)

    result.total_trades   = int(stats.get("total_trade_count", 0) or 0)
    result.win_rate       = float(stats.get("win_rate",        0) or 0)
    result.profit_factor  = float(stats.get("profit_factor",   0) or 0)
    result.avg_trade_pnl  = float(stats.get("average_trade",   0) or 0)
    result.total_commission = float(stats.get("total_commission", 0) or 0)
    result.total_slippage   = float(stats.get("total_slippage",   0) or 0)
    result.raw_stats        = {k: v for k, v in stats.items()
                               if v is not None}


class BridgeEngine:
    """核心回测引擎（不继承 BaseEngine，纯计算层）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log  = log_fn or (lambda m: None)
        self._feed = SignalFeed(log_fn=self._log)
        self._results:       list[BacktestResult]  = []
        self._batch_results: list[BatchResult]     = []
        self._run_count = 0

    # ── signal management ─────────────────────────────────────────────
    def load_signals(self, records: list[SignalRecord]) -> int:
        return self._feed.load_signals(records)

    def add_signal(self, rec: SignalRecord) -> None:
        self._feed.add_signal(rec)

    def clear_signals(self) -> None:
        self._feed.clear()

    def set_source_weights(self, weights: dict[SignalSource, float]) -> None:
        self._feed.set_source_weights(weights)

    def get_feed(self) -> SignalFeed:
        return self._feed

    # ── single run ────────────────────────────────────────────────────
    def run(self, config: BacktestConfig) -> BacktestResult:
        """运行单次回测，返回 BacktestResult。"""
        run_id = f"RUN_{uuid.uuid4().hex[:8].upper()}"
        result = BacktestResult(
            run_id    = run_id,
            config_id = config.config_id,
            name      = config.name or run_id,
            status    = RunStatus.RUNNING,
            started_at= datetime.now(),
        )
        self._run_count += 1
        self._log(f"[BridgeEngine] run {run_id}: {config.name} "
                  f"mode={config.mode.value} "
                  f"signal={config.signal_source.value}")

        try:
            from vnpy.trader.constant import Interval, Exchange
            from vnpy_ctastrategy.backtesting import BacktestingEngine

            engine = BacktestingEngine()
            engine.set_parameters(
                vt_symbol  = config.vt_symbol,
                interval   = Interval(config.interval),
                start      = config.start,
                end        = config.end,
                rate       = config.rate,
                slippage   = config.slippage,
                size       = config.size,
                pricetick  = config.pricetick,
                capital    = int(config.capital),
            )

            # select strategy class
            strategy_cls = _STRATEGY_MAP.get(config.mode, BridgeCtaStrategy)

            # build setting
            setting = {
                "signal_threshold": config.signal_threshold,
                "max_pos":          config.max_pos,
                "sizing_method":    config.sizing.value,
                "use_risk_filter":  config.use_risk_filter,
            }

            engine.add_strategy(strategy_cls, setting)

            # inject signal feed into strategy instance
            strategy = engine.strategy
            strategy.signal_feed = self._feed
            self._feed.reset_cursors()

            # signal stats
            symbol = config.vt_symbol.split(".")[0]
            result.signals_total = self._feed.signal_count(symbol)

            # run
            engine.load_data()
            engine.run_backtesting()

            df = engine.calculate_result()
            if df is not None and not df.empty:
                stats = engine.calculate_statistics(output=False)
                _parse_stats(stats, result)

            # collect signal usage from strategy
            if hasattr(strategy, "signals_used"):
                result.signals_used = strategy.signals_used

            result.status      = RunStatus.COMPLETED
            result.finished_at = datetime.now()
            self._log(
                f"[BridgeEngine] {run_id} done: "
                f"return={result.total_return:.2%} "
                f"sharpe={result.sharpe_ratio:.3f} "
                f"maxDD={result.max_drawdown:.2%} "
                f"trades={result.total_trades} "
                f"duration={result.duration_s:.1f}s")

        except Exception as e:
            result.status      = RunStatus.FAILED
            result.error_msg   = str(e)
            result.finished_at = datetime.now()
            self._log(f"[BridgeEngine] {run_id} FAILED: {e}")
            self._log(traceback.format_exc())

        self._results.append(result)
        return result

    # ── batch run ─────────────────────────────────────────────────────
    def run_batch(
        self,
        configs:     list[BacktestConfig],
        batch_name:  str = "",
        on_progress: Callable | None = None,   # (i, total, result) → None
    ) -> BatchResult:
        """批量运行多个配置，返回 BatchResult。"""
        batch_id = f"BATCH_{uuid.uuid4().hex[:8].upper()}"
        batch    = BatchResult(
            batch_id   = batch_id,
            name       = batch_name or batch_id,
            started_at = datetime.now(),
        )
        self._log(
            f"[BridgeEngine] batch {batch_id}: {len(configs)} runs")

        for i, cfg in enumerate(configs):
            result = self.run(cfg)
            batch.results.append(result)
            batch.run_ids.append(result.run_id)
            if on_progress:
                on_progress(i + 1, len(configs), result)

        batch.finished_at = datetime.now()
        self._batch_results.append(batch)
        self._log(
            f"[BridgeEngine] batch {batch_id} done: "
            f"completed={len([r for r in batch.results if r.status==RunStatus.COMPLETED])} "
            f"failed={len([r for r in batch.results if r.status==RunStatus.FAILED])}")
        return batch

    # ── signal generators (convenience) ──────────────────────────────
    @staticmethod
    def generate_random_signals(
        symbol:     str,
        start:      datetime,
        end:        datetime,
        interval_days: int          = 1,
        source:     SignalSource    = SignalSource.ALPHA_FACTORY,
        seed:       int             = 42,
    ) -> list[SignalRecord]:
        """
        生成随机信号序列（用于测试/基准比较）。
        在实际使用中，信号由各模块引擎计算后注入。
        """
        import random
        import math
        from datetime import timedelta

        rng   = random.Random(seed)
        recs  = []
        dt    = start
        trend = 0.0    # random walk trend

        while dt <= end:
            # random walk with mean reversion
            shock  = rng.gauss(0, 0.3)
            trend  = trend * 0.9 + shock * 0.1
            raw_ic = trend + rng.gauss(0, 0.2)
            ic     = max(-1.0, min(1.0, raw_ic))

            direction = (SignalDirection.LONG  if ic >  0.05
                         else SignalDirection.SHORT if ic < -0.05
                         else SignalDirection.FLAT)

            recs.append(SignalRecord(
                signal_id  = f"SIG_{symbol}_{str(dt)[:10]}",
                source     = source,
                symbol     = symbol,
                direction  = direction,
                strength   = round(ic, 4),
                confidence = round(0.5 + abs(ic) * 0.5, 4),
                timestamp  = dt,
            ))
            dt += timedelta(days=interval_days)

        return recs

    # ── query ─────────────────────────────────────────────────────────
    def get_result(self, run_id: str) -> BacktestResult | None:
        for r in self._results:
            if r.run_id == run_id:
                return r
        return None

    def get_all_results(self) -> list[BacktestResult]:
        return list(self._results)

    def get_batch(self, batch_id: str) -> BatchResult | None:
        for b in self._batch_results:
            if b.batch_id == batch_id:
                return b
        return None

    def get_all_batches(self) -> list[BatchResult]:
        return list(self._batch_results)

    def get_best(self, metric: str = "sharpe_ratio",
                  n: int = 5) -> list[BacktestResult]:
        done = [r for r in self._results if r.status == RunStatus.COMPLETED]
        return sorted(done, key=lambda r: getattr(r, metric, 0),
                       reverse=True)[:n]

    def compare(self, run_ids: list[str]) -> list[dict]:
        """返回多次回测结果的对比字典列表。"""
        out = []
        for rid in run_ids:
            r = self.get_result(rid)
            if r:
                out.append(r.to_dict())
        return out

    def summary(self) -> dict:
        done = [r for r in self._results if r.status == RunStatus.COMPLETED]
        fail = [r for r in self._results if r.status == RunStatus.FAILED]
        best_s = max(done, key=lambda r: r.sharpe_ratio) if done else None
        return {
            "total_runs":    self._run_count,
            "completed":     len(done),
            "failed":        len(fail),
            "total_batches": len(self._batch_results),
            "feed_signals":  self._feed.signal_count(),
            "feed_symbols":  len(self._feed.symbols()),
            "best_sharpe":   round(best_s.sharpe_ratio, 4) if best_s else 0.0,
            "best_run_id":   best_s.run_id if best_s else "",
        }
