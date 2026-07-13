"""
temporal_intelligence_ai/utils/transition_utils.py

Regime 状态转移检测工具函数。

三类检测器：
  1. Regime Shift Detection      — 基于滚动均值漂移检测
  2. Volatility Break Detection  — 基于波动率结构突变
  3. Liquidity Regime Detection  — 基于成交量/价格冲击比率变化

所有函数严格只使用历史已知数据，无前瞻偏差。
"""
from __future__ import annotations

import math
from typing import List, Dict

from ..constant import RegimeType, TransitionType
from ..model.transition_model import TransitionSignal, RegimeProbability


# ── 基础统计 ─────────────────────────────────────────────────────────

def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var)


def _ema(series: List[float], span: int) -> float:
    """指数加权均值（最新 span 个点）。"""
    if not series:
        return 0.0
    alpha = 2.0 / (span + 1)
    result = series[0]
    for v in series[1:]:
        result = alpha * v + (1 - alpha) * result
    return result


# ── 1. Regime Shift Detection ────────────────────────────────────────

def detect_regime_shift(
    returns:       List[float],
    fast_window:   int   = 10,
    slow_window:   int   = 40,
    threshold:     float = 2.0,
) -> TransitionSignal:
    """
    基于滚动均值 CUSUM 漂移检测 Regime 切换。

    当快速均值与慢速均值的标准化差值超过阈值时，
    判定为 Regime Shift 信号。

    strength = |fast_mean - slow_mean| / slow_std，归一化至 [0, 1]
    """
    n = len(returns)
    if n < slow_window + 1:
        return TransitionSignal(
            signal_type  = TransitionType.REGIME_SHIFT,
            strength     = 0.0,
            is_triggered = False,
            threshold    = threshold,
            raw_value    = 0.0,
            description  = "数据不足",
        )

    fast_tail = returns[-fast_window:]
    slow_tail = returns[-slow_window:]

    fast_mean = _mean(fast_tail)
    slow_mean = _mean(slow_tail)
    slow_std  = _std(slow_tail)

    if slow_std == 0:
        raw = 0.0
    else:
        raw = abs(fast_mean - slow_mean) / slow_std

    strength     = min(1.0, raw / threshold)
    is_triggered = raw > threshold

    return TransitionSignal(
        signal_type  = TransitionType.REGIME_SHIFT,
        strength     = round(strength, 6),
        is_triggered = is_triggered,
        threshold    = threshold,
        raw_value    = round(raw, 6),
        description  = f"均值漂移 z={raw:.2f}  阈值={threshold}",
    )


# ── 2. Volatility Break Detection ────────────────────────────────────

def detect_volatility_break(
    prices:        List[float],
    short_window:  int   = 10,
    long_window:   int   = 40,
    break_ratio:   float = 1.8,
) -> TransitionSignal:
    """
    波动率结构突变检测。

    当短期年化波动率 / 长期年化波动率 > break_ratio（或 < 1/break_ratio）时，
    判定为 Volatility Break 信号。

    strength = |short_vol / long_vol - 1|，归一化至 [0, 1]
    """
    n = len(prices)
    if n < long_window + 1:
        return TransitionSignal(
            signal_type  = TransitionType.VOLATILITY_BREAK,
            strength     = 0.0,
            is_triggered = False,
            threshold    = break_ratio,
            raw_value    = 0.0,
            description  = "数据不足",
        )

    def _vol(px: List[float]) -> float:
        if len(px) < 2:
            return 0.0
        log_r = [
            math.log(px[i] / px[i - 1])
            for i in range(1, len(px))
            if px[i - 1] > 0 and px[i] > 0
        ]
        return _std(log_r) * math.sqrt(252) if log_r else 0.0

    short_vol = _vol(prices[-short_window - 1:])
    long_vol  = _vol(prices[-long_window - 1:])

    if long_vol == 0:
        ratio = 1.0
    else:
        ratio = short_vol / long_vol

    raw      = abs(ratio - 1.0)
    strength = min(1.0, raw / (break_ratio - 1.0))
    is_trig  = ratio > break_ratio or ratio < (1.0 / break_ratio)

    return TransitionSignal(
        signal_type  = TransitionType.VOLATILITY_BREAK,
        strength     = round(strength, 6),
        is_triggered = is_trig,
        threshold    = break_ratio,
        raw_value    = round(ratio, 6),
        description  = f"波动率比值={ratio:.2f}  阈值={break_ratio}",
    )


# ── 3. Liquidity Regime Detection ────────────────────────────────────

def detect_liquidity_regime(
    volumes:       List[float],
    returns:       List[float],
    short_window:  int   = 10,
    long_window:   int   = 40,
    threshold:     float = 1.5,
) -> TransitionSignal:
    """
    流动性 Regime 变化检测。

    使用 Amihud 非流动性比率的变化：
    ILLIQ = |return| / volume

    短期 ILLIQ 均值 / 长期 ILLIQ 均值 > threshold 时触发。

    strength = ratio 归一化至 [0, 1]
    """
    n = min(len(volumes), len(returns))
    if n < long_window:
        return TransitionSignal(
            signal_type  = TransitionType.LIQUIDITY_REGIME,
            strength     = 0.0,
            is_triggered = False,
            threshold    = threshold,
            raw_value    = 0.0,
            description  = "数据不足",
        )

    vols = volumes[-n:]
    rets = returns[-n:]

    illiq = [
        abs(rets[i]) / vols[i] if vols[i] > 0 else 0.0
        for i in range(n)
    ]

    short_illiq = _mean(illiq[-short_window:])
    long_illiq  = _mean(illiq[-long_window:])

    if long_illiq == 0:
        ratio = 1.0
    else:
        ratio = short_illiq / long_illiq

    strength = min(1.0, abs(ratio - 1.0) / (threshold - 1.0))
    is_trig  = ratio > threshold or ratio < (1.0 / threshold)

    return TransitionSignal(
        signal_type  = TransitionType.LIQUIDITY_REGIME,
        strength     = round(strength, 6),
        is_triggered = is_trig,
        threshold    = threshold,
        raw_value    = round(ratio, 6),
        description  = f"ILLIQ 比值={ratio:.2f}  阈值={threshold}",
    )


