"""
research_validation/model/result_model.py

验证结果数据结构（Phase 1 骨架）。

Phase 2+ 各引擎计算完成后填充对应 Result 对象。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..constant import ValidationStatus, RegimeType, StabilityLevel


@dataclass
class WalkForwardResult:
    """Walk Forward Analysis 单窗口结果（Phase 2）。"""
    window_idx:   int      = 0
    train_start:  datetime = field(default_factory=datetime.now)
    train_end:    datetime = field(default_factory=datetime.now)
    test_start:   datetime = field(default_factory=datetime.now)
    test_end:     datetime = field(default_factory=datetime.now)
    train_ic:     float    = 0.0
    test_ic:      float    = 0.0
    train_sharpe: float    = 0.0
    test_sharpe:  float    = 0.0

    @property
    def ic_decay(self) -> float:
        """IC 从样本内到样本外的衰减比例。"""
        if abs(self.train_ic) < 1e-9:
            return 0.0
        return (self.train_ic - self.test_ic) / abs(self.train_ic)


@dataclass
class OOSResult:
    """Out-of-Sample 测试结果（Phase 2）。"""
    is_ic:      float = 0.0   # 样本内 IC
    oos_ic:     float = 0.0   # 样本外 IC
    is_sharpe:  float = 0.0
    oos_sharpe: float = 0.0
    is_period:  tuple[datetime, datetime] | None = None
    oos_period: tuple[datetime, datetime] | None = None

    @property
    def overfit_ratio(self) -> float:
        """过拟合比率：>1 表示样本内显著好于样本外。"""
        if abs(self.oos_ic) < 1e-9:
            return float("inf")
        return self.is_ic / self.oos_ic


@dataclass
class RegimeResult:
    """市场状态因子表现结果（Phase 3）。"""
    regime:     RegimeType = RegimeType.UNKNOWN
    ic_mean:    float      = 0.0
    ic_std:     float      = 0.0
    ic_ir:      float      = 0.0    # IC / IC_std
    sample_count: int      = 0


@dataclass
class StabilityResult:
    """因子稳定性分析结果（Phase 4）。"""
    rolling_ic:      list[float] = field(default_factory=list)
    rolling_sharpe:  list[float] = field(default_factory=list)
    rolling_dates:   list[datetime] = field(default_factory=list)
    ic_stability:    StabilityLevel = StabilityLevel.INVALID
    decay_halflife:  float = 0.0   # IC 衰减半衰期（日）


@dataclass
class BiasWarning:
    """单条偏差检测警告（Phase 5）。"""
    bias_type:   str   = ""
    severity:    str   = "warning"   # "warning" | "critical"
    description: str   = ""
    detail:      str   = ""


@dataclass
class ValidationResult:
    """
    完整验证结果汇总。

    由 ValidationEngine 在所有子引擎完成后填充并发布。
    """
    task_id:     str              = ""
    factor_name: str              = ""
    status:      ValidationStatus = ValidationStatus.IDLE
    computed_at: datetime         = field(default_factory=datetime.now)

    # 子模块结果（Phase 2+）
    walkforward_results: list[WalkForwardResult] = field(default_factory=list)
    oos_result:          OOSResult | None         = None
    regime_summary:      object | None            = None   # RegimeSummary (Phase 3)
    stability_summary:   object | None            = None   # StabilitySummary (Phase 4)
    bias_summary:        object | None            = None   # BiasSummary (Phase 5)

    # 综合评分（Phase 2+）
    overall_score:    float = 0.0   # 0 ~ 100，越高越可信
    is_real_alpha:    bool  = False  # 最终判断

    @property
    def has_warnings(self) -> bool:
        return len(self.bias_warnings) > 0

    @property
    def critical_warnings(self) -> list[BiasWarning]:
        return [w for w in self.bias_warnings if w.severity == "critical"]
