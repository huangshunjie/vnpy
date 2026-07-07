"""
temporal_intelligence_ai/utils/decay_utils.py

Alpha 衰减计算工具函数。

三种衰减模式：
  1. 指数衰减（Exponential Decay）
     — 经典半衰期模型，与时间无关的恒定衰减率
  2. Regime 依赖衰减（Regime-Dependent Decay）
     — 不同市场 Regime 下衰减率不同
  3. 波动率调整衰减（Volatility-Adjusted Decay）
     — 高波动环境加速衰减

所有函数严格只使用历史已知参数，无前瞻偏差。
"""
from __future__ import annotations

import math
from typing import List

from ..constant import CyclePhase, RegimeType, DecayMode
from ..model.decay_model import DecayCurve, DecayCurvePoint, DecayMetrics


# ── 基础衰减公式 ─────────────────────────────────────────────────────

def exponential_decay(initial: float, decay_rate: float, t: int) -> float:
    """
    标准指数衰减。

    S(t) = S₀ · e^(-λ·t)

    Args:
        initial:    初始强度 S₀ ∈ (0, 1]
        decay_rate: 衰减率 λ > 0（越大衰减越快）
        t:          时间步数（bars）
    """
    if decay_rate <= 0 or t < 0:
        return initial
    return initial * math.exp(-decay_rate * t)


def half_life_to_rate(half_life: float) -> float:
    """
    半衰期（bars）转换为衰减率 λ。

    λ = ln(2) / T½
    """
    if half_life <= 0:
        return 0.0
    return math.log(2.0) / half_life


def rate_to_half_life(decay_rate: float) -> float:
    """衰减率 λ 转换为半衰期（bars）。"""
    if decay_rate <= 0:
        return float("inf")
    return math.log(2.0) / decay_rate


def expected_expiry_bar(current_strength: float, decay_rate: float,
                        min_threshold: float = 0.10) -> int:
    """
    基于当前强度和衰减率，估算到达最小阈值所需的剩余 bar 数。

    t = ln(S_min / S_current) / (-λ)
    """
    if decay_rate <= 0 or current_strength <= min_threshold:
        return 0
    if current_strength <= 0:
        return 0
    ratio = min_threshold / current_strength
    if ratio <= 0 or ratio >= 1:
        return 0
    return max(0, int(math.log(ratio) / (-decay_rate)))


# ── Regime 依赖衰减 ──────────────────────────────────────────────────

_REGIME_DECAY_MULTIPLIERS: dict[str, float] = {
    RegimeType.BULL_QUIET.value:    0.70,   # 牛市低波动：衰减最慢
    RegimeType.BULL_VOLATILE.value: 1.10,   # 牛市高波动：稍快
    RegimeType.BEAR_QUIET.value:    1.20,   # 熊市低波动：加快
    RegimeType.BEAR_VOLATILE.value: 1.60,   # 熊市高波动：明显加快
    RegimeType.SIDEWAYS.value:      0.90,   # 横盘：接近基准
    RegimeType.CRISIS.value:        2.50,   # 危机：极速衰减
    RegimeType.UNKNOWN.value:       1.00,   # 未知：基准
}

_CYCLE_DECAY_MULTIPLIERS: dict[str, float] = {
    CyclePhase.EXPANSION.value:   0.80,   # 扩张期：Alpha 存续更久
    CyclePhase.PEAK.value:        1.20,   # 顶部：开始加速衰减
    CyclePhase.CONTRACTION.value: 1.50,   # 收缩期：快速衰减
    CyclePhase.TROUGH.value:      1.30,   # 底部：衰减仍快
    CyclePhase.TRANSITION.value:  1.10,   # 过渡：轻微加速
    CyclePhase.UNKNOWN.value:     1.00,
}


def regime_decay_multiplier(regime: RegimeType) -> float:
    """返回指定 Regime 的衰减速率乘子。"""
    return _REGIME_DECAY_MULTIPLIERS.get(regime.value, 1.0)


def cycle_decay_multiplier(phase: CyclePhase) -> float:
    """返回指定周期阶段的衰减速率乘子。"""
    return _CYCLE_DECAY_MULTIPLIERS.get(phase.value, 1.0)


def regime_dependent_decay(
    initial:    float,
    base_rate:  float,
    t:          int,
    regime:     RegimeType,
    phase:      CyclePhase,
) -> float:
    """
    Regime 依赖衰减。

    λ_eff = λ_base · M_regime · M_cycle
    S(t)  = S₀ · e^(-λ_eff · t)
    """
    m_regime = regime_decay_multiplier(regime)
    m_cycle  = cycle_decay_multiplier(phase)
    effective_rate = base_rate * m_regime * m_cycle
    return exponential_decay(initial, effective_rate, t)


def regime_penalty(regime: RegimeType, phase: CyclePhase) -> float:
    """
    计算 Regime + 周期联合惩罚因子 [0, 1]。

    0 = 无惩罚，1 = 完全衰减。
    """
    m = regime_decay_multiplier(regime) * cycle_decay_multiplier(phase)
    # 归一化到 [0, 1]：乘子 1.0 → 惩罚 0；乘子 2.5 → 惩罚 ~0.6
    return min(1.0, max(0.0, (m - 1.0) / 2.5))


