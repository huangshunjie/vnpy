"""
cross_market_ai/utils/cross_market_utils.py

Phase 2: 跨市场结构距离 / 相似度工具函数（纯函数，无副作用）。
"""
from __future__ import annotations

import math
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..model.structure_model import MarketStructureVector


def normalize_market_id(market_id: str) -> str:
    """统一市场 ID 格式。"""
    return market_id.strip().lower()


def market_ids_are_valid(markets: list[str]) -> bool:
    """校验市场列表非空且无重复。"""
    if not markets:
        return False
    return len(markets) == len(set(markets))


def format_score(score: Optional[float], decimals: int = 4) -> str:
    """格式化评分输出。"""
    if score is None:
        return "N/A"
    return f"{score:.{decimals}f}"


# ── 结构距离计算 ──────────────────────────────────────────────────────

def compute_structural_distance(
    vec_a: "MarketStructureVector",
    vec_b: "MarketStructureVector",
    weights: dict[str, float] | None = None,
) -> float:
    """
    计算两个市场结构向量之间的加权欧氏距离。

    维度权重默认：
      volatility   0.30  — 波动率结构差异对 Alpha 影响最大
      liquidity    0.25  — 流动性差异影响执行成本
      participant  0.20  — 参与者结构影响信号持续性
      noise        0.15  — 噪音差异影响信噪比
      regime       0.10  — Regime 分布差异影响时序统计性质

    Returns:
        float ∈ [0, ∞)，值越小表示两市场结构越相似
    """
    w = weights or {
        "volatility":  0.30,
        "liquidity":   0.25,
        "participant": 0.20,
        "noise":       0.15,
        "regime":      0.10,
    }

    vol_dist   = _vol_distance(vec_a, vec_b)
    liq_dist   = _liq_distance(vec_a, vec_b)
    part_dist  = _part_distance(vec_a, vec_b)
    noise_dist = _noise_distance(vec_a, vec_b)
    reg_dist   = _regime_distance(vec_a, vec_b)

    weighted_sq = (
        w.get("volatility",  0.30) * vol_dist  ** 2 +
        w.get("liquidity",   0.25) * liq_dist  ** 2 +
        w.get("participant", 0.20) * part_dist ** 2 +
        w.get("noise",       0.15) * noise_dist** 2 +
        w.get("regime",      0.10) * reg_dist  ** 2
    )
    return round(math.sqrt(weighted_sq), 6)


def compute_structural_similarity(
    vec_a: "MarketStructureVector",
    vec_b: "MarketStructureVector",
    weights: dict[str, float] | None = None,
) -> float:
    """
    结构相似度 ∈ [0, 1]，由距离转换而来。
    similarity = 1 / (1 + distance)
    """
    dist = compute_structural_distance(vec_a, vec_b, weights)
    return round(1.0 / (1.0 + dist), 4)


def rank_markets_by_similarity(
    source: "MarketStructureVector",
    candidates: list["MarketStructureVector"],
    weights: dict[str, float] | None = None,
) -> list[tuple[str, float]]:
    """
    将候选市场按与 source 的结构相似度从高到低排序。

    Returns:
        list of (market_id, similarity_score) sorted descending
    """
    scored = [
        (c.market_id, compute_structural_similarity(source, c, weights))
        for c in candidates
    ]
    return sorted(scored, key=lambda x: x[1], reverse=True)


def compute_portability_gap(
    vec_a: "MarketStructureVector",
    vec_b: "MarketStructureVector",
) -> float:
    """
    计算两市场的 Alpha 可迁移性差距。
    差距越小，Alpha 从 A 迁移到 B 的预期性能损耗越低。

    Returns:
        float ∈ [0, 1]，0 = 完全可迁移，1 = 完全不可迁移
    """
    port_gap  = abs(vec_a.portability_score - vec_b.portability_score)
    struct_d  = compute_structural_distance(vec_a, vec_b)
    # 归一化结构距离（经验上 distance > 1.5 视为完全不同）
    norm_dist = min(struct_d / 1.5, 1.0)
    gap = port_gap * 0.4 + norm_dist * 0.6
    return round(min(gap, 1.0), 4)


