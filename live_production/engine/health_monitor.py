"""
live_production/engine/health_monitor.py  (Phase 5)

HealthMonitor — 实时健康监控引擎。

监控指标：
  - 网关往返延迟（ms）
  - 心跳状态（ok / timeout）
  - 订单成功率（近 60s 滑动窗口）
  - 行情数据延迟（s）
  - 综合健康分数（0-1）→ HEALTHY / WARNING / CRITICAL

阈值配置（可运行时修改）：
  latency_warn_ms   = 200   超过则 WARNING
  latency_crit_ms   = 500   超过则 CRITICAL
  heartbeat_timeout = 30    秒，超时则 CRITICAL
  order_rate_warn   = 0.95  低于则 WARNING
  order_rate_crit   = 0.80  低于则 CRITICAL
  data_delay_warn_s = 3     超过则 WARNING
  data_delay_crit_s = 10    超过则 CRITICAL

❌ 不执行任何交易逻辑
✔  采集数据 → 评估状态 → 广播 EVENT_HEALTH_UPDATE
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from ..constant import SystemHealthState
from ..event import EVENT_HEALTH_UPDATE
from ..utils.metrics_utils import (
    LatencyTracker,
    RateCounter,
    RollingWindow,
    compute_health_score,
)


@dataclass
class HealthThresholds:
    latency_warn_ms:    float = 200.0
    latency_crit_ms:    float = 500.0
    heartbeat_timeout:  float = 30.0    # seconds
    order_rate_warn:    float = 0.95
    order_rate_crit:    float = 0.80
    data_delay_warn_s:  float = 3.0
    data_delay_crit_s:  float = 10.0
    health_score_warn:  float = 0.70
    health_score_crit:  float = 0.40


@dataclass
class HealthSnapshot:
    """单次健康快照。"""
    health_state:       SystemHealthState = SystemHealthState.UNKNOWN
    health_score:       float = 0.0
    latency_ms:         float = 0.0
    latency_p95_ms:     float = 0.0
    order_success_rate: float = 0.0
    data_delay_s:       float = 0.0
    heartbeat_ok:       bool  = False
    last_heartbeat_at:  datetime | None = None
    snapshot_at:        datetime = field(default_factory=datetime.now)
    alerts:             list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "health_state":       self.health_state.value,
            "health_score":       round(self.health_score, 3),
            "latency_ms":         round(self.latency_ms, 1),
            "latency_p95_ms":     round(self.latency_p95_ms, 1),
            "order_success_rate": round(self.order_success_rate, 4),
            "data_delay_s":       round(self.data_delay_s, 1),
            "heartbeat_ok":       self.heartbeat_ok,
            "last_heartbeat_at":  str(self.last_heartbeat_at)[:19]
                                  if self.last_heartbeat_at else "---",
            "snapshot_at":        str(self.snapshot_at)[:19],
            "alerts":             self.alerts,
        }


class HealthMonitor:
    """实时健康监控引擎（Phase 5）。"""

    def __init__(
        self,
        event_publish_fn: Callable,
        log_fn:           Callable,
        thresholds:       HealthThresholds | None = None,
    ) -> None:
        self._publish    = event_publish_fn
        self._log        = log_fn
        self._thresholds = thresholds or HealthThresholds()
        self._lock       = threading.Lock()

        # 指标采集器
        self._latency       = LatencyTracker(maxlen=120)
        self._order_rate    = RateCounter(window_seconds=60.0)
        self._data_delay    = RollingWindow(maxlen=60)

        # 心跳
        self._last_heartbeat_at: datetime | None = None
        self._heartbeat_ok = False

        # 当前快照 + 历史
        self._current: HealthSnapshot = HealthSnapshot()
        self._history: list[HealthSnapshot] = []
        self._max_history = 600    # 最多 10 分钟 @1s
        self._prev_state  = SystemHealthState.UNKNOWN

    # ------------------------------------------------------------------ #
    #  数据上报接口（外部调用）
    # ------------------------------------------------------------------ #

    def record_latency(self, latency_ms: float) -> None:
        """上报网关往返延迟。"""
        self._latency.record(latency_ms)

    def record_order_result(self, success: bool) -> None:
        """上报订单执行结果（成功/失败）。"""
        self._order_rate.record(success)

    def record_data_delay(self, delay_s: float) -> None:
        """上报行情数据延迟（秒）。"""
        self._data_delay.push(max(0.0, delay_s))

    def record_heartbeat(self, ok: bool = True) -> None:
        """上报心跳状态。"""
        with self._lock:
            self._heartbeat_ok      = ok
            self._last_heartbeat_at = datetime.now()

    # ------------------------------------------------------------------ #
    #  评估健康状态（主循环调用 / 手动调用）
    # ------------------------------------------------------------------ #

    def evaluate(self) -> HealthSnapshot:
        """
        基于当前指标计算健康状态，广播 EVENT_HEALTH_UPDATE。

        Returns
        -------
        HealthSnapshot  本次评估结果
        """
        t = self._thresholds
        alerts: list[str] = []

        # 读取当前指标
        latency_ms  = self._latency.latest_ms
        lat_p95     = self._latency.p95_ms
        order_rate  = self._order_rate.rate()
        data_delay  = self._data_delay.latest() if len(self._data_delay) > 0 else 0.0

        # 心跳超时检查
        with self._lock:
            hb_ok = self._heartbeat_ok
            hb_at = self._last_heartbeat_at

        if hb_at is not None:
            elapsed = (datetime.now() - hb_at).total_seconds()
            if elapsed > t.heartbeat_timeout:
                hb_ok = False
                alerts.append(
                    f"心跳超时 {elapsed:.0f}s > {t.heartbeat_timeout}s"
                )
        else:
            hb_ok = False

        # 各维度告警检查
        if latency_ms >= t.latency_crit_ms:
            alerts.append(f"网关延迟 CRITICAL {latency_ms:.0f}ms")
        elif latency_ms >= t.latency_warn_ms:
            alerts.append(f"网关延迟 WARNING {latency_ms:.0f}ms")

        if order_rate < t.order_rate_crit:
            alerts.append(f"订单成功率 CRITICAL {order_rate:.1%}")
        elif order_rate < t.order_rate_warn:
            alerts.append(f"订单成功率 WARNING {order_rate:.1%}")

        if data_delay >= t.data_delay_crit_s:
            alerts.append(f"行情延迟 CRITICAL {data_delay:.1f}s")
        elif data_delay >= t.data_delay_warn_s:
            alerts.append(f"行情延迟 WARNING {data_delay:.1f}s")

        if not hb_ok and hb_at is not None:
            alerts.append("心跳异常")

        # 综合健康分
        score = compute_health_score(
            latency_ms         = latency_ms,
            order_success_rate = order_rate,
            data_delay_s       = data_delay,
            heartbeat_ok       = hb_ok,
        )

        # 健康等级
        if not hb_ok or score < t.health_score_crit:
            state = SystemHealthState.CRITICAL
        elif score < t.health_score_warn or alerts:
            state = SystemHealthState.WARNING
        else:
            state = SystemHealthState.HEALTHY

        snap = HealthSnapshot(
            health_state       = state,
            health_score       = score,
            latency_ms         = latency_ms,
            latency_p95_ms     = lat_p95,
            order_success_rate = order_rate,
            data_delay_s       = data_delay,
            heartbeat_ok       = hb_ok,
            last_heartbeat_at  = hb_at,
            alerts             = alerts,
        )

        with self._lock:
            self._current = snap
            self._history.append(snap)
            if len(self._history) > self._max_history:
                self._history.pop(0)

        # 状态变化时打日志
        if state != self._prev_state:
            self._log(
                f"[Health] {self._prev_state.value} -> {state.value}"
                f"  score={score:.3f}  alerts={len(alerts)}"
            )
            self._prev_state = state

        self._publish(EVENT_HEALTH_UPDATE, snap.to_dict())
        return snap

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    @property
    def current(self) -> HealthSnapshot:
        return self._current

    @property
    def state(self) -> SystemHealthState:
        return self._current.health_state

    def get_history(self, limit: int = 120) -> list[HealthSnapshot]:
        return self._history[-limit:]

    def get_latency_series(self, limit: int = 60) -> list[float]:
        return self._latency._win.to_list()[-limit:]

    def get_order_rate_history(self, limit: int = 60) -> list[float]:
        # RateCounter 不保存历史序列；通过 history snapshots 提取
        snaps = self.get_history(limit)
        return [s.order_success_rate for s in snaps]

    def summary(self) -> dict:
        snap = self._current
        return {
            "health_state":       snap.health_state.value,
            "health_score":       round(snap.health_score, 3),
            "latency_ms":         round(snap.latency_ms, 1),
            "latency_p95_ms":     round(snap.latency_p95_ms, 1),
            "order_success_rate": round(snap.order_success_rate, 4),
            "data_delay_s":       round(snap.data_delay_s, 1),
            "heartbeat_ok":       snap.heartbeat_ok,
            "alerts":             snap.alerts,
            "history_count":      len(self._history),
        }

    def update_thresholds(self, **kwargs) -> None:
        """动态更新告警阈值，如 update_thresholds(latency_warn_ms=150)。"""
        for k, v in kwargs.items():
            if hasattr(self._thresholds, k):
                setattr(self._thresholds, k, v)
                self._log(f"[Health] threshold updated: {k}={v}")
