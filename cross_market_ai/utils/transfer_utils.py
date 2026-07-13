"""
cross_market_ai/utils/transfer_utils.py

Phase 3: Alpha 迁移工具函数（纯函数，无副作用）。
核心公式：Alpha_B = T(Alpha_A, Market_A → Market_B)
"""
from __future__ import annotations

import math
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..model.structure_model import MarketStructureVector


# ── 迁移系数计算 ──────────────────────────────────────────────────────

def compute_transfer_coefficient(
    correlation_stability:  float,
    regime_invariance:      float,
    volatility_sensitivity: float,
    liquidity_sensitivity:  float,
    weights: dict[str, float] | None = None,
) -> float:
    """
    计算 Alpha 迁移系数 T ∈ [0,1]。

    T 越高表示 Alpha_A 越能在 Market_B 上保持有效性。

    权重默认：
      regime_invariance      0.35  — Regime 不变性最重要
      correlation_stability  0.30  — 相关性稳定性
      volatility_sensitivity 0.20  — 波动率敏感度（低敏感=高分）
      liquidity_sensitivity  0.15  — 流动性敏感度（低敏感=高分）
    """
    w = weights or {
        "regime_invariance":      0.35,
        "correlation_stability":  0.30,
        "volatility_sensitivity": 0.20,
        "liquidity_sensitivity":  0.15,
    }
    # 敏感度取反：低敏感度 → 高迁移性
    vol_score = max(0.0, 1.0 - volatility_sensitivity)
    liq_score = max(0.0, 1.0 - liquidity_sensitivity)

    t = (
        w.get("regime_invariance",      0.35) * regime_invariance      +
        w.get("correlation_stability",  0.30) * correlation_stability  +
        w.get("volatility_sensitivity", 0.20) * vol_score              +
        w.get("liquidity_sensitivity",  0.15) * liq_score
    )
    return round(max(0.0, min(1.0, t)), 4)


def is_transferable(
    transfer_coefficient: float,
    threshold: float = 0.40,
) -> bool:
    """判断 Alpha 是否满足迁移条件。"""
    return transfer_coefficient >= threshold


def classify_transfer_confidence(transfer_coefficient: float) -> str:
    """将迁移系数转换为置信度标签。"""
    if transfer_coefficient >= 0.70:
        return "HIGH"
    if transfer_coefficient >= 0.50:
        return "MODERATE"
    if transfer_coefficient >= 0.35:
        return "LOW"
    return "REJECT"


# ── 波动率适配 ────────────────────────────────────────────────────────

def compute_vol_scale(
    vol_src: float,
    vol_dst: float,
    sensitivity: float = 0.7,
) -> float:
    """
    计算波动率缩放系数。

    Alpha_B 的仓位规模 = Alpha_A 仓位 × vol_scale。
    sensitivity: Alpha 对波动率的敏感度（0=不敏感，1=完全按比例缩放）。
    """
    if vol_src <= 0:
        return 1.0
    raw_ratio = vol_dst / vol_src
    # 按敏感度插值：sensitivity=0 → scale=1.0（不调整），sensitivity=1 → scale=raw_ratio
    scale = 1.0 + (raw_ratio - 1.0) * sensitivity
    return round(max(0.1, min(scale, 10.0)), 4)


def compute_liq_scale(
    spread_src_bps: float,
    spread_dst_bps: float,
    sensitivity: float = 0.5,
) -> float:
    """
    计算流动性缩放系数（影响成交量上限）。

    spread 越大表示流动性越差。
    scale < 1 表示需要降低仓位以适应更差的流动性。
    """
    if spread_src_bps <= 0:
        return 1.0
    ratio = spread_src_bps / max(spread_dst_bps, 0.01)
    scale = 1.0 + (ratio - 1.0) * sensitivity
    return round(max(0.1, min(scale, 5.0)), 4)


def compute_signal_decay_adjustment(
    decay_days_src: int,
    vol_scale:      float,
    regime_stability_dst: float,
) -> int:
    """
    调整信号衰减周期。

    目标市场波动率更高 → 信号衰减更快（decay_days 缩短）。
    目标市场 Regime 更不稳定 → 信号衰减更快。
    """
    vol_adj     = 1.0 / max(vol_scale, 0.1)
    regime_adj  = 0.5 + regime_stability_dst * 0.5
    adjusted    = int(decay_days_src * vol_adj * regime_adj)
    return max(1, min(adjusted, decay_days_src * 3))


