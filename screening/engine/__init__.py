"""
screening/engine/__init__.py

ScreeningEngine 主引擎 + 所有子引擎统一导出（Phase 9 重构）。

原 engine.py 内容合并到此处，解决与 engine/ 子包的同名冲突。
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from ..constant import APP_NAME, ScreeningStatus
from ..event import (
    EVENT_SCREENING_STARTED,
    EVENT_SCREENING_DONE,
    EVENT_SCREENING_ERROR,
    EVENT_SCREENING_LOG,
    EVENT_UNIVERSE_UPDATED,
    EVENT_SCREENING_PROGRESS,
    EVENT_SCORE_UPDATED,
    EVENT_BACKTEST_DONE,
    EVENT_PORTFOLIO_GENERATED,
)
from .universe_engine   import UniverseEngine
from .condition_engine  import ConditionEngine
from .factor_rank_engine import FactorRankEngine
from .scoring_engine    import ScoringEngine
from .risk_filter_engine import RiskFilterEngine
from .backtest_engine   import BacktestEngine
from .portfolio_engine  import PortfolioEngineBridge
from ..repository.screening_repository import SqliteScreeningRepository


class ScreeningEngine(BaseEngine):
    """Quant Screening Platform 主引擎（Phase 8 完整实现）。"""

    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)

        self._status: ScreeningStatus = ScreeningStatus.IDLE
        self._started_at: Optional[datetime] = None
        self._log_records: list[str] = []

        self._universe_engine    = UniverseEngine(log_fn=self._log)
        self._condition_engine   = ConditionEngine(log_fn=self._log)
        self._factor_rank_engine = FactorRankEngine(log_fn=self._log)
        self._scoring_engine     = ScoringEngine(log_fn=self._log)
        self._risk_filter_engine = RiskFilterEngine(log_fn=self._log)
        self._backtest_engine    = BacktestEngine(log_fn=self._log)
        self._portfolio_bridge   = PortfolioEngineBridge(log_fn=self._log)
        self._repository         = SqliteScreeningRepository()

        self._log(f"[{APP_NAME}] ScreeningEngine created (Phase 8)")

    # ── BaseEngine ───────────────────────────────────────────────────

    def init(self) -> None:
        self._universe_engine.set_main_engine(self.main_engine)
        self._condition_engine.set_main_engine(self.main_engine)
        self._risk_filter_engine.set_main_engine(self.main_engine)
        self._log(f"[{APP_NAME}] init()")

    def start(self) -> None:
        self._started_at = datetime.now()
        self._log(f"[{APP_NAME}] start()")

    def stop(self) -> None:
        self._log(f"[{APP_NAME}] stop()")
        self._repository.close()

    def close(self) -> None:
        self.stop()

    # ── 主流程 ───────────────────────────────────────────────────────

    def run_screening(self) -> None:
        """完整选股流程（Phase 2-6）。"""
        self._status = ScreeningStatus.RUNNING
        self.dispatch_event(EVENT_SCREENING_STARTED, {"status": "started"})
        try:
            # Phase 2: Universe
            self.dispatch_event(EVENT_SCREENING_PROGRESS, {"step": "universe", "pct": 10})
            universe = self._universe_engine.build_universe()
            if universe:
                self.dispatch_event(EVENT_UNIVERSE_UPDATED, universe.to_dict())
                self._log(f"[{APP_NAME}] Universe: {universe.total_after_filter} 只")
                symbols = universe.symbols
            else:
                self._log(f"[{APP_NAME}] Universe 空")
                symbols = []

            # Phase 3: Condition
            self.dispatch_event(EVENT_SCREENING_PROGRESS, {"step": "condition", "pct": 30})
            symbols = self._condition_engine.filter_symbols(symbols)
            self._log(f"[{APP_NAME}] 条件过滤: {len(symbols)} 只")

            # Phase 4: Factor Ranking
            self.dispatch_event(EVENT_SCREENING_PROGRESS, {"step": "factor", "pct": 50})
            rank_result = self._factor_rank_engine.rank_symbols(symbols)
            if rank_result:
                self._log(f"[{APP_NAME}] 因子排序完成")

            # Phase 5: Scoring
            self.dispatch_event(EVENT_SCREENING_PROGRESS, {"step": "scoring", "pct": 70})
            import uuid as _uuid
            result = self._scoring_engine.score_symbols(
                symbols=symbols,
                rank_result=rank_result,
                run_id=str(_uuid.uuid4())[:8],
                factor_config_name=self._factor_rank_engine.get_config().name,
            )
            if result:
                self.dispatch_event(EVENT_SCORE_UPDATED, result.to_dict())
                self._log(f"[{APP_NAME}] 评分完成: Top1={result.stocks[0].symbol if result.stocks else 'N/A'}")

            # Phase 6: Risk Filter
            self.dispatch_event(EVENT_SCREENING_PROGRESS, {"step": "risk", "pct": 85})
            if result:
                result, risk_log = self._risk_filter_engine.filter_result(result)
                for msg in risk_log[:5]:
                    self._log(f"[{APP_NAME}] 风险过滤: {msg}")
                passed = [s for s in result.stocks if s.passed_risk_filter]
                self._log(f"[{APP_NAME}] 风险过滤完成: {len(passed)} 只通过")
                self.dispatch_event(EVENT_SCORE_UPDATED, result.to_dict())

        except Exception as e:
            import traceback
            self._log(f"[{APP_NAME}] run_screening 异常: {e}\n{traceback.format_exc()}")
            self.dispatch_event(EVENT_SCREENING_ERROR, {"msg": str(e)})
            self._status = ScreeningStatus.ERROR
            return

        self._status = ScreeningStatus.DONE
        self.dispatch_event(EVENT_SCREENING_DONE, {
            "status": "done",
            "symbol_count": len(symbols),
        })

    def run_backtest(self) -> None:
        """选股组合回测（Phase 7）。"""
        sr = self._scoring_engine.get_last_result()
        if not sr or not sr.stocks:
            self._log(f"[{APP_NAME}] run_backtest: 请先运行选股流程")
            return
        symbols = [s.symbol for s in sr.stocks if s.passed_risk_filter]
        scores  = {s.symbol: s.composite_score for s in sr.stocks}
        result  = self._backtest_engine.run_backtest(symbols, scores)
        if result:
            self.dispatch_event(EVENT_BACKTEST_DONE, result.to_dict())

    def generate_portfolio(self) -> None:
        """生成组合权重建议（Phase 8）。"""
        sr = self._scoring_engine.get_last_result()
        if not sr or not sr.stocks:
            self._log(f"[{APP_NAME}] generate_portfolio: 请先运行选股流程")
            return
        symbols = [s.symbol for s in sr.stocks if s.passed_risk_filter]
        scores  = {s.symbol: s.composite_score for s in sr.stocks}
        result  = self._portfolio_bridge.generate_portfolio(symbols, scores)
        if result:
            self.dispatch_event(EVENT_PORTFOLIO_GENERATED, result.to_dict())

    # ── 子引擎访问器 ──────────────────────────────────────────────────

    @property
    def universe_engine(self) -> UniverseEngine:
        return self._universe_engine

    @property
    def condition_engine(self) -> ConditionEngine:
        return self._condition_engine

    @property
    def factor_rank_engine(self) -> FactorRankEngine:
        return self._factor_rank_engine

    @property
    def scoring_engine(self) -> ScoringEngine:
        return self._scoring_engine

    @property
    def risk_filter_engine(self) -> RiskFilterEngine:
        return self._risk_filter_engine

    @property
    def backtest_engine(self) -> BacktestEngine:
        return self._backtest_engine

    @property
    def portfolio_bridge(self) -> PortfolioEngineBridge:
        return self._portfolio_bridge

    @property
    def repository(self) -> SqliteScreeningRepository:
        return self._repository

    # ── 状态 ─────────────────────────────────────────────────────────

    def get_status(self) -> ScreeningStatus:
        return self._status

    def is_running(self) -> bool:
        return self._status == ScreeningStatus.RUNNING

    def get_summary(self) -> dict:
        uptime = 0.0
        if self._started_at:
            uptime = round((datetime.now() - self._started_at).total_seconds(), 1)
        return {
            "app": APP_NAME, "phase": 8,
            "status": self._status.value, "uptime": uptime,
            "universe":     self._universe_engine.summary(),
            "condition":    self._condition_engine.summary(),
            "factor_rank":  self._factor_rank_engine.summary(),
            "scoring":      self._scoring_engine.summary(),
            "risk_filter":  self._risk_filter_engine.summary(),
            "backtest":     self._backtest_engine.summary(),
            "portfolio":    self._portfolio_bridge.summary(),
        }

    # ── 事件 / 日志 ───────────────────────────────────────────────────

    def dispatch_event(self, event_type: str, data: dict = None) -> None:
        self.event_engine.put(Event(event_type, data or {}))

    def _log(self, msg: str) -> None:
        ts = str(datetime.now())[:19]
        self._log_records.append(f"{ts}  {msg}")
        self.dispatch_event(EVENT_SCREENING_LOG, {"msg": msg, "ts": ts})
        try:
            self.write_log(msg)
        except Exception:
            pass

    def get_logs(self, limit: int = 200) -> list:
        return self._log_records[-limit:]


__all__ = [
    "ScreeningEngine",
    "UniverseEngine",
    "ConditionEngine",
    "FactorRankEngine",
    "ScoringEngine",
    "RiskFilterEngine",
    "BacktestEngine",
    "PortfolioEngineBridge",
]
