"""
adaptive_learning_ai/engine/orchestration_engine.py  (Phase 5)

OrchestrationEngine — 学习调度引擎。

职责：
  - 协调 Feedback → Learning → Adaptation → Update 完整闭环
  - 周期调度（计数器驱动）
  - 系统健康度计算
  - 生成 SystemLearningState 总览快照
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable

from ..constant import SystemStatus, AdaptationTarget
from ..model.system_model import SystemLearningState
from .feedback_engine   import FeedbackEngine
from .learning_engine   import LearningEngine
from .adaptation_engine import AdaptationEngine
from .update_engine     import UpdateEngine


class OrchestrationEngine:
    """学习调度引擎（Phase 5 完整实现）。"""

    def __init__(
        self,
        feedback_engine:   FeedbackEngine,
        learning_engine:   LearningEngine,
        adaptation_engine: AdaptationEngine,
        update_engine:     UpdateEngine,
        log_fn: Callable | None = None,
    ) -> None:
        self._fe  = feedback_engine
        self._le  = learning_engine
        self._ae  = adaptation_engine
        self._ue  = update_engine
        self._log = log_fn or (lambda m: None)

        self._cycle            = 0
        self._status           = SystemStatus.IDLE
        self._cycle_results:   list[dict] = []
        self._state            = SystemLearningState()

    def init(self)  -> None: self._log("[OrchestrationEngine] init()")
    def start(self) -> None:
        self._status = SystemStatus.COLLECTING
        self._log("[OrchestrationEngine] start()")

    def stop(self)  -> None:
        self._status = SystemStatus.STOPPED
        self._log("[OrchestrationEngine] stop()")

    # ── full closed-loop cycle ────────────────────────────────────────
    def run_full_cycle(
        self,
        min_confidence:     float = 0.5,
        min_priority_level: int   = 3,
        blend_factor:       float = 0.3,
    ) -> dict:
        """
        完整闭环：
          Feedback(close batch)
          → Learning(signals + patterns)
          → Adaptation(proposals + apply)
          → Update(versions + records)
          → State snapshot
        """
        self._cycle += 1
        self._status = SystemStatus.LEARNING

        # Step 1: close feedback batch → records
        batch   = self._fe.next_cycle()
        fb_recs = batch.records if batch else []

        # Step 2: learning
        signals, patterns = self._le.learn_from_records(fb_recs)

        # Step 3: adaptation
        proposals = self._ae.generate_proposals(patterns, blend_factor)
        applied   = self._ae.auto_apply(
            proposals, min_confidence, min_priority_level)

        # Step 4: update → version management
        update_rec = self._ue.apply_records(applied, self._cycle, "full_cycle")

        result = {
            "cycle":            self._cycle,
            "n_feedback":       len(fb_recs),
            "n_signals":        len(signals),
            "n_patterns":       len(patterns),
            "n_proposals":      len(proposals),
            "n_applied":        len(applied),
            "n_versions":       update_rec.n_params_updated,
            "targets_affected": update_rec.targets_affected,
            "system_health":    0.0,   # filled below
        }

        self._cycle_results.append(result)
        self._update_state()
        result["system_health"] = self._state.system_health

        self._status = SystemStatus.COLLECTING
        self._log(
            f"[OrchestrationEngine] full_cycle={self._cycle}: "
            f"fb={len(fb_recs)} sig={len(signals)} pat={len(patterns)} "
            f"prop={len(proposals)} applied={len(applied)} "
            f"health={self._state.system_health:.1f}")
        return result

    # ── system health ─────────────────────────────────────────────────
    def _compute_health(self) -> float:
        """
        系统健康度 [0, 100]。

        组成：
          40% — 反馈质量（avg_signal，越高越好）
          30% — 学习质量（avg_confidence）
          20% — 自适应成功率（applied / proposals）
          10% — 更新稳定性（rollback 越少越好）
        """
        fb_s  = self._fe.get_state()
        le_s  = self._le.get_state()
        ae_s  = self._ae.get_state()
        ue_s  = self._ue.summary()

        fb_score  = fb_s.avg_signal  * 100 * 0.40
        le_score  = le_s.avg_confidence * 100 * 0.30

        n_prop    = ae_s.total_proposals
        n_applied = ae_s.total_applied
        adapt_rate = (n_applied / n_prop) if n_prop > 0 else 0.5
        ae_score  = adapt_rate * 100 * 0.20

        n_rollback = ue_s.get("n_rollbacks", 0)
        n_updates  = max(ue_s.get("total_updates", 1), 1)
        rollback_rate = n_rollback / n_updates
        ue_score  = max(0.0, (1.0 - rollback_rate * 2)) * 100 * 0.10

        return round(fb_score + le_score + ae_score + ue_score, 2)

    def _update_state(self) -> None:
        fb_s = self._fe.get_state()
        le_s = self._le.get_state()
        ae_s = self._ae.get_state()
        ue_s = self._ue.summary()

        n_prop    = ae_s.total_proposals
        n_applied = ae_s.total_applied
        adapt_rate = round(n_applied / max(n_prop, 1), 4)

        health = self._compute_health()

        # avg improvement across all update records
        ue_recs = self._ue.get_update_records(100)
        avg_imp = (sum(r.avg_improvement for r in ue_recs) / len(ue_recs)
                   if ue_recs else 0.0)

        active_targets = sorted({
            p.target.value
            for p in self._ae.get_proposals(100)
            if p.approved
        })

        self._state = SystemLearningState(
            cycle              = self._cycle,
            phase              = 5,
            total_feedback     = fb_s.total_records,
            total_signals      = le_s.total_signals,
            total_patterns     = le_s.active_patterns,
            total_proposals    = n_prop,
            total_applied      = n_applied,
            total_updates      = ue_s.get("total_updates",  0),
            total_rollbacks    = ue_s.get("n_rollbacks",    0),
            system_health      = health,
            learning_velocity  = le_s.learning_velocity,
            adaptation_rate    = adapt_rate,
            avg_improvement    = round(avg_imp, 4),
            active_targets     = active_targets,
            feedback_summary   = self._fe.summary(),
            learning_summary   = le_s.to_dict(),
            adaptation_summary = ae_s.to_dict(),
            update_summary     = ue_s,
            updated_at         = datetime.now(),
        )

    # ── query ─────────────────────────────────────────────────────────
    def get_state(self) -> SystemLearningState:
        self._update_state()
        return self._state

    def get_cycle_results(self, n: int = 10) -> list[dict]:
        return self._cycle_results[-n:]

    def summary(self) -> dict:
        self._update_state()
        return {
            "phase":           5,
            "status":          self._status.value,
            "cycle":           self._cycle,
            "system_health":   self._state.system_health,
            "learning_velocity":self._state.learning_velocity,
            "adaptation_rate": self._state.adaptation_rate,
            "total_feedback":  self._state.total_feedback,
            "total_applied":   self._state.total_applied,
            "total_updates":   self._state.total_updates,
        }
