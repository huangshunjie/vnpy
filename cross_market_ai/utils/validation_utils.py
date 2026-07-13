"""
cross_market_ai/utils/validation_utils.py

Phase 4: 普适性评分工具函数（纯函数，无副作用）。

四个评分维度：
  1. cross_market_stability   — 跨市场稳定性
  2. regime_robustness        — Regime 鲁棒性
  3. structural_invariance    — 结构不变性
  4. execution_independence   — 执行独立性
"""
from __future__ import annotations

import math
from typing import Optional


# ── 维度 1：跨市场稳定性 ──────────────────────────────────────────────

def compute_cross_market_stability(
    transfer_coeffs: list[float],
    n_transferable:  int,
    n_total:         int,
) -> float:
    """
    跨市场稳定性 ∈ [0, 1]。

    指标：
      - 迁移系数均值（平均质量）
      - 迁移系数标准差倒数（一致性）
      - 可迁移市场覆盖率

    高稳定性 = 在多个市场上均有较高且一致的迁移系数。
    """
    if not transfer_coeffs or n_total == 0:
        return 0.0

    avg     = sum(transfer_coeffs) / len(transfer_coeffs)
    std     = _std(transfer_coeffs)
    cv      = std / max(avg, 1e-9)           # 变异系数（越低越稳定）
    coverage = n_transferable / max(n_total, 1)

    consistency  = max(0.0, 1.0 - cv)
    stability    = avg * 0.45 + consistency * 0.35 + coverage * 0.20
    return round(max(0.0, min(1.0, stability)), 4)


# ── 维度 2：Regime 鲁棒性 ─────────────────────────────────────────────

def compute_regime_robustness(
    alignment_scores:  list[float],
    regime_invariances: list[float],
) -> float:
    """
    Regime 鲁棒性 ∈ [0, 1]。

    指标：
      - 跨市场 Regime 对齐评分均值（越高越容易在目标市场找到相应状态）
      - Alpha 在不同 Regime 下的不变性（越高越不依赖特定市场状态）

    高鲁棒性 = Alpha 在各种 Regime 下均可有效，且市场间 Regime 易对齐。
    """
    if not alignment_scores and not regime_invariances:
        return 0.0

    avg_align = (sum(alignment_scores) / len(alignment_scores)
                 if alignment_scores else 0.5)
    avg_inv   = (sum(regime_invariances) / len(regime_invariances)
                 if regime_invariances else 0.5)

    robustness = avg_align * 0.40 + avg_inv * 0.60
    return round(max(0.0, min(1.0, robustness)), 4)


# ── 维度 3：结构不变性 ────────────────────────────────────────────────

def compute_structural_invariance(
    portability_scores: list[float],
    structural_distances: list[float],
    ic_decays: list[float],
) -> float:
    """
    结构不变性 ∈ [0, 1]。

    指标：
      - 目标市场的可迁移性先验评分均值
      - 结构距离与 IC 衰减率的相关性（距离越大但衰减越小，则不变性越高）
      - IC 衰减率均值（越低越好）

    高结构不变性 = Alpha 的有效性不依赖特定市场的微观结构。
    """
    if not portability_scores:
        return 0.0

    avg_port   = sum(portability_scores) / len(portability_scores)
    avg_decay  = sum(ic_decays) / len(ic_decays) if ic_decays else 0.5
    decay_pen  = max(0.0, 1.0 - avg_decay)

    # 结构距离与衰减的相关性：相关性弱 → 不变性高
    if structural_distances and ic_decays and len(structural_distances) == len(ic_decays):
        corr = _pearson_corr(structural_distances, ic_decays)
        dist_inv = max(0.0, 1.0 - max(corr, 0.0))
    else:
        dist_inv = 0.5

    invariance = avg_port * 0.40 + decay_pen * 0.35 + dist_inv * 0.25
    return round(max(0.0, min(1.0, invariance)), 4)


# ── 维度 4：执行独立性 ────────────────────────────────────────────────

def compute_execution_independence(
    vol_scales:    list[float],
    liq_scales:    list[float],
    vol_sensitivity:   float,
    liquidity_sensitivity: float,
) -> float:
    """
    执行独立性 ∈ [0, 1]。

    指标：
      - vol_scale 方差（越小 = Alpha 对波动率结构依赖越低）
      - liq_scale 方差（越小 = Alpha 对流动性结构依赖越低）
      - Alpha 元数据中的敏感度先验（越低越好）

    高执行独立性 = Alpha 信号的有效性与执行成本结构解耦。
    """
    vol_cv  = _cv(vol_scales)  if vol_scales  else 0.5
    liq_cv  = _cv(liq_scales)  if liq_scales  else 0.5

    vol_indep = max(0.0, 1.0 - vol_cv * 0.5)
    liq_indep = max(0.0, 1.0 - liq_cv * 0.5)
    sens_indep = max(0.0, 1.0 - (vol_sensitivity + liquidity_sensitivity) / 2.0)

    independence = vol_indep * 0.30 + liq_indep * 0.30 + sens_indep * 0.40
    return round(max(0.0, min(1.0, independence)), 4)


