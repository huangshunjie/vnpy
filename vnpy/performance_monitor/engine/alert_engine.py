"""
performance_monitor/engine/alert_engine.py

AlertEngine — 告警引擎。

职责：
  - 维护每个模块的告警阈值规则
  - 每次收到新快照时评估所有规则
  - 派发 Alert 对象，去重（同一模块同类问题不重复告警）
  - 维护活跃告警列表与历史
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Callable
import uuid

from ..constant import AlertLevel, MetricType, ModuleStatus, MONITORED_MODULES
from ..model.metric_model import Alert, SystemSnapshot, ModuleMetrics


# ── 默认告警规则 ──────────────────────────────────────────────────────
# (metric, threshold, level, message_template)
_DEFAULT_RULES: list[tuple[MetricType, float, AlertLevel, str]] = [
    # latency
    (MetricType.LATENCY, 2000.0,  AlertLevel.WARNING,  "avg latency {v:.0f}ms > 2000ms"),
    (MetricType.LATENCY, 5000.0,  AlertLevel.CRITICAL, "avg latency {v:.0f}ms > 5000ms"),
    (MetricType.LATENCY, 10000.0, AlertLevel.FATAL,    "avg latency {v:.0f}ms > 10s"),
    # error_rate
    (MetricType.ERROR_RATE, 0.10, AlertLevel.WARNING,  "error rate {v:.1%} > 10%"),
    (MetricType.ERROR_RATE, 0.30, AlertLevel.CRITICAL, "error rate {v:.1%} > 30%"),
    (MetricType.ERROR_RATE, 0.60, AlertLevel.FATAL,    "error rate {v:.1%} > 60%"),
    # throughput (< minimum triggers warning — checked separately)
]

# ── 模块级最低吞吐量（0 = 不检查） ───────────────────────────────────
_MIN_THROUGHPUT: dict[str, float] = {
    "execution_engine":          0.5,   # 至少 0.5 events/min
    "risk_engine_2":             0.5,
    "data_intelligence_ai":      0.5,
    "system_integration_bus":    1.0,
}

# ── 模块离线告警级别 ──────────────────────────────────────────────────
_OFFLINE_LEVEL: dict[str, AlertLevel] = {
    "execution_engine":          AlertLevel.FATAL,
    "risk_engine_2":             AlertLevel.FATAL,
    "data_intelligence_ai":      AlertLevel.CRITICAL,
    "system_integration_bus":    AlertLevel.CRITICAL,
    "portfolio_engine":          AlertLevel.CRITICAL,
    "alpha_factory_2":           AlertLevel.WARNING,
    "market_regime_ai":          AlertLevel.WARNING,
}

# dedup window: 同一 (module, metric, level) 在此窗口内不重复告警
_DEDUP_WINDOW_SECS = 120.0


class AlertEngine:
    """告警引擎。"""

    def __init__(
        self,
        on_alert: Callable | None = None,   # (Alert) → None
        log_fn:   Callable | None = None,
    ) -> None:
        self._on_alert = on_alert or (lambda a: None)
        self._log      = log_fn or (lambda m: None)

        self._active_alerts:  list[Alert] = []
        self._alert_history:  list[Alert] = []
        # dedup cache: {(module, metric, level): last_fired_at}
        self._dedup: dict[tuple, datetime] = {}

    # ── evaluate snapshot ─────────────────────────────────────────────
    def evaluate(self, snapshot: SystemSnapshot) -> list[Alert]:
        """
        根据最新系统快照评估所有告警规则。
        返回本次新触发的告警列表。
        """
        new_alerts: list[Alert] = []
        now = datetime.now()

        for mod, m_dict in snapshot.modules.items():
            # latency rules
            avg_lat = m_dict.get("avg_latency_1m", 0.0)
            for metric, thresh, level, tmpl in _DEFAULT_RULES:
                if metric == MetricType.LATENCY and avg_lat > thresh:
                    a = self._make_alert(mod, metric, level,
                                         tmpl.format(v=avg_lat), avg_lat, thresh)
                    if a:
                        new_alerts.append(a)

                # error_rate rules
                err = m_dict.get("error_rate_1m", 0.0)
                if metric == MetricType.ERROR_RATE and err > thresh:
                    a = self._make_alert(mod, metric, level,
                                         tmpl.format(v=err), err, thresh)
                    if a:
                        new_alerts.append(a)

            # throughput minimum
            min_tp = _MIN_THROUGHPUT.get(mod, 0.0)
            tp     = m_dict.get("throughput_1m", 0.0)
            status = m_dict.get("status", "unknown")
            if min_tp > 0 and tp < min_tp and status == "active":
                a = self._make_alert(
                    mod, MetricType.THROUGHPUT, AlertLevel.WARNING,
                    f"throughput {tp:.2f} < min {min_tp}",
                    tp, min_tp)
                if a:
                    new_alerts.append(a)

            # offline alerts
            if status == ModuleStatus.OFFLINE.value:
                lvl = _OFFLINE_LEVEL.get(mod, AlertLevel.WARNING)
                a   = self._make_alert(
                    mod, MetricType.CUSTOM, lvl,
                    f"{mod} OFFLINE", 0.0, 0.0)
                if a:
                    new_alerts.append(a)

        # auto-resolve: alerts for modules that are now healthy
        self._auto_resolve(snapshot)

        self._active_alerts.extend(new_alerts)
        self._alert_history.extend(new_alerts)
        if len(self._alert_history) > 1000:
            self._alert_history = self._alert_history[-1000:]

        for a in new_alerts:
            self._on_alert(a)
            self._log(f"[AlertEngine] [{a.level.value.upper()}] "
                      f"{a.module}: {a.message}")
        return new_alerts

    def _make_alert(
        self,
        module:    str,
        metric:    MetricType,
        level:     AlertLevel,
        message:   str,
        value:     float,
        threshold: float,
    ) -> Alert | None:
        """构建告警，若在 dedup 窗口内则返回 None（不重复告警）。"""
        key = (module, metric, level)
        now = datetime.now()
        last = self._dedup.get(key)
        if last and (now - last).total_seconds() < _DEDUP_WINDOW_SECS:
            return None
        self._dedup[key] = now
        return Alert(
            alert_id  = f"ALT_{uuid.uuid4().hex[:8].upper()}",
            module    = module,
            level     = level,
            metric    = metric,
            message   = message,
            value     = value,
            threshold = threshold,
            fired_at  = now,
        )

    def _auto_resolve(self, snapshot: SystemSnapshot) -> None:
        """将已恢复模块的告警标记为 resolved。"""
        resolved_modules = {
            mod for mod, d in snapshot.modules.items()
            if d.get("status") == ModuleStatus.ACTIVE.value
            and d.get("error_rate_1m", 0) < 0.05
            and d.get("avg_latency_1m", 0) < 500
        }
        now = datetime.now()
        for a in self._active_alerts:
            if a.module in resolved_modules and not a.resolved:
                a.resolved    = True
                a.resolved_at = now
        self._active_alerts = [a for a in self._active_alerts if not a.resolved]

    # ── manual resolve ────────────────────────────────────────────────
    def resolve(self, alert_id: str) -> bool:
        for a in self._active_alerts:
            if a.alert_id == alert_id:
                a.resolved    = True
                a.resolved_at = datetime.now()
                self._active_alerts.remove(a)
                return True
        return False

    def resolve_module(self, module: str) -> int:
        """手动解除指定模块的所有告警。"""
        now = datetime.now()
        count = 0
        still_active = []
        for a in self._active_alerts:
            if a.module == module:
                a.resolved = True; a.resolved_at = now; count += 1
            else:
                still_active.append(a)
        self._active_alerts = still_active
        return count

    # ── query ─────────────────────────────────────────────────────────
    def get_active(self, level: AlertLevel | None = None) -> list[Alert]:
        if level is None:
            return list(self._active_alerts)
        return [a for a in self._active_alerts if a.level == level]

    def get_history(self, n: int = 100) -> list[Alert]:
        return self._alert_history[-n:]

    def active_count(self, level: AlertLevel | None = None) -> int:
        return len(self.get_active(level))

    def summary(self) -> dict:
        return {
            "active_total":    len(self._active_alerts),
            "active_critical": self.active_count(AlertLevel.CRITICAL),
            "active_fatal":    self.active_count(AlertLevel.FATAL),
            "active_warning":  self.active_count(AlertLevel.WARNING),
            "total_fired":     len(self._alert_history),
        }
