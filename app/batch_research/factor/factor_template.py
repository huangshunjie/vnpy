"""
factor/factor_template.py

FactorTemplate  —  所有因子的抽象基类
BBRFactor       —  基于 BatchBacktestResult 强类型字段的新路径基类（推荐使用）
ResultFactor    —  旧路径基类（从 BacktestResult.statistics dict 读值，deprecated）
BarFactor       —  基于 BarData 原始数据的因子基类

迁移说明：
  新代码应继承 BBRFactor，旧代码继承 ResultFactor 不受影响（向后兼容）。
  BBRFactor._extract() 直接读 BatchBacktestResult 强类型字段，
  不依赖 r.statistics dict，与重构后的数据模型完全对齐。
"""

from __future__ import annotations

import math
import warnings
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    from ..task import BacktestResult
    from ..batch_result import BatchBacktestResult


# ──────────────────────────────────────────────────── #
#  FactorTemplate  —  抽象基类
# ──────────────────────────────────────────────────── #

class FactorTemplate(ABC):
    """
    所有因子的抽象基类。

    子类必须：
      1. 设置唯一的类级别 factor_name 字符串
      2. 实现 calculate(results, **kwargs) -> pd.Series

    返回的 Series 必须：
      - 以 vt_symbol 字符串为 index
      - 包含数值（float / int）
      - 跳过无法计算的 symbol（不包含 NaN，直接 omit）
    """

    factor_name: str = ""
    description: str = ""
    higher_is_better: bool = True

    @abstractmethod
    def calculate(
        self,
        results: list,
        **kwargs,
    ) -> "pd.Series":
        """计算截面因子值，返回 pd.Series(values, index=vt_symbols)。"""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.factor_name!r})"


# ──────────────────────────────────────────────────── #
#  BBRFactor  —  新路径：接受 BatchBacktestResult
# ──────────────────────────────────────────────────── #

class BBRFactor(FactorTemplate):
    """
    基于 BatchBacktestResult 强类型字段的因子基类（推荐使用）。

    子类只需实现 _extract(result: BatchBacktestResult) -> float | None。
    status != "success" 的结果自动跳过。
    NaN / Inf 值自动过滤。

    示例::

        class MyFactor(BBRFactor):
            factor_name = "my_custom_factor"
            higher_is_better = True

            def _extract(self, result: BatchBacktestResult) -> float | None:
                if result.total_trade_count < 10:
                    return None
                return result.sharpe_ratio * result.calmar_ratio
    """

    def calculate(
        self,
        results: list["BatchBacktestResult"],
        **kwargs,
    ) -> "pd.Series":
        import pandas as pd  # noqa: PLC0415

        data: dict[str, float] = {}
        for r in results:
            if getattr(r, "status", "") != "success":
                continue
            val = self._extract(r)
            if val is None:
                continue
            try:
                fval = float(val)
                if not math.isnan(fval) and not math.isinf(fval):
                    data[r.vt_symbol] = fval
            except (TypeError, ValueError):
                pass

        return pd.Series(data, name=self.factor_name)

    def _extract(self, result: "BatchBacktestResult") -> float | None:
        """从 BatchBacktestResult 提取因子值，None 表示跳过该 symbol。"""
        raise NotImplementedError


# ──────────────────────────────────────────────────── #
#  ResultFactor  —  旧路径（deprecated，保持向后兼容）
# ──────────────────────────────────────────────────── #

