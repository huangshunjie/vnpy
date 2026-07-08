"""check_app_icons.py"""
import sys, pathlib
sys.path.insert(0, r"c:\Users\11229\Documents\GitHub\vnpy")
from importlib import import_module

apps = [
    ("vnpy_ctastrategy",               "CtaStrategyApp"),
    ("vnpy_ctabacktester",             "CtaBacktesterApp"),
    ("vnpy_datamanager",               "DataManagerApp"),
    ("vnpy.app.batch_research",        "BatchResearchApp"),
    ("vnpy.factor_research",           "FactorResearchApp"),
    ("vnpy.portfolio_engine",          "PortfolioEngineApp"),
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

no_icon = []
for mod_name, cls_name in apps:
    try:
        mod = import_module(mod_name)
        cls = getattr(mod, cls_name)
        icon = str(getattr(cls, "icon_name", ""))
        exists = pathlib.Path(icon).exists() if icon else False
        status = "OK " if exists else "NO "
        if not exists:
            no_icon.append((cls_name, getattr(cls, "display_name", ""), icon))
        print(f"{status}  {cls_name:<42}  {icon[:50]}")
    except Exception as e:
        print(f"ERR  {mod_name}: {e}")

print(f"\n=== {len(no_icon)} apps without valid icon ===")
for cls_name, display, icon in no_icon:
    print(f"  {cls_name:<42}  display={display[:40]!r}")
