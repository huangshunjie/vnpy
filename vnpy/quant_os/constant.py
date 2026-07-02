"""
quant_os/constant.py

Quant OS 枚举常量（Phase 1 定义）。
"""

from __future__ import annotations

from enum import Enum


class OsState(str, Enum):
    """Quant OS 整体运行状态。"""
    IDLE    = "idle"
    RUNNING = "running"
    PAUSED  = "paused"
    STOPPED = "stopped"
    ERROR   = "error"


class ModuleType(str, Enum):
    """子模块类型。"""
    FACTOR     = "factor"
    STRATEGY   = "strategy"
    PORTFOLIO  = "portfolio"
    EXECUTION  = "execution"
    RISK       = "risk"
    VALIDATION = "validation"


class ModuleState(str, Enum):
    """子模块生命周期状态（Phase 2 实现状态机）。"""
    INIT    = "init"
    RUNNING = "running"
    PAUSED  = "paused"
    STOPPED = "stopped"
    ERROR   = "error"


APP_NAME: str = "QuantOS"
