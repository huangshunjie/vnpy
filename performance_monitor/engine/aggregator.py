"""
performance_monitor/engine/aggregator.py

MetricAggregator — 指标聚合器。

职责：
  - 从 MetricCollector 读取原始缓冲数据
  - 计算滑动窗口统计（avg/p95/p99/max latency、throughput、error_rate）
  - 检测模块超时（IDLE / OFFLINE）
  - 计算全系统健康分 [0, 100]
"""
from __future__ import annotations
import math
from datetime import datetime, timedelta
from typing import Callable

from ..constant import ModuleStatus, MONITORED_MODULES, AggWindow
from ..model.metric_model import ModuleMetrics, SystemSnapshot
from .collector import MetricCollector

import uuid


# ── 超时阈值（秒） ─────────────────────────────────────────────────────
_IDLE_TIMEOUT: dict[str, float] = {
    "data_intelligence_ai":          30.0,
    "alpha_factory_2":               60.0,
    "market_regime_ai":              30.0,
    "portfolio_engine":              20.0,
    "capital_allocation_ai":         30.0,
    "risk_engine_2":                 15.0,
    "strategy_lifecycle_ai":         60.0,
    "execution_engine":              10.0,
    "execution_intelligence_ai":     10.0,
    "adaptive_learning_ai":         120.0,
    "global_portfolio_intelligence": 30.0,
    "live_production":               15.0,
    "quant_os":                      30.0,
    "factor_research":               60.0,
    "research_validation":           60.0,
    "system_integration_bus":        15.0,
}
_OFFLINE_MULTIPLIER = 5.0   # idle_timeout × 5 = offline threshold


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sv = sorted(values)
    k  = (len(sv) - 1) * pct / 100.0
    lo, hi = int(k), min(int(k) + 1, len(sv) - 1)
    return round(sv[lo] + (sv[hi] - sv[lo]) * (k - lo), 3)


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 3) if values else 0.0


def _throughput_epm(ts_buf, window_secs: float = 60.0) -> float:
    """Events per minute in the last window_secs."""
    if not ts_buf:
        return 0.0
    cutoff = datetime.now() - timedelta(seconds=window_secs)
    recent = [t for t in ts_buf if t >= cutoff]
    return round(len(recent) / (window_secs / 60.0), 2)


def _error_rate(event_ts_buf, error_ts_buf,
                window_secs: float = 60.0) -> float:
    cutoff = datetime.now() - timedelta(seconds=window_secs)
    ev = sum(1 for t in event_ts_buf if t >= cutoff)
    er = sum(1 for t in error_ts_buf if t >= cutoff)
    if ev == 0:
        return 0.0
    return round(er / ev, 4)


