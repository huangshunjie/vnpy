"""
screening/model/universe.py

股票池数据模型（Phase 1）。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from ..constant import MarketUniverse, UniverseFilter


@dataclass
class UniverseFilterRule:
    """单条基础过滤规则。"""
    filter_type: UniverseFilter
    value: float = 0.0
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "filter_type": self.filter_type.value,
            "value": self.value,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UniverseFilterRule":
        return cls(
            filter_type=UniverseFilter(d["filter_type"]),
            value=float(d.get("value", 0.0)),
            enabled=bool(d.get("enabled", True)),
        )


@dataclass
class UniverseConfig:
    """股票池配置（用户定义的选股范围）。"""
    name: str = "default"
    market: MarketUniverse = MarketUniverse.CSI_300
    custom_symbols: List[str] = field(default_factory=list)
    filter_rules: List[UniverseFilterRule] = field(default_factory=list)
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "market": self.market.value,
            "custom_symbols": list(self.custom_symbols),
            "filter_rules": [r.to_dict() for r in self.filter_rules],
            "description": self.description,
            "created_at": str(self.created_at)[:19],
            "updated_at": str(self.updated_at)[:19],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UniverseConfig":
        return cls(
            name=d.get("name", "default"),
            market=MarketUniverse(d.get("market", MarketUniverse.CSI_300.value)),
            custom_symbols=list(d.get("custom_symbols", [])),
            filter_rules=[UniverseFilterRule.from_dict(r) for r in d.get("filter_rules", [])],
            description=d.get("description", ""),
        )

    @classmethod
    def default(cls) -> "UniverseConfig":
        """默认配置：沪深300，排除 ST，上市满250天，日均成交额 > 5000万。"""
        return cls(
            name="default",
            market=MarketUniverse.CSI_300,
            filter_rules=[
                UniverseFilterRule(UniverseFilter.EXCLUDE_ST, enabled=True),
                UniverseFilterRule(UniverseFilter.EXCLUDE_SUSPENDED, enabled=True),
                UniverseFilterRule(UniverseFilter.MIN_LISTING_DAYS, value=250.0),
                UniverseFilterRule(UniverseFilter.MIN_DAILY_TURNOVER, value=5e7),
            ],
        )


@dataclass
class UniverseData:
    """股票池运行结果：经过基础过滤后的股票列表。"""
    config: UniverseConfig
    symbols: List[str] = field(default_factory=list)
    total_before_filter: int = 0
    total_after_filter: int = 0
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "config": self.config.to_dict(),
            "symbols": list(self.symbols),
            "total_before_filter": self.total_before_filter,
            "total_after_filter": self.total_after_filter,
            "generated_at": str(self.generated_at)[:19],
        }
