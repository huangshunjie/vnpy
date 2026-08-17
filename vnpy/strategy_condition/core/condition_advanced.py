"""
strategy_condition/core/condition_advanced.py
新增条件工厂函数：强势股、偏离、K线升级、成交量升级、回调升级、趋势升级、市场环境、评分节点
"""
from __future__ import annotations

from .condition import Condition
from ..constant import ConditionCategory, ConditionIndicator


# === 强势股条件 ===

def cond_strength_returnn(n=20, min_return=20.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.STRENGTH, ConditionIndicator.STRENGTH_RETURN_N,
                     {"n": n, "min_return": min_return},
                     weight, f"{n}日涨幅>={min_return}%")


def cond_strength_limit_up_count(n=20, min_count=1, weight=1.0) -> Condition:
    return Condition(ConditionCategory.STRENGTH, ConditionIndicator.STRENGTH_LIMIT_UP_COUNT,
                     {"n": n, "min_count": min_count},
                     weight, f"{n}日涨停>={min_count}次")


def cond_strength_big_yang_count(n=20, min_count=2, min_pct=5.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.STRENGTH, ConditionIndicator.STRENGTH_BIG_YANG_COUNT,
                     {"n": n, "min_count": min_count, "min_pct": min_pct},
                     weight, f"{n}日大阳>={min_count}次")


def cond_strength_vol_break(n=20, vol_ratio=2.0, price_pct=3.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.STRENGTH, ConditionIndicator.STRENGTH_VOL_BREAK,
                     {"n": n, "vol_ratio": vol_ratio, "price_pct": price_pct},
                     weight, f"{n}日放量突破")


def cond_strength_score(n=20, min_score=0.4, weight=1.0) -> Condition:
    return Condition(ConditionCategory.STRENGTH, ConditionIndicator.STRENGTH_SCORE,
                     {"n": n, "min_score": min_score},
                     weight, f"强势股评分>={min_score}")


# === 均线偏离条件 ===

def cond_dev_ma5(max_dev_pct=5.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.DEVIATION, ConditionIndicator.DEV_MA5,
                     {"max_dev_pct": max_dev_pct},
                     weight, f"MA5乖离<={max_dev_pct}%")


def cond_dev_ma10(max_dev_pct=5.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.DEVIATION, ConditionIndicator.DEV_MA10,
                     {"max_dev_pct": max_dev_pct},
                     weight, f"MA10乖离<={max_dev_pct}%")


def cond_dev_ma20(max_dev_pct=8.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.DEVIATION, ConditionIndicator.DEV_MA20,
                     {"max_dev_pct": max_dev_pct},
                     weight, f"MA20乖离<={max_dev_pct}%")


def cond_dev_ma10_ma20(max_distance_pct=5.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.DEVIATION, ConditionIndicator.DEV_MA10_MA20,
                     {"max_distance_pct": max_distance_pct},
                     weight, f"MA10-MA20距离<={max_distance_pct}%")


def cond_dev_overbought(ma_period=10, max_above_pct=10.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.DEVIATION, ConditionIndicator.DEV_OVERBOUGHT,
                     {"ma_period": ma_period, "max_above_pct": max_above_pct},
                     weight, f"超涨过滤(MA{ma_period}上方<={max_above_pct}%)")


# === K线升级条件 ===

def cond_kline_yin(weight=1.0) -> Condition:
    return Condition(ConditionCategory.KLINE, ConditionIndicator.KLINE_YIN,
                     {}, weight, "阴线")


def cond_kline_yang(weight=1.0) -> Condition:
    return Condition(ConditionCategory.KLINE, ConditionIndicator.KLINE_YANG,
                     {}, weight, "阳线")


def cond_kline_shrink_yin(vol_period=5, vol_ratio=0.8, weight=1.0) -> Condition:
    return Condition(ConditionCategory.KLINE, ConditionIndicator.KLINE_SHRINK_YIN,
                     {"vol_period": vol_period, "vol_ratio": vol_ratio},
                     weight, f"缩量阴线(量比<{vol_ratio})")


