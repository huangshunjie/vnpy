"""
screening/model/screening_result.py

选股结果数据模型（Phase 1）。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class StockScore:
    """单只股票的综合评分结果。"""
    symbol: str
    name: str = ""
    composite_score: float = 0.0          # 综合得分 0~100
    rank: int = 0                          # 在结果集中的排名
    factor_contributions: Dict[str, float] = field(default_factory=dict)
    passed_condition: bool = True          # 是否通过条件过滤
    passed_risk_filter: bool = True        # 是否通过风险过滤
    percentile: float = 0.0               # 百分位排名 0~1

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "composite_score": round(self.composite_score, 4),
            "rank": self.rank,
            "factor_contributions": {k: round(v, 4) for k, v in self.factor_contributions.items()},
            "passed_condition": self.passed_condition,
            "passed_risk_filter": self.passed_risk_filter,
            "percentile": round(self.percentile, 4),
        }


@dataclass
class ScreeningResult:
    """一次完整选股运行的结果。"""
    run_id: str
    universe_name: str = ""
    condition_name: str = ""
    factor_config_name: str = ""
    stocks: List[StockScore] = field(default_factory=list)
    total_universe: int = 0               # 初始股票池大小
    total_passed_condition: int = 0       # 通过条件过滤数量
    total_passed_risk: int = 0            # 通过风险过滤数量
    final_count: int = 0                  # 最终入选数量
    generated_at: datetime = field(default_factory=datetime.now)
    elapsed_seconds: float = 0.0

    def get_top_n(self, n: int) -> List[StockScore]:
        return sorted(self.stocks, key=lambda s: s.composite_score, reverse=True)[:n]

    def get_top_pct(self, pct: float) -> List[StockScore]:
        """返回前 pct% 的股票，pct 取值 0~1。"""
        n = max(1, int(len(self.stocks) * pct))
        return self.get_top_n(n)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "universe_name": self.universe_name,
            "condition_name": self.condition_name,
            "factor_config_name": self.factor_config_name,
            "total_universe": self.total_universe,
            "total_passed_condition": self.total_passed_condition,
            "total_passed_risk": self.total_passed_risk,
            "final_count": self.final_count,
            "generated_at": str(self.generated_at)[:19],
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "stocks": [s.to_dict() for s in self.stocks],
        }
