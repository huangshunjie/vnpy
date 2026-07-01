"""
execution_engine/engine/slippage_engine.py

SlippageEngine — 滑点模型（Phase 2 实现）。

支持三种滑点模型：
  1. FIXED      : 固定 Tick 数滑点
                  fill_price = signal_price ± tick_size × ticks
  2. PERCENTAGE : 百分比滑点
                  fill_price = signal_price × (1 ± rate)
  3. VOLATILITY : 波动率自适应滑点（简化版）
                  fill_price = signal_price × (1 ± vol_factor × daily_vol)

设计原则：
  - 纯函数风格，无状态（配置参数通过 SlippageConfig 传入）
  - 做多（LONG）方向：成交价高于信号价（不利滑点为正）
  - 做空（SHORT）方向：成交价低于信号价（不利滑点为负）
  - 所有模型支持 seed 参数保证回测可复现
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from ..constant import SlippageModel


@dataclass
class SlippageConfig:
    """滑点模型配置。"""
    model:       SlippageModel = SlippageModel.FIXED

    # FIXED 模型参数
    tick_size:   float = 0.01       # 最小变动单位
    ticks:       int   = 1          # 固定滑点 Tick 数

    # PERCENTAGE 模型参数
    rate:        float = 0.0002     # 0.02% 百分比滑点

    # VOLATILITY 模型参数
    vol_factor:  float = 0.1        # 波动率系数（滑点 = vol_factor × daily_vol）
    daily_vol:   float = 0.015      # 日波动率（默认 1.5%，可由行情数据更新）

    # 随机扰动：给滑点加入 ±noise 比例的随机噪声（模拟真实市场不确定性）
    noise_ratio: float = 0.2        # 噪声幅度比例（相对于基础滑点）
    random_seed: int | None = None  # 设置后回测可复现


class SlippageEngine:
    """
    滑点计算引擎（无状态，纯函数风格）。

    使用方式：
        engine = SlippageEngine(config)
        fill_price = engine.apply(signal_price, direction="LONG")
    """

    def __init__(self, config: SlippageConfig | None = None) -> None:
        self.config = config or SlippageConfig()
        self._rng   = random.Random(self.config.random_seed)

    def apply(
        self,
        signal_price: float,
        direction: str,
        volume: float = 1.0,
    ) -> float:
        """
        对信号价格施加滑点，返回模拟成交价。

        Parameters
        ----------
        signal_price : 信号触发时的参考价格
        direction    : "LONG"（做多）或 "SHORT"（做空）
        volume       : 成交数量（VOLATILITY 模型中大单滑点更大）

        Returns
        -------
        float  施加滑点后的成交价格
        """
        if signal_price <= 0:
            return signal_price

        model = self.config.model

        if model == SlippageModel.FIXED:
            base_slip = self._fixed_slippage()
        elif model == SlippageModel.PERCENTAGE:
            base_slip = self._pct_slippage(signal_price)
        elif model == SlippageModel.VOLATILITY:
            base_slip = self._vol_slippage(signal_price, volume)
        else:
            base_slip = 0.0

        # 加入随机噪声
        if self.config.noise_ratio > 0 and base_slip > 0:
            noise = self._rng.uniform(
                -self.config.noise_ratio,
                 self.config.noise_ratio,
            )
            base_slip = base_slip * (1.0 + noise)

        # 方向调整：LONG 成交价更高（不利滑点），SHORT 成交价更低
        if direction == "LONG":
            fill_price = signal_price + base_slip
        else:
            fill_price = signal_price - base_slip

        return max(fill_price, self.config.tick_size)  # 价格不能为负

    def compute_slippage(
        self,
        signal_price: float,
        fill_price: float,
        direction: str,
    ) -> tuple[float, float]:
        """
        给定信号价和成交价，计算滑点绝对值和百分比。

        Returns
        -------
        (slippage_abs, slippage_pct)
          slippage_abs > 0 表示不利滑点（LONG 成交价高于信号 / SHORT 成交价低于信号）
        """
        if direction == "LONG":
            slip = fill_price - signal_price
        else:
            slip = signal_price - fill_price

        slip_pct = slip / signal_price if signal_price > 0 else 0.0
        return slip, slip_pct

    def update_volatility(self, daily_vol: float) -> None:
        """动态更新日波动率（供 dispatcher 在行情更新时调用）。"""
        if daily_vol > 0:
            self.config.daily_vol = daily_vol

    def set_config(self, config: SlippageConfig) -> None:
        """替换滑点配置（UI 修改后调用）。"""
        self.config = config
        self._rng   = random.Random(config.random_seed)

    # ------------------------------------------------------------------ #
    #  各模型内部计算
    # ------------------------------------------------------------------ #

    def _fixed_slippage(self) -> float:
        """固定 Tick 数滑点。"""
        return self.config.tick_size * self.config.ticks

    def _pct_slippage(self, signal_price: float) -> float:
        """百分比滑点。"""
        return signal_price * self.config.rate

    def _vol_slippage(self, signal_price: float, volume: float) -> float:
        """
        波动率自适应滑点（简化版）。

        基础公式：slip = signal_price × vol_factor × daily_vol
        大单额外冲击：impact = sqrt(volume / avg_daily_volume)（此处简化为 1）
        """
        base = signal_price * self.config.vol_factor * self.config.daily_vol
        # 简化冲击项：对量级 > 1 的订单轻微增大滑点
        vol_impact = math.sqrt(max(volume, 1.0)) / math.sqrt(max(volume, 1.0) + 10.0)
        return base * (1.0 + vol_impact * 0.5)
