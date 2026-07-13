"""
cross_market_ai/model/alpha_model.py

Phase 3: Alpha 迁移数据模型 — 完整字段定义。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AlphaTransferRecord:
    """单次 Alpha 迁移计算结果。"""
    alpha_id:    str = ""
    market_src:  str = ""
    market_dst:  str = ""

    # 迁移条件评分（Phase 3 核心）
    correlation_stability:   float = 0.0   # 相关性稳定性 ∈ [0,1]
    regime_invariance:       float = 0.0   # Regime 不变性 ∈ [0,1]
    volatility_sensitivity:  float = 0.0   # 波动率敏感度（低=好）∈ [0,1]
    liquidity_sensitivity:   float = 0.0   # 流动性敏感度（低=好）∈ [0,1]

    # 迁移系数 T(Alpha_A, Market_A → Market_B)
    transfer_coefficient:    float = 0.0   # ∈ [0,1]

    # 调整参数（应用迁移系数后的 Alpha 参数缩放）
    vol_scale:               float = 1.0   # 波动率缩放比例
    liq_scale:               float = 1.0   # 流动性缩放比例
    signal_decay_adjusted:   int   = 0     # 调整后的信号衰减周期（天）

    # 预期性能
    expected_ic_src:         float = 0.0
    expected_ic_dst:         float = 0.0
    expected_ic_decay:       float = 0.0   # IC 衰减率 = (src-dst)/src
    expected_sharpe_dst:     float = 0.0

    # 迁移结论
    is_transferable:         bool  = False
    rejection_reason:        str   = ""
    confidence:              str   = ""    # HIGH / MODERATE / LOW / REJECT
    status:                  str   = "computed"
    transferred_at:          str   = ""

    def to_dict(self) -> dict:
        return {
            "alpha_id":               self.alpha_id,
            "market_src":             self.market_src,
            "market_dst":             self.market_dst,
            "correlation_stability":  self.correlation_stability,
            "regime_invariance":      self.regime_invariance,
            "volatility_sensitivity": self.volatility_sensitivity,
            "liquidity_sensitivity":  self.liquidity_sensitivity,
            "transfer_coefficient":   self.transfer_coefficient,
            "vol_scale":              self.vol_scale,
            "liq_scale":              self.liq_scale,
            "signal_decay_adjusted":  self.signal_decay_adjusted,
            "expected_ic_src":        self.expected_ic_src,
            "expected_ic_dst":        self.expected_ic_dst,
            "expected_ic_decay":      self.expected_ic_decay,
            "expected_sharpe_dst":    self.expected_sharpe_dst,
            "is_transferable":        self.is_transferable,
            "rejection_reason":       self.rejection_reason,
            "confidence":             self.confidence,
            "status":                 self.status,
            "transferred_at":         self.transferred_at,
        }


@dataclass
class AlphaTransferState:
    """Alpha 迁移引擎运行状态。"""
    total_transfers: int   = 0
    successful:      int   = 0
    rejected:        int   = 0
    avg_coefficient: float = 0.0
    last_alpha_id:   str   = ""
    last_pair:       str   = ""
    status:          str   = "idle"

    def to_dict(self) -> dict:
        return {
            "total_transfers": self.total_transfers,
            "successful":      self.successful,
            "rejected":        self.rejected,
            "avg_coefficient": round(self.avg_coefficient, 4),
            "last_alpha_id":   self.last_alpha_id,
            "last_pair":       self.last_pair,
            "status":          self.status,
        }
