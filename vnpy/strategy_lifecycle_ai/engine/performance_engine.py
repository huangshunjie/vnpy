"""
strategy_lifecycle_ai/engine/performance_engine.py  (Phase 2)

PerformanceEngine — 策略表现跟踪引擎（完整实现）。

实现：
  - analyze()      完整绩效计算流水线
  - multi_period   daily / weekly / monthly 多周期统计
  - 维护 PerformanceHistory（滚动 Sharpe / Drawdown 序列）
  - get_ranking()  按 Sharpe 排名

❌ 无 IO / 无网络 / 纯计算
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..constant import PerformanceRating
from ..model.performance_model import PerformanceState, PerformanceHistory
from ..utils.performance_utils import (
    compute_returns,
    compute_sharpe,
    compute_sortino,
    compute_max_drawdown,
    compute_win_rate,
    compute_profit_factor,
    compute_calmar,
    compute_turnover,
    compute_pnl_curve,
    compute_cumulative_return,
    compute_annualized_return,
    compute_multi_period,
    classify_performance,
    compute_rolling_sharpe,
    compute_rolling_drawdown,
)


class PerformanceEngine:
    """策略表现跟踪引擎（Phase 2 完整实现）。"""

    def __init__(
        self,
        log_fn:     Callable | None = None,
        annualize:  int  = 252,
        risk_free:  float = 0.0,
        history_max: int = 500,
    ) -> None:
        self._log        = log_fn or (lambda m: None)
        self._annualize  = annualize
        self._risk_free  = risk_free
        self._states:    dict[str, PerformanceState]   = {}
        self._histories: dict[str, PerformanceHistory] = {}
        self._bar_count  = 0

    # ------------------------------------------------------------------ #
    #  核心接口
    # ------------------------------------------------------------------ #

    def analyze(
        self,
        strategy_id:  str,
        pnl_series:   list[float],
        trade_count:  int = 0,
    ) -> PerformanceState:
        """
        完整绩效计算流水线。

        Parameters
        ----------
        strategy_id  : 策略 ID
        pnl_series   : 净值 / 账户价值序列（至少 2 个元素）
        trade_count  : 区间内交易次数

        Returns
        -------
        PerformanceState
        """
        self._bar_count += 1

        # ── 基础收益率 ────────────────────────────────────────────────
        returns   = compute_returns(pnl_series)
        pnl_curve = compute_pnl_curve(returns)

        # ── 核心指标 ──────────────────────────────────────────────────
        sharpe        = compute_sharpe(returns, self._risk_free, self._annualize)
        sortino       = compute_sortino(returns, self._risk_free, self._annualize)
        max_dd        = compute_max_drawdown(pnl_series)
        win_rate      = compute_win_rate(returns)
        profit_factor = compute_profit_factor(returns)
        calmar        = compute_calmar(returns, pnl_series, self._annualize)
        ann_return    = compute_annualized_return(returns, self._annualize)
        cum_return    = compute_cumulative_return(returns)
        daily_pnl     = (pnl_series[-1] - pnl_series[-2]
                         if len(pnl_series) >= 2 else 0.0)
        turnover      = compute_turnover(trade_count, len(returns))

        # ── 多周期统计 ────────────────────────────────────────────────
        multi = compute_multi_period(returns, pnl_curve) if len(returns) >= 5 else {}

        # ── 评级 ──────────────────────────────────────────────────────
        rating = classify_performance(sharpe)

        state = PerformanceState(
            strategy_id   = strategy_id,
            sharpe        = sharpe,
            sortino       = sortino,
            calmar        = calmar,
            max_drawdown  = max_dd,
            win_rate      = win_rate,
            profit_factor = profit_factor,
            total_pnl     = pnl_series[-1] - pnl_series[0] if pnl_series else 0.0,
            ann_return    = ann_return,
            cum_return    = cum_return,
            daily_pnl     = daily_pnl,
            turnover      = turnover,
            trade_count   = trade_count,
            sample_count  = len(returns),
            rating        = rating,
            period        = "daily",
            updated_at    = datetime.now(),
            multi_period  = multi,
        )

        self._states[strategy_id] = state

        # ── 历史追踪 ──────────────────────────────────────────────────
        if strategy_id not in self._histories:
            self._histories[strategy_id] = PerformanceHistory(strategy_id)
        self._histories[strategy_id].append(state)

        self._log(
            f"[PerformanceEngine] {strategy_id}"
            f"  sharpe={sharpe:.3f}"
            f"  dd={max_dd:.3f}"
            f"  wr={win_rate:.2%}"
            f"  rating={rating.value}"
        )
        return state

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_state(self, strategy_id: str) -> PerformanceState:
        if strategy_id not in self._states:
            self._states[strategy_id] = PerformanceState(
                strategy_id=strategy_id)
        return self._states[strategy_id]

    def get_history(
        self,
        strategy_id: str,
        limit: int = 30,
    ) -> list[dict]:
        h = self._histories.get(strategy_id)
        if h is None:
            return []
        return h.get_records(limit=limit)

    def get_all(self) -> list[PerformanceState]:
        return list(self._states.values())

    def get_rolling_sharpe(
        self,
        strategy_id: str,
        window: int = 60,
    ) -> list[float]:
        """获取滚动 Sharpe 序列（供 Phase 3 衰减检测使用）。"""
        h = self._histories.get(strategy_id)
        if h is None:
            return []
        sharpe_series = h.get_sharpe_series()
        if len(sharpe_series) < window:
            return sharpe_series
        return sharpe_series[-window:]

    def get_rolling_drawdown(
        self,
        strategy_id: str,
        window: int = 60,
    ) -> list[float]:
        """获取滚动最大回撤序列（供 Phase 3 衰减检测使用）。"""
        h = self._histories.get(strategy_id)
        if h is None:
            return []
        dd_series = h.get_drawdown_series()
        if len(dd_series) < window:
            return dd_series
        return dd_series[-window:]

    def get_ranking(self, top_n: int = 10) -> list[dict]:
        """按 Sharpe 排名（降序）。"""
        states = [s for s in self._states.values()
                  if s.rating != PerformanceRating.UNKNOWN]
        states.sort(key=lambda s: s.sharpe, reverse=True)
        return [s.to_dict() for s in states[:top_n]]

    def get_best(self) -> PerformanceState | None:
        ranking = self.get_ranking(top_n=1)
        if not ranking:
            return None
        sid = ranking[0]["strategy_id"]
        return self._states.get(sid)

    def get_worst(self) -> PerformanceState | None:
        states = [s for s in self._states.values()
                  if s.rating != PerformanceRating.UNKNOWN]
        if not states:
            return None
        return min(states, key=lambda s: s.sharpe)

    def get_by_rating(
        self,
        rating: PerformanceRating,
    ) -> list[PerformanceState]:
        return [s for s in self._states.values() if s.rating == rating]

    # ------------------------------------------------------------------ #
    #  参数更新
    # ------------------------------------------------------------------ #

    def update_params(
        self,
        annualize: int | None = None,
        risk_free: float | None = None,
    ) -> None:
        if annualize is not None: self._annualize = annualize
        if risk_free  is not None: self._risk_free  = risk_free

    # ------------------------------------------------------------------ #
    #  摘要
    # ------------------------------------------------------------------ #

    def summary(self) -> dict:
        all_s  = self.get_all()
        rated  = [s for s in all_s if s.rating != PerformanceRating.UNKNOWN]
        avg_sh = (sum(s.sharpe for s in rated) / len(rated)
                  if rated else 0.0)
        return {
            "tracked":      len(all_s),
            "rated":        len(rated),
            "avg_sharpe":   round(avg_sh, 4),
            "bar_count":    self._bar_count,
            "phase":        2,
        }
