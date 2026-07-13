"""
live_production/engine/recovery_engine.py  (Phase 3)
"""
from __future__ import annotations
import threading, uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable
from ..constant import TradingState
from ..event import EVENT_RECOVERY_TRIGGER
from ..utils.recovery_utils import save_checkpoint, load_latest_checkpoint, list_checkpoints


class RecoveryPhase(str, Enum):
    IDLE      = "idle"
    PREPARING = "preparing"
    RESTORING = "restoring"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED    = "failed"


class RecoveryTrigger(str, Enum):
    MANUAL        = "manual"
    AUTO_DEGRADED = "auto_degraded"
    SCHEDULED     = "scheduled"
    STARTUP       = "startup"


@dataclass
class RecoveryStep:
    step_name: str
    phase:     RecoveryPhase
    success:   bool     = True
    detail:    str      = ""
    ts:        datetime = field(default_factory=datetime.now)

    def to_line(self) -> str:
        ok = "OK" if self.success else "FAIL"
        return f"[{str(self.ts)[:19]}] {ok}  [{self.phase.value}]  {self.step_name}  {self.detail}"


@dataclass
class RecoveryRecord:
    record_id:       str
    trigger:         RecoveryTrigger
    started_at:      datetime            = field(default_factory=datetime.now)
    finished_at:     "datetime | None"   = None
    phase:           RecoveryPhase       = RecoveryPhase.IDLE
    steps:           list                = field(default_factory=list)
    checkpoint_path: str                 = ""
    orders_flagged:  int                 = 0
    inconsistencies: int                 = 0
    success:         bool                = False
    error_msg:       str                 = ""

    @property
    def elapsed_seconds(self) -> float:
        end = self.finished_at or datetime.now()
        return (end - self.started_at).total_seconds()

    def to_dict(self) -> dict:
        return {
            "record_id":       self.record_id,
            "trigger":         self.trigger.value,
            "started_at":      str(self.started_at)[:19],
            "finished_at":     str(self.finished_at)[:19] if self.finished_at else "---",
            "phase":           self.phase.value,
            "elapsed_s":       round(self.elapsed_seconds, 1),
            "orders_flagged":  self.orders_flagged,
            "inconsistencies": self.inconsistencies,
            "success":         self.success,
            "error_msg":       self.error_msg,
        }


