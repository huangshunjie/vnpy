"""
global_portfolio_intelligence/utils/objective_utils.py  (Phase 2)

统一目标函数工具函数。

目标函数形式：
  Maximize:
    w_ret  * Return
    - w_risk * Risk
    - w_cost * Cost
    - w_turn * Turnover
    + w_alpha* Alpha Quality
    + w_exec * Execution Efficiency

多目标评分（0-100）：
  Sharpe / Drawdown / Capacity / Stability
"""
from __future__ import annotations
import math


# ──────────────────────────────────────────────────────────────────────
#  统一目标函数
# ──────────────────────────────────────────────────────────────────────

DEFAULT_WEIGHTS = {
    "return":     0.30,
    "risk":       0.25,
    "cost":       0.15,
    "turnover":   0.10,
    "alpha":      0.10,
    "execution":  0.10,
}


def compute_unified_objective(
    expected_return:      float,
    risk:                 float,
    cost:                 float,
    turnover:             float,
    alpha_quality:        float,
    execution_efficiency: float,
    weights:              dict[str, float] | None = None,
) -> dict[str, float]:
    """
    计算统一目标函数值。

    所有输入均为归一化到 [0,1] 的无量纲分数：
      expected_return      — 预期收益分（越高越好）
      risk                 — 风险分（越高越差，加负号）
      cost                 — 成本分（越高越差，加负号）
      turnover             — 换手率分（越高越差，加负号）
      alpha_quality        — Alpha 质量分（越高越好）
      execution_efficiency — 执行效率分（越高越好）

    Returns dict with:
      objective   : 综合目标函数值 [-1, 1]
      components  : 各分量贡献
      score       : 归一化到 [0, 100] 的系统得分
    """
    w = weights or DEFAULT_WEIGHTS

    comp = {
        "return":    w.get("return",    0.30) *  expected_return,
        "risk":      w.get("risk",      0.25) * -risk,
        "cost":      w.get("cost",      0.15) * -cost,
        "turnover":  w.get("turnover",  0.10) * -turnover,
        "alpha":     w.get("alpha",     0.10) *  alpha_quality,
        "execution": w.get("execution", 0.10) *  execution_efficiency,
    }
    obj = sum(comp.values())

    # 归一化到 [0, 100]
    # 理论最大值 = 所有正贡献全满 = w_ret + w_alpha + w_exec
    # 理论最小值 = 所有负贡献全满 = -(w_risk + w_cost + w_turn)
    w_pos = w.get("return", 0.30) + w.get("alpha", 0.10) + w.get("execution", 0.10)
    w_neg = w.get("risk",   0.25) + w.get("cost",  0.15) + w.get("turnover",  0.10)
    denom = max(w_pos + w_neg, 1e-9)
    score = round((obj + w_neg) / denom * 100, 2)

    return {
        "objective":  round(obj,   6),
        "score":      score,
        "components": {k: round(v, 6) for k, v in comp.items()},
    }


# ──────────────────────────────────────────────────────────────────────
#  多目标评分
# ──────────────────────────────────────────────────────────────────────

def compute_sharpe_score(
    returns: list[float],
    risk_free: float = 0.0,
    annualize: int = 252,
) -> float:
    """
    计算夏普比率并映射到 [0, 100]。

    returns: 日收益率序列
    映射规则：Sharpe < 0 → 0；Sharpe ≥ 3 → 100
    """
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    std  = math.sqrt(sum((r - mean) ** 2 for r in returns) / (len(returns) - 1))
    if std <= 0:
        return 100.0 if mean > risk_free / annualize else 0.0
    sharpe = (mean - risk_free / annualize) / std * math.sqrt(annualize)
    return round(min(max(sharpe / 3.0 * 100, 0.0), 100.0), 2)


def compute_drawdown_score(
    cumulative_returns: list[float],
) -> float:
    """
    计算最大回撤并映射到 [0, 100]（回撤越小分数越高）。

    cumulative_returns: 净值序列（如 [1.0, 1.02, 0.98, ...]）
    映射规则：MDD = 0% → 100；MDD ≥ 30% → 0
    """
    if not cumulative_returns:
        return 100.0
    peak = cumulative_returns[0]
    max_dd = 0.0
    for v in cumulative_returns:
        peak = max(peak, v)
        dd   = (peak - v) / max(peak, 1e-9)
        max_dd = max(max_dd, dd)
    score = max(0.0, 1.0 - max_dd / 0.30) * 100
    return round(score, 2)


def compute_capacity_score(
    used_capital:  float,
    total_capital: float,
    target_ratio:  float = 0.85,
) -> float:
    """
    资金容量利用率评分 [0, 100]。

    用量接近 target_ratio（默认 85%）时得分最高，
    过低（资金闲置）或过高（接近上限）均扣分。
    """
    if total_capital <= 0:
        return 0.0
    ratio = used_capital / total_capital
    deviation = abs(ratio - target_ratio)
    score = max(0.0, (1.0 - deviation / target_ratio)) * 100
    return round(score, 2)


def compute_stability_score(
    returns: list[float],
    window: int = 20,
) -> float:
    """
    收益稳定性评分 [0, 100]。

    用滚动波动率的变化系数（CV）衡量稳定性：
    CV 越小，收益越稳定，分数越高。
    """
    if len(returns) < window + 1:
        return 50.0
    # 计算滚动标准差序列
    vols = []
    for i in range(window, len(returns)):
        seg  = returns[i - window: i]
        mean = sum(seg) / window
        std  = math.sqrt(sum((r - mean) ** 2 for r in seg) / (window - 1))
        vols.append(std)
    if not vols or sum(vols) <= 0:
        return 100.0
    mean_vol = sum(vols) / len(vols)
    std_vol  = math.sqrt(
        sum((v - mean_vol) ** 2 for v in vols) / max(len(vols) - 1, 1))
    cv = std_vol / max(mean_vol, 1e-9)
    score = max(0.0, (1.0 - cv)) * 100
    return round(min(score, 100.0), 2)


# ──────────────────────────────────────────────────────────────────────
#  综合多目标评分
# ──────────────────────────────────────────────────────────────────────

def compute_multi_objective_score(
    sharpe_score:    float,
    drawdown_score:  float,
    capacity_score:  float,
    stability_score: float,
    weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """
    加权合并四个子目标评分，返回综合多目标得分。

    默认权重：Sharpe 40% / Drawdown 30% / Capacity 15% / Stability 15%
    """
    w = weights or {
        "sharpe":    0.40,
        "drawdown":  0.30,
        "capacity":  0.15,
        "stability": 0.15,
    }
    composite = (
        w.get("sharpe",    0.40) * sharpe_score
        + w.get("drawdown",  0.30) * drawdown_score
        + w.get("capacity",  0.15) * capacity_score
        + w.get("stability", 0.15) * stability_score
    )
    return {
        "composite":      round(composite,    2),
        "sharpe_score":   round(sharpe_score,    2),
        "drawdown_score": round(drawdown_score,  2),
        "capacity_score": round(capacity_score,  2),
        "stability_score":round(stability_score, 2),
    }


# ──────────────────────────────────────────────────────────────────────
#  归一化工具
# ──────────────────────────────────────────────────────────────────────

def normalize(value: float, min_val: float, max_val: float) -> float:
    """将 value 线性归一化到 [0, 1]。"""
    rng = max_val - min_val
    if rng <= 0:
        return 0.5
    return round(min(max((value - min_val) / rng, 0.0), 1.0), 6)


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return min(max(value, lo), hi)
