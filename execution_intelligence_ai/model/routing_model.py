"""
execution_intelligence_ai/model/routing_model.py  (Phase 4)

VenueProfile  — 交易场所/经纪商配置文件
RoutingState  — 单次路由决策状态
RoutingResult — 评分后的场所候选列表
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import RoutingMode


@dataclass
class VenueProfile:
    """
    交易场所/经纪商配置文件。

    代表一个可以接收子订单的执行场所（直连交易所 / 经纪商 / 暗池）。
    Phase 4 使用静态配置；Phase 5 可基于历史反馈动态更新。
    """
    venue_id:          str   = ""
    name:              str   = ""
    venue_type:        str   = "broker"   # "broker" | "exchange" | "darkpool"
    # 成本特征
    commission_bps:    float = 3.0        # 佣金（bp）
    avg_slippage_bps:  float = 5.0        # 历史平均滑点（bp）
    spread_bps:        float = 5.0        # 报价价差（bp）
    # 速度特征
    avg_latency_ms:    float = 10.0       # 平均延迟（毫秒）
    fill_rate:         float = 0.95       # 历史成交率 [0,1]
    # 可用性
    is_available:      bool  = True
    max_order_size:    float = 0.0        # 0 = 不限
    min_order_size:    float = 1.0
    # 暗池特有：最小规模阈值（低于此不路由至暗池）
    darkpool_min_size: float = 0.0

    def total_cost_bps(self) -> float:
        """综合执行成本 = 佣金 + 平均滑点 + 价差/2"""
        return round(self.commission_bps
                     + self.avg_slippage_bps
                     + self.spread_bps / 2, 4)

    def to_dict(self) -> dict:
        return {
            "venue_id":         self.venue_id,
            "name":             self.name,
            "venue_type":       self.venue_type,
            "commission_bps":   self.commission_bps,
            "avg_slippage_bps": self.avg_slippage_bps,
            "spread_bps":       self.spread_bps,
            "avg_latency_ms":   self.avg_latency_ms,
            "fill_rate":        self.fill_rate,
            "is_available":     self.is_available,
            "total_cost_bps":   self.total_cost_bps(),
        }


@dataclass
class VenueScore:
    """单个场所的评分结果。"""
    venue_id:   str   = ""
    score:      float = 0.0      # [0, 1]，越高越优
    cost_bps:   float = 0.0
    latency_ms: float = 0.0
    fill_rate:  float = 0.0
    reason:     str   = ""

    def to_dict(self) -> dict:
        return {
            "venue_id":   self.venue_id,
            "score":      round(self.score,      4),
            "cost_bps":   round(self.cost_bps,   4),
            "latency_ms": round(self.latency_ms, 2),
            "fill_rate":  round(self.fill_rate,  4),
            "reason":     self.reason,
        }


@dataclass
class RoutingState:
    """单次路由决策完整状态。"""
    execution_id:       str         = ""
    slice_id:           str         = ""
    symbol:             str         = ""
    routing_mode:       RoutingMode = RoutingMode.BALANCED
    # 候选场所及评分
    candidates:         list[VenueScore] = field(default_factory=list)
    # 选定场所
    selected_venue_id:  str         = ""
    selected_venue_name: str        = ""
    expected_cost_bps:  float       = 0.0
    expected_latency_ms: float      = 0.0
    # 实现值（成交后回填）
    realized_cost_bps:  float       = 0.0
    realized_latency_ms: float      = 0.0
    decided_at:         datetime    = field(default_factory=datetime.now)
    meta:               dict        = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "execution_id":        self.execution_id,
            "slice_id":            self.slice_id,
            "symbol":              self.symbol,
            "routing_mode":        self.routing_mode.value,
            "selected_venue_id":   self.selected_venue_id,
            "selected_venue_name": self.selected_venue_name,
            "expected_cost_bps":   round(self.expected_cost_bps,    4),
            "expected_latency_ms": round(self.expected_latency_ms,  2),
            "realized_cost_bps":   round(self.realized_cost_bps,    4),
            "realized_latency_ms": round(self.realized_latency_ms,  2),
            "n_candidates":        len(self.candidates),
            "decided_at":          str(self.decided_at)[:19],
            "candidates":          [c.to_dict() for c in self.candidates],
        }
