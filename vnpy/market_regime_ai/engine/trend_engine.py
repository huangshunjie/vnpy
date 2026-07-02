"""
market_regime_ai/engine/trend_engine.py  (Phase 3)

TrendEngine — 趋势分析引擎（完整实现）。

实现：
  - 接收价格序列（close prices）
  - 计算趋势强度、方向、持续性、ADX代理、线性回归斜率/R²
  - 输出 TrendState
  - 维护方向历史序列（用于持续性计算）

❌ 无 IO / 无网络 / 纯计算
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..constant import TrendDirection
from ..model.trend_model import TrendState
from ..utils.trend_utils import (
    compute_linear_regression,
    compute_trend_strength,
    compute_trend_persistence,
    classify_trend_direction,
    compute_adx_proxy,
    compute_sma,
)


class TrendEngine:
    """
    趋势分析引擎（Phase 3 完整实现）。

    用法：
        engine = TrendEngine(log_fn=print)
        state  = engine.analyze(prices)
    """

    def __init__(
        self,
        log_fn:              Callable | None = None,
        window:              int   = 20,
        strong_threshold:    float = 0.50,
        weak_threshold:      float = 0.20,
        persistence_window:  int   = 10,
        history_max_len:     int   = 500,
    ) -> None:
        self._log               = log_fn or (lambda m: None)
        self._window            = window
        self._strong_thr        = strong_threshold
        self._weak_thr          = weak_threshold
        self._persistence_win   = persistence_window
        self._history_max_len   = history_max_len

        self._state             = TrendState()
        self._dir_history:      list[TrendDirection] = []
        self._bar_count         = 0

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def analyze(self, prices: list[float]) -> TrendState:
        """
        计算趋势状态。

        Parameters
        ----------
        prices : 收盘价序列（至少需要 window + 2 个值）

        Returns
        -------
        TrendState
        """
        self._bar_count += 1

        if len(prices) < 4:
            self._log(f"[TrendEngine] insufficient data ({len(prices)} bars)")
            return self._state

        # 趋势强度 + R²
        strength = compute_trend_strength(
            prices, window=self._window)

        slope, r_squared = compute_linear_regression(
            prices, window=self._window)

        # ADX 代理
        adx = compute_adx_proxy(prices, window=self._window)

        # 趋势方向
        direction = classify_trend_direction(
            slope     = slope,
            strength  = strength,
            strong_threshold = self._strong_thr,
            weak_threshold   = self._weak_thr,
        )

        # 更新方向历史
        self._dir_history.append(direction)
        if len(self._dir_history) > self._history_max_len:
            self._dir_history.pop(0)

        # 持续性
        persistence = compute_trend_persistence(
            self._dir_history,
            window=self._persistence_win,
        )

        # 持续 bar 数
        bars_in_trend = self._count_bars_in_trend(direction)

        new_state = TrendState(
            direction      = direction,
            strength       = strength,
            persistence    = persistence,
            adx            = adx,
            slope          = slope,
            r_squared      = r_squared,
            bars_in_trend  = bars_in_trend,
            updated_at     = datetime.now(),
        )
        self._state = new_state

        self._log(
            f"[TrendEngine] bar={self._bar_count}"
            f"  dir={direction.value:12s}"
            f"  strength={strength:.3f}"
            f"  r2={r_squared:.3f}"
            f"  adx={adx:.1f}"
        )

        return new_state

    # ------------------------------------------------------------------ #
    #  辅助：持续 bar 数
    # ------------------------------------------------------------------ #

    def _count_bars_in_trend(self, current: TrendDirection) -> int:
        """从历史末尾向前数连续同类方向的 bar 数。"""
        up_set   = {TrendDirection.STRONG_UP,   TrendDirection.WEAK_UP}
        down_set = {TrendDirection.STRONG_DOWN, TrendDirection.WEAK_DOWN}

        if current in up_set:
            same_group = up_set
        elif current in down_set:
            same_group = down_set
        else:
            return 1

        count = 0
        for d in reversed(self._dir_history):
            if d in same_group:
                count += 1
            else:
                break
        return max(1, count)

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_state(self) -> TrendState:
        return self._state

    def get_direction_history(self, limit: int = 50) -> list[str]:
        return [d.value for d in self._dir_history[-limit:]]

    def get_trend_score(self) -> float:
        """返回供 RegimeEngine 使用的趋势强度评分 [0, 1]。"""
        return self._state.strength

    def get_trend_sign(self) -> float:
        """
        返回趋势方向符号供 RegimeEngine 使用。
        +1=上涨 / -1=下跌 / 0=横盘
        """
        d = self._state.direction
        if d in (TrendDirection.STRONG_UP, TrendDirection.WEAK_UP):
            return 1.0
        if d in (TrendDirection.STRONG_DOWN, TrendDirection.WEAK_DOWN):
            return -1.0
        return 0.0

    def summary(self) -> dict:
        return {
            "trend_direction": self._state.direction.value,
            "strength":        round(self._state.strength,     4),
            "persistence":     round(self._state.persistence,  4),
            "adx":             round(self._state.adx,          2),
            "r_squared":       round(self._state.r_squared,    4),
            "bars_in_trend":   self._state.bars_in_trend,
            "phase":           3,
        }

    # ------------------------------------------------------------------ #
    #  参数更新
    # ------------------------------------------------------------------ #

    def update_params(
        self,
        window:           int   | None = None,
        strong_threshold: float | None = None,
        weak_threshold:   float | None = None,
        persistence_window: int | None = None,
    ) -> None:
        if window             is not None: self._window           = window
        if strong_threshold   is not None: self._strong_thr       = strong_threshold
        if weak_threshold     is not None: self._weak_thr         = weak_threshold
        if persistence_window is not None: self._persistence_win  = persistence_window
