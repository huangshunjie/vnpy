"""
execution_intelligence_ai/model/feedback_model.py  (Phase 5)

FeedbackState   — 单次执行的质量反馈汇总
ExecutionReport — 完整执行报告（含所有切片 + 指标）
FeedbackMetrics — 计算指标集合
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import FeedbackMetric


@dataclass
class SliceFeedback:
    """单个切片的成交反馈。"""
    slice_id:           str     = ""
    sequence:           int     = 0
    planned_volume:     float   = 0.0
    filled_volume:      float   = 0.0
    planned_price:      float   = 0.0
    filled_price:       float   = 0.0
    slippage_bps:       float   = 0.0
    latency_ms:         float   = 0.0
    venue_id:           str     = ""
    fill_rate:          float   = 0.0
    submitted_at:       datetime | None = None
    filled_at:          datetime | None = None

    def to_dict(self) -> dict:
        return {
            "slice_id":       self.slice_id,
            "sequence":       self.sequence,
            "planned_volume": self.planned_volume,
            "filled_volume":  self.filled_volume,
            "fill_rate":      round(self.fill_rate,    4),
            "slippage_bps":   round(self.slippage_bps, 4),
            "latency_ms":     round(self.latency_ms,   2),
            "venue_id":       self.venue_id,
        }


@dataclass
class FeedbackState:
    """单次执行任务的质量反馈汇总（Phase 5 完整版）。"""
    execution_id:       str     = ""
    symbol:             str     = ""
    direction:          str     = ""
    total_volume:       float   = 0.0

    # 成交汇总
    filled_volume:      float   = 0.0
    fill_rate:          float   = 0.0

    # 成本指标
    slippage_bps:       float   = 0.0    # 加权平均滑点
    commission_bps:     float   = 0.0    # 佣金
    market_impact_bps:  float   = 0.0    # 实现市场冲击
    total_cost_bps:     float   = 0.0    # 滑点 + 佣金 + 冲击

    # VWAP 基准偏差
    vwap_deviation_bps: float   = 0.0

    # 时间指标
    avg_latency_ms:     float   = 0.0
    execution_duration_s: float = 0.0

    # 切片统计
    n_slices:           int     = 0
    n_filled:           int     = 0
    n_partial:          int     = 0
    n_cancelled:        int     = 0

    # 质量评分 [0,100]
    quality_score:      float   = 0.0

    started_at:         datetime | None = None
    completed_at:       datetime | None = None
    slice_feedbacks:    list[SliceFeedback] = field(default_factory=list)
    meta:               dict    = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "execution_id":         self.execution_id,
            "symbol":               self.symbol,
            "direction":            self.direction,
            "total_volume":         self.total_volume,
            "filled_volume":        self.filled_volume,
            "fill_rate":            round(self.fill_rate,            4),
            "slippage_bps":         round(self.slippage_bps,         4),
            "commission_bps":       round(self.commission_bps,       4),
            "market_impact_bps":    round(self.market_impact_bps,    4),
            "total_cost_bps":       round(self.total_cost_bps,       4),
            "vwap_deviation_bps":   round(self.vwap_deviation_bps,   4),
            "avg_latency_ms":       round(self.avg_latency_ms,       2),
            "execution_duration_s": round(self.execution_duration_s, 2),
            "n_slices":             self.n_slices,
            "n_filled":             self.n_filled,
            "quality_score":        round(self.quality_score,        2),
            "started_at":           str(self.started_at)[:19] if self.started_at else "",
            "completed_at":         str(self.completed_at)[:19] if self.completed_at else "",
        }


@dataclass
class ExecutionReport:
    """
    完整执行报告：父订单维度。
    由 FeedbackEngine 在任务完成后生成。
    """
    execution_id:    str           = ""
    symbol:          str           = ""
    direction:       str           = ""
    strategy:        str           = ""
    total_volume:    float         = 0.0
    feedback:        FeedbackState = field(default_factory=FeedbackState)
    generated_at:    datetime      = field(default_factory=datetime.now)
    # 闭环建议
    recommendations: list[str]     = field(default_factory=list)
    next_params:     dict          = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "execution_id":  self.execution_id,
            "symbol":        self.symbol,
            "direction":     self.direction,
            "strategy":      self.strategy,
            "total_volume":  self.total_volume,
            "feedback":      self.feedback.to_dict(),
            "recommendations": self.recommendations,
            "next_params":   self.next_params,
            "generated_at":  str(self.generated_at)[:19],
        }
