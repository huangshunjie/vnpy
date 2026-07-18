"""
strategy_condition/core/condition.py
条件抽象基类 + 所有具体条件工厂函数
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict

from ..constant import ConditionCategory, ConditionIndicator


@dataclass
class Condition:
    """条件叶节点。评估逻辑由 condition_engine.py 负责，此处只做数据建模。"""
    category:  ConditionCategory
    indicator: ConditionIndicator
    params:    Dict[str, Any] = field(default_factory=dict)
    weight:    float          = 1.0
    label:     str            = ""
    enabled:   bool           = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category":  self.category.value,
            "indicator": self.indicator.value,
            "params":    self.params,
            "weight":    self.weight,
            "label":     self.label,
            "enabled":   self.enabled,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Condition":
        return cls(
            category=  ConditionCategory(d["category"]),
            indicator= ConditionIndicator(d["indicator"]),
            params=    d.get("params", {}),
            weight=    d.get("weight", 1.0),
            label=     d.get("label", ""),
            enabled=   d.get("enabled", True),
        )

    def display_name(self) -> str:
        return self.label if self.label else self.indicator.value

    def __repr__(self) -> str:
        return (f"Condition({self.indicator.value}, "
                f"params={self.params}, w={self.weight})")


# ── 趋势条件 ──────────────────────────────────────────────────────────

def cond_ma_slope(ma_period=20, slope_window=10,
                  min_slope=0.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.TREND, ConditionIndicator.MA_SLOPE,
                     {"ma_period": ma_period, "slope_window": slope_window,
                      "min_slope": min_slope},
                     weight, f"MA{ma_period}斜率向上")


def cond_weekly_ma_slope(ma_period=13, slope_window=5,
                         min_slope=0.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.TREND, ConditionIndicator.WEEKLY_MA_SLOPE,
                     {"ma_period": ma_period, "slope_window": slope_window,
                      "min_slope": min_slope},
                     weight, f"{ma_period}周均线向上")


def cond_ma_alignment(periods=None, weight=1.0) -> Condition:
    return Condition(ConditionCategory.TREND, ConditionIndicator.MA_ALIGNMENT,
                     {"periods": periods or [5, 10, 20, 60]},
                     weight, "均线多头排列")


def cond_new_high_n(n=20, weight=1.0) -> Condition:
    return Condition(ConditionCategory.TREND, ConditionIndicator.NEW_HIGH_N,
                     {"n": n}, weight, f"{n}日新高突破")


# ── 回调条件 ──────────────────────────────────────────────────────────

def cond_pullback_pct(window=10, min_drop=-8.0,
                      max_drop=-2.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.PULLBACK, ConditionIndicator.PULLBACK_PCT,
                     {"window": window, "min_drop": min_drop, "max_drop": max_drop},
                     weight, f"跌幅回调{min_drop}%~{max_drop}%")


def cond_pullback_from_high(window=20, min_drop=-10.0,
                             max_drop=-2.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.PULLBACK, ConditionIndicator.PULLBACK_FROM_HIGH,
                     {"window": window, "min_drop": min_drop, "max_drop": max_drop},
                     weight, f"从高点回撤{min_drop}%~{max_drop}%")


def cond_pullback_to_ma(ma_period=20, tol_pct=2.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.PULLBACK, ConditionIndicator.PULLBACK_TO_MA,
                     {"ma_period": ma_period, "ma_tol_pct": tol_pct},
                     weight, f"回踩MA{ma_period}")


# ── 动量条件 ──────────────────────────────────────────────────────────

def cond_macd_golden(fast=12, slow=26, signal=9, weight=1.0) -> Condition:
    return Condition(ConditionCategory.MOMENTUM, ConditionIndicator.MACD_GOLDEN,
                     {"fast": fast, "slow": slow, "signal": signal},
                     weight, "MACD 金叉")


def cond_macd_death(fast=12, slow=26, signal=9, weight=1.0) -> Condition:
    return Condition(ConditionCategory.MOMENTUM, ConditionIndicator.MACD_DEATH,
                     {"fast": fast, "slow": slow, "signal": signal},
                     weight, "MACD 死叉")


def cond_rsi_range(period=14, min_rsi=30.0, max_rsi=70.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.MOMENTUM, ConditionIndicator.RSI_RANGE,
                     {"period": period, "min": min_rsi, "max": max_rsi},
                     weight, f"RSI({period}) {min_rsi}~{max_rsi}")


def cond_return_n_days(n=10, min_return=5.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.MOMENTUM, ConditionIndicator.RETURN_N_DAYS,
                     {"n": n, "min_return": min_return},
                     weight, f"{n}日收益>={min_return}%")


# ── 成交量条件 ────────────────────────────────────────────────────────

def cond_volume_ratio(period=20, min_ratio=1.5, weight=1.0) -> Condition:
    return Condition(ConditionCategory.VOLUME, ConditionIndicator.VOLUME_RATIO,
                     {"period": period, "min_ratio": min_ratio},
                     weight, f"量比>={min_ratio}x")


def cond_volume_price_up(period=20, min_ratio=1.5, min_chg=1.0,
                          weight=1.0) -> Condition:
    return Condition(ConditionCategory.VOLUME, ConditionIndicator.VOLUME_PRICE_UP,
                     {"period": period, "min_ratio": min_ratio, "min_chg": min_chg},
                     weight, f"放量上涨>{min_chg}%")


def cond_volume_shrink(period=20, max_ratio=0.7, weight=1.0) -> Condition:
    return Condition(ConditionCategory.VOLUME, ConditionIndicator.VOLUME_SHRINK,
                     {"period": period, "max_ratio": max_ratio},
                     weight, f"缩量<={max_ratio}x")


# ── K线行为条件 ───────────────────────────────────────────────────────

def cond_continuous_rise(window=10, min_days=3, weight=1.0) -> Condition:
    return Condition(ConditionCategory.KLINE, ConditionIndicator.CONTINUOUS_RISE,
                     {"window": window, "min_days": min_days},
                     weight, f"近{window}日连涨>={min_days}天")


def cond_limit_up_count(window=20, min_count=1, weight=1.0) -> Condition:
    return Condition(ConditionCategory.KLINE, ConditionIndicator.LIMIT_UP_COUNT,
                     {"window": window, "min_count": min_count},
                     weight, f"近{window}日涨停>={min_count}次")


def cond_big_yang_count(window=20, min_count=2, min_pct=3.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.KLINE, ConditionIndicator.BIG_YANG_COUNT,
                     {"window": window, "min_count": min_count, "min_pct": min_pct},
                     weight, f"近{window}日大阳>={min_count}次")


def cond_kline_strength(min_score=0.4, weight=1.0) -> Condition:
    return Condition(ConditionCategory.KLINE, ConditionIndicator.KLINE_STRENGTH,
                     {"min_score": min_score},
                     weight, f"K线强度>={min_score}")


# ── 波动条件 ──────────────────────────────────────────────────────────

def cond_atr_ratio(period=14, min_ratio=1.0, max_ratio=9999.0,
                   weight=1.0) -> Condition:
    return Condition(ConditionCategory.VOLATILITY, ConditionIndicator.ATR_RATIO,
                     {"period": period, "min": min_ratio, "max": max_ratio},
                     weight, f"ATR振幅{min_ratio}%~{max_ratio}%")


def cond_boll_width(period=20, std_mult=2.0, min_width=0.05,
                    max_width=9999.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.VOLATILITY, ConditionIndicator.BOLL_WIDTH,
                     {"period": period, "std_mult": std_mult,
                      "min": min_width, "max": max_width},
                     weight, f"布林带宽>={min_width}")


# ── 卖出条件 ──────────────────────────────────────────────────────────

def cond_stop_loss(pct=8.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.EXIT, ConditionIndicator.STOP_LOSS,
                     {"pct": pct}, weight, f"止损-{pct}%")


def cond_take_profit(pct=15.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.EXIT, ConditionIndicator.TAKE_PROFIT,
                     {"pct": pct}, weight, f"止盈+{pct}%")


def cond_trailing_stop(take_profit=15.0, trail_drawdown=10.0,
                        weight=1.0) -> Condition:
    return Condition(ConditionCategory.EXIT, ConditionIndicator.TRAILING_STOP,
                     {"take_profit": take_profit, "trail_drawdown": trail_drawdown},
                     weight, f"追踪止盈+{take_profit}%回撤{trail_drawdown}%")


def cond_max_hold_days(days=60, weight=1.0) -> Condition:
    return Condition(ConditionCategory.EXIT, ConditionIndicator.MAX_HOLD_DAYS,
                     {"days": days}, weight, f"持仓>={days}天")


def cond_ma_break_down(ma_period=20, weight=1.0) -> Condition:
    return Condition(ConditionCategory.EXIT, ConditionIndicator.MA_BREAK_DOWN,
                     {"ma_period": ma_period}, weight, f"跌破MA{ma_period}")


def cond_macd_death_sell(fast=12, slow=26, signal=9, weight=1.0) -> Condition:
    return Condition(ConditionCategory.EXIT, ConditionIndicator.MACD_DEATH_SELL,
                     {"fast": fast, "slow": slow, "signal": signal},
                     weight, "MACD死叉卖出")


# ── 通用反序列化 ──────────────────────────────────────────────────────

def condition_from_dict(d: dict) -> Condition:
    return Condition.from_dict(d)
