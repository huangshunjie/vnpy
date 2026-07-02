"""
market_regime_ai/utils/trend_utils.py  (Phase 3)

趋势工具函数 — 完整实现。

实现：
  - compute_linear_regression   线性回归（斜率 / R²）
  - compute_trend_strength      趋势强度 [0,1]
  - compute_trend_persistence   趋势持续性 [0,1]
  - classify_trend_direction    趋势方向分类
  - compute_adx_proxy           ADX 代理（无需 High/Low，仅用收盘价）
  - compute_ema                 指数移动平均
  - compute_sma                 简单移动平均

❌ 无 IO / 无网络 / 纯计算
"""

from __future__ import annotations
import math
from ..constant import TrendDirection


# ─────────────────────────────────────────────────────────────────────────────
#  移动平均
# ─────────────────────────────────────────────────────────────────────────────

def compute_sma(prices: list[float], window: int) -> float:
    """简单移动平均。"""
    if len(prices) < window:
        return prices[-1] if prices else 0.0
    recent = prices[-window:]
    return round(sum(recent) / len(recent), 6)


def compute_ema(
    prices: list[float],
    window: int,
    smoothing: float = 2.0,
) -> float:
    """
    指数移动平均（最后一个值）。

    alpha = smoothing / (window + 1)
    """
    if not prices:
        return 0.0
    alpha = smoothing / (window + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = alpha * p + (1 - alpha) * ema
    return round(ema, 6)


def compute_ema_series(
    prices:    list[float],
    window:    int,
    smoothing: float = 2.0,
) -> list[float]:
    """返回完整 EMA 序列。"""
    if not prices:
        return []
    alpha = smoothing / (window + 1)
    result = [prices[0]]
    for p in prices[1:]:
        result.append(alpha * p + (1 - alpha) * result[-1])
    return [round(v, 6) for v in result]


# ─────────────────────────────────────────────────────────────────────────────
#  线性回归
# ─────────────────────────────────────────────────────────────────────────────

def compute_linear_regression(
    values: list[float],
    window: int = 20,
) -> tuple[float, float]:
    """
    对最近 window 个值做线性回归。

    Returns
    -------
    (slope, r_squared)
      slope     : 斜率（已按均值标准化）
      r_squared : 拟合优度 [0, 1]
    """
    data = values[-window:]
    n = len(data)
    if n < 3:
        return 0.0, 0.0

    x_mean = (n - 1) / 2.0
    y_mean = sum(data) / n

    ss_xy = sum((i - x_mean) * (data[i] - y_mean) for i in range(n))
    ss_xx = sum((i - x_mean) ** 2 for i in range(n))
    ss_yy = sum((v - y_mean) ** 2 for v in data)

    if ss_xx < 1e-12:
        return 0.0, 0.0

    slope = ss_xy / ss_xx

    # 标准化斜率：除以均值（避免价格量纲影响）
    if abs(y_mean) > 1e-12:
        normalized_slope = slope / y_mean
    else:
        normalized_slope = slope

    r_squared = 0.0
    if ss_yy > 1e-12:
        r_squared = min(1.0, (ss_xy ** 2) / (ss_xx * ss_yy))

    return round(normalized_slope, 8), round(r_squared, 6)


# ─────────────────────────────────────────────────────────────────────────────
#  趋势强度
# ─────────────────────────────────────────────────────────────────────────────

def compute_trend_strength(
    prices:    list[float],
    window:    int   = 20,
    r2_weight: float = 0.6,
    ma_weight: float = 0.4,
) -> float:
    """
    趋势强度 [0, 1]。

    公式：
        strength = r2_weight × R²
                 + ma_weight × |price_vs_ma_ratio|（截断到 [0, 1]）

    R² 越高 + 价格偏离均线越远 → 趋势越强。

    Parameters
    ----------
    prices    : 价格序列
    window    : 回归窗口
    r2_weight : R² 的权重
    ma_weight : MA 偏离度的权重

    Returns
    -------
    float [0, 1]
    """
    if len(prices) < 3:
        return 0.0

    _, r2 = compute_linear_regression(prices, window)

    # 价格 vs SMA 偏离度（标准化到 [0, 1]）
    sma = compute_sma(prices, window)
    if sma > 1e-12:
        ma_dev = abs(prices[-1] - sma) / sma
        ma_score = min(1.0, ma_dev * 10)  # 偏离 10% 即满分
    else:
        ma_score = 0.0

    strength = r2_weight * r2 + ma_weight * ma_score
    return round(min(1.0, max(0.0, strength)), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  趋势方向分类
# ─────────────────────────────────────────────────────────────────────────────

def classify_trend_direction(
    slope:            float,
    strength:         float,
    strong_threshold: float = 0.50,
    weak_threshold:   float = 0.20,
) -> TrendDirection:
    """
    将斜率 + 强度映射到趋势方向。

    slope > 0, strength > strong_threshold → STRONG_UP
    slope > 0, strength > weak_threshold   → WEAK_UP
    slope < 0, strength > strong_threshold → STRONG_DOWN
    slope < 0, strength > weak_threshold   → WEAK_DOWN
    else                                   → FLAT
    """
    if strength < weak_threshold:
        return TrendDirection.FLAT

    if slope > 0:
        if strength >= strong_threshold:
            return TrendDirection.STRONG_UP
        return TrendDirection.WEAK_UP
    elif slope < 0:
        if strength >= strong_threshold:
            return TrendDirection.STRONG_DOWN
        return TrendDirection.WEAK_DOWN
    return TrendDirection.FLAT


# ─────────────────────────────────────────────────────────────────────────────
#  趋势持续性
# ─────────────────────────────────────────────────────────────────────────────

def compute_trend_persistence(
    directions: list[TrendDirection],
    window:     int = 10,
) -> float:
    """
    趋势持续性：最近 window 个 bar 中同方向占比。

    上涨类（STRONG_UP / WEAK_UP）和下跌类（STRONG_DOWN / WEAK_DOWN）
    分别计算，取最大值作为持续性。

    Returns
    -------
    float [0, 1]
    """
    if not directions:
        return 0.0
    recent = directions[-window:]
    n = len(recent)
    if n == 0:
        return 0.0

    up_set   = {TrendDirection.STRONG_UP, TrendDirection.WEAK_UP}
    down_set = {TrendDirection.STRONG_DOWN, TrendDirection.WEAK_DOWN}

    up_count   = sum(1 for d in recent if d in up_set)
    down_count = sum(1 for d in recent if d in down_set)

    return round(max(up_count, down_count) / n, 6)


# ─────────────────────────────────────────────────────────────────────────────
#  ADX 代理（仅用收盘价）
# ─────────────────────────────────────────────────────────────────────────────

def compute_adx_proxy(
    prices: list[float],
    window: int = 14,
) -> float:
    """
    ADX 代理指标 [0, 100]（仅用收盘价序列模拟）。

    实现：基于价格变动的方向性运动指数简化版。
    正向变动 > 负向变动 → 上涨趋势；反之下跌趋势。
    ADX = 100 × |DI+ - DI-| / (DI+ + DI-)

    Returns
    -------
    float [0, 100]
    """
    if len(prices) < window + 1:
        return 0.0

    moves = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    recent = moves[-window:]

    pos_sum = sum(m for m in recent if m > 0)
    neg_sum = sum(abs(m) for m in recent if m < 0)
    total   = pos_sum + neg_sum

    if total < 1e-12:
        return 0.0

    adx = 100.0 * abs(pos_sum - neg_sum) / total
    return round(min(100.0, adx), 4)
