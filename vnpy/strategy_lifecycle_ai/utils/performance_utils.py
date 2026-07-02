"""
strategy_lifecycle_ai/utils/performance_utils.py  (Phase 2)

策略表现指标计算工具函数（完整实现）。

实现：
  - compute_returns           对数收益率序列
  - compute_sharpe            年化 Sharpe Ratio
  - compute_max_drawdown      最大回撤
  - compute_win_rate          胜率
  - compute_turnover          换手率代理
  - compute_pnl_curve         累积 PnL 曲线
  - compute_sortino           Sortino Ratio
  - compute_calmar            Calmar Ratio
  - compute_multi_period      多周期统计
  - classify_performance      评级分类

❌ 无 IO / 无网络 / 纯计算
"""

from __future__ import annotations
import math
from ..constant import PerformanceRating


# ─────────────────────────────────────────────────────────────────────────────
#  收益率
# ─────────────────────────────────────────────────────────────────────────────

def compute_returns(pnl_series: list[float]) -> list[float]:
    """
    从 PnL 序列计算简单收益率。

    Parameters
    ----------
    pnl_series : 净值或账户价值序列（至少 2 个元素）

    Returns
    -------
    list[float]  长度 = len(pnl_series) - 1
    """
    if len(pnl_series) < 2:
        return []
    returns = []
    for i in range(1, len(pnl_series)):
        prev = pnl_series[i - 1]
        curr = pnl_series[i]
        if prev == 0:
            returns.append(0.0)
        else:
            returns.append((curr - prev) / abs(prev))
    return returns


def compute_log_returns(pnl_series: list[float]) -> list[float]:
    """对数收益率序列。"""
    if len(pnl_series) < 2:
        return []
    returns = []
    for i in range(1, len(pnl_series)):
        prev = pnl_series[i - 1]
        curr = pnl_series[i]
        if prev <= 0 or curr <= 0:
            returns.append(0.0)
        else:
            returns.append(math.log(curr / prev))
    return returns


# ─────────────────────────────────────────────────────────────────────────────
#  Sharpe Ratio
# ─────────────────────────────────────────────────────────────────────────────