class ResultFactor(FactorTemplate):
    """
    从 BacktestResult.statistics dict 读取因子值的旧路径基类。

    .. deprecated::
        请改用 BBRFactor，直接读 BatchBacktestResult 强类型字段。
        本类保留以兼容现有代码，未来版本可能移除。
    """

    def calculate(
        self,
        results: list["BacktestResult"],
        **kwargs,
    ) -> "pd.Series":
        import pandas as pd  # noqa: PLC0415

        data: dict[str, float] = {}
        for r in results:
            if not getattr(r, "statistics", None):
                continue
            val = self._extract(r)
            if val is None:
                continue
            try:
                fval = float(val)
                if not math.isnan(fval) and not math.isinf(fval):
                    data[r.vt_symbol] = fval
            except (TypeError, ValueError):
                pass

        return pd.Series(data, name=self.factor_name)

    def _extract(self, result: "BacktestResult") -> float | None:
        """从旧版 BacktestResult 提取因子值，None 表示跳过。"""
        raise NotImplementedError


# ──────────────────────────────────────────────────── #
#  内置 BBRFactor 实现（从旧 ResultFactor 迁移而来）
# ──────────────────────────────────────────────────── #

class SharpeRatioFactor(BBRFactor):
    factor_name      = "sharpe_ratio"
    description      = "Annualised Sharpe ratio"
    higher_is_better = True

    def _extract(self, r: "BatchBacktestResult") -> float | None:
        return r.sharpe_ratio


class TotalReturnFactor(BBRFactor):
    factor_name      = "total_return"
    description      = "Total return (%) over the backtest period"
    higher_is_better = True

    def _extract(self, r: "BatchBacktestResult") -> float | None:
        return r.total_return


class AnnualReturnFactor(BBRFactor):
    factor_name      = "annual_return"
    description      = "Annualised return (%)"
    higher_is_better = True

    def _extract(self, r: "BatchBacktestResult") -> float | None:
        return r.annual_return


class MaxDrawdownFactor(BBRFactor):
    factor_name      = "max_ddpercent"
    description      = "Maximum drawdown (%), less negative = better"
    higher_is_better = True

    def _extract(self, r: "BatchBacktestResult") -> float | None:
        return r.max_ddpercent


class CalmarRatioFactor(BBRFactor):
    factor_name      = "calmar_ratio"
    description      = "Calmar ratio: annual_return / abs(max_ddpercent)"
    higher_is_better = True

    def _extract(self, r: "BatchBacktestResult") -> float | None:
        return r.calmar_ratio


class ReturnDrawdownRatioFactor(BBRFactor):
    factor_name      = "return_drawdown_ratio"
    description      = "Return-to-drawdown ratio"
    higher_is_better = True

    def _extract(self, r: "BatchBacktestResult") -> float | None:
        return r.return_drawdown_ratio


class WinRateFactor(BBRFactor):
    factor_name      = "win_rate"
    description      = "Daily win rate (%)"
    higher_is_better = True

    def _extract(self, r: "BatchBacktestResult") -> float | None:
        return r.win_rate if r.win_rate else None


class TradingFrequencyFactor(BBRFactor):
    factor_name      = "daily_trade_count"
    description      = "Average daily trade count"
    higher_is_better = False

    def _extract(self, r: "BatchBacktestResult") -> float | None:
        return r.daily_trade_count if r.daily_trade_count else None


class EwmSharpeFactor(BBRFactor):
    factor_name      = "ewm_sharpe"
    description      = "Exponentially-weighted Sharpe ratio"
    higher_is_better = True

    def _extract(self, r: "BatchBacktestResult") -> float | None:
        return r.ewm_sharpe if r.ewm_sharpe else None


class ProfitFactorFactor(BBRFactor):
    factor_name      = "profit_factor"
    description      = "Gross profit / gross cost ratio"
    higher_is_better = True

    def _extract(self, r: "BatchBacktestResult") -> float | None:
        return r.profit_factor if r.profit_factor else None


class AnnualVolatilityFactor(BBRFactor):
    factor_name      = "annual_volatility"
    description      = "Annualised volatility (%)"
    higher_is_better = False

    def _extract(self, r: "BatchBacktestResult") -> float | None:
        return r.annual_volatility if r.annual_volatility else None


