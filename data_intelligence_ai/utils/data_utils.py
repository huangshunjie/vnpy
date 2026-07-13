"""
data_intelligence_ai/utils/data_utils.py  (Phase 5)

通用数据工具函数。

- 时间戳对齐
- 数据归一化
- 滑动窗口
- 简单统计工具（无外部依赖）
"""
from __future__ import annotations
import math
from datetime import datetime, timedelta


def align_timestamps(
    series_a: list[tuple[datetime, float]],
    series_b: list[tuple[datetime, float]],
    tolerance_secs: float = 60.0,
) -> list[tuple[datetime, float, float]]:
    """
    对两个时间序列按时间戳对齐（最近邻匹配）。
    Returns [(timestamp, a_val, b_val), ...]
    """
    if not series_a or not series_b:
        return []
    result = []
    b_list = sorted(series_b, key=lambda x: x[0])
    for ts_a, val_a in series_a:
        best = min(b_list, key=lambda x: abs((x[0] - ts_a).total_seconds()))
        diff = abs((best[0] - ts_a).total_seconds())
        if diff <= tolerance_secs:
            result.append((ts_a, val_a, best[1]))
    return result


def sliding_window(
    values:      list[float],
    window_size: int,
    step:        int = 1,
) -> list[list[float]]:
    """返回滑动窗口列表。"""
    if len(values) < window_size:
        return []
    return [values[i:i + window_size]
            for i in range(0, len(values) - window_size + 1, step)]


def rolling_mean(values: list[float], n: int) -> list[float]:
    """简单滚动均值（无外部依赖）。"""
    if n <= 0 or not values:
        return []
    result = []
    for i in range(n - 1, len(values)):
        window = values[i - n + 1: i + 1]
        result.append(sum(window) / n)
    return result


def rolling_std(values: list[float], n: int) -> list[float]:
    """简单滚动标准差。"""
    if n <= 1 or not values:
        return []
    result = []
    for i in range(n - 1, len(values)):
        window = values[i - n + 1: i + 1]
        mu    = sum(window) / n
        sigma = math.sqrt(sum((x - mu) ** 2 for x in window) / n)
        result.append(sigma)
    return result


def min_max_normalize(
    values:  list[float],
    new_min: float = 0.0,
    new_max: float = 1.0,
) -> list[float]:
    """Min-max 归一化到 [new_min, new_max]。"""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [new_min] * len(values)
    scale = (new_max - new_min) / (hi - lo)
    return [round(new_min + (v - lo) * scale, 8) for v in values]


def zscore_normalize(values: list[float]) -> list[float]:
    """Z-score 标准化。"""
    if len(values) < 2:
        return [0.0] * len(values)
    mu    = sum(values) / len(values)
    sigma = math.sqrt(sum((v - mu) ** 2 for v in values) / len(values))
    if sigma < 1e-10:
        return [0.0] * len(values)
    return [round((v - mu) / sigma, 8) for v in values]


def pct_change(values: list[float]) -> list[float]:
    """逐差收益率序列。"""
    if len(values) < 2:
        return []
    result = []
    for i in range(1, len(values)):
        prev = values[i - 1]
        result.append(round((values[i] - prev) / abs(prev), 8) if prev != 0 else 0.0)
    return result


def log_returns(values: list[float]) -> list[float]:
    """对数收益率序列。"""
    if len(values) < 2:
        return []
    result = []
    for i in range(1, len(values)):
        p0, p1 = values[i - 1], values[i]
        result.append(round(math.log(p1 / p0), 8) if p0 > 0 and p1 > 0 else 0.0)
    return result


def ewma(values: list[float], alpha: float = 0.1) -> list[float]:
    """指数加权移动平均（alpha ∈ (0,1]）。"""
    if not values:
        return []
    result = [values[0]]
    for v in values[1:]:
        result.append(round(alpha * v + (1 - alpha) * result[-1], 8))
    return result


def correlation(xs: list[float], ys: list[float]) -> float:
    """Pearson 相关系数（无外部依赖）。"""
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    xs, ys = xs[:n], ys[:n]
    mx = sum(xs) / n
    my = sum(ys) / n
    num  = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx   = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy   = math.sqrt(sum((y - my) ** 2 for y in ys))
    denom = sx * sy
    return round(num / denom, 6) if denom > 1e-10 else 0.0


def compute_drawdown(equity_curve: list[float]) -> tuple[float, int]:
    """
    最大回撤及其位置。
    Returns (max_drawdown_pct, trough_index)
    """
    if len(equity_curve) < 2:
        return 0.0, 0
    peak      = equity_curve[0]
    max_dd    = 0.0
    trough_ix = 0
    for i, v in enumerate(equity_curve):
        if v > peak:
            peak = v
        dd = (peak - v) / max(peak, 1e-10)
        if dd > max_dd:
            max_dd    = dd
            trough_ix = i
    return round(max_dd, 6), trough_ix


def resample_ohlc(
    timestamps: list[datetime],
    prices:     list[float],
    period_secs:float = 60.0,
) -> list[dict]:
    """
    简单 OHLC 重采样。
    Returns [{"timestamp": dt, "open": o, "high": h, "low": l, "close": c}, ...]
    """
    if not timestamps or not prices:
        return []
    bars: list[dict] = []
    start = timestamps[0]
    bar   = {"timestamp": start, "open": prices[0],
             "high": prices[0], "low": prices[0], "close": prices[0]}
    for ts, price in zip(timestamps[1:], prices[1:]):
        if (ts - start).total_seconds() >= period_secs:
            bars.append(bar)
            start = ts
            bar   = {"timestamp": ts, "open": price,
                     "high": price, "low": price, "close": price}
        else:
            bar["high"]  = max(bar["high"], price)
            bar["low"]   = min(bar["low"],  price)
            bar["close"] = price
    bars.append(bar)
    return bars
