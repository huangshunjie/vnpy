"""
research_validation/model/validation_model.py

验证任务参数与任务对象数据结构（Phase 1 骨架）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ValidationParams:
    """
    验证任务参数。

    Phase 2+ 各引擎从此对象读取配置，UI 构造后传给 run_validation()。
    """
    # 因子标识
    factor_name:    str = ""
    factor_source:  str = ""   # "factor_research" | "database" | "custom"

    # 时间范围
    start_date:  datetime = field(default_factory=datetime.now)
    end_date:    datetime = field(default_factory=datetime.now)

    # Walk Forward 参数（Phase 2）
    train_window: int = 252   # 训练窗口（日历天）
    test_window:  int = 63    # 测试窗口（日历天）
    step_size:    int = 21    # 每次滚动步长（日历天）

    # OOS 参数（Phase 2）
    oos_ratio:    float = 0.3   # 样本外比例

    # Regime 参数（Phase 3）
    regime_lookback: int = 60

    # Stability 参数（Phase 4）
    stability_window: int = 60

    # 启用模块开关
    run_walkforward: bool = True
    run_oos:         bool = True
    run_regime:      bool = True
    run_stability:   bool = True
    run_bias:        bool = True


@dataclass
class ValidationTask:
    """
    验证任务对象（运行时状态追踪）。
    """
    task_id:     str              = ""
    params:      ValidationParams = field(default_factory=ValidationParams)
    created_at:  datetime         = field(default_factory=datetime.now)
    started_at:  datetime | None  = None
    finished_at: datetime | None  = None
    progress:    float            = 0.0    # 0.0 ~ 1.0
    message:     str              = ""

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
