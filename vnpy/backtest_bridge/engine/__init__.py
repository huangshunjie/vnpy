"""
backtest_bridge/engine/__init__.py

BacktestBridgeEngine — VeighNa BaseEngine 子类。
将所有模块信号接入 VeighNa 原生回测，提供统一的回测接口。
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from ..constant import (
    APP_NAME, SignalSource, BridgeMode, RunStatus, PositionSizing,
)
from ..event import (
    EVENT_BRIDGE_STARTED, EVENT_BRIDGE_STOPPED,
    EVENT_RUN_STARTED, EVENT_RUN_COMPLETED, EVENT_RUN_FAILED,
    EVENT_BATCH_COMPLETED, EVENT_SIGNAL_INJECTED,
    EVENT_RESULT_UPDATED, EVENT_COMPARISON_READY, EVENT_BRIDGE_LOG,
)
from .bridge_engine import BridgeEngine
from ..model.signal_model import (
    SignalRecord, BacktestConfig, BacktestResult, BatchResult,
)
from ..strategy.signal_feed import SignalFeed


class BacktestBridgeEngine(BaseEngine):
    """
    回测桥接引擎（VeighNa BaseEngine）。

    核心接口：
      inject_signal(rec)              — 注入单条信号
      inject_signals(records)         — 批量注入信号
      inject_from_module(module, ...) — 从模块事件自动注入
      generate_test_signals(...)      — 生成随机测试信号
      run(config)                     — 运行单次回测
      run_batch(configs)              — 批量回测
      get_result(run_id)              — 查询结果
      get_best(metric, n)             — 最优结果排名
      compare(run_ids)                — 多次结果对比
      get_summary()                   — 引擎汇总
    """

    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine,
                 event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)
        self._started_at:  datetime | None = None
        self._log_records: list[str]       = []

        self._bridge = BridgeEngine(log_fn=self._log)
        self._log(f"[{APP_NAME}] BacktestBridgeEngine created")

    # ── lifecycle ─────────────────────────────────────────────────────
    def init(self) -> None:
        self._log(f"[{APP_NAME}] init()")

    def start(self) -> None:
        self._started_at = datetime.now()
        self.dispatch_event(EVENT_BRIDGE_STARTED,
                            {"app": APP_NAME, "status": "started"})
        self._log(f"[{APP_NAME}] started")

    def stop(self) -> None:
        self.dispatch_event(EVENT_BRIDGE_STOPPED,
                            {"uptime": self._uptime()})
        self._log(f"[{APP_NAME}] stopped")

    def close(self) -> None:
        self.stop()

    # ── signal injection ──────────────────────────────────────────────
    def inject_signal(self, rec: SignalRecord) -> None:
        """注入单条信号记录。"""
        self._bridge.add_signal(rec)
        self.dispatch_event(EVENT_SIGNAL_INJECTED, rec.to_dict())

    def inject_signals(self, records: list[SignalRecord]) -> int:
        """批量注入信号，返回注入数量。"""
        count = self._bridge.load_signals(records)
        self.dispatch_event(EVENT_SIGNAL_INJECTED,
                            {"count": count, "batch": True})
        self._log(f"[{APP_NAME}] injected {count} signals")
        return count

    def clear_signals(self) -> None:
        self._bridge.clear_signals()
        self._log(f"[{APP_NAME}] signals cleared")

    def set_source_weights(
        self, weights: dict[SignalSource, float]
    ) -> None:
        self._bridge.set_source_weights(weights)

    def generate_test_signals(
        self,
        symbol:        str,
        start:         datetime,
        end:           datetime,
        interval_days: int       = 1,
        source:        SignalSource = SignalSource.ALPHA_FACTORY,
        seed:          int       = 42,
    ) -> list[SignalRecord]:
        """生成随机测试信号并自动注入（用于开发调试）。"""
        recs = BridgeEngine.generate_random_signals(
            symbol, start, end, interval_days, source, seed)
        self._bridge.load_signals(recs)
        self._log(f"[{APP_NAME}] generated {len(recs)} test signals "
                  f"for {symbol} [{str(start)[:10]} → {str(end)[:10]}]")
        return recs

    # ── backtesting ────────────────────────────────────────────────────
    def run(self, config: BacktestConfig) -> BacktestResult:
        """运行单次回测。"""
        self.dispatch_event(EVENT_RUN_STARTED, config.to_dict())
        result = self._bridge.run(config)
        if result.status == RunStatus.COMPLETED:
            self.dispatch_event(EVENT_RUN_COMPLETED, result.to_dict())
        else:
            self.dispatch_event(EVENT_RUN_FAILED, result.to_dict())
        self.dispatch_event(EVENT_RESULT_UPDATED, result.to_dict())
        return result

    def run_batch(
        self,
        configs:    list[BacktestConfig],
        batch_name: str = "",
        on_progress: Callable | None = None,
    ) -> BatchResult:
        """批量运行，返回 BatchResult。"""
        self._log(
            f"[{APP_NAME}] batch start: {len(configs)} runs")

        def _progress(i, total, r):
            self.dispatch_event(EVENT_RESULT_UPDATED, r.to_dict())
            pct = round(i / total * 100)
            self._log(
                f"[{APP_NAME}] batch [{i}/{total}] {r.name} "
                f"return={r.total_return:.2%} sharpe={r.sharpe_ratio:.3f}")
            if on_progress:
                on_progress(i, total, r)

        batch = self._bridge.run_batch(configs, batch_name, _progress)
        self.dispatch_event(EVENT_BATCH_COMPLETED, batch.to_dict())
        return batch

    def compare(self, run_ids: list[str]) -> list[dict]:
        """返回多次回测结果的对比字典。"""
        data = self._bridge.compare(run_ids)
        self.dispatch_event(EVENT_COMPARISON_READY,
                            {"run_ids": run_ids, "count": len(data)})
        return data

    # ── quick-run helpers ─────────────────────────────────────────────
    def quick_alpha_backtest(
        self,
        vt_symbol: str,
        start:     datetime,
        end:       datetime,
        capital:   float   = 1_000_000,
        max_pos:   float   = 1.0,
        seed:      int     = 42,
    ) -> BacktestResult:
        """一键运行 AlphaFactory 信号回测（含随机信号生成）。"""
        self.generate_test_signals(
            vt_symbol.split(".")[0], start, end, seed=seed)
        config = BacktestConfig(
            config_id      = f"ALPHA_{vt_symbol}",
            name           = f"Alpha/{vt_symbol}",
            vt_symbol      = vt_symbol,
            start          = start,
            end            = end,
            capital        = capital,
            mode           = BridgeMode.FACTOR_DRIVEN,
            signal_source  = SignalSource.ALPHA_FACTORY,
            max_pos        = max_pos,
        )
        return self.run(config)

    def quick_fusion_backtest(
        self,
        vt_symbol: str,
        start:     datetime,
        end:       datetime,
        capital:   float = 1_000_000,
        seed:      int   = 42,
    ) -> BacktestResult:
        """一键运行 DIL Fusion 信号回测。"""
        symbol = vt_symbol.split(".")[0]
        self.generate_test_signals(symbol, start, end,
                                    source=SignalSource.DATA_FUSION, seed=seed)
        self.generate_test_signals(symbol, start, end,
                                    source=SignalSource.MARKET_REGIME, seed=seed+1)
        config = BacktestConfig(
            config_id     = f"FUSION_{vt_symbol}",
            name          = f"Fusion/{vt_symbol}",
            vt_symbol     = vt_symbol,
            start         = start,
            end           = end,
            capital       = capital,
            mode          = BridgeMode.FUSION_DRIVEN,
            signal_source = SignalSource.DATA_FUSION,
        )
        return self.run(config)

    def quick_compare(
        self,
        vt_symbol: str,
        start:     datetime,
        end:       datetime,
        capital:   float = 1_000_000,
    ) -> BatchResult:
        """运行4种模式对比批量回测。"""
        symbol = vt_symbol.split(".")[0]
        for src, seed in [
            (SignalSource.ALPHA_FACTORY,  42),
            (SignalSource.DATA_FUSION,    43),
            (SignalSource.MARKET_REGIME,  44),
        ]:
            self.generate_test_signals(symbol, start, end, source=src, seed=seed)

        configs = [
            BacktestConfig(config_id=f"BB_SIGNAL",  name="Signal-Driven",
                           vt_symbol=vt_symbol, start=start, end=end,
                           capital=capital, mode=BridgeMode.SIGNAL_DRIVEN,
                           signal_source=SignalSource.ALPHA_FACTORY),
            BacktestConfig(config_id=f"BB_FUSION",  name="Fusion-Driven",
                           vt_symbol=vt_symbol, start=start, end=end,
                           capital=capital, mode=BridgeMode.FUSION_DRIVEN,
                           signal_source=SignalSource.DATA_FUSION),
            BacktestConfig(config_id=f"BB_ALPHA",   name="Alpha-Driven",
                           vt_symbol=vt_symbol, start=start, end=end,
                           capital=capital, mode=BridgeMode.FACTOR_DRIVEN,
                           signal_source=SignalSource.ALPHA_FACTORY),
            BacktestConfig(config_id=f"BB_HYBRID",  name="Hybrid",
                           vt_symbol=vt_symbol, start=start, end=end,
                           capital=capital, mode=BridgeMode.HYBRID,
                           signal_source=SignalSource.COMBINED,
                           use_risk_filter=True),
        ]
        self.set_source_weights({
            SignalSource.ALPHA_FACTORY: 0.4,
            SignalSource.DATA_FUSION:   0.4,
            SignalSource.MARKET_REGIME: 0.2,
        })
        return self.run_batch(configs, batch_name=f"Compare/{vt_symbol}")

    # ── query ─────────────────────────────────────────────────────────
    def get_result(self, run_id: str) -> BacktestResult | None:
        return self._bridge.get_result(run_id)

    def get_all_results(self) -> list[BacktestResult]:
        return self._bridge.get_all_results()

    def get_batch(self, batch_id: str) -> BatchResult | None:
        return self._bridge.get_batch(batch_id)

    def get_all_batches(self) -> list[BatchResult]:
        return self._bridge.get_all_batches()

    def get_best(self, metric: str = "sharpe_ratio",
                  n: int = 5) -> list[BacktestResult]:
        return self._bridge.get_best(metric, n)

    def get_feed(self) -> SignalFeed:
        return self._bridge.get_feed()

    def get_logs(self, limit: int = 200) -> list[str]:
        return self._log_records[-limit:]

    def get_summary(self) -> dict:
        bs = self._bridge.summary()
        return {
            "app":           APP_NAME,
            "uptime":        self._uptime(),
            "total_runs":    bs["total_runs"],
            "completed":     bs["completed"],
            "failed":        bs["failed"],
            "total_batches": bs["total_batches"],
            "feed_signals":  bs["feed_signals"],
            "feed_symbols":  bs["feed_symbols"],
            "best_sharpe":   bs["best_sharpe"],
            "best_run_id":   bs["best_run_id"],
        }

    # ── events ────────────────────────────────────────────────────────
    def dispatch_event(self, event_type: str,
                        data: dict | None = None) -> None:
        self.event_engine.put(Event(event_type, data or {}))

    # ── internal ─────────────────────────────────────────────────────
    def _uptime(self) -> float:
        if self._started_at is None:
            return 0.0
        return round((datetime.now() - self._started_at).total_seconds(), 1)

    def _log(self, msg: str) -> None:
        ts = str(datetime.now())[:19]
        self._log_records.append(f"{ts}  {msg}")
        try:    self.write_log(msg)
        except: pass


__all__ = ["BacktestBridgeEngine", "BridgeEngine"]
