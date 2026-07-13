"""
quant_os/model/strategy_model.py

StrategyRecord / TriggerRule — 策略调度数据模型（Phase 4）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TriggerType(str, Enum):
    """调度触发类型。"""
    FACTOR_UPDATE    = "factor_update"     # 因子更新 → 触发策略重算
    STRATEGY_CHANGE  = "strategy_change"   # 策略变化 → 更新 Portfolio
    RISK_ALERT       = "risk_alert"        # 风控触发 → 调整 Execution
    SCHEDULE         = "schedule"          # 定时触发（开盘/收盘/周期）
    MANUAL           = "manual"            # 手动触发
    FEEDBACK         = "feedback"          # 执行反馈 → 更新状态


class FlowStage(str, Enum):
    """调度流水线阶段。"""
    FACTOR    = "factor"
    STRATEGY  = "strategy"
    PORTFOLIO = "portfolio"
    EXECUTION = "execution"
    RISK      = "risk"
    FEEDBACK  = "feedback"
    IDLE      = "idle"


class TriggerStatus(str, Enum):
    """触发记录状态。"""
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"


@dataclass
class TriggerRule:
    """
    调度触发规则。

    定义在什么条件下触发哪条调度链路。
    """
    rule_id:      str         = ""
    name:         str         = ""
    trigger_type: TriggerType = TriggerType.MANUAL

    # 触发条件（Phase 4 保留扩展，暂为描述性字段）
    source_module:  str = ""   # 触发来源模块（如 "FactorResearch"）
    target_modules: list[str] = field(default_factory=list)  # 目标模块链路

    # 启用/禁用
    enabled: bool = True

    # 描述
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "rule_id":       self.rule_id,
            "name":          self.name,
            "trigger_type":  self.trigger_type.value,
            "source":        self.source_module,
            "targets":       self.target_modules,
            "enabled":       self.enabled,
            "description":   self.description,
        }


@dataclass
class TriggerRecord:
    """单次触发的执行记录。"""
    record_id:    str           = ""
    rule_id:      str           = ""
    trigger_type: TriggerType   = TriggerType.MANUAL
    status:       TriggerStatus = TriggerStatus.PENDING

    triggered_at:  datetime        = field(default_factory=datetime.now)
    completed_at:  datetime | None = None

    # 流水线执行轨迹
    stages_completed: list[FlowStage] = field(default_factory=list)
    current_stage:    FlowStage       = FlowStage.IDLE

    # 结果 / 错误
    payload:   dict = field(default_factory=dict)
    error_msg: str  = ""

    @property
    def elapsed_ms(self) -> float:
        end = self.completed_at or datetime.now()
        return (end - self.triggered_at).total_seconds() * 1000

    def to_dict(self) -> dict:
        return {
            "record_id":        self.record_id,
            "rule_id":          self.rule_id,
            "trigger_type":     self.trigger_type.value,
            "status":           self.status.value,
            "triggered_at":     str(self.triggered_at)[:19],
            "completed_at":     str(self.completed_at)[:19] if self.completed_at else "—",
            "elapsed_ms":       round(self.elapsed_ms, 1),
            "current_stage":    self.current_stage.value,
            "stages_completed": [s.value for s in self.stages_completed],
            "error_msg":        self.error_msg,
        }


@dataclass
class StrategyRecord:
    """
    策略调度记录 — 记录一条策略的调度状态与触发历史。
    """
    strategy_id:   str  = ""
    strategy_name: str  = ""
    alpha_id:      str  = ""

    # 当前调度状态
    is_scheduled:  bool = False
    current_stage: FlowStage = FlowStage.IDLE

    # 触发历史（最近 N 条）
    trigger_history: list[TriggerRecord] = field(default_factory=list)

    # 统计
    total_triggers:     int = 0
    successful_triggers: int = 0
    failed_triggers:    int = 0

    last_triggered_at:  datetime | None = None

    @property
    def success_rate(self) -> float:
        if self.total_triggers == 0:
            return 0.0
        return self.successful_triggers / self.total_triggers

    def add_trigger(self, record: TriggerRecord) -> None:
        self.trigger_history.append(record)
        if len(self.trigger_history) > 50:
            self.trigger_history.pop(0)
        self.total_triggers += 1
        self.last_triggered_at = record.triggered_at
        if record.status == TriggerStatus.COMPLETED:
            self.successful_triggers += 1
        elif record.status == TriggerStatus.FAILED:
            self.failed_triggers += 1

    def to_dict(self) -> dict:
        return {
            "strategy_id":       self.strategy_id,
            "strategy_name":     self.strategy_name,
            "alpha_id":          self.alpha_id,
            "is_scheduled":      self.is_scheduled,
            "current_stage":     self.current_stage.value,
            "total_triggers":    self.total_triggers,
            "success_rate":      round(self.success_rate, 3),
            "last_triggered_at": str(self.last_triggered_at)[:19]
                                  if self.last_triggered_at else "—",
        }
