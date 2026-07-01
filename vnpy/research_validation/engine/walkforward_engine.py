"""
research_validation/engine/walkforward_engine.py

WalkForwardEngine — Walk Forward Analysis 引擎（Phase 2 实现）。

职责：
  - 接收因子截面序列 + 收益截面序列
  - 按 rolling_windows() 切分滚动窗口
  - 逐窗口计算 Train IC / Test IC / Sharpe
  - 汇总跨窗口衰减比率与过拟合评分

❌ 不允许优化策略 / 预测模型 / 机器学习。
❌ 不允许连接交易接口。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..utils.stats_utils import (
    calc_ic,
    calc_rank_ic,
    calc_sharpe,
    calc_ir,
    calc_t_stat,
    summarize_ic_series,
)
from ..utils.time_split_utils import rolling_windows, count_valid_windows
from ..model.result_model import WalkForwardResult


@dataclass
class WalkForwardSummary:
    """Walk Forward 跨窗口汇总统计。"""
    n_windows:       int   = 0
    avg_train_ic:    float = 0.0
    avg_test_ic:     float = 0.0
    avg_ic_decay:    float = 0.0   # (train - test) / |train|，均值
    avg_train_sharpe: float = 0.0
    avg_test_sharpe:  float = 0.0
    test_ic_ir:      float = 0.0   # 基于各窗口 test IC 的 IR
    test_ic_t_stat:  float = 0.0
    test_win_rate:   float = 0.0   # test IC > 0 的窗口比例
    overfit_score:   float = 0.0   # 0~100，越低越好（越接近0表示越无过拟合）

    @property
    def is_robust(self) -> bool:
        """test IC IR > 0.3 且 overfit_score < 40 视为稳健。"""
        return self.test_ic_ir > 0.3 and self.overfit_score < 40.0

    @property
    def verdict(self) -> str:
        if self.is_robust:
            return "PASS — 因子样本外表现稳健"
        if self.avg_test_ic <= 0.0:
            return "FAIL — 样本外 IC 为负，因子无效"
        if self.overfit_score >= 40.0:
            return "WARN — 存在过拟合迹象"
        return "UNCERTAIN — 数据量不足或信号较弱"


class WalkForwardEngine:
    """
    Walk Forward Analysis 引擎（Phase 2 实现）。

    使用方式：
        engine = WalkForwardEngine()
        engine.set_windows(train=252, test=63, step=21)
        results, summary = engine.run(factor_cs, return_cs, dates)
    """

    def __init__(self) -> None:
        self.train_window: int  = 252
        self.test_window:  int  = 63
        self.step_size:    int  = 21
        self.use_rank_ic:  bool = False   # True = RankIC，False = IC
        self._results:  list[WalkForwardResult] = []
        self._summary:  WalkForwardSummary | None = None

    def set_windows(
        self,
        train: int,
        test:  int,
        step:  int = 21,
    ) -> None:
        if train <= 0 or test <= 0 or step <= 0:
            raise ValueError("train / test / step 必须为正整数。")
        self.train_window = train
        self.test_window  = test
        self.step_size    = step

    def preview_windows(
        self,
        n_periods: int,
    ) -> int:
        """在不计算的情况下预览可生成的窗口数量。"""
        return count_valid_windows(
            n_periods, self.train_window, self.test_window, self.step_size
        )

    # ------------------------------------------------------------------ #
    #  主计算入口
    # ------------------------------------------------------------------ #

    def run(
        self,
        factor_cs: list[dict[str, float]],
        return_cs: list[dict[str, float]],
        dates:     list[datetime],
    ) -> tuple[list[WalkForwardResult], WalkForwardSummary]:
        """
        执行 Walk Forward 滚动验证。

        Parameters
        ----------
        factor_cs : 按时间升序排列的因子截面序列 [{symbol: value}, ...]
        return_cs : 对应的持有期收益截面序列 [{symbol: ret}, ...]
        dates     : 对应日期序列（长度须与 factor_cs 相同）

        Returns
        -------
        (results, summary)
          results  : 逐窗口 WalkForwardResult 列表
          summary  : 跨窗口汇总统计
        """
        n = len(dates)
        if n != len(factor_cs) or n != len(return_cs):
            raise ValueError("dates / factor_cs / return_cs 长度必须一致。")
        if n < self.train_window + self.test_window:
            raise ValueError(
                f"数据长度 {n} 不足以生成任何窗口"
                f"（最小需求：{self.train_window + self.test_window}）。"
            )

        ic_fn = calc_rank_ic if self.use_rank_ic else calc_ic
        windows = rolling_windows(
            dates, self.train_window, self.test_window, self.step_size
        )

        self._results = []
        for idx, (train_dates, test_dates) in enumerate(windows):
            # 按日期索引切片
            t_start = dates.index(train_dates[0])
            t_end   = dates.index(train_dates[-1]) + 1
            v_start = dates.index(test_dates[0])
            v_end   = dates.index(test_dates[-1]) + 1

            train_ics = [
                ic_fn(factor_cs[i], return_cs[i])
                for i in range(t_start, t_end)
            ]
            test_ics = [
                ic_fn(factor_cs[i], return_cs[i])
                for i in range(v_start, v_end)
            ]

            train_ret = self._portfolio_returns(factor_cs, return_cs, t_start, t_end)
            test_ret  = self._portfolio_returns(factor_cs, return_cs, v_start, v_end)

            train_ic_mean = sum(train_ics) / len(train_ics) if train_ics else 0.0
            test_ic_mean  = sum(test_ics)  / len(test_ics)  if test_ics  else 0.0

            result = WalkForwardResult(
                window_idx   = idx,
                train_start  = train_dates[0],
                train_end    = train_dates[-1],
                test_start   = test_dates[0],
                test_end     = test_dates[-1],
                train_ic     = train_ic_mean,
                test_ic      = test_ic_mean,
                train_sharpe = calc_sharpe(train_ret),
                test_sharpe  = calc_sharpe(test_ret),
            )
            self._results.append(result)

        self._summary = self._build_summary(self._results)
        return self._results, self._summary

    # ------------------------------------------------------------------ #
    #  结果查询
    # ------------------------------------------------------------------ #

    def get_results(self) -> list[WalkForwardResult]:
        return list(self._results)

    def get_summary(self) -> WalkForwardSummary | None:
        return self._summary

    def reset(self) -> None:
        self._results.clear()
        self._summary = None

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _portfolio_returns(
        factor_cs: list[dict[str, float]],
        return_cs: list[dict[str, float]],
        start: int,
        end:   int,
    ) -> list[float]:
        """
        简单 Top-decile 多空组合收益估算。

        每期按因子排序，取前 10% 做多 / 后 10% 做空，
        计算等权多空组合日度收益。
        """
        period_rets = []
        for i in range(start, end):
            fc = factor_cs[i]
            rc = return_cs[i]
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

    @staticmethod
    def _build_summary(
        results: list[WalkForwardResult],
    ) -> WalkForwardSummary:
        if not results:
            return WalkForwardSummary()

        n          = len(results)
        train_ics  = [r.train_ic  for r in results]
        test_ics   = [r.test_ic   for r in results]
        decays     = [r.ic_decay  for r in results]
        t_sharpes  = [r.train_sharpe for r in results]
        v_sharpes  = [r.test_sharpe  for r in results]

        avg_train_ic = sum(train_ics) / n
        avg_test_ic  = sum(test_ics)  / n
        avg_decay    = sum(decays)    / n
        win_rate     = sum(1 for ic in test_ics if ic > 0) / n

        # 过拟合评分（0~100）：衰减越大、test IC 越低 → 分数越高
        raw_overfit = max(0.0, avg_decay) * 100.0
        overfit_score = min(100.0, raw_overfit)

        return WalkForwardSummary(
            n_windows        = n,
            avg_train_ic     = avg_train_ic,
            avg_test_ic      = avg_test_ic,
            avg_ic_decay     = avg_decay,
            avg_train_sharpe = sum(t_sharpes) / n,
            avg_test_sharpe  = sum(v_sharpes)  / n,
            test_ic_ir       = calc_ir(test_ics),
            test_ic_t_stat   = calc_t_stat(test_ics),
            test_win_rate    = win_rate,
            overfit_score    = overfit_score,
        )
