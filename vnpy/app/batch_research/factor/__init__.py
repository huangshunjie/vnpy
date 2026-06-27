"""factor sub-package: multi-factor cross-sectional research."""

from .factor_engine import FactorEngine
from .factor_template import (
    FactorTemplate,
    ResultFactor,
    BarFactor,
    SharpeRatioFactor,
    TotalReturnFactor,
    AnnualReturnFactor,
    MaxDrawdownFactor,
    CalmarRatioFactor,
    ReturnDrawdownRatioFactor,
    WinRateFactor,
    TradingFrequencyFactor,
    EwmSharpeFactor,
    ProfitFactorFactor,
    PriceMomentumFactor,
    VolatilityFactor,
    RSIFactor,
)

__all__ = [
    "FactorEngine",
    "FactorTemplate",
    "ResultFactor",
    "BarFactor",
    "SharpeRatioFactor",
    "TotalReturnFactor",
    "AnnualReturnFactor",
    "MaxDrawdownFactor",
    "CalmarRatioFactor",
    "ReturnDrawdownRatioFactor",
    "WinRateFactor",
    "TradingFrequencyFactor",
    "EwmSharpeFactor",
    "ProfitFactorFactor",
    "PriceMomentumFactor",
    "VolatilityFactor",
    "RSIFactor",
]