class RecoveryEngine:
    """
    Live Production System Recovery Engine (Phase 3).

    Responsibilities:
      1. Checkpoint save / load
      2. Automatic recovery flow: PREPARING -> RESTORING -> VERIFYING -> COMPLETED/FAILED
      3. Flag pending orders for reconciliation (Phase 4 will actually process them)
      4. Broadcast module-reconnect events
      5. Consistency check (stub, Phase 4 fills in real logic)

    No trading logic, no direct module calls.
    """

    def __init__(self, event_publish_fn, log_fn, state_manager=None, checkpoint_dir=None):
        self._publish        = event_publish_fn
        self._log            = log_fn
        self._state_manager  = state_manager
        self._checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None
        self._phase          = RecoveryPhase.IDLE
        self._lock           = threading.Lock()
        self._records        = []
        self._max_records    = 100
        self._active_record  = None
        self._checkpoint_count    = 0
        self._last_checkpoint_at  = None

    # ------------------------------------------------------------------
    #  Checkpoint
    # ------------------------------------------------------------------

    def save_checkpoint(self, snapshot: dict) -> str:
        try:
            fp = save_checkpoint(snapshot, directory=self._checkpoint_dir)
            self._checkpoint_count += 1
            self._last_checkpoint_at = datetime.now()
            self._log(f"[Recovery] Checkpoint saved: {fp.name}  (#{self._checkpoint_count})")
            return str(fp)
        except Exception as e:
            self._log(f"[Recovery][ERROR] Checkpoint save failed: {e}")
            return ""

    def load_latest(self):
        data = load_latest_checkpoint(directory=self._checkpoint_dir)
        if data:
            self._log("[Recovery] Loaded latest checkpoint.")
        else:
            self._log("[Recovery] No checkpoint found.")
        return data

    def list_checkpoints(self) -> list:
        return list_checkpoints(directory=self._checkpoint_dir)

    # ------------------------------------------------------------------
    #  Trigger recovery
    # ------------------------------------------------------------------

    def trigger_recovery(self, trigger=None, reason: str = "") -> RecoveryRecord:
        if trigger is None:
            trigger = RecoveryTrigger.MANUAL
        with self._lock:
            if self._phase in (RecoveryPhase.PREPARING, RecoveryPhase.RESTORING,
                               RecoveryPhase.VERIFYING):
                self._log("[Recovery][WARN] Recovery already in progress, skip.")
                return self._active_record

        rec = RecoveryRecord(
            record_id = uuid.uuid4().hex[:8].upper(),
            trigger   = trigger,
        )
        with self._lock:
            self._active_record = rec

        self._log(f"[Recovery] Start  id={rec.record_id}  trigger={trigger.value}  {reason}")
        self._publish(EVENT_RECOVERY_TRIGGER, {
            "record_id": rec.record_id,
            "trigger":   trigger.value,
            "reason":    reason,
        })

        if self._state_manager and not self._state_manager.is_in_recovery:
            self._state_manager.start_recovery(f"RecoveryEngine id={rec.record_id}")

        self._phase_preparing(rec)
        self._phase_restoring(rec)
        self._phase_verifying(rec)
        self._finalize(rec)

        with self._lock:
            self._records.append(rec)
            if len(self._records) > self._max_records:
                self._records.pop(0)
            self._active_record = None
            self._phase = RecoveryPhase.IDLE

        return rec

    # ------------------------------------------------------------------
    #  Recovery phases
    # ------------------------------------------------------------------

    def _phase_preparing(self, rec: RecoveryRecord) -> None:
        self._set_phase(rec, RecoveryPhase.PREPARING)
        snapshot = load_latest_checkpoint(directory=self._checkpoint_dir)
        if snapshot:
            rec.checkpoint_path = str(snapshot.get("_filepath", ""))
            self._step(rec, "Load Checkpoint", RecoveryPhase.PREPARING, True,
                       "snapshot found")
        else:
            self._step(rec, "Load Checkpoint", RecoveryPhase.PREPARING, False,
                       "no checkpoint, cold recovery")
        self._log(f"[Recovery] PREPARING done  cp={'found' if snapshot else 'none'}")

    def _phase_restoring(self, rec: RecoveryRecord) -> None:
        self._set_phase(rec, RecoveryPhase.RESTORING)

        self._step(rec, "Restore system state", RecoveryPhase.RESTORING, True,
                   "state restored to RECOVERY")

        pending = self._scan_pending_orders()
        rec.orders_flagged = pending
        self._step(rec, "Flag pending orders", RecoveryPhase.RESTORING, True,
                   f"{pending} orders flagged for reconciliation")

        self._publish("eLiveProd.recovery.reconnect", {
            "record_id": rec.record_id, "action": "reconnect",
        })
        self._step(rec, "Notify module reconnect", RecoveryPhase.RESTORING, True,
                   "reconnect event broadcast")
        self._log(f"[Recovery] RESTORING done  orders_flagged={rec.orders_flagged}")

    def _phase_verifying(self, rec: RecoveryRecord) -> None:
        self._set_phase(rec, RecoveryPhase.VERIFYING)
        n = self._check_consistency()
        rec.inconsistencies = n
        ok = (n == 0)
        self._step(rec, "Consistency check", RecoveryPhase.VERIFYING, ok,
                   "clean" if ok else f"{n} inconsistencies logged")
        self._log(f"[Recovery] VERIFYING done  inconsistencies={n}")

    def _finalize(self, rec: RecoveryRecord) -> None:
        critical_fail = [
            s for s in rec.steps
            if not s.success and s.step_name in ("Restore system state",
                                                  "Notify module reconnect")
        ]
        rec.finished_at = datetime.now()
        if not critical_fail:
            rec.success = True
            rec.phase   = RecoveryPhase.COMPLETED
            self._log(f"[Recovery] COMPLETED  id={rec.record_id}  "
                      f"elapsed={rec.elapsed_seconds:.1f}s")
            if self._state_manager:
                self._state_manager.recovery_success(f"RecoveryEngine id={rec.record_id}")
        else:
            rec.success   = False
            rec.phase     = RecoveryPhase.FAILED
            rec.error_msg = "; ".join(s.detail for s in critical_fail)
            self._log(f"[Recovery][ERROR] FAILED  id={rec.record_id}  {rec.error_msg}")
            if self._state_manager:
                self._state_manager.recovery_fail(f"RecoveryEngine id={rec.record_id}")

        self._publish("eLiveProd.recovery.result", {
            "record_id": rec.record_id,
            "success":   rec.success,
            "elapsed_s": rec.elapsed_seconds,
        })

    # ------------------------------------------------------------------
    #  Query
    # ------------------------------------------------------------------

    @property
    def phase(self) -> RecoveryPhase:
        return self._phase

    @property
    def is_recovering(self) -> bool:
        return self._phase in (RecoveryPhase.PREPARING,
                               RecoveryPhase.RESTORING,
                               RecoveryPhase.VERIFYING)

    def get_records(self, limit: int = 50) -> list:
        return self._records[-limit:]

    def get_active_record(self):
        return self._active_record

    def summary(self) -> dict:
        total = len(self._records)
        ok    = sum(1 for r in self._records if r.success)
        return {
            "phase":            self._phase.value,
            "total":            total,
            "succeeded":        ok,
            "failed":           total - ok,
            "checkpoint_count": self._checkpoint_count,
            "last_checkpoint_at": str(self._last_checkpoint_at)[:19]
                                  if self._last_checkpoint_at else "---",
        }

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------

    def _set_phase(self, rec: RecoveryRecord, phase: RecoveryPhase) -> None:
        rec.phase   = phase
        self._phase = phase
        self._log(f"[Recovery] Phase -> {phase.value}")

    def _step(self, rec, name, phase, success, detail="") -> None:
        s = RecoveryStep(step_name=name, phase=phase, success=success, detail=detail)
        rec.steps.append(s)
        self._log(f"[Recovery]   {'OK' if success else 'FAIL'}  {name}  {detail}")

    def _scan_pending_orders(self) -> int:
        return 0   # Phase 4 Order Sync will fill in

    def _check_consistency(self) -> int:
        return 0   # Phase 4 will fill in
