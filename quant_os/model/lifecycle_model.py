"""
quant_os/model/lifecycle_model.py

AlphaLifecycle / StrategyLifecycle — 生命周期数据模型（Phase 3）。

Alpha 生命周期：
    Generated → Validated → Live → Degraded → Retired

Strategy 生命周期：
    Backtest → PaperTrading → LiveTrading → Disabled
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
#  枚举
# ─────────────────────────────────────────────────────────────────────────────

class AlphaState(str, Enum):
    GENERATED = "generated"
    VALIDATED = "validated"
    LIVE      = "live"
    DEGRADED  = "degraded"
    RETIRED   = "retired"


class StrategyState(str, Enum):
    BACKTEST     = "backtest"
    PAPER        = "paper_trading"
    LIVE         = "live_trading"
    DISABLED     = "disabled"


# ─────────────────────────────────────────────────────────────────────────────
#  合法状态转换表
# ─────────────────────────────────────────────────────────────────────────────

ALPHA_TRANSITIONS: dict[AlphaState, set[AlphaState]] = {
    AlphaState.GENERATED: {AlphaState.VALIDATED, AlphaState.RETIRED},
    AlphaState.VALIDATED: {AlphaState.LIVE,      AlphaState.RETIRED},
    AlphaState.LIVE:      {AlphaState.DEGRADED,  AlphaState.RETIRED},
    AlphaState.DEGRADED:  {AlphaState.LIVE,      AlphaState.RETIRED},
    AlphaState.RETIRED:   set(),
}

STRATEGY_TRANSITIONS: dict[StrategyState, set[StrategyState]] = {
    StrategyState.BACKTEST: {StrategyState.PAPER,    StrategyState.DISABLED},
    StrategyState.PAPER:    {StrategyState.LIVE,     StrategyState.BACKTEST, StrategyState.DISABLED},
    StrategyState.LIVE:     {StrategyState.PAPER,    StrategyState.DISABLED},
    StrategyState.DISABLED: {StrategyState.BACKTEST, StrategyState.PAPER},
}


# ─────────────────────────────────────────────────────────────────────────────
#  数据模型
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StateTransitionRecord:
    """单次状态转换历史记录。"""
    from_state: str      = ""
    to_state:   str      = ""
    reason:     str      = ""
    ts:         datetime = field(default_factory=datetime.now)

    def to_line(self) -> str:
        return f"[{str(self.ts)[:19]}] {self.from_state} → {self.to_state}  {self.reason}"


@dataclass
class AlphaLifecycle:
    """
    Alpha 因子生命周期记录。

    一个 alpha_id 对应一个 AlphaLifecycle 实例，
    由 LifecycleManager 统一管理状态流转。
    """
    alpha_id:    str        = ""
    factor_name: str        = ""
    state:       AlphaState = AlphaState.GENERATED

    created_at:  datetime   = field(default_factory=datetime.now)
    updated_at:  datetime   = field(default_factory=datetime.now)

    # 关键时间戳
    validated_at: datetime | None = None
    live_at:      datetime | None = None
    retired_at:   datetime | None = None

    # 退化触发条件（由 Phase 4 Orchestrator 设置）
    ic_threshold:  float = 0.01    # IC 低于此值触发 Degraded
    ic_window:     int   = 60      # 评估窗口期数

    # 验证得分（来自 ValidationEngine）
    validation_score: float = 0.0
    is_validated:     bool  = False

    # 备注
    notes:  str = ""
    tags:   list[str] = field(default_factory=list)

    # 状态历史
    history: list[StateTransitionRecord] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        return self.state in (AlphaState.LIVE, AlphaState.DEGRADED)

    @property
    def is_retired(self) -> bool:
        return self.state == AlphaState.RETIRED

    @property
    def age_days(self) -> float:
        return (datetime.now() - self.created_at).total_seconds() / 86400

    def to_dict(self) -> dict:
        return {
            "alpha_id":         self.alpha_id,
            "factor_name":      self.factor_name,
            "state":            self.state.value,
            "created_at":       str(self.created_at)[:19],
            "updated_at":       str(self.updated_at)[:19],
            "validation_score": self.validation_score,
            "is_validated":     self.is_validated,
            "age_days":         round(self.age_days, 1),
            "notes":            self.notes,
        }


@dataclass
class StrategyLifecycle:
    """
    Strategy 生命周期记录。

    一个 strategy_id 对应一个 StrategyLifecycle 实例。
    """
    strategy_id:   str           = ""
    strategy_name: str           = ""
    state:         StrategyState = StrategyState.BACKTEST

    created_at:    datetime      = field(default_factory=datetime.now)
    updated_at:    datetime      = field(default_factory=datetime.now)

    # 关键时间戳
    paper_at:      datetime | None = None
    live_at:       datetime | None = None
    disabled_at:   datetime | None = None

    # 回测统计（由 Phase 4 Orchestrator 填充）
    backtest_sharpe: float = 0.0
    backtest_ic:     float = 0.0
    live_sharpe:     float = 0.0

    # 关联的 alpha_id
    alpha_id:  str  = ""
    notes:     str  = ""
    tags:      list[str] = field(default_factory=list)

    # 状态历史
    history: list[StateTransitionRecord] = field(default_factory=list)

    @property
    def is_live(self) -> bool:
        return self.state == StrategyState.LIVE

    @property
    def is_active(self) -> bool:
        return self.state in (StrategyState.PAPER, StrategyState.LIVE)

    def to_dict(self) -> dict:
        return {
            "strategy_id":     self.strategy_id,
            "strategy_name":   self.strategy_name,
            "state":           self.state.value,
            "created_at":      str(self.created_at)[:19],
            "updated_at":      str(self.updated_at)[:19],
            "backtest_sharpe": self.backtest_sharpe,
            "live_sharpe":     self.live_sharpe,
            "alpha_id":        self.alpha_id,
            "notes":           self.notes,
        }