# ── IC / Sharpe 预测 ──────────────────────────────────────────────────

def predict_transferred_ic(
    ic_src:              float,
    transfer_coefficient: float,
    vol_scale:           float,
    regime_invariance:   float,
) -> float:
    """
    预测 Alpha 迁移后在目标市场的 IC 期望值。

    IC_dst ≈ IC_src × T × regime_factor × vol_penalty
    """
    vol_penalty    = 1.0 / max(math.sqrt(vol_scale), 0.5)
    regime_factor  = 0.5 + regime_invariance * 0.5
    ic_dst         = ic_src * transfer_coefficient * regime_factor * vol_penalty
    return round(max(0.0, ic_dst), 5)


def predict_transferred_sharpe(
    sharpe_src:          float,
    transfer_coefficient: float,
    liq_scale:           float,
) -> float:
    """
    预测 Alpha 迁移后在目标市场的 Sharpe 期望值。

    Sharpe_dst ≈ Sharpe_src × T × liq_factor
    """
    liq_factor = 1.0 / max(math.sqrt(max(liq_scale, 0.1)), 0.5)
    sharpe_dst = sharpe_src * transfer_coefficient * liq_factor
    return round(max(0.0, sharpe_dst), 4)


def compute_ic_decay_rate(ic_src: float, ic_dst: float) -> float:
    """
    IC 衰减率 = (IC_src - IC_dst) / |IC_src|。
    0 = 无衰减，1 = 完全失效。
    """
    if ic_src == 0:
        return 1.0
    return round(max(0.0, min(1.0, (ic_src - ic_dst) / abs(ic_src))), 4)


# ── 结构差异 → 迁移条件 ───────────────────────────────────────────────

def derive_transfer_conditions_from_structure(
    vec_src: "MarketStructureVector",
    vec_dst: "MarketStructureVector",
    alpha_vol_sensitivity:  float = 0.5,
    alpha_liq_sensitivity:  float = 0.5,
    alpha_regime_invariance: float = 0.5,
) -> dict:
    """
    从市场结构向量差异推导四个迁移条件评分。

    Args:
        vec_src / vec_dst:       Phase 2 计算的结构向量
        alpha_vol_sensitivity:   Alpha 元数据中的波动率敏感度
        alpha_liq_sensitivity:   Alpha 元数据中的流动性敏感度
        alpha_regime_invariance: Alpha 元数据中的 Regime 不变性

    Returns:
        dict with correlation_stability / regime_invariance /
                   volatility_sensitivity / liquidity_sensitivity
    """
    # 相关性稳定性：两市场相关性越高且稳定，信号迁移越可靠
    cross_corr = vec_src.cross_correlations.get(vec_dst.market_id, 0.0)
    corr_stab  = max(0.0, abs(cross_corr) * 0.7 + (1.0 - abs(cross_corr)) * 0.3)

    # 波动率敏感度：目标市场与源市场波动率比例越大，Alpha 越需要调整
    vol_ratio      = vec_dst.volatility.annual_vol / max(vec_src.volatility.annual_vol, 1e-6)
    vol_sensitivity = min(abs(vol_ratio - 1.0) * alpha_vol_sensitivity, 1.0)

    # 流动性敏感度：目标市场价差比源市场大越多，Alpha 越难迁移
    spread_ratio   = vec_dst.liquidity.bid_ask_spread_bps / max(vec_src.liquidity.bid_ask_spread_bps, 0.01)
    liq_sensitivity = min(abs(spread_ratio - 1.0) * alpha_liq_sensitivity * 0.5, 1.0)

    # Regime 不变性：综合 Alpha 内生不变性 + 两市场 Regime 结构差异
    entropy_diff   = abs(vec_src.regime.entropy - vec_dst.regime.entropy)
    regime_inv     = max(0.0, alpha_regime_invariance - entropy_diff * 0.3)

    return {
        "correlation_stability":  round(corr_stab, 4),
        "regime_invariance":      round(regime_inv, 4),
        "volatility_sensitivity": round(vol_sensitivity, 4),
        "liquidity_sensitivity":  round(liq_sensitivity, 4),
    }
