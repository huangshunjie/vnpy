"""
execution_intelligence_ai/model/impact_model.py  (Phase 3)

ImpactState   — 单次冲击估算结果（含 AC 分解）
ImpactHistory — 历史冲击记录（用于闭环修正）
ImpactParams  — 冲击模型参数
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import ImpactLevel


@dataclass
class ImpactParams:
    """冲击模型参数。"""
    model:      str   = "sqrt"    # "linear" | "sqrt" | "almgren_chriss"
    eta:        float = 0.2       # Almgren-Chriss 临时冲击系数
    gamma:      float = 0.1       # Almgren-Chriss 永久冲击系数
    coeff:      float = 1.0       # linear / sqrt 调节系数
    adv:        float = 1e6       # 日均成交量（股）
    spread_bps: float = 5.0       # 买卖价差（bp）
    alpha:      float = 0.3       # 实时修正权重（EWA）

    def to_dict(self) -> dict:
        return {
            "model":      self.model,
            "eta":        self.eta,
            "gamma":      self.gamma,
            "coeff":      self.coeff,
            "adv":        self.adv,
            "spread_bps": self.spread_bps,
            "alpha":      self.alpha,
        }


@dataclass
class ImpactState:
    """单次冲击估算完整状态。"""
    execution_id:       str         = ""
    symbol:             str         = ""
    order_size:         float       = 0.0
    adv:                float       = 0.0
    volatility:         float       = 0.0
    order_size_ratio:   float       = 0.0    # order_size / adv

    # 估算值
    estimated_bp:       float       = 0.0    # 总估算冲击（bp）
    temporary_bp:       float       = 0.0    # 临时冲击（AC模型）
    permanent_bp:       float       = 0.0    # 永久冲击（AC模型）
    temp_ratio:         float       = 0.0    # 临时冲击占比

    # 实现值（成交后回填）
    realized_bp:        float       = 0.0
    adjusted_bp:        float       = 0.0    # EWA修正后估算

    # 流动性
    liquidity_score:    float       = 1.0
    spread_bps:         float       = 0.0

    impact_level:       ImpactLevel = ImpactLevel.NEGLIGIBLE
    model:              str         = "sqrt"
    estimated_at:       datetime    = field(default_factory=datetime.now)
    realized_at:        datetime | None = None
    meta:               dict        = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "execution_id":     self.execution_id,
            "symbol":           self.symbol,
            "order_size":       self.order_size,
            "adv":              self.adv,
            "volatility":       round(self.volatility,       6),
            "order_size_ratio": round(self.order_size_ratio, 4),
            "estimated_bp":     round(self.estimated_bp,     4),
            "temporary_bp":     round(self.temporary_bp,     4),
            "permanent_bp":     round(self.permanent_bp,     4),
            "temp_ratio":       round(self.temp_ratio,       4),
            "realized_bp":      round(self.realized_bp,      4),
            "adjusted_bp":      round(self.adjusted_bp,      4),
            "liquidity_score":  round(self.liquidity_score,  4),
            "spread_bps":       round(self.spread_bps,       4),
            "impact_level":     self.impact_level.value,
            "model":            self.model,
            "estimated_at":     str(self.estimated_at)[:19],
        }


@dataclass
class ImpactRecord:
    """单条历史冲击记录（用于模型校准）。"""
    execution_id:  str      = ""
    symbol:        str      = ""
    order_size:    float    = 0.0
    adv:           float    = 0.0
    volatility:    float    = 0.0
    estimated_bp:  float    = 0.0
    realized_bp:   float    = 0.0
    error_bp:      float    = 0.0      # realized - estimated
    recorded_at:   datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "symbol":       self.symbol,
            "order_size":   self.order_size,
            "estimated_bp": round(self.estimated_bp, 4),
            "realized_bp":  round(self.realized_bp,  4),
            "error_bp":     round(self.error_bp,      4),
            "recorded_at":  str(self.recorded_at)[:19],
        }


@dataclass
class ImpactHistory:
    """历史冲击记录集合 + 统计摘要。"""
    records: list[ImpactRecord] = field(default_factory=list)

    def add(self, rec: ImpactRecord) -> None:
        self.records.append(rec)

    def recent(self, n: int = 50) -> list[ImpactRecord]:
        return self.records[-n:]

    def mean_error_bp(self) -> float:
        if not self.records:
            return 0.0
        return round(sum(r.error_bp for r in self.records) / len(self.records), 4)

    def rmse_bp(self) -> float:
        if not self.records:
            return 0.0
        import math
        mse = sum(r.error_bp ** 2 for r in self.records) / len(self.records)
        return round(math.sqrt(mse), 4)

    def to_dict(self) -> dict:
        return {
            "count":         len(self.records),
            "mean_error_bp": self.mean_error_bp(),
            "rmse_bp":       self.rmse_bp(),
            "records":       [r.to_dict() for r in self.recent(20)],
        }
