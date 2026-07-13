"""
quant_os/engine/orchestrator.py

Orchestrator — 策略调度引擎（Phase 4 实现）。

调度链路（事件驱动）：
    Factor → Strategy → Portfolio → Execution → Risk → Feedback

职责：
  - 注册 / 管理触发规则（TriggerRule）
  - 监听上游事件，按规则触发下游链路
  - 记录每次触发的执行轨迹（TriggerRecord）
  - 维护策略调度记录（StrategyRecord）
  - 发布 EVENT_STRATEGY_TRIGGER 事件

❌ 不允许执行交易逻辑
❌ 不允许修改模块内部逻辑
❌ 只通过事件通信，不直接调用模块函数
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Callable

from ..model.strategy_model import (
    TriggerRule, TriggerRecord, StrategyRecord,
    TriggerType, TriggerStatus, FlowStage,
)
from ..event import EVENT_STRATEGY_TRIGGER, EVENT_LIFECYCLE_CHANGE, EVENT_SYSTEM_LOG

# 标准调度流水线顺序
_PIPELINE: list[FlowStage] = [
    FlowStage.FACTOR,
    FlowStage.STRATEGY,
    FlowStage.PORTFOLIO,
    FlowStage.EXECUTION,
    FlowStage.RISK,
    FlowStage.FEEDBACK,
]

# 每种触发类型对应的起始阶段
_TRIGGER_START: dict[TriggerType, FlowStage] = {
    TriggerType.FACTOR_UPDATE:   FlowStage.FACTOR,
    TriggerType.STRATEGY_CHANGE: FlowStage.STRATEGY,
    TriggerType.RISK_ALERT:      FlowStage.EXECUTION,
    TriggerType.SCHEDULE:        FlowStage.FACTOR,
    TriggerType.MANUAL:          FlowStage.FACTOR,
    TriggerType.FEEDBACK:        FlowStage.FEEDBACK,
}


class Orchestrator:
    """
    策略调度引擎（Phase 4）。

    使用方式：
        orch = Orchestrator(event_publish_fn)
        rule_id = orch.add_rule("因子更新触发", TriggerType.FACTOR_UPDATE,
                                source="FactorResearch",
                                targets=["StrategyEngine","PortfolioEngine"])
        orch.trigger(rule_id, payload={"factor": "momentum"})
    """

    def __init__(self, event_publish_fn: Callable) -> None:
        """
        Parameters
        ----------
        event_publish_fn : (event_type: str, data: dict) -> None
        """
        self._publish  = event_publish_fn
        self._rules:     dict[str, TriggerRule]   = {}
        self._records:   list[TriggerRecord]       = []   # 全局触发历史（最近500条）
        self._strategies: dict[str, StrategyRecord] = {}
        self._max_history = 500

        self._register_default_rules()

    # ------------------------------------------------------------------ #
    #  规则管理
    # ------------------------------------------------------------------ #

    def add_rule(
        self,
        name:          str,
        trigger_type:  TriggerType | str,
        *,
        rule_id:       str | None   = None,
        source_module: str          = "",
        target_modules: list[str]  | None = None,
        description:   str          = "",
        enabled:       bool         = True,
    ) -> str:
        """
        注册触发规则。

        Returns
        -------
        str  rule_id
        """
        if isinstance(trigger_type, str):
            trigger_type = TriggerType(trigger_type)

        rid = rule_id or str(uuid.uuid4())[:12]
        rule = TriggerRule(
            rule_id        = rid,
            name           = name,
            trigger_type   = trigger_type,
            source_module  = source_module,
            target_modules = target_modules or [],
            description    = description,
            enabled        = enabled,
        )
        self._rules[rid] = rule
        self._log(f"触发规则已注册：{name}（{trigger_type.value}）")
        return rid

    def enable_rule(self, rule_id: str) -> bool:
        rule = self._rules.get(rule_id)
        if rule is None:
            return False
        rule.enabled = True
        return True

    def disable_rule(self, rule_id: str) -> bool:
        rule = self._rules.get(rule_id)
        if rule is None:
            return False
        rule.enabled = False
        return True

    def get_rule(self, rule_id: str) -> TriggerRule | None:
        return self._rules.get(rule_id)

    def get_all_rules(self) -> list[TriggerRule]:
        return list(self._rules.values())

    # ------------------------------------------------------------------ #
    #  策略注册
    # ------------------------------------------------------------------ #

    def register_strategy(
        self,
        strategy_id:   str,
        strategy_name: str,
        alpha_id:      str = "",
    ) -> StrategyRecord:
        """将策略注册到调度系统。"""
        if strategy_id not in self._strategies:
            self._strategies[strategy_id] = StrategyRecord(
                strategy_id   = strategy_id,
                strategy_name = strategy_name,
                alpha_id      = alpha_id,
            )
            self._log(f"策略已注册到调度器：{strategy_name}（{strategy_id}）")
        return self._strategies[strategy_id]

    def schedule_strategy(self, strategy_id: str) -> bool:
        """启用策略的自动调度。"""
        rec = self._strategies.get(strategy_id)
        if rec is None:
            return False
        rec.is_scheduled = True
        self._log(f"策略调度已启用：{strategy_id}")
        return True

    def unschedule_strategy(self, strategy_id: str) -> bool:
        """禁用策略的自动调度。"""
        rec = self._strategies.get(strategy_id)
        if rec is None:
            return False
        rec.is_scheduled = False
        self._log(f"策略调度已禁用：{strategy_id}")
        return True

    # ------------------------------------------------------------------ #
    #  触发调度
    # ------------------------------------------------------------------ #

    def trigger(
        self,
        rule_id:     str,
        *,
        strategy_id: str | None = None,
        payload:     dict | None = None,
    ) -> TriggerRecord | None:
        """
        执行一次调度触发。

        Parameters
        ----------
        rule_id     : 规则 ID
        strategy_id : 可选，绑定到特定策略
        payload     : 上游传入的数据（只读传递，不修改）

        Returns
        -------
        TriggerRecord | None
        """
        rule = self._rules.get(rule_id)
        if rule is None or not rule.enabled:
            return None

        record = TriggerRecord(
            record_id    = str(uuid.uuid4())[:12],
            rule_id      = rule_id,
            trigger_type = rule.trigger_type,
            status       = TriggerStatus.RUNNING,
            payload      = payload or {},
        )

        # 确定起始阶段
        start_stage = _TRIGGER_START.get(rule.trigger_type, FlowStage.FACTOR)
        start_idx   = _PIPELINE.index(start_stage)

        try:
            for stage in _PIPELINE[start_idx:]:
                record.current_stage = stage
                self._execute_stage(stage, rule, record)
                record.stages_completed.append(stage)

            record.status       = TriggerStatus.COMPLETED
            record.completed_at = datetime.now()
            record.current_stage = FlowStage.IDLE

        except Exception as exc:
            record.status       = TriggerStatus.FAILED
            record.error_msg    = str(exc)
            record.completed_at = datetime.now()

        # 更新策略记录
        if strategy_id and strategy_id in self._strategies:
            self._strategies[strategy_id].add_trigger(record)
            self._strategies[strategy_id].current_stage = record.current_stage

        # 全局历史
        self._records.append(record)
        if len(self._records) > self._max_history:
            self._records.pop(0)

        # 发布事件
        self._publish(EVENT_STRATEGY_TRIGGER, {
            "record_id":    record.record_id,
            "rule_id":      rule_id,
            "rule_name":    rule.name,
            "trigger_type": rule.trigger_type.value,
            "status":       record.status.value,
            "stages":       [s.value for s in record.stages_completed],
            "elapsed_ms":   record.elapsed_ms,
            "error_msg":    record.error_msg,
        })

        return record

    def trigger_by_type(
        self,
        trigger_type: TriggerType | str,
        *,
        strategy_id: str | None = None,
        payload:     dict | None = None,
    ) -> list[TriggerRecord]:
        """触发所有匹配类型且已启用的规则。"""
        if isinstance(trigger_type, str):
            trigger_type = TriggerType(trigger_type)

        results = []
        for rule in self._rules.values():
            if rule.enabled and rule.trigger_type == trigger_type:
                rec = self.trigger(rule.rule_id,
                                   strategy_id=strategy_id,
                                   payload=payload)
                if rec is not None:
                    results.append(rec)
        return results

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_recent_records(self, limit: int = 100) -> list[TriggerRecord]:
        return self._records[-limit:]

    def get_strategy_record(self, strategy_id: str) -> StrategyRecord | None:
        return self._strategies.get(strategy_id)

    def get_all_strategy_records(self) -> list[StrategyRecord]:
        return list(self._strategies.values())

    def summary(self) -> dict:
        total     = len(self._records)
        completed = sum(1 for r in self._records if r.status == TriggerStatus.COMPLETED)
        failed    = sum(1 for r in self._records if r.status == TriggerStatus.FAILED)
        return {
            "rules":      len(self._rules),
            "strategies": len(self._strategies),
            "triggers": {
                "total":     total,
                "completed": completed,
                "failed":    failed,
                "success_rate": round(completed / total, 3) if total else 0.0,
            },
        }

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    @property
    def strategy_count(self) -> int:
        return len(self._strategies)

    @property
    def total_triggers(self) -> int:
        return len(self._records)

    # ------------------------------------------------------------------ #
    #  内部实现
    # ------------------------------------------------------------------ #

    def _execute_stage(
        self,
        stage:  FlowStage,
        rule:   TriggerRule,
        record: TriggerRecord,
    ) -> None:
        """
        执行单个流水线阶段。

        Phase 4 实现：仅发布阶段事件，不调用模块内部逻辑。
        Phase 5+ 可在此接入各模块的调度回调。
        """
        self._publish(EVENT_STRATEGY_TRIGGER, {
            "stage":        stage.value,
            "rule_id":      rule.rule_id,
            "rule_name":    rule.name,
            "trigger_type": rule.trigger_type.value,
            "record_id":    record.record_id,
            "targets":      rule.target_modules,
            "payload_keys": list(record.payload.keys()),
        })

    def _register_default_rules(self) -> None:
        """注册系统内置的默认调度规则。"""
        self.add_rule(
            name          = "因子更新 → 策略重算",
            trigger_type  = TriggerType.FACTOR_UPDATE,
            rule_id       = "builtin_factor_update",
            source_module = "FactorResearch",
            target_modules = ["StrategyEngine", "PortfolioEngine"],
            description   = "因子值更新后，触发策略信号重算和组合权重更新",
        )
        self.add_rule(
            name          = "策略变化 → 组合更新",
            trigger_type  = TriggerType.STRATEGY_CHANGE,
            rule_id       = "builtin_strategy_change",
            source_module = "StrategyEngine",
            target_modules = ["PortfolioEngine", "ExecutionEngine"],
            description   = "策略信号变化后，更新组合权重并触发执行",
        )
        self.add_rule(
            name          = "风控触发 → 调整执行",
            trigger_type  = TriggerType.RISK_ALERT,
            rule_id       = "builtin_risk_alert",
            source_module = "RiskEngine",
            target_modules = ["ExecutionEngine"],
            description   = "风控模块触发警报后，调整或暂停执行",
        )
        self.add_rule(
            name          = "执行反馈 → 状态更新",
            trigger_type  = TriggerType.FEEDBACK,
            rule_id       = "builtin_feedback",
            source_module = "ExecutionEngine",
            target_modules = ["StrategyEngine", "RiskEngine"],
            description   = "执行完成后，将成交结果反馈给策略和风控",
        )

    def _log(self, msg: str) -> None:
        self._publish(EVENT_SYSTEM_LOG, {"message": msg})
