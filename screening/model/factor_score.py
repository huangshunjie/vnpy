"""
screening/model/factor_score.py

因子评分与排序结果数据模型（Phase 1）。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from ..constant import ScoreMethod, RankDirection


@dataclass
class FactorWeight:
    """单个因子的权重配置。"""
    factor_name: str
    weight: float = 1.0
    direction: RankDirection = RankDirection.DESC
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "factor_name": self.factor_name,
            "weight": self.weight,
            "direction": self.direction.value,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FactorWeight":
        return cls(
            factor_name=d["factor_name"],
            weight=float(d.get("weight", 1.0)),
            direction=RankDirection(d.get("direction", RankDirection.DESC.value)),
            enabled=bool(d.get("enabled", True)),
        )


@dataclass
class FactorRankConfig:
    """多因子排序配置。"""
    method: ScoreMethod = ScoreMethod.MANUAL
    factors: List[FactorWeight] = field(default_factory=list)
    name: str = "default"

    @property
    def active_factors(self) -> List[FactorWeight]:
        return [f for f in self.factors if f.enabled]

    def to_dict(self) -> dict:
        return {
            "method": self.method.value,
            "factors": [f.to_dict() for f in self.factors],
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FactorRankConfig":
        return cls(
            method=ScoreMethod(d.get("method", ScoreMethod.MANUAL.value)),
            factors=[FactorWeight.from_dict(f) for f in d.get("factors", [])],
            name=d.get("name", "default"),
        )

    @classmethod
    def default_multi_factor(cls) -> "FactorRankConfig":
        """默认多因子配置：动量40% + 质量30% + 价值20% + 低波10%。"""
        return cls(
            name="default_multi",
            method=ScoreMethod.MANUAL,
            factors=[
                FactorWeight("momentum", weight=0.4, direction=RankDirection.DESC),
                FactorWeight("quality",  weight=0.3, direction=RankDirection.DESC),
                FactorWeight("value",    weight=0.2, direction=RankDirection.DESC),
                FactorWeight("low_vol",  weight=0.1, direction=RankDirection.ASC),
            ],
        )


@dataclass
class FactorScore:
    """单只股票的单个因子得分。"""
    symbol: str
    factor_name: str
    raw_value: float = 0.0      # 原始因子值
    z_score: float = 0.0        # 标准化 Z-score
    percentile: float = 0.0     # 百分位排名 (0~1)
    rank: int = 0               # 在 Universe 中的排名

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "factor_name": self.factor_name,
            "raw_value": self.raw_value,
            "z_score": self.z_score,
            "percentile": self.percentile,
            "rank": self.rank,
        }


@dataclass
class RankResult:
    """多因子排序完成后的综合结果。"""
    config: FactorRankConfig
    scores: List[FactorScore] = field(default_factory=list)
    symbol_rank: Dict[str, int] = field(default_factory=dict)
    symbol_composite: Dict[str, float] = field(default_factory=dict)

    def get_top_n(self, n: int) -> List[str]:
        sorted_symbols = sorted(
            self.symbol_composite, key=lambda s: self.symbol_composite[s], reverse=True
        )
        return sorted_symbols[:n]

    def to_dict(self) -> dict:
        return {
            "config": self.config.to_dict(),
            "symbol_rank": dict(self.symbol_rank),
            "symbol_composite": {k: round(v, 6) for k, v in self.symbol_composite.items()},
        }
