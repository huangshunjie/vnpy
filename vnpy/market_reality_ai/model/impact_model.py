"""
market_reality_ai/model/impact_model.py

Phase 3: Market Impact Simulator — 完整模型。

冲击分解:
  Total Impact = Temporary + Permanent + Spread Cost
  ─────────────────────────────────────────────────────────
  Temporary : 短暂价格移动，随时间按 power-law 衰减
  Permanent : 永久信息价格影响 (Kyle lambda)
  Spread    : 买卖价差穿越成本 (Kyle 1985 adverse selection)

理论来源:
  Almgren & Chriss (2001) — Optimal execution of portfolio transactions
  Kyle (1985)             — Continuous auctions and insider trading
  Kissell & Glantz (2003) — Managing Trade Execution Risk
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import ImpactType


# ── Market Liquidity Snapshot ─────────────────────────────────────────

@dataclass
class LiquidityState:
    """
    市场流动性快照。

    Fields
    ------
    symbol        : 合约代码
    bid_depth     : 最优买档累计挂单量 (contracts)
    ask_depth     : 最优卖档累计挂单量 (contracts)
    spread_bps    : 买卖价差 (basis points)
    adv           : 日均成交量 (average daily volume)
    volume_1m     : 最近1分钟成交量
    volatility_1h : 最近1小时波动率（年化）
    market_depth  : 可用市场深度指数 ∈ [0.0, 1.0]  (1.0 = 完全流动)
    regime        : 市场状态 (normal / stressed / illiquid / crisis)
    timestamp     : 快照时间戳
    """
    symbol:        str   = ""
    bid_depth:     float = 0.0
    ask_depth:     float = 0.0
    spread_bps:    float = 5.0
    adv:           float = 10000.0
    volume_1m:     float = 0.0
    volatility_1h: float = 0.02
    market_depth:  float = 1.0    # 0.0 = fully illiquid, 1.0 = full depth
    regime:        str   = "normal"
    timestamp:     datetime = field(default_factory=datetime.now)

    @property
    def total_depth(self) -> float:
        return self.bid_depth + self.ask_depth

    @property
    def depth_imbalance(self) -> float:
        """Bid-ask depth imbalance ∈ [-1, +1]. +1 = all bids, -1 = all asks."""
        td = self.total_depth
        if td < 1e-9:
            return 0.0
        return (self.bid_depth - self.ask_depth) / td

    def to_dict(self) -> dict:
        return {
            "symbol":        self.symbol,
            "bid_depth":     round(self.bid_depth,     4),
            "ask_depth":     round(self.ask_depth,     4),
            "spread_bps":    round(self.spread_bps,    4),
            "adv":           self.adv,
            "volume_1m":     round(self.volume_1m,     4),
            "volatility_1h": round(self.volatility_1h, 6),
            "market_depth":  round(self.market_depth,  4),
            "regime":        self.regime,
            "timestamp":     str(self.timestamp)[:19],
        }

    @classmethod
    def stressed(cls, symbol: str = "") -> "LiquidityState":
        return cls(symbol=symbol, spread_bps=20.0, adv=3000.0,
                   market_depth=0.3, volatility_1h=0.06, regime="stressed")

    @classmethod
    def illiquid(cls, symbol: str = "") -> "LiquidityState":
        return cls(symbol=symbol, spread_bps=50.0, adv=1000.0,
                   market_depth=0.1, volatility_1h=0.10, regime="illiquid")

    @classmethod
    def crisis(cls, symbol: str = "") -> "LiquidityState":
        return cls(symbol=symbol, spread_bps=200.0, adv=200.0,
                   market_depth=0.02, volatility_1h=0.25, regime="crisis")


# ── Impact Estimate (single order) ───────────────────────────────────

@dataclass
class ImpactEstimate:
    """
    单笔订单的市场冲击估计结果。

    Components
    ----------
    temporary_bps  : 短暂冲击 (bps) — 衰减型，order 完成后逐渐恢复
    permanent_bps  : 永久冲击 (bps) — Kyle lambda × 信息成本
    spread_cost_bps: 价差成本 (bps) — 穿越买卖价差的成本
    decay_half_life: 短暂冲击半衰期 (秒)
    total_cost_bps : temporary + permanent + spread
    impact_type    : TEMPORARY / PERMANENT / DECAY
    participation  : order_size / adv
    """
    estimate_id:     str        = ""
    symbol:          str        = ""
    order_size:      float      = 0.0
    direction:       int        = 1       # +1 buy / -1 sell
    impact_type:     ImpactType = ImpactType.TEMPORARY

    # computed components
    temporary_bps:   float = 0.0
    permanent_bps:   float = 0.0
    spread_cost_bps: float = 0.0
    total_cost_bps:  float = 0.0

    # meta
    participation:    float = 0.0
    decay_half_life:  float = 300.0   # seconds
    liquidity_state:  LiquidityState = field(
        default_factory=LiquidityState)
    timestamp:        datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "estimate_id":    self.estimate_id,
            "symbol":         self.symbol,
            "order_size":     self.order_size,
            "direction":      self.direction,
            "impact_type":    self.impact_type.value,
            "temporary_bps":  round(self.temporary_bps,   4),
            "permanent_bps":  round(self.permanent_bps,   4),
            "spread_cost_bps":round(self.spread_cost_bps, 4),
            "total_cost_bps": round(self.total_cost_bps,  4),
            "participation":  round(self.participation,   6),
            "decay_half_life":self.decay_half_life,
            "regime":         self.liquidity_state.regime,
            "phase":          3,
        }

    def decayed_impact(self, elapsed_seconds: float) -> float:
        """
        Temporary impact remaining after elapsed_seconds.

        Almgren power-law decay:
          I(t) = I₀ × exp(-ln2 × t / half_life)
        """
        import math
        if self.decay_half_life <= 0:
            return 0.0
        return round(
            self.temporary_bps
            * math.exp(-math.log(2) * elapsed_seconds / self.decay_half_life),
            4)


# ── Market Impact State (aggregate) ──────────────────────────────────

@dataclass
class ImpactState:
    """
    市场冲击仿真整体状态 — 聚合所有已估计的冲击结果。
    """
    total_estimates:    int   = 0
    avg_total_cost_bps: float = 0.0
    avg_temporary_bps:  float = 0.0
    avg_permanent_bps:  float = 0.0
    avg_spread_cost_bps:float = 0.0
    avg_participation:  float = 0.0
    max_cost_bps:       float = 0.0
    estimates:          list[ImpactEstimate] = field(default_factory=list)
    updated_at:         datetime = field(default_factory=datetime.now)

    def update_from_estimates(self) -> None:
        es = self.estimates
        if not es:
            return
        n = len(es)
        self.total_estimates    = n
        self.avg_total_cost_bps = round(
            sum(e.total_cost_bps  for e in es) / n, 4)
        self.avg_temporary_bps  = round(
            sum(e.temporary_bps   for e in es) / n, 4)
        self.avg_permanent_bps  = round(
            sum(e.permanent_bps   for e in es) / n, 4)
        self.avg_spread_cost_bps= round(
            sum(e.spread_cost_bps for e in es) / n, 4)
        self.avg_participation  = round(
            sum(e.participation   for e in es) / n, 6)
        self.max_cost_bps       = round(
            max(e.total_cost_bps  for e in es), 4)
        self.updated_at         = datetime.now()

    def to_dict(self) -> dict:
        return {
            "total_estimates":     self.total_estimates,
            "avg_total_cost_bps":  self.avg_total_cost_bps,
            "avg_temporary_bps":   self.avg_temporary_bps,
            "avg_permanent_bps":   self.avg_permanent_bps,
            "avg_spread_cost_bps": self.avg_spread_cost_bps,
            "avg_participation":   self.avg_participation,
            "max_cost_bps":        self.max_cost_bps,
            "phase":               3,
        }