class MetricAggregator:
    """指标聚合器。"""

    def __init__(
        self,
        collector:     MetricCollector,
        window:        AggWindow = AggWindow.W1M,
        on_status_change: Callable | None = None,  # (module, old, new) → None
        log_fn:        Callable | None = None,
    ) -> None:
        self._collector = collector
        self._window    = window
        self._on_status = on_status_change or (lambda mod, o, n: None)
        self._log       = log_fn or (lambda m: None)
        self._snapshot_history: list[SystemSnapshot] = []

    # ── periodic update (called every N seconds) ─────────────────────
    def update(self) -> SystemSnapshot:
        """
        更新所有模块的聚合指标，检测超时，生成系统快照。
        应由定时器每 5-10 秒调用一次。
        """
        all_m = self._collector.get_all_metrics()
        w_secs = self._window.value

        for mod, m in all_m.items():
            self._update_module(m, w_secs)

        snap = self._build_snapshot(all_m)
        self._snapshot_history.append(snap)
        if len(self._snapshot_history) > 500:
            self._snapshot_history.pop(0)
        return snap

    def _update_module(self, m: ModuleMetrics, w_secs: float) -> None:
        """更新单个模块的聚合指标并检测超时。"""
        # latency stats from buffer
        lat_buf = list(m._latency_buf)
        if lat_buf:
            cutoff = datetime.now() - timedelta(seconds=w_secs)
            # _latency_buf has no timestamps — use all recent values
            recent_lat = lat_buf[-min(len(lat_buf), int(w_secs)):] if lat_buf else []
            m.avg_latency_1m = _mean(recent_lat)
            m.p95_latency_1m = _percentile(recent_lat, 95)
            m.p99_latency_1m = _percentile(recent_lat, 99)
            m.max_latency_1m = round(max(recent_lat), 3) if recent_lat else 0.0

        # throughput & error rate
        m.throughput_1m = _throughput_epm(m._event_ts_buf, w_secs)
        m.error_rate_1m = _error_rate(m._event_ts_buf, m._error_ts_buf, w_secs)
        m.throughput    = m.throughput_1m
        m.error_rate    = m.error_rate_1m

        # timeout detection
        self._check_timeout(m)

    def _check_timeout(self, m: ModuleMetrics) -> None:
        if m.status == ModuleStatus.UNKNOWN:
            return
        if m.last_seen is None:
            return

        ago = m.last_seen_ago_s
        idle_t    = _IDLE_TIMEOUT.get(m.module, 60.0)
        offline_t = idle_t * _OFFLINE_MULTIPLIER

        prev = m.status
        if ago > offline_t:
            m.status = ModuleStatus.OFFLINE
        elif ago > idle_t:
            m.status = ModuleStatus.IDLE
        elif m.error_rate_1m > 0.3:
            m.status = ModuleStatus.DEGRADED
        else:
            m.status = ModuleStatus.ACTIVE

        if m.status != prev:
            self._log(f"[Aggregator] {m.module}: {prev.value} → {m.status.value}")
            self._on_status(m.module, prev, m.status)

    def _build_snapshot(self, all_m: dict[str, ModuleMetrics]) -> SystemSnapshot:
        """构建全系统瞬时快照。"""
        snap = SystemSnapshot(
            snapshot_id = f"SS_{uuid.uuid4().hex[:8].upper()}",
            taken_at    = datetime.now(),
        )

        active_lats = []
        for mod, m in all_m.items():
            snap.total_events += m.event_count
            snap.total_errors += m.error_count
            snap.system_throughput += m.throughput_1m

            if m.avg_latency_1m > 0:
                active_lats.append(m.avg_latency_1m)

            st = m.status
            if st == ModuleStatus.ACTIVE:    snap.active_count   += 1
            elif st == ModuleStatus.IDLE:    snap.idle_count     += 1
            elif st == ModuleStatus.DEGRADED:snap.degraded_count += 1
            elif st == ModuleStatus.OFFLINE: snap.offline_count  += 1
            else:                            snap.unknown_count  += 1

            snap.modules[mod] = m.to_dict()

        # system error rate (weighted by event count)
        total_ev = snap.total_events or 1
        snap.system_error_rate = round(snap.total_errors / total_ev, 4)

        # avg latency
        snap.avg_latency_ms = _mean(active_lats)

        # health score
        snap.health_score = self._compute_health(snap, all_m)

        return snap

    def _compute_health(self, snap: SystemSnapshot,
                         all_m: dict[str, ModuleMetrics]) -> float:
        """
        系统健康分 [0, 100]:
          - 每个 OFFLINE  模块  -15
          - 每个 DEGRADED 模块  -8
          - 每个 IDLE     模块  -3
          - 系统 error_rate > 0.1  -10
          - 系统 error_rate > 0.3  additional -15
          - avg_latency > 1000ms   -5
          - avg_latency > 5000ms   additional -10
        """
        score = 100.0
        score -= snap.offline_count  * 15.0
        score -= snap.degraded_count * 8.0
        score -= snap.idle_count     * 3.0

        if snap.system_error_rate > 0.3:
            score -= 25.0
        elif snap.system_error_rate > 0.1:
            score -= 10.0

        if snap.avg_latency_ms > 5000:
            score -= 15.0
        elif snap.avg_latency_ms > 1000:
            score -= 5.0

        return round(max(score, 0.0), 1)

    # ── query ─────────────────────────────────────────────────────────
    def get_latest_snapshot(self) -> SystemSnapshot | None:
        return self._snapshot_history[-1] if self._snapshot_history else None

    def get_snapshot_history(self, n: int = 60) -> list[SystemSnapshot]:
        return self._snapshot_history[-n:]

    def get_module_latency_history(self,
                                    module: str,
                                    n: int = 100) -> list[float]:
        m = self._collector.get_metrics(module)
        if m is None:
            return []
        return list(m._latency_buf)[-n:]

    def summary(self) -> dict:
        snap = self.get_latest_snapshot()
        if snap is None:
            return {"health_score": 100.0, "snapshots": 0}
        return {
            "health_score":      snap.health_score,
            "system_throughput": snap.system_throughput,
            "avg_latency_ms":    snap.avg_latency_ms,
            "system_error_rate": snap.system_error_rate,
            "active_count":      snap.active_count,
            "offline_count":     snap.offline_count,
            "snapshots":         len(self._snapshot_history),
        }
