"""
market_behavior/model/candle.py
CandleBar — 标准化K线对象
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from ..constant import BoardType


@dataclass
class CandleBar:
    """标准化K线对象，由 CandleEngine 解析生成。"""

    # ── 基础字段 ──────────────────────────────────────────────────────
    symbol:     str
    dt:         datetime
    open:       float
    high:       float
    low:        float
    close:      float
    volume:     float
    turnover:   float = 0.0          # 成交额
    turnover_rate: float = 0.0       # 换手率（%）
    board:      BoardType = BoardType.MAIN

    # ── 派生字段（CandleEngine.parse() 填充）────────────────────────
    prev_close: float = 0.0          # 昨收（用于涨跌幅计算）

    # 涨跌幅
    change_pct: float = 0.0          # (close - prev_close) / prev_close * 100

    # 实体
    body:       float = 0.0          # abs(close - open)
    body_pct:   float = 0.0          # body / prev_close * 100
    body_ratio: float = 0.0          # body / (high - low)，实体占振幅比

    # 影线
    upper_shadow:       float = 0.0  # high - max(open, close)
    lower_shadow:       float = 0.0  # min(open, close) - low
    upper_shadow_ratio: float = 0.0  # upper_shadow / (high - low)
    lower_shadow_ratio: float = 0.0  # lower_shadow / (high - low)

    # 振幅
    amplitude:  float = 0.0          # (high - low) / prev_close * 100

    # 方向
    is_yang:    bool  = False         # close >= open
    is_yin:     bool  = False         # close < open

    # 涨跌停标记（由 LimitRuleEngine 填充）
    is_limit_up:   bool = False
    is_limit_down: bool = False
    limit_pct:     float = 10.0      # 该板块当日涨跌停幅度

    def to_dict(self) -> dict:
        return {
            "symbol":             self.symbol,
            "dt":                 str(self.dt)[:19],
            "open":               self.open,
            "high":               self.high,
            "low":                self.low,
            "close":              self.close,
            "volume":             self.volume,
            "change_pct":         round(self.change_pct, 4),
            "body_pct":           round(self.body_pct, 4),
            "body_ratio":         round(self.body_ratio, 4),
            "upper_shadow_ratio": round(self.upper_shadow_ratio, 4),
            "lower_shadow_ratio": round(self.lower_shadow_ratio, 4),
            "amplitude":          round(self.amplitude, 4),
            "is_yang":            self.is_yang,
            "is_limit_up":        self.is_limit_up,
            "is_limit_down":      self.is_limit_down,
        }
