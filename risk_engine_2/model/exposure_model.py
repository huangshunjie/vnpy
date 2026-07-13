"""
risk_engine_2/model/exposure_model.py

风险暴露数据模型（Phase 2）。

PositionSnapshot  : 单标的持仓快照
PortfolioSnapshot : 全组合持仓快照（所有标的合计）
ExposureReport    : 风险暴露分析报告（Beta / 杠杆 / 集中度）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PositionSnapshot:
    """
    单标的持仓快照。

    由 ExposureEngine 从 Execution Engine 的成交回报中实时维护。
    """
    symbol:     str   = ""
    direction:  str   = "LONG"      # "LONG" / "SHORT" / "NET"
    industry:   str   = ""          # 行业分类（Phase 2 集中度计算使用）

    # 数量
    volume:         float = 0.0     # 净持仓（多 - 空）
    long_volume:    float = 0.0
    short_volume:   float = 0.0

    # 价格
    avg_price:      float = 0.0     # 持仓均价
    last_price:     float = 0.0     # 最新价格（来自行情）

    # 市值
    market_value:   float = 0.0     # = volume × last_price × multiplier
    multiplier:     float = 1.0     # 合约乘数

    # 风险属性（Phase 2 beta 暴露使用）
    beta:           float = 1.0     # 相对市场的 beta（默认 1.0）

    # PnL
    unrealized_pnl: float = 0.0

    # 时间
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def notional(self) -> float:
        """名义价值（绝对值）。"""
        return abs(self.volume) * self.last_price * self.multiplier

    @property
    def beta_contribution(self) -> float:
        """该标的对组合 Beta 的贡献 = weight × beta（由 ExposureEngine 计算权重后使用）。"""
        return self.beta * self.market_value

    def update_price(self, last_price: float) -> None:
        """更新最新价格并重算市值和浮动 PnL。"""
        if last_price <= 0:
            return
        self.last_price    = last_price
        self.market_value  = self.volume * last_price * self.multiplier
        self.unrealized_pnl = (last_price - self.avg_price) * self.volume * self.multiplier


@dataclass
class PortfolioSnapshot:
    """
    全组合持仓快照（所有标的汇总）。

    由 ExposureEngine 维护，每次收到成交回报后更新。
    """
    positions:   dict[str, PositionSnapshot] = field(default_factory=dict)
    nav:         float = 0.0            # 组合净值（外部注入）
    updated_at:  datetime = field(default_factory=datetime.now)

    # ── 汇总指标（由 ExposureEngine 计算填充）──────────────────────────────
    total_long_notional:  float = 0.0
    total_short_notional: float = 0.0
    total_net_notional:   float = 0.0
    total_gross_notional: float = 0.0
    leverage:             float = 0.0   # = gross_notional / nav
    portfolio_beta:       float = 0.0   # = Σ (w_i × β_i)

    # 行业集中度：{industry: weight}
    industry_weights: dict[str, float] = field(default_factory=dict)

    @property
    def position_count(self) -> int:
        return len([p for p in self.positions.values() if abs(p.volume) > 1e-9])

    def get_position(self, symbol: str) -> PositionSnapshot | None:
        return self.positions.get(symbol)

    def upsert_position(self, pos: PositionSnapshot) -> None:
        """插入或更新持仓。"""
        self.positions[pos.symbol] = pos
        self.updated_at = datetime.now()

    def remove_position(self, symbol: str) -> None:
        """移除持仓（平仓后调用）。"""
        self.positions.pop(symbol, None)

    def get_weight(self, symbol: str) -> float:
        """获取标的在组合中的权重（market_value / nav）。"""
        if self.nav <= 0:
            return 0.0
        pos = self.positions.get(symbol)
        if pos is None:
            return 0.0
        return pos.market_value / self.nav


@dataclass
class ExposureReport:
    """
    风险暴露分析报告（Phase 2）。

    由 ExposureEngine.compute_report() 生成，
    供 LimitEngine 校验和 UI 展示使用。
    """
    # 组合基本指标
    nav:                  float = 0.0
    position_count:       int   = 0
    total_gross_notional: float = 0.0
    total_net_notional:   float = 0.0
    leverage:             float = 0.0
    portfolio_beta:       float = 0.0

    # 单票最大权重（用于仓位集中度检查）
    max_single_weight:    float = 0.0
    max_single_symbol:    str   = ""

    # 行业集中度：{industry: weight}
    industry_weights:  dict[str, float] = field(default_factory=dict)
    max_industry_weight: float = 0.0
    max_industry_name:   str   = ""

    # 各标的权重：{symbol: weight}
    symbol_weights:    dict[str, float] = field(default_factory=dict)

    # 各标的 Beta 贡献：{symbol: beta_contribution}
    beta_contributions: dict[str, float] = field(default_factory=dict)

    # 时间
    computed_at: datetime = field(default_factory=datetime.now)

    @property
    def is_overleveraged(self) -> bool:
        """杠杆是否超过 1.0（多空对冲组合可能 > 1）。"""
        return self.leverage > 1.0
