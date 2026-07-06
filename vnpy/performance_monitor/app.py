"""
performance_monitor/app.py
"""
from vnpy.trader.app import BaseApp
from .constant import APP_NAME
from .engine import PerformanceMonitorEngine


class PerformanceMonitorApp(BaseApp):
    app_name     = APP_NAME
    app_module   = "vnpy.performance_monitor"
    app_path     = __file__
    display_name = "Performance Monitor  全系统实时监控"
    engine_class = PerformanceMonitorEngine
    widget_name  = "PerformanceDashboard"
    icon_name    = ""
