"""
research_validation/engine/stability_engine.py

StabilityEngine — 因子稳定性分析引擎（Phase 4 实现）。

职责：
  - Rolling IC / RankIC 时间序列计算
  - IC 衰减分析（lag=1..max_lag）
  - IC 稳定性评级（STRONG / MODERATE / WEAK / UNSTABLE）
  - Rolling Sharpe 稳定性
  - 因子自相关检测

❌ 不允许机器学习 / 预测模型。
❌ 不允许连接任何交易接口。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..utils.stats_utils import (
    calc_ic, calc_rank_ic, calc_sharpe,
    calc_ir, calc_t_stat, summarize_ic_series,
    _mean, _std,
)
from ..utils.correlation_utils import (
    calc_rolling_ic,
    calc_ic_decay,
    calc_ic_decay_halflife,
    calc_autocorr_series,
    classify_ic_stability,
)
from ..constant import StabilityLevel


# ─────────────────────────────────────────────────────────────────────────────
#  数据结构
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StabilitySummary:
    """因子稳定性分析完整汇总。"""

    # 全期 IC 统计
    overall_ic_mean:   float = 0.0
    overall_ic_std:    float = 0.0
    overall_ic_ir:     float = 0.0
    overall_ic_t_stat: float = 0.0
    overall_win_rate:  float = 0.0

    # Rolling IC 序列
    rolling_ic:      list[float] = field(default_factory=list)
    rolling_ic_mean: float       = 0.0   # rolling IC 的均值（去除 NaN）
    rolling_ic_std:  float       = 0.0   # rolling IC 的标准差

    # Rolling Sharpe（Top-decile 多空）
    rolling_sharpe:  list[float] = field(default_factory=list)

    # IC 衰减
    ic_decay:            list[float] = field(default_factory=list)   # lag=1..max_lag
    ic_decay_halflife:   float       = 0.0   # 半衰期（期数）

    # 自相关（检测因子持续性 / 过度平滑）
    autocorr_series:     list[float] = field(default_factory=list)   # lag=1..10
    lag1_autocorr:       float       = 0.0

    # 稳定性评级
    stability_level:     str         = "UNSTABLE"   # STRONG/MODERATE/WEAK/UNSTABLE
    stability_score:     float       = 0.0          # 0~100

    # 窗口参数
    rolling_window:      int         = 60
    decay_max_lag:       int         = 20

    @property
    def stability_level_enum(self) -> StabilityLevel:
        mapping = {
            "STRONG":   StabilityLevel.STRONG,
            "MODERATE": StabilityLevel.MODERATE,
            "WEAK":     StabilityLevel.WEAK,
        }
        return mapping.get(self.stability_level, StabilityLevel.INVALID)

    @property
    def valid_rolling_ic(self) -> list[float]:
        return [x for x in self.rolling_ic if not math.isnan(x)]

    def to_text(self) -> str:
        lines = [
            "  因子稳定性分析报告",
            "  " + "─" * 55,
            f"  稳定性评级  : {self.stability_level}  (评分 {self.stability_score:.1f}/100)",
            f"  全期 IC     : mean={self.overall_ic_mean:+.4f}  IR={self.overall_ic_ir:.3f}"
            f"  t={self.overall_ic_t_stat:.2f}  win={self.overall_win_rate:.1%}",
            f"  Rolling IC  : mean={self.rolling_ic_mean:+.4f}  std={self.rolling_ic_std:.4f}",
            f"  IC 半衰期   : {self.ic_decay_halflife:.1f} 期",
            f"  Lag-1 自相关: {self.lag1_autocorr:+.3f}",
            "  " + "─" * 55,
        ]
        # 衰减曲线简要
        if self.ic_decay:
            decay_str = "  IC 衰减(lag1-10): "
            decay_str += "  ".join(
                f"{v:+.3f}" for v in self.ic_decay[:10]
            )
            lines.append(decay_str)
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
#  StabilityEngine
# ─────────────────────────────────────────────────────────────────────────────

class StabilityEngine:
    """
    因子稳定性分析引擎（Phase 4 实现）。

    使用方式：
        engine = StabilityEngine()
        engine.set_window(60)
        summary = engine.run(factor_cs, return_cs, dates)
    """

    def __init__(self) -> None:
        self.rolling_window: int  = 60
        self.decay_max_lag:  int  = 20
        self.use_rank_ic:    bool = False
        self._summary: StabilitySummary | None = None

    def set_window(self, window: int) -> None:
        if window < 5:
            raise ValueError("rolling_window 至少 5 期。")
        self.rolling_window = window

    def set_decay_lag(self, max_lag: int) -> None:
        if max_lag < 1:
            raise ValueError("decay_max_lag 至少 1。")
        self.decay_max_lag = max_lag

    # ------------------------------------------------------------------ #
    #  主计算入口
    # ------------------------------------------------------------------ #

    def run(
        self,
        factor_cs: list[dict[str, float]],
        return_cs: list[dict[str, float]],
        dates:     list,
    ) -> StabilitySummary:
        """
        执行因子稳定性分析。

        Parameters
        ----------
        factor_cs : 因子截面序列（按时间升序）
        return_cs : 收益截面序列（同长度）
        dates     : 对应日期序列

        Returns
        -------
        StabilitySummary
        """
        n = len(dates)
        if n != len(factor_cs) or n != len(return_cs):
            raise ValueError("factor_cs / return_cs / dates 长度必须一致。")
        if n < self.rolling_window + 1:
            raise ValueError(
                f"数据长度 {n} 不足（最少需要 rolling_window+1="
                f"{self.rolling_window+1} 期）。"
            )

        ic_fn = calc_rank_ic if self.use_rank_ic else calc_ic

        # 1. 全期点 IC 序列
        spot_ics = [ic_fn(factor_cs[i], return_cs[i]) for i in range(n)]
        overall_stats = summarize_ic_series(spot_ics)

        # 2. Rolling IC
        rolling_ic = calc_rolling_ic(
            factor_cs, return_cs,
            window   = self.rolling_window,
            use_rank = self.use_rank_ic,
        )
        valid_ric = [x for x in rolling_ic if not math.isnan(x)]
        ric_mean = _mean(valid_ric) if valid_ric else 0.0
        ric_std  = _std(valid_ric, ddof=1) if len(valid_ric) > 1 else 0.0

        # 3. Rolling Sharpe（Top-decile 多空）
        rolling_sharpe = self._calc_rolling_sharpe(
            factor_cs, return_cs, self.rolling_window
        )

        # 4. IC 衰减
        ic_decay = calc_ic_decay(
            factor_cs, return_cs,
            max_lag  = self.decay_max_lag,
            use_rank = self.use_rank_ic,
        )
        halflife = calc_ic_decay_halflife(ic_decay)

        # 5. 自相关（检测因子 IC 是否具有持续性）
        autocorr = calc_autocorr_series(spot_ics, max_lag=10)
        lag1_ac  = autocorr[0] if autocorr else 0.0

        # 6. 稳定性评级
        level = classify_ic_stability(rolling_ic)
        score = self._calc_stability_score(
            overall_stats, ric_mean, ric_std, halflife, lag1_ac
        )

        self._summary = StabilitySummary(
            overall_ic_mean   = overall_stats["mean"],
            overall_ic_std    = overall_stats["std"],
            overall_ic_ir     = overall_stats["ir"],
            overall_ic_t_stat = overall_stats["t_stat"],
            overall_win_rate  = overall_stats["win_rate"],
            rolling_ic        = rolling_ic,
            rolling_ic_mean   = ric_mean,
            rolling_ic_std    = ric_std,
            rolling_sharpe    = rolling_sharpe,
            ic_decay          = ic_decay,
            ic_decay_halflife  = halflife,
            autocorr_series   = autocorr,
            lag1_autocorr     = lag1_ac,
            stability_level   = level,
            stability_score   = score,
            rolling_window    = self.rolling_window,
            decay_max_lag     = self.decay_max_lag,
        )
        return self._summary

    def get_summary(self) -> StabilitySummary | None:
        return self._summary

    def reset(self) -> None:
        self._summary = None

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _calc_rolling_sharpe(
        factor_cs: list[dict[str, float]],
        return_cs: list[dict[str, float]],
        window:    int,
    ) -> list[float]:
        """
        计算滚动窗口 Top-decile 多空组合 Sharpe。
        前 window-1 期返回 NaN。
        """
        n       = len(factor_cs)
        periods = []

        for i in range(n):
            fc, rc = factor_cs[i], return_cs[i]
            common = [s for s in fc if s in rc]
            if len(common) < 10:
                periods.append(0.0)
                continue
            sorted_s = sorted(common, key=lambda s: fc[s], reverse=True)
            n10      = max(1, len(sorted_s) // 10)
            long_r   = sum(rc[s] for s in sorted_s[:n10])  / n10
            short_r  = sum(rc[s] for s in sorted_s[-n10:]) / n10
            periods.append(long_r - short_r)

        result = [float('nan')] * n
        for i in range(window - 1, n):
            w_rets = periods[i - window + 1 : i + 1]
            result[i] = calc_sharpe(w_rets)
        return result

    @staticmethod
    def _calc_stability_score(
        overall_stats: dict,
        ric_mean:      float,
        ric_std:       float,
        halflife:      float,
        lag1_ac:       float,
    ) -> float:
        """
        计算稳定性综合评分（0~100）。

        维度：
          全期 IC IR        0~30 分
          Rolling IC 正向比 0~25 分
          IC 半衰期         0~25 分（越长越好）
          自相关惩罚        0~20 分（自相关过高 → 因子过度平滑）
        """
        score = 0.0

        # IR 贡献（0~30）
        ir = overall_stats.get("ir", 0.0)
        if ir > 0:
            score += min(30.0, ir * 20.0)

        # Rolling IC 正向比（0~25）
        win_rate = overall_stats.get("win_rate", 0.0)
        if win_rate > 0.6:
            score += 25.0
        elif win_rate > 0.5:
            score += (win_rate - 0.5) / 0.1 * 25.0

        # IC 半衰期（0~25）：半衰期 >= 5 期满分
        if halflife >= 5.0:
            score += 25.0
        elif halflife > 1.0:
            score += (halflife - 1.0) / 4.0 * 25.0

        # 自相关惩罚（-20~0）：
        # |lag1_ac| > 0.5 表示因子过度平滑，可能包含前视偏差
        ac_penalty = max(0.0, (abs(lag1_ac) - 0.3)) / 0.7 * 20.0
        score -= ac_penalty

        return round(min(100.0, max(0.0, score)), 1)
