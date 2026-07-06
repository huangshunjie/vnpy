"""
system_console/event.py
"""

APP_NAME = "SystemConsole"

# lifecycle
EVENT_CONSOLE_STARTED        = "eSC_ConsoleStarted"
EVENT_CONSOLE_STOPPED        = "eSC_ConsoleStopped"

# module lifecycle
EVENT_MODULE_STARTING        = "eSC_ModuleStarting"
EVENT_MODULE_STARTED         = "eSC_ModuleStarted"
EVENT_MODULE_STOPPING        = "eSC_ModuleStopping"
EVENT_MODULE_STOPPED         = "eSC_ModuleStopped"
EVENT_MODULE_ERROR           = "eSC_ModuleError"
EVENT_MODULE_STATE_CHANGED   = "eSC_ModuleStateChanged"

# system state
EVENT_SYSTEM_STATE_UPDATED   = "eSC_SystemStateUpdated"
EVENT_ALL_STARTED            = "eSC_AllStarted"
EVENT_ALL_STOPPED            = "eSC_AllStopped"

# dashboard
EVENT_DASHBOARD_TICK         = "eSC_DashboardTick"
EVENT_CONSOLE_LOG            = "eSC_Log"