# ── 综合评分 ──────────────────────────────────────────────────────────

def compute_universality_score(
    cross_market_stability: float,
    regime_robustness:      float,
    structural_invariance:  float,
    execution_independence: float,
    weights: dict[str, float] | None = None,
) -> float:
    """
    综合普适性评分 ∈ [0, 1]。

    默认权重（基于学术研究重要性排序）：
      cross_market_stability  0.35  — 最直接反映跨市场泛化能力
      regime_robustness       0.25  — Regime 切换是最常见的失效原因
      structural_invariance   0.25  — 结构不变性是长期可迁移的基础
      execution_independence  0.15  — 执行层面相对可通过参数调整补偿
    """
    w = weights or {
        "cross_market_stability": 0.35,
        "regime_robustness":      0.25,
        "structural_invariance":  0.25,
        "execution_independence": 0.15,
    }
    score = (
        w.get("cross_market_stability", 0.35) * cross_market_stability +
        w.get("regime_robustness",      0.25) * regime_robustness      +
        w.get("structural_invariance",  0.25) * structural_invariance  +
        w.get("execution_independence", 0.15) * execution_independence
    )
    return round(max(0.0, min(1.0, score)), 4)


def classify_universality_grade(score: float) -> tuple[str, str]:
    """
    将综合评分映射到等级和结论。

    Returns: (grade, verdict)
    """
    if score >= 0.75:
        return (
            "UNIVERSAL",
            "宇宙级可迁移结构：该 Alpha 在所有测试市场均显示稳健性，"
            "可以信心较高地跨市场部署。",
        )
    if score >= 0.55:
        return (
            "PORTABLE",
            "可迁移结构：该 Alpha 在结构相似的市场间可有效迁移，"
            "建议优先部署于高相似度市场，并监控衰减。",
        )
    if score >= 0.35:
        return (
            "LOCAL",
            "局部有效结构：该 Alpha 对原市场结构依赖较强，"
            "跨市场迁移需大幅参数调整，建议仅在同类市场尝试。",
        )
    return (
        "FRAGILE",
        "脆弱结构：该 Alpha 强烈依赖原市场的特定微观结构，"
        "跨市场迁移风险极高，不建议直接迁移。",
    )


# ── Phase 5 预留（跨市场验证指标）────────────────────────────────────

def compute_performance_decay(
    sharpe_train: float,
    sharpe_test:  float,
) -> Optional[float]:
    """性能衰减率 = (sharpe_train - sharpe_test) / |sharpe_train|。"""
    if sharpe_train == 0:
        return None
    return round(max(0.0, min(1.0,
        (sharpe_train - sharpe_test) / abs(sharpe_train)
    )), 4)


def compute_sharpe_stability(sharpe_series: list[float]) -> Optional[float]:
    """Sharpe 稳定性：系列标准差倒数，归一化到 [0,1]。"""
    if len(sharpe_series) < 2:
        return None
    std = _std(sharpe_series)
    avg = abs(sum(sharpe_series) / len(sharpe_series))
    cv  = std / max(avg, 1e-9)
    return round(max(0.0, 1.0 - min(cv, 1.0)), 4)


def compute_drawdown_consistency(
    drawdowns_train: list[float],
    drawdowns_test:  list[float],
) -> Optional[float]:
    """回撤一致性：测试集回撤与训练集回撤的比例接近 1 则一致性高。"""
    if not drawdowns_train or not drawdowns_test:
        return None
    avg_train = sum(drawdowns_train) / len(drawdowns_train)
    avg_test  = sum(drawdowns_test)  / len(drawdowns_test)
    if avg_train == 0:
        return None
    ratio = avg_test / avg_train
    consistency = max(0.0, 1.0 - abs(ratio - 1.0))
    return round(min(consistency, 1.0), 4)


def validation_passed(
    performance_decay: Optional[float],
    decay_threshold:   float = 0.50,
) -> bool:
    """判断跨市场验证是否通过。"""
    if performance_decay is None:
        return False
    return performance_decay < decay_threshold


# ── 纯函数数学工具 ────────────────────────────────────────────────────

def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = sum(values) / len(values)
    return math.sqrt(sum((x - avg) ** 2 for x in values) / len(values))


def _cv(values: list[float]) -> float:
    """变异系数 = std / |mean|。"""
    if not values:
        return 0.0
    avg = sum(values) / len(values)
    std = _std(values)
    return std / max(abs(avg), 1e-9)


def _pearson_corr(xs: list[float], ys: list[float]) -> float:
    """Pearson 相关系数。"""
    n = len(xs)
    if n < 2 or len(ys) != n:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num    = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x  = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y  = math.sqrt(sum((y - my) ** 2 for y in ys))
    denom  = den_x * den_y
    return round(num / denom, 4) if denom > 0 else 0.0
