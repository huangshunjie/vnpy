"""
adaptive_learning_ai/engine/__init__.py  (Phase 5 Final)

GlobalLearningEngine — 完整五阶段自适应学习系统顶层引擎。
"""
from __future__ import annotations
from datetime import datetime

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from ..constant import APP_NAME, SystemStatus, FeedbackType, AdaptationTarget
from ..event import (
    EVENT_FEEDBACK_RECEIVED, EVENT_LEARNING_STARTED,
    EVENT_MODEL_UPDATED, EVENT_SYSTEM_ADAPTED,
    EVENT_LEARNING_CYCLE_COMPLETED,
)
from .learning_engine      import LearningEngine
from .feedback_engine      import FeedbackEngine
from .adaptation_engine    import AdaptationEngine
from .update_engine        import UpdateEngine
from .orchestration_engine import OrchestrationEngine
from ..model.feedback_model   import FeedbackRecord, FeedbackState
from ..model.learning_model   import LearningSignal, LearningPattern, LearningState
from ..model.adaptation_model import AdaptationProposal, AdaptationRecord, AdaptationState
from ..model.system_model     import ModelVersion, SystemUpdateRecord, SystemLearningState


class GlobalLearningEngine(BaseEngine):
    """自适应学习系统 — VeighNa 顶层引擎（Phase 5 Final）。"""

    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)
        self._status:      SystemStatus    = SystemStatus.IDLE
        self._started_at:  datetime | None = None
        self._log_records: list[str]       = []

        self._feedback_engine   = FeedbackEngine(log_fn=self._log)
        self._learning_engine   = LearningEngine(log_fn=self._log)
        self._adaptation_engine = AdaptationEngine(log_fn=self._log)
        self._update_engine     = UpdateEngine(log_fn=self._log)
        self._orchestration     = OrchestrationEngine(
            self._feedback_engine, self._learning_engine,
            self._adaptation_engine, self._update_engine,
            log_fn=self._log)
        self._log(f"[{APP_NAME}] GlobalLearningEngine created (Phase 5)")

    # ── lifecycle ────────────────────────────────────────────────────
    def init(self) -> None:
        self._log(f"[{APP_NAME}] init()")
        for e in [self._feedback_engine, self._learning_engine,
                  self._adaptation_engine, self._update_engine,
                  self._orchestration]:
            e.init()
        self._status = SystemStatus.IDLE

    def start(self) -> None:
        self._started_at = datetime.now()
        self._status     = SystemStatus.COLLECTING
        for e in [self._feedback_engine, self._learning_engine,
                  self._adaptation_engine, self._update_engine,
                  self._orchestration]:
            e.start()
        self.dispatch_event(EVENT_LEARNING_STARTED,
                            {"status": self._status.value, "phase": 5})

    def stop(self) -> None:
        self._status = SystemStatus.STOPPED
        for e in [self._feedback_engine, self._learning_engine,
                  self._adaptation_engine, self._update_engine,
                  self._orchestration]:
            e.stop()
        self._log(f"[{APP_NAME}] stop()")

    def close(self) -> None:
        self.stop()

    # ── Phase 5: full closed-loop ────────────────────────────────────
    def run_full_cycle(self, min_confidence=0.5,
                        min_priority_level=3, blend_factor=0.3) -> dict:
        """完整闭环：Feedback→Learning→Adaptation→Update。"""
        self._status = SystemStatus.LEARNING
        result = self._orchestration.run_full_cycle(
            min_confidence, min_priority_level, blend_factor)
        self._status = SystemStatus.COLLECTING
        self.dispatch_event(EVENT_SYSTEM_ADAPTED, result)
        self.dispatch_event(EVENT_LEARNING_CYCLE_COMPLETED, result)
        return result

    def reweight_strategies(self, performance_scores,
                             target=None, blend_factor=0.2):
        from ..constant import AdaptationTarget as AT
        t = target if target is not None else AT.STRATEGY_ALLOCATION
        versions = self._update_engine.reweight_strategies(
            performance_scores, t, blend_factor)
        self.dispatch_event(EVENT_SYSTEM_ADAPTED,
                            {"n_reweighted": len(versions)})
        return versions

    def rollback_param(self, target, entity_id, n_steps=1):
        mv = self._update_engine.rollback(target, entity_id, n_steps)
        if mv:
            self.dispatch_event(EVENT_SYSTEM_ADAPTED, mv.to_dict())
        return mv

    def get_system_learning_state(self) -> SystemLearningState:
        return self._orchestration.get_state()

    def get_model_version(self, target, entity_id):
        return self._update_engine.get_current_version(target, entity_id)

    def get_version_history(self, target, entity_id, n=10):
        return self._update_engine.get_version_history(target, entity_id, n)

    def get_update_records(self, n=20):
        return self._update_engine.get_update_records(n)

    def get_cycle_results(self, n=10):
        return self._orchestration.get_cycle_results(n)

    # ── Phase 4 interface ────────────────────────────────────────────
    def run_adaptation_cycle(self, min_confidence=0.6,
                              min_priority_level=2, blend_factor=0.3) -> dict:
        self._status = SystemStatus.ADAPTING
        batch   = self._feedback_engine.next_cycle()
        records = batch.records if batch else []
        signals, patterns = self._learning_engine.learn_from_records(records)
        proposals = self._adaptation_engine.generate_proposals(
            patterns, blend_factor=blend_factor)
        applied   = self._adaptation_engine.auto_apply(
            proposals, min_confidence, min_priority_level)
        update_rec = self._update_engine.apply_records(
            applied, self._learning_engine._cycle, "adaptation")
        result = {
            "cycle": self._learning_engine._cycle,
            "n_records": len(records), "n_signals": len(signals),
            "n_patterns": len(patterns), "n_proposals": len(proposals),
            "n_applied": len(applied), "n_versions": update_rec.n_params_updated,
            "proposals": [p.to_dict() for p in proposals],
            "records":   [r.to_dict() for r in applied],
        }
        self._status = SystemStatus.COLLECTING
        self.dispatch_event(EVENT_SYSTEM_ADAPTED, result)
        self.dispatch_event(EVENT_LEARNING_CYCLE_COMPLETED, result)
        return result

    def generate_adaptation_proposals(self, blend_factor=0.3):
        patterns  = self._learning_engine.get_patterns()
        proposals = self._adaptation_engine.generate_proposals(
            patterns, blend_factor)
        self.dispatch_event(EVENT_SYSTEM_ADAPTED, {"n_proposals": len(proposals)})
        return proposals

    def apply_adaptation_proposals(self, proposals,
                                    min_confidence=0.6, min_priority_level=2):
        records = self._adaptation_engine.auto_apply(
            proposals, min_confidence, min_priority_level)
        self.dispatch_event(EVENT_SYSTEM_ADAPTED, {"n_applied": len(records)})
        return records

    def adapt_by_regime(self, regime_weights, target=None, blend_factor=0.2):
        from ..constant import AdaptationTarget as AT
        t = target if target is not None else AT.STRATEGY_ALLOCATION
        records = self._adaptation_engine.adapt_by_regime(
            regime_weights, t, blend_factor)
        self.dispatch_event(EVENT_SYSTEM_ADAPTED,
                            {"n_regime_adapted": len(records)})
        return records

    def apply_decay_correction(self, entity_id, target, decay_rate, floor=0.01):
        rec = self._adaptation_engine.apply_decay_correction(
            entity_id, target, decay_rate, floor)
        if rec:
            self.dispatch_event(EVENT_SYSTEM_ADAPTED, rec.to_dict())
        return rec

    def register_param(self, target, entity_id, value):
        self._adaptation_engine.register_param(target, entity_id, value)

    def get_param(self, target, entity_id):
        return self._adaptation_engine.get_param(target, entity_id)

    def get_all_params(self, target):
        return self._adaptation_engine.get_all_params(target)

    def get_adaptation_state(self):
        return self._adaptation_engine.get_state()

    def get_adaptation_proposals(self, n=20, approved=None):
        return self._adaptation_engine.get_proposals(n, approved)

    def get_adaptation_records(self, n=50):
        return self._adaptation_engine.get_records(n)

    # ── Phase 3 interface ────────────────────────────────────────────
    def run_learning_cycle(self) -> dict:
        self._status = SystemStatus.LEARNING
        batch   = self._feedback_engine.next_cycle()
        records = batch.records if batch else []
        signals, patterns = self._learning_engine.learn_from_records(records)
        result = {"cycle": self._learning_engine._cycle,
                  "n_records": len(records), "n_signals": len(signals),
                  "n_patterns": len(patterns),
                  "patterns": [p.to_dict() for p in patterns]}
        self._status = SystemStatus.COLLECTING
        self.dispatch_event(EVENT_MODEL_UPDATED, result)
        self.dispatch_event(EVENT_LEARNING_CYCLE_COMPLETED, result)
        return result

    def learn_from_feedback(self, record):
        signal = self._learning_engine.learn_from_single(record)
        self.dispatch_event(EVENT_MODEL_UPDATED, signal.to_dict())
        return signal

    def get_learning_signals(self, n=50, target=None, fb_type=None):
        return self._learning_engine.get_signals(n, target, fb_type)

    def get_learning_patterns(self, target=None):
        return self._learning_engine.get_patterns(target)

    def get_high_confidence_signals(self, threshold=0.7):
        return self._learning_engine.get_high_confidence_signals(threshold)

    def get_urgent_signals(self, n=5):
        return self._learning_engine.get_urgent_signals(n)

    def get_learning_state(self):
        return self._learning_engine.get_state()

    # ── Phase 2 interface ────────────────────────────────────────────
    def collect_feedback(self, feedback):
        r = self._feedback_engine.ingest(feedback)
        self.dispatch_event(EVENT_FEEDBACK_RECEIVED, r.to_dict())
        return r.to_dict()

    def trigger_learning(self):
        return self.run_learning_cycle()

    def ingest_feedback(self, raw):
        r = self._feedback_engine.ingest(raw)
        self.dispatch_event(EVENT_FEEDBACK_RECEIVED, r.to_dict())
        return r

    def ingest_execution_feedback(self, dp, ap, sym="", sid=""):
        r = self._feedback_engine.ingest_execution(dp, ap, sym, sid)
        self.dispatch_event(EVENT_FEEDBACK_RECEIVED, r.to_dict()); return r

    def ingest_strategy_feedback(self, er, ar, sid=""):
        r = self._feedback_engine.ingest_strategy(er, ar, sid)
        self.dispatch_event(EVENT_FEEDBACK_RECEIVED, r.to_dict()); return r

    def ingest_portfolio_feedback(self, tw, aw, sym=""):
        r = self._feedback_engine.ingest_portfolio(tw, aw, sym)
        self.dispatch_event(EVENT_FEEDBACK_RECEIVED, r.to_dict()); return r

    def ingest_risk_feedback(self, rl, ar, sid=""):
        r = self._feedback_engine.ingest_risk(rl, ar, sid)
        self.dispatch_event(EVENT_FEEDBACK_RECEIVED, r.to_dict()); return r

    def ingest_alpha_feedback(self, ei, ai, aid=""):
        r = self._feedback_engine.ingest_alpha(ei, ai, aid)
        self.dispatch_event(EVENT_FEEDBACK_RECEIVED, r.to_dict()); return r

    def next_feedback_cycle(self):
        batch = self._feedback_engine.next_cycle()
        return batch.to_dict() if batch else {}

    def get_feedback_state(self):
        return self._feedback_engine.get_state()

    def get_feedback_records(self, n=50, fb_type=None):
        return self._feedback_engine.get_records(n, fb_type)

    def get_high_severity_records(self, threshold=0.7):
        return self._feedback_engine.get_high_severity_records(threshold)

    # ── events / query / summary ─────────────────────────────────────
    def dispatch_event(self, event_type, data=None):
        self.event_engine.put(Event(event_type, data or {}))

    def get_status(self):
        return self._status

    def get_logs(self, limit=200):
        return self._log_records[-limit:]

    def get_summary(self) -> dict:
        orch_summ = self._orchestration.summary()
        return {
            "app":            APP_NAME,
            "phase":          5,
            "status":         self._status.value,
            "uptime":         self._uptime(),
            "feedback":       self._feedback_engine.summary(),
            "learning":       self._learning_engine.summary(),
            "adaptation":     self._adaptation_engine.summary(),
            "update":         self._update_engine.summary(),
            "orchestration":  orch_summ,
        }

    def _uptime(self):
        if self._started_at is None: return 0.0
        return round((datetime.now() - self._started_at).total_seconds(), 1)

    def _log(self, msg):
        ts = str(datetime.now())[:19]
        self._log_records.append(f"{ts}  {msg}")
        try:    self.write_log(msg)
        except: pass


__all__ = [
    "GlobalLearningEngine", "LearningEngine", "FeedbackEngine",
    "AdaptationEngine", "UpdateEngine", "OrchestrationEngine",
]