def compute_sharpe(
    returns:   list[float],
    risk_free: float = 0.0,
    annualize: int   = 252,
) -> float:
    """
    年化 Sharpe Ratio。

    Parameters
    ----------
    returns   : 日收益率序列
    risk_free : 日无风险利率（默认 0）
    annualize : 年化系数（日线=252，周=52，月=12）

    Returns
    -------
    float  Sharpe Ratio，数据不足时返回 0.0
    """
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free for r in returns]
    n      = len(excess)
    mean   = sum(excess) / n
    var    = sum((r - mean) ** 2 for r in excess) / (n - 1) if n > 1 else 0.0
    std    = math.sqrt(var) if var > 0 else 0.0
    if std == 0:
        return 0.0
    return round(mean / std * math.sqrt(annualize), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  Sortino Ratio
# ─────────────────────────────────────────────────────────────────────────────

def compute_sortino(
    returns:   list[float],
    risk_free: float = 0.0,
    annualize: int   = 252,
) -> float:
    """
    年化 Sortino Ratio（仅惩罚下行波动率）。
    """
    if len(returns) < 2:
        return 0.0
    excess     = [r - risk_free for r in returns]
    mean       = sum(excess) / len(excess)
    downside   = [r for r in excess if r < 0]
    if not downside:
        return 999.0   # 无下行风险
    down_var   = sum(r ** 2 for r in downside) / len(downside)
    down_std   = math.sqrt(down_var)
    if down_std == 0:
        return 0.0
    return round(mean / down_std * math.sqrt(annualize), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  最大回撤
# ─────────────────────────────────────────────────────────────────────────────

def compute_max_drawdown(pnl_series: list[float]) -> float:
    """
    最大回撤（以峰值的百分比表示，正值）。

    Returns
    -------
    float  [0, 1]，0 = 无回撤
    """
    if len(pnl_series) < 2:
        return 0.0
    peak    = pnl_series[0]
    max_dd  = 0.0
    for v in pnl_series:
        if v > peak:
            peak = v
        dd = (peak - v) / abs(peak) if peak != 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 6)


def compute_drawdown_series(pnl_series: list[float]) -> list[float]:
    """
    逐日回撤序列（从当前高点的百分比回撤）。
    """
    if not pnl_series:
        return []
    peak   = pnl_series[0]
    result = []
    for v in pnl_series:
        if v > peak:
            peak = v
        dd = (peak - v) / abs(peak) if peak != 0 else 0.0
        result.append(round(dd, 6))
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  Calmar Ratio
# ─────────────────────────────────────────────────────────────────────────────

def compute_calmar(
    returns:      list[float],
    pnl_series:   list[float],
    annualize:    int = 252,
) -> float:
    """
    Calmar Ratio = 年化收益 / 最大回撤。
    """
    max_dd = compute_max_drawdown(pnl_series)
    if max_dd == 0 or not returns:
        return 0.0
    ann_return = sum(returns) / len(returns) * annualize
    return round(ann_return / max_dd, 6)


# ─────────────────────────────────────────────────────────────────────────────
#  胜率
# ─────────────────────────────────────────────────────────────────────────────

def compute_win_rate(returns: list[float]) -> float:
    """
    胜率 = 正收益天数 / 总天数。

    Returns
    -------
    float [0, 1]
    """
    if not returns:
        return 0.0
    wins = sum(1 for r in returns if r > 0)
    return round(wins / len(returns), 6)


def compute_profit_factor(returns: list[float]) -> float:
    """
    Profit Factor = 总盈利 / 总亏损绝对值。
    """
    gains  = sum(r for r in returns if r > 0)
    losses = sum(abs(r) for r in returns if r < 0)
    if losses == 0:
        return 999.0
    return round(gains / losses, 6)


# ─────────────────────────────────────────────────────────────────────────────
#  换手率
# ─────────────────────────────────────────────────────────────────────────────

def compute_turnover(
    trade_count: int,
    period_days: int,
) -> float:
    """
    换手率代理 = 交易次数 / 交易天数。

    Returns
    -------
    float  日均交易次数（0 = 无交易）
    """
    if period_days <= 0:
        return 0.0
    return round(trade_count / period_days, 6)


# ─────────────────────────────────────────────────────────────────────────────
#  累积 PnL 曲线
# ─────────────────────────────────────────────────────────────────────────────

def compute_pnl_curve(returns: list[float], start: float = 1.0) -> list[float]:
    """
    从收益率序列构建累积净值曲线（初始值 = start）。
    """
    curve = [start]
    for r in returns:
        curve.append(round(curve[-1] * (1 + r), 6))
    return curve


def compute_cumulative_return(returns: list[float]) -> float:
    """
    区间总收益率。
    """
    if not returns:
        return 0.0
    nav = 1.0
    for r in returns:
        nav *= (1 + r)
    return round(nav - 1.0, 6)


def compute_annualized_return(
    returns:   list[float],
    annualize: int = 252,
) -> float:
    """年化收益率。"""
    if not returns:
        return 0.0
    return round(sum(returns) / len(returns) * annualize, 6)


# ─────────────────────────────────────────────────────────────────────────────
#  多周期统计
# ─────────────────────────────────────────────────────────────────────────────

def compute_multi_period(
    returns:   list[float],
    pnl_curve: list[float],
) -> dict:
    """
    计算 daily / weekly / monthly 多周期统计。

    Parameters
    ----------
    returns   : 日收益率序列
    pnl_curve : 累积净值曲线

    Returns
    -------
    dict  {period: {sharpe, max_drawdown, win_rate, ann_return}}
    """
    def _aggregate(rets: list[float], step: int) -> list[float]:
        """按步长聚合收益率（简单相加近似）。"""
        agg = []
        for i in range(0, len(rets), step):
            chunk = rets[i: i + step]
            if chunk:
                cum = 1.0
                for r in chunk:
                    cum *= (1 + r)
                agg.append(cum - 1.0)
        return agg

    result: dict[str, dict] = {}
    for period, step, ann in [
        ("daily",   1,  252),
        ("weekly",  5,  52),
        ("monthly", 21, 12),
    ]:
        agg = _aggregate(returns, step)
        curve_step = pnl_curve[::step]
        result[period] = {
            "sharpe":       compute_sharpe(agg, annualize=ann),
            "max_drawdown": compute_max_drawdown(curve_step),
            "win_rate":     compute_win_rate(agg),
            "ann_return":   compute_annualized_return(agg, annualize=ann),
            "sample_count": len(agg),
        }
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  评级分类
# ─────────────────────────────────────────────────────────────────────────────

def classify_performance(sharpe: float) -> PerformanceRating:
    """
    根据 Sharpe Ratio 评级。

    ≥ 2.0 → EXCELLENT
    ≥ 1.0 → GOOD
    ≥ 0.0 → NEUTRAL
    <  0.0 → WEAK
    """
    if sharpe >= 2.0: return PerformanceRating.EXCELLENT
    if sharpe >= 1.0: return PerformanceRating.GOOD
    if sharpe >= 0.0: return PerformanceRating.NEUTRAL
    return PerformanceRating.WEAK


# ─────────────────────────────────────────────────────────────────────────────
#  滚动统计（供衰减检测 Phase 3 使用）
# ─────────────────────────────────────────────────────────────────────────────

def compute_rolling_sharpe(
    returns:   list[float],
    window:    int = 60,
    annualize: int = 252,
) -> list[float]:
    """
    滚动 Sharpe 序列（供 Phase 3 衰减检测使用）。
    """
    if len(returns) < window:
        return [compute_sharpe(returns, annualize=annualize)]
    result = []
    for i in range(window, len(returns) + 1):
        chunk = returns[i - window: i]
        result.append(compute_sharpe(chunk, annualize=annualize))
    return result


def compute_rolling_drawdown(
    pnl_series: list[float],
    window:     int = 60,
) -> list[float]:
    """
    滚动最大回撤序列（供 Phase 3 衰减检测使用）。
    """
    if len(pnl_series) < window:
        return [compute_max_drawdown(pnl_series)]
    result = []
    for i in range(window, len(pnl_series) + 1):
        chunk = pnl_series[i - window: i]
        result.append(compute_max_drawdown(chunk))
    return result
