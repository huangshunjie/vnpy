"""
market_regime_ai/event.py  (Phase 5)

Market Regime Intelligence System — 事件常量。
"""

# Phase 1 ~ 4
EVENT_REGIME_DETECTED   = "eMarketRegimeDetected"
EVENT_REGIME_CHANGED    = "eMarketRegimeChanged"
EVENT_VOLATILITY_UPDATE = "eMarketVolatilityUpdate"
EVENT_TREND_UPDATE      = "eMarketTrendUpdate"
EVENT_LIQUIDITY_UPDATE  = "eMarketLiquidityUpdate"

# Phase 4
EVENT_DECISION_SIGNAL   = "eMarketDecisionSignal"

# Phase 5 — 联动事件
EVENT_REGIME_WEIGHT_MODIFIER   = "eMarketRegimeWeightModifier"   # → Capital Allocation AI
EVENT_RISK_SIGNAL_OUTPUT       = "eMarketRiskSignalOutput"        # → Quant OS / Risk
EVENT_CAPITAL_SIGNAL_OUTPUT    = "eMarketCapitalSignalOutput"     # → Quant OS / Capital
EVENT_INTEGRATION_HEARTBEAT    = "eMarketIntegrationHeartbeat"   # 联动心跳
