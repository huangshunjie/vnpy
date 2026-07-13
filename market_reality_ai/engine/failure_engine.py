"""
market_reality_ai/engine/failure_engine.py

Phase 5: Failure Mode Analysis Engine — complete implementation.

Pipeline per analyze() call:
  1. Extract context metrics
  2. Run 7 checkers -> detected failures with severity scores
  3. Build FailureMode objects, update FailureState
  4. Compute cascade risk (Poisson spread model)
  5. Check fatal combinations
  6. Generate structured report
"""
from __future__ import annotations
from datetime import datetime

from ..constant import SimulationStatus, FailureModeType, FailureSeverity
from ..model.failure_model import FailureMode, FailureEvent, FailureState
from ..utils.failure_utils import (
    new_failure_id, new_event_id,
    severity_from_score, severity_score,
    check_execution_breakdown, check_liquidity_crisis, check_risk_overflow,
    cascade_risk_score, cascade_depth as _cascade_depth,
    is_fatal_combination, fatal_combination_names,
    system_failure_score, failure_report,
)

_IMPACT = {
    "execution_breakdown":  "Orders rejected, capital frozen, positions unhedged",
    "liquidity_crisis":     "No fills available, strategy cannot trade",
    "risk_overflow":        "Forced liquidation spiral, portfolio destruction",
    "strategy_failure":     "Alpha generation degraded, adverse selection",
    "model_breakdown":      "Stale parameters, wrong regime signals",
    "cascade_failure":      "Multiple simultaneous failures, systemic collapse",
    "system_overload":      "Engine stops, all orders missed",
}

_CONDITION = {
    "execution_breakdown":  "latency>5000ms OR rejection_rate>50% OR fill_rate<20%",
    "liquidity_crisis":     "spread>200bps OR market_depth<5%",
    "risk_overflow":        "drawdown>20% OR leverage>5x",
    "strategy_failure":     "signal_quality<20% OR adverse_pct>60%",
    "model_breakdown":      "prediction_error>30% OR param_staleness>30d",
    "cascade_failure":      "3+ active failures OR cascade_risk>70%",
    "system_overload":      "CPU>90% OR mem>85% OR queue_depth>10000",
}


