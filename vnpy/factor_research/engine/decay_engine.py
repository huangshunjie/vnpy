"""
factor_research/engine/decay_engine.py

DecayEngine — IC Decay 计算引擎。

职责：
  - 对 lag=1,2,...,max_lag 循环调用 IcEngine.compute()
  - 把每个 lag 的 ic_mean / rank_ic_mean / icir 汇总成 DecayResult
  - 计算最优持有期（|IC| 最大处的 lag）
  - 严禁直接操作 UI，严禁直接访问数据库

设计：
  DecayEngine 持有一个 IcEngine 实例，compute() 是纯函数式调用。
  每次 lag 循环共用同一份 DataFrame，无额外 IO。
  progress_callback 可选，供 dispatcher 向 EventEngine 汇报进度。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    import pandas as pd

from .ic_engine import IcEngine
from ..model import DecayPoint, DecayResult


class DecayEngine:
    """IC Decay 计算引擎。"""

    def __init__(self) -> None:
        self._ic_engine = IcEngine()

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def compute(
        self,
        df: "pd.DataFrame",
        vt_symbol: str,
        factor_name: str = "momentum_20",
        momentum_window: int = 20,
        max_lag: int = 20,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> DecayResult:
        """
        对 lag = 1, 2, ..., max_lag 逐一计算 IC 统计量，汇总为 DecayResult。

        参数：
            df               : DataEngine 返回的 OHLCV DataFrame
            vt_symbol        : 合约代码
            factor_name      : 因子名称标签
            momentum_window  : 动量因子窗口
            max_lag          : 最大持有期天数
            progress_callback: 可选回调 (current_lag, max_lag)，用于汇报进度

        返回：
            DecayResult — 含 max_lag 个 DecayPoint
        """
        points: list[DecayPoint] = []

        for lag in range(1, max_lag + 1):
            if progress_callback is not None:
                progress_callback(lag, max_lag)

            ic_stats = self._ic_engine.compute(
                df,
                vt_symbol=vt_symbol,
                factor_name=factor_name,
                momentum_window=momentum_window,
                lag=lag,
            )

            points.append(DecayPoint(
                lag=lag,
                ic_mean=ic_stats.ic_mean,
                rank_ic_mean=ic_stats.rank_ic_mean,
                icir=ic_stats.icir,
                rank_icir=ic_stats.rank_icir,
                sample_size=ic_stats.sample_size,
            ))

        return DecayResult(
            vt_symbol=vt_symbol,
            factor_name=factor_name,
            max_lag=max_lag,
            points=points,
        )