# ──────────────────────────────────────────────────── #
#  BarFactor  —  基于原始 BarData 的因子基类
# ──────────────────────────────────────────────────── #

class BarFactor(FactorTemplate):
    """
    基于原始 BarData 计算的因子基类。

    子类覆盖 _compute_for_symbol(symbol, bars) -> float | None。
    bars_map 通过 kwargs["bars_map"] 传入。
    """

    def calculate(
        self,
        results: list,
        **kwargs,
    ) -> "pd.Series":
        import pandas as pd  # noqa: PLC0415

        bars_map: dict = kwargs.get("bars_map", {})
        data: dict[str, float] = {}

        for r in results:
            bars = bars_map.get(r.vt_symbol)
            if not bars:
                continue
            val = self._compute_for_symbol(r.vt_symbol, bars)
            if val is None:
                continue
            try:
                fval = float(val)
                if not math.isnan(fval) and not math.isinf(fval):
                    data[r.vt_symbol] = fval
            except (TypeError, ValueError):
                pass

        return pd.Series(data, name=self.factor_name)

    def _compute_for_symbol(
        self,
        vt_symbol: str,
        bars: list,
    ) -> float | None:
        raise NotImplementedError


# ──────────────────────────────────────────────────── #
#  内置 BarFactor 实现
# ──────────────────────────────────────────────────── #

class PriceMomentumFactor(BarFactor):
    """价格动量因子：trailing N bar 的收益率。"""
    factor_name      = "price_momentum"
    description      = "Price momentum over trailing N bars"
    higher_is_better = True

    def __init__(self, lookback: int = 60) -> None:
        self.lookback = lookback
        self.factor_name = f"price_momentum_{lookback}b"

    def _compute_for_symbol(self, vt_symbol: str, bars: list) -> float | None:
        if len(bars) < self.lookback + 1:
            return None
        start_price = bars[-self.lookback - 1].close_price
        end_price   = bars[-1].close_price
        if start_price <= 0:
            return None
        return (end_price - start_price) / start_price * 100


class VolatilityFactor(BarFactor):
    """实现波动率因子：日对数收益率的年化标准差。"""
    factor_name      = "volatility_60b"
    description      = "Annualised realised volatility over trailing 60 bars"
    higher_is_better = False

    def __init__(self, lookback: int = 60, annual_days: int = 240) -> None:
        self.lookback    = lookback
        self.annual_days = annual_days
        self.factor_name = f"volatility_{lookback}b"

    def _compute_for_symbol(self, vt_symbol: str, bars: list) -> float | None:
        if len(bars) < self.lookback + 1:
            return None
        closes = [b.close_price for b in bars[-self.lookback - 1:]]
        log_rets = [
            math.log(closes[i] / closes[i - 1])
            for i in range(1, len(closes))
            if closes[i - 1] > 0 and closes[i] > 0
        ]
        if len(log_rets) < 2:
            return None
        n    = len(log_rets)
        mean = sum(log_rets) / n
        var  = sum((r - mean) ** 2 for r in log_rets) / (n - 1)
        return math.sqrt(var * self.annual_days) * 100


class RSIFactor(BarFactor):
    """RSI 因子：相对强弱指标。"""
    factor_name      = "rsi_14"
    description      = "RSI over trailing 14 bars"
    higher_is_better = False

    def __init__(self, period: int = 14) -> None:
        self.period = period
        self.factor_name = f"rsi_{period}"

    def _compute_for_symbol(self, vt_symbol: str, bars: list) -> float | None:
        if len(bars) < self.period + 1:
            return None
        closes = [b.close_price for b in bars[-(self.period + 1):]]
        gains, losses = [], []
        for i in range(1, len(closes)):
            delta = closes[i] - closes[i - 1]
            gains.append(max(delta, 0))
            losses.append(max(-delta, 0))
        avg_gain = sum(gains) / self.period
        avg_loss = sum(losses) / self.period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - 100 / (1 + rs)
