"""
BacktestParameter

统一管理一次批量回测的全局参数。
字段与 BacktestingEngine.set_parameters() 完全对齐（vnpy_ctastrategy 4.4.0）。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from vnpy.trader.constant import Interval
from vnpy_ctastrategy.backtesting import BacktestingMode


@dataclass
class BacktestParameter:
    """
    全局回测参数，作为批量回测的唯一配置入口。

    所有字段直接对应 BacktestingEngine.set_parameters() 的参数签名，
    保证 Worker 透传时不会出现字段不匹配。
    """

    # ---------- 时间范围 ----------
    start: datetime
    end: datetime

    # ---------- 合约规格 ----------
    interval: Interval = Interval.DAILY

    # ---------- 资金与成本 ----------
    capital: int = 1_000_000
    rate: float = 1e-4          # 手续费率（双边）
    slippage: float = 0.0       # 滑点（元/股）
    size: float = 1.0           # 合约乘数（股票为1）
    pricetick: float = 0.01     # 最小价格变动

    # ---------- 风险参数 ----------
    risk_free: float = 0.03     # 无风险利率（年化，用于 Sharpe 计算）
    annual_days: int = 240      # 年化交易日数
    half_life: int = 120        # EWM Sharpe 半衰期

    # ---------- 回测模式 ----------
    mode: BacktestingMode = BacktestingMode.BAR

    # ---------- 策略参数 ----------
    strategy_setting: dict[str, Any] = field(default_factory=dict)

    def to_engine_kwargs(self, vt_symbol: str) -> dict[str, Any]:
        """
        将参数转换为 BacktestingEngine.set_parameters() 所需的 kwargs。

        :param vt_symbol: 单只股票的 vt_symbol，由 BacktestTask 提供。
        :return: 可直接 **解包 传入 set_parameters() 的字典。
        """
        return {
            "vt_symbol": vt_symbol,
            "interval": self.interval,
            "start": self.start,
            "end": self.end,
            "rate": self.rate,
            "slippage": self.slippage,
            "size": self.size,
            "pricetick": self.pricetick,
            "capital": self.capital,
            "mode": self.mode,
            "risk_free": self.risk_free,
            "annual_days": self.annual_days,
            "half_life": self.half_life,
        }

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise ValueError(
                f"start ({self.start}) 必须早于 end ({self.end})"
            )
        if self.capital <= 0:
            raise ValueError(f"capital 必须大于 0，当前值：{self.capital}")
        if self.rate < 0:
            raise ValueError(f"rate 不能为负数，当前值：{self.rate}")
