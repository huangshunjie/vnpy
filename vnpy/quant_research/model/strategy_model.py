"""
quant_research/model/strategy_model.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..constant import StrategyStatus

STRATEGY_TYPES = [
    "cta", "equity_long", "market_neutral",
    "arbitrage", "high_frequency", "multi_factor", "macro", "other",
]


@dataclass
class StrategyVersion:
    version_id:  str      = ""
    strategy_id: str      = ""
    version:     str      = ""
    note:        str      = ""
    params:      Dict[str, Any] = field(default_factory=dict)
    created_at:  datetime = field(default_factory=datetime.now)
    created_by:  str      = ""

    def to_dict(self) -> dict:
        return {
            "version_id":  self.version_id,
            "strategy_id": self.strategy_id,
            "version":     self.version,
            "note":        self.note,
            "created_at":  self.created_at.isoformat(),
        }


@dataclass
class StrategyRecord:
    strategy_id:    str             = ""
    name:           str             = ""
    version:        str             = "v1.0"
    description:    str             = ""
    status:         StrategyStatus  = StrategyStatus.DRAFT
    strategy_type:  str             = ""
    author:         str             = ""
    code_path:      str             = ""
    params:         Dict[str, Any]  = field(default_factory=dict)

    # 绩效指标
    annual_return:  float           = 0.0
    max_drawdown:   float           = 0.0
    sharpe:         float           = 0.0
    sortino:        float           = 0.0
    calmar:         float           = 0.0
    win_rate:       float           = 0.0
    turnover:       float           = 0.0
    profit_factor:  float           = 0.0

    # 关联
    feature_ids:    List[str]       = field(default_factory=list)
    backtest_ids:   List[str]       = field(default_factory=list)
    dataset_ids:    List[str]       = field(default_factory=list)

    # 版本历史
    versions:       List[StrategyVersion] = field(default_factory=list)

    tags:           List[str]       = field(default_factory=list)
    created_at:     datetime        = field(default_factory=datetime.now)
    updated_at:     datetime        = field(default_factory=datetime.now)
    published_at:   Optional[datetime] = None
    retired_at:     Optional[datetime] = None
    created_by:     str             = ""
    universe:       str             = ""   # 交易标的范围，如 "HS300"

    def to_dict(self) -> dict:
        return {
            "strategy_id":   self.strategy_id,
            "name":          self.name,
            "version":       self.version,
            "status":        self.status.value,
            "strategy_type": self.strategy_type,
            "author":        self.author,
            "annual_return": round(self.annual_return, 4),
            "max_drawdown":  round(self.max_drawdown, 4),
            "sharpe":        round(self.sharpe, 4),
            "tags":          self.tags,
            "created_at":    self.created_at.isoformat(),
            "updated_at":    self.updated_at.isoformat(),
        }
