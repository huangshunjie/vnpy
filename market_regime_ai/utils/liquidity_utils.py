"""
market_regime_ai/utils/liquidity_utils.py  (Phase 3)

流动性工具函数 — 完整实现。

实现：
  - compute_volume_ratio        成交量比率
  - compute_turnover_ratio      换手率代理
  - compute_spread_proxy        价差代理（基于高低价或价格波动）
  - compute_illiquidity_score   Amihud 非流动性综合评分
  - classify_liquidity_level    流动性水平分类
  - compute_avg_volume          历史均量

❌ 无 IO / 无网络 / 纯计算
"""

from __future__ import annotations
import math
from ..constant import LiquidityLevel


# ─────────────────────────────────────────────────────────────────────────────
#  成交量比率
# ─────────────────────────────────────────────────────────────────────────────

def compute_volume_ratio(
    current_volume: float,
    avg_volume:     float,
) -> float:
    """
    成交量比率 = current / avg。

    > 1.0 : 放量（流动性改善）
    < 1.0 : 缩量（流动性下降）
    """
    if avg_volume < 1e-12:
        return 1.0
    return round(current_volume / avg_volume, 6)


def compute_avg_volume(
    volumes: list[float],
    window:  int = 20,
) -> float:
    """计算历史均量。"""
    if not volumes:
        return 0.0
    recent = volumes[-window:]
    return round(sum(recent) / len(recent), 6)


def compute_volume_percentile(
    current_volume: float,
    volume_history: list[float],
    min_history:    int = 20,
) -> float:
    """当前成交量在历史序列中的分位数 [0, 1]。"""
    if len(volume_history) < min_history:
        return 0.5
    count_below = sum(1 for v in volume_history if v < current_volume)
    return round(count_below / len(volume_history), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  换手率代理
# ─────────────────────────────────────────────────────────────────────────────

def compute_turnover_ratio(
    volume:         float,
    avg_volume:     float,
    price:          float,
    avg_price:      float,
) -> float:
    """
    换手率代理（归一化成交额比值）。

    turnover_ratio = (volume × price) / (avg_volume × avg_price)

    > 1.0 : 换手率上升
    < 1.0 : 换手率下降
    """
    denom = avg_volume * avg_price
    if denom < 1e-12:
        return 1.0
    return round((volume * price) / denom, 6)


# ─────────────────────────────────────────────────────────────────────────────
#  价差代理
# ─────────────────────────────────────────────────────────────────────────────

def compute_spread_proxy(
    high:  float,
    low:   float,
    close: float,
) -> float:
    """
    价差代理（基于高低价）= (high - low) / close。

    高 = 价差宽（流动性差）
    低 = 价差窄（流动性好）

    Returns
    -------
    float [0, ∞)，通常 < 0.05（5%）
    """
    if close < 1e-12:
        return 0.0
    return round((high - low) / close, 8)


def compute_spread_proxy_from_returns(
    returns: list[float],
    window:  int = 20,
) -> float:
    """
    仅有收盘价时的价差代理（基于收益率绝对值均值）。

    higher abs return → wider spread（流动性差代理）
    """
    if len(returns) < 2:
        return 0.0
    recent = returns[-window:]
    return round(sum(abs(r) for r in recent) / len(recent), 8)


# ─────────────────────────────────────────────────────────────────────────────
#  Amihud 非流动性评分
# ─────────────────────────────────────────────────────────────────────────────

def compute_amihud_illiquidity(
    returns: list[float],
    volumes: list[float],
    window:  int = 20,
) -> float:
    """
    Amihud (2002) 非流动性比率（简化版）。

    ILLIQ = mean( |return| / volume )

    高 ILLIQ → 每单位成交量引起更大价格冲击 → 流动性差

    Returns
    -------
    float [0, ∞)，已归一化到 [0, 1]（使用 sigmoid 压缩）
    """
    if len(returns) < 2 or len(volumes) < 2:
        return 0.5

    n = min(len(returns), len(volumes), window)
    rets = returns[-n:]
    vols = volumes[-n:]

    ratios = []
    for r, v in zip(rets, vols):
        if v > 1e-12:
            ratios.append(abs(r) / v)

    if not ratios:
        return 0.5

    raw = sum(ratios) / len(ratios)
    # sigmoid 压缩（scale 使 raw=1e-6 → 0.5 附近）
    scaled = raw * 1e6
    return round(1.0 / (1.0 + math.exp(-scaled + 5)), 6)


def compute_illiquidity_score(
    volume_ratio:   float,
    spread_proxy:   float,
    turnover_ratio: float,
    w_vol:          float = 0.40,
    w_spread:       float = 0.35,
    w_turnover:     float = 0.25,
) -> float:
    """
    非流动性综合评分 [0, 1]（高 = 流动性差）。

    各因子贡献：
      volume_ratio   : 低成交量 → 高非流动性
      spread_proxy   : 宽价差   → 高非流动性
      turnover_ratio : 低换手率 → 高非流动性

    Parameters
    ----------
    volume_ratio   : 成交量比率（compute_volume_ratio 输出）
    spread_proxy   : 价差代理（归一化，通常 < 0.05，需先标准化）
    turnover_ratio : 换手率比率

    Returns
    -------
    float [0, 1]
    """
    # 成交量贡献：成交量低 → 非流动性高
    vol_contrib = max(0.0, min(1.0, 1.0 - volume_ratio / 3.0))

    # 价差贡献：spread_proxy 已是 0~1 的比例（截断到合理范围）
    spread_norm  = min(1.0, spread_proxy * 20.0)   # 5% → 1.0

    # 换手率贡献：换手率低 → 非流动性高
    turn_contrib = max(0.0, min(1.0, 1.0 - turnover_ratio / 3.0))

    score = (
        w_vol      * vol_contrib
        + w_spread * spread_norm
        + w_turnover * turn_contrib
    )
    return round(min(1.0, max(0.0, score)), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  流动性水平分类
# ─────────────────────────────────────────────────────────────────────────────

def classify_liquidity_level(
    illiquidity_score: float,
    vol_percentile:    float,
    very_low_thr:      float = 0.75,
    low_thr:           float = 0.55,
    high_thr:          float = 0.30,
) -> LiquidityLevel:
    """
    将流动性评分映射到流动性水平。

    illiquidity_score > very_low_thr → VERY_LOW
    illiquidity_score > low_thr      → LOW
    vol_percentile    > 0.70         → HIGH（成交量大）
    else                             → NORMAL
    """
    if illiquidity_score > very_low_thr:
        return LiquidityLevel.VERY_LOW
    if illiquidity_score > low_thr:
        return LiquidityLevel.LOW
    if vol_percentile > 0.70:
        return LiquidityLevel.HIGH
    return LiquidityLevel.NORMAL
