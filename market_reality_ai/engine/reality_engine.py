"""
market_reality_ai/engine/reality_engine.py

Phase 1: 仿真协调器 Stub。
Phase 2–5: 逐步填充，调度5个子引擎。
"""
from __future__ import annotations
from datetime import datetime
from ..constant import SimulationMode, SimulationStatus, SurvivalGrade


class RealityEngine:
    """
    仿真协调器 — 调度所有子引擎。

    Phase 1: 方法骨架，无仿真逻辑。
    Phase 2: 注入 ExecutionSimulator
    Phase 3: 注入 ImpactSimulator
    Phase 4: 注入 StressEngine + WalkForwardEngine
    Phase 5: 注入 FailureEngine
    """

    def __init__(self, log_fn=None) -> None:
        self._log      = log_fn or (lambda m, lvl="INFO": None)
        self._status   = SimulationStatus.IDLE
        self._phase    = 1
        self._started_at: datetime | None = None

        # sub-engine slots — filled in Phase 2–5
        self._execution_sim  = None   # Phase 2
        self._impact_sim     = None   # Phase 3
        self._stress_eng     = None   # Phase 4
        self._walkforward_eng= None   # Phase 4
        self._failure_eng    = None   # Phase 5

    def init(self) -> None:
        """Phase 1 stub — sub-engine init留待后续阶段。"""
        self._log("[RealityEngine] init() [Phase 1 stub]")

    def start(self) -> None:
        self._started_at = datetime.now()
        self._status     = SimulationStatus.IDLE
        self._log("[RealityEngine] started")

    def stop(self) -> None:
        self._status = SimulationStatus.IDLE
        self._log("[RealityEngine] stopped")

    # ── Phase 2 stub ─────────────────────────────────────────────────
    def simulate_execution(self, order_params: dict) -> dict:
        """Phase 2: ExecutionSimulator.simulate() — stub."""
        self._log("[RealityEngine] simulate_execution() [Phase 2 stub]")
        return {"status": "stub", "phase": 2}

    # ── Phase 3 stub ─────────────────────────────────────────────────
    def estimate_impact(self, order_params: dict) -> dict:
        """Phase 3: ImpactSimulator.estimate() — stub."""
        self._log("[RealityEngine] estimate_impact() [Phase 3 stub]")
        return {"status": "stub", "phase": 3}

    # ── Phase 4 stub ─────────────────────────────────────────────────
    def run_stress_test(self, scenario: str, params: dict) -> dict:
        """Phase 4: StressEngine.run() — stub."""
        self._log(f"[RealityEngine] run_stress_test({scenario}) [Phase 4 stub]")
        return {"status": "stub", "phase": 4}

    def run_walk_forward(self, window_days: int, step_days: int) -> dict:
        """Phase 4: WalkForwardEngine.run() — stub."""
        self._log("[RealityEngine] run_walk_forward() [Phase 4 stub]")
        return {"status": "stub", "phase": 4}

    # ── Phase 5 stub ─────────────────────────────────────────────────
    def analyze_failure_modes(self, context: dict) -> dict:
        """Phase 5: FailureEngine.analyze() — stub."""
        self._log("[RealityEngine] analyze_failure_modes() [Phase 5 stub]")
        return {"status": "stub", "phase": 5}

    # ── survival score stub ──────────────────────────────────────────
    def compute_survival_score(self) -> dict:
        """Phase 4/5 combined — stub."""
        return {"score": None, "grade": SurvivalGrade.F.value, "phase": 4}

    @property
    def status(self) -> SimulationStatus:
        return self._status
