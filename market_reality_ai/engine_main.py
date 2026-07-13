"""
market_reality_ai/engine_main.py

Phase 2: ExecutionSimulator
Phase 3: ImpactSimulator
Phase 4: StressEngine + WalkForwardEngine
Phase 5: FailureEngine — complete implementation
"""
from __future__ import annotations
from datetime import datetime

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import (
    APP_NAME, APP_VERSION,
    SimulationMode, SimulationStatus, SurvivalGrade, StressScenarioType,
)
from .event import (
    EVENT_REALITY_STARTED, EVENT_REALITY_STOPPED,
    EVENT_EXECUTION_SIMULATED, EVENT_SLIPPAGE_RECORDED,
    EVENT_IMPACT_ESTIMATED,
    EVENT_STRESS_TEST_STARTED, EVENT_STRESS_TEST_COMPLETED,
    EVENT_STRESS_SCENARIO_TRIGGERED, EVENT_SURVIVAL_SCORE_UPDATED,
    EVENT_WALKFORWARD_STARTED, EVENT_WALKFORWARD_UPDATED,
    EVENT_WALKFORWARD_COMPLETED,
    EVENT_FAILURE_MODE_DETECTED, EVENT_FAILURE_REPORT_READY,
    EVENT_REALITY_LOG,
)
from .engine.execution_simulator import ExecutionSimulator
from .engine.impact_simulator    import ImpactSimulator
from .engine.stress_engine       import StressEngine
from .engine.walkforward_engine  import WalkForwardEngine
from .engine.failure_engine      import FailureEngine


