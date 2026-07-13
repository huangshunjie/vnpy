"""
market_regime_ai/engine/volatility_engine.py  (Phase 3)

VolatilityEngine — 波动率分析引擎（完整实现）。

实现：
  - 接收价格序列（close prices）
  - 计算 rolling vol (20/60)、realized vol、分位数、vol ratio
  - 输出 VolatilityState（含 regime + 切换检测）
  - 维护波动率历史序列

❌ 无 IO / 无网络 / 纯计算
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..constant import VolatilityRegime
from ..model.volatility_model import VolatilityState
from ..utils.volatility_utils import (
    compute_returns,
    compute_rolling_vol,
    compute_realized_vol,
    compute_vol_percentile,
    compute_vol_ratio,
    classify_vol_regime,
    detect_vol_regime_shift,
    detect_vol_spike,
    compute_avg_vol,
)


class VolatilityEngine:
    """
    波动率分析引擎（Phase 3 完整实现）。

    用法：
        engine = VolatilityEngine(log_fn=print)
        state  = engine.analyze(prices)
    """

    def __init__(
        self,
        log_fn:            Callable | None = None,
        short_window:      int   = 20,
        long_window:       int   = 60,
        annualize_factor:  float = 252.0,
        extreme_thr:       float = 0.90,
        high_thr:          float = 0.65,
        low_thr:           float = 0.20,
        spike_mult:        float = 2.0,
        history_max_len:   int   = 500,
    ) -> None:
        self._log             = log_fn or (lambda m: None)
        self._short_window    = short_window
        self._long_window     = long_window
        self._annualize       = annualize_factor
        self._extreme_thr     = extreme_thr
        self._high_thr        = high_thr
        self._low_thr         = low_thr
        self._spike_mult      = spike_mult
        self._history_max_len = history_max_len

        self._state         = VolatilityState()
        self._vol_history:  list[float] = []
        self._bar_count     = 0

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def analyze(self, prices: list[float]) -> VolatilityState:
        """
        计算波动率状态。

        Parameters
        ----------
        prices : 收盘价序列（至少需要 short_window + 2 个值）

        Returns
        -------
        VolatilityState
        """
        self._bar_count += 1

        if len(prices) < 4:
            self._log(f"[VolatilityEngine] insufficient data ({len(prices)} bars)")
            return self._state

        returns = compute_returns(prices)

        # Rolling vol（短期 / 长期）
        vol_20 = compute_rolling_vol(
            returns, window=self._short_window,
            annualize_factor=self._annualize)
        vol_60 = compute_rolling_vol(
            returns, window=self._long_window,
            annualize_factor=self._annualize)

        # 已实现波动率（全样本）
        realized_vol = compute_realized_vol(
            returns, annualize_factor=self._annualize)

        # 更新历史
        if vol_20 > 0:
            self._vol_history.append(vol_20)
            if len(self._vol_history) > self._history_max_len:
                self._vol_history.pop(0)

        # 历史分位数
        percentile = compute_vol_percentile(
            vol_20, self._vol_history[:-1]   # 排除当前值
            if len(self._vol_history) > 1 else []
        )

        # 短/长期比值
        vol_ratio = compute_vol_ratio(vol_20, vol_60)

        # 状态分类
        regime = classify_vol_regime(
            vol_20, percentile,
            extreme_thr = self._extreme_thr,
            high_thr    = self._high_thr,
            low_thr     = self._low_thr,
        )

        # 切换检测
        prev_regime    = self._state.regime
        regime_shifted = detect_vol_regime_shift(prev_regime, regime)

        # Spike 检测
        avg_v = compute_avg_vol(self._vol_history, window=self._long_window)
        spike = detect_vol_spike(vol_20, avg_v, self._spike_mult)

        new_state = VolatilityState(
            regime          = regime,
            realized_vol    = realized_vol,
            rolling_vol_20  = vol_20,
            rolling_vol_60  = vol_60,
            vol_percentile  = percentile,
            vol_ratio       = vol_ratio,
            regime_shifted  = regime_shifted,
            updated_at      = datetime.now(),
        )
        new_state.meta = {
            "bar_count": self._bar_count,
            "spike":     spike,
            "avg_vol":   round(avg_v, 6),
        }
        self._state = new_state

        self._log(
            f"[VolatilityEngine] bar={self._bar_count}"
            f"  vol20={vol_20:.4f}  pct={percentile:.3f}"
            f"  regime={regime.value}  shifted={regime_shifted}"
        )

        return new_state

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_state(self) -> VolatilityState:
        return self._state

    def get_vol_history(self, limit: int = 60) -> list[float]:
        return self._vol_history[-limit:]

    def get_vol_score(self) -> float:
        """返回供 RegimeEngine 使用的标准化波动率评分 [0, 1]。"""
        return self._state.vol_percentile

    def summary(self) -> dict:
        return {
            "vol_regime":    self._state.regime.value,
            "vol_20":        round(self._state.rolling_vol_20, 4),
            "vol_60":        round(self._state.rolling_vol_60, 4),
            "vol_percentile": round(self._state.vol_percentile, 4),
            "vol_ratio":     round(self._state.vol_ratio, 4),
            "phase":         3,
        }

    # ------------------------------------------------------------------ #
    #  参数更新
    # ------------------------------------------------------------------ #

    def update_params(
        self,
        short_window:   int   | None = None,
        long_window:    int   | None = None,
        extreme_thr:    float | None = None,
        high_thr:       float | None = None,
        low_thr:        float | None = None,
    ) -> None:
        if short_window is not None: self._short_window = short_window
        if long_window  is not None: self._long_window  = long_window
        if extreme_thr  is not None: self._extreme_thr  = extreme_thr
        if high_thr     is not None: self._high_thr     = high_thr
        if low_thr      is not None: self._low_thr      = low_thr
