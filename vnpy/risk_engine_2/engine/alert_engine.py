"""
risk_engine_2/engine/alert_engine.py

AlertEngine — 预警规则 + 触发机制（Phase 3）。

职责：
  - 持有预警规则集合（AlertRule）
  - 每次风险状态更新后检查所有规则
  - 触发时生成 AlertRecord，返回给 RiskCoreEngine 发布事件
  - 支持冷却时间（同一规则短时间内不重复告警）
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..constant import AlertType, RiskLevel, RiskAction
from ..model.drawdown_model import AlertRecord, DrawdownState
from ..model.exposure_model import ExposureReport


@dataclass
class AlertRule:
    """单条预警规则。"""
    rule_id:    str        = ""
    alert_type: AlertType  = AlertType.DRAWDOWN_BREACH
    threshold:  float      = 0.0          # 触发阈值
    risk_level: RiskLevel  = RiskLevel.WARNING
    action:     RiskAction = RiskAction.ALERT
    enabled:    bool       = True
    cooldown_s: int        = 60            # 冷却时间（秒），0 = 不限制
    description: str       = ""

    # 内部：上次触发时间
    _last_triggered: datetime | None = field(default=None, repr=False)

    def can_trigger(self) -> bool:
        """是否已过冷却时间。"""
        if not self.enabled:
            return False
        if self._last_triggered is None:
            return True
        if self.cooldown_s <= 0:
            return True
        return (datetime.now() - self._last_triggered).total_seconds() >= self.cooldown_s

    def mark_triggered(self) -> None:
        self._last_triggered = datetime.now()


class AlertEngine:
    """
    预警引擎（Phase 3）。

    使用方式：
        engine = AlertEngine()
        alerts = engine.check_drawdown(drawdown_state)
        alerts += engine.check_exposure(exposure_report)
        for alert in alerts:
            # 发布 EVENT_RISK_ALERT
    """

    def __init__(self) -> None:
        self._rules:   dict[str, AlertRule] = {}
        self._history: list[AlertRecord]    = []
        self._load_defaults()

    # ------------------------------------------------------------------ #
    #  默认规则
    # ------------------------------------------------------------------ #

    def _load_defaults(self) -> None:
        defaults = [
            AlertRule(
                rule_id    = "drawdown_warning",
                alert_type = AlertType.DRAWDOWN_BREACH,
                threshold  = 0.05,
                risk_level = RiskLevel.WARNING,
                action     = RiskAction.ALERT,
                cooldown_s = 120,
                description= "回撤预警 5%",
            ),
            AlertRule(
                rule_id    = "drawdown_critical",
                alert_type = AlertType.DRAWDOWN_BREACH,
                threshold  = 0.10,
                risk_level = RiskLevel.CRITICAL,
                action     = RiskAction.REDUCE_POSITION,
                cooldown_s = 300,
                description= "回撤硬限制 10%，触发减仓",
            ),
            AlertRule(
                rule_id    = "daily_loss_warning",
                alert_type = AlertType.DAILY_LOSS_BREACH,
                threshold  = 0.03,
                risk_level = RiskLevel.WARNING,
                action     = RiskAction.ALERT,
                cooldown_s = 300,
                description= "当日亏损预警 3%",
            ),
            AlertRule(
                rule_id    = "daily_loss_critical",
                alert_type = AlertType.DAILY_LOSS_BREACH,
                threshold  = 0.05,
                risk_level = RiskLevel.CRITICAL,
                action     = RiskAction.HALT_TRADING,
                cooldown_s = 0,
                description= "当日亏损 5%，暂停交易",
            ),
            AlertRule(
                rule_id    = "leverage_breach",
                alert_type = AlertType.LEVERAGE_BREACH,
                threshold  = 1.8,
                risk_level = RiskLevel.WARNING,
                action     = RiskAction.ALERT,
                cooldown_s = 120,
                description= "杠杆预警 1.8x",
            ),
        ]
        for r in defaults:
            self._rules[r.rule_id] = r

    # ------------------------------------------------------------------ #
    #  规则管理
    # ------------------------------------------------------------------ #

    def add_rule(self, rule: AlertRule) -> None:
        self._rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> None:
        self._rules.pop(rule_id, None)

    def get_rules(self) -> list[AlertRule]:
        return list(self._rules.values())

    # ------------------------------------------------------------------ #
    #  校验（核心）
    # ------------------------------------------------------------------ #

    def check_drawdown(self, state: DrawdownState) -> list[AlertRecord]:
        """检查回撤预警。"""
        alerts: list[AlertRecord] = []
        for rule in self._rules.values():
            if not rule.can_trigger():
                continue
            value = None
            if rule.alert_type == AlertType.DRAWDOWN_BREACH:
                value = state.current_drawdown_pct
            elif rule.alert_type == AlertType.DAILY_LOSS_BREACH:
                value = state.daily_loss_pct
            else:
                continue

            if value >= rule.threshold:
                alert = self._make_alert(rule, value)
                alerts.append(alert)
                rule.mark_triggered()

        return alerts

    def check_exposure(self, report: ExposureReport) -> list[AlertRecord]:
        """检查暴露预警（杠杆 / 仓位）。"""
        alerts: list[AlertRecord] = []
        for rule in self._rules.values():
            if not rule.can_trigger():
                continue
            value = None
            if rule.alert_type == AlertType.LEVERAGE_BREACH:
                value = report.leverage
            elif rule.alert_type == AlertType.POSITION_BREACH:
                value = report.max_single_weight
            else:
                continue

            if value is not None and value >= rule.threshold:
                alert = self._make_alert(rule, value)
                alerts.append(alert)
                rule.mark_triggered()

        return alerts

    # ------------------------------------------------------------------ #
    #  历史记录
    # ------------------------------------------------------------------ #

    def get_history(self) -> list[AlertRecord]:
        return list(self._history)

    def get_unacknowledged(self) -> list[AlertRecord]:
        return [a for a in self._history if not a.acknowledged]

    def acknowledge(self, alert_id: str) -> None:
        for a in self._history:
            if a.alert_id == alert_id:
                a.acknowledge()
                break

    def acknowledge_all(self) -> None:
        for a in self._history:
            if not a.acknowledged:
                a.acknowledge()

    def clear_history(self) -> None:
        self._history.clear()

    # ------------------------------------------------------------------ #
    #  内部
    # ------------------------------------------------------------------ #

    def _make_alert(self, rule: AlertRule, value: float) -> AlertRecord:
        alert = AlertRecord(
            alert_id        = str(uuid.uuid4())[:8],
            alert_type      = rule.alert_type,
            risk_level      = rule.risk_level,
            action          = rule.action,
            triggered_value = value,
            threshold       = rule.threshold,
            message         = (
                f"{rule.description}  "
                f"当前={value:.4%}  阈值={rule.threshold:.4%}"
            ),
        )
        self._history.append(alert)
        return alert
