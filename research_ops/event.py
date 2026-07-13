"""
research_ops/event.py

ResearchOps Platform 2.0 — 所有事件常量。
命名规则：EVENT_RO_{MODULE}_{ACTION}
"""

# ─────────────────────────────────────────────────────────────────────
# Workspace
# ─────────────────────────────────────────────────────────────────────
EVENT_RO_WS_CREATED    = "eROWsCreated"
EVENT_RO_WS_UPDATED    = "eROWsUpdated"
EVENT_RO_WS_DELETED    = "eROWsDeleted"
EVENT_RO_WS_SWITCHED   = "eROWsSwitched"
EVENT_RO_WS_ARCHIVED   = "eROWsArchived"

EVENT_RO_PRJ_CREATED   = "eROPrjCreated"
EVENT_RO_PRJ_UPDATED   = "eROPrjUpdated"
EVENT_RO_PRJ_DELETED   = "eROPrjDeleted"
EVENT_RO_PRJ_STARRED   = "eROPrjStarred"
EVENT_RO_PRJ_UNSTARRED = "eROPrjUnstarred"

# ─────────────────────────────────────────────────────────────────────
# Experiment
# ─────────────────────────────────────────────────────────────────────
EVENT_RO_EXP_CREATED   = "eROExpCreated"
EVENT_RO_EXP_UPDATED   = "eROExpUpdated"
EVENT_RO_EXP_DELETED   = "eROExpDeleted"
EVENT_RO_EXP_STARTED   = "eROExpStarted"
EVENT_RO_EXP_COMPLETED = "eROExpCompleted"
EVENT_RO_EXP_FAILED    = "eROExpFailed"
EVENT_RO_EXP_ARCHIVED  = "eROExpArchived"

EVENT_RO_RUN_CREATED   = "eRORunCreated"
EVENT_RO_RUN_UPDATED   = "eRORunUpdated"
EVENT_RO_RUN_COMPLETED = "eRORunCompleted"
EVENT_RO_RUN_FAILED    = "eRORunFailed"
EVENT_RO_RUN_KILLED    = "eRORunKilled"

EVENT_RO_METRIC_LOGGED = "eROMetricLogged"
EVENT_RO_PARAM_LOGGED  = "eROParamLogged"
EVENT_RO_TAG_ADDED     = "eROTagAdded"

# ─────────────────────────────────────────────────────────────────────
# Registry — Dataset
# ─────────────────────────────────────────────────────────────────────
EVENT_RO_DS_REGISTERED = "eRODsRegistered"
EVENT_RO_DS_UPDATED    = "eRODsUpdated"
EVENT_RO_DS_DELETED    = "eRODsDeleted"
EVENT_RO_DS_VERSIONED  = "eRODsVersioned"
EVENT_RO_DS_LINEAGE    = "eRODsLineage"

# ─────────────────────────────────────────────────────────────────────
# Registry — Feature
# ─────────────────────────────────────────────────────────────────────
EVENT_RO_FT_REGISTERED = "eROFtRegistered"
EVENT_RO_FT_UPDATED    = "eROFtUpdated"
EVENT_RO_FT_DELETED    = "eROFtDeleted"
EVENT_RO_FT_DEPRECATED = "eROFtDeprecated"
EVENT_RO_FT_IC_UPDATED = "eROFtIcUpdated"

# ─────────────────────────────────────────────────────────────────────
# Registry — Strategy
# ─────────────────────────────────────────────────────────────────────
EVENT_RO_ST_REGISTERED = "eROStRegistered"
EVENT_RO_ST_UPDATED    = "eROStUpdated"
EVENT_RO_ST_DELETED    = "eROStDeleted"
EVENT_RO_ST_STATUS     = "eROStStatus"
EVENT_RO_ST_VERSIONED  = "eROStVersioned"

# ─────────────────────────────────────────────────────────────────────
# Registry — Model
# ─────────────────────────────────────────────────────────────────────
EVENT_RO_ML_REGISTERED = "eROMLRegistered"
EVENT_RO_ML_UPDATED    = "eROMLUpdated"
EVENT_RO_ML_DELETED    = "eROMLDeleted"
EVENT_RO_ML_DEPLOYED   = "eROMLDeployed"
EVENT_RO_ML_RETIRED    = "eROMLRetired"

# ─────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────
EVENT_RO_PL_CREATED    = "eROPlCreated"
EVENT_RO_PL_UPDATED    = "eROPlUpdated"
EVENT_RO_PL_DELETED    = "eROPlDeleted"
EVENT_RO_PL_STARTED    = "eROPlStarted"
EVENT_RO_PL_COMPLETED  = "eROPlCompleted"
EVENT_RO_PL_FAILED     = "eROPlFailed"
EVENT_RO_PL_PAUSED     = "eROPlPaused"
EVENT_RO_PL_RESET      = "eROPlReset"

EVENT_RO_NODE_STARTED   = "eRONodeStarted"
EVENT_RO_NODE_COMPLETED = "eRONodeCompleted"
EVENT_RO_NODE_FAILED    = "eRONodeFailed"
EVENT_RO_NODE_SKIPPED   = "eRONodeSkipped"

# ─────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────
EVENT_RO_RPT_CREATED   = "eRORptCreated"
EVENT_RO_RPT_UPDATED   = "eRORptUpdated"
EVENT_RO_RPT_DELETED   = "eRORptDeleted"
EVENT_RO_RPT_PUBLISHED = "eRORptPublished"
EVENT_RO_RPT_RENDERED  = "eRORptRendered"

# ─────────────────────────────────────────────────────────────────────
# Knowledge Base
# ─────────────────────────────────────────────────────────────────────
EVENT_RO_KB_CREATED    = "eROKbCreated"
EVENT_RO_KB_UPDATED    = "eROKbUpdated"
EVENT_RO_KB_DELETED    = "eROKbDeleted"
EVENT_RO_KB_TAGGED     = "eROKbTagged"

# ─────────────────────────────────────────────────────────────────────
# Governance
# ─────────────────────────────────────────────────────────────────────
EVENT_RO_GOV_SUBMITTED = "eROGovSubmitted"
EVENT_RO_GOV_APPROVED  = "eROGovApproved"
EVENT_RO_GOV_REJECTED  = "eROGovRejected"
EVENT_RO_GOV_FROZEN    = "eROGovFrozen"
EVENT_RO_GOV_RELEASED  = "eROGovReleased"
EVENT_RO_AUDIT_LOGGED  = "eROAuditLogged"

# ─────────────────────────────────────────────────────────────────────
# System
# ─────────────────────────────────────────────────────────────────────
EVENT_RO_LOG           = "eROLog"
EVENT_RO_ERROR         = "eROError"

# ── Registry ──────────────────────────────────────────────────────
EVENT_RO_DS_CREATED    = "eRODsCreated"
EVENT_RO_DS_UPDATED    = "eRODsUpdated"
EVENT_RO_DS_DELETED    = "eRODsDeleted"

EVENT_RO_FT_CREATED    = "eROFtCreated"
EVENT_RO_FT_UPDATED    = "eROFtUpdated"
EVENT_RO_FT_DELETED    = "eROFtDeleted"

EVENT_RO_ST_CREATED    = "eROStCreated"
EVENT_RO_ST_UPDATED    = "eROStUpdated"
EVENT_RO_ST_DELETED    = "eROStDeleted"

EVENT_RO_ML_CREATED    = "eROMLCreated"
EVENT_RO_ML_UPDATED    = "eROMLUpdated"
EVENT_RO_ML_DELETED    = "eROMLDeleted"
EVENT_RO_ML_DEPLOYED   = "eROMLDeployed"