class RealitySimulationEngine(BaseEngine):
    """Phase 2-5 wired. All engines complete."""

    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine,
                 event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)
        self._version    = APP_VERSION
        self._status     = SimulationStatus.IDLE
        self._started_at: datetime | None = None
        self._log_records: list[str] = []

        self._execution_simulator = ExecutionSimulator(log_fn=self._log)
        self._impact_simulator    = ImpactSimulator(log_fn=self._log)
        self._stress_engine       = StressEngine(log_fn=self._log)
        self._walkforward_engine  = WalkForwardEngine(log_fn=self._log)
        self._failure_engine      = FailureEngine(log_fn=self._log)

        self._log(f"[{APP_NAME}] v{APP_VERSION} engine created")

    # ── lifecycle ─────────────────────────────────────────────────────
    def init(self) -> None:
        self._execution_simulator.init()
        self._impact_simulator.init()
        self._stress_engine.init()
        self._walkforward_engine.init()
        self._failure_engine.init()
        self._log(f"[{APP_NAME}] init()  Phase 2-5 engines ready")

    def start(self) -> None:
        self._started_at = datetime.now()
        self._status     = SimulationStatus.RUNNING
        self._execution_simulator.start()
        self._impact_simulator.start()
        self._stress_engine.start()
        self._walkforward_engine.start()
        self._failure_engine.start()
        self.dispatch_event(EVENT_REALITY_STARTED, {
            "app": APP_NAME, "version": self._version,
            "status": self._status.value, "phase": 5,
        })
        self._log(f"[{APP_NAME}] started  phase=5")

    def stop(self) -> None:
        self._execution_simulator.stop()
        self._impact_simulator.stop()
        self._stress_engine.stop()
        self._walkforward_engine.stop()
        self._failure_engine.stop()
        self._status = SimulationStatus.IDLE
        self.dispatch_event(EVENT_REALITY_STOPPED, {"uptime": self._uptime()})
        self._log(f"[{APP_NAME}] stopped")

    def close(self) -> None:
        self.stop()

    # ── Phase 2+3: simulate_execution ────────────────────────────────
    def simulate_execution(
        self,
        order_params:   dict | None = None,
        mode:           SimulationMode = SimulationMode.EXECUTION_REALITY,
        seed:           int | None = None,
        include_impact: bool = True,
    ) -> dict:
        params = dict(order_params or {})
        impact_d: dict = {"total_cost_bps": 0.0,
                          "temporary_bps": 0.0, "permanent_bps": 0.0}
        if include_impact:
            imp_est      = self._impact_simulator.estimate(params)
            impact_d     = imp_est.to_dict()
            params["_impact_bps"] = imp_est.total_cost_bps
        rec   = self._execution_simulator.simulate(params, seed=seed)
        d     = rec.to_dict()
        d["impact_bps"]    = round(impact_d.get("total_cost_bps", 0.0), 4)
        d["temporary_bps"] = round(impact_d.get("temporary_bps",  0.0), 4)
        d["permanent_bps"] = round(impact_d.get("permanent_bps",  0.0), 4)
        d["impact_state"]  = self._impact_simulator.get_state().to_dict()
        state  = self._execution_simulator.get_state()
        result = {"status": "ok", "phase": 3, "mode": mode.value,
                  **d, "execution_state": state.to_dict()}
        self.dispatch_event(EVENT_EXECUTION_SIMULATED, result)
        self.dispatch_event(EVENT_SLIPPAGE_RECORDED, d)
        return result

    def simulate_batch(
        self, orders: list[dict],
        seed_start: int | None = None,
        include_impact: bool = True,
    ) -> list[dict]:
        results = []
        for i, op in enumerate(orders):
            seed = (seed_start + i) if seed_start is not None else None
            results.append(self.simulate_execution(
                op, seed=seed, include_impact=include_impact))
        return results

    def calibrate_execution(
        self, historical_trades: list[dict], adv: float = 10000.0,
    ) -> dict:
        return self._execution_simulator.calibrate(
            historical_trades, adv).to_dict()

    def get_execution_state(self) -> dict:
        return self._execution_simulator.get_state().to_dict()

    def get_execution_records(self, limit: int = 200) -> list[dict]:
        return [r.to_dict()
                for r in self._execution_simulator.get_records(limit)]

    # ── Phase 3: estimate_impact ──────────────────────────────────────
    def estimate_impact(
        self,
        order_params: dict | None = None,
        liquidity_state=None,
    ) -> dict:
        params = dict(order_params or {})
        est    = self._impact_simulator.estimate(params, liquidity_state)
        d      = est.to_dict()
        result = {"status": "ok", "phase": 3, **d,
                  "impact_state": self._impact_simulator.get_state().to_dict()}
        self.dispatch_event(EVENT_IMPACT_ESTIMATED, result)
        return result

    def calibrate_impact(
        self, observations: list[dict], adv: float = 10000.0,
    ) -> dict:
        return self._impact_simulator.calibrate(observations, adv)

    def get_impact_state(self) -> dict:
        return self._impact_simulator.get_state().to_dict()

    def get_impact_estimates(self, limit: int = 200) -> list[dict]:
        return [e.to_dict()
                for e in self._impact_simulator.get_estimates(limit)]

    # ── Phase 4: run_stress_test ──────────────────────────────────────
    def run_stress_test(
        self,
        scenario: str = "flash_crash",
        params:   dict | None = None,
        seed:     int | None = None,
    ) -> dict:
        """Phase 4 complete: run one stress scenario."""
        try:
            stype = StressScenarioType(scenario)
        except ValueError:
            stype = StressScenarioType.FLASH_CRASH

        self.dispatch_event(EVENT_STRESS_TEST_STARTED,
                            {"scenario": scenario, "params": params or {}})
        self.dispatch_event(EVENT_STRESS_SCENARIO_TRIGGERED,
                            {"scenario": scenario})

        result_obj = self._stress_engine.run(stype, params=params, seed=seed)
        d          = result_obj.to_dict()
        state      = self._stress_engine.get_state().to_dict()
        result     = {**d, "status": "ok", "phase": 4, "stress_state": state}

        self.dispatch_event(EVENT_STRESS_TEST_COMPLETED, result)
        self.dispatch_event(EVENT_SURVIVAL_SCORE_UPDATED, {
            "score": d["survival_score"], "grade": d["survival_grade"]})
        self._log(
            f"[{APP_NAME}] stress({scenario})  "
            f"dd={d['max_drawdown']:.1%}  "
            f"surv={d['survival_rate']:.1%}  "
            f"grade={d['survival_grade']}  score={d['survival_score']:.1f}")
        return result

    def run_all_stress_scenarios(
        self, params_overrides: dict | None = None,
    ) -> dict:
        """Run all 6 standard stress scenarios, return aggregate."""
        results = self._stress_engine.run_all_scenarios(params_overrides)
        score_d = self._stress_engine.compute_survival_score(results)
        state   = self._stress_engine.get_state().to_dict()
        self.dispatch_event(EVENT_SURVIVAL_SCORE_UPDATED, score_d)
        return {
            "status": "ok", "phase": 4,
            "scenarios":      [r.to_dict() for r in results],
            "survival_score": score_d,
            "stress_state":   state,
        }

    def get_survival_score(self) -> dict:
        score_d = self._stress_engine.compute_survival_score()
        self.dispatch_event(EVENT_SURVIVAL_SCORE_UPDATED, score_d)
        return {**score_d, "status": "ok", "phase": 4}

    def get_stress_state(self) -> dict:
        return self._stress_engine.get_state().to_dict()

    def get_stress_results(self, limit: int = 50) -> list[dict]:
        return [r.to_dict() for r in self._stress_engine.get_results(limit)]

    # ── Phase 4: run_walk_forward ─────────────────────────────────────
    def run_walk_forward(
        self,
        window_days: int = 60,
        step_days:   int = 10,
        n_windows:   int = 12,
        seed:        int = 42,
    ) -> dict:
        """Phase 4 complete: rolling reality gap analysis."""
        self.dispatch_event(EVENT_WALKFORWARD_STARTED, {
            "window_days": window_days, "step_days": step_days,
            "n_windows": n_windows,
        })
        wf_state = self._walkforward_engine.run(
            window_days, step_days, n_windows, seed)
        d = wf_state.to_dict()
        self.dispatch_event(EVENT_WALKFORWARD_UPDATED, d)
        self.dispatch_event(EVENT_WALKFORWARD_COMPLETED, d)
        self._log(
            f"[{APP_NAME}] walk_forward  n={d['total_windows']}  "
            f"avg_gap={d['avg_reality_gap']:.1f}bps  "
            f"score={d['reality_gap_score']:.1f}")
        return {
            **d,
            "status": "ok", "phase": 4,
            "windows": [w.to_dict()
                        for w in self._walkforward_engine.get_windows(50)],
        }

    def get_walkforward_state(self) -> dict:
        return self._walkforward_engine.get_state().to_dict()

    # ── Phase 5 stub ──────────────────────────────────────────────────
    def analyze_failure_modes(
        self, context: dict | None = None,
    ) -> dict:
        """
        Failure Mode Analysis — Phase 5 complete.
        Detects: execution_breakdown / liquidity_crisis / risk_overflow /
                 strategy_failure / model_breakdown / cascade_failure / system_overload
        """
        result = self._failure_engine.analyze(context or {})
        result["phase"] = 5
        self.dispatch_event(EVENT_FAILURE_MODE_DETECTED, result)
        self.dispatch_event(EVENT_FAILURE_REPORT_READY, result)
        self._log(
            f"[{APP_NAME}] failure_analysis  "
            f"n={result.get('failure_count',0)}  "
            f"cascade={result.get('cascade_risk',0):.3f}  "
            f"fatal={result.get('is_fatal',False)}")
        return result

    def get_failure_state(self) -> dict:
        return self._failure_engine.get_state().to_dict()

    def get_failure_report(self) -> dict:
        return self._failure_engine.generate_report()

    def detect_cascade(self) -> dict:
        return self._failure_engine.detect_cascade()

    def resolve_failure(self, failure_id: str) -> bool:
        return self._failure_engine.resolve_failure(failure_id)

    def clear_failures(self) -> None:
        self._failure_engine.clear()

    # ── query ─────────────────────────────────────────────────────────
    def get_status(self) -> SimulationStatus:
        return self._status

    def get_logs(self, limit: int = 200) -> list[str]:
        return self._log_records[-limit:]

    def get_summary(self) -> dict:
        es = self._execution_simulator.get_state().to_dict()
        im = self._impact_simulator.get_state().to_dict()
        st = self._stress_engine.get_state().to_dict()
        wf = self._walkforward_engine.get_state().to_dict()
        fs = self._failure_engine.get_state().to_dict()
        sc = self._stress_engine.compute_survival_score()
        return {
            "app":                   APP_NAME,
            "version":               self._version,
            "phase":                 5,
            "status":                self._status.value,
            "uptime":                self._uptime(),
            "total_simulations":     es.get("total_simulations",   0),
            "avg_slippage_bps":      es.get("avg_slippage_bps",    0.0),
            "avg_fill_rate":         es.get("avg_fill_rate",        0.0),
            "rejection_rate":        es.get("rejection_rate",       0.0),
            "total_impact_estimates":im.get("total_estimates",     0),
            "avg_impact_cost_bps":   im.get("avg_total_cost_bps",  0.0),
            "stress_total_tests":    st.get("total_tests",          0),
            "stress_system_score":   st.get("system_score",         0.0),
            "stress_system_grade":   st.get("system_grade",         "F"),
            "survival_score":        sc.get("score",                0.0),
            "survival_grade":        sc.get("grade",                "F"),
            "wf_total_windows":      wf.get("total_windows",        0),
            "wf_avg_reality_gap":    wf.get("avg_reality_gap",      0.0),
            "wf_reality_gap_score":  wf.get("reality_gap_score",    0.0),
            # Phase 5
            "failure_active_count":  fs.get("active_count",         0),
            "failure_max_severity":  fs.get("max_severity",         1),
            "failure_cascade_risk":  fs.get("cascade_risk",         0.0),
            "failure_is_fatal":      fs.get("is_fatal",             False),
            "failure_system_score":  fs.get("system_score",         0.0),
        }

    # ── event dispatch ────────────────────────────────────────────────
    def dispatch_event(self, event_type: str,
                        data: dict | None = None) -> None:
        self.event_engine.put(Event(event_type, data or {}))

    # ── internal ─────────────────────────────────────────────────────
    def _uptime(self) -> float:
        if self._started_at is None:
            return 0.0
        return round(
            (datetime.now() - self._started_at).total_seconds(), 1)

    def _log(self, msg: str, level: str = "INFO") -> None:
        ts   = str(datetime.now())[:19]
        line = f"{ts}  [{level}]  {msg}"
        self._log_records.append(line)
        if len(self._log_records) > 5000:
            self._log_records = self._log_records[-5000:]
        self.dispatch_event(EVENT_REALITY_LOG, {"line": line, "level": level})
        try:
            self.write_log(msg)
        except Exception:
            pass