class FailureEngine:
    """Failure Mode Analysis Engine — Phase 5 complete."""

    def __init__(self, log_fn=None) -> None:
        self._log    = log_fn or (lambda m: None)
        self._status = SimulationStatus.IDLE
        self._state  = FailureState()

    def init(self) -> None:
        self._status = SimulationStatus.IDLE
        self._state  = FailureState()
        self._log("[FailureEngine] initialised")

    def start(self) -> None:
        self._status = SimulationStatus.RUNNING
        self._log("[FailureEngine] started")

    def stop(self) -> None:
        self._status = SimulationStatus.IDLE
        self._log("[FailureEngine] stopped")

    def analyze(self, context: dict | None = None) -> dict:
        """Run full failure mode analysis. Returns failure_report dict."""
        ctx     = context or {}
        regime  = ctx.get("regime", "normal")
        detected: list[FailureMode] = []

        # 1. Execution breakdown
        r = check_execution_breakdown(
            latency_ms     = ctx.get("latency_ms",     0.0),
            rejection_rate = ctx.get("rejection_rate", 0.0),
            fill_rate      = ctx.get("fill_rate",      1.0),
            regime         = regime,
        )
        if r["detected"]:
            detected.append(self._make_failure(
                "execution_breakdown", r["score"],
                r["trigger"], r["value"], regime))

        # 2. Liquidity crisis
        r = check_liquidity_crisis(
            spread_bps   = ctx.get("spread_bps",   5.0),
            market_depth = ctx.get("market_depth", 1.0),
            regime       = regime,
        )
        if r["detected"]:
            detected.append(self._make_failure(
                "liquidity_crisis", r["score"],
                r["trigger"], r["value"], regime))

        # 3. Risk overflow
        r = check_risk_overflow(
            drawdown = ctx.get("drawdown", 0.0),
            leverage = ctx.get("leverage", 1.0),
            regime   = regime,
        )
        if r["detected"]:
            detected.append(self._make_failure(
                "risk_overflow", r["score"],
                r["trigger"], r["value"], regime))

        # 4. Strategy failure
        sq = ctx.get("signal_quality", 1.0)
        if sq < 0.20:
            score = severity_score("strategy_failure",
                                    1.0 - sq, 0.80, regime)
            if score > 0:
                detected.append(self._make_failure(
                    "strategy_failure", score,
                    "signal_quality", sq, regime))

        # 5. Model breakdown
        staleness = float(ctx.get("param_staleness", 0))
        pred_err  = float(ctx.get("prediction_error", 0.0))
        if staleness > 30 or pred_err > 0.30:
            val   = max(staleness / 30.0, pred_err / 0.30)
            score = severity_score("model_breakdown", val, 1.0, regime)
            if score > 0:
                trig = "param_staleness" if staleness > 30 else "prediction_error"
                tval = staleness if staleness > 30 else pred_err
                detected.append(self._make_failure(
                    "model_breakdown", score, trig, tval, regime))

        # 6. System overload
        cpu = float(ctx.get("cpu_pct", 0.0))
        mem = float(ctx.get("mem_pct", 0.0))
        if cpu > 90.0 or mem > 85.0:
            val   = max(cpu / 90.0, mem / 85.0)
            score = severity_score("system_overload", val, 1.0, regime)
            if score > 0:
                trig = "cpu_pct" if cpu > 90 else "mem_pct"
                detected.append(self._make_failure(
                    "system_overload", score, trig,
                    cpu if cpu > 90 else mem, regime))

        # 7. Cascade (meta-check: 3+ distinct failure types)
        existing = ctx.get("existing_failure_types", [])
        all_types = [f.mode_type.value for f in detected] + existing
        if len(set(all_types)) >= 3:
            max_s = max(
                (f.severity.value for f in detected), default=1)
            c_risk = cascade_risk_score(all_types, max_s)
            if c_risk > 0.50:
                detected.append(self._make_failure(
                    "cascade_failure", c_risk * 100.0,
                    "active_count", float(len(all_types)), regime))

        # Update state
        self._state.active_failures = detected
        self._state.status          = SimulationStatus.RUNNING
        self._state.update()

        # Record events
        for fm in detected:
            evt = FailureEvent(
                event_id    = new_event_id(),
                failure_id  = fm.failure_id,
                mode_type   = fm.mode_type,
                severity    = fm.severity,
                description = (f"{fm.mode_type.value}: "
                               f"{fm.trigger}={fm.trigger_value:.3f}"),
                raw_data    = ctx,
            )
            self._state.failure_events.append(evt)
            if len(self._state.failure_events) > 5000:
                self._state.failure_events = (
                    self._state.failure_events[-5000:])

        self._log(
            f"[FailureEngine] analyze n={len(detected)}  "
            f"cascade={self._state.cascade_risk:.3f}  "
            f"fatal={self._state.is_fatal}  "
            f"score={self._state.system_score:.1f}")

        return {
            **failure_report(
                [f.to_dict() for f in detected],
                self._state.cascade_risk,
                self._state.cascade_depth,
                self._state.is_fatal,
                self._state.system_score,
            ),
            "failure_state": self._state.to_dict(),
            "status": "ok",
        }

    def detect_cascade(
        self,
        failure_modes: list | None = None,
    ) -> dict:
        """Detect cascade risk from a list of FailureMode objects."""
        modes   = failure_modes or self._state.active_failures
        types   = [f.mode_type.value for f in modes]
        max_sev = max((f.severity.value for f in modes), default=1)
        c_risk  = cascade_risk_score(types, max_sev)
        c_depth = _cascade_depth(types, c_risk)
        fatal   = is_fatal_combination(types)
        self._log(
            f"[FailureEngine] cascade n={len(types)}  "
            f"risk={c_risk:.3f}  depth={c_depth}  fatal={fatal}")
        return {
            "cascade_active": c_depth > 0,
            "cascade_risk":   c_risk,
            "cascade_depth":  c_depth,
            "fatal":          fatal,
            "fatal_combos":   fatal_combination_names(types),
            "phase":          5,
        }

    def generate_report(self) -> dict:
        """Generate complete failure analysis report from current state."""
        active = self._state.active_failures
        report = failure_report(
            [f.to_dict() for f in active],
            self._state.cascade_risk,
            self._state.cascade_depth,
            self._state.is_fatal,
            self._state.system_score,
        )
        report.update({
            "status":        "ok",
            "failure_state": self._state.to_dict(),
            "event_count":   len(self._state.failure_events),
            "active_modes":  [f.to_dict() for f in active],
        })
        return report

    def resolve_failure(self, failure_id: str) -> bool:
        """Mark a failure as resolved. Returns True if found."""
        for fm in self._state.active_failures:
            if fm.failure_id == failure_id:
                fm.resolved    = True
                fm.resolved_at = datetime.now()
                self._state.active_failures = [
                    f for f in self._state.active_failures
                    if not f.resolved]
                self._state.update()
                self._log(f"[FailureEngine] resolved {failure_id}")
                return True
        return False

    def clear(self) -> None:
        """Clear all active failures."""
        self._state.active_failures = []
        self._state.update()
        self._log("[FailureEngine] cleared")

    def get_state(self) -> FailureState:
        return self._state

    def get_active_failures(self) -> list:
        return self._state.active_failures

    def get_events(self, limit: int = 200) -> list:
        return self._state.failure_events[-limit:]

    @property
    def status(self):
        return self._status

    def _make_failure(
        self,
        type_str:      str,
        score:         float,
        trigger:       str,
        trigger_value: float,
        regime:        str,
    ) -> FailureMode:
        sev    = severity_from_score(score)
        c_risk = min(0.9, score / 100.0 * 1.5)
        return FailureMode(
            failure_id     = new_failure_id(),
            mode_type      = FailureModeType(type_str),
            severity       = sev,
            condition      = _CONDITION.get(type_str, ""),
            trigger        = trigger,
            impact         = _IMPACT.get(type_str, ""),
            cascade_risk   = round(c_risk, 4),
            severity_score = round(score, 2),
            trigger_value  = round(trigger_value, 4),
        )
