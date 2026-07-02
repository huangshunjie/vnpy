"""
market_regime_ai/utils/regime_utils.py  (Phase 2)

市场状态工具函数 — 完整实现。

实现：
  - compute_regime_scores     多因子评分（Vol / Trend / Liq / Corr）
  - classify_regime           状态分类（带置信度）
  - score_to_confidence       置信度映射
  - detect_regime_change      状态切换检测
  - compute_factor_weights    动态权重计算
  - normalize_score           单因子归一化
  - build_regime_summary      摘要构建

❌ 无 IO，无网络，无线程，纯计算
"""

from __future__ import annotations

import math
from ..constant import MarketRegime, RegimeConfidence


# ─────────────────────────────────────────────────────────────────────────────
#  归一化
# ─────────────────────────────────────────────────────────────────────────────

def normalize_score(value: float, lo: float, hi: float) -> float:
    """
    将 value 线性归一化到 [0, 1]。

    Parameters
    ----------
    value : 原始值
    lo    : 历史最低参考值
    hi    : 历史最高参考值

    Returns
    -------
    float  [0, 1]
    """
    if hi <= lo:
        return 0.5
    clipped = max(lo, min(hi, value))
    return round((clipped - lo) / (hi - lo), 6)


def clip_score(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """截断到 [lo, hi]。"""
    return max(lo, min(hi, value))


# ─────────────────────────────────────────────────────────────────────────────
#  置信度
# ─────────────────────────────────────────────────────────────────────────────

def score_to_confidence(score: float) -> RegimeConfidence:
    """
    将置信度评分映射到枚举。

    score ≥ 0.75 → HIGH
    score ≥ 0.50 → MEDIUM
    else         → LOW
    """
    if score >= 0.75:
        return RegimeConfidence.HIGH
    if score >= 0.50:
        return RegimeConfidence.MEDIUM
    return RegimeConfidence.LOW


# ─────────────────────────────────────────────────────────────────────────────
#  多因子评分
# ─────────────────────────────────────────────────────────────────────────────

def compute_regime_scores(
    vol_score:   float,    # 波动率评分 [0,1]，高 = 高波动
    trend_score: float,    # 趋势强度评分 [0,1]，高 = 强趋势
    trend_sign:  float,    # 趋势方向符号 +1=上 / -1=下 / 0=横
    liq_score:   float,    # 流动性评分 [0,1]，高 = 流动性好
    corr_score:  float,    # 相关性评分 [0,1]，高 = 高相关（系统性风险）
) -> dict[str, float]:
    """
    计算各市场状态的得分。

    状态评分公式：

    Bull：
        trend_score × 0.50
        + (1 - vol_score) × 0.20    # 波动率低加分
        + liq_score × 0.20           # 流动性好加分
        + (trend_sign == 1) × 0.10   # 上涨方向

    Bear：
        trend_score × 0.50
        + vol_score × 0.20           # 波动率高加分（熊市常伴随高波动）
        + (1 - liq_score) × 0.10
        + (trend_sign == -1) × 0.20  # 下跌方向

    Sideways：
        (1 - trend_score) × 0.60     # 趋势弱
        + (1 - vol_score) × 0.20
        + (1 - corr_score) × 0.20

    High Vol：
        vol_score × 0.60
        + corr_score × 0.25          # 高相关常伴随高波动
        + (1 - liq_score) × 0.15

    Low Liq：
        (1 - liq_score) × 0.70
        + vol_score × 0.20
        + corr_score × 0.10

    Returns
    -------
    dict  {MarketRegime.value: score}  score ∈ [0, 1]
    """
    up   = 1.0 if trend_sign > 0 else 0.0
    down = 1.0 if trend_sign < 0 else 0.0

    bull = (
        trend_score * 0.50
        + (1 - vol_score) * 0.20
        + liq_score * 0.20
        + up * 0.10
    )
    bear = (
        trend_score * 0.50
        + vol_score * 0.20
        + (1 - liq_score) * 0.10
        + down * 0.20
    )
    sideways = (
        (1 - trend_score) * 0.60
        + (1 - vol_score) * 0.20
        + (1 - corr_score) * 0.20
    )
    high_vol = (
        vol_score * 0.60
        + corr_score * 0.25
        + (1 - liq_score) * 0.15
    )
    low_liq = (
        (1 - liq_score) * 0.70
        + vol_score * 0.20
        + corr_score * 0.10
    )

    return {
        MarketRegime.BULL.value:     round(clip_score(bull),     6),
        MarketRegime.BEAR.value:     round(clip_score(bear),     6),
        MarketRegime.SIDEWAYS.value: round(clip_score(sideways), 6),
        MarketRegime.HIGH_VOL.value: round(clip_score(high_vol), 6),
        MarketRegime.LOW_LIQ.value:  round(clip_score(low_liq),  6),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  状态分类
# ─────────────────────────────────────────────────────────────────────────────

def classify_regime(
    scores:          dict[str, float],
    min_score:       float = 0.40,
    high_vol_override: bool = True,
    low_liq_override:  bool = True,
    high_vol_threshold: float = 0.65,
    low_liq_threshold:  float = 0.65,
) -> tuple[MarketRegime, float]:
    """
    从多因子评分字典中选出最终市场状态。

    规则：
      1. High Vol 和 Low Liq 优先（override）：
         若对应评分 ≥ threshold，直接判定为该状态
      2. 否则取最高分状态
      3. 若最高分 < min_score，返回 UNKNOWN

    Parameters
    ----------
    scores              : compute_regime_scores() 返回的评分字典
    min_score           : 最低有效评分阈值
    high_vol_override   : High Vol 优先覆盖（默认 True）
    low_liq_override    : Low Liq 优先覆盖（默认 True）
    high_vol_threshold  : High Vol 覆盖触发阈值
    low_liq_threshold   : Low Liq 覆盖触发阈值

    Returns
    -------
    (MarketRegime, confidence_score)
    """
    if not scores:
        return MarketRegime.UNKNOWN, 0.0

    # Override 检查（High Vol > Low Liq > 普通最高分）
    if low_liq_override:
        liq_sc = scores.get(MarketRegime.LOW_LIQ.value, 0.0)
        if liq_sc >= low_liq_threshold:
            return MarketRegime.LOW_LIQ, liq_sc

    if high_vol_override:
        vol_sc = scores.get(MarketRegime.HIGH_VOL.value, 0.0)
        if vol_sc >= high_vol_threshold:
            return MarketRegime.HIGH_VOL, vol_sc

    # 普通最高分
    best_key = max(scores, key=scores.__getitem__)
    best_sc  = scores[best_key]

    if best_sc < min_score:
        return MarketRegime.UNKNOWN, best_sc

    try:
        regime = MarketRegime(best_key)
    except ValueError:
        regime = MarketRegime.UNKNOWN

    return regime, best_sc


# ─────────────────────────────────────────────────────────────────────────────
#  动态权重
# ─────────────────────────────────────────────────────────────────────────────

def compute_factor_weights(
    data_quality: dict[str, float],
) -> dict[str, float]:
    """
    根据各因子数据质量动态调整权重。

    Parameters
    ----------
    data_quality : {factor_name: quality_score [0,1]}
      factor_name ∈ {"vol", "trend", "liq", "corr"}

    Returns
    -------
    dict  {factor_name: weight}  权重归一化，和为 1
    """
    base = {"vol": 0.30, "trend": 0.35, "liq": 0.20, "corr": 0.15}
    adjusted = {
        k: base[k] * data_quality.get(k, 1.0)
        for k in base
    }
    total = sum(adjusted.values())
    if total < 1e-9:
        return {k: 1 / len(base) for k in base}
    return {k: round(v / total, 6) for k, v in adjusted.items()}


# ─────────────────────────────────────────────────────────────────────────────
#  状态切换检测
# ─────────────────────────────────────────────────────────────────────────────

def detect_regime_change(
    prev:    MarketRegime,
    current: MarketRegime,
) -> bool:
    """检测市场状态是否发生切换。"""
    return prev != current and current != MarketRegime.UNKNOWN


def compute_regime_stability(
    history: list[MarketRegime],
    window:  int = 5,
) -> float:
    """
    计算状态稳定性（最近 window 个状态的一致性）。

    Returns
    -------
    float  [0, 1]，1.0 = 完全稳定（所有状态相同）
    """
    if not history:
        return 0.0
    recent = history[-window:]
    if not recent:
        return 0.0
    most_common = max(set(recent), key=recent.count)
    return round(recent.count(most_common) / len(recent), 4)


# ─────────────────────────────────────────────────────────────────────────────
#  摘要
# ─────────────────────────────────────────────────────────────────────────────

def build_regime_summary(
    regime:     MarketRegime,
    confidence: float,
    scores:     dict[str, float],
    stability:  float,
    duration:   int,
) -> dict:
    """构建状态评估摘要。"""
    return {
        "regime":     regime.value,
        "confidence": round(confidence, 4),
        "confidence_level": score_to_confidence(confidence).value,
        "scores":     {k: round(v, 4) for k, v in scores.items()},
        "top2": sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2],
        "stability":  round(stability, 4),
        "duration_bars": duration,
    }
