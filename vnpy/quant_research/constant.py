"""
quant_research/constant.py

所有枚举常量。
"""
from enum import Enum


APP_NAME = "QuantResearch"


class ExperimentStatus(Enum):
    DRAFT     = "draft"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    ARCHIVED  = "archived"


class DatasetStatus(Enum):
    PENDING  = "pending"
    READY    = "ready"
    OUTDATED = "outdated"
    ERROR    = "error"


class FeatureStatus(Enum):
    EXPERIMENTAL = "experimental"
    REVIEW       = "review"
    STABLE       = "stable"
    DEPRECATED   = "deprecated"


class StrategyStatus(Enum):
    DRAFT    = "draft"
    TESTING  = "testing"
    LIVE     = "live"
    RETIRED  = "retired"


class ModelStatus(Enum):
    TRAINING  = "training"
    EVALUATED = "evaluated"
    DEPLOYED  = "deployed"
    RETIRED   = "retired"


class BacktestStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"


class PipelineStatus(Enum):
    IDLE      = "idle"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    PAUSED    = "paused"


class ReportFormat(Enum):
    MARKDOWN = "markdown"
    HTML     = "html"
    PDF      = "pdf"


class ArtifactType(Enum):
    MODEL   = "model"
    REPORT  = "report"
    CSV     = "csv"
    EXCEL   = "excel"
    IMAGE   = "image"
    LOG     = "log"
    CONFIG  = "config"
    OTHER   = "other"


class WorkspaceStatus(Enum):
    ACTIVE   = "active"
    ARCHIVED = "archived"
