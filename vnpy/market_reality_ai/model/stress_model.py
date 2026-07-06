"""
market_reality_ai/model/stress_model.py

Phase 4: Stress Testing + Walk-Forward complete models.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import StressScenarioType, SurvivalGrade, SimulationStatus


@dataclass
class StressScenario:
    """单个压力场景定义 (Phase 4 完整实现)。"""
    scenario_id:     str               = ""
    scenario_type:   StressScenarioType= StressScenarioType.FLASH_CRASH
    name:            str               = ""
    description:     str               = ""
    shock_magnitude: float = 0.0
    duration_bars:   int   = 5
    liquidity_factor:float = 1.0
    volatility_mult: float = 1.0
    correlation_adj: float = 0.0
    regime:          str   = "normal"
    custom_params:   dict  = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "scenario_id":     self.scenario_id,
            "scenario_type":   self.scenario_type.value,
            "name":            self.name,
            "description":     self.description,
            "shock_magnitude": round(self.shock_magnitude, 4),
            "duration_bars":   self.duration_bars,
            "liquidity_factor":round(self.liquidity_factor, 4),
            "volatility_mult": round(self.volatility_mult,  4),
            "correlation_adj": round(self.correlation_adj,  4),
            "regime":          self.regime,
        }


@dataclass
class StressResult:
    """单次压力测试结果 (Phase 4 完整实现)。"""
    result_id:              str             = ""
    scenario:               StressScenario  = field(default_factory=StressScenario)
    status:                 SimulationStatus= SimulationStatus.IDLE

    max_drawdown:           float = 0.0
    survival_rate:          float = 0.0
    exec_degradation:       float = 0.0
    fill_rate_under_stress: float = 0.0
    avg_slippage_stress_bps:float = 0.0
    survival_grade:         SurvivalGrade   = SurvivalGrade.F
    survival_score:         float = 0.0

    # path data
    portfolio_path:         list[float]     = field(default_factory=list)
    initial_portfolio_value:float = 1_000_000.0

    started_at:  datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    notes:       str = ""

    def to_dict(self) -> dict:
        return {
            "result_id":              self.result_id,
            "scenario_type":          self.scenario.scenario_type.value,
            "scenario_name":          self.scenario.name,
            "status":                 self.status.value,
            "max_drawdown":           round(self.max_drawdown,            4),
            "survival_rate":          round(self.survival_rate,           4),
            "exec_degradation":       round(self.exec_degradation,        4),
            "fill_rate_under_stress": round(self.fill_rate_under_stress,  4),
            "avg_slippage_stress_bps":round(self.avg_slippage_stress_bps, 2),
            "survival_grade":         self.survival_grade.value,
            "survival_score":         round(self.survival_score,          2),
            "path_length":            len(self.portfolio_path),
            "phase":                  4,
        }


@dataclass
class StressState:
    """压力测试整体状态 (Phase 4)。"""
    status:        SimulationStatus = SimulationStatus.IDLE
    total_tests:   int              = 0
    passed_tests:  int              = 0   # grade >= C
    failed_tests:  int              = 0   # grade == F
    worst_grade:   SurvivalGrade    = SurvivalGrade.F
    system_score:  float            = 0.0
    system_grade:  str              = "F"
    results:       list[StressResult]= field(default_factory=list)
    updated_at:    datetime          = field(default_factory=datetime.now)

    def update_from_results(self) -> None:
        if not self.results:
            return
        from ..utils.stress_utils import (
            system_survival_score, survival_grade, worst_grade)
        scores = [r.survival_score for r in self.results]
        grades = [r.survival_grade.value for r in self.results]
        self.total_tests  = len(self.results)
        self.passed_tests = sum(1 for r in self.results
                                if r.survival_grade != SurvivalGrade.F)
        self.failed_tests = self.total_tests - self.passed_tests
        self.system_score = system_survival_score(scores)
        self.system_grade = survival_grade(self.system_score)
        self.worst_grade  = SurvivalGrade(worst_grade(grades))
        self.updated_at   = datetime.now()

    def to_dict(self) -> dict:
        return {
            "status":       self.status.value,
            "total_tests":  self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "worst_grade":  self.worst_grade.value,
            "system_score": round(self.system_score, 2),
            "system_grade": self.system_grade,
            "phase":        4,
        }


# ── Walk-Forward models ───────────────────────────────────────────────

@dataclass
class WalkForwardWindow:
    """单个滚动验证窗口结果。"""
    window_id:        str     = ""
    start_date:       str     = ""
    end_date:         str     = ""
    window_days:      int     = 60
    backtest_return:  float   = 0.0   # simulated ideal return
    realized_return:  float   = 0.0   # execution-reality-adjusted return
    reality_gap_bps:  float   = 0.0   # backtest - realized (bps)
    slippage_drag_bps:float   = 0.0
    impact_drag_bps:  float   = 0.0
    regime:           str     = "normal"
    n_trades:         int     = 0

    def to_dict(self) -> dict:
        return {
            "window_id":         self.window_id,
            "start_date":        self.start_date,
            "end_date":          self.end_date,
            "window_days":       self.window_days,
            "backtest_return":   round(self.backtest_return,  6),
            "realized_return":   round(self.realized_return,  6),
            "reality_gap_bps":   round(self.reality_gap_bps,  4),
            "slippage_drag_bps": round(self.slippage_drag_bps,4),
            "impact_drag_bps":   round(self.impact_drag_bps,  4),
            "regime":            self.regime,
            "n_trades":          self.n_trades,
        }


@dataclass
class WalkForwardState:
    """Walk-Forward 整体状态。"""
    status:            SimulationStatus  = SimulationStatus.IDLE
    total_windows:     int               = 0
    avg_reality_gap:   float             = 0.0
    worst_gap:         float             = 0.0
    best_gap:          float             = 0.0
    reality_gap_score: float             = 0.0
    regime_breakdown:  dict              = field(default_factory=dict)
    windows:           list[WalkForwardWindow] = field(default_factory=list)
    updated_at:        datetime          = field(default_factory=datetime.now)

    def update_from_windows(self) -> None:
        if not self.windows:
            return
        from ..utils.stress_utils import reality_gap_score
        gaps = [w.reality_gap_bps for w in self.windows]
        self.total_windows   = len(self.windows)
        self.avg_reality_gap = round(sum(gaps) / len(gaps), 4)
        self.worst_gap       = round(max(gaps, key=abs), 4)
        self.best_gap        = round(min(gaps, key=abs), 4)
        self.reality_gap_score = reality_gap_score(self.avg_reality_gap)
        # regime breakdown
        breakdown: dict[str, list[float]] = {}
        for w in self.windows:
            breakdown.setdefault(w.regime, []).append(w.reality_gap_bps)
        self.regime_breakdown = {
            r: round(sum(v)/len(v), 4) for r, v in breakdown.items()}
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "status":            self.status.value,
            "total_windows":     self.total_windows,
            "avg_reality_gap":   self.avg_reality_gap,
            "worst_gap":         self.worst_gap,
            "best_gap":          self.best_gap,
            "reality_gap_score": self.reality_gap_score,
            "regime_breakdown":  self.regime_breakdown,
            "phase":             4,
        }