def cond_kline_volyin(vol_period=5, min_vol_ratio=1.5, weight=1.0) -> Condition:
    return Condition(ConditionCategory.KLINE, ConditionIndicator.KLINE_VOL_YIN,
                     {"vol_period": vol_period, "min_vol_ratio": min_vol_ratio},
                     weight, "放量阴线")


def cond_kline_long_lower(min_ratio=2.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.KLINE, ConditionIndicator.KLINE_LONG_LOWER,
                     {"min_ratio": min_ratio},
                     weight, "长下影线")


def cond_kline_doji(max_body_ratio=0.1, weight=1.0) -> Condition:
    return Condition(ConditionCategory.KLINE, ConditionIndicator.KLINE_DOJI,
                     {"max_body_ratio": max_body_ratio},
                     weight, "十字星")


def cond_kline_big_yang(min_pct=5.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.KLINE, ConditionIndicator.KLINE_BIG_YANG,
                     {"min_pct": min_pct},
                     weight, f"大阳线>={min_pct}%")


def cond_kline_limit_up(weight=1.0) -> Condition:
    return Condition(ConditionCategory.KLINE, ConditionIndicator.KLINE_LIMIT_UP,
                     {}, weight, "涨停K线")


# === 成交量升级条件 ===

def cond_volume_layer(up_window=10, dn_window=5, max_ratio=0.6, weight=1.0) -> Condition:
    return Condition(ConditionCategory.VOLUME, ConditionIndicator.VOLUME_LAYER,
                     {"up_window": up_window, "dn_window": dn_window,
                      "max_ratio": max_ratio},
                     weight, f"分层量能(调整<上涨*{max_ratio})")


def cond_volume_upphase(n=20, min_ratio=1.3, weight=1.0) -> Condition:
    return Condition(ConditionCategory.VOLUME, ConditionIndicator.VOLUME_UP_PHASE,
                     {"n": n, "min_ratio": min_ratio},
                     weight, f"上涨阶段量能>={min_ratio}x")


def cond_volume_yin_filter(vol_period=5, min_vol_ratio=1.5, weight=1.0) -> Condition:
    return Condition(ConditionCategory.VOLUME, ConditionIndicator.VOLUME_YIN_FILTER,
                     {"vol_period": vol_period, "min_vol_ratio": min_vol_ratio},
                     weight, "无放量阴线")


def cond_fund_intensity(n=10, min_score=0.5, weight=1.0) -> Condition:
    return Condition(ConditionCategory.VOLUME, ConditionIndicator.FUND_INTENSITY,
                     {"n": n, "min_score": min_score},
                     weight, f"资金介入强度>={min_score}")


# === 回调升级条件 ===

def cond_pullback_to_ma5(tol_pct=2.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.PULLBACK, ConditionIndicator.PULLBACK_TO_MA5,
                     {"ma_period": 5, "tol_pct": tol_pct},
                     weight, f"回踩MA5({tol_pct}%)")


def cond_pullback_to_ma10(tol_pct=2.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.PULLBACK, ConditionIndicator.PULLBACK_TO_MA10,
                     {"ma_period": 10, "tol_pct": tol_pct},
                     weight, f"回踩MA10({tol_pct}%)")


def cond_pullback_to_ma20(tol_pct=3.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.PULLBACK, ConditionIndicator.PULLBACK_TO_MA20,
                     {"ma_period": 20, "tol_pct": tol_pct},
                     weight, f"回踩MA20({tol_pct}%)")


def cond_pullback_to_ma30(tol_pct=3.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.PULLBACK, ConditionIndicator.PULLBACK_TO_MA30,
                     {"ma_period": 30, "tol_pct": tol_pct},
                     weight, f"回踩MA30({tol_pct}%)")


