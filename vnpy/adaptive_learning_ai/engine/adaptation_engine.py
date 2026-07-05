"""
adaptive_learning_ai/engine/adaptation_engine.py  (Phase 4)

AdaptationEngine — 参数自适应引擎。

职责：
  - 接收 LearningPattern 列表
  - 生成 AdaptationProposal（三种规则 + 三种更新策略）
  - 应用已批准的 proposal，记录 AdaptationRecord
  - 维护当前参数表与历史变更记录
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable
import uuid

from ..constant import AdaptationTarget, UpdateStrategy, SystemStatus
from ..model.learning_model   import LearningPattern
from ..model.adaptation_model import (
    AdaptationProposal, AdaptationRecord, AdaptationState)
from ..utils.adaptation_utils import (
    patterns_to_proposals, pattern_to_proposal,
    apply_constraints, compute_new_value,
)


class AdaptationEngine:
    """参数自适应引擎（Phase 4 完整实现）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log        = log_fn or (lambda m: None)
        self._status     = SystemStatus.IDLE

        # 当前参数表 {target.value: {entity_id: value}}
        self._params: dict[str, dict[str, float]] = {
            t.value: {} for t in AdaptationTarget}

        self._proposals: list[AdaptationProposal] = []
        self._records:   list[AdaptationRecord]   = []
        self._state      = AdaptationState()

    def init(self)  -> None: self._log("[AdaptationEngine] init()")
    def start(self) -> None:
        self._status = SystemStatus.COLLECTING
        self._log("[AdaptationEngine] start()")

    def stop(self)  -> None:
        self._status = SystemStatus.STOPPED
        self._log("[AdaptationEngine] stop()")

    # ── parameter registry ───────────────────────────────────────────
    def register_param(self, target: AdaptationTarget,
                        entity_id: str, value: float) -> None:
        """注册一个可调参数的初始值。"""
        self._params[target.value][entity_id] = value
        self._log(f"[AdaptationEngine] register {target.value}/{entity_id}={value}")

    def get_param(self, target: AdaptationTarget,
                   entity_id: str) -> float | None:
        return self._params[target.value].get(entity_id)

    def get_all_params(self, target: AdaptationTarget) -> dict[str, float]:
        return dict(self._params[target.value])

    # ── core pipeline ─────────────────────────────────────────────────
    def generate_proposals(
        self,
        patterns:     list[LearningPattern],
        blend_factor: float = 0.3,
    ) -> list[AdaptationProposal]:
        """
        从 LearningPattern 列表生成 AdaptationProposal。

        current_values 从内部参数表查找；未注册则默认 1.0。
        """
        current_values: dict[str, float] = {}
        for p in patterns:
            for eid in (p.entity_ids or [p.target.value]):
                val = self._params[p.target.value].get(eid, 1.0)
                current_values[eid] = val

        proposals = patterns_to_proposals(patterns, current_values, blend_factor)
        proposals = [apply_constraints(pr) for pr in proposals]

        self._proposals.extend(proposals)
        self._update_state()
        self._log(
            f"[AdaptationEngine] generated {len(proposals)} proposals "
            f"from {len(patterns)} patterns")
        return proposals

    def auto_apply(
        self,
        proposals:          list[AdaptationProposal],
        min_confidence:     float = 0.6,
        min_priority_level: int   = 2,   # 1 or 2 → apply; 3 → skip
    ) -> list[AdaptationRecord]:
        """
        自动批准并应用满足条件的 proposal。

        Conditions:
          confidence >= min_confidence  AND
          priority   <= min_priority_level (越小越高)
        """
        records = []
        for prop in proposals:
            if (prop.confidence >= min_confidence
                    and prop.priority <= min_priority_level):
                rec = self._apply_proposal(prop)
                records.append(rec)
        self._update_state()
        return records

    def apply_proposal(self, proposal: AdaptationProposal) -> AdaptationRecord:
        """手动应用单条 proposal。"""
        rec = self._apply_proposal(proposal)
        self._update_state()
        return rec

    def _apply_proposal(self, proposal: AdaptationProposal) -> AdaptationRecord:
        target = proposal.target
        eid    = proposal.entity_id
        cur    = self._params[target.value].get(eid, proposal.current_value)

        success   = True
        error_msg = ""
        try:
            new_val = proposal.proposed_value
            self._params[target.value][eid] = new_val
            proposal.approved = True
        except Exception as e:
            success   = False
            error_msg = str(e)
            new_val   = cur

        rec = AdaptationRecord(
            record_id      = f"REC_{uuid.uuid4().hex[:8].upper()}",
            proposal_id    = proposal.proposal_id,
            target         = target,
            entity_id      = eid,
            dimension      = proposal.dimension,
            value_before   = cur,
            value_after    = new_val,
            actual_delta   = new_val - cur,
            update_strategy= proposal.update_strategy,
            success        = success,
            error_msg      = error_msg,
            applied_at     = datetime.now(),
        )
        self._records.append(rec)
        self._log(
            f"[AdaptationEngine] applied {target.value}/{eid}: "
            f"{cur:.6f} → {new_val:.6f}  ({'+' if rec.actual_delta>=0 else ''}"
            f"{rec.actual_delta:.6f})  ok={success}")
        return rec

    # ── regime-aware batch adaptation ────────────────────────────────
    def adapt_by_regime(
        self,
        regime_weights: dict[str, float],  # {entity_id: regime_multiplier}
        target:         AdaptationTarget = AdaptationTarget.STRATEGY_ALLOCATION,
        blend_factor:   float = 0.2,
    ) -> list[AdaptationRecord]:
        """
        根据市场状态权重批量调整目标参数。
        regime_weight > 1 → 上调；< 1 → 下调。
        """
        records = []
        for eid, rw in regime_weights.items():
            cur = self._params[target.value].get(eid, 1.0)
            delta_pct = (rw - 1.0) * blend_factor
            new_val, actual_delta = compute_new_value(
                cur, delta_pct, UpdateStrategy.BLEND, blend_factor)
            rec = AdaptationRecord(
                record_id       = f"REC_{uuid.uuid4().hex[:8].upper()}",
                proposal_id     = "regime_adapt",
                target          = target,
                entity_id       = eid,
                dimension       = target.value,
                value_before    = cur,
                value_after     = new_val,
                actual_delta    = actual_delta,
                update_strategy = UpdateStrategy.BLEND,
                success         = True,
            )
            self._params[target.value][eid] = new_val
            self._records.append(rec)
            records.append(rec)

        self._update_state()
        self._log(
            f"[AdaptationEngine] regime_adapt: {len(records)} params updated")
        return records

    # ── decay-triggered correction ───────────────────────────────────
    def apply_decay_correction(
        self,
        entity_id:  str,
        target:     AdaptationTarget,
        decay_rate: float,
        floor:      float = 0.01,
    ) -> AdaptationRecord | None:
        """
        衰减触发修正：将当前参数乘以 (1 - decay_rate * blend)。
        """
        cur = self._params[target.value].get(entity_id)
        if cur is None:
            return None
        delta_pct = -decay_rate * 0.5
        new_val, actual_delta = compute_new_value(
            cur, delta_pct, UpdateStrategy.BLEND)
        new_val = max(new_val, floor)
        self._params[target.value][entity_id] = new_val
        rec = AdaptationRecord(
            record_id       = f"REC_{uuid.uuid4().hex[:8].upper()}",
            proposal_id     = "decay_correction",
            target          = target,
            entity_id       = entity_id,
            dimension       = target.value,
            value_before    = cur,
            value_after     = new_val,
            actual_delta    = new_val - cur,
            update_strategy = UpdateStrategy.BLEND,
            success         = True,
        )
        self._records.append(rec)
        self._update_state()
        return rec

    # ── state update ──────────────────────────────────────────────────
    def _update_state(self) -> None:
        props  = self._proposals
        n      = len(props)
        applied = sum(1 for r in self._records if r.success)
        failed  = sum(1 for r in self._records if not r.success)
        pending = sum(1 for p in props if not p.approved)

        avg_conf = (sum(p.confidence for p in props) / n) if n else 0.0
        avg_dlt  = (sum(abs(p.delta_pct) for p in props) / n) if n else 0.0
        hi_pri   = sum(1 for p in props if p.priority == 1)

        tc: dict[str, int] = {}
        for p in props:
            tc[p.target.value] = tc.get(p.target.value, 0) + 1

        recent = [r.to_dict() for r in self._records[-5:]]

        self._state = AdaptationState(
            total_proposals    = n,
            total_applied      = applied,
            total_failed       = failed,
            pending_proposals  = pending,
            target_counts      = tc,
            avg_confidence     = round(avg_conf, 4),
            avg_delta_pct      = round(avg_dlt,  4),
            high_priority_count= hi_pri,
            recent_records     = recent,
            updated_at         = datetime.now(),
        )

    # ── query ─────────────────────────────────────────────────────────
    def get_state(self) -> AdaptationState:
        return self._state

    def get_proposals(self, n: int = 20,
                       approved: bool | None = None) -> list[AdaptationProposal]:
        ps = self._proposals
        if approved is not None:
            ps = [p for p in ps if p.approved == approved]
        return ps[-n:]

    def get_records(self, n: int = 50) -> list[AdaptationRecord]:
        return self._records[-n:]

    def summary(self) -> dict:
        return {
            "phase":             4,
            "status":            self._status.value,
            "total_proposals":   self._state.total_proposals,
            "total_applied":     self._state.total_applied,
            "pending":           self._state.pending_proposals,
            "avg_confidence":    self._state.avg_confidence,
            "high_priority":     self._state.high_priority_count,
            "target_counts":     self._state.target_counts,
        }
