"""
factor/builtin_factors.py

内置因子统一入口。

从 factor_template.py 重新导出所有内置因子类，
外部代码只需::

    from vnpy.app.batch_research.factor.builtin_factors import (
        SharpeRatioFactor, CalmarFactor, MomentumFactor, WinRateFactor,
    )

不需要关心内部来自哪个模块。
"""

from .factor_template import (
    # ResultFactor 系列（读 BacktestResult.statistics）
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

    # BarFactor 系列（读 BarData）
    PriceMomentumFactor,
    VolatilityFactor,
    RSIFactor,
)

# 别名：让外部可以用更简短的名字
CalmarFactor     = CalmarRatioFactor
MomentumFactor   = TotalReturnFactor    # 总收益率作为动量近似

#: 开箱即用的推荐四因子组合（均等权重）
DEFAULT_FACTORS: list = [
    SharpeRatioFactor(),
    CalmarRatioFactor(),
    WinRateFactor(),
    TotalReturnFactor(),
]

__all__ = [
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
    "CalmarFactor",
    "MomentumFactor",
    "DEFAULT_FACTORS",
]