def cond_first_pullback(ma_period=10, tol_pct=2.0, lookback=20, weight=1.0) -> Condition:
    return Condition(ConditionCategory.PULLBACK, ConditionIndicator.FIRST_PULLBACK,
                     {"ma_period": ma_period, "tol_pct": tol_pct, "lookback": lookback},
                     weight, f"首次回踩MA{ma_period}")


def cond_shrink_pullback(pullback_days=3, vol_period=10,
                         max_vol_ratio=0.7, weight=1.0) -> Condition:
    return Condition(ConditionCategory.PULLBACK, ConditionIndicator.SHRINK_PULLBACK,
                     {"pullback_days": pullback_days, "vol_period": vol_period,
                      "max_vol_ratio": max_vol_ratio},
                     weight, "缩量回调")


def cond_strong_pullback_score(ma_period=10, min_score=0.5, weight=1.0) -> Condition:
    return Condition(ConditionCategory.PULLBACK, ConditionIndicator.STRONG_PULLBACK_SCORE,
                     {"ma_period": ma_period, "min_score": min_score},
                     weight, f"强势回调评分>={min_score}")


# === 趋势升级条件 ===

def cond_trend_strength(periods=None, min_score=0.75, weight=1.0) -> Condition:
    return Condition(ConditionCategory.TREND, ConditionIndicator.TREND_STRENGTH,
                     {"periods": periods or [5, 10, 20, 30], "min_score": min_score},
                     weight, "均线趋势强度")


def cond_price_above_ma(ma_period=20, weight=1.0) -> Condition:
    return Condition(ConditionCategory.TREND, ConditionIndicator.PRICE_ABOVE_MA,
                     {"ma_period": ma_period},
                     weight, f"价格站上MA{ma_period}")


def cond_trend_days(ma_period=20, min_days=5, weight=1.0) -> Condition:
    return Condition(ConditionCategory.TREND, ConditionIndicator.TREND_DAYS,
                     {"ma_period": ma_period, "min_days": min_days},
                     weight, f"趋势持续>={min_days}天")


def cond_trend_intact(ma_period=20, n=10, weight=1.0) -> Condition:
    return Condition(ConditionCategory.TREND, ConditionIndicator.TREND_INTACT,
                     {"ma_period": ma_period, "n": n},
                     weight, f"趋势未破坏(近{n}日)")


def cond_ma_bindong(periods=None, max_spread_pct=2.0, weight=1.0) -> Condition:
    return Condition(ConditionCategory.TREND, ConditionIndicator.MA_BINDONG,
                     {"periods": periods or [5, 10, 20, 30],
                      "max_spread_pct": max_spread_pct},
                     weight, f"均线粘合(<{max_spread_pct}%)")


def cond_trend_score(min_score=0.6, weight=1.0) -> Condition:
    return Condition(ConditionCategory.TREND, ConditionIndicator.TREND_SCORE,
                     {"min_score": min_score},
                     weight, f"趋势评分>={min_score}")


# === 市场环境条件 ===

def cond_market_index_trend(ma_period=20, weight=1.0) -> Condition:
    return Condition(ConditionCategory.MARKET, ConditionIndicator.MARKET_INDEX_TREND,
                     {"ma_period": ma_period},
                     weight, f"指数>MA{ma_period}")


def cond_market_risk(weight=1.0) -> Condition:
    return Condition(ConditionCategory.MARKET, ConditionIndicator.MARKET_RISK,
                     {}, weight, "市场风险安全")


# === 综合评分条件 ===

def cond_score_node(weights=None, min_score=80.0, weight=1.0) -> Condition:
    """
    综合评分节点：
    weights: {"trend": 25, "strength": 20, "volume": 20,
              "pullback": 20, "kline": 10, "market": 5}
    min_score: 满分100，达到该分数则触发
    """
    default_weights = {
        "trend": 25, "strength": 20, "volume": 20,
        "pullback": 20, "kline": 10, "market": 5
    }
    return Condition(ConditionCategory.SCORE, ConditionIndicator.SCORE_NODE,
                     {"weights": weights or default_weights,
                      "min_score": min_score},
                     weight, f"综合评分>={min_score}")