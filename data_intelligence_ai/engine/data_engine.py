"""
data_intelligence_ai/engine/data_engine.py  (Phase 1 Stub)

DataEngine — 顶层数据引擎骨架。
Phase 1: 仅骨架，无任何数据处理逻辑。
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable

from ..constant import APP_NAME, SystemStatus
from ..event import (
    EVENT_DATA_INGESTED,
    EVENT_FEATURE_UPDATED,
    EVENT_DATA_QUALITY_CHECKED,
    EVENT_DATA_FUSED,
    EVENT_DATA_UPDATED,
)


class DataEngine:
    """数据智能系统顶层引擎（Phase 1 骨架）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log         = log_fn or (lambda m: None)
        self._status      = SystemStatus.IDLE
        self._started_at: datetime | None = None
        self._ingest_count  = 0
        self._feature_count = 0

    def init(self) -> None:
        self._log(f"[{APP_NAME}] DataEngine init()")
        self._status = SystemStatus.IDLE

    def start(self) -> None:
        self._started_at = datetime.now()
        self._status     = SystemStatus.INGESTING
        self._log(f"[{APP_NAME}] DataEngine start()")

    def stop(self) -> None:
        self._status = SystemStatus.STOPPED
        self._log(f"[{APP_NAME}] DataEngine stop()")

    def ingest_data(self, raw: dict) -> dict:
        """
        接收原始数据（Phase 2 实现）。
        Phase 1: 仅计数，返回空结果。
        """
        self._ingest_count += 1
        self._log(f"[{APP_NAME}] ingest_data: {list(raw.keys())}")
        return {}

    def update_feature_store(self, feature: dict) -> dict:
        """
        更新特征仓库（Phase 2 实现）。
        Phase 1: 仅计数，返回空结果。
        """
        self._feature_count += 1
        self._log(f"[{APP_NAME}] update_feature_store: {feature.get('feature_name','')}")
        return {}

    def dispatch_event(self, event_type: str, data: dict | None = None) -> None:
        """广播事件（由 GlobalDataEngine 覆盖实现）。"""
        self._log(f"[{APP_NAME}] dispatch_event: {event_type}")

    def get_status(self) -> SystemStatus:
        return self._status

    def _uptime(self) -> float:
        if self._started_at is None:
            return 0.0
        return round((datetime.now() - self._started_at).total_seconds(), 1)

    def summary(self) -> dict:
        return {
            "phase":         1,
            "status":        self._status.value,
            "uptime":        self._uptime(),
            "ingest_count":  self._ingest_count,
            "feature_count": self._feature_count,
        }
