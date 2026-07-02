"""
market_regime_ai/utils/volatility_utils.py  (Phase 3)

波动率工具函数 — 完整实现。

实现：
  - compute_rolling_vol        滚动波动率（年化）
  - compute_vol_percentile     历史分位数
  - compute_vol_ratio          短/长期波动率比值
  - classify_vol_regime        波动率状态分类
  - detect_vol_regime_shift    状态切换检测
  - compute_realized_vol       已实现波动率

❌ 无 IO / 无网络 / 纯计算
"""

from __future__ import annotations
import math
from ..constant import VolatilityRegime


# ─────────────────────────────────────────────────────────────────────────────
#  收益率计算
# ─────────────────────────────────────────────────────────────────────────────

def compute_returns(prices: list[float]) -> list[float]:
    """计算对数收益率序列。"""
    if len(prices) < 2:
        return []
    returns = []
    for i in range(1, len(prices)):
        p0, p1 = prices[i - 1], prices[i]
        if p0 > 1e-12 and p1 > 1e-12:
            returns.append(math.log(p1 / p0))
        else:
            returns.append(0.0)
    return returns


# ─────────────────────────────────────────────────────────────────────────────
#  滚动波动率
# ─────────────────────────────────────────────────────────────────────────────

def compute_rolling_vol(
    returns:          list[float],
    window:           int   = 20,
    annualize_factor: float = 252.0,
    min_periods:      int   = 5,
) -> float:
    """
    滚动波动率（年化标准差）。

    Parameters
    ----------
    returns          : 对数收益率序列
    window           : 滚动窗口 bar 数
    annualize_factor : 年化系数（日线=252，小时线=252*6.5）
    min_periods      : 最少有效样本数

    Returns
    -------
    float  年化波动率（0.0 表示数据不足）
    """
    if len(returns) < min_periods:
        return 0.0
    recent = returns[-window:]
    n = len(recent)
    if n < min_periods:
        return 0.0
    mean = sum(recent) / n
    variance = sum((r - mean) ** 2 for r in recent) / (n - 1)
    return round(math.sqrt(variance * annualize_factor), 6)


def compute_multi_window_vol(
    returns:          list[float],
    windows:          list[int]   = (20, 60),
    annualize_factor: float       = 252.0,
) -> dict[int, float]:
    """计算多窗口波动率。"""
    return {
        w: compute_rolling_vol(returns, window=w,
                               annualize_factor=annualize_factor)
        for w in windows
    }


def compute_realized_vol(
    returns:          list[float],
    annualize_factor: float = 252.0,
) -> float:
    """已实现波动率（全样本）。"""
    return compute_rolling_vol(
        returns, window=len(returns),
        annualize_factor=annualize_factor, min_periods=2)


# ─────────────────────────────────────────────────────────────────────────────
#  历史分位数
# ─────────────────────────────────────────────────────────────────────────────

def compute_vol_percentile(
    current_vol:  float,
    vol_history:  list[float],
    min_history:  int = 20,
) -> float:
    """
    当前波动率在历史序列中的分位数 [0, 1]。

    Parameters
    ----------
    current_vol  : 当前波动率
    vol_history  : 历史波动率序列
    min_history  : 最少历史样本数

    Returns
    -------
    float [0, 1]，0.5 表示位于中位数
    """
    if len(vol_history) < min_history:
        return 0.5
    count_below = sum(1 for v in vol_history if v < current_vol)
    return round(count_below / len(vol_history), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  短/长期比值
# ─────────────────────────────────────────────────────────────────────────────

def compute_vol_ratio(
    short_vol: float,
    long_vol:  float,
) -> float:
    """
    波动率比值 = short_vol / long_vol。

    > 1.0 : 短期波动率上升（波动率扩张）
    < 1.0 : 短期波动率收缩
    = 1.0 : 持平
    """
    if long_vol < 1e-10:
        return 1.0
    return round(short_vol / long_vol, 6)


# ─────────────────────────────────────────────────────────────────────────────
#  状态分类
# ─────────────────────────────────────────────────────────────────────────────

def classify_vol_regime(
    current_vol:   float,
    percentile:    float,
    extreme_thr:   float = 0.90,
    high_thr:      float = 0.65,
    low_thr:       float = 0.20,
) -> VolatilityRegime:
    """
    将波动率分位数映射到波动率状态。

    percentile > extreme_thr → EXTREME
    percentile > high_thr    → HIGH
    percentile < low_thr     → LOW
    else                     → NORMAL
    """
    if percentile > extreme_thr:
        return VolatilityRegime.EXTREME
    if percentile > high_thr:
        return VolatilityRegime.HIGH
    if percentile < low_thr:
        return VolatilityRegime.LOW
    return VolatilityRegime.NORMAL


# ─────────────────────────────────────────────────────────────────────────────
#  状态切换检测
# ─────────────────────────────────────────────────────────────────────────────

def detect_vol_regime_shift(
    prev_regime: VolatilityRegime,
    curr_regime: VolatilityRegime,
) -> bool:
    """检测波动率状态是否发生切换。"""
    return prev_regime != curr_regime


def detect_vol_spike(
    current_vol: float,
    avg_vol:     float,
    spike_mult:  float = 2.0,
) -> bool:
    """
    检测波动率突刺（spike）。

    当前波动率 > avg_vol × spike_mult 时触发。
    """
    if avg_vol < 1e-10:
        return False
    return (current_vol / avg_vol) >= spike_mult


# ─────────────────────────────────────────────────────────────────────────────
#  历史均值
# ─────────────────────────────────────────────────────────────────────────────

def compute_avg_vol(
    vol_history: list[float],
    window:      int = 60,
) -> float:
    """计算历史平均波动率。"""
    if not vol_history:
        return 0.0
    recent = vol_history[-window:]
    return round(sum(recent) / len(recent), 6)
