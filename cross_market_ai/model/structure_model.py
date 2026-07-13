"""
cross_market_ai/model/structure_model.py

Phase 2: 市场结构数据模型 — 完整字段定义。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VolatilityStructure:
    """波动率结构维度。"""
    annual_vol:       float = 0.0
    daily_vol:        float = 0.0
    vol_of_vol:       float = 0.0
    skew:             float = 0.0
    excess_kurtosis:  float = 0.0
    jump_intensity:   float = 0.0
    source:           str   = "prior"

    def to_dict(self) -> dict:
        return {
            "annual_vol":      self.annual_vol,
            "daily_vol":       self.daily_vol,
            "vol_of_vol":      self.vol_of_vol,
            "skew":            self.skew,
            "excess_kurtosis": self.excess_kurtosis,
            "jump_intensity":  self.jump_intensity,
            "source":          self.source,
        }


@dataclass
class LiquidityStructure:
    """流动性结构维度。"""
    bid_ask_spread_bps:  float = 0.0
    depth_score:         float = 0.0
    turnover_ratio:      float = 0.0
    market_impact_coeff: float = 0.0
    lot_size:            float = 1.0
    tick_size:           float = 0.01
    source:              str   = "prior"

    def to_dict(self) -> dict:
        return {
            "bid_ask_spread_bps":  self.bid_ask_spread_bps,
            "depth_score":         self.depth_score,
            "turnover_ratio":      self.turnover_ratio,
            "market_impact_coeff": self.market_impact_coeff,
            "lot_size":            self.lot_size,
            "tick_size":           self.tick_size,
            "source":              self.source,
        }


@dataclass
class ParticipantStructure:
    """参与者结构维度。"""
    retail_ratio:         float = 0.0
    institutional_ratio:  float = 0.0
    hft_ratio:            float = 0.0
    info_asymmetry:       float = 0.0
    source:               str   = "prior"

    def to_dict(self) -> dict:
        return {
            "retail_ratio":        self.retail_ratio,
            "institutional_ratio": self.institutional_ratio,
            "hft_ratio":           self.hft_ratio,
            "info_asymmetry":      self.info_asymmetry,
            "source":              self.source,
        }


@dataclass
class MicrostructureNoise:
    """微观结构噪音维度。"""
    noise_ratio:         float = 0.0
    autocorr_lag1:       float = 0.0
    price_discreteness:  float = 0.0
    adverse_selection:   float = 0.0
    limit_distortion:    float = 0.0
    source:              str   = "prior"

    def to_dict(self) -> dict:
        return {
            "noise_ratio":        self.noise_ratio,
            "autocorr_lag1":      self.autocorr_lag1,
            "price_discreteness": self.price_discreteness,
            "adverse_selection":  self.adverse_selection,
            "limit_distortion":   self.limit_distortion,
            "source":             self.source,
        }


@dataclass
class RegimeDistribution:
    """Regime 分布维度。"""
    distribution:    dict  = field(default_factory=dict)
    n_regimes:       int   = 0
    dominant_regime: str   = ""
    entropy:         float = 0.0
    source:          str   = "prior"

    def to_dict(self) -> dict:
        return {
            "distribution":    self.distribution,
            "n_regimes":       self.n_regimes,
            "dominant_regime": self.dominant_regime,
            "entropy":         self.entropy,
            "source":          self.source,
        }


@dataclass
class MarketStructureVector:
    """
    市场结构完整向量 Vector(σ, liquidity, regime, noise, correlation)。

    这是 Cross-Market Intelligence System 的核心数据结构。
    所有跨市场分析均基于此向量进行比较和迁移。
    """
    market_id:    str = ""
    market_type:  str = ""

    volatility:   VolatilityStructure   = field(default_factory=VolatilityStructure)
    liquidity:    LiquidityStructure    = field(default_factory=LiquidityStructure)
    participant:  ParticipantStructure  = field(default_factory=ParticipantStructure)
    noise:        MicrostructureNoise   = field(default_factory=MicrostructureNoise)
    regime:       RegimeDistribution    = field(default_factory=RegimeDistribution)

    # 跨市场相关性（与其他市场的相关系数字典）
    cross_correlations: dict = field(default_factory=dict)

    # 综合结构评分（由 StructureMapper 计算）
    complexity_score:    float = 0.0   # 市场复杂度 ∈ [0, 1]
    tradability_score:   float = 0.0   # 可交易性 ∈ [0, 1]
    portability_score:   float = 0.0   # Alpha 可迁移性先验 ∈ [0, 1]

    computed_at: str = ""
    phase:       int = 2

    def to_dict(self) -> dict:
        return {
            "market_id":          self.market_id,
            "market_type":        self.market_type,
            "volatility":         self.volatility.to_dict(),
            "liquidity":          self.liquidity.to_dict(),
            "participant":        self.participant.to_dict(),
            "noise":              self.noise.to_dict(),
            "regime":             self.regime.to_dict(),
            "cross_correlations": self.cross_correlations,
            "complexity_score":   self.complexity_score,
            "tradability_score":  self.tradability_score,
            "portability_score":  self.portability_score,
            "computed_at":        self.computed_at,
            "phase":              self.phase,
        }

    def to_numeric_vector(self) -> list[float]:
        """
        将结构向量压缩为数值列表，用于距离计算。
        维度顺序：[σ, liq, participant, noise, regime_entropy]
        """
        return [
            self.volatility.annual_vol,
            self.liquidity.bid_ask_spread_bps / 100.0,
            self.participant.retail_ratio,
            self.noise.noise_ratio,
            self.regime.entropy,
        ]


@dataclass
class StructureState:
    """市场结构映射器运行状态。"""
    total_mapped:    int   = 0
    markets:         list  = field(default_factory=list)
    last_market_id:  str   = ""
    status:          str   = "idle"
    last_updated:    str   = ""

    def to_dict(self) -> dict:
        return {
            "total_mapped":   self.total_mapped,
            "markets":        self.markets,
            "last_market_id": self.last_market_id,
            "status":         self.status,
            "last_updated":   self.last_updated,
        }
