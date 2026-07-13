"""
performance_monitor/event.py

Performance Monitor — 事件常量。
"""

APP_NAME = "PerformanceMonitor"

# ── 监控生命周期 ──────────────────────────────────────────────────────
EVENT_MONITOR_STARTED       = "ePM_MonitorStarted"
EVENT_MONITOR_STOPPED       = "ePM_MonitorStopped"

# ── 指标更新 ──────────────────────────────────────────────────────────
EVENT_METRIC_UPDATED        = "ePM_MetricUpdated"       # 单个模块指标刷新
EVENT_SNAPSHOT_UPDATED      = "ePM_SnapshotUpdated"     # 全系统快照刷新

# ── 告警 ──────────────────────────────────────────────────────────────
EVENT_ALERT_INFO            = "ePM_AlertInfo"
EVENT_ALERT_WARNING         = "ePM_AlertWarning"
EVENT_ALERT_CRITICAL        = "ePM_AlertCritical"
EVENT_ALERT_FATAL           = "ePM_AlertFatal"

# ── 模块状态变化 ──────────────────────────────────────────────────────
EVENT_MODULE_STATUS_CHANGED = "ePM_ModuleStatusChanged"
EVENT_MODULE_OFFLINE        = "ePM_ModuleOffline"
EVENT_MODULE_RECOVERED      = "ePM_ModuleRecovered"

# ── Dashboard 控制 ────────────────────────────────────────────────────
EVENT_DASHBOARD_REFRESH     = "ePM_DashboardRefresh"
