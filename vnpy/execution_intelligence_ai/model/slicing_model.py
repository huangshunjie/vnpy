"""
execution_intelligence_ai/model/slicing_model.py  (Phase 2)

OrderSliceState  — 单个子切片状态
SlicePlan        — 完整拆单计划（父订单 → 切片列表）
SlicingParams    — 拆单参数（策略类型 + 超参数）
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import SliceStatus, ExecutionStrategy


@dataclass
class SlicingParams:
    """拆单参数。"""
    strategy:         ExecutionStrategy = ExecutionStrategy.TWAP
    n_slices:         int               = 10       # 目标切片数（TWAP/VWAP/Adaptive）
    interval_seconds: int               = 60       # 切片间隔（秒）
    pov_rate:         float             = 0.10     # POV 参与率 [0,1]
    vol_threshold:    float             = 0.015    # 波动率阈值（Adaptive）
    liq_threshold:    float             = 0.5      # 流动性阈值（Adaptive）
    min_slice_volume: float             = 1.0      # 最小单片量
    max_slice_volume: float             = 0.0      # 最大单片量（0=不限）
    # VWAP 历史成交量分布（按时段）
    volume_profile:   list[float]       = field(default_factory=list)
    # Adaptive 预估波动率序列
    volatility_seq:   list[float]       = field(default_factory=list)
    # Adaptive 预估流动性序列
    liquidity_seq:    list[float]       = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "strategy":         self.strategy.value,
            "n_slices":         self.n_slices,
            "interval_seconds": self.interval_seconds,
            "pov_rate":         self.pov_rate,
            "vol_threshold":    self.vol_threshold,
            "liq_threshold":    self.liq_threshold,
            "min_slice_volume": self.min_slice_volume,
            "max_slice_volume": self.max_slice_volume,
        }


@dataclass
class OrderSliceState:
    """单个切片子订单状态。"""
    slice_id:      str         = ""
    execution_id:  str         = ""
    sequence:      int         = 0
    symbol:        str         = ""
    exchange:      str         = ""
    direction:     str         = ""
    volume:        float       = 0.0
    filled_volume: float       = 0.0
    target_price:  float       = 0.0
    filled_price:  float       = 0.0
    slippage_bps:  float       = 0.0
    status:        SliceStatus = SliceStatus.PENDING
    scheduled_at:  datetime    = field(default_factory=datetime.now)
    submitted_at:  datetime | None = None
    filled_at:     datetime | None = None
    meta:          dict        = field(default_factory=dict)

    @property
    def fill_rate(self) -> float:
        if self.volume <= 0:
            return 0.0
        return round(min(self.filled_volume / self.volume, 1.0), 6)

    def to_dict(self) -> dict:
        return {
            "slice_id":      self.slice_id,
            "execution_id":  self.execution_id,
            "sequence":      self.sequence,
            "symbol":        self.symbol,
            "direction":     self.direction,
            "volume":        self.volume,
            "filled_volume": self.filled_volume,
            "fill_rate":     self.fill_rate,
            "target_price":  round(self.target_price, 4),
            "filled_price":  round(self.filled_price, 4),
            "slippage_bps":  round(self.slippage_bps, 4),
            "status":        self.status.value,
            "scheduled_at":  str(self.scheduled_at)[:19],
        }


@dataclass
class SlicePlan:
    """
    完整拆单计划：父订单 → 切片列表 + 元信息。
    由 SlicingEngine 生成，传递给路由/执行层。
    """
    execution_id:   str              = ""
    symbol:         str              = ""
    exchange:       str              = ""
    direction:      str              = ""
    total_volume:   float            = 0.0
    params:         SlicingParams    = field(default_factory=SlicingParams)
    slices:         list[OrderSliceState] = field(default_factory=list)
    created_at:     datetime         = field(default_factory=datetime.now)
    meta:           dict             = field(default_factory=dict)

    @property
    def n_slices(self) -> int:
        return len(self.slices)

    @property
    def total_planned_volume(self) -> float:
        return round(sum(s.volume for s in self.slices), 6)

    @property
    def total_filled_volume(self) -> float:
        return round(sum(s.filled_volume for s in self.slices), 6)

    @property
    def overall_fill_rate(self) -> float:
        if self.total_volume <= 0:
            return 0.0
        return round(self.total_filled_volume / self.total_volume, 6)

    @property
    def pending_slices(self) -> list[OrderSliceState]:
        return [s for s in self.slices if s.status == SliceStatus.PENDING]

    @property
    def filled_slices(self) -> list[OrderSliceState]:
        return [s for s in self.slices
                if s.status == SliceStatus.FILLED]

    def to_dict(self) -> dict:
        return {
            "execution_id":        self.execution_id,
            "symbol":              self.symbol,
            "exchange":            self.exchange,
            "direction":           self.direction,
            "total_volume":        self.total_volume,
            "n_slices":            self.n_slices,
            "total_planned":       self.total_planned_volume,
            "total_filled":        self.total_filled_volume,
            "overall_fill_rate":   self.overall_fill_rate,
            "strategy":            self.params.strategy.value,
            "created_at":          str(self.created_at)[:19],
            "slices":              [s.to_dict() for s in self.slices],
        }
