"""
temporal_intelligence_ai/utils/dependency_utils.py

时间依赖分析工具函数。

Signal(t) = f(Signal(t-1), Signal(t-5), Signal(t-n))

核心分析：
  1. 自相关（AutoCorrelation）    — 信号自身的时间记忆结构
  2. 偏自相关（Partial AutoCorr） — 控制中间滞后后的净依赖
  3. 互相关（CrossCorrelation）   — 信号间领先/滞后关系
  4. 时间维度分解                  — 短/中/长期贡献度拆解

所有函数严格只使用历史已知数据，无前瞻偏差。
"""
from __future__ import annotations

import math
from typing import List, Tuple

from ..constant import SignalHorizon
from ..model.dependency_model import (
    LagCorrelation,
    AutoCorrResult,
    CrossCorrResult,
    HorizonDecomposition,
)


# ── 基础统计工具 ─────────────────────────────────────────────────────

def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var)


def _pearson(xs: List[float], ys: List[float]) -> float:
    """皮尔逊相关系数，序列长度不一时取最短。"""
    n = min(len(xs), len(ys))
    if n < 4:
        return 0.0
    x, y = xs[-n:], ys[-n:]
    mx, my = _mean(x), _mean(y)
    cov  = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    sx   = math.sqrt(sum((v - mx) ** 2 for v in x))
    sy   = math.sqrt(sum((v - my) ** 2 for v in y))
    return cov / (sx * sy) if sx * sy > 0 else 0.0


def significance_threshold(n: int, alpha: float = 0.05) -> float:
    """
    自相关显著性临界值（Bartlett 近似）。

    threshold ≈ z_{α/2} / sqrt(n)
    alpha=0.05 → z = 1.96
    """
    if n <= 0:
        return 1.0
    return 1.96 / math.sqrt(n)


# ── 自相关分析 ────────────────────────────────────────────────────────

def autocorrelation_at_lag(series: List[float], lag: int) -> float:
    """
    计算序列在指定滞后阶 k 的自相关系数。

    r(k) = cov(x_t, x_{t-k}) / var(x)
    """
    n = len(series)
    if lag <= 0 or lag >= n:
        return 0.0
    x_t   = series[lag:]
    x_lag = series[:-lag]
    return _pearson(x_t, x_lag)


def compute_autocorr(
    signal_id: str,
    series:    List[float],
    max_lag:   int = 30,
) -> AutoCorrResult:
    """
    计算信号的完整自相关结构（lag 1 到 max_lag）。

    同时计算：
      - peak_lag：绝对相关最大的滞后阶
      - memory_score：加权综合记忆强度 [0, 1]
        (短期滞后权重更高，代表"现时记忆")
    """
    n     = len(series)
    lags: List[LagCorrelation] = []
    thresh = significance_threshold(n)

    peak_corr = 0.0
    peak_lag  = 1

    for k in range(1, min(max_lag + 1, n)):
        r = autocorrelation_at_lag(series, k)
        is_sig = abs(r) > thresh
        lags.append(LagCorrelation(lag=k, correlation=r, is_significant=is_sig))
        if abs(r) > abs(peak_corr):
            peak_corr = r
            peak_lag  = k

    # 加权记忆强度：lag 越小权重越大
    total_w = 0.0
    w_sum   = 0.0
    for lc in lags:
        w = 1.0 / lc.lag
        w_sum   += w * abs(lc.correlation)
        total_w += w
    memory_score = w_sum / total_w if total_w > 0 else 0.0

    # 划分时间维度
    if max_lag <= 5:
        horizon = SignalHorizon.SHORT_TERM
    elif max_lag <= 20:
        horizon = SignalHorizon.MID_TERM
    else:
        horizon = SignalHorizon.LONG_TERM

    return AutoCorrResult(
        signal_id    = signal_id,
        horizon      = horizon,
        lags         = lags,
        max_lag      = max_lag,
        peak_lag     = peak_lag,
        peak_corr    = round(abs(peak_corr), 6),
        memory_score = round(min(1.0, memory_score), 6),
    )


# ── 偏自相关（Durbin–Levinson 递推） ─────────────────────────────────

