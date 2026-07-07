"""
platform_engineering/model/metric.py
指标、告警、健康分数模型。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from ..constant import MetricLayer, MetricType, HealthLevel, AlertSeverity


@dataclass
class MetricPoint:
    metric_id:   str       = ""
    name:        str       = ""
    layer:       MetricLayer  = MetricLayer.SYSTEM
    metric_type: MetricType   = MetricType.GAUGE
    value:       float     = 0.0
    unit:        str       = ""
    labels:      Dict[str, str] = field(default_factory=dict)
    source:      str       = ""
    timestamp:   datetime  = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "metric_id": self.metric_id,
            "name":      self.name,
            "layer":     self.layer.value,
            "value":     self.value,
            "unit":      self.unit,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class MetricSeries:
    series_id: str = ""
    name:      str = ""
    layer:     MetricLayer = MetricLayer.SYSTEM
    points:    List[MetricPoint] = field(default_factory=list)
    max_size:  int = 1000

    def append(self, point: MetricPoint) -> None:
        self.points.append(point)
        if len(self.points) > self.max_size:
            self.points = self.points[-self.max_size:]

    def latest(self) -> Optional[MetricPoint]:
        return self.points[-1] if self.points else None


@dataclass
class AlertRecord:
    alert_id:    str          = ""
    name:        str          = ""
    severity:    AlertSeverity = AlertSeverity.WARNING
    layer:       MetricLayer   = MetricLayer.SYSTEM
    message:     str          = ""
    metric_name: str          = ""
    metric_value: float       = 0.0
    threshold:   float        = 0.0
    source:      str          = ""
    is_resolved: bool         = False
    resolved_at: Optional[datetime] = None
    created_at:  datetime     = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "alert_id":  self.alert_id,
            "name":      self.name,
            "severity":  self.severity.value,
            "message":   self.message,
            "is_resolved": self.is_resolved,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PlatformHealthScore:
    score:       float      = 100.0   # 0-100
    level:       HealthLevel = HealthLevel.GREEN
    data_score:     float   = 100.0
    strategy_score: float   = 100.0
    trading_score:  float   = 100.0
    system_score:   float   = 100.0
    active_alerts:  int     = 0
    updated_at:  datetime   = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "score":          self.score,
            "level":          self.level.value,
            "data_score":     self.data_score,
            "strategy_score": self.strategy_score,
            "trading_score":  self.trading_score,
            "system_score":   self.system_score,
            "active_alerts":  self.active_alerts,
            "updated_at":     self.updated_at.isoformat(),
        }