# ── 波动率调整衰减 ────────────────────────────────────────────────────

def volatility_adjustment_factor(
    current_vol: float,
    baseline_vol: float = 0.20,
    sensitivity: float  = 2.0,
) -> float:
    """
    波动率调整乘子。

    当前波动率高于基准时加速衰减，低于基准时减缓衰减。

    adj = exp(sensitivity · (vol - baseline) / baseline)
    结果 clip 到 [0.5, 3.0]

    Args:
        current_vol:  当前年化波动率
        baseline_vol: 基准波动率（默认 20%）
        sensitivity:  敏感度系数
    """
    if baseline_vol <= 0:
        return 1.0
    ratio = (current_vol - baseline_vol) / baseline_vol
    adj   = math.exp(sensitivity * ratio)
    return max(0.5, min(3.0, adj))


def volatility_adjusted_decay(
    initial:      float,
    base_rate:    float,
    t:            int,
    current_vol:  float,
    baseline_vol: float = 0.20,
    sensitivity:  float = 2.0,
) -> float:
    """
    波动率调整衰减。

    λ_vol = λ_base · adj_factor(vol)
    S(t)  = S₀ · e^(-λ_vol · t)
    """
    adj  = volatility_adjustment_factor(current_vol, baseline_vol, sensitivity)
    rate = base_rate * adj
    return exponential_decay(initial, rate, t)


# ── 综合衰减计算 ──────────────────────────────────────────────────────

def compute_decay_metrics(
    age_bars:     int,
    base_rate:    float,
    initial:      float        = 1.0,
    regime:       RegimeType   = RegimeType.UNKNOWN,
    phase:        CyclePhase   = CyclePhase.UNKNOWN,
    current_vol:  float        = 0.20,
    baseline_vol: float        = 0.20,
    vol_sensitivity: float     = 2.0,
    min_threshold: float       = 0.05,
    weights: tuple[float, float, float] = (0.40, 0.35, 0.25),
) -> DecayMetrics:
    """
    计算三种衰减模式的综合 DecayMetrics。

    Args:
        age_bars:        Alpha 已存续的 bar 数
        base_rate:       基础衰减率 λ
        initial:         初始强度（通常为 1.0）
        regime:          当前市场 Regime
        phase:           当前周期阶段
        current_vol:     当前年化波动率
        baseline_vol:    基准波动率
        vol_sensitivity: 波动率调整敏感度
        min_threshold:   到期判断阈值
        weights:         三种模式权重 (exp, regime, vol)，需合计 ≤ 1

    Returns:
        DecayMetrics
    """
    t = age_bars

    exp_s  = exponential_decay(initial, base_rate, t)
    reg_s  = regime_dependent_decay(initial, base_rate, t, regime, phase)
    vol_s  = volatility_adjusted_decay(
        initial, base_rate, t, current_vol, baseline_vol, vol_sensitivity)

    w_e, w_r, w_v = weights
    w_sum = w_e + w_r + w_v
    combined = (w_e * exp_s + w_r * reg_s + w_v * vol_s) / w_sum

    vol_adj = volatility_adjustment_factor(current_vol, baseline_vol, vol_sensitivity)
    r_penalty = regime_penalty(regime, phase)

    hl   = rate_to_half_life(base_rate)
    exp_bar = expected_expiry_bar(combined, base_rate, min_threshold)

    return DecayMetrics(
        exponential_strength  = round(max(0.0, exp_s), 6),
        regime_strength       = round(max(0.0, reg_s), 6),
        volatility_strength   = round(max(0.0, vol_s), 6),
        combined_strength     = round(max(0.0, min(1.0, combined)), 6),
        half_life             = round(hl, 4),
        decay_rate            = round(base_rate, 8),
        age_bars              = t,
        regime_penalty        = round(r_penalty, 4),
        volatility_adjustment = round(vol_adj, 4),
    )


# ── 衰减曲线生成 ──────────────────────────────────────────────────────

def build_decay_curve(
    alpha_id:     str,
    mode:         DecayMode,
    current_age:  int,
    base_rate:    float,
    initial:      float        = 1.0,
    horizon:      int          = 60,
    regime:       RegimeType   = RegimeType.UNKNOWN,
    phase:        CyclePhase   = CyclePhase.UNKNOWN,
    current_vol:  float        = 0.20,
    baseline_vol: float        = 0.20,
    vol_sensitivity: float     = 2.0,
) -> DecayCurve:
    """
    生成从当前 age 开始、未来 horizon 个 bar 的衰减曲线。

    曲线仅反映"当前参数下的衰减趋势"，不是价格预测。
    """
    points: list[DecayCurvePoint] = []

    for i in range(horizon + 1):
        t = current_age + i
        if mode == DecayMode.EXPONENTIAL:
            s = exponential_decay(initial, base_rate, t)
        elif mode == DecayMode.REGIME_DEPENDENT:
            s = regime_dependent_decay(initial, base_rate, t, regime, phase)
        else:
            s = volatility_adjusted_decay(
                initial, base_rate, t, current_vol, baseline_vol, vol_sensitivity)

        points.append(DecayCurvePoint(bar=i, strength=round(max(0.0, s), 6)))

    return DecayCurve(alpha_id=alpha_id, mode=mode, points=points)
