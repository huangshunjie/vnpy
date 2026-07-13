"""
live_production/engine/failover_engine.py  (Phase 4)

FailoverEngine — 故障切换引擎。

职责：
  1. 维护降级模式状态机：FULL → PARTIAL → SAFE_MODE
  2. 风控接管：触发后广播停止执行事件，Risk Engine 接管
  3. 自动降级：检测到异常自动降级，记录原因
  4. 降级恢复：问题消除后逐步恢复至 FULL

❌ 不直接调用 Execution / Risk / Portfolio
✔  通过 EventEngine 广播事件，各模块自行响应
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable

from ..constant import FailoverMode, TradingState
from ..event import EVENT_FAILOVER_TRIGGER


class FailoverReason(str, Enum):
    EXECUTION_ERROR   = "execution_error"
    RISK_BREACH       = "risk_breach"
    CONNECTIVITY_LOSS = "connectivity_loss"
    DATA_ANOMALY      = "data_anomaly"
    MANUAL            = "manual"
    AUTO_RECOVERY     = "auto_recovery"


@dataclass
class FailoverRecord:
    record_id:   str
    from_mode:   FailoverMode
    to_mode:     FailoverMode
    reason:      FailoverReason
    detail:      str      = ""
    ts:          datetime = field(default_factory=datetime.now)
    risk_takeover: bool   = False   # 是否触发了风控接管

    def to_dict(self) -> dict:
        return {
            "record_id":     self.record_id,
            "from_mode":     self.from_mode.value,
            "to_mode":       self.to_mode.value,
            "reason":        self.reason.value,
            "detail":        self.detail,
            "ts":            str(self.ts)[:19],
            "risk_takeover": self.risk_takeover,
        }


# 合法降级路径
_DOWNGRADE: dict[FailoverMode, FailoverMode] = {
    FailoverMode.FULL:     FailoverMode.PARTIAL,
    FailoverMode.PARTIAL:  FailoverMode.SAFE_MODE,
}
# 合法恢复路径
_UPGRADE: dict[FailoverMode, FailoverMode] = {
    FailoverMode.SAFE_MODE: FailoverMode.PARTIAL,
    FailoverMode.PARTIAL:   FailoverMode.FULL,
}


class FailoverEngine:
    """故障切换引擎（Phase 4）。"""

    def __init__(
        self,
        event_publish_fn: Callable,
        log_fn:           Callable,
        state_manager=None,
    ) -> None:
        self._publish       = event_publish_fn
        self._log           = log_fn
        self._state_manager = state_manager

        self._mode    = FailoverMode.FULL
        self._lock    = threading.Lock()
        self._records: list[FailoverRecord] = []
        self._max_records = 200

        self._risk_takeover_active = False

    # ------------------------------------------------------------------ #
    #  降级操作
    # ------------------------------------------------------------------ #

    def downgrade(
        self,
        reason: FailoverReason = FailoverReason.MANUAL,
        detail: str = "",
        force_safe: bool = False,
    ) -> bool:
        """
        降级一步（FULL→PARTIAL 或 PARTIAL→SAFE_MODE）。

        force_safe=True 时直接跳至 SAFE_MODE（用于严重故障）。
        """
        with self._lock:
            if force_safe:
                return self._do_switch(
                    self._mode, FailoverMode.SAFE_MODE, reason, detail
                )
            next_mode = _DOWNGRADE.get(self._mode)
            if next_mode is None:
                self._log(f"[Failover] Already at lowest mode: {self._mode.value}")
                return False
            return self._do_switch(self._mode, next_mode, reason, detail)

    def upgrade(
        self,
        reason: FailoverReason = FailoverReason.AUTO_RECOVERY,
        detail: str = "",
    ) -> bool:
        """恢复一步（SAFE_MODE→PARTIAL 或 PARTIAL→FULL）。"""
        with self._lock:
            next_mode = _UPGRADE.get(self._mode)
            if next_mode is None:
                self._log(f"[Failover] Already at highest mode: {self._mode.value}")
                return False
            return self._do_switch(self._mode, next_mode, reason, detail)

    def upgrade_full(
        self,
        reason: FailoverReason = FailoverReason.AUTO_RECOVERY,
        detail: str = "",
    ) -> bool:
        """直接恢复到 FULL（两步合并）。"""
        changed = False
        while self._mode != FailoverMode.FULL:
            ok = self.upgrade(reason, detail)
            if not ok:
                break
            changed = True
        return changed

    # ------------------------------------------------------------------ #
    #  风控接管
    # ------------------------------------------------------------------ #

    def trigger_risk_takeover(self, detail: str = "") -> bool:
        """
        触发风控接管：
          1. 强制降级至 SAFE_MODE
          2. 广播 risk_takeover 事件（Risk Engine 订阅后接管）
          3. 通知 StateManager 进入 DEGRADED
        """
        self._log(f"[Failover][RISK TAKEOVER] {detail}")

        self.downgrade(
            reason      = FailoverReason.RISK_BREACH,
            detail      = detail,
            force_safe  = True,
        )
        self._risk_takeover_active = True

        self._publish("eLiveProd.failover.risk_takeover", {
            "mode":   FailoverMode.SAFE_MODE.value,
            "detail": detail,
        })

        if self._state_manager:
            self._state_manager.mark_degraded(
                f"风控接管: {detail}",
                trigger="risk_takeover",
            )
        return True

    def release_risk_takeover(self, detail: str = "") -> bool:
        """解除风控接管，逐步恢复至 FULL。"""
        if not self._risk_takeover_active:
            return False
        self._risk_takeover_active = False
        self.upgrade_full(
            reason = FailoverReason.AUTO_RECOVERY,
            detail = detail or "风控接管解除",
        )
        self._publish("eLiveProd.failover.risk_released", {
            "mode":   self._mode.value,
            "detail": detail,
        })
        return True

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    @property
    def mode(self) -> FailoverMode:
        return self._mode

    @property
    def is_risk_takeover(self) -> bool:
        return self._risk_takeover_active

    @property
    def is_safe_mode(self) -> bool:
        return self._mode == FailoverMode.SAFE_MODE

    def get_records(self, limit: int = 100) -> list[FailoverRecord]:
        return self._records[-limit:]

    def summary(self) -> dict:
        total     = len(self._records)
        downgrades = sum(1 for r in self._records
                         if _DOWNGRADE.get(r.from_mode) == r.to_mode
                         or r.to_mode == FailoverMode.SAFE_MODE)
        return {
            "mode":             self._mode.value,
            "risk_takeover":    self._risk_takeover_active,
            "total_switches":   total,
            "downgrades":       downgrades,
            "upgrades":         total - downgrades,
        }

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    def _do_switch(
        self,
        from_mode: FailoverMode,
        to_mode:   FailoverMode,
        reason:    FailoverReason,
        detail:    str,
    ) -> bool:
        import uuid
        risk_takeover = (
            to_mode == FailoverMode.SAFE_MODE
            and reason == FailoverReason.RISK_BREACH
        )
        rec = FailoverRecord(
            record_id    = uuid.uuid4().hex[:8].upper(),
            from_mode    = from_mode,
            to_mode      = to_mode,
            reason       = reason,
            detail       = detail,
            risk_takeover = risk_takeover,
        )
        self._mode = to_mode
        self._records.append(rec)
        if len(self._records) > self._max_records:
            self._records.pop(0)

        direction = "DOWNGRADE" if _DOWNGRADE.get(from_mode) == to_mode or (
            to_mode == FailoverMode.SAFE_MODE and from_mode != FailoverMode.SAFE_MODE
        ) else "UPGRADE"

        self._log(
            f"[Failover] {direction}  {from_mode.value} -> {to_mode.value}"
            f"  reason={reason.value}  {detail}"
        )
        self._publish(EVENT_FAILOVER_TRIGGER, {
            "record_id": rec.record_id,
            "from_mode": from_mode.value,
            "to_mode":   to_mode.value,
            "reason":    reason.value,
            "detail":    detail,
        })
        return True