# ── Regime 概率估计 ──────────────────────────────────────────────────

def estimate_regime_probabilities(
    volatility:   float,
    trend:        float,
    regime_signal_strength:    float,
    volatility_signal_strength: float,
) -> RegimeProbability:
    """
    基于当前波动率、趋势方向和检测信号强度，
    估算各 Regime 的后验概率分布。

    使用规则权重法（非 HMM），保持轻量可解释。
    """
    raw: Dict[str, float] = {}

    # 基础得分：从波动率和趋势划分
    if volatility > 0.45:
        raw[RegimeType.CRISIS.value]        = 0.60
        raw[RegimeType.BEAR_VOLATILE.value] = 0.25
        raw[RegimeType.BULL_VOLATILE.value] = 0.10
        raw[RegimeType.SIDEWAYS.value]      = 0.03
        raw[RegimeType.BULL_QUIET.value]    = 0.01
        raw[RegimeType.BEAR_QUIET.value]    = 0.01
    elif trend > 0.10:
        if volatility > 0.22:
            raw[RegimeType.BULL_VOLATILE.value] = 0.55
            raw[RegimeType.BULL_QUIET.value]    = 0.20
            raw[RegimeType.SIDEWAYS.value]      = 0.12
            raw[RegimeType.BEAR_VOLATILE.value] = 0.08
            raw[RegimeType.BEAR_QUIET.value]    = 0.03
            raw[RegimeType.CRISIS.value]        = 0.02
        else:
            raw[RegimeType.BULL_QUIET.value]    = 0.60
            raw[RegimeType.BULL_VOLATILE.value] = 0.20
            raw[RegimeType.SIDEWAYS.value]      = 0.12
            raw[RegimeType.BEAR_QUIET.value]    = 0.05
            raw[RegimeType.BEAR_VOLATILE.value] = 0.02
            raw[RegimeType.CRISIS.value]        = 0.01
    elif trend < -0.10:
        if volatility > 0.22:
            raw[RegimeType.BEAR_VOLATILE.value] = 0.55
            raw[RegimeType.BEAR_QUIET.value]    = 0.20
            raw[RegimeType.SIDEWAYS.value]      = 0.12
            raw[RegimeType.BULL_VOLATILE.value] = 0.08
            raw[RegimeType.BULL_QUIET.value]    = 0.03
            raw[RegimeType.CRISIS.value]        = 0.02
        else:
            raw[RegimeType.BEAR_QUIET.value]    = 0.60
            raw[RegimeType.BEAR_VOLATILE.value] = 0.20
            raw[RegimeType.SIDEWAYS.value]      = 0.12
            raw[RegimeType.BULL_QUIET.value]    = 0.05
            raw[RegimeType.BULL_VOLATILE.value] = 0.02
            raw[RegimeType.CRISIS.value]        = 0.01
    else:
        raw[RegimeType.SIDEWAYS.value]      = 0.55
        raw[RegimeType.BULL_QUIET.value]    = 0.18
        raw[RegimeType.BEAR_QUIET.value]    = 0.14
        raw[RegimeType.BULL_VOLATILE.value] = 0.07
        raw[RegimeType.BEAR_VOLATILE.value] = 0.05
        raw[RegimeType.CRISIS.value]        = 0.01

    # 转移信号会提升不确定性（把概率向 UNKNOWN 方向稀释）
    uncertainty = (regime_signal_strength + volatility_signal_strength) / 2
    if uncertainty > 0:
        for k in raw:
            raw[k] = raw[k] * (1.0 - uncertainty * 0.3)
        raw[RegimeType.UNKNOWN.value] = uncertainty * 0.3

    # 归一化
    total = sum(raw.values())
    if total > 0:
        probs = {k: round(v / total, 4) for k, v in raw.items()}
    else:
        probs = {RegimeType.UNKNOWN.value: 1.0}

    return RegimeProbability(probabilities=probs)


# ── 综合转移概率 ──────────────────────────────────────────────────────

def compute_transition_probability(
    regime_signal:     TransitionSignal,
    volatility_signal: TransitionSignal,
    liquidity_signal:  TransitionSignal,
    weights: tuple[float, float, float] = (0.45, 0.35, 0.20),
) -> tuple[float, float]:
    """
    综合三类信号计算转移概率与置信度。

    Returns:
        (transition_prob, confidence)
    """
    w_r, w_v, w_l = weights
    prob = (
        w_r * regime_signal.strength
        + w_v * volatility_signal.strength
        + w_l * liquidity_signal.strength
    )

    triggered = sum([
        regime_signal.is_triggered,
        volatility_signal.is_triggered,
        liquidity_signal.is_triggered,
    ])
    confidence = triggered / 3.0

    return round(min(1.0, prob), 6), round(confidence, 6)
