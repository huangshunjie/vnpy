"""
market_regime_ai/engine/liquidity_engine.py  (Phase 3)

LiquidityEngine — 流动性分析引擎（完整实现）。

实现：
  - 接收价格序列 + 成交量序列
  - 计算成交量比率、换手率、价差代理、Amihud 非流动性
  - 输出 LiquidityState
  - 支持仅有收盘价时的降级计算

❌ 无 IO / 无网络 / 纯计算
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..constant import LiquidityLevel
from ..model.liquidity_model import LiquidityState
from ..utils.liquidity_utils import (
    compute_volume_ratio,
    compute_avg_volume,
    compute_volume_percentile,
    compute_turnover_ratio,
    compute_spread_proxy,
    compute_spread_proxy_from_returns,
    compute_illiquidity_score,
    compute_amihud_illiquidity,
    classify_liquidity_level,
)
from ..utils.volatility_utils import compute_returns


class LiquidityEngine:
    """
    流动性分析引擎（Phase 3 完整实现）。

    用法（有成交量）：
        state = engine.analyze(prices, volumes, highs, lows)

    用法（仅有收盘价）：
        state = engine.analyze(prices)
    """

    def __init__(
        self,
        log_fn:          Callable | None = None,
        vol_window:      int   = 20,
        very_low_thr:    float = 0.75,
        low_thr:         float = 0.55,
        high_thr:        float = 0.30,
        history_max_len: int   = 500,
    ) -> None:
        self._log             = log_fn or (lambda m: None)
        self._vol_window      = vol_window
        self._very_low_thr    = very_low_thr
        self._low_thr         = low_thr
        self._high_thr        = high_thr
        self._history_max_len = history_max_len

        self._state              = LiquidityState()
        self._volume_history:    list[float] = []
        self._bar_count          = 0

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def analyze(
        self,
        prices:  list[float],
        volumes: list[float] | None = None,
        highs:   list[float] | None = None,
        lows:    list[float] | None = None,
    ) -> LiquidityState:
        """
        计算流动性状态。

        Parameters
        ----------
        prices  : 收盘价序列（必须）
        volumes : 成交量序列（可选，有则精度更高）
        highs   : 最高价序列（可选，用于价差代理）
        lows    : 最低价序列（可选，用于价差代理）

        Returns
        -------
        LiquidityState
        """
        self._bar_count += 1

        if len(prices) < 3:
            self._log(f"[LiquidityEngine] insufficient data ({len(prices)} bars)")
            return self._state

        returns = compute_returns(prices)

        has_volume = (
            volumes is not None
            and len(volumes) >= 2
        )
        has_hl = (
            highs is not None and lows is not None
            and len(highs) == len(prices)
            and len(lows)  == len(prices)
        )

        # ── 成交量相关 ────────────────────────────────────────────────
        if has_volume:
            cur_vol  = float(volumes[-1])
            avg_vol  = compute_avg_volume(volumes, window=self._vol_window)
            vol_ratio = compute_volume_ratio(cur_vol, avg_vol)

            self._volume_history.extend(volumes[-5:])
            if len(self._volume_history) > self._history_max_len:
                self._volume_history = self._volume_history[-self._history_max_len:]

            vol_pct = compute_volume_percentile(
                cur_vol, self._volume_history[:-1]
                if len(self._volume_history) > 1 else [])

            avg_price = sum(prices[-self._vol_window:]) / min(
                len(prices), self._vol_window)
            turnover_ratio = compute_turnover_ratio(
                cur_vol, avg_vol, prices[-1], avg_price)
        else:
            vol_ratio      = 1.0
            vol_pct        = 0.5
            turnover_ratio = 1.0

        # ── 价差代理 ──────────────────────────────────────────────────
        if has_hl:
            spread = compute_spread_proxy(
                highs[-1], lows[-1], prices[-1])
        elif returns:
            spread = compute_spread_proxy_from_returns(
                returns, window=self._vol_window)
        else:
            spread = 0.0

        # ── Amihud 非流动性 ───────────────────────────────────────────
        if has_volume and len(volumes) >= 2:
            amihud = compute_amihud_illiquidity(
                returns, volumes, window=self._vol_window)
        else:
            amihud = 0.5    # 无成交量时中性填充

        # ── 综合评分 ──────────────────────────────────────────────────
        ill_score = compute_illiquidity_score(
            volume_ratio   = vol_ratio,
            spread_proxy   = spread,
            turnover_ratio = turnover_ratio,
        )

        # ── 流动性水平分类 ────────────────────────────────────────────
        level = classify_liquidity_level(
            illiquidity_score = ill_score,
            vol_percentile    = vol_pct,
            very_low_thr      = self._very_low_thr,
            low_thr           = self._low_thr,
            high_thr          = self._high_thr,
        )

        new_state = LiquidityState(
            level             = level,
            volume_ratio      = vol_ratio,
            turnover_ratio    = turnover_ratio,
            spread_proxy      = spread,
            vol_percentile    = vol_pct,
            illiquidity_score = ill_score,
            updated_at        = datetime.now(),
        )
        new_state.meta = {
            "bar_count": self._bar_count,
            "amihud":    round(amihud, 6),
            "has_volume": has_volume,
        }
        self._state = new_state

        self._log(
            f"[LiquidityEngine] bar={self._bar_count}"
            f"  level={level.value:9s}"
            f"  ill={ill_score:.3f}"
            f"  vol_ratio={vol_ratio:.2f}"
            f"  spread={spread:.5f}"
        )

        return new_state

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_state(self) -> LiquidityState:
        return self._state

    def get_liq_score(self) -> float:
        """返回供 RegimeEngine 使用的流动性评分 [0, 1]（高 = 流动性好）。"""
        return round(1.0 - self._state.illiquidity_score, 6)

    def get_vol_percentile(self) -> float:
        return self._state.vol_percentile

    def summary(self) -> dict:
        return {
            "liquidity_level":   self._state.level.value,
            "illiquidity_score": round(self._state.illiquidity_score, 4),
            "volume_ratio":      round(self._state.volume_ratio,      4),
            "spread_proxy":      round(self._state.spread_proxy,      6),
            "vol_percentile":    round(self._state.vol_percentile,    4),
            "phase":             3,
        }

    # ------------------------------------------------------------------ #
    #  参数更新
    # ------------------------------------------------------------------ #

    def update_params(
        self,
        vol_window:   int   | None = None,
        very_low_thr: float | None = None,
        low_thr:      float | None = None,
    ) -> None:
        if vol_window   is not None: self._vol_window   = vol_window
        if very_low_thr is not None: self._very_low_thr = very_low_thr
        if low_thr      is not None: self._low_thr      = low_thr
