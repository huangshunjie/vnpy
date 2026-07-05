"""
global_portfolio_intelligence/utils/optimization_utils.py  (Phase 3)

跨模块优化算法工具。

优化范围：
  Alpha weights       — Alpha 因子权重
  Strategy allocation — 策略资金分配
  Portfolio weights   — 组合持仓权重
  Capital distribution— 资金分配比例
  Execution intensity — 执行力度

算法：
  梯度上升（无约束）
  投影梯度（simplex约束：权重之和=1，各分量>=0）
  风险平价
  等权基准
"""
from __future__ import annotations
import math


# ──────────────────────────────────────────────────────────────────────
#  Simplex 投影（权重归一化到概率单纯形）
# ──────────────────────────────────────────────────────────────────────

def project_to_simplex(weights: list[float]) -> list[float]:
    """
    将任意向量投影到标准概率单纯形：
      sum(w) = 1，w_i >= 0

    使用排序算法，O(n log n)。
    """
    n = len(weights)
    if n == 0:
        return []
    u = sorted(weights, reverse=True)
    cssv = 0.0
    rho  = 0
    for j in range(n):
        cssv += u[j]
        if u[j] - (cssv - 1.0) / (j + 1) > 0:
            rho = j
    theta = (sum(u[:rho + 1]) - 1.0) / (rho + 1)
    return [round(max(w - theta, 0.0), 8) for w in weights]


def normalize_weights(weights: list[float]) -> list[float]:
    """简单归一化（不保证非负性，适用于无约束场景）。"""
    total = sum(weights)
    if abs(total) < 1e-12:
        n = len(weights)
        return [1.0 / n] * n if n > 0 else []
    return [round(w / total, 8) for w in weights]


# ──────────────────────────────────────────────────────────────────────
#  梯度估算（数值梯度，用于黑盒目标函数）
# ──────────────────────────────────────────────────────────────────────

def numerical_gradient(
    func,
    x: list[float],
    eps: float = 1e-5,
) -> list[float]:
    """
    数值梯度（中心差分）。

    func: 接受 list[float] → float 的目标函数
    x:    当前参数向量
    """
    grad = []
    for i in range(len(x)):
        x_plus  = list(x); x_plus[i]  += eps
        x_minus = list(x); x_minus[i] -= eps
        g = (func(x_plus) - func(x_minus)) / (2 * eps)
        grad.append(g)
    return grad


# ──────────────────────────────────────────────────────────────────────
#  投影梯度上升（simplex约束）
# ──────────────────────────────────────────────────────────────────────

def projected_gradient_ascent(
    func,
    x0:            list[float],
    lr:            float = 0.05,
    n_iter:        int   = 50,
    tol:           float = 1e-6,
    constrained:   bool  = True,
) -> tuple[list[float], list[float]]:
    """
    投影梯度上升（最大化目标函数）。

    func:        list[float] → float，目标函数（越大越好）
    x0:          初始参数向量
    lr:          学习率
    n_iter:      最大迭代次数
    tol:         收敛阈值（相邻两步目标值变化）
    constrained: True → 每步投影到单纯形（权重之和=1）

    Returns (best_x, obj_history)
    """
    x = list(x0)
    if constrained:
        x = project_to_simplex(x)

    obj_history = []
    prev_obj    = func(x)
    obj_history.append(prev_obj)

    for _ in range(n_iter):
        grad = numerical_gradient(func, x)
        # 梯度上升步
        x_new = [xi + lr * gi for xi, gi in zip(x, grad)]
        if constrained:
            x_new = project_to_simplex(x_new)

        new_obj = func(x_new)
        obj_history.append(new_obj)

        if abs(new_obj - prev_obj) < tol:
            x = x_new
            break

        x        = x_new
        prev_obj = new_obj

    return x, obj_history


# ──────────────────────────────────────────────────────────────────────
#  风险平价权重
# ──────────────────────────────────────────────────────────────────────

