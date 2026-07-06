"""
market_reality_ai/engine/stress_engine.py

Phase 4: Stress Testing Engine — complete implementation.

Six standard scenarios:
  flash_crash / liquidity_dry_up / extreme_volatility /
  regime_collapse / correlation_breakdown / fat_tail_event

Per scenario:
  1. Load scenario parameters
  2. Simulate portfolio path (drawdown model)
  3. Compute execution degradation under stress
  4. Score: 50% drawdown + 30% survival + 20% execution
  5. Map score -> S/A/B/C/F grade

System score:  0.6 * mean + 0.4 * min  (pessimistic aggregation)
"""
from __future__ import annotations
from datetime import datetime

from ..constant import SimulationStatus, StressScenarioType, SurvivalGrade
from ..model.stress_model import (
    StressScenario, StressResult, StressState)
from ..utils.stress_utils import (
    new_stress_id, get_scenario_params,
    simulate_drawdown_path, max_drawdown_from_path, survival_rate_from_path,
    execution_degradation, fill_rate_under_stress, slippage_under_stress,
    scenario_survival_score, system_survival_score,
    survival_grade, worst_grade,
)

# Standard scenario order for run_all_scenarios
_ALL_SCENARIOS = [
    StressScenarioType.FLASH_CRASH,
    StressScenarioType.LIQUIDITY_DRY_UP,
    StressScenarioType.EXTREME_VOLATILITY,
    StressScenarioType.REGIME_COLLAPSE,
    StressScenarioType.CORRELATION_BREAKDOWN,
    StressScenarioType.FAT_TAIL_EVENT,
]

_SCENARIO_NAMES = {
    "flash_crash":           "Flash Crash",
    "liquidity_dry_up":      "Liquidity Dry-Up",
    "extreme_volatility":    "Extreme Volatility",
    "regime_collapse":       "Regime Collapse",
    "correlation_breakdown": "Correlation Breakdown",
    "fat_tail_event":        "Fat Tail Event",
}


