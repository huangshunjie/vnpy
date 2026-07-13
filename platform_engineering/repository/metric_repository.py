"""
platform_engineering/repository/metric_repository.py
指标与告警内存存储。
"""
from __future__ import annotations
from typing import Dict, List, Optional
from ..model.metric import MetricPoint, MetricSeries, AlertRecord


class MetricRepository:
    def __init__(self) -> None:
        self._series:  Dict[str, MetricSeries] = {}
        self._alerts:  Dict[str, AlertRecord]  = {}

    # ── series ────────────────────────────────────────────────────
    def get_series(self, name: str) -> Optional[MetricSeries]:
        return self._series.get(name)

    def ensure_series(self, name: str, **kwargs) -> MetricSeries:
        if name not in self._series:
            self._series[name] = MetricSeries(series_id=name, name=name, **kwargs)
        return self._series[name]

    def append_point(self, point: MetricPoint) -> None:
        s = self.ensure_series(point.name, layer=point.layer)
        s.append(point)

    def list_series(self) -> List[MetricSeries]:
        return list(self._series.values())

    def delete_series(self, name: str) -> None:
        self._series.pop(name, None)

    # ── alerts ────────────────────────────────────────────────────
    def save_alert(self, alert: AlertRecord) -> None:
        self._alerts[alert.alert_id] = alert

    def get_alert(self, alert_id: str) -> Optional[AlertRecord]:
        return self._alerts.get(alert_id)

    def list_alerts(self, active_only: bool = False) -> List[AlertRecord]:
        alerts = list(self._alerts.values())
        if active_only:
            alerts = [a for a in alerts if not a.is_resolved]
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)

    def delete_alert(self, alert_id: str) -> None:
        self._alerts.pop(alert_id, None)

    def stats(self) -> dict:
        total   = len(self._alerts)
        active  = sum(1 for a in self._alerts.values() if not a.is_resolved)
        return {
            "series": len(self._series),
            "alerts": total,
            "active_alerts": active,
        }
