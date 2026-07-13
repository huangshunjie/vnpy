"""
quant_research/model/backtest_model.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..constant import BacktestStatus


@dataclass
class DailyEquity:
    date:          str   = ""
    equity:        float = 0.0
    returns:       float = 0.0
    drawdown:      float = 0.0
    benchmark:     float = 0.0

    def to_dict(self) -> dict:
        return {
            "date":      self.date,
            "equity":    round(self.equity, 4),
            "returns":   round(self.returns, 6),
            "drawdown":  round(self.drawdown, 6),
            "benchmark": round(self.benchmark, 6),
        }


@dataclass
class BacktestRecord:
    backtest_id:    str            = ""
    name:           str            = ""
    description:    str            = ""
    status:         BacktestStatus = BacktestStatus.PENDING

    # 回测参数
    strategy_id:    str            = ""
    strategy_name:  str            = ""
    start_date:     str            = ""
    end_date:       str            = ""
    initial_capital: float         = 1_000_000.0
    commission:     float          = 0.0003
    slippage:       float          = 0.0
    universe:       str            = ""
    params:         Dict[str, Any] = field(default_factory=dict)

    # 绩效指标
    annual_return:  float          = 0.0
    max_drawdown:   float          = 0.0
    sharpe:         float          = 0.0
    sortino:        float          = 0.0
    calmar:         float          = 0.0
    win_rate:       float          = 0.0
    turnover:       float          = 0.0
    profit_factor:  float          = 0.0
    total_return:   float          = 0.0
    alpha:          float          = 0.0
    beta:           float          = 0.0
    information_ratio: float       = 0.0

    # 交易统计
    total_trades:   int            = 0
    avg_holding_days: float        = 0.0
    max_position_conc: float       = 0.0

    # 净值曲线
    equity_curve:   List[DailyEquity] = field(default_factory=list)

    # 月度收益 { "2024-01": 0.023, ... }
    monthly_returns: Dict[str, float] = field(default_factory=dict)

    # 关联
    model_ids:      List[str]      = field(default_factory=list)
    feature_ids:    List[str]      = field(default_factory=list)
    dataset_ids:    List[str]      = field(default_factory=list)

    tags:           List[str]      = field(default_factory=list)
    error_msg:      str            = ""
    created_at:     datetime       = field(default_factory=datetime.now)
    updated_at:     datetime       = field(default_factory=datetime.now)
    submitted_at:   Optional[datetime] = None
    completed_at:   Optional[datetime] = None
    created_by:     str            = ""

    def to_dict(self) -> dict:
        return {
            "backtest_id":   self.backtest_id,
            "name":          self.name,
            "status":        self.status.value,
            "strategy_id":   self.strategy_id,
            "start_date":    self.start_date,
            "end_date":      self.end_date,
            "annual_return": round(self.annual_return, 4),
            "max_drawdown":  round(self.max_drawdown, 4),
            "sharpe":        round(self.sharpe, 4),
            "total_return":  round(self.total_return, 4),
            "created_at":    self.created_at.isoformat(),
        }
