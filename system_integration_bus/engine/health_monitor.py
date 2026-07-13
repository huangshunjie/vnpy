"""
system_integration_bus/engine/health_monitor.py

HealthMonitor — 子引擎健康监控。

职责：
  - 追踪每个子引擎的心跳与消息活跃度
  - 检测引擎超时（长时间无消息 → DEGRADED / OFFLINE）
  - 发出健康状态变化通知
  - 维护全局健康快照
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Callable

from ..constant import HealthStatus, BusChannel
from ..model.bus_model import EngineHealthRecord


# ── 各模块的超时阈值 (秒) ────────────────────────────────────────────
_TIMEOUT_MAP: dict[str, float] = {
    "data_intelligence_ai":       60.0,
    "alpha_factory_2":            120.0,
    "market_regime_ai":           60.0,
    "portfolio_engine":           30.0,
    "capital_allocation_ai":      60.0,
    "risk_engine_2":              30.0,
    "strategy_lifecycle_ai":      120.0,
    "execution_engine":           15.0,
    "execution_intelligence_ai":  15.0,
    "adaptive_learning_ai":       300.0,
    "global_portfolio_intelligence": 60.0,
    "live_production":            30.0,
    "quant_os":                   60.0,
}

# ── Channel → module name ────────────────────────────────────────────
_CHANNEL_MODULE: dict[BusChannel, str] = {
    BusChannel.DATA_INTELLIGENCE: "data_intelligence_ai",
    BusChannel.ALPHA:             "alpha_factory_2",
    BusChannel.REGIME:            "market_regime_ai",
    BusChannel.PORTFOLIO:         "portfolio_engine",
    BusChannel.CAPITAL:           "capital_allocation_ai",
    BusChannel.RISK:              "risk_engine_2",
    BusChannel.STRATEGY_LIFECYCLE:"strategy_lifecycle_ai",
    BusChannel.EXECUTION:         "execution_engine",
    BusChannel.EXECUTION_INTEL:   "execution_intelligence_ai",
    BusChannel.LEARNING:          "adaptive_learning_ai",
}


class HealthMonitor:
    """子引擎健康监控器。"""

    def __init__(
        self,
        on_status_change: Callable | None = None,  # (record: EngineHealthRecord) → None
        log_fn:           Callable | None = None,
    ) -> None:
        self._on_change = on_status_change or (lambda r: None)
        self._log       = log_fn or (lambda m: None)

        # {module_name: EngineHealthRecord}
        self._records: dict[str, EngineHealthRecord] = {}
        self._init_records()

    def _init_records(self) -> None:
        for mod in _TIMEOUT_MAP:
            self._records[mod] = EngineHealthRecord(
                engine_name = mod,
                module      = mod,
                status      = HealthStatus.UNKNOWN,
                last_seen   = datetime.now(),
            )

    # ── pulse (called by ChannelRouter on every message) ─────────────
    def pulse(self, module: str, latency_ms: float = 0.0) -> None:
        """记录一次来自 module 的消息（心跳更新）。"""
        rec = self._records.get(module)
        if rec is None:
            rec = EngineHealthRecord(engine_name=module, module=module)
            self._records[module] = rec

        prev_status = rec.status
        rec.last_seen     = datetime.now()
        rec.message_count += 1
        rec.latency_ms    = latency_ms
        rec.status        = HealthStatus.HEALTHY

        if prev_status != HealthStatus.HEALTHY:
            self._log(f"[HealthMonitor] {module} → HEALTHY (recovered)")
            self._on_change(rec)

    def record_error(self, module: str) -> None:
        rec = self._records.get(module)
        if rec:
            rec.error_count += 1

    # ── periodic check ────────────────────────────────────────────────
    def check_all(self) -> list[EngineHealthRecord]:
        """
        遍历所有记录，根据最后活跃时间更新健康状态。
        应定期调用（如每 10 秒）。
        """
        changed = []
        now = datetime.now()
        for mod, rec in self._records.items():
            timeout = _TIMEOUT_MAP.get(mod, 60.0)
            elapsed = (now - rec.last_seen).total_seconds()

            if rec.status == HealthStatus.UNKNOWN:
                continue   # 尚未收到任何消息

            if elapsed > timeout * 3:
                new_status = HealthStatus.OFFLINE
            elif elapsed > timeout:
                new_status = HealthStatus.DEGRADED
            else:
                new_status = HealthStatus.HEALTHY

            if new_status != rec.status:
                rec.status = new_status
                self._log(
                    f"[HealthMonitor] {mod} → {new_status.value} "
                    f"(elapsed={elapsed:.0f}s timeout={timeout:.0f}s)")
                changed.append(rec)
                self._on_change(rec)

        return changed

    # ── channel convenience ───────────────────────────────────────────
    def pulse_channel(self, channel: BusChannel,
                       latency_ms: float = 0.0) -> None:
        mod = _CHANNEL_MODULE.get(channel)
        if mod:
            self.pulse(mod, latency_ms)

    # ── query ─────────────────────────────────────────────────────────
    def get_record(self, module: str) -> EngineHealthRecord | None:
        return self._records.get(module)

    def get_all(self) -> dict[str, EngineHealthRecord]:
        return dict(self._records)

    def get_offline(self) -> list[EngineHealthRecord]:
        return [r for r in self._records.values()
                if r.status == HealthStatus.OFFLINE]

    def get_degraded(self) -> list[EngineHealthRecord]:
        return [r for r in self._records.values()
                if r.status == HealthStatus.DEGRADED]

    def get_healthy_count(self) -> int:
        return sum(1 for r in self._records.values()
                   if r.status == HealthStatus.HEALTHY)

    def get_online_channels(self) -> set[BusChannel]:
        """返回对应模块 HEALTHY 的 Channel 集合。"""
        online = set()
        for ch, mod in _CHANNEL_MODULE.items():
            rec = self._records.get(mod)
            if rec and rec.status == HealthStatus.HEALTHY:
                online.add(ch)
        return online

    def summary(self) -> dict:
        healthy  = self.get_healthy_count()
        degraded = len(self.get_degraded())
        offline  = len(self.get_offline())
        unknown  = sum(1 for r in self._records.values()
                       if r.status == HealthStatus.UNKNOWN)
        return {
            "total":    len(self._records),
            "healthy":  healthy,
            "degraded": degraded,
            "offline":  offline,
            "unknown":  unknown,
            "details":  {k: v.status.value for k, v in self._records.items()},
        }
