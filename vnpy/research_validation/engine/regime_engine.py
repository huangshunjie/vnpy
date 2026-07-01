"""
research_validation/engine/regime_engine.py

RegimeEngine — 市场状态识别引擎（Phase 3 实现）。

市场状态识别算法：
  基于收益率序列的滚动均值和波动率，用简单阈值规则分类：
    Bull     : 滚动均值 >  +threshold
    Bear     : 滚动均值 <  -threshold
    Sideways : 介于中间

按市场状态分组计算因子 IC，输出各状态下的 IC 均值 / IR / t-stat。

❌ 不允许机器学习 / 隐马尔可夫模型 / 任何预测模型。
❌ 不允许连接任何交易接口。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

from ..constant import RegimeType
from ..utils.stats_utils import calc_ic, calc_rank_ic, calc_ir, calc_t_stat, summarize_ic_series


# ─────────────────────────────────────────────────────────────────────────────
#  数据结构
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RegimeLabel:
    """单期市场状态标注。"""
    date:        object          # datetime / date
    regime:      RegimeType      = RegimeType.UNKNOWN
    rolling_ret: float           = 0.0   # 滚动均值
    rolling_vol: float           = 0.0   # 滚动波动率


@dataclass
class RegimeICResult:
    """单个市场状态下的 IC 统计。"""
    regime:       RegimeType     = RegimeType.UNKNOWN
    ic_mean:      float          = 0.0
    ic_std:       float          = 0.0
    ic_ir:        float          = 0.0
    ic_t_stat:    float          = 0.0
    win_rate:     float          = 0.0
    sample_count: int            = 0
    ic_series:    list[float]    = field(default_factory=list)

    @property
    def is_significant(self) -> bool:
        """|t| > 1.96 视为 5% 显著。"""
        return abs(self.ic_t_stat) > 1.96

    @property
    def label(self) -> str:
        return self.regime.value.upper()

    @property
    def summary(self) -> str:
        sig = "*" if self.is_significant else " "
        return (
            f"  [{self.label:8s}]{sig} "
            f"IC={self.ic_mean:+.4f}  IR={self.ic_ir:.3f}"
            f"  t={self.ic_t_stat:.2f}  win={self.win_rate:.1%}"
            f"  n={self.sample_count}"
        )


@dataclass
class RegimeSummary:
    """跨市场状态的 IC 对比汇总。"""
    bull_result:     RegimeICResult | None = None
    bear_result:     RegimeICResult | None = None
    sideways_result: RegimeICResult | None = None
    regime_labels:   list[RegimeLabel]     = field(default_factory=list)

    # 市场状态分布
    bull_pct:     float = 0.0
    bear_pct:     float = 0.0
    sideways_pct: float = 0.0

    @property
    def best_regime(self) -> RegimeICResult | None:
        """IC 最高的市场状态。"""
        candidates = [r for r in [self.bull_result, self.bear_result, self.sideways_result]
                      if r is not None and r.sample_count > 0]
        return max(candidates, key=lambda r: r.ic_mean) if candidates else None

    @property
    def worst_regime(self) -> RegimeICResult | None:
        """IC 最低的市场状态。"""
        candidates = [r for r in [self.bull_result, self.bear_result, self.sideways_result]
                      if r is not None and r.sample_count > 0]
        return min(candidates, key=lambda r: r.ic_mean) if candidates else None

    @property
    def all_results(self) -> list[RegimeICResult]:
        return [r for r in [self.bull_result, self.bear_result, self.sideways_result]
                if r is not None]

    def to_text(self) -> str:
        lines = ["  市场状态因子 IC 对比", "  " + "─" * 55]
        lines.append(
            f"  状态分布：Bull={self.bull_pct:.1%}  "
            f"Bear={self.bear_pct:.1%}  "
            f"Sideways={self.sideways_pct:.1%}"
        )
        lines.append("  " + "─" * 55)
        for r in self.all_results:
            lines.append(r.summary)
        best = self.best_regime
        if best:
            lines.append(f"  最佳状态：{best.label}  IC={best.ic_mean:+.4f}")
        lines.append("  " + "─" * 55)
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
#  RegimeEngine 主体
# ─────────────────────────────────────────────────────────────────────────────

class RegimeEngine:
    """
    市场状态识别引擎（Phase 3 实现）。

    使用方式：
        engine = RegimeEngine()
        engine.set_lookback(60)
        engine.set_threshold(0.001)
        summary = engine.run(factor_cs, market_rets, dates)
    """

    def __init__(self) -> None:
        self.lookback:   int   = 60      # 滚动窗口期数
        self.threshold:  float = 0.0005  # Bull/Bear 判断阈值（每期收益率）
        self.use_rank_ic: bool = False
        self._summary: RegimeSummary | None = None

    def set_lookback(self, periods: int) -> None:
        if periods < 5:
            raise ValueError("lookback 至少 5 期。")
        self.lookback = periods

    def set_threshold(self, threshold: float) -> None:
        """
        Bull / Bear 判断阈值（每期均值收益率）。
        滚动均值 > +threshold → Bull
        滚动均值 < -threshold → Bear
        介于中间               → Sideways
        """
        self.threshold = abs(threshold)

    # ------------------------------------------------------------------ #
    #  主计算入口
    # ------------------------------------------------------------------ #

    def run(
        self,
        factor_cs:   list[dict[str, float]],
        market_rets: list[float],
        dates:       list,
        *,
        return_cs:   list | None = None,
        use_rank_ic: bool = False,
    ) -> RegimeSummary:
        """
        执行市场状态识别 + 因子分状态 IC 分析。

        Parameters
        ----------
        factor_cs   : 因子截面序列 [{symbol: value}, ...]
        market_rets : 市场整体收益率序列（与 factor_cs 等长，代表市场日度收益）
        dates       : 对应日期序列

        Returns
        -------
        RegimeSummary
        """
        n = len(dates)
        if n != len(factor_cs) or n != len(market_rets):
            raise ValueError("factor_cs / market_rets / dates 长度必须一致。")
        if n < self.lookback + 1:
            raise ValueError(
                f"数据长度 {n} 不足（最少需要 lookback+1={self.lookback+1} 期）。"
            )

        if return_cs is not None and len(return_cs) != n:
            raise ValueError("return_cs 长度必须与 dates 一致。")

        self.use_rank_ic = use_rank_ic

        # 1. 识别每期市场状态（基于标量 market_rets）
        labels = self._detect_regimes(market_rets, dates)

        # 2. 确定用于 IC 计算的收益截面
        #    优先使用传入的 return_cs（个股截面）；
        #    否则退化为市场收益复制给所有 symbol。
        if return_cs is not None:
            ic_return_cs = return_cs
        else:
            ic_return_cs = self._build_forward_returns(factor_cs, market_rets)

        # 3. 按市场状态分组计算 IC
        grouped = self._group_by_regime(factor_cs, ic_return_cs, labels)

        # 4. 计算各状态统计
        ic_fn = calc_rank_ic if self.use_rank_ic else calc_ic

        def _compute(regime: RegimeType) -> RegimeICResult:
            periods = grouped.get(regime, [])
            if not periods:
                return RegimeICResult(regime=regime, sample_count=0)
            ics = [ic_fn(f, r) for f, r in periods]
            stats = summarize_ic_series(ics)
            return RegimeICResult(
                regime       = regime,
                ic_mean      = stats["mean"],
                ic_std       = stats["std"],
                ic_ir        = stats["ir"],
                ic_t_stat    = stats["t_stat"],
                win_rate     = stats["win_rate"],
                sample_count = stats["count"],
                ic_series    = ics,
            )

        total = max(len(labels), 1)
        bull_n     = sum(1 for l in labels if l.regime == RegimeType.BULL)
        bear_n     = sum(1 for l in labels if l.regime == RegimeType.BEAR)
        sideways_n = sum(1 for l in labels if l.regime == RegimeType.SIDEWAYS)

        self._summary = RegimeSummary(
            bull_result     = _compute(RegimeType.BULL),
            bear_result     = _compute(RegimeType.BEAR),
            sideways_result = _compute(RegimeType.SIDEWAYS),
            regime_labels   = labels,
            bull_pct        = bull_n     / total,
            bear_pct        = bear_n     / total,
            sideways_pct    = sideways_n / total,
        )
        return self._summary

    def get_summary(self) -> RegimeSummary | None:
        return self._summary

    def reset(self) -> None:
        self._summary = None

    # ------------------------------------------------------------------ #
    #  市场状态识别（纯规则，无预测模型）
    # ------------------------------------------------------------------ #

    def _detect_regimes(
        self,
        market_rets: list[float],
        dates:       list,
    ) -> list[RegimeLabel]:
        """
        基于滚动均值阈值规则识别市场状态。

        前 lookback 期因窗口未满，标注为 UNKNOWN。
        """
        n      = len(market_rets)
        labels = []

        for i in range(n):
            if i < self.lookback:
                labels.append(RegimeLabel(
                    date        = dates[i],
                    regime      = RegimeType.UNKNOWN,
                    rolling_ret = 0.0,
                    rolling_vol = 0.0,
                ))
                continue

            window = market_rets[i - self.lookback : i]
            roll_mean = sum(window) / self.lookback
            mean_sq   = sum(x * x for x in window) / self.lookback
            roll_std  = math.sqrt(max(0.0, mean_sq - roll_mean ** 2))

            if roll_mean > self.threshold:
                regime = RegimeType.BULL
            elif roll_mean < -self.threshold:
                regime = RegimeType.BEAR
            else:
                regime = RegimeType.SIDEWAYS

            labels.append(RegimeLabel(
                date        = dates[i],
                regime      = regime,
                rolling_ret = roll_mean,
                rolling_vol = roll_std,
            ))

        return labels

    # ------------------------------------------------------------------ #
    #  构建 forward returns（因子→收益对齐）
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_forward_returns(
        factor_cs:   list[dict[str, float]],
        market_rets: list[float],
    ) -> list[dict[str, float]]:
        """
        每期 forward return = 市场收益 × symbol 权重（等权近似）。

        说明：在没有个股收益时，用市场整体收益对所有 symbol 赋相同值，
        这样 IC 退化为因子均值与市场收益的相关性（符合截面验证逻辑）。
        调用方若有个股收益，应直接传入 return_cs 而非此方法。
        """
        n = len(factor_cs)
        fwd = []
        for i in range(n):
            # 使用当期市场收益作为所有 symbol 的代理收益
            r = market_rets[i]
            fwd.append({sym: r for sym in factor_cs[i]})
        return fwd

    # ------------------------------------------------------------------ #
    #  按市场状态分组
    # ------------------------------------------------------------------ #

    @staticmethod
    def _group_by_regime(
        factor_cs: list[dict[str, float]],
        fwd_rets:  list[dict[str, float]],
        labels:    list[RegimeLabel],
    ) -> dict[RegimeType, list[tuple]]:
        """
        将 (factor_cross_section, return_cross_section) 按市场状态分组。

        Returns
        -------
        {RegimeType: [(factor_cs_t, return_cs_t), ...]}
        """
        grouped: dict[RegimeType, list[tuple]] = {
            RegimeType.BULL:     [],
            RegimeType.BEAR:     [],
            RegimeType.SIDEWAYS: [],
        }
        for i, label in enumerate(labels):
            if label.regime in grouped:
                grouped[label.regime].append((factor_cs[i], fwd_rets[i]))
        return grouped

    # ------------------------------------------------------------------ #
    #  便捷方法：仅做市场状态识别（不计算 IC）
    # ------------------------------------------------------------------ #

    def detect(
        self,
        market_rets: list[float],
        dates:       list,
    ) -> list[RegimeLabel]:
        """
        仅识别市场状态，不分析因子。
        供 RegimeTab 独立展示状态时间轴使用。
        """
        return self._detect_regimes(market_rets, dates)

    # ------------------------------------------------------------------ #
    #  工具：从因子截面估算市场收益（无行情数据时的代理）
    # ------------------------------------------------------------------ #

    @staticmethod
    def estimate_market_return_from_cs(
        return_cs: list[dict[str, float]],
    ) -> list[float]:
        """
        从收益截面估算每期等权市场收益（所有 symbol 均值）。
        当没有独立市场指数数据时使用。
        """
        result = []
        for rc in return_cs:
            vals = list(rc.values())
            result.append(sum(vals) / len(vals) if vals else 0.0)
        return result
