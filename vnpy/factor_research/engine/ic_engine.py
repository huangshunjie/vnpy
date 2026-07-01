"""
factor_research/engine/ic_engine.py

IcEngine — IC / RankIC 计算引擎。

职责：
  - 从 DataFrame 构造测试因子（close 的 N 日动量）
  - 计算远期收益（forward returns）
  - 计算 Pearson IC 序列与 Spearman RankIC 序列
  - 汇总 IC_mean / IC_std / ICIR / 胜率等统计量
  - 把滚动 IC / RankIC 序列一并存入 IcStats，供 IcSeriesTab 绘图
  - 严禁直接操作 UI，严禁直接访问数据库

单合约场景说明：
  单合约没有横截面，IC 退化为时序相关性：
    因子值序列（t 时刻） vs 远期收益序列（t+lag 时刻）
  多合约截面 IC 在后续阶段实现。

测试因子：close.pct_change(momentum_window)
  momentum_window 默认 20，表示 20 日收益率动量因子。
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from ..model import IcStats


class IcEngine:
    """IC / RankIC 计算引擎。"""

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def compute(
        self,
        df: "pd.DataFrame",
        vt_symbol: str,
        factor_name: str = "momentum_20",
        momentum_window: int = 20,
        lag: int = 5,
    ) -> IcStats:
        """
        对单合约 OHLCV DataFrame 计算 IC 统计量及时序序列。

        参数：
            df               : DataEngine 返回的 DataFrame（index=datetime）
            vt_symbol        : 合约代码，仅用于结果标记
            factor_name      : 因子名称标签
            momentum_window  : 动量因子窗口（close.pct_change(N)）
            lag              : 远期收益持有期（天）

        返回：
            IcStats — 含统计量 + ic_series + rank_ic_series
        """
        import pandas as pd
        from scipy.stats import pearsonr, spearmanr

        def _empty() -> IcStats:
            return IcStats(vt_symbol=vt_symbol, factor_name=factor_name,
                           lag=lag, sample_size=0)

        if df is None or df.empty or "close" not in df.columns:
            return _empty()

        close = df["close"].copy()

        # 构造测试因子：N 日动量
        factor_series = close.pct_change(momentum_window)
        # 构造远期收益：lag 日后的持有期收益
        forward_ret = close.pct_change(lag).shift(-lag)

        combined = pd.concat(
            [factor_series.rename("factor"), forward_ret.rename("fwd")],
            axis=1,
        ).dropna()

        n = len(combined)
        if n < 10:
            return IcStats(vt_symbol=vt_symbol, factor_name=factor_name,
                           lag=lag, sample_size=n)

        f = combined["factor"].values
        r = combined["fwd"].values

        ic_val, _      = pearsonr(f, r)
        rank_ic_val, _ = spearmanr(f, r)

        # 滚动窗口：min(60, n//4)，至少 10
        roll_win = max(10, min(60, n // 4))

        ic_s     = self._rolling_pearson(combined["factor"], combined["fwd"], roll_win)
        rank_ic_s = self._rolling_spearman(combined["factor"], combined["fwd"], roll_win)

        ic_clean     = ic_s.dropna()
        rank_ic_clean = rank_ic_s.dropna()

        def _safe(arr, fn):
            if len(arr) == 0:
                return float("nan")
            v = fn(arr)
            return float(v) if not math.isnan(float(v)) else float("nan")

        ic_mean = _safe(ic_clean, lambda x: x.mean())
        ic_std  = _safe(ic_clean, lambda x: x.std())
        icir    = ic_mean / ic_std if ic_std and ic_std > 1e-12 else float("nan")
        ic_pos  = _safe(ic_clean, lambda x: (x > 0).mean())

        ric_mean = _safe(rank_ic_clean, lambda x: x.mean())
        ric_std  = _safe(rank_ic_clean, lambda x: x.std())
        ricir    = ric_mean / ric_std if ric_std and ric_std > 1e-12 else float("nan")
        ric_pos  = _safe(rank_ic_clean, lambda x: (x > 0).mean())

        return IcStats(
            vt_symbol=vt_symbol,
            factor_name=factor_name,
            lag=lag,
            ic_mean=ic_mean,
            ic_std=ic_std,
            icir=icir,
            ic_positive_rate=ic_pos,
            rank_ic_mean=ric_mean,
            rank_ic_std=ric_std,
            rank_icir=ricir,
            rank_ic_positive_rate=ric_pos,
            sample_size=n,
            ic_series_len=len(ic_clean),
            # 滚动序列——完整保留（含 NaN），供绘图层自行处理
            ic_series=ic_s,
            rank_ic_series=rank_ic_s,
        )

    # ------------------------------------------------------------------ #
    #  辅助：滚动相关系数
    # ------------------------------------------------------------------ #

    @staticmethod
    def _rolling_pearson(
        x: "pd.Series",
        y: "pd.Series",
        window: int,
    ) -> "pd.Series":
        return x.rolling(window).corr(y)

    @staticmethod
    def _rolling_spearman(
        x: "pd.Series",
        y: "pd.Series",
        window: int,
    ) -> "pd.Series":
        def _win(sub_x: "pd.Series") -> float:
            from scipy.stats import spearmanr
            sub_y = y.loc[sub_x.index]
            if len(sub_x) < 3:
                return float("nan")
            val, _ = spearmanr(sub_x.values, sub_y.values)
            return float(val)

        return x.rolling(window).apply(_win, raw=False)
