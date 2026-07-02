"""
alpha_factory_2/engine/lifecycle_engine.py  (Phase 5)

LifecycleEngine — Alpha 生命周期管理引擎。

生命周期：
    Generated → Scored → Screened → Live → Degraded → Retired
                                  ↘ Rejected

合法迁移表（VALID_TRANSITIONS）：
    Generated  → Scored, Rejected
    Scored     → Screened, Rejected
    Screened   → Live, Rejected
    Live       → Degraded, Retired
    Degraded   → Live, Retired
    Rejected   → (terminal)
    Retired    → (terminal)

自动迁移规则（auto_evaluate）：
    Screened  → Live            若评分 >= live_score_threshold
    Live      → Degraded        若评分下降超过 degrade_delta
    Live      → Retired         若 IC 连续下降超过 retire_streak
    Degraded  → Retired         若已在 Degraded 状态超过 max_degrade_days
    Degraded  → Live            若评分恢复超过 recover_delta

❌ 不执行任何交易逻辑
✔  仅维护状态，广播 EVENT_ALPHA_LIVE / EVENT_ALPHA_RETIRED
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from ..constant import AlphaStatus
from ..model.lifecycle_model import AlphaLifecycle, LifecycleEvent
from ..model.alpha_model import AlphaSignal
from ..model.score_model import AlphaScore


# ─────────────────────────────────────────────────────────────────────────────
#  合法迁移表
# ─────────────────────────────────────────────────────────────────────────────

VALID_TRANSITIONS: dict[AlphaStatus, set[AlphaStatus]] = {
    AlphaStatus.GENERATED: {AlphaStatus.SCORED,    AlphaStatus.REJECTED},
    AlphaStatus.SCORED:    {AlphaStatus.SCREENED,  AlphaStatus.REJECTED},
    AlphaStatus.SCREENED:  {AlphaStatus.LIVE,      AlphaStatus.REJECTED},
    AlphaStatus.LIVE:      {AlphaStatus.DEGRADED,  AlphaStatus.RETIRED},
    AlphaStatus.DEGRADED:  {AlphaStatus.LIVE,      AlphaStatus.RETIRED},
    AlphaStatus.REJECTED:  set(),   # terminal
    AlphaStatus.RETIRED:   set(),   # terminal
}


# ─────────────────────────────────────────────────────────────────────────────
#  自动迁移阈值配置
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LifecycleThresholds:
    live_score_threshold: float = 0.25    # Screened → Live 的最低评分
    degrade_delta:        float = 0.10    # 评分下降超过此值 → Degraded
    recover_delta:        float = 0.08    # 评分恢复超过此值 → Live
    retire_ic_threshold:  float = -0.03   # IC 低于此值计入低 IC 连续计数
    retire_streak:        int   = 3       # 连续低 IC 期数触发退役
    max_degrade_days:     int   = 30      # Degraded 状态超过此天数强制退役


# ─────────────────────────────────────────────────────────────────────────────
#  LifecycleEngine
# ─────────────────────────────────────────────────────────────────────────────

class LifecycleEngine:
    """
    Alpha 生命周期管理引擎（Phase 5）。

    使用方式：
        le = LifecycleEngine()
        lc = le.register(alpha)
        le.transition(alpha_id, AlphaStatus.SCORED, "scored")
        le.auto_evaluate(alpha, score)   # 自动迁移
    """

    def __init__(
        self,
        thresholds: LifecycleThresholds | None = None,
        log_fn:     Callable | None            = None,
    ) -> None:
        self._t        = thresholds or LifecycleThresholds()
        self._log      = log_fn or (lambda msg: None)
        self._registry: dict[str, AlphaLifecycle] = {}

        # 自动迁移追踪
        # {alpha_id: {"last_score": float, "low_ic_streak": int,
        #             "degraded_at": datetime|None}}
        self._tracker: dict[str, dict] = {}

    # ------------------------------------------------------------------ #
    #  注册
    # ------------------------------------------------------------------ #

    def register(self, alpha: AlphaSignal) -> AlphaLifecycle:
        """注册新 Alpha 进入生命周期。"""
        if alpha.alpha_id in self._registry:
            return self._registry[alpha.alpha_id]
        lc = AlphaLifecycle(alpha_id=alpha.alpha_id)
        self._registry[alpha.alpha_id] = lc
        self._tracker[alpha.alpha_id] = {
            "last_score":    0.0,
            "low_ic_streak": 0,
            "degraded_at":   None,
        }
        self._log(f"[LifecycleEngine] registered {alpha.alpha_id}")
        return lc

    # ------------------------------------------------------------------ #
    #  状态迁移
    # ------------------------------------------------------------------ #

    def transition(
        self,
        alpha_id:   str,
        new_status: AlphaStatus,
        reason:     str = "",
        force:      bool = False,
    ) -> bool:
        """
        执行状态迁移（带合法性校验）。

        Parameters
        ----------
        alpha_id   : Alpha ID
        new_status : 目标状态
        reason     : 迁移原因
        force      : 跳过合法性校验（仅内部使用）

        Returns
        -------
        bool  True = 迁移成功
        """
        lc = self._registry.get(alpha_id)
        if lc is None:
            self._log(f"[LifecycleEngine] transition: {alpha_id} not found")
            return False

        if not force:
            allowed = VALID_TRANSITIONS.get(lc.status, set())
            if new_status not in allowed:
                self._log(
                    f"[LifecycleEngine] INVALID transition "
                    f"{lc.status.value} -> {new_status.value} "
                    f"for {alpha_id}"
                )
                return False

        ev = LifecycleEvent(
            from_status = lc.status,
            to_status   = new_status,
            reason      = reason,
        )
        lc.events.append(ev)
        lc.status = new_status

        if new_status == AlphaStatus.RETIRED:
            lc.retired_at = datetime.now()

        self._log(
            f"[LifecycleEngine] {alpha_id}: "
            f"{ev.from_status.value} -> {new_status.value}  [{reason}]"
        )
        return True

    # ------------------------------------------------------------------ #
    #  自动迁移评估
    # ------------------------------------------------------------------ #

    def auto_evaluate(
        self,
        alpha: AlphaSignal,
        score: AlphaScore,
    ) -> AlphaStatus | None:
        """
        根据最新评分自动评估是否需要状态迁移。

        规则：
          Screened  → Live      若 total_score >= live_score_threshold
          Live      → Degraded  若 total_score 下降 >= degrade_delta
          Degraded  → Live      若 total_score 恢复 >= recover_delta
          Live/Degraded → Retired  若连续 retire_streak 次 IC < threshold
          Degraded  → Retired   若已在 Degraded 状态 >= max_degrade_days

        Returns
        -------
        AlphaStatus | None  发生了迁移则返回新状态，否则 None
        """
        lc = self._registry.get(alpha.alpha_id)
        if lc is None:
            return None

        tr = self._tracker.setdefault(alpha.alpha_id, {
            "last_score":    0.0,
            "low_ic_streak": 0,
            "degraded_at":   None,
        })
        t         = self._t
        cur_score = score.total_score
        cur_ic    = score.ic
        last_score = tr["last_score"]
        status     = lc.status

        # 更新低 IC 连续计数
        if cur_ic < t.retire_ic_threshold:
            tr["low_ic_streak"] += 1
        else:
            tr["low_ic_streak"] = 0

        new_status: AlphaStatus | None = None

        if status == AlphaStatus.SCREENED:
            if cur_score >= t.live_score_threshold:
                new_status = AlphaStatus.LIVE
                reason = f"score {cur_score:.4f} >= {t.live_score_threshold} → LIVE"
            else:
                reason = f"score {cur_score:.4f} < {t.live_score_threshold}, stay SCREENED"

        elif status == AlphaStatus.LIVE:
            # 退役优先检查
            if tr["low_ic_streak"] >= t.retire_streak:
                new_status = AlphaStatus.RETIRED
                reason = (
                    f"连续 {tr['low_ic_streak']} 次 IC "
                    f"< {t.retire_ic_threshold} → RETIRED"
                )
            elif last_score > 0 and (last_score - cur_score) >= t.degrade_delta:
                new_status = AlphaStatus.DEGRADED
                tr["degraded_at"] = datetime.now()
                reason = (
                    f"score 下降 {last_score - cur_score:.4f} "
                    f">= {t.degrade_delta} → DEGRADED"
                )

        elif status == AlphaStatus.DEGRADED:
            # 退役优先检查
            if tr["low_ic_streak"] >= t.retire_streak:
                new_status = AlphaStatus.RETIRED
                reason = (
                    f"连续 {tr['low_ic_streak']} 次 IC "
                    f"< {t.retire_ic_threshold} → RETIRED (from DEGRADED)"
                )
            elif tr["degraded_at"] is not None:
                days_degraded = (
                    datetime.now() - tr["degraded_at"]
                ).total_seconds() / 86400
                if days_degraded >= t.max_degrade_days:
                    new_status = AlphaStatus.RETIRED
                    reason = (
                        f"Degraded {days_degraded:.1f}天 "
                        f">= {t.max_degrade_days}天 → RETIRED"
                    )
            if new_status is None and last_score > 0:
                if (cur_score - last_score) >= t.recover_delta:
                    new_status = AlphaStatus.LIVE
                    tr["degraded_at"] = None
                    reason = (
                        f"score 恢复 {cur_score - last_score:.4f} "
                        f">= {t.recover_delta} → LIVE"
                    )

        tr["last_score"] = cur_score

        if new_status is not None:
            self.transition(alpha.alpha_id, new_status, reason)

        return new_status

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_lifecycle(self, alpha_id: str) -> AlphaLifecycle | None:
        return self._registry.get(alpha_id)

    def list_by_status(self, status: AlphaStatus) -> list[AlphaLifecycle]:
        return [lc for lc in self._registry.values() if lc.status == status]

    def get_all(self) -> list[AlphaLifecycle]:
        return list(self._registry.values())

    def get_timeline(
        self,
        alpha_id: str,
    ) -> list[dict]:
        """返回单个 Alpha 的完整迁移时间轴。"""
        lc = self._registry.get(alpha_id)
        if lc is None:
            return []
        return [
            {
                "from": ev.from_status.value,
                "to":   ev.to_status.value,
                "reason": ev.reason,
                "ts":   str(ev.ts)[:19],
            }
            for ev in lc.events
        ]

    def update_thresholds(self, **kwargs) -> None:
        """动态更新自动迁移阈值。"""
        for k, v in kwargs.items():
            if hasattr(self._t, k):
                setattr(self._t, k, v)
                self._log(f"[LifecycleEngine] threshold updated: {k}={v}")

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for lc in self._registry.values():
            counts[lc.status.value] = counts.get(lc.status.value, 0) + 1
        total = len(self._registry)
        live  = counts.get(AlphaStatus.LIVE.value, 0)
        return {
            "total":     total,
            "live":      live,
            "by_status": counts,
        }
