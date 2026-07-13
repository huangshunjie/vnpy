"""
research_ops/constant.py

ResearchOps Platform 2.0 — 所有枚举常量。
"""
from enum import Enum

APP_NAME = "ResearchOps"


# ─────────────────────────────────────────────────────────────────────
# Workspace / Project
# ─────────────────────────────────────────────────────────────────────

class WorkspaceStatus(Enum):
    ACTIVE   = "active"
    ARCHIVED = "archived"


class ProjectStatus(Enum):
    ACTIVE      = "active"
    PAUSED      = "paused"
    COMPLETED   = "completed"
    ARCHIVED    = "archived"


# ─────────────────────────────────────────────────────────────────────
# Experiment
# ─────────────────────────────────────────────────────────────────────

class ExperimentStatus(Enum):
    DRAFT     = "draft"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    ARCHIVED  = "archived"


class RunStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    KILLED    = "killed"


# ─────────────────────────────────────────────────────────────────────
# Registry — Dataset / Feature / Strategy / Model
# ─────────────────────────────────────────────────────────────────────

class DatasetStatus(Enum):
    PENDING   = "pending"
    READY     = "ready"
    OUTDATED  = "outdated"
    ERROR     = "error"


class FeatureStatus(Enum):
    DRAFT      = "draft"
    REVIEW     = "review"
    STABLE     = "stable"
    DEPRECATED = "deprecated"


class StrategyStatus(Enum):
    IDEA       = "idea"
    RESEARCH   = "research"
    VALIDATED  = "validated"
    PAPER      = "paper"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"


class ModelStatus(Enum):
    TRAINING  = "training"
    EVALUATED = "evaluated"
    DEPLOYED  = "deployed"
    RETIRED   = "retired"


# ─────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────

class PipelineStatus(Enum):
    IDLE      = "idle"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    PAUSED    = "paused"


class NodeStatus(Enum):
    IDLE      = "idle"
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"


class NodeType(Enum):
    DATA_LOAD    = "data_load"
    FEATURE_CALC = "feature_calc"
    MODEL_TRAIN  = "model_train"
    BACKTEST     = "backtest"
    VALIDATION   = "validation"
    REPORT       = "report"
    NOTIFY       = "notify"
    CUSTOM       = "custom"


class TriggerType(Enum):
    MANUAL   = "manual"
    SCHEDULE = "schedule"
    EVENT    = "event"


# ─────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────

class ReportFormat(Enum):
    MARKDOWN = "markdown"
    HTML     = "html"
    PDF      = "pdf"


class ReportType(Enum):
    RESEARCH  = "research"
    BACKTEST  = "backtest"
    FACTOR    = "factor"
    MODEL     = "model"
    RISK      = "risk"
    DAILY     = "daily"
    WEEKLY    = "weekly"
    CUSTOM    = "custom"


# ─────────────────────────────────────────────────────────────────────
# Knowledge Base
# ─────────────────────────────────────────────────────────────────────

class NoteType(Enum):
    RESEARCH  = "research"
    EXPERIENCE = "experience"
    FAILURE   = "failure"
    INSIGHT   = "insight"
    REFERENCE = "reference"


# ─────────────────────────────────────────────────────────────────────
# Governance
# ─────────────────────────────────────────────────────────────────────

class GovernanceStatus(Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FROZEN   = "frozen"
    RELEASED = "released"


class AuditAction(Enum):
    CREATE   = "create"
    UPDATE   = "update"
    DELETE   = "delete"
    APPROVE  = "approve"
    REJECT   = "reject"
    FREEZE   = "freeze"
    RELEASE  = "release"
    DEPLOY   = "deploy"
    RETIRE   = "retire"


# ─────────────────────────────────────────────────────────────────────
# Artifact
# ─────────────────────────────────────────────────────────────────────

class ArtifactType(Enum):
    MODEL    = "model"
    DATASET  = "dataset"
    REPORT   = "report"
    CSV      = "csv"
    EXCEL    = "excel"
    IMAGE    = "image"
    LOG      = "log"
    CONFIG   = "config"
    CODE     = "code"
    OTHER    = "other"


# ─────────────────────────────────────────────────────────────────────
# Priority
# ─────────────────────────────────────────────────────────────────────

class Priority(Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    URGENT = "urgent"