class StressEngine:
    """
    压力测试引擎 — Phase 4 完整实现。

    每次 run() 调用:
      1. 解析 scenario_type -> 预设参数
      2. simulate_drawdown_path() 生成资产组合路径
      3. max_drawdown_from_path() 计算最大回撤
      4. survival_rate_from_path() 计算生存率
      5. execution_degradation() 计算执行质量损失
      6. scenario_survival_score() -> grade -> StressResult

    run_all_scenarios():
      对全部6个标准场景依次运行，聚合 system_survival_score。
    """

    def __init__(self, log_fn=None) -> None:
        self._log    = log_fn or (lambda m: None)
        self._status = SimulationStatus.IDLE
        self._state  = StressState()

        # default portfolio for simulation
        self._portfolio_value: float = 1_000_000.0
        self._n_positions:     int   = 10
        self._normal_fill:     float = 0.95
        self._normal_slippage: float = 5.0   # bps
        self._seed_base:       int   = 42

    # ── lifecycle ─────────────────────────────────────────────────────
    def init(self) -> None:
        self._status = SimulationStatus.IDLE
        self._state  = StressState()
        self._log("[StressEngine] initialised")

    def start(self) -> None:
        self._status = SimulationStatus.RUNNING
        self._log("[StressEngine] started")

    def stop(self) -> None:
        self._status = SimulationStatus.IDLE
        self._log("[StressEngine] stopped")

    def configure(
        self,
        portfolio_value: float = 1_000_000.0,
        n_positions:     int   = 10,
        normal_fill:     float = 0.95,
        normal_slippage: float = 5.0,
    ) -> None:
        """Configure portfolio parameters for stress simulation."""
        self._portfolio_value = portfolio_value
        self._n_positions     = n_positions
        self._normal_fill     = normal_fill
        self._normal_slippage = normal_slippage

    # ── main entry: run one scenario ──────────────────────────────────
    def run(
        self,
        scenario_type: StressScenarioType,
        params:        dict | None = None,
        seed:          int | None  = None,
    ) -> StressResult:
        """
        Run a single stress scenario.

        Parameters
        ----------
        scenario_type : StressScenarioType
        params        : optional parameter overrides
        seed          : random seed for reproducibility

        Returns StressResult with all fields populated.
        """
        stype  = scenario_type.value
        sp     = get_scenario_params(stype, params)
        _seed  = seed if seed is not None else self._seed_base

        scenario = StressScenario(
            scenario_id     = new_stress_id(),
            scenario_type   = scenario_type,
            name            = _SCENARIO_NAMES.get(stype, stype),
            description     = sp.get("description", ""),
            shock_magnitude = sp["shock_magnitude"],
            duration_bars   = sp["duration_bars"],
            liquidity_factor= sp["liquidity_factor"],
            volatility_mult = sp["volatility_mult"],
            correlation_adj = sp.get("correlation_adj", 0.0),
            regime          = sp.get("regime", "normal"),
        )

        self._log(
            f"[StressEngine] running {scenario.name}  "
            f"shock={scenario.shock_magnitude:.0%}  "
            f"liq={scenario.liquidity_factor:.2f}  "
            f"vol_mult={scenario.volatility_mult:.1f}x")

        # ── Step 1: simulate portfolio path ─────────────────────────
        path = simulate_drawdown_path(
            initial_value    = self._portfolio_value,
            shock_magnitude  = scenario.shock_magnitude,
            duration_bars    = scenario.duration_bars,
            volatility_mult  = scenario.volatility_mult,
            liquidity_factor = scenario.liquidity_factor,
            correlation_adj  = scenario.correlation_adj,
            n_positions      = self._n_positions,
            seed             = _seed,
        )

        # ── Step 2: risk metrics ────────────────────────────────────
        mdd   = max_drawdown_from_path(path)
        surv  = survival_rate_from_path(
            path, self._portfolio_value, survival_threshold=0.50)

        # ── Step 3: execution metrics ───────────────────────────────
        exec_deg  = execution_degradation(
            scenario.liquidity_factor,
            scenario.volatility_mult,
            scenario.regime,
        )
        fill_s  = fill_rate_under_stress(
            self._normal_fill,
            scenario.liquidity_factor,
            scenario.volatility_mult,
        )
        slip_s  = slippage_under_stress(
            self._normal_slippage,
            scenario.liquidity_factor,
            scenario.volatility_mult,
        )

        # ── Step 4: score and grade ─────────────────────────────────
        score = scenario_survival_score(mdd, surv, exec_deg)
        grade = survival_grade(score)
        grade_enum = SurvivalGrade(grade)

        result = StressResult(
            result_id               = new_stress_id(),
            scenario                = scenario,
            status                  = SimulationStatus.COMPLETED,
            max_drawdown            = mdd,
            survival_rate           = surv,
            exec_degradation        = exec_deg,
            fill_rate_under_stress  = fill_s,
            avg_slippage_stress_bps = slip_s,
            survival_grade          = grade_enum,
            survival_score          = score,
            portfolio_path          = path,
            initial_portfolio_value = self._portfolio_value,
            finished_at             = datetime.now(),
        )

        self._append_result(result)
        self._log(
            f"[StressEngine] {scenario.name}  "
            f"dd={mdd:.1%}  surv={surv:.1%}  "
            f"exec_deg={exec_deg:.2f}  "
            f"score={score:.1f}  grade={grade}")
        return result

    # ── run all standard scenarios ────────────────────────────────────
    def run_all_scenarios(
        self,
        params_overrides: dict[str, dict] | None = None,
    ) -> list[StressResult]:
        """
        Run all 6 standard stress scenarios.

        Parameters
        ----------
        params_overrides : dict mapping scenario_type_value -> override dict

        Returns list of StressResult, one per scenario.
        """
        results = []
        overrides = params_overrides or {}

        for i, stype in enumerate(_ALL_SCENARIOS):
            override = overrides.get(stype.value)
            result   = self.run(stype, params=override, seed=self._seed_base + i)
            results.append(result)

        self._log(
            f"[StressEngine] run_all_scenarios complete  "
            f"system_score={self._state.system_score:.1f}  "
            f"grade={self._state.system_grade}")
        return results

    # ── survival score ────────────────────────────────────────────────
    def compute_survival_score(
        self,
        results: list[StressResult] | None = None,
    ) -> dict:
        """
        Compute system survival score from a list of StressResult.
        If results is None, uses all results in current state.

        Returns dict with score, grade, per_scenario breakdown.
        """
        if results is None:
            results = self._state.results
        if not results:
            return {"score": 0.0, "grade": "F",
                    "per_scenario": {}, "phase": 4}

        scores = {
            r.scenario.scenario_type.value: r.survival_score
            for r in results
        }
        sys_score = system_survival_score(list(scores.values()))
        sys_grade = survival_grade(sys_score)
        worst     = worst_grade([r.survival_grade.value for r in results])

        return {
            "score":        sys_score,
            "grade":        sys_grade,
            "worst_grade":  worst,
            "per_scenario": scores,
            "n_scenarios":  len(results),
            "phase":        4,
        }

    # ── query ──────────────────────────────────────────────────────────
    def get_state(self) -> StressState:
        return self._state

    def get_statistics(self) -> dict:
        return self._state.to_dict()

    def get_results(self, limit: int = 100) -> list[StressResult]:
        return self._state.results[-limit:]

    @property
    def status(self) -> SimulationStatus:
        return self._status

    # ── internal ──────────────────────────────────────────────────────
    def _append_result(self, result: StressResult) -> None:
        self._state.results.append(result)
        if len(self._state.results) > 1000:
            self._state.results = self._state.results[-1000:]
        self._state.status = SimulationStatus.RUNNING
        self._state.update_from_results()
