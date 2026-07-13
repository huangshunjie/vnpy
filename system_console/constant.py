"""
system_console/constant.py
"""
from enum import Enum

APP_NAME = "SystemConsole"


# ── 18 custom modules (module_key → display metadata) ────────────────
MODULE_REGISTRY: list[dict] = [
    # Layer 0 — Data
    {"key": "data_intelligence_ai",          "label": "DIL",        "layer": 0,
     "app_name": "DataIntelligenceAI",        "display": "Data Intelligence AI"},
    # Layer 1 — Signal
    {"key": "alpha_factory_2",               "label": "Alpha",      "layer": 1,
     "app_name": "AlphaFactory2",             "display": "Alpha Factory 2.0"},
    {"key": "market_regime_ai",              "label": "Regime",     "layer": 1,
     "app_name": "MarketRegimeAI",            "display": "Market Regime AI"},
    # Layer 2 — Portfolio/Risk
    {"key": "portfolio_engine",              "label": "Portfolio",  "layer": 2,
     "app_name": "PortfolioEngine",           "display": "Portfolio Engine"},
    {"key": "capital_allocation_ai",         "label": "Capital",    "layer": 2,
     "app_name": "CapitalAllocationAI",       "display": "Capital Allocation AI"},
    {"key": "risk_engine_2",                 "label": "Risk",       "layer": 2,
     "app_name": "RiskEngine2",               "display": "Risk Engine 2.0"},
    # Layer 3 — Strategy
    {"key": "strategy_lifecycle_ai",         "label": "Strategy",   "layer": 3,
     "app_name": "StrategyLifecycleAI",       "display": "Strategy Lifecycle AI"},
    {"key": "research_validation",           "label": "Research",   "layer": 3,
     "app_name": "ResearchValidation",        "display": "Research Validation"},
    {"key": "factor_research",               "label": "Factor",     "layer": 3,
     "app_name": "FactorResearch",            "display": "Factor Research"},
    # Layer 4 — Execution
    {"key": "execution_engine",              "label": "Execution",  "layer": 4,
     "app_name": "ExecutionEngine",           "display": "Execution Engine"},
    {"key": "execution_intelligence_ai",     "label": "Exec-AI",    "layer": 4,
     "app_name": "ExecutionIntelligenceAI",   "display": "Execution Intelligence AI"},
    # Layer 5 — Learning
    {"key": "adaptive_learning_ai",          "label": "Learning",   "layer": 5,
     "app_name": "AdaptiveLearningAI",        "display": "Adaptive Learning AI"},
    # Layer 6 — Global
    {"key": "global_portfolio_intelligence", "label": "GlobalPort", "layer": 6,
     "app_name": "GlobalPortfolioIntelligence", "display": "Global Portfolio Intel"},
    {"key": "live_production",               "label": "Live",       "layer": 6,
     "app_name": "LiveProduction",            "display": "Live Production"},
    {"key": "quant_os",                      "label": "QuantOS",    "layer": 6,
     "app_name": "QuantOS",                   "display": "Quant OS"},
    # Layer 7 — Infrastructure
    {"key": "system_integration_bus",        "label": "SIBus",      "layer": 7,
     "app_name": "SystemIntegrationBus",      "display": "System Integration Bus"},
    {"key": "performance_monitor",           "label": "Monitor",    "layer": 7,
     "app_name": "PerformanceMonitor",        "display": "Performance Monitor"},
    {"key": "backtest_bridge",               "label": "Backtest",   "layer": 7,
     "app_name": "BacktestBridge",            "display": "Backtest Bridge"},
]

MODULE_KEYS: list[str] = [m["key"] for m in MODULE_REGISTRY]


class ModuleState(Enum):
    """模块运行状态。"""
    UNKNOWN  = "unknown"
    STARTING = "starting"
    RUNNING  = "running"
    STOPPING = "stopping"
    STOPPED  = "stopped"
    ERROR    = "error"


class ConsoleStatus(Enum):
    """主控台整体状态。"""
    IDLE     = "idle"
    PARTIAL  = "partial"    # 部分模块运行中
    RUNNING  = "running"    # 全部核心模块运行中
    STOPPING = "stopping"
    ERROR    = "error"


class SystemLayer(Enum):
    """系统层次（用于分组显示）。"""
    DATA        = 0
    SIGNAL      = 1
    PORTFOLIO   = 2
    STRATEGY    = 3
    EXECUTION   = 4
    LEARNING    = 5
    GLOBAL      = 6
    INFRA       = 7
