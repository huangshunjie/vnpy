"""
quant_os/engine/lifecycle_manager.py

LifecycleManager — Alpha / Strategy 生命周期管理引擎（Phase 3 实现）。

职责：
  - 创建 / 查询 AlphaLifecycle / StrategyLifecycle
  - 校验并执行状态流转（ALPHA_TRANSITIONS / STRATEGY_TRANSITIONS）
  - 记录每次状态变更历史
  - 发布 EVENT_LIFECYCLE_CHANGE 事件

❌ 不允许调用交易执行逻辑
❌ 不允许修改模块内部逻辑
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Callable

from ..model.lifecycle_model import (
    AlphaLifecycle,
    AlphaState,
    StrategyLifecycle,
    StrategyState,
    StateTransitionRecord,
    ALPHA_TRANSITIONS,
    STRATEGY_TRANSITIONS,
)
from ..event import EVENT_LIFECYCLE_CHANGE


class LifecycleManager:
    """
    生命周期管理器（Phase 3）。

    使用方式：
        mgr = LifecycleManager(event_publish_fn)
        alpha_id = mgr.create_alpha("my_factor")
        mgr.advance_alpha(alpha_id, AlphaState.VALIDATED, reason="IC > 0.05")
    """

    def __init__(self, event_publish_fn: Callable) -> None:
        """
        Parameters
        ----------
        event_publish_fn : (event_type: str, data: dict) -> None
                           用于向 EventBus / VeighNa EventEngine 发布事件。
        """
        self._publish = event_publish_fn
        self._alphas:     dict[str, AlphaLifecycle]    = {}
        self._strategies: dict[str, StrategyLifecycle] = {}

    # ------------------------------------------------------------------ #
    #  Alpha 生命周期
    # ------------------------------------------------------------------ #

    def create_alpha(
        self,
        factor_name:      str,
        *,
        alpha_id:         str | None = None,
        validation_score: float      = 0.0,
        notes:            str        = "",
        tags:             list[str] | None = None,
    ) -> str:
        """
        创建 Alpha 生命周期记录，初始状态为 GENERATED。

        Returns
        -------
        str  alpha_id
        """
        aid = alpha_id or str(uuid.uuid4())[:12]
        if aid in self._alphas:
            return aid

        alpha = AlphaLifecycle(
            alpha_id         = aid,
            factor_name      = factor_name,
            state            = AlphaState.GENERATED,
            validation_score = validation_score,
            notes            = notes,
            tags             = tags or [],
        )
        self._alphas[aid] = alpha
        self._publish(EVENT_LIFECYCLE_CHANGE, {
            "entity":    "alpha",
            "id":        aid,
            "name":      factor_name,
            "old_state": "",
            "new_state": AlphaState.GENERATED.value,
            "reason":    "alpha created",
        })
        return aid

    def advance_alpha(
        self,
        alpha_id:  str,
        new_state: AlphaState | str,
        *,
        reason:    str = "",
        score:     float | None = None,
    ) -> bool:
        """
        推进 Alpha 状态（校验合法转换）。

        Parameters
        ----------
        alpha_id  : Alpha 标识符
        new_state : 目标状态
        reason    : 转换原因（记录到历史）
        score     : 可选更新 validation_score

        Returns
        -------
        bool  True = 转换成功，False = 非法或不存在
        """
        alpha = self._alphas.get(alpha_id)
        if alpha is None:
            return False

        if isinstance(new_state, str):
            try:
                new_state = AlphaState(new_state)
            except ValueError:
                return False

        allowed = ALPHA_TRANSITIONS.get(alpha.state, set())
        if new_state not in allowed:
            return False

        old_state  = alpha.state
        alpha.state      = new_state
        alpha.updated_at = datetime.now()

        if score is not None:
            alpha.validation_score = score

        # 设置关键时间戳
        if new_state == AlphaState.VALIDATED:
            alpha.validated_at  = datetime.now()
            alpha.is_validated  = True
        elif new_state == AlphaState.LIVE:
            alpha.live_at = datetime.now()
        elif new_state == AlphaState.RETIRED:
            alpha.retired_at = datetime.now()

        # 记录历史
        alpha.history.append(StateTransitionRecord(
            from_state = old_state.value,
            to_state   = new_state.value,
            reason     = reason,
        ))

        self._publish(EVENT_LIFECYCLE_CHANGE, {
            "entity":    "alpha",
            "id":        alpha_id,
            "name":      alpha.factor_name,
            "old_state": old_state.value,
            "new_state": new_state.value,
            "reason":    reason,
        })
        return True

    def retire_alpha(self, alpha_id: str, reason: str = "手动退役") -> bool:
        """退役 Alpha（任意状态 → RETIRED，绕过状态机，视为强制退役）。"""
        alpha = self._alphas.get(alpha_id)
        if alpha is None or alpha.state == AlphaState.RETIRED:
            return False
        old = alpha.state
        alpha.state      = AlphaState.RETIRED
        alpha.retired_at = datetime.now()
        alpha.updated_at = datetime.now()
        alpha.history.append(StateTransitionRecord(
            from_state = old.value,
            to_state   = AlphaState.RETIRED.value,
            reason     = reason,
        ))
        self._publish(EVENT_LIFECYCLE_CHANGE, {
            "entity":    "alpha",
            "id":        alpha_id,
            "name":      alpha.factor_name,
            "old_state": old.value,
            "new_state": AlphaState.RETIRED.value,
            "reason":    reason,
        })
        return True

    # ------------------------------------------------------------------ #
    #  Strategy 生命周期
    # ------------------------------------------------------------------ #

    def create_strategy(
        self,
        strategy_name: str,
        *,
        strategy_id:      str | None = None,
        alpha_id:         str        = "",
        backtest_sharpe:  float      = 0.0,
        backtest_ic:      float      = 0.0,
        notes:            str        = "",
        tags:             list[str] | None = None,
    ) -> str:
        """
        创建 Strategy 生命周期记录，初始状态为 BACKTEST。

        Returns
        -------
        str  strategy_id
        """
        sid = strategy_id or str(uuid.uuid4())[:12]
        if sid in self._strategies:
            return sid

        strat = StrategyLifecycle(
            strategy_id    = sid,
            strategy_name  = strategy_name,
            state          = StrategyState.BACKTEST,
            alpha_id       = alpha_id,
            backtest_sharpe = backtest_sharpe,
            backtest_ic    = backtest_ic,
            notes          = notes,
            tags           = tags or [],
        )
        self._strategies[sid] = strat
        self._publish(EVENT_LIFECYCLE_CHANGE, {
            "entity":    "strategy",
            "id":        sid,
            "name":      strategy_name,
            "old_state": "",
            "new_state": StrategyState.BACKTEST.value,
            "reason":    "strategy created",
        })
        return sid

    def advance_strategy(
        self,
        strategy_id: str,
        new_state:   StrategyState | str,
        *,
        reason:      str   = "",
        live_sharpe: float | None = None,
    ) -> bool:
        """
        推进 Strategy 状态（校验合法转换）。

        Returns
        -------
        bool  True = 成功，False = 非法或不存在
        """
        strat = self._strategies.get(strategy_id)
        if strat is None:
            return False

        if isinstance(new_state, str):
            try:
                new_state = StrategyState(new_state)
            except ValueError:
                return False

        allowed = STRATEGY_TRANSITIONS.get(strat.state, set())
        if new_state not in allowed:
            return False

        old_state   = strat.state
        strat.state       = new_state
        strat.updated_at  = datetime.now()

        if live_sharpe is not None:
            strat.live_sharpe = live_sharpe

        if new_state == StrategyState.PAPER:
            strat.paper_at    = datetime.now()
        elif new_state == StrategyState.LIVE:
            strat.live_at     = datetime.now()
        elif new_state == StrategyState.DISABLED:
            strat.disabled_at = datetime.now()

        strat.history.append(StateTransitionRecord(
            from_state = old_state.value,
            to_state   = new_state.value,
            reason     = reason,
        ))

        self._publish(EVENT_LIFECYCLE_CHANGE, {
            "entity":    "strategy",
            "id":        strategy_id,
            "name":      strat.strategy_name,
            "old_state": old_state.value,
            "new_state": new_state.value,
            "reason":    reason,
        })
        return True

    def disable_strategy(self, strategy_id: str, reason: str = "手动禁用") -> bool:
        """强制禁用策略（任意状态 → DISABLED）。"""
        strat = self._strategies.get(strategy_id)
        if strat is None or strat.state == StrategyState.DISABLED:
            return False
        old = strat.state
        strat.state       = StrategyState.DISABLED
        strat.disabled_at = datetime.now()
        strat.updated_at  = datetime.now()
        strat.history.append(StateTransitionRecord(
            from_state = old.value,
            to_state   = StrategyState.DISABLED.value,
            reason     = reason,
        ))
        self._publish(EVENT_LIFECYCLE_CHANGE, {
            "entity":    "strategy",
            "id":        strategy_id,
            "name":      strat.strategy_name,
            "old_state": old.value,
            "new_state": StrategyState.DISABLED.value,
            "reason":    reason,
        })
        return True

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_alpha(self, alpha_id: str) -> AlphaLifecycle | None:
        return self._alphas.get(alpha_id)

    def get_strategy(self, strategy_id: str) -> StrategyLifecycle | None:
        return self._strategies.get(strategy_id)

    def get_all_alphas(self) -> list[AlphaLifecycle]:
        return list(self._alphas.values())

    def get_all_strategies(self) -> list[StrategyLifecycle]:
        return list(self._strategies.values())

    def get_alphas_by_state(self, state: AlphaState | str) -> list[AlphaLifecycle]:
        if isinstance(state, str):
            state = AlphaState(state)
        return [a for a in self._alphas.values() if a.state == state]

    def get_strategies_by_state(self, state: StrategyState | str) -> list[StrategyLifecycle]:
        if isinstance(state, str):
            state = StrategyState(state)
        return [s for s in self._strategies.values() if s.state == state]

    def get_strategies_for_alpha(self, alpha_id: str) -> list[StrategyLifecycle]:
        return [s for s in self._strategies.values() if s.alpha_id == alpha_id]

    def summary(self) -> dict:
        alphas     = list(self._alphas.values())
        strategies = list(self._strategies.values())
        return {
            "alpha": {
                "total":     len(alphas),
                "by_state":  {s.value: sum(1 for a in alphas if a.state == s)
                               for s in AlphaState},
            },
            "strategy": {
                "total":     len(strategies),
                "by_state":  {s.value: sum(1 for st in strategies if st.state == s)
                               for s in StrategyState},
            },
        }

    @property
    def alpha_count(self) -> int:
        return len(self._alphas)

    @property
    def strategy_count(self) -> int:
        return len(self._strategies)

    @property
    def live_alpha_count(self) -> int:
        return sum(1 for a in self._alphas.values() if a.state == AlphaState.LIVE)

    @property
    def live_strategy_count(self) -> int:
        return sum(1 for s in self._strategies.values() if s.state == StrategyState.LIVE)
