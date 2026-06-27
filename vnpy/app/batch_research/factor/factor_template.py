"""
FactorTemplate

Abstract base class for all factors in the batch research system.

A "factor" here operates on a list of BacktestResult objects (cross-sectional)
and returns a pd.Series indexed by vt_symbol with the factor values.

Factor types supported:
  - ResultFactor:  reads statistics fields from BacktestResult directly
                   (e.g. Sharpe, MaxDD, Calmar, Momentum, Volatility)
  - BarFactor:     computes from raw BarData (e.g. price momentum, RSI, MACD)
  - CustomFactor:  fully user-defined via subclassing

Naming convention:
  factor_name must be unique within a FactorEngine instance.
  Use snake_case, e.g. 'sharpe_ratio', 'momentum_12m', 'max_ddpercent'.

Usage::

    class MyFactor(FactorTemplate):
        factor_name = "my_factor"

        def calculate(self, results, **kwargs):
            return pd.Series(
                {r.vt_symbol: some_value(r) for r in results if r.statistics}
            )

    engine = FactorEngine()
    engine.register(MyFactor())
    factor_df = engine.calculate(results)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    from ..task import BacktestResult


class FactorTemplate(ABC):
    """
    Abstract base class for cross-sectional factors.

    Subclasses must:
      1. Set a unique class-level ``factor_name`` string.
      2. Implement ``calculate(results, **kwargs) -> pd.Series``.

    The returned Series must:
      - Be indexed by vt_symbol strings
      - Contain numeric values (float / int)
      - Exclude symbols where the factor cannot be computed (NaN or omit)
    """

    factor_name: str = ""

    # Optional metadata — used by FactorEngine reports
    description: str = ""
    higher_is_better: bool = True   # for display in rank/IC reports

    @abstractmethod
    def calculate(
        self,
        results: list["BacktestResult"],
        **kwargs,
    ) -> "pd.Series":
        """
        Compute factor values cross-sectionally.

        :param results: List of BacktestResult objects from BatchBacktestingEngine.
        :param kwargs:  Optional additional data (bars_map, fundamental_data, etc.)
        :return:        pd.Series(values, index=vt_symbols), numeric dtype.
        """

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.factor_name!r})"


# ------------------------------------------------------------------ #
#  Convenience base for factors that read BacktestResult.statistics
# ------------------------------------------------------------------ #

class ResultFactor(FactorTemplate):
    """
    Base class for factors derived directly from BacktestResult statistics.

    Subclasses only need to override ``_extract(result) -> float | None``.
    Symbols with no statistics (FAILED/SKIPPED) are automatically excluded.
    """

    def calculate(
        self,
        results: list["BacktestResult"],
        **kwargs,
    ) -> "pd.Series":
        import pandas as pd  # noqa: PLC0415

        data: dict[str, float] = {}
        for r in results:
            if not r.statistics:
                continue
            val = self._extract(r)
            if val is not None:
                import math
                if not math.isnan(val) and not math.isinf(val):
                    data[r.vt_symbol] = val
        return pd.Series(data, name=self.factor_name)

    def _extract(self, result: "BacktestResult") -> float | None:
        """
        Extract a numeric value from one BacktestResult.
        Return None to exclude this symbol from the factor.
        """
        raise NotImplementedError


# ------------------------------------------------------------------ #
#  Built-in ResultFactors
# ------------------------------------------------------------------ #

class SharpeRatioFactor(ResultFactor):
    factor_name = "sharpe_ratio"
    description = "Annualised Sharpe ratio from backtesting"
    higher_is_better = True

    def _extract(self, result: "BacktestResult") -> float | None:
        return result.sharpe_ratio


class TotalReturnFactor(ResultFactor):
    factor_name = "total_return"
    description = "Total return (%) over the backtest period"
    higher_is_better = True

    def _extract(self, result: "BacktestResult") -> float | None:
        return result.total_return


class AnnualReturnFactor(ResultFactor):
    factor_name = "annual_return"
    description = "Annualised return (%) from backtesting"
    higher_is_better = True

    def _extract(self, result: "BacktestResult") -> float | None:
        return result.annual_return


class MaxDrawdownFactor(ResultFactor):
    factor_name = "max_ddpercent"
    description = "Maximum drawdown (%), lower is better (more negative = worse)"
    higher_is_better = True   # less negative = better

    def _extract(self, result: "BacktestResult") -> float | None:
        return result.max_ddpercent


class CalmarRatioFactor(ResultFactor):
    factor_name = "calmar_ratio"
    description = "Calmar ratio: annual_return / abs(max_ddpercent)"
    higher_is_better = True

    def _extract(self, result: "BacktestResult") -> float | None:
        mdd = abs(result.max_ddpercent)
        if mdd == 0:
            return None
        return result.annual_return / mdd


class ReturnDrawdownRatioFactor(ResultFactor):
    factor_name = "return_drawdown_ratio"
    description = "Return-to-drawdown ratio from BacktestingEngine"
    higher_is_better = True

    def _extract(self, result: "BacktestResult") -> float | None:
        return result.statistics.get("return_drawdown_ratio")


class WinRateFactor(ResultFactor):
    """
    Per-symbol win rate: fraction of winning trades.
    Requires trade-level stats; falls back to statistics dict lookup.
    """
    factor_name = "win_rate"
    description = "Trade-level win rate (%)"
    higher_is_better = True

    def _extract(self, result: "BacktestResult") -> float | None:
        stats = result.statistics
        total = stats.get("total_trade_count", 0)
        if not total:
            return None
        # BacktestingEngine doesn't expose winning_trade_count directly,
        # so we derive it from daily_net_pnl sign heuristic if available,
        # or return None to omit.
        return stats.get("win_rate")   # populated by enrich_statistics if present


class TradingFrequencyFactor(ResultFactor):
    factor_name = "daily_trade_count"
    description = "Average daily trade count"
    higher_is_better = False   # more trading = higher costs

    def _extract(self, result: "BacktestResult") -> float | None:
        return result.statistics.get("daily_trade_count")


class EwmSharpeFactor(ResultFactor):
    factor_name = "ewm_sharpe"
    description = "Exponentially-weighted Sharpe ratio"
    higher_is_better = True

    def _extract(self, result: "BacktestResult") -> float | None:
        return result.statistics.get("ewm_sharpe")


class ProfitFactorFactor(ResultFactor):
    """profit_factor added by StatisticsAnalyzer.enrich()."""
    factor_name = "profit_factor"
    description = "Gross profit / gross cost ratio"
    higher_is_better = True

    def _extract(self, result: "BacktestResult") -> float | None:
        return result.statistics.get("profit_factor")


# ------------------------------------------------------------------ #
#  BarFactor base class (for price/volume momentum, RSI, MACD, etc.)
# ------------------------------------------------------------------ #

class BarFactor(FactorTemplate):
    """
    Base class for factors computed from raw BarData.

    calculate() receives both results (for metadata) and
    bars_map (vt_symbol -> list[BarData]) via kwargs.

    Subclasses override _compute_for_symbol(symbol, bars) -> float | None.
    """

    def calculate(
        self,
        results: list["BacktestResult"],
        **kwargs,
    ) -> "pd.Series":
        import pandas as pd  # noqa: PLC0415
        import math

        bars_map: dict = kwargs.get("bars_map", {})
        data: dict[str, float] = {}

        for r in results:
            bars = bars_map.get(r.vt_symbol)
            if not bars:
                continue
            val = self._compute_for_symbol(r.vt_symbol, bars)
            if val is not None and not math.isnan(val) and not math.isinf(val):
                data[r.vt_symbol] = val

        return pd.Series(data, name=self.factor_name)

    def _compute_for_symbol(
        self,
        vt_symbol: str,
        bars: list,
    ) -> float | None:
        raise NotImplementedError


# ------------------------------------------------------------------ #
#  Built-in BarFactors
# ------------------------------------------------------------------ #

class PriceMomentumFactor(BarFactor):
    """
    Price momentum: return over a trailing window of bars.

    momentum = (close[-1] - close[-lookback]) / close[-lookback]
    """
    factor_name = "price_momentum"
    description = "Price momentum over trailing N bars"
    higher_is_better = True

    def __init__(self, lookback: int = 60) -> None:
        self.lookback = lookback
        self.factor_name = f"price_momentum_{lookback}b"

    def _compute_for_symbol(self, vt_symbol: str, bars: list) -> float | None:
        if len(bars) < self.lookback + 1:
            return None
        start_price = bars[-self.lookback - 1].close_price
        end_price = bars[-1].close_price
        if start_price <= 0:
            return None
        return (end_price - start_price) / start_price * 100


class VolatilityFactor(BarFactor):
    """
    Realised volatility: annualised std of daily log-returns.
    lower_is_better in a risk-adjusted context.
    """
    factor_name = "volatility_60b"
    description = "Annualised realised volatility over trailing 60 bars"
    higher_is_better = False

    def __init__(self, lookback: int = 60, annual_days: int = 240) -> None:
        self.lookback = lookback
        self.annual_days = annual_days
        self.factor_name = f"volatility_{lookback}b"

    def _compute_for_symbol(self, vt_symbol: str, bars: list) -> float | None:
        import math
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
        n = len(log_rets)
        mean = sum(log_rets) / n
        variance = sum((r - mean) ** 2 for r in log_rets) / (n - 1)
        return math.sqrt(variance * self.annual_days) * 100


class RSIFactor(BarFactor):
    """
    Relative Strength Index (RSI) computed on trailing close prices.
    RSI in [0, 100]; higher = more overbought.
    """
    factor_name = "rsi_14"
    description = "RSI over trailing 14 bars"
    higher_is_better = False   # overbought territory = lower expected return

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
