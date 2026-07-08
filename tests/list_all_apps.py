"""list_all_apps.py"""
import sys
sys.path.insert(0, r"c:\Users\11229\Documents\GitHub\vnpy")

# 直接扫描 run.py 里注册的所有 App 模块
apps_to_check = [
    ("vnpy_ctastrategy",               "CtaStrategyApp"),
    ("vnpy_ctabacktester",             "CtaBacktesterApp"),
    ("vnpy_datamanager",               "DataManagerApp"),
    ("vnpy_portfoliostrategy",         "PortfolioStrategyApp"),
    ("vnpy.portfolio_engine",          "PortfolioEngineApp"),
    ("vnpy.batch_research",            "BatchResearchApp"),
    ("vnpy.factor_research",           "FactorResearchApp"),
    ("vnpy.execution_engine",          "ExecutionEngineApp"),
    ("vnpy.risk_engine_2",             "RiskEngine2App"),
    ("vnpy.research_validation",       "ResearchValidationApp"),
    ("vnpy.quant_os",                  "QuantOSApp"),
    ("vnpy.live_production",           "LiveProductionApp"),
    ("vnpy.alpha_factory_2",           "AlphaFactory2App"),
    ("vnpy.capital_allocation_ai",     "CapitalAllocationApp"),
    ("vnpy.market_regime_ai",          "MarketRegimeApp"),
    ("vnpy.strategy_lifecycle_ai",     "StrategyLifecycleApp"),
    ("vnpy.execution_intelligence_ai", "ExecutionIntelligenceApp"),
    ("vnpy.global_portfolio_intelligence", "GlobalPortfolioIntelligenceApp"),
    ("vnpy.adaptive_learning_ai",      "AdaptiveLearningApp"),
    ("vnpy.data_intelligence_ai",      "DataIntelligenceApp"),
    ("vnpy.system_integration_bus",    "SystemIntegrationBusApp"),
    ("vnpy.performance_monitor",       "PerformanceMonitorApp"),
    ("vnpy.backtest_bridge",           "BacktestBridgeApp"),
    ("vnpy.system_console",            "SystemConsoleApp"),
    ("vnpy.market_reality_ai",         "MarketRealityApp"),
    ("vnpy.temporal_intelligence_ai",  "TemporalIntelligenceApp"),
    ("vnpy.quant_research",            "QuantResearchApp"),
    ("vnpy.platform_engineering",      "PlatformEngineeringApp"),
    ("vnpy.research_ops",              "ResearchOpsApp"),
]

from importlib import import_module
for mod_name, cls_name in apps_to_check:
    try:
        mod = import_module(mod_name)
        cls = getattr(mod, cls_name)
        print(f"app_name={cls.app_name!r:30s} display={cls.display_name!r:30s} widget={cls.widget_name!r}")
    except Exception as e:
        print(f"ERR  {mod_name}.{cls_name}: {e}")
