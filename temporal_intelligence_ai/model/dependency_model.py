"""
temporal_intelligence_ai/model/dependency_model.py

时间依赖数据模型。

LagCorrelation      — 单个滞后阶的相关性结果
AutoCorrResult      — 单信号自相关分析结果
CrossCorrResult     — 双信号互相关分析结果
DependencyMatrix    — 多信号时间依赖矩阵
DependencyState     — 完整时间依赖快照（由 DependencyEngine 输出）
DependencyHistory   — 历史依赖快照序列
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from ..constant import SignalHorizon


@dataclass
class LagCorrelation:
    """单个滞后阶的相关性。"""
    lag:         int   = 0
    correlation: float = 0.0
    is_significant: bool = False   # |r| > significance_threshold


@dataclass
class AutoCorrResult:
    """
    单信号自相关分析结果。

    分析 Signal(t) 与 Signal(t-k) 的线性依赖强度，
    识别信号自身的时间记忆结构。
    """
    signal_id:  str                    = ""
    horizon:    SignalHorizon          = SignalHorizon.SHORT_TERM
    lags:       List[LagCorrelation]   = field(default_factory=list)
    max_lag:    int                    = 0
    peak_lag:   int                    = 0       # 最大绝对相关所在滞后阶
    peak_corr:  float                  = 0.0     # 最大绝对相关值
    memory_score: float                = 0.0     # 综合记忆强度 [0, 1]

    def to_dict(self) -> dict:
        return {
            "signal_id":    self.signal_id,
            "horizon":      self.horizon.value,
            "max_lag":      self.max_lag,
            "peak_lag":     self.peak_lag,
            "peak_corr":    round(self.peak_corr, 4),
            "memory_score": round(self.memory_score, 4),
            "lags": [
                {"lag": lc.lag, "corr": round(lc.correlation, 4),
                 "sig": lc.is_significant}
                for lc in self.lags
            ],
        }


@dataclass
class CrossCorrResult:
    """
    双信号互相关分析结果。

    分析 Signal_A(t) 与 Signal_B(t-k) 的依赖关系，
    识别信号间的领先/滞后结构。
    """
    signal_a:   str                    = ""
    signal_b:   str                    = ""
    lags:       List[LagCorrelation]   = field(default_factory=list)
    lead_lag:   int                    = 0    # 正值：A 领先 B；负值：B 领先 A
    peak_corr:  float                  = 0.0
    dependency_strength: float         = 0.0  # 综合依赖强度 [0, 1]

    def to_dict(self) -> dict:
        return {
            "signal_a":           self.signal_a,
            "signal_b":           self.signal_b,
            "lead_lag":           self.lead_lag,
            "peak_corr":          round(self.peak_corr, 4),
            "dependency_strength": round(self.dependency_strength, 4),
        }


@dataclass
class DependencyMatrix:
    """
    多信号时间依赖矩阵。

    存储所有信号对之间的互相关强度，用于热力图可视化。
    """
    signal_ids: List[str]                        = field(default_factory=list)
    matrix:     Dict[str, Dict[str, float]]      = field(default_factory=dict)

    def set(self, a: str, b: str, value: float) -> None:
        self.matrix.setdefault(a, {})[b] = value
        self.matrix.setdefault(b, {})[a] = value

    def get(self, a: str, b: str) -> float:
        return self.matrix.get(a, {}).get(b, 0.0)

    def to_flat_list(self) -> List[dict]:
        result = []
        seen   = set()
        for a in self.signal_ids:
            for b in self.signal_ids:
                key = tuple(sorted([a, b]))
                if key not in seen and a != b:
                    result.append({
                        "a": a, "b": b,
                        "value": round(self.get(a, b), 4)
                    })
                    seen.add(key)
        return result


@dataclass
class HorizonDecomposition:
    """三时间维度分解：短/中/长期信号贡献度。"""
    short_term_weight: float = 0.0   # t-1 ~ t-5 贡献度
    mid_term_weight:   float = 0.0   # t-5 ~ t-20 贡献度
    long_term_weight:  float = 0.0   # t-20+ 贡献度
    dominant_horizon:  SignalHorizon = SignalHorizon.SHORT_TERM

    def to_dict(self) -> dict:
        return {
            "short_term":       round(self.short_term_weight, 4),
            "mid_term":         round(self.mid_term_weight, 4),
            "long_term":        round(self.long_term_weight, 4),
            "dominant_horizon": self.dominant_horizon.value,
        }


@dataclass
class DependencyState:
    """
    完整时间依赖快照。

    由 DependencyEngine.analyze() 生成，
    通过 EVENT_TEMPORAL_ANALYSIS_COMPLETED 附带派发。
    """
    timestamp:         datetime               = field(default_factory=datetime.now)
    signal_ids:        List[str]              = field(default_factory=list)
    autocorr_results:  Dict[str, AutoCorrResult]  = field(default_factory=dict)
    crosscorr_results: List[CrossCorrResult]  = field(default_factory=list)
    dep_matrix:        DependencyMatrix       = field(default_factory=DependencyMatrix)
    horizon_decomp:    HorizonDecomposition   = field(default_factory=HorizonDecomposition)
    overall_memory:    float                  = 0.0   # 系统整体记忆强度 [0, 1]

    def to_dict(self) -> dict:
        return {
            "timestamp":      self.timestamp.isoformat(),
            "signal_count":   len(self.signal_ids),
            "overall_memory": round(self.overall_memory, 4),
            "horizon":        self.horizon_decomp.to_dict(),
            "autocorr": {
                sid: r.to_dict()
                for sid, r in self.autocorr_results.items()
            },
            "crosscorr": [r.to_dict() for r in self.crosscorr_results],
            "matrix":    self.dep_matrix.to_flat_list(),
        }


@dataclass
class DependencyHistory:
    """历史依赖快照序列。"""
    max_size: int                    = 200
    records:  List[DependencyState] = field(default_factory=list)

    def append(self, state: DependencyState) -> None:
        self.records.append(state)
        if len(self.records) > self.max_size:
            self.records = self.records[-self.max_size:]

    def last(self) -> Optional[DependencyState]:
        return self.records[-1] if self.records else None

    def memory_scores(self) -> List[float]:
        return [r.overall_memory for r in self.records]
