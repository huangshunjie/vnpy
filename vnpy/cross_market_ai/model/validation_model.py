"""
cross_market_ai/model/validation_model.py

Phase 5: 跨市场验证数据模型 — 完整字段定义。

核心概念：Train on Market_A, Test on Market_B, measure degradation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PerformanceSnapshot:
    """单市场性能快照（用于训练/测试对比）。"""
    market_id:    str   = ""
    sharpe:       float = 0.0
    ic_mean:      float = 0.0
    ic_std:       float = 0.0
    max_drawdown: float = 0.0
    win_rate:     float = 0.0
    n_samples:    int   = 0
    source:       str   = "prior"

    def to_dict(self) -> dict:
        return {
            "market_id":    self.market_id,
            "sharpe":       round(self.sharpe,       4),
            "ic_mean":      round(self.ic_mean,      5),
            "ic_std":       round(self.ic_std,       5),
            "max_drawdown": round(self.max_drawdown, 4),
            "win_rate":     round(self.win_rate,     4),
            "n_samples":    self.n_samples,
            "source":       self.source,
        }


@dataclass
class DegradationMetrics:
    """性能衰减度量。"""
    sharpe_decay:       float = 0.0   # (sharpe_train - sharpe_test) / |sharpe_train|
    ic_decay:           float = 0.0   # (ic_train - ic_test) / |ic_train|
    drawdown_ratio:     float = 1.0   # max_dd_test / max_dd_train
    win_rate_delta:     float = 0.0   # win_rate_train - win_rate_test
    composite_decay:    float = 0.0   # 加权综合衰减率 ∈ [0,1]

    def to_dict(self) -> dict:
        return {
            "sharpe_decay":    round(self.sharpe_decay,    4),
            "ic_decay":        round(self.ic_decay,        4),
            "drawdown_ratio":  round(self.drawdown_ratio,  4),
            "win_rate_delta":  round(self.win_rate_delta,  4),
            "composite_decay": round(self.composite_decay, 4),
        }


@dataclass
class StructuralCompatibility:
    """结构兼容性评估（整合 Phase 2/3 结果）。"""
    structural_similarity:   float = 0.0
    regime_alignment_score:  float = 0.0
    transfer_coefficient:    float = 0.0
    portability_prior:       float = 0.0
    compatibility_score:     float = 0.0  # 综合兼容性 ∈ [0,1]

    def to_dict(self) -> dict:
        return {
            "structural_similarity":  round(self.structural_similarity,  4),
            "regime_alignment_score": round(self.regime_alignment_score, 4),
            "transfer_coefficient":   round(self.transfer_coefficient,   4),
            "portability_prior":      round(self.portability_prior,      4),
            "compatibility_score":    round(self.compatibility_score,    4),
        }


@dataclass
class ValidationRecord:
    """
    单次跨市场验证完整记录。

    验证逻辑：
      1. 获取 Alpha 在 market_train 和 market_test 上的性能快照
      2. 计算性能衰减指标
      3. 整合 Phase 2/3 的结构兼容性
      4. 给出验证结论（PASS / DEGRADED / FAIL）
    """
    alpha_id:      str = ""
    market_train:  str = ""
    market_test:   str = ""

    # 性能快照
    perf_train:    PerformanceSnapshot = field(default_factory=PerformanceSnapshot)
    perf_test:     PerformanceSnapshot = field(default_factory=PerformanceSnapshot)

    # 衰减指标
    degradation:   DegradationMetrics = field(default_factory=DegradationMetrics)

    # 结构兼容性（Phase 2/3 成果复用）
    compatibility: StructuralCompatibility = field(
        default_factory=StructuralCompatibility
    )

    # 验证结论
    passed:              bool  = False
    verdict:             str   = ""    # PASS / DEGRADED / FAIL
    verdict_detail:      str   = ""
    decay_threshold:     float = 0.50  # 衰减率超过此值视为 FAIL
    degrade_threshold:   float = 0.30  # 衰减率超过此值视为 DEGRADED

    # 预测与实际对比
    predicted_decay:     float = 0.0   # Phase 3 预测的 IC 衰减率
    actual_decay:        float = 0.0   # Phase 5 实测综合衰减率
    prediction_error:    float = 0.0   # |predicted - actual|

    status:       str = "computed"
    validated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "alpha_id":          self.alpha_id,
            "market_train":      self.market_train,
            "market_test":       self.market_test,
            "perf_train":        self.perf_train.to_dict(),
            "perf_test":         self.perf_test.to_dict(),
            "degradation":       self.degradation.to_dict(),
            "compatibility":     self.compatibility.to_dict(),
            "passed":            self.passed,
            "verdict":           self.verdict,
            "verdict_detail":    self.verdict_detail,
            "decay_threshold":   self.decay_threshold,
            "degrade_threshold": self.degrade_threshold,
            "predicted_decay":   round(self.predicted_decay,  4),
            "actual_decay":      round(self.actual_decay,     4),
            "prediction_error":  round(self.prediction_error, 4),
            "status":            self.status,
            "validated_at":      self.validated_at,
        }


@dataclass
class ValidationState:
    """跨市场验证引擎运行状态。"""
    total_validations: int   = 0
    passed:            int   = 0
    degraded:          int   = 0
    failed:            int   = 0
    avg_decay_rate:    float = 0.0
    avg_prediction_error: float = 0.0
    last_alpha_id:     str   = ""
    last_pair:         str   = ""
    status:            str   = "idle"

    def to_dict(self) -> dict:
        return {
            "total_validations":    self.total_validations,
            "passed":               self.passed,
            "degraded":             self.degraded,
            "failed":               self.failed,
            "avg_decay_rate":       round(self.avg_decay_rate,       4),
            "avg_prediction_error": round(self.avg_prediction_error, 4),
            "last_alpha_id":        self.last_alpha_id,
            "last_pair":            self.last_pair,
            "status":               self.status,
        }