def risk_parity_weights(
    volatilities: list[float],
    correlation:  list[list[float]] | None = None,
) -> list[float]:
    """
    风险平价权重（简化版，忽略相关性时等于逆波动率加权）。

    volatilities: 每个资产/策略的波动率
    correlation:  相关矩阵（可选，暂不使用，预留 Phase 4）

    Returns 归一化权重列表
    """
    n = len(volatilities)
    if n == 0:
        return []
    inv_vols = [1.0 / max(v, 1e-9) for v in volatilities]
    return normalize_weights(inv_vols)


# ──────────────────────────────────────────────────────────────────────
#  等权基准
# ──────────────────────────────────────────────────────────────────────

def equal_weights(n: int) -> list[float]:
    if n <= 0:
        return []
    return [round(1.0 / n, 8)] * n


# ──────────────────────────────────────────────────────────────────────
#  跨模块联合评分
# ──────────────────────────────────────────────────────────────────────

def compute_cross_module_score(
    alpha_weights:    list[float],
    strategy_allocs:  list[float],
    portfolio_weights:list[float],
    capital_dist:     list[float],
    exec_intensity:   list[float],
    alpha_scores:     list[float],
    strategy_scores:  list[float],
    portfolio_scores: list[float],
) -> dict[str, float]:
    """
    计算跨模块联合评分。

    每个维度：权重向量 ⊙ 评分向量 → 加权平均得分
    最终综合分 = 五个维度的均值（各 25% / 25% / 25% / 12.5% / 12.5%）

    Returns dict with per-dimension scores and composite.
    """
    def weighted_avg(weights, scores):
        if not weights or not scores:
            return 50.0
        n = min(len(weights), len(scores))
        total_w = sum(weights[:n])
        if total_w <= 0:
            return sum(scores[:n]) / n
        return sum(w * s for w, s in zip(weights[:n], scores[:n])) / total_w

    alpha_dim     = weighted_avg(alpha_weights,    alpha_scores)
    strategy_dim  = weighted_avg(strategy_allocs,  strategy_scores)
    portfolio_dim = weighted_avg(portfolio_weights, portfolio_scores)

    # execution intensity → 效率分（越高越好，线性映射到0-100）
    exec_score = (sum(exec_intensity) / len(exec_intensity) * 100
                  if exec_intensity else 50.0)
    exec_score = min(max(exec_score, 0.0), 100.0)

    # capital distribution → 集中度惩罚（HHI）
    cap_dim = _capital_concentration_score(capital_dist)

    composite = round(
        0.25 * alpha_dim
        + 0.25 * strategy_dim
        + 0.25 * portfolio_dim
        + 0.125 * exec_score
        + 0.125 * cap_dim,
        2,
    )
    return {
        "composite":       composite,
        "alpha_score":     round(alpha_dim,    2),
        "strategy_score":  round(strategy_dim, 2),
        "portfolio_score": round(portfolio_dim,2),
        "execution_score": round(exec_score,   2),
        "capital_score":   round(cap_dim,      2),
    }


def _capital_concentration_score(dist: list[float]) -> float:
    """
    资金集中度评分：HHI 越低（越分散）分数越高。
    HHI = sum(w_i^2)
    HHI_min = 1/n（等权），HHI_max = 1（全集中）
    """
    if not dist:
        return 50.0
    n = len(dist)
    total = sum(dist)
    if total <= 0:
        return 50.0
    norm = [d / total for d in dist]
    hhi  = sum(w ** 2 for w in norm)
    hhi_min = 1.0 / n
    score = max(0.0, (1.0 - hhi) / max(1.0 - hhi_min, 1e-9)) * 100
    return round(score, 2)


# ──────────────────────────────────────────────────────────────────────
#  优化循环收敛检测
# ──────────────────────────────────────────────────────────────────────

def has_converged(
    history: list[float],
    window:  int   = 5,
    tol:     float = 1e-4,
) -> bool:
    """判断目标函数历史是否已收敛（最近 window 步的标准差 < tol）。"""
    if len(history) < window:
        return False
    recent = history[-window:]
    mean   = sum(recent) / window
    std    = math.sqrt(sum((v - mean) ** 2 for v in recent) / window)
    return std < tol
