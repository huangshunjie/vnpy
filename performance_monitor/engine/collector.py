"""
performance_monitor/engine/collector.py

MetricCollector — 指标采集器（16模块 / 121事件订阅）。
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable

from vnpy.event import EventEngine, Event

from ..constant import ModuleStatus, MONITORED_MODULES, MetricType
from ..model.metric_model import ModuleMetrics, MetricPoint

# ── 全量事件 → (module, is_error) ────────────────────────────────────
_ALL_EVENTS: dict[str, tuple[str, bool]] = {
    # data_intelligence_ai
    "eDI_DataIngested":        ("data_intelligence_ai",   False),
    "eDI_FeatureUpdated":      ("data_intelligence_ai",   False),
    "eDI_DataQualityChecked":  ("data_intelligence_ai",   False),
    "eDI_DataFused":           ("data_intelligence_ai",   False),
    "eDI_DataUpdated":         ("data_intelligence_ai",   False),
    # alpha_factory_2
    "eAlphaFactory.generated": ("alpha_factory_2",        False),
    "eAlphaFactory.scored":    ("alpha_factory_2",        False),
    "eAlphaFactory.screened":  ("alpha_factory_2",        False),
    "eAlphaFactory.rejected":  ("alpha_factory_2",        True),
    "eAlphaFactory.live":      ("alpha_factory_2",        False),
    "eAlphaFactory.retired":   ("alpha_factory_2",        False),
    # market_regime_ai
    "eMarketRegimeDetected":        ("market_regime_ai",  False),
    "eMarketRegimeChanged":         ("market_regime_ai",  False),
    "eMarketVolatilityUpdate":      ("market_regime_ai",  False),
    "eMarketTrendUpdate":           ("market_regime_ai",  False),
    "eMarketLiquidityUpdate":       ("market_regime_ai",  False),
    "eMarketDecisionSignal":        ("market_regime_ai",  False),
    "eMarketRegimeWeightModifier":  ("market_regime_ai",  False),
    "eMarketRiskSignalOutput":      ("market_regime_ai",  False),
    "eMarketCapitalSignalOutput":   ("market_regime_ai",  False),
    "eMarketIntegrationHeartbeat":  ("market_regime_ai",  False),
    # portfolio_engine
    "ePortfolio.update":       ("portfolio_engine",       False),
    "ePortfolio.risk":         ("portfolio_engine",       False),
    "ePortfolio.rebalance":    ("portfolio_engine",       False),
    "ePortfolio.log":          ("portfolio_engine",       False),
    # capital_allocation_ai
    "eCapitalAI.capital_update":      ("capital_allocation_ai", False),
    "eCapitalAI.allocation_updated":  ("capital_allocation_ai", False),
    "eCapitalAI.alpha_rank_updated":  ("capital_allocation_ai", False),
    "eCapitalAI.rebalance_trigger":   ("capital_allocation_ai", False),
    "eCapitalAI.risk_budget_updated": ("capital_allocation_ai", False),
    # risk_engine_2
    "eRiskUpdate":             ("risk_engine_2",          False),
    "eRiskAlert":              ("risk_engine_2",          True),
    "eRiskLimit":              ("risk_engine_2",          True),
    "eRiskDrawdown":           ("risk_engine_2",          True),
    "eRiskLog":                ("risk_engine_2",          False),
    "eRisk.portfolioUpdate":   ("risk_engine_2",          False),
    "eRisk.factorExposure":    ("risk_engine_2",          False),
    "eRisk.orderGate":         ("risk_engine_2",          True),
    "eRisk.styleDrift":        ("risk_engine_2",          False),
    "eRisk.status":            ("risk_engine_2",          False),
    # strategy_lifecycle_ai
    "eStrategyRegistered":           ("strategy_lifecycle_ai", False),
    "eStrategyUpdated":              ("strategy_lifecycle_ai", False),
    "eStrategyDecayDetected":        ("strategy_lifecycle_ai", True),
    "eStrategyEvolved":              ("strategy_lifecycle_ai", False),
    "eStrategyRetired":              ("strategy_lifecycle_ai", False),
    "eStrategyPerformanceUpdate":    ("strategy_lifecycle_ai", False),
    "eStrategyDecayLevelChanged":    ("strategy_lifecycle_ai", False),
    "eStrategyEvolutionTriggered":   ("strategy_lifecycle_ai", False),
    "eStrategyLifecycleHeartbeat":   ("strategy_lifecycle_ai", False),
    # execution_engine
    "eExecutionLog":           ("execution_engine",       False),
    "eOrderUpdate":            ("execution_engine",       False),
    "eFillUpdate":             ("execution_engine",       False),
    "eExecutionError":         ("execution_engine",       True),
    "ePortfolioSignal":        ("execution_engine",       False),
    "eCtaSignal":              ("execution_engine",       False),
    "eFactorSignal":           ("execution_engine",       False),
    "eBatchOrderReq":          ("execution_engine",       False),
    "eExecutionDone":          ("execution_engine",       False),
    # execution_intelligence_ai
    "eExecutionStart":         ("execution_intelligence_ai", False),
    "eOrderSliced":            ("execution_intelligence_ai", False),
    "eImpactEstimated":        ("execution_intelligence_ai", False),
    "eRouteSelected":          ("execution_intelligence_ai", False),
    "eExecutionCompleted":     ("execution_intelligence_ai", False),
    "eFeedbackUpdated":        ("execution_intelligence_ai", False),
    "eExecutionAborted":       ("execution_intelligence_ai", True),
    # adaptive_learning_ai
    "eAL_FeedbackReceived":        ("adaptive_learning_ai", False),
    "eAL_LearningStarted":         ("adaptive_learning_ai", False),
    "eAL_ModelUpdated":            ("adaptive_learning_ai", False),
    "eAL_SystemAdapted":           ("adaptive_learning_ai", False),
    "eAL_LearningCycleCompleted":  ("adaptive_learning_ai", False),
    # global_portfolio_intelligence
    "eGPI_Update":             ("global_portfolio_intelligence", False),
    "eGPI_Rebalance":          ("global_portfolio_intelligence", False),
    "eGPI_RiskAlert":          ("global_portfolio_intelligence", True),
    "eGPI_PositionUpdate":     ("global_portfolio_intelligence", False),
    "eGPI_PerformanceUpdate":  ("global_portfolio_intelligence", False),
    # live_production
    "eLive_Started":           ("live_production",        False),
    "eLive_Stopped":           ("live_production",        False),
    "eLive_OrderSent":         ("live_production",        False),
    "eLive_FillReceived":      ("live_production",        False),
    "eLive_Error":             ("live_production",        True),
    "eLive_StatusUpdate":      ("live_production",        False),
    # quant_os
    "eQOS_Started":            ("quant_os",               False),
    "eQOS_Stopped":            ("quant_os",               False),
    "eQOS_ModuleLoaded":       ("quant_os",               False),
    "eQOS_ModuleError":        ("quant_os",               True),
    "eQOS_Heartbeat":          ("quant_os",               False),
    "eQOS_SystemStatus":       ("quant_os",               False),
    # factor_research
    "eFactorResearch_Updated": ("factor_research",        False),
    "eFactorResearch_Scored":  ("factor_research",        False),
    "eFactorResearch_Expired": ("factor_research",        False),
    "eFactorResearch_Error":   ("factor_research",        True),
    "eFactorResearch_Log":     ("factor_research",        False),
    # research_validation
    "eRV_ValidationStarted":   ("research_validation",    False),
    "eRV_ValidationCompleted": ("research_validation",    False),
    "eRV_ValidationFailed":    ("research_validation",    True),
    "eRV_ReportGenerated":     ("research_validation",    False),
    "eRV_BacktestCompleted":   ("research_validation",    False),
    "eRV_Log":                 ("research_validation",    False),
    # system_integration_bus
    "eSIB_BusStarted":         ("system_integration_bus", False),
    "eSIB_BusStopped":         ("system_integration_bus", False),
    "eSIB_BusDegraded":        ("system_integration_bus", True),
    "eSIB_StageIngest":        ("system_integration_bus", False),
    "eSIB_StageSignal":        ("system_integration_bus", False),
    "eSIB_StageAllocate":      ("system_integration_bus", False),
    "eSIB_StageExecute":       ("system_integration_bus", False),
    "eSIB_StageLearn":         ("system_integration_bus", False),
    "eSIB_BusMessage":         ("system_integration_bus", False),
    "eSIB_EngineHealth":       ("system_integration_bus", False),
    "eSIB_EngineOffline":      ("system_integration_bus", True),
    "eSIB_EngineRecovered":    ("system_integration_bus", False),
    "eSIB_PipelineCycle":      ("system_integration_bus", False),
    "eSIB_PipelineError":      ("system_integration_bus", True),
    "eSIB_SignalForwarded":    ("system_integration_bus", False),
    "eSIB_RiskGate":           ("system_integration_bus", False),
    "eSIB_RegimeBroadcast":    ("system_integration_bus", False),
}


class MetricCollector:
    """指标采集器 — 订阅 16 个模块的全部事件，更新 ModuleMetrics。"""

    def __init__(
        self,
        event_engine: EventEngine,
        on_metric:    Callable | None = None,
        log_fn:       Callable | None = None,
    ) -> None:
        self._ee        = event_engine
        self._on_metric = on_metric or (lambda p: None)
        self._log       = log_fn or (lambda m: None)
        self._metrics: dict[str, ModuleMetrics] = {
            mod: ModuleMetrics(module=mod) for mod in MONITORED_MODULES
        }
        self._last_ts: dict[str, datetime] = {}
        self._registered = False

    def start(self) -> None:
        for ev in _ALL_EVENTS:
            self._ee.register(ev, self._on_event)
        self._registered = True
        self._log(f"[MetricCollector] registered {len(_ALL_EVENTS)} handlers")

    def stop(self) -> None:
        if not self._registered:
            return
        for ev in _ALL_EVENTS:
            try:
                self._ee.unregister(ev, self._on_event)
            except Exception:
                pass
        self._registered = False
        self._log("[MetricCollector] stopped")

    def _on_event(self, event: Event) -> None:
        mapping = _ALL_EVENTS.get(event.type)
        if mapping is None:
            return
        module, is_error = mapping
        m = self._metrics.get(module)
        if m is None:
            return

        now = datetime.now()
        prev = self._last_ts.get(module)
        if prev is not None:
            lat = (now - prev).total_seconds() * 1000.0
            m.latency_ms = round(lat, 3)
            m._latency_buf.append(lat)
        self._last_ts[module] = now

        m.event_count += 1
        m._event_ts_buf.append(now)

        if is_error:
            m.error_count += 1
            m._error_ts_buf.append(now)
            m.last_error = now

        if m.first_seen is None:
            m.first_seen = now
        m.last_seen = now

        prev_status = m.status
        m.status = ModuleStatus.ACTIVE
        if prev_status != ModuleStatus.ACTIVE:
            self._log(f"[MetricCollector] {module} ACTIVE")

        self._on_metric(MetricPoint(
            module=module, metric=MetricType.EVENT_COUNT,
            value=float(m.event_count), unit="count", sampled_at=now,
            tags={"event_type": event.type, "is_error": str(is_error)},
        ))

    # ── direct injection (for testing / simulation) ───────────────────
    def inject(self, event_type: str, data: dict | None = None) -> None:
        """直接注入一条事件（绕过 EventEngine，用于测试）。"""
        from vnpy.event import Event as _Ev
        self._on_event(_Ev(event_type, data or {}))

    # ── query ─────────────────────────────────────────────────────────
    def get_metrics(self, module: str) -> ModuleMetrics | None:
        return self._metrics.get(module)

    def get_all_metrics(self) -> dict[str, ModuleMetrics]:
        return dict(self._metrics)

    @property
    def total_event_types(self) -> int:
        return len(_ALL_EVENTS)

    @property
    def total_events_received(self) -> int:
        return sum(m.event_count for m in self._metrics.values())

    @property
    def total_errors_received(self) -> int:
        return sum(m.error_count for m in self._metrics.values())