def partial_autocorrelation(series: List[float], max_lag: int = 20) -> List[float]:
    """
    计算偏自相关系数序列（PACF），使用 Durbin–Levinson 递推算法。

    返回长度为 max_lag 的列表，index 0 对应 lag=1。
    """
    n = len(series)
    if n < 4:
        return [0.0] * max_lag

    max_lag = min(max_lag, n - 1)
    # 先获取全序列自相关值
    acf = [1.0] + [autocorrelation_at_lag(series, k)
                   for k in range(1, max_lag + 1)]

    pacf_vals: List[float] = []
    phi = [[0.0] * (max_lag + 1) for _ in range(max_lag + 1)]

    for k in range(1, max_lag + 1):
        if k == 1:
            phi[1][1] = acf[1]
        else:
            num = acf[k] - sum(phi[k - 1][j] * acf[k - j] for j in range(1, k))
            den = 1.0 - sum(phi[k - 1][j] * acf[j] for j in range(1, k))
            phi[k][k] = num / den if den != 0 else 0.0
            for j in range(1, k):
                phi[k][j] = phi[k - 1][j] - phi[k][k] * phi[k - 1][k - j]
        pacf_vals.append(round(phi[k][k], 6))

    # 补齐长度
    while len(pacf_vals) < max_lag:
        pacf_vals.append(0.0)
    return pacf_vals[:max_lag]


# ── 互相关分析 ────────────────────────────────────────────────────────

def cross_correlation_at_lag(
    series_a: List[float],
    series_b: List[float],
    lag: int,
) -> float:
    """
    计算 series_a(t) 与 series_b(t-lag) 的互相关系数。

    lag > 0：a 领先 b；lag < 0：b 领先 a
    """
    if lag == 0:
        return _pearson(series_a, series_b)
    elif lag > 0:
        return _pearson(series_a[lag:], series_b[:-lag])
    else:
        k = -lag
        return _pearson(series_a[:-k], series_b[k:])


def compute_crosscorr(
    signal_a:  str,
    series_a:  List[float],
    signal_b:  str,
    series_b:  List[float],
    max_lag:   int = 20,
) -> CrossCorrResult:
    """
    计算两信号之间的互相关结构。

    扫描 lag ∈ [-max_lag, max_lag]，找到领先/滞后关系与峰值相关。
    """
    n      = min(len(series_a), len(series_b))
    thresh = significance_threshold(n)
    lags:  List[LagCorrelation] = []

    peak_corr = 0.0
    peak_lag  = 0

    for k in range(-max_lag, max_lag + 1):
        r    = cross_correlation_at_lag(series_a, series_b, k)
        is_s = abs(r) > thresh
        lags.append(LagCorrelation(lag=k, correlation=r, is_significant=is_s))
        if abs(r) > abs(peak_corr):
            peak_corr = r
            peak_lag  = k

    dep_strength = min(1.0, abs(peak_corr) * 1.5)

    return CrossCorrResult(
        signal_a            = signal_a,
        signal_b            = signal_b,
        lags                = lags,
        lead_lag            = peak_lag,
        peak_corr           = round(peak_corr, 6),
        dependency_strength = round(dep_strength, 6),
    )


# ── 时间维度分解 ──────────────────────────────────────────────────────

def decompose_horizons(
    series:       List[float],
    short_range:  Tuple[int, int] = (1, 5),
    mid_range:    Tuple[int, int] = (5, 20),
    long_range:   Tuple[int, int] = (20, 60),
) -> HorizonDecomposition:
    """
    将自相关结构分解为短/中/长三个时间维度的贡献度。

    贡献度 = 该时间窗口内所有显著自相关系数绝对值之和 / 总和

    Signal(t) = f(Signal(t-1), Signal(t-5), Signal(t-n)) 的量化表达。
    """
    n      = len(series)
    thresh = significance_threshold(n)

    def band_power(lo: int, hi: int) -> float:
        total = 0.0
        count = 0
        for k in range(lo, min(hi, n)):
            r = autocorrelation_at_lag(series, k)
            if abs(r) > thresh:
                total += abs(r)
            count += 1
        return total / count if count > 0 else 0.0

    s_pw = band_power(*short_range)
    m_pw = band_power(*mid_range)
    l_pw = band_power(*long_range)
    total = s_pw + m_pw + l_pw

    if total == 0:
        return HorizonDecomposition(
            short_term_weight = 0.0,
            mid_term_weight   = 0.0,
            long_term_weight  = 0.0,
            dominant_horizon  = SignalHorizon.SHORT_TERM,
        )

    sw = s_pw / total
    mw = m_pw / total
    lw = l_pw / total

    if sw >= mw and sw >= lw:
        dom = SignalHorizon.SHORT_TERM
    elif mw >= lw:
        dom = SignalHorizon.MID_TERM
    else:
        dom = SignalHorizon.LONG_TERM

    return HorizonDecomposition(
        short_term_weight = round(sw, 4),
        mid_term_weight   = round(mw, 4),
        long_term_weight  = round(lw, 4),
        dominant_horizon  = dom,
    )


# ── 综合记忆强度 ──────────────────────────────────────────────────────

def overall_memory_score(autocorr_results: dict) -> float:
    """
    多信号综合记忆强度：所有 AutoCorrResult 的 memory_score 均值。
    """
    scores = [r.memory_score for r in autocorr_results.values()]
    return round(sum(scores) / len(scores), 4) if scores else 0.0
