"""
strategy_lifecycle_ai/utils/decay_utils.py  (Phase 3)

衰减检测工具函数（完整实现）。

实现：
  - compute_sharpe_slope        Sharpe 变化斜率（线性回归）
  - compute_dd_expansion        回撤扩张量
  - compute_ic_decay_proxy      IC 衰减代理（自相关衰减）
  - compute_performance_slope   绩效斜率（PnL 序列线性回归）
  - compute_decay_score         综合衰减评分 [0,1]
  - classify_decay_level        衰减等级分类
  - compute_decay_persistence   持续衰减天数
  - compute_regime_sensitivity  对市场状态的敏感度

❌ 无 IO / 无网络 / 纯计算
"""

from __future__ import annotations
import math
from ..constant import DecayLevel


# ─────────────────────────────────────────────────────────────────────────────
#  内部工具：线性回归斜率
# ─────────────────────────────────────────────────────────────────────────────

def _linear_slope(series: list[float]) -> float:
    """
    最小二乘线性回归斜率。
    y = a + b*x，返回 b（斜率）。
    数据不足时返回 0.0。
    """
    n = len(series)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(series) / n
    num = sum((i - x_mean) * (series[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    return num / den


def _z_score(value: float, mean: float, std: float) -> float:
    """标准化得分，std=0 时返回 0。"""
    if std == 0:
        return 0.0
    return (value - mean) / std


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# ─────────────────────────────────────────────────────────────────────────────
#  Sharpe 衰减斜率
# ─────────────────────────────────────────────────────────────────────────────

def compute_sharpe_slope(
    sharpe_series: list[float],
    window: int = 10,
) -> float:
    """
    计算滚动 Sharpe 序列的线性回归斜率。

    负斜率 = Sharpe 下降（衰减信号）。
    正斜率 = Sharpe 恢复（修复信号）。

    Parameters
    ----------
    sharpe_series : 历史 Sharpe 序列（每 bar 一次）
    window        : 使用最近 N 个点

    Returns
    -------
    float  斜率（每 bar）
    """
    if len(sharpe_series) < 2:
        return 0.0
    tail = sharpe_series[-window:]
    return round(_linear_slope(tail), 8)


# ─────────────────────────────────────────────────────────────────────────────
#  回撤扩张量
# ─────────────────────────────────────────────────────────────────────────────

def compute_dd_expansion(
    dd_series: list[float],
    window: int = 10,
) -> float:
    """
    计算最大回撤序列的扩张量。

    定义：近期均值回撤 - 历史均值回撤（正值 = 回撤在扩大）。

    Parameters
    ----------
    dd_series : 历史最大回撤序列（每 bar 一次），值 ∈ [0,1]
    window    : 近期窗口大小

    Returns
    -------
    float  回撤扩张量 ∈ [-1, 1]（正 = 扩张，负 = 收缩）
    """
    if len(dd_series) < window * 2:
        return 0.0
    recent  = dd_series[-window:]
    earlier = dd_series[-window * 2: -window]
    if not earlier:
        return 0.0
    recent_mean  = sum(recent)  / len(recent)
    earlier_mean = sum(earlier) / len(earlier)
    return round(recent_mean - earlier_mean, 6)


# ─────────────────────────────────────────────────────────────────────────────
#  IC 衰减代理
# ─────────────────────────────────────────────────────────────────────────────

def compute_ic_decay_proxy(
    returns: list[float],
    window: int = 20,
    lag: int = 1,
) -> float:
    """
    IC 衰减代理：通过收益率序列的 lag-1 自相关衰减推断因子 IC 退化。

    原理：
      - 高自相关 → 因子仍有预测力
      - 自相关趋向 0 → 因子 IC 衰减
      - 返回 1 - |autocorr|，越高 = 衰减越严重

    Parameters
    ----------
    returns : 日收益率序列
    window  : 使用最近 N 期
    lag     : 自相关滞后阶数

    Returns
    -------
    float [0, 1]（0 = IC 完整，1 = IC 完全衰减）
    """
    series = returns[-window:]
    n = len(series)
    if n < lag + 2:
        return 0.5  # 数据不足，中性值

    mean = sum(series) / n
    var  = sum((r - mean) ** 2 for r in series) / n
    if var == 0:
        return 1.0  # 无波动 = IC 失效

    cov = sum(
        (series[i] - mean) * (series[i - lag] - mean)
        for i in range(lag, n)
    ) / (n - lag)

    autocorr = cov / var
    return round(_clamp(1.0 - abs(autocorr)), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  绩效斜率
# ─────────────────────────────────────────────────────────────────────────────

def compute_performance_slope(
    pnl_series: list[float],
    window: int = 20,
) -> float:
    """
    计算 PnL 曲线（净值序列）的线性回归斜率。

    负斜率 = 净值持续下降（绩效衰减信号）。

    Parameters
    ----------
    pnl_series : 净值序列
    window     : 使用最近 N 个点

    Returns
    -------
    float  斜率（每 bar）
    """
    if len(pnl_series) < 2:
        return 0.0
    tail = pnl_series[-window:]
    return round(_linear_slope(tail), 8)


# ─────────────────────────────────────────────────────────────────────────────
#  综合衰减评分
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_WEIGHTS = {
    "sharpe_slope":  0.35,
    "dd_expansion":  0.30,
    "ic_decay":      0.20,
    "perf_slope":    0.15,
}


def compute_decay_score(
    sharpe_slope:  float,
    dd_expansion:  float,
    ic_decay:      float,
    perf_slope:    float,
    weights: dict | None = None,
) -> float:
    """
    综合衰减评分 [0, 1]（高 = 衰减严重）。

    各分量归一化规则：
      sharpe_slope : 负值越大 → 分数越高（最大惩罚 0.05/bar）
      dd_expansion : 正值越大 → 分数越高（最大 0.15）
      ic_decay     : 直接使用 [0,1]
      perf_slope   : 负值越大 → 分数越高（最大惩罚 0.01/bar）

    Parameters
    ----------
    sharpe_slope : Sharpe 变化斜率（通常为负）
    dd_expansion : 回撤扩张量
    ic_decay     : IC 衰减代理 [0,1]
    perf_slope   : 绩效斜率（通常为负）
    weights      : 自定义权重字典（键同上）

    Returns
    -------
    float [0, 1]
    """
    w = weights if weights is not None else _DEFAULT_WEIGHTS

    # 各指标归一化到 [0,1]
    s_norm  = _clamp(-sharpe_slope / 0.05)       # 斜率为 -0.05 → score=1.0
    dd_norm = _clamp(dd_expansion  / 0.15)       # 扩张 0.15 → score=1.0
    ic_norm = _clamp(ic_decay)                   # 直接 [0,1]
    p_norm  = _clamp(-perf_slope   / 0.01)       # 斜率为 -0.01 → score=1.0

    score = (
        w.get("sharpe_slope", 0.35) * s_norm  +
        w.get("dd_expansion", 0.30) * dd_norm +
        w.get("ic_decay",     0.20) * ic_norm +
        w.get("perf_slope",   0.15) * p_norm
    )
    return round(_clamp(score), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  衰减等级分类
# ─────────────────────────────────────────────────────────────────────────────

_DECAY_THRESHOLDS = {
    DecayLevel.CRITICAL: 0.75,
    DecayLevel.SEVERE:   0.55,
    DecayLevel.MODERATE: 0.35,
    DecayLevel.MILD:     0.15,
}


def classify_decay_level(
    decay_score:  float,
    sharpe_slope: float,
    dd_expansion: float,
    override_threshold: float | None = None,
) -> DecayLevel:
    """
    综合衰减等级判定。

    主规则（decay_score 分段）：
      ≥ 0.75 → CRITICAL
      ≥ 0.55 → SEVERE
      ≥ 0.35 → MODERATE
      ≥ 0.15 → MILD
      <  0.15 → NONE

    强制升级规则：
      Sharpe 下降 + 回撤上升 → 至少 MODERATE
    """
    thresholds = _DECAY_THRESHOLDS.copy()
    if override_threshold is not None:
        thresholds[DecayLevel.MODERATE] = override_threshold

    level = DecayLevel.NONE
    for lv, thr in sorted(thresholds.items(), key=lambda x: -x[1]):
        if decay_score >= thr:
            level = lv
            break

    # 强制升级：Sharpe 下降 + 回撤上升 → 至少 MODERATE
    if sharpe_slope < -0.005 and dd_expansion > 0.01:
        if level in (DecayLevel.NONE, DecayLevel.MILD):
            level = DecayLevel.MODERATE

    return level


# ─────────────────────────────────────────────────────────────────────────────
#  持续衰减天数
# ─────────────────────────────────────────────────────────────────────────────

def compute_decay_persistence(
    decay_level_history: list[DecayLevel],
) -> int:
    """
    计算从最近一次非 NONE 状态起，连续衰减的 bar 数。

    Parameters
    ----------
    decay_level_history : 历史衰减等级序列（最新在末尾）

    Returns
    -------
    int  连续衰减 bar 数（0 = 当前无衰减）
    """
    count = 0
    for level in reversed(decay_level_history):
        if level != DecayLevel.NONE:
            count += 1
        else:
            break
    return count


# ─────────────────────────────────────────────────────────────────────────────
#  市场状态敏感度
# ─────────────────────────────────────────────────────────────────────────────

def compute_regime_sensitivity(
    returns_bull: list[float],
    returns_bear: list[float],
) -> float:
    """
    策略对市场状态切换的敏感度。

    定义：牛市平均收益 vs 熊市平均收益的差异程度。
    高敏感度 = 策略收益高度依赖市场方向（状态切换风险大）。

    Returns
    -------
    float [0, 1]（0 = 无敏感度，1 = 极度方向性依赖）
    """
    if not returns_bull or not returns_bear:
        return 0.0
    mean_bull = sum(returns_bull) / len(returns_bull)
    mean_bear = sum(returns_bear) / len(returns_bear)
    diff = abs(mean_bull - mean_bear)
    # 归一化：差异 ≥ 0.02（日均 2%）视为极度敏感
    return round(_clamp(diff / 0.02), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  滚动衰减评分序列
# ─────────────────────────────────────────────────────────────────────────────

def compute_rolling_decay_scores(
    sharpe_series: list[float],
    dd_series:     list[float],
    returns:       list[float],
    pnl_series:    list[float],
    window: int = 10,
) -> list[float]:
    """
    生成滚动衰减评分序列（供历史可视化使用）。

    Parameters
    ----------
    sharpe_series : 历史 Sharpe 序列
    dd_series     : 历史最大回撤序列
    returns       : 日收益率序列
    pnl_series    : 净值序列
    window        : 滚动窗口大小

    Returns
    -------
    list[float]  每个时点的衰减评分
    """
    n = min(len(sharpe_series), len(dd_series), len(returns), len(pnl_series))
    if n < window:
        return []
    scores = []
    for i in range(window, n + 1):
        sh_slope = compute_sharpe_slope(sharpe_series[:i], window)
        dd_exp   = compute_dd_expansion(dd_series[:i], window)
        ic_d     = compute_ic_decay_proxy(returns[:i], window)
        p_slope  = compute_performance_slope(pnl_series[:i], window)
        score    = compute_decay_score(sh_slope, dd_exp, ic_d, p_slope)
        scores.append(score)
    return scores
