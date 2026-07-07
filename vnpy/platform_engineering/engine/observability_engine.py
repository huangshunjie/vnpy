"""
platform_engineering/engine/observability_engine.py
ObservabilityEngine 完整版 — Phase 2
四层指标采集 + 告警规则引擎 + 健康分计算
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..model.metric import MetricPoint, MetricSeries, AlertRecord, PlatformHealthScore
from ..repository.metric_repository import MetricRepository
from ..constant import (
    MetricLayer, MetricType, AlertSeverity, HealthLevel,
)

# ── 告警规则 ──────────────────────────────────────────────────────

class AlertRule:
    """单条阈值告警规则。"""

    def __init__(
        self,
        rule_id:    str,
        name:       str,
        metric_name: str,
        layer:      MetricLayer,
        severity:   AlertSeverity,
        threshold:  float,
        comparator: str   = ">",      # ">", "<", ">=", "<="
        auto_resolve: bool = True,
        message_tpl: str  = "",
    ) -> None:
        self.rule_id      = rule_id
        self.name         = name
        self.metric_name  = metric_name
        self.layer        = layer
        self.severity     = severity
        self.threshold    = threshold
        self.comparator   = comparator
        self.auto_resolve = auto_resolve
        self.message_tpl  = message_tpl or f"{name}: {{value:.2f}} (threshold {threshold})"
        self._active_alert_id: Optional[str] = None

    def evaluate(self, value: float) -> bool:
        ops: Dict[str, Callable[[float, float], bool]] = {
            ">":  lambda v, t: v > t,
            "<":  lambda v, t: v < t,
            ">=": lambda v, t: v >= t,
            "<=": lambda v, t: v <= t,
        }
        fn = ops.get(self.comparator, ops[">"])
        return fn(value, self.threshold)

    def format_message(self, value: float) -> str:
        try:
            return self.message_tpl.format(value=value)
        except Exception:
            return self.message_tpl


# ── 健康分权重 ────────────────────────────────────────────────────

_LAYER_WEIGHT = {
    MetricLayer.DATA:     0.30,
    MetricLayer.STRATEGY: 0.30,
    MetricLayer.TRADING:  0.25,
    MetricLayer.SYSTEM:   0.15,
}

_SEVERITY_PENALTY = {
    AlertSeverity.INFO:     0,
    AlertSeverity.WARNING:  5,
    AlertSeverity.ERROR:    15,
    AlertSeverity.CRITICAL: 30,
}


# ── ObservabilityEngine ───────────────────────────────────────────

class ObservabilityEngine:
    """
    四层可观测性引擎。
    - record_metric()  : 写入指标数据点，自动评估告警规则
    - get_health_score(): 返回当前平台健康分
    - list_alerts()    : 列出告警记录
    - resolve_alert()  : 手动解除告警
    - add_rule() / remove_rule(): 动态管理告警规则
    - layer_score()    : 查询单层得分
    """

    def __init__(self) -> None:
        self._repo:  MetricRepository           = MetricRepository()
        self._rules: Dict[str, AlertRule]        = {}
        self._score: PlatformHealthScore         = PlatformHealthScore()
        self._layer_scores: Dict[MetricLayer, float] = {
            l: 100.0 for l in MetricLayer
        }
        self._on_alert_callbacks: List[Callable[[AlertRecord], None]] = []
        self._setup_default_rules()

    # ── lifecycle ─────────────────────────────────────────────────

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    # ── default rules ─────────────────────────────────────────────

    def _setup_default_rules(self) -> None:
        defaults: List[Tuple] = [
            # (name, metric_name, layer, severity, threshold, comparator)
            ("CPU 过高",      "system.cpu_pct",      MetricLayer.SYSTEM,   AlertSeverity.WARNING,  80.0, ">"),
            ("CPU 严重",      "system.cpu_pct",      MetricLayer.SYSTEM,   AlertSeverity.CRITICAL, 95.0, ">"),
            ("内存过高",      "system.mem_pct",      MetricLayer.SYSTEM,   AlertSeverity.WARNING,  85.0, ">"),
            ("内存严重",      "system.mem_pct",      MetricLayer.SYSTEM,   AlertSeverity.CRITICAL, 95.0, ">"),
            ("数据延迟告警",  "data.delay_secs",     MetricLayer.DATA,     AlertSeverity.WARNING,  60.0, ">"),
            ("数据延迟严重",  "data.delay_secs",     MetricLayer.DATA,     AlertSeverity.CRITICAL, 300.0, ">"),
            ("数据缺失率",    "data.missing_rate",   MetricLayer.DATA,     AlertSeverity.WARNING,  0.05, ">"),
            ("订单延迟告警",  "trading.order_delay_ms", MetricLayer.TRADING, AlertSeverity.WARNING, 500.0, ">"),
            ("执行失败率",    "trading.failure_rate",MetricLayer.TRADING,  AlertSeverity.ERROR,    0.02, ">"),
            ("策略性能漂移",  "strategy.perf_drift", MetricLayer.STRATEGY, AlertSeverity.WARNING,  0.20, ">"),
            ("Alpha 衰减",    "strategy.alpha_decay",MetricLayer.STRATEGY, AlertSeverity.WARNING,  0.30, ">"),
            ("风险敞口告警",  "strategy.risk_drift", MetricLayer.STRATEGY, AlertSeverity.ERROR,    0.50, ">"),
        ]
        for name, metric, layer, sev, thresh, cmp in defaults:
            self.add_rule(AlertRule(
                rule_id     = "DEFAULT-" + uuid.uuid4().hex[:6].upper(),
                name        = name,
                metric_name = metric,
                layer       = layer,
                severity    = sev,
                threshold   = thresh,
                comparator  = cmp,
                auto_resolve= True,
            ))

    # ── rule management ───────────────────────────────────────────

    def add_rule(self, rule: AlertRule) -> None:
        self._rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> None:
        self._rules.pop(rule_id, None)

    def list_rules(self) -> List[AlertRule]:
        return list(self._rules.values())

    # ── metric ingestion ──────────────────────────────────────────

    def record_metric(self, point: MetricPoint) -> None:
        self._repo.append_point(point)
        self._evaluate_rules(point)
        self._recalculate_score()

    def record_many(self, points: List[MetricPoint]) -> None:
        for p in points:
            self._repo.append_point(p)
            self._evaluate_rules(p)
        self._recalculate_score()

    def make_point(
        self,
        name:   str,
        value:  float,
        layer:  MetricLayer,
        metric_type: MetricType = MetricType.GAUGE,
        unit:   str = "",
        source: str = "",
        labels: Dict[str, str] = None,
    ) -> MetricPoint:
        return MetricPoint(
            metric_id   = uuid.uuid4().hex,
            name        = name,
            layer       = layer,
            metric_type = metric_type,
            value       = value,
            unit        = unit,
            source      = source,
            labels      = labels or {},
            timestamp   = datetime.now(),
        )

    # ── alert evaluation ──────────────────────────────────────────

    def _evaluate_rules(self, point: MetricPoint) -> None:
        for rule in self._rules.values():
            if rule.metric_name != point.name:
                continue
            triggered = rule.evaluate(point.value)
            if triggered and rule._active_alert_id is None:
                alert = AlertRecord(
                    alert_id     = "ALT-" + uuid.uuid4().hex[:8].upper(),
                    name         = rule.name,
                    severity     = rule.severity,
                    layer        = rule.layer,
                    message      = rule.format_message(point.value),
                    metric_name  = point.name,
                    metric_value = point.value,
                    threshold    = rule.threshold,
                    source       = point.source,
                    is_resolved  = False,
                    created_at   = datetime.now(),
                )
                self._repo.save_alert(alert)
                rule._active_alert_id = alert.alert_id
                for cb in self._on_alert_callbacks:
                    try:
                        cb(alert)
                    except Exception:
                        pass
            elif not triggered and rule.auto_resolve and rule._active_alert_id:
                self.resolve_alert(rule._active_alert_id)
                rule._active_alert_id = None

    def on_alert(self, callback: Callable[[AlertRecord], None]) -> None:
        """注册告警触发回调。"""
        self._on_alert_callbacks.append(callback)

    # ── health score calculation ──────────────────────────────────

    def _recalculate_score(self) -> None:
        active_alerts = self._repo.list_alerts(active_only=True)

        # 按层分组
        layer_penalties: Dict[MetricLayer, float] = {l: 0.0 for l in MetricLayer}
        for alert in active_alerts:
            penalty = _SEVERITY_PENALTY.get(alert.severity, 0)
            layer_penalties[alert.layer] = min(
                100.0, layer_penalties[alert.layer] + penalty)

        # 各层得分
        for layer in MetricLayer:
            self._layer_scores[layer] = max(0.0, 100.0 - layer_penalties[layer])

        # 加权总分
        total = sum(
            self._layer_scores[l] * w for l, w in _LAYER_WEIGHT.items()
        )
        self._score.score           = round(total, 1)
        self._score.data_score      = self._layer_scores[MetricLayer.DATA]
        self._score.strategy_score  = self._layer_scores[MetricLayer.STRATEGY]
        self._score.trading_score   = self._layer_scores[MetricLayer.TRADING]
        self._score.system_score    = self._layer_scores[MetricLayer.SYSTEM]
        self._score.active_alerts   = len(active_alerts)
        self._score.updated_at      = datetime.now()

        if total >= 80:
            self._score.level = HealthLevel.GREEN
        elif total >= 50:
            self._score.level = HealthLevel.YELLOW
        else:
            self._score.level = HealthLevel.RED

    # ── public query ──────────────────────────────────────────────

    def get_health_score(self) -> PlatformHealthScore:
        return self._score

    def layer_score(self, layer: MetricLayer) -> float:
        return self._layer_scores.get(layer, 100.0)

    def list_alerts(self, active_only: bool = True) -> List[AlertRecord]:
        return self._repo.list_alerts(active_only=active_only)

    def resolve_alert(self, alert_id: str) -> None:
        alert = self._repo.get_alert(alert_id)
        if alert and not alert.is_resolved:
            alert.is_resolved = True
            alert.resolved_at = datetime.now()
            self._repo.save_alert(alert)
            # clear rule reference
            for rule in self._rules.values():
                if rule._active_alert_id == alert_id:
                    rule._active_alert_id = None
            self._recalculate_score()

    def get_series(self, name: str) -> Optional[MetricSeries]:
        return self._repo.get_series(name)

    def list_series(self) -> List[MetricSeries]:
        return self._repo.list_series()

    def stats(self) -> dict:
        s = self._repo.stats()
        s["health_score"]    = self._score.score
        s["health_level"]    = self._score.level.value
        s["data_score"]      = self._score.data_score
        s["strategy_score"]  = self._score.strategy_score
        s["trading_score"]   = self._score.trading_score
        s["system_score"]    = self._score.system_score
        s["rules"]           = len(self._rules)
        return s
