"""
cross_market_ai/utils/regime_utils.py

Phase 3: Regime 对齐工具函数（纯函数，无副作用）。
"""
from __future__ import annotations

import math
from typing import Optional


# ── 分布相似度 ────────────────────────────────────────────────────────

def compute_bhattacharyya(dist_a: dict, dist_b: dict) -> float:
    """
    Bhattacharyya 系数 ∈ [0,1]。
    1 = 完全相同分布，0 = 完全不同。
    用于衡量两市场 Regime 分布重叠程度。
    """
    all_keys = set(dist_a) | set(dist_b)
    bc = sum(
        math.sqrt(dist_a.get(k, 0.0) * dist_b.get(k, 0.0))
        for k in all_keys
    )
    return round(min(bc, 1.0), 6)


def compute_kl_divergence(p: dict, q: dict) -> float:
    """
    KL 散度 D_KL(P||Q)。
    0 = 完全相同，越大越不同。
    非对称，p 为参考分布（源市场）。
    """
    eps = 1e-9
    all_keys = set(p) | set(q)
    kl = sum(
        p.get(k, eps) * math.log(p.get(k, eps) / max(q.get(k, eps), eps))
        for k in all_keys if p.get(k, 0.0) > 0
    )
    return round(max(kl, 0.0), 6)


def compute_js_divergence(p: dict, q: dict) -> float:
    """
    Jensen-Shannon 散度（对称版 KL）∈ [0,1]。
    0 = 完全相同。
    """
    all_keys = set(p) | set(q)
    eps = 1e-9
    m = {k: (p.get(k, 0.0) + q.get(k, 0.0)) / 2.0 for k in all_keys}
    js = 0.5 * compute_kl_divergence(p, m) + 0.5 * compute_kl_divergence(q, m)
    return round(min(js, 1.0), 6)


def compute_regime_entropy(dist: dict) -> float:
    """
    Regime 分布的归一化香农熵 ∈ [0,1]。
    0 = 单一状态确定，1 = 完全均匀分布。
    """
    values = [v for v in dist.values() if v > 0]
    if not values:
        return 0.0
    raw     = -sum(p * math.log2(p) for p in values)
    max_ent = math.log2(len(values)) if len(values) > 1 else 1.0
    return round(raw / max_ent, 6) if max_ent > 0 else 0.0


# ── Regime 标签对齐 ───────────────────────────────────────────────────

def align_regime_labels(
    dist_a: dict,
    dist_b: dict,
    similarity_threshold: float = 0.15,
) -> dict[str, str]:
    """
    将两个市场的 Regime 标签进行最优对齐映射。

    策略：按概率降序贪心匹配，概率差 < threshold 视为可对齐。
    Returns: {regime_a: regime_b} 映射字典
    """
    sorted_a = sorted(dist_a.items(), key=lambda x: x[1], reverse=True)
    sorted_b = sorted(dist_b.items(), key=lambda x: x[1], reverse=True)

    mapping: dict[str, str] = {}
    used_b: set[str] = set()

    for ra, pa in sorted_a:
        best_match: Optional[str] = None
        best_diff   = float("inf")
        for rb, pb in sorted_b:
            if rb in used_b:
                continue
            diff = abs(pa - pb)
            if diff < best_diff:
                best_diff  = diff
                best_match = rb
        if best_match is not None and best_diff <= similarity_threshold:
            mapping[ra] = best_match
            used_b.add(best_match)

    return mapping


def get_unmatched_regimes(
    dist_a: dict, dist_b: dict, mapping: dict[str, str]
) -> tuple[list[str], list[str]]:
    """
    返回未能对齐的 Regime 标签列表。
    Returns: (unmatched_in_a, unmatched_in_b)
    """
    unmatched_a = [r for r in dist_a if r not in mapping]
    unmatched_b = [r for r in dist_b if r not in mapping.values()]
    return unmatched_a, unmatched_b


def compute_regime_alignment_score(
    overlap:       float,
    kl_div:        float,
    persistence_gap: float,
    n_matched:     int,
    n_total:       int,
) -> float:
    """
    综合 Regime 对齐评分 ∈ [0,1]。

    高分 = 两市场 Regime 分布相似 + 持续性接近 + 大多数状态可对齐。
    此评分作为 Alpha 迁移预条件之一输入 Phase 3 迁移引擎。
    """
    coverage      = n_matched / max(n_total, 1)
    kl_penalty    = min(kl_div / 2.0, 1.0)
    persist_pen   = min(persistence_gap * 2.0, 1.0)
    score = (
        overlap   * 0.40 +
        coverage  * 0.30 +
        (1.0 - kl_penalty)  * 0.20 +
        (1.0 - persist_pen) * 0.10
    )
    return round(max(0.0, min(1.0, score)), 4)


def is_regime_alignable(alignment_score: float, threshold: float = 0.35) -> bool:
    """判断 Regime 对齐分是否达到 Alpha 迁移的基本门槛。"""
    return alignment_score >= threshold


# ── 稳定性 ────────────────────────────────────────────────────────────

def regime_is_stable(regime_history: list[str], window: int = 20) -> bool:
    """
    判断近期 Regime 是否稳定（切换频率低于 10%）。
    """
    if len(regime_history) < window:
        return False
    recent      = regime_history[-window:]
    transitions = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])
    return transitions <= window * 0.10


def compute_persistence(regime_sequence: list[str]) -> float:
    """
    计算 Regime 留存概率（不切换的比例）。
    """
    if len(regime_sequence) < 2:
        return 1.0
    stays = sum(
        1 for i in range(1, len(regime_sequence))
        if regime_sequence[i] == regime_sequence[i - 1]
    )
    return round(stays / (len(regime_sequence) - 1), 4)
