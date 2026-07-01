"""
research_validation/engine/oos_engine.py

OOSEngine — Out-of-Sample Testing 引擎（Phase 2 实现）。

职责：
  - 严格时间切分（防止未来函数）
  - 样本内 / 样本外 IC / Sharpe 对比
  - 过拟合比率计算
  - validate_no_lookahead 时间戳验证

❌ 不允许优化策略 / 预测模型 / 机器学习。
"""

from __future__ import annotations

from datetime import datetime

from ..utils.stats_utils import (
    calc_ic, calc_rank_ic, calc_sharpe,
    calc_ir, calc_t_stat, summarize_ic_series,
)
from ..utils.time_split_utils import split_train_test, validate_no_lookahead
from ..model.result_model import OOSResult


class OOSEngine:
    """
    Out-of-Sample Testing 引擎（Phase 2 实现）。

    使用方式：
        engine = OOSEngine()
        engine.set_split(oos_ratio=0.3)
        result = engine.run(factor_cs, return_cs, dates)
    """

    def __init__(self) -> None:
        self.oos_ratio:   float = 0.3
        self.use_rank_ic: bool  = False
        self._result:     OOSResult | None = None

    def set_split(self, oos_ratio: float) -> None:
        if not (0.0 < oos_ratio < 1.0):
            raise ValueError(f"oos_ratio 须在 (0,1) 内，当前：{oos_ratio}")
        self.oos_ratio = oos_ratio

    # ------------------------------------------------------------------ #
    #  主计算入口
    # ------------------------------------------------------------------ #

    def run(
        self,
        factor_cs: list[dict[str, float]],
        return_cs: list[dict[str, float]],
        dates:     list[datetime],
    ) -> OOSResult:
        """
        执行 Out-of-Sample 验证。

        Parameters
        ----------
        factor_cs : 按时间升序因子截面序列
        return_cs : 对应持有期收益截面序列
        dates     : 对应日期序列

        Returns
        -------
        OOSResult  包含 IS/OOS 指标对比及过拟合评估
        """
        n = len(dates)
        if n != len(factor_cs) or n != len(return_cs):
            raise ValueError("dates / factor_cs / return_cs 长度必须一致。")
        if n < 4:
            raise ValueError("数据量过少（至少需要 4 期）。")

        ic_fn = calc_rank_ic if self.use_rank_ic else calc_ic

        # 严格时间切分
        is_dates, oos_dates = split_train_test(dates, self.oos_ratio)
        split_idx = len(is_dates)

        is_factor  = factor_cs[:split_idx]
        is_return  = return_cs[:split_idx]
        oos_factor = factor_cs[split_idx:]
        oos_return = return_cs[split_idx:]

        # 前视偏差检查：OOS 首期必须晚于 IS 末期
        if not validate_no_lookahead(is_dates[-1], oos_dates[0], lag=1):
            raise ValueError(
                f"Look-ahead Bias 检测：OOS 起始 {oos_dates[0]} "
                f"不晚于 IS 末尾 {is_dates[-1]}。"
            )

        # 计算 IC 序列
        is_ics  = [ic_fn(f, r) for f, r in zip(is_factor, is_return)]
        oos_ics = [ic_fn(f, r) for f, r in zip(oos_factor, oos_return)]

        # 简单多空组合收益
        is_rets  = self._portfolio_returns(is_factor,  is_return)
        oos_rets = self._portfolio_returns(oos_factor, oos_return)

        is_stats  = summarize_ic_series(is_ics)
        oos_stats = summarize_ic_series(oos_ics)

        self._result = OOSResult(
            is_ic      = is_stats["mean"],
            oos_ic     = oos_stats["mean"],
            is_sharpe  = calc_sharpe(is_rets),
            oos_sharpe = calc_sharpe(oos_rets),
            is_period  = (is_dates[0],  is_dates[-1]),
            oos_period = (oos_dates[0], oos_dates[-1]),
        )

        # 附加扩展字段（挂在 result 上，UI 直接读取）
        self._result.is_stats  = is_stats
        self._result.oos_stats = oos_stats
        self._result.is_n      = len(is_ics)
        self._result.oos_n     = len(oos_ics)

        return self._result

    def check_lookahead(
        self,
        factor_timestamps: list[datetime],
        return_timestamps: list[datetime],
    ) -> list[dict]:
        """
        批量检测每期因子时间戳 vs 收益时间戳是否存在前视偏差。

        Returns
        -------
        list[dict]  违规记录列表，空列表 = 无前视偏差
        """
        violations = []
        for i, (ft, rt) in enumerate(
            zip(factor_timestamps, return_timestamps)
        ):
            if not validate_no_lookahead(ft, rt, lag=1):
                violations.append({
                    "period":   i,
                    "factor_ts":  ft,
                    "return_ts":  rt,
                    "message": (
                        f"期 {i}：收益时间戳 {rt} <= 因子时间戳 {ft}，"
                        "存在前视偏差。"
                    ),
                })
        return violations

    def get_result(self) -> OOSResult | None:
        return self._result

    def reset(self) -> None:
        self._result = None

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _portfolio_returns(
        factor_cs: list[dict[str, float]],
        return_cs: list[dict[str, float]],
    ) -> list[float]:
        """Top-decile 多空组合每期收益估算。"""
        period_rets = []
        for fc, rc in zip(factor_cs, return_cs):
            common = [s for s in fc if s in rc]
            if len(common) < 10:
                period_rets.append(0.0)
                continue
            sorted_syms = sorted(common, key=lambda s: fc[s], reverse=True)
            n10 = max(1, len(sorted_syms) // 10)
            long_ret  = sum(rc[s] for s in sorted_syms[:n10])  / n10
            short_ret = sum(rc[s] for s in sorted_syms[-n10:]) / n10
            period_rets.append(long_ret - short_ret)
        return period_rets