def compute_transfer_feasibility(
    vec_src: "MarketStructureVector",
    vec_dst: "MarketStructureVector",
) -> dict:
    """
    综合评估 Alpha 从 src 迁移到 dst 的可行性。

    Returns:
        dict with keys:
          feasibility_score ∈ [0, 1]  — 迁移可行性
          similarity        ∈ [0, 1]  — 结构相似度
          portability_gap   ∈ [0, 1]  — 可迁移性差距
          recommendation    str       — 建议
    """
    similarity      = compute_structural_similarity(vec_src, vec_dst)
    portability_gap = compute_portability_gap(vec_src, vec_dst)
    feasibility     = round(similarity * 0.6 + (1.0 - portability_gap) * 0.4, 4)

    if feasibility >= 0.75:
        recommendation = "HIGH_CONFIDENCE: 结构高度相似，Alpha 迁移可行性强"
    elif feasibility >= 0.50:
        recommendation = "MODERATE: 结构中等相似，建议适度调整后迁移"
    elif feasibility >= 0.30:
        recommendation = "LOW: 结构差异显著，迁移需大幅参数调整"
    else:
        recommendation = "REJECT: 结构差异过大，Alpha 迁移风险极高"

    return {
        "market_src":       vec_src.market_id,
        "market_dst":       vec_dst.market_id,
        "feasibility_score":feasibility,
        "similarity":       similarity,
        "portability_gap":  portability_gap,
        "recommendation":   recommendation,
    }


# ── 各维度距离计算（归一化到 [0, 1]）────────────────────────────────

def _vol_distance(a: "MarketStructureVector", b: "MarketStructureVector") -> float:
    """波动率结构距离（归一化）。"""
    av, bv = a.volatility, b.volatility
    # 年化波动率差（归一化到最大差 1.0）
    d_vol  = abs(av.annual_vol - bv.annual_vol) / 1.0
    d_skew = abs(av.skew - bv.skew) / 2.0
    d_kurt = abs(av.excess_kurtosis - bv.excess_kurtosis) / 10.0
    d_jump = abs(av.jump_intensity - bv.jump_intensity) / 0.1
    return min(d_vol * 0.5 + d_skew * 0.2 + d_kurt * 0.15 + d_jump * 0.15, 1.0)


def _liq_distance(a: "MarketStructureVector", b: "MarketStructureVector") -> float:
    """流动性结构距离（归一化）。"""
    al, bl = a.liquidity, b.liquidity
    d_spread = abs(al.bid_ask_spread_bps - bl.bid_ask_spread_bps) / 20.0
    d_depth  = abs(al.depth_score - bl.depth_score)
    d_impact = abs(al.market_impact_coeff - bl.market_impact_coeff)
    return min(d_spread * 0.5 + d_depth * 0.3 + d_impact * 0.2, 1.0)


def _part_distance(a: "MarketStructureVector", b: "MarketStructureVector") -> float:
    """参与者结构距离（归一化）。"""
    ap, bp = a.participant, b.participant
    d_retail = abs(ap.retail_ratio - bp.retail_ratio)
    d_hft    = abs(ap.hft_ratio - bp.hft_ratio)
    d_asym   = abs(ap.info_asymmetry - bp.info_asymmetry)
    return min(d_retail * 0.5 + d_hft * 0.3 + d_asym * 0.2, 1.0)


def _noise_distance(a: "MarketStructureVector", b: "MarketStructureVector") -> float:
    """微观结构噪音距离（归一化）。"""
    an, bn = a.noise, b.noise
    d_noise = abs(an.noise_ratio - bn.noise_ratio)
    d_autocorr = abs(an.autocorr_lag1 - bn.autocorr_lag1) / 0.3
    d_adv  = abs(an.adverse_selection - bn.adverse_selection)
    d_lim  = abs(an.limit_distortion - bn.limit_distortion)
    return min(d_noise * 0.35 + d_autocorr * 0.25 + d_adv * 0.2 + d_lim * 0.2, 1.0)


def _regime_distance(a: "MarketStructureVector", b: "MarketStructureVector") -> float:
    """Regime 分布距离（归一化），基于熵差和分布重叠。"""
    ar, br   = a.regime, b.regime
    d_entropy = abs(ar.entropy - br.entropy)
    # 两分布公共 key 的占比差之和（近似 L1 距离）
    all_keys = set(ar.distribution) | set(br.distribution)
    if all_keys:
        l1 = sum(
            abs(ar.distribution.get(k, 0.0) - br.distribution.get(k, 0.0))
            for k in all_keys
        ) / 2.0
    else:
        l1 = 0.0
    return min(d_entropy * 0.4 + l1 * 0.6, 1.0)
