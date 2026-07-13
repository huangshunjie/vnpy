"""
live_production/engine/state_manager.py

TradingStateManager — 交易状态管理器（Phase 2）。

职责：
  - 维护实盘交易状态机（INIT → RUNNING → DEGRADED → RECOVERY → STOPPED）
  - 校验状态转换合法性
  - 记录每次转换的历史
  - 通过 EventEngine 广播 EVENT_STATE_CHANGE

状态转换触发条件（Phase 2 定义，Phase 3/4 实际接入）：
  INIT     → RUNNING    : 系统正常启动
  RUNNING  → DEGRADED   : Execution 异常 / 模块错误
  RUNNING  → STOPPED    : 正常停止
  DEGRADED → RECOVERY   : 风险触发，进入恢复流程
  DEGRADED → RUNNING    : 降级问题消除，恢复正常
  DEGRADED → STOPPED    : 强制停止
  RECOVERY → RUNNING    : 恢复成功
  RECOVERY → STOPPED    : 恢复失败，安全停止
  STOPPED  → INIT       : 重置，准备重新启动

❌ 禁止任何交易 / 下单逻辑
❌ 禁止直接调用 Execution / Risk / Portfolio
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from ..constant import TradingState
from ..event import EVENT_STATE_CHANGE


# ─────────────────────────────────────────────────────────────────────────────
#  合法状态转换表
# ─────────────────────────────────────────────────────────────────────────────

VALID_TRANSITIONS: dict[TradingState, set[TradingState]] = {
    TradingState.INIT:     {TradingState.RUNNING,   TradingState.STOPPED},
    TradingState.RUNNING:  {TradingState.DEGRADED,  TradingState.STOPPED},
    TradingState.DEGRADED: {TradingState.RECOVERY,  TradingState.RUNNING, TradingState.STOPPED},
    TradingState.RECOVERY: {TradingState.RUNNING,   TradingState.STOPPED},
    TradingState.STOPPED:  {TradingState.INIT},
}

# 触发原因分类
TRIGGER_EXECUTION_ERROR  = "execution_error"
TRIGGER_RISK_ALERT       = "risk_alert"
TRIGGER_RECOVERY_SUCCESS = "recovery_success"
TRIGGER_RECOVERY_FAIL    = "recovery_fail"
TRIGGER_MANUAL           = "manual"
TRIGGER_SYSTEM_START     = "system_start"
TRIGGER_SYSTEM_STOP      = "system_stop"
TRIGGER_MODULE_ERROR     = "module_error"
TRIGGER_DEGRADED_CLEAR   = "degraded_clear"


# ─────────────────────────────────────────────────────────────────────────────
#  历史记录
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StateTransition:
    """单次状态转换记录。"""
    from_state: TradingState
    to_state:   TradingState
    trigger:    str = ""
    reason:     str = ""
    ts:         datetime = field(default_factory=datetime.now)

    def to_line(self) -> str:
        return (
            f"[{str(self.ts)[:19]}] "
            f"{self.from_state.value} → {self.to_state.value}"
            f"  trigger={self.trigger}  {self.reason}"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  StateManager
# ─────────────────────────────────────────────────────────────────────────────

class TradingStateManager:
    """
    交易状态管理器（Phase 2）。

    使用方式：
        mgr = TradingStateManager(event_publish_fn, log_fn)
        mgr.start()                          # INIT → RUNNING
        mgr.transition_to(TradingState.DEGRADED,
                          trigger=TRIGGER_EXECUTION_ERROR,
                          reason="CTP 连接断开")
        mgr.transition_to(TradingState.RECOVERY,
                          trigger=TRIGGER_RISK_ALERT)
        mgr.transition_to(TradingState.RUNNING,
                          trigger=TRIGGER_RECOVERY_SUCCESS)
        mgr.stop()                           # → STOPPED
    """

    def __init__(
        self,
        event_publish_fn: Callable,   # (event_type: str, data: dict) -> None
        log_fn:           Callable,   # (msg: str) -> None
    ) -> None:
        self._publish = event_publish_fn
        self._log     = log_fn
        self._state   = TradingState.INIT
        self._lock    = threading.Lock()
        self._history: list[StateTransition] = []
        self._max_history = 500

        # 关键时间戳
        self._started_at:   datetime | None = None
        self._degraded_at:  datetime | None = None
        self._recovery_at:  datetime | None = None
        self._stopped_at:   datetime | None = None

    # ------------------------------------------------------------------ #
    #  快捷方法
    # ------------------------------------------------------------------ #

    def start(self, reason: str = "") -> bool:
        """INIT → RUNNING。"""
        return self.transition_to(
            TradingState.RUNNING,
            trigger=TRIGGER_SYSTEM_START,
            reason=reason or "系统启动",
        )

    def stop(self, reason: str = "") -> bool:
        """任意状态 → STOPPED（强制停止，跳过状态机校验）。"""
        return self._force_stop(reason or "系统停止")

    def mark_degraded(self, reason: str = "", trigger: str = TRIGGER_MODULE_ERROR) -> bool:
        """RUNNING → DEGRADED（模块异常触发）。"""
        return self.transition_to(
            TradingState.DEGRADED,
            trigger=trigger,
            reason=reason,
        )

    def start_recovery(self, reason: str = "") -> bool:
        """DEGRADED → RECOVERY。"""
        return self.transition_to(
            TradingState.RECOVERY,
            trigger=TRIGGER_RISK_ALERT,
            reason=reason or "进入恢复流程",
        )

    def recovery_success(self, reason: str = "") -> bool:
        """RECOVERY → RUNNING。"""
        return self.transition_to(
            TradingState.RUNNING,
            trigger=TRIGGER_RECOVERY_SUCCESS,
            reason=reason or "恢复成功",
        )

    def recovery_fail(self, reason: str = "") -> bool:
        """RECOVERY → STOPPED。"""
        return self.transition_to(
            TradingState.STOPPED,
            trigger=TRIGGER_RECOVERY_FAIL,
            reason=reason or "恢复失败",
        )

    def clear_degraded(self, reason: str = "") -> bool:
        """DEGRADED → RUNNING（降级原因消除）。"""
        return self.transition_to(
            TradingState.RUNNING,
            trigger=TRIGGER_DEGRADED_CLEAR,
            reason=reason or "降级原因消除",
        )

    def reset(self, reason: str = "") -> bool:
        """STOPPED → INIT（准备重启）。"""
        return self.transition_to(
            TradingState.INIT,
            trigger=TRIGGER_MANUAL,
            reason=reason or "系统重置",
        )

    # ------------------------------------------------------------------ #
    #  核心状态转换
    # ------------------------------------------------------------------ #

    def transition_to(
        self,
        new_state: TradingState,
        *,
        trigger: str = TRIGGER_MANUAL,
        reason:  str = "",
    ) -> bool:
        """
        执行状态转换（校验合法性）。

        Parameters
        ----------
        new_state : 目标状态
        trigger   : 触发类型（用于日志和事件）
        reason    : 人类可读的原因描述

        Returns
        -------
        bool  True = 转换成功，False = 非法转换或相同状态
        """
        with self._lock:
            if new_state == self._state:
                return True   # 幂等，视为成功

            allowed = VALID_TRANSITIONS.get(self._state, set())
            if new_state not in allowed:
                self._log(
                    f"[StateManager] 非法转换：{self._state.value} → {new_state.value}"
                    f"  trigger={trigger}  原因={reason}"
                )
                return False

            return self._do_transition(new_state, trigger, reason)

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    @property
    def state(self) -> TradingState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state == TradingState.RUNNING

    @property
    def is_degraded(self) -> bool:
        return self._state == TradingState.DEGRADED

    @property
    def is_in_recovery(self) -> bool:
        return self._state == TradingState.RECOVERY

    @property
    def is_stopped(self) -> bool:
        return self._state == TradingState.STOPPED

    def get_history(self, limit: int = 100) -> list[StateTransition]:
        return self._history[-limit:]

    def get_history_lines(self, limit: int = 100) -> list[str]:
        return [t.to_line() for t in self._history[-limit:]]

    def summary(self) -> dict:
        return {
            "state":        self._state.value,
            "started_at":   str(self._started_at)[:19] if self._started_at else "—",
            "degraded_at":  str(self._degraded_at)[:19] if self._degraded_at else "—",
            "recovery_at":  str(self._recovery_at)[:19] if self._recovery_at else "—",
            "stopped_at":   str(self._stopped_at)[:19] if self._stopped_at else "—",
            "transitions":  len(self._history),
        }

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    def _do_transition(
        self,
        new_state: TradingState,
        trigger:   str,
        reason:    str,
    ) -> bool:
        old_state   = self._state
        self._state = new_state
        now         = datetime.now()

        # 更新关键时间戳
        if new_state == TradingState.RUNNING and self._started_at is None:
            self._started_at  = now
        elif new_state == TradingState.DEGRADED:
            self._degraded_at = now
        elif new_state == TradingState.RECOVERY:
            self._recovery_at = now
        elif new_state == TradingState.STOPPED:
            self._stopped_at  = now

        # 记录历史
        rec = StateTransition(
            from_state = old_state,
            to_state   = new_state,
            trigger    = trigger,
            reason     = reason,
        )
        self._history.append(rec)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # 日志
        self._log(
            f"[StateManager] {old_state.value} → {new_state.value}"
            f"  trigger={trigger}  {reason}"
        )

        # 广播事件
        self._publish(EVENT_STATE_CHANGE, {
            "old_state": old_state.value,
            "new_state": new_state.value,
            "trigger":   trigger,
            "reason":    reason,
            "ts":        str(now)[:19],
        })
        return True

    def _force_stop(self, reason: str) -> bool:
        """强制停止，允许从任意状态转为 STOPPED。"""
        with self._lock:
            if self._state == TradingState.STOPPED:
                return True
            return self._do_transition(TradingState.STOPPED, TRIGGER_SYSTEM_STOP, reason)
