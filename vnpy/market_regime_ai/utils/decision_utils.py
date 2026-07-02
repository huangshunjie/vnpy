"""
market_regime_ai/utils/decision_utils.py  (Phase 4)

决策工具函数 — 完整实现。

实现：
  - compute_capital_adjustment   资本调整系数
  - compute_risk_adjustment      风险调整系数
  - compute_position_limit       仓位上限建议
  - compute_rebalance_urgency    再平衡紧迫度
  - map_regime_to_strategy       状态→策略推荐映射
  - build_decision_summary       决策摘要

❌ 无 IO / 无网络 / 纯计算
"""

from __future__ import annotations
from ..constant import (
    MarketRegime, RegimeConfidence,
    StrategyRecommendation, VolatilityRegime, LiquidityLevel,
)


# ─────────────────────────────────────────────────────────────────────────────
#  策略推荐映射表
# ─────────────────────────────────────────────────────────────────────────────

_REGIME_STRATEGY: dict[MarketRegime, StrategyRecommendation] = {
    MarketRegime.BULL:     StrategyRecommendation.MOMENTUM,
    MarketRegime.BEAR:     StrategyRecommendation.DEFENSIVE,
    MarketRegime.SIDEWAYS: StrategyRecommendation.MEAN_REVERSION,
    MarketRegime.HIGH_VOL: StrategyRecommendation.RISK_REDUCTION,
    MarketRegime.LOW_LIQ:  StrategyRecommendation.REDUCE_FREQ,
    MarketRegime.UNKNOWN:  StrategyRecommendation.NEUTRAL,
}

# 各状态的基准资本调整系数（1.0 = 无调整）
_REGIME_CAPITAL_BASE: dict[MarketRegime, float] = {
    MarketRegime.BULL:     1.20,   # 牛市：增配
    MarketRegime.BEAR:     0.70,   # 熊市：减配
    MarketRegime.SIDEWAYS: 0.90,   # 震荡：小幅减配
    MarketRegime.HIGH_VOL: 0.65,   # 高波动：大幅减配
    MarketRegime.LOW_LIQ:  0.75,   # 低流动：减配
    MarketRegime.UNKNOWN:  1.00,   # 未知：中性
}

# 各状态的基准风险调整系数（1.0 = 无调整）
_REGIME_RISK_BASE: dict[MarketRegime, float] = {
    MarketRegime.BULL:     1.10,   # 牛市：可适当放宽风险
    MarketRegime.BEAR:     0.60,   # 熊市：严格收紧风险
    MarketRegime.SIDEWAYS: 0.85,   # 震荡：略收紧
    MarketRegime.HIGH_VOL: 0.50,   # 高波动：大幅收紧
    MarketRegime.LOW_LIQ:  0.70,   # 低流动：收紧
    MarketRegime.UNKNOWN:  1.00,
}


def map_regime_to_strategy(
    regime: MarketRegime,
) -> StrategyRecommendation:
    """市场状态 → 策略推荐。"""
    return _REGIME_STRATEGY.get(regime, StrategyRecommendation.NEUTRAL)


# ─────────────────────────────────────────────────────────────────────────────
#  资本调整系数
# ─────────────────────────────────────────────────────────────────────────────

