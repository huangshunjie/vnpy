"""
platform_engineering/event.py
所有平台级事件常量。
"""

# ── Observability ──────────────────────────────────────────────────
EVENT_PE_METRIC_UPDATED   = "ePE_MetricUpdated"
EVENT_PE_ALERT_TRIGGERED  = "ePE_AlertTriggered"
EVENT_PE_ALERT_RESOLVED   = "ePE_AlertResolved"
EVENT_PE_HEALTH_UPDATED   = "ePE_HealthUpdated"

# ── Task Execution ─────────────────────────────────────────────────
EVENT_PE_TASK_CREATED     = "ePE_TaskCreated"
EVENT_PE_TASK_QUEUED      = "ePE_TaskQueued"
EVENT_PE_TASK_STARTED     = "ePE_TaskStarted"
EVENT_PE_TASK_COMPLETED   = "ePE_TaskCompleted"
EVENT_PE_TASK_FAILED      = "ePE_TaskFailed"
EVENT_PE_TASK_CANCELLED   = "ePE_TaskCancelled"
EVENT_PE_TASK_TIMEOUT     = "ePE_TaskTimeout"
EVENT_PE_TASK_RETRYING    = "ePE_TaskRetrying"
EVENT_PE_WORKER_ONLINE    = "ePE_WorkerOnline"
EVENT_PE_WORKER_OFFLINE   = "ePE_WorkerOffline"

# ── Deployment ─────────────────────────────────────────────────────
EVENT_PE_DEPLOY_CREATED   = "ePE_DeployCreated"
EVENT_PE_DEPLOY_STAGED    = "ePE_DeployStaged"
EVENT_PE_DEPLOY_APPROVED  = "ePE_DeployApproved"
EVENT_PE_DEPLOY_REJECTED  = "ePE_DeployRejected"
EVENT_PE_DEPLOY_LIVE      = "ePE_DeployLive"
EVENT_PE_DEPLOY_PAUSED    = "ePE_DeployPaused"
EVENT_PE_DEPLOY_RESUMED   = "ePE_DeployResumed"
EVENT_PE_DEPLOY_ROLLED_BACK = "ePE_DeployRolledBack"
EVENT_PE_DEPLOY_RETIRED   = "ePE_DeployRetired"

# ── Strategy Health ────────────────────────────────────────────────
EVENT_PE_HEALTH_SCORE_UPDATED  = "ePE_HealthScoreUpdated"
EVENT_PE_HEALTH_WARNING        = "ePE_HealthWarning"
EVENT_PE_HEALTH_CRITICAL       = "ePE_HealthCritical"
EVENT_PE_HEALTH_RETIRE_SIGNAL  = "ePE_HealthRetireSignal"

# ── Configuration ──────────────────────────────────────────────────
EVENT_PE_CONFIG_CREATED   = "ePE_ConfigCreated"
EVENT_PE_CONFIG_UPDATED   = "ePE_ConfigUpdated"
EVENT_PE_CONFIG_ROLLED_BACK = "ePE_ConfigRolledBack"
EVENT_PE_CONFIG_DELETED   = "ePE_ConfigDeleted"

# ── Security ───────────────────────────────────────────────────────
EVENT_PE_USER_CREATED     = "ePE_UserCreated"
EVENT_PE_USER_UPDATED     = "ePE_UserUpdated"
EVENT_PE_USER_DELETED     = "ePE_UserDeleted"
EVENT_PE_LOGIN_SUCCESS    = "ePE_LoginSuccess"
EVENT_PE_LOGIN_FAILED     = "ePE_LoginFailed"
EVENT_PE_PERMISSION_DENIED = "ePE_PermissionDenied"
EVENT_PE_AUDIT_LOGGED     = "ePE_AuditLogged"

# ── API Gateway ────────────────────────────────────────────────────
EVENT_PE_API_REQUEST      = "ePE_ApiRequest"
EVENT_PE_API_ERROR        = "ePE_ApiError"

# ── Platform ───────────────────────────────────────────────────────
EVENT_PE_ENGINE_STARTED   = "ePE_EngineStarted"
EVENT_PE_ENGINE_STOPPED   = "ePE_EngineStopped"
EVENT_PE_ERROR            = "ePE_Error"
EVENT_PE_LOG              = "ePE_Log"
