"""
execution_intelligence_ai/utils/impact_utils.py  (Phase 3)

市场冲击工具函数 — 三层冲击模型：
  1. Linear Model        — 线性近似（简单基准）
  2. Square-Root Model   — 平方根模型（行业标准）
  3. Almgren-Chriss      — 临时冲击 + 永久冲击分离

所有函数只使用纯 Python / math，无外部依赖。
"""
from __future__ import annotations
import math


# ──────────────────────────────────────────────────────────────────────
#  基础参数说明
#
#  order_size : 本次订单手数/股数
#  adv        : 日均成交量（Average Daily Volume）
#  volatility : 日收益率标准差（如 0.02 = 2%/day）
#  spread_bps : 买卖价差（基点）
#  eta        : 临时冲击系数（Almgren-Chriss），典型值 0.1~0.6
#  gamma      : 永久冲击系数（Almgren-Chriss），典型值 0.05~0.3
#  返回值均为基点（bp = 0.01%）
# ──────────────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────────────
#  Layer 1: Linear Model
# ──────────────────────────────────────────────────────────────────────

def linear_impact(
    order_size: float,
    adv: float,
    volatility: float,
    coeff: float = 1.0,
) -> float:
    """
    线性冲击模型（基准）。

    Impact(bp) = coeff × volatility × (order_size / adv) × 10000

    适用场景：小订单、快速估算。
    """
    if adv <= 0 or order_size <= 0:
        return 0.0
    ratio = order_size / adv
    return round(coeff * volatility * ratio * 10000, 4)


# ──────────────────────────────────────────────────────────────────────
#  Layer 2: Square-Root Model（行业标准）
# ──────────────────────────────────────────────────────────────────────

def sqrt_impact(
    order_size: float,
    adv: float,
    volatility: float,
    coeff: float = 1.0,
) -> float:
    """
    平方根冲击模型（Barra / JP Morgan 标准）。

    Impact(bp) = coeff × volatility × sqrt(order_size / adv) × 10000

    平方根关系反映了流动性的凹性：
    大订单冲击小于线性预测，因为交易者会适应。
    """
    if adv <= 0 or order_size <= 0:
        return 0.0
    ratio = order_size / adv
    return round(coeff * volatility * math.sqrt(ratio) * 10000, 4)


# ──────────────────────────────────────────────────────────────────────
#  Layer 3: Almgren-Chriss（临时 + 永久分离）
# ──────────────────────────────────────────────────────────────────────

def almgren_chriss_impact(
    order_size: float,
    adv: float,
    volatility: float,
    eta: float = 0.2,
    gamma: float = 0.1,
) -> dict[str, float]:
    """
    Almgren-Chriss 冲击分解模型。

    临时冲击（Temporary Impact）：
      I_temp(bp) = eta × volatility × sqrt(order_size / adv) × 10000
      — 执行期间的价格压力，执行完毕后恢复

    永久冲击（Permanent Impact）：
      I_perm(bp) = gamma × volatility × (order_size / adv) × 10000
      — 信息效应导致的永久价格移动

    总冲击：
      I_total = I_temp + I_perm

    Returns dict with keys:
      temporary_bp, permanent_bp, total_bp, ratio (temp/total)
    """
    if adv <= 0 or order_size <= 0:
        return {"temporary_bp": 0.0, "permanent_bp": 0.0,
                "total_bp": 0.0, "ratio": 0.0}

    ratio = order_size / adv
    temp  = eta   * volatility * math.sqrt(ratio) * 10000
    perm  = gamma * volatility * ratio            * 10000
    total = temp + perm
    r     = round(temp / total, 4) if total > 0 else 0.0

    return {
        "temporary_bp": round(temp,  4),
        "permanent_bp": round(perm,  4),
        "total_bp":     round(total, 4),
        "ratio":        r,               # 临时冲击占比
    }


# ──────────────────────────────────────────────────────────────────────
#  流动性评分
# ──────────────────────────────────────────────────────────────────────

def calc_liquidity_score(
    adv: float,
    spread_bps: float,
    order_size: float,
    adv_max: float = 1e8,
    spread_max: float = 50.0,
) -> float:
    """
    综合流动性评分 [0, 1]，越高越好。

    组成：
      - ADV 分量（40%）：adv / adv_max，反映市场深度
      - 价差分量（40%）：1 - spread / spread_max，越窄越好
      - 规模分量（20%）：1 - order_size / adv，订单越小相对越好
    """
    adv_score    = min(adv / max(adv_max, 1), 1.0)
    spread_score = max(0.0, 1.0 - spread_bps / max(spread_max, 1))
    size_ratio   = min(order_size / max(adv, 1), 1.0)
    size_score   = max(0.0, 1.0 - size_ratio)

    score = 0.40 * adv_score + 0.40 * spread_score + 0.20 * size_score
    return round(min(max(score, 0.0), 1.0), 4)


# ──────────────────────────────────────────────────────────────────────
#  订单量 vs 冲击曲线（用于 UI 绘图）
# ──────────────────────────────────────────────────────────────────────

def impact_curve(
    adv: float,
    volatility: float,
    model: str = "sqrt",
    n_points: int = 20,
    max_ratio: float = 0.5,
    eta: float = 0.2,
    gamma: float = 0.1,
) -> list[dict]:
    """
    生成冲击曲线数据点（用于 UI 折线图）。

    model: "linear" | "sqrt" | "almgren_chriss"
    Returns list of {"ratio": ..., "impact_bp": ...}
    """
    if adv <= 0 or volatility <= 0:
        return []

    points: list[dict] = []
    for i in range(1, n_points + 1):
        ratio = max_ratio * i / n_points
        size  = ratio * adv

        if model == "linear":
            imp_bp = linear_impact(size, adv, volatility)
        elif model == "almgren_chriss":
            imp_bp = almgren_chriss_impact(size, adv, volatility,
                                           eta, gamma)["total_bp"]
        else:  # sqrt (default)
            imp_bp = sqrt_impact(size, adv, volatility)

        points.append({"ratio": round(ratio, 4), "impact_bp": round(imp_bp, 4)})
    return points


# ──────────────────────────────────────────────────────────────────────
#  冲击等级分类
# ──────────────────────────────────────────────────────────────────────

def classify_impact_level(impact_bps: float) -> str:
    """按冲击基点划分等级。"""
    if impact_bps < 2:
        return "negligible"
    elif impact_bps < 10:
        return "low"
    elif impact_bps < 30:
        return "medium"
    elif impact_bps < 80:
        return "high"
    return "severe"


# ──────────────────────────────────────────────────────────────────────
#  实时修正（基于执行反馈）
# ──────────────────────────────────────────────────────────────────────

def adjust_impact_estimate(
    estimated_bp:    float,
    realized_bp:     float,
    alpha:           float = 0.3,
) -> float:
    """
    指数加权修正：将历史估算向实现值靠拢。

    adjusted = (1 - alpha) * estimated + alpha * realized
    alpha=0 完全保持原估算，alpha=1 完全用实现值替代。
    """
    return round((1 - alpha) * estimated_bp + alpha * realized_bp, 4)


def estimate_linear_impact(
    order_size: float,
    adv: float,
    volatility: float,
) -> float:
    """向后兼容 Phase 1 接口（别名）。"""
    return sqrt_impact(order_size, adv, volatility)