def compute_capital_adjustment(
    regime:         MarketRegime,
    confidence:     float,
    vol_regime:     VolatilityRegime = VolatilityRegime.NORMAL,
    liq_level:      LiquidityLevel   = LiquidityLevel.NORMAL,
    min_factor:     float = 0.40,
    max_factor:     float = 1.50,
) -> float:
    """
    资本调整系数 [min_factor, max_factor]。

    公式：
        base     = _REGIME_CAPITAL_BASE[regime]
        vol_adj  : 高波动额外减配
        liq_adj  : 低流动性额外减配
        conf_adj : 低置信度向 1.0 收敛

        raw      = base × vol_adj × liq_adj
        adjusted = raw × confidence + 1.0 × (1 - confidence)

    Returns
    -------
    float  [min_factor, max_factor]
    """
    base = _REGIME_CAPITAL_BASE.get(regime, 1.0)

    # 波动率额外惩罚
    vol_penalty = {
        VolatilityRegime.LOW:     1.05,
        VolatilityRegime.NORMAL:  1.00,
        VolatilityRegime.HIGH:    0.85,
        VolatilityRegime.EXTREME: 0.65,
    }.get(vol_regime, 1.0)

    # 流动性额外惩罚
    liq_penalty = {
        LiquidityLevel.HIGH:     1.05,
        LiquidityLevel.NORMAL:   1.00,
        LiquidityLevel.LOW:      0.88,
        LiquidityLevel.VERY_LOW: 0.72,
    }.get(liq_level, 1.0)

    raw = base * vol_penalty * liq_penalty

    # 置信度收敛：低置信度时向中性（1.0）靠拢
    adjusted = raw * confidence + 1.0 * (1.0 - confidence)

    return round(max(min_factor, min(max_factor, adjusted)), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  风险调整系数
# ─────────────────────────────────────────────────────────────────────────────

def compute_risk_adjustment(
    regime:     MarketRegime,
    confidence: float,
    vol_regime: VolatilityRegime = VolatilityRegime.NORMAL,
    min_factor: float = 0.30,
    max_factor: float = 1.30,
) -> float:
    """
    风险调整系数 [min_factor, max_factor]。

    高 → 允许更高风险敞口
    低 → 要求收紧风险敞口

    Returns
    -------
    float  [min_factor, max_factor]
    """
    base = _REGIME_RISK_BASE.get(regime, 1.0)

    vol_penalty = {
        VolatilityRegime.LOW:     1.10,
        VolatilityRegime.NORMAL:  1.00,
        VolatilityRegime.HIGH:    0.75,
        VolatilityRegime.EXTREME: 0.50,
    }.get(vol_regime, 1.0)

    raw      = base * vol_penalty
    adjusted = raw * confidence + 1.0 * (1.0 - confidence)

    return round(max(min_factor, min(max_factor, adjusted)), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  仓位上限
# ─────────────────────────────────────────────────────────────────────────────

def compute_position_limit(
    regime:     MarketRegime,
    confidence: float,
    base_limit: float = 1.0,
) -> float:
    """
    单品种仓位上限建议（相对于基准上限的比例）。

    Returns
    -------
    float  [0.1, 1.5]
    """
    capital_adj = compute_capital_adjustment(regime, confidence)
    limit       = base_limit * capital_adj
    return round(max(0.1, min(1.5, limit)), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  再平衡紧迫度
# ─────────────────────────────────────────────────────────────────────────────

def compute_rebalance_urgency(
    regime_changed: bool,
    regime:         MarketRegime,
    confidence:     float,
    stability:      float,
) -> float:
    """
    再平衡紧迫度 [0, 1]。

    高 → 需要立即调整仓位
    低 → 可以维持现状

    Returns
    -------
    float [0, 1]
    """
    urgency = 0.0

    # 状态切换：高紧迫度
    if regime_changed:
        urgency += 0.5

    # 高风险状态：额外紧迫
    if regime in (MarketRegime.HIGH_VOL, MarketRegime.BEAR):
        urgency += 0.3

    # 低流动性：中等紧迫
    if regime == MarketRegime.LOW_LIQ:
        urgency += 0.2

    # 高置信度放大紧迫度；低置信度衰减
    urgency *= confidence

    # 低稳定性（震荡频繁切换）降低紧迫度
    urgency *= max(0.5, stability)

    return round(min(1.0, urgency), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  决策摘要
# ─────────────────────────────────────────────────────────────────────────────

def build_decision_summary(
    regime:            MarketRegime,
    recommendation:    StrategyRecommendation,
    capital_adj:       float,
    risk_adj:          float,
    position_limit:    float,
    rebalance_urgency: float,
    confidence:        float,
) -> dict:
    """构建完整决策摘要。"""
    return {
        "regime":             regime.value,
        "recommendation":     recommendation.value,
        "capital_adjustment": round(capital_adj,       4),
        "risk_adjustment":    round(risk_adj,           4),
        "position_limit":     round(position_limit,     4),
        "rebalance_urgency":  round(rebalance_urgency,  4),
        "confidence":         round(confidence,         4),
        "action": _infer_action(capital_adj, risk_adj, rebalance_urgency),
    }


def _infer_action(
    capital_adj:       float,
    risk_adj:          float,
    rebalance_urgency: float,
) -> str:
    """根据调整系数推断行动建议文本。"""
    if rebalance_urgency > 0.7:
        return "REBALANCE_NOW"
    if capital_adj < 0.70:
        return "REDUCE_EXPOSURE"
    if capital_adj > 1.15:
        return "INCREASE_EXPOSURE"
    if risk_adj < 0.65:
        return "TIGHTEN_RISK"
    return "MAINTAIN"
