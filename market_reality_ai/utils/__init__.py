"""
market_reality_ai/utils/__init__.py
"""
from .reality_utils import (
    new_id, now_str, clamp, bps_to_pct, pct_to_bps,
    safe_div, weighted_average,
)
from .stress_utils import (
    get_scenario_params, apply_price_shock,
    simulate_drawdown_path, max_drawdown_from_path, survival_rate_from_path,
    execution_degradation, fill_rate_under_stress, slippage_under_stress,
    scenario_survival_score, system_survival_score,
    survival_grade, worst_grade,
    reality_gap_bps, reality_gap_score, regime_label_from_vol,
    new_stress_id, new_wf_id,
)
from .execution_utils import (
    new_exec_id, realized_price,
    vol_scaled_slippage, directional_slippage,
    fill_rate, realised_fill,
    latency_ms, delay_noise_bps,
    rejection_probability, is_rejected,
    effective_spread_bps,
    calibrate_from_history, _default_params, execution_statistics,
)
from .impact_utils import (
    new_impact_id, regime_multiplier, participation_rate,
    temporary_impact_bps, permanent_impact_bps,
    spread_cost_bps, total_impact_bps,
    decay_half_life, decayed_impact,
    impact_adjusted_price, liquidity_score,
    calibrate_impact_params, default_impact_params, impact_statistics,
)
from .failure_utils import (
    new_failure_id, new_event_id,
    severity_from_score, severity_score, severity_weight,
    check_execution_breakdown, check_liquidity_crisis, check_risk_overflow,
    cascade_risk_score, cascade_depth,
    is_fatal_combination, fatal_combination_names,
    system_failure_score, failure_report, format_failure_summary,
)
