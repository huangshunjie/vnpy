"""
strategy_condition/core/signal.py
信号数据模型：BuySignal / SellSignal / SignalRecord
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..constant import SignalType, SignalSource


@dataclass
class SignalRecord:
    """
    单次信号记录（买入或卖出）。
    由 scan_engine 或 backtest_engine 生成，保存到结果列表供 UI 展示。
    """
    signal_id:    str                   # 唯一 ID
    signal_type:  SignalType            # BUY / SELL
    source:       SignalSource          # scan / backtest / realtime
    symbol:       str                   # 股票代码
    dt:           datetime              # 信号产生时间
    price:        float                 # 触发价格（通常为收盘价）
    score:        float                 # 综合评分 [0, 1]
    strategy_name: str                  = ""    # 所属策略名称
    # 各条件评分明细 {indicator_name: (passed, score)}
    detail:       Dict[str, Any]        = field(default_factory=dict)
    # 持有期结果（回测时填充）
    exit_dt:      Optional[datetime]    = None
    exit_price:   Optional[float]       = None
    exit_reason:  str                   = ""    # stop_loss / take_profit / max_hold
    hold_days:    int                   = 0
    pnl_pct:      Optional[float]       = None  # 收益率（扣成本后）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id":    self.signal_id,
            "signal_type":  self.signal_type.value,
            "source":       self.source.value,
            "symbol":       self.symbol,
            "dt":           str(self.dt)[:19],
            "price":        round(self.price, 4),
            "score":        round(self.score, 4),
            "strategy_name": self.strategy_name,
            "detail":       self.detail,
            "exit_dt":      str(self.exit_dt)[:19] if self.exit_dt else None,
            "exit_price":   round(self.exit_price, 4) if self.exit_price else None,
            "exit_reason":  self.exit_reason,
            "hold_days":    self.hold_days,
            "pnl_pct":      round(self.pnl_pct * 100, 4) if self.pnl_pct is not None else None,
        }

    @property
    def is_profitable(self) -> Optional[bool]:
        if self.pnl_pct is None:
            return None
        return self.pnl_pct > 0

    def __repr__(self) -> str:
        pnl = f" pnl={self.pnl_pct*100:.2f}%" if self.pnl_pct is not None else ""
        return (f"Signal({self.signal_type.value} {self.symbol} "
                f"@{self.price} score={self.score:.3f}{pnl})")


@dataclass
class SignalBatch:
    """
    一次选股或回测运行的信号批次结果汇总。
    """
    batch_id:      str
    strategy_name: str
    source:        SignalSource
    run_dt:        datetime
    signals:       List[SignalRecord]   = field(default_factory=list)
    params:        Dict[str, Any]       = field(default_factory=dict)

    # ── 统计快捷方法 ──────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return len(self.signals)

    @property
    def buy_signals(self) -> List[SignalRecord]:
        return [s for s in self.signals if s.signal_type == SignalType.BUY]

    @property
    def avg_score(self) -> float:
        if not self.signals:
            return 0.0
        return sum(s.score for s in self.signals) / len(self.signals)

    def backtest_metrics(self) -> Dict[str, Any]:
        """快速统计回测结果指标（仅含有 pnl_pct 的信号）"""
        finished = [s for s in self.signals if s.pnl_pct is not None]
        if not finished:
            return {"count": 0, "valid": False}
        pnls    = [s.pnl_pct for s in finished]
        wins    = [p for p in pnls if p > 0]
        hit_rate = len(wins) / len(pnls)
        avg_ret  = sum(pnls) / len(pnls)
        exit_reasons: Dict[str, int] = {}
        for s in finished:
            exit_reasons[s.exit_reason] = exit_reasons.get(s.exit_reason, 0) + 1
        return {
            "count":        len(finished),
            "hit_rate":     round(hit_rate, 4),
            "avg_return":   round(avg_ret * 100, 4),
            "max_return":   round(max(pnls) * 100, 4),
            "min_return":   round(min(pnls) * 100, 4),
            "exit_reasons": exit_reasons,
            "valid":        True,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id":      self.batch_id,
            "strategy_name": self.strategy_name,
            "source":        self.source.value,
            "run_dt":        str(self.run_dt)[:19],
            "count":         self.count,
            "avg_score":     round(self.avg_score, 4),
            "params":        self.params,
            "metrics":       self.backtest_metrics(),
        }
