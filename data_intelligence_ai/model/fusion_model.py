"""
data_intelligence_ai/model/fusion_model.py  (Phase 4)

FusionInput      — 单维度融合输入（来自一个数据源）
FusedState       — 融合后的统一系统状态
FusionRecord     — 单次融合操作记录
FusionState      — 数据融合系统当前状态快照
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import FusionMode, DataType


@dataclass
class FusionInput:
    """单维度融合输入——来自一个数据源的量化信号。"""
    source:      DataType = DataType.MARKET
    symbol:      str      = ""
    score:       float    = 0.0          # 归一化信号值 [0, 1]
    confidence:  float    = 1.0          # 数据质量置信度 [0, 1]
    weight:      float    = 1.0          # 融合权重
    timestamp:   datetime = field(default_factory=datetime.now)
    metadata:    dict     = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source":     self.source.value,
            "symbol":     self.symbol,
            "score":      round(self.score,      6),
            "confidence": round(self.confidence, 4),
            "weight":     round(self.weight,     4),
            "timestamp":  str(self.timestamp)[:19],
        }


@dataclass
class FusedState:
    """
    融合后的统一系统状态（Phase 4 完整版）。

    Unified State = f(market, alpha, portfolio, execution, risk, regime)
    """
    fusion_id:       str        = ""
    mode:            FusionMode = FusionMode.WEIGHTED_AVERAGE
    symbol:          str        = ""
    timestamp:       datetime   = field(default_factory=datetime.now)

    # 各维度分数
    market_score:    float = 0.0
    alpha_score:     float = 0.0
    portfolio_score: float = 0.0
    execution_score: float = 0.0
    risk_score:      float = 0.0
    regime_score:    float = 0.0

    # 融合结果
    unified_score:   float = 0.0         # [0, 1]
    confidence:      float = 1.0         # 融合置信度 [0, 1]
    n_sources:       int   = 0           # 参与融合的数据源数量

    # 融合元数据
    weights_used:    dict  = field(default_factory=dict)    # {source: weight}
    sources_present: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "fusion_id":       self.fusion_id,
            "mode":            self.mode.value,
            "symbol":          self.symbol,
            "timestamp":       str(self.timestamp)[:19],
            "market_score":    round(self.market_score,    4),
            "alpha_score":     round(self.alpha_score,     4),
            "portfolio_score": round(self.portfolio_score, 4),
            "execution_score": round(self.execution_score, 4),
            "risk_score":      round(self.risk_score,      4),
            "regime_score":    round(self.regime_score,    4),
            "unified_score":   round(self.unified_score,   4),
            "confidence":      round(self.confidence,      4),
            "n_sources":       self.n_sources,
            "weights_used":    self.weights_used,
            "sources_present": self.sources_present,
        }


@dataclass
class FusionRecord:
    """单次融合操作的完整记录（含输入快照）。"""
    record_id:    str        = ""
    symbol:       str        = ""
    mode:         FusionMode = FusionMode.WEIGHTED_AVERAGE
    inputs:       list[FusionInput] = field(default_factory=list)
    result:       FusedState | None = None
    fused_at:     datetime   = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "symbol":    self.symbol,
            "mode":      self.mode.value,
            "n_inputs":  len(self.inputs),
            "result":    self.result.to_dict() if self.result else {},
            "fused_at":  str(self.fused_at)[:19],
        }


@dataclass
class FusionState:
    """数据融合系统当前状态快照（Phase 4）。"""
    total_fusions:   int   = 0
    active_symbols:  int   = 0
    avg_unified:     float = 0.0
    avg_confidence:  float = 1.0
    mode:            FusionMode = FusionMode.WEIGHTED_AVERAGE

    # 按数据源统计
    source_counts:   dict  = field(default_factory=dict)
    symbol_scores:   dict  = field(default_factory=dict)    # {symbol: unified_score}

    updated_at:      datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "total_fusions":  self.total_fusions,
            "active_symbols": self.active_symbols,
            "avg_unified":    round(self.avg_unified,    4),
            "avg_confidence": round(self.avg_confidence, 4),
            "mode":           self.mode.value,
            "source_counts":  self.source_counts,
            "symbol_scores":  {k: round(v, 4) for k, v in self.symbol_scores.items()},
            "updated_at":     str(self.updated_at)[:19],
        }
