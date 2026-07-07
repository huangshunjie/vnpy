"""
temporal_intelligence_ai/utils/cycle_utils.py

市场周期分析工具函数。

所有函数只消费历史数据，严格禁止任何前瞻偏差。
输入：价格序列 / 成交量序列（list[float]，时间升序）
输出：标量或枚举，供 CycleEngine 调用
"""
from __future__ import annotations

import math
from typing import List

from ..constant import CyclePhase, RegimeType


# ── 基础统计 ─────────────────────────────────────────────────────────

def rolling_returns(prices: List[float], window: int = 1) -> List[float]:
    """计算滚动 window 期收益率序列。"""
    if len(prices) < window + 1:
        return []
    return [
        (prices[i] - prices[i - window]) / prices[i - window]
        if prices[i - window] != 0 else 0.0
        for i in range(window, len(prices))
    ]


def annualized_volatility(prices: List[float], window: int = 20,
                           periods_per_year: int = 252) -> float:
    """
    计算最近 window 期年化波动率。

    使用对数收益率，避免价格量纲影响。
    """
    if len(prices) < window + 1:
        return 0.0
    tail = prices[-(window + 1):]
    log_rets = [
        math.log(tail[i] / tail[i - 1])
        for i in range(1, len(tail))
        if tail[i - 1] > 0 and tail[i] > 0
    ]
    if len(log_rets) < 2:
        return 0.0
    mean = sum(log_rets) / len(log_rets)
    variance = sum((r - mean) ** 2 for r in log_rets) / (len(log_rets) - 1)
    return math.sqrt(variance * periods_per_year)


def trend_strength(prices: List[float], fast: int = 10,
                   slow: int = 30) -> float:
    """
    趋势强度指标 [-1, 1]。

    基于快慢均线差值归一化，正值代表上行趋势，负值代表下行。
    """
    if len(prices) < slow:
        return 0.0
    fast_ma = sum(prices[-fast:]) / fast
    slow_ma = sum(prices[-slow:]) / slow
    if slow_ma == 0:
        return 0.0
    raw = (fast_ma - slow_ma) / slow_ma
    return max(-1.0, min(1.0, raw * 10))


def momentum_score(prices: List[float], window: int = 20) -> float:
    """滚动 window 期累计收益率（动量）。"""
    if len(prices) < window + 1:
        return 0.0
    base = prices[-(window + 1)]
    if base == 0:
        return 0.0
    return (prices[-1] - base) / base


def max_drawdown(prices: List[float], window: int = 60) -> float:
    """最近 window 期最大回撤（负值）。"""
    tail = prices[-window:] if len(prices) >= window else prices
    if not tail:
        return 0.0
    peak = tail[0]
    mdd  = 0.0
    for p in tail:
        if p > peak:
            peak = p
        dd = (p - peak) / peak if peak > 0 else 0.0
        if dd < mdd:
            mdd = dd
    return mdd


def market_breadth(returns: List[float]) -> float:
    """
    市场宽度：上涨品种占比 [0, 1]。

    Args:
        returns: 同一时间截面各品种的收益率列表
    """
    if not returns:
        return 0.5
    up = sum(1 for r in returns if r > 0)
    return up / len(returns)


def cross_asset_correlation(series_a: List[float],
                            series_b: List[float],
                            window: int = 20) -> float:
    """
    两资产序列最近 window 期皮尔逊相关系数。

    返回 [-1, 1]，缺失数据时返回 0.0。
    """
    n = min(window, len(series_a), len(series_b))
    if n < 4:
        return 0.0
    a = series_a[-n:]
    b = series_b[-n:]
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    cov  = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    std_a = math.sqrt(sum((x - mean_a) ** 2 for x in a))
    std_b = math.sqrt(sum((x - mean_b) ** 2 for x in b))
    denom = std_a * std_b
    return cov / denom if denom > 0 else 0.0


# ── 周期阶段识别 ──────────────────────────────────────────────────────

def identify_cycle_phase(
    volatility:      float,
    trend:           float,
    momentum:        float,
    drawdown:        float,
    breadth:         float,
) -> tuple[CyclePhase, float]:
    """
    基于五因子规则引擎识别周期阶段，返回 (phase, confidence)。

    规则逻辑（基于宏观周期理论，无前瞻偏差）：
      EXPANSION   : trend > 0.15,  momentum > 0,    breadth > 0.55, vol < 0.25
      PEAK        : trend > 0.05,  momentum > 0,    breadth < 0.50, vol > 0.20
      CONTRACTION : trend < -0.10, momentum < 0,    breadth < 0.45
      TROUGH      : trend < -0.05, drawdown < -0.15, breadth < 0.40, vol > 0.30
      TRANSITION  : 其余模糊区域

    置信度由满足规则数量 / 规则总数线性映射。
    """
    scores: dict[CyclePhase, int] = {p: 0 for p in CyclePhase}
    total_rules = 4

    # EXPANSION
    if trend > 0.15:       scores[CyclePhase.EXPANSION] += 1
    if momentum > 0.01:    scores[CyclePhase.EXPANSION] += 1
    if breadth > 0.55:     scores[CyclePhase.EXPANSION] += 1
    if volatility < 0.25:  scores[CyclePhase.EXPANSION] += 1

    # PEAK
    if 0.0 < trend <= 0.20:  scores[CyclePhase.PEAK] += 1
    if momentum > 0.0:        scores[CyclePhase.PEAK] += 1
    if breadth < 0.52:        scores[CyclePhase.PEAK] += 1
    if volatility > 0.18:     scores[CyclePhase.PEAK] += 1

    # CONTRACTION
    if trend < -0.10:      scores[CyclePhase.CONTRACTION] += 1
    if momentum < -0.01:   scores[CyclePhase.CONTRACTION] += 1
    if breadth < 0.45:     scores[CyclePhase.CONTRACTION] += 1
    if drawdown < -0.08:   scores[CyclePhase.CONTRACTION] += 1

    # TROUGH
    if trend < -0.05:      scores[CyclePhase.TROUGH] += 1
    if drawdown < -0.15:   scores[CyclePhase.TROUGH] += 1
    if breadth < 0.40:     scores[CyclePhase.TROUGH] += 1
    if volatility > 0.30:  scores[CyclePhase.TROUGH] += 1

    # 取最高分阶段，同分时优先 TRANSITION
    best_phase = CyclePhase.TRANSITION
    best_score = 0
    for phase, score in scores.items():
        if phase == CyclePhase.UNKNOWN:
            continue
        if score > best_score:
            best_score = score
            best_phase = phase

    if best_score == 0:
        return CyclePhase.UNKNOWN, 0.0

    confidence = best_score / total_rules
    return best_phase, round(confidence, 4)


def classify_regime(
    volatility: float,
    trend:      float,
) -> RegimeType:
    """
    基于波动率与趋势方向分类市场 Regime。

    高波动阈值：annualized vol > 0.35
    危机阈值  ：annualized vol > 0.55
    """
    if volatility > 0.55:
        return RegimeType.CRISIS
    if trend > 0.05:
        return RegimeType.BULL_VOLATILE if volatility > 0.25 else RegimeType.BULL_QUIET
    if trend < -0.05:
        return RegimeType.BEAR_VOLATILE if volatility > 0.25 else RegimeType.BEAR_QUIET
    return RegimeType.SIDEWAYS
