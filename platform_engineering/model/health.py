"""
platform_engineering/model/health.py
策略健康监控模型。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from ..constant import HealthStatus, HealthLevel


@dataclass
class HealthMetricSnapshot:
    sharpe:        Optional[float] = None
    max_drawdown:  Optional[float] = None
    win_rate:      Optional[float] = None
    alpha_decay:   Optional[float] = None
    ic_mean:       Optional[float] = None
    ic_std:        Optional[float] = None
    risk_exposure: Optional[float] = None
    order_delay_ms: Optional[float] = None
    fill_rate:     Optional[float] = None
    slippage_bps:  Optional[float] = None
    updated_at:    datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()
                if k != "updated_at" and v is not None}


@dataclass
class StrategyHealthRecord:
    health_id:      str          = ""
    strategy_id:    str          = ""
    strategy_name:  str          = ""
    status:         HealthStatus = HealthStatus.UNKNOWN
    level:          HealthLevel  = HealthLevel.YELLOW
    score:          float        = 0.0      # 0–100
    perf_score:     float        = 0.0
    risk_score:     float        = 0.0
    alpha_score:    float        = 0.0
    exec_score:     float        = 0.0
    snapshot:       HealthMetricSnapshot = field(
                        default_factory=HealthMetricSnapshot)
    warnings:       List[str]    = field(default_factory=list)
    retire_reason:  str          = ""
    last_checked:   datetime     = field(default_factory=datetime.now)
    created_at:     datetime     = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "health_id":     self.health_id,
            "strategy_name": self.strategy_name,
            "status":        self.status.value,
            "level":         self.level.value,
            "score":         self.score,
            "last_checked":  self.last_checked.isoformat(),
        }
