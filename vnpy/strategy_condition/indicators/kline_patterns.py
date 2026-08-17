"""
strategy_condition/indicators/kline_patterns.py
K线形态升级：阴线、阳线、缩量阴线、放量阴线、长下影、十字星、大阳线、涨停K线、K线组合
"""
from __future__ import annotations
from typing import List, Tuple


def _calc_vol_ma(volumes: List[float], period: int = 5) -> float:
    if len(volumes) < period:
        return 0.0
    return sum(volumes[-period:]) / period


def check_kline_yin(closes, opens) -> Tuple[bool, float]:
    """当日阴线: close< open"""
    if len(closes) == 0 or len(opens) == 0:
        return False, 0.0
    passed = bool(closes[-1] < opens[-1])
    return passed, 1.0 if passed else 0.0


def check_kline_yang(closes, opens) -> Tuple[bool, float]:
    """当日阳线: close > open"""
    if len(closes) == 0 or len(opens) == 0:
        return False, 0.0
    passed = bool(closes[-1] > opens[-1])
    return passed, 1.0 if passed else 0.0


def check_kline_shrink_yin(closes: List[float], opens: List[float],
                           volumes: List[float],
                           vol_period: int = 5,
                           max_vol_ratio: float = 1.0) -> Tuple[bool, float]:
    """
    缩量阴线: close < open 且 volume < MA(volume, vol_period) * max_vol_ratio
    
    参数:
        vol_period: 均量周期(默认5)
        max_vol_ratio: 缩量比例阈值(默认1.0)，当日量/均量上限
    """
    if len(closes) == 0 or len(opens) == 0 or len(volumes) < vol_period:
        return False, 0.0
    is_yin = closes[-1] < opens[-1]
    vol_ma = _calc_vol_ma(volumes[:-1], vol_period) if len(volumes) > vol_period else _calc_vol_ma(volumes, vol_period)
    if vol_ma <= 0:
        return False, 0.0
    vol_ratio = volumes[-1] / vol_ma
    is_shrink = vol_ratio < max_vol_ratio
    passed = is_yin and is_shrink
    # score: 缩量越明显分数越高
    score = (1.0 - vol_ratio / max_vol_ratio) if passed else 0.0
    return passed, min(max(score, 0.0), 1.0)


def check_kline_volyin(closes: List[float], opens: List[float],
                        volumes: List[float],
                        vol_period: int = 5,
                        min_vol_ratio: float = 1.5) -> Tuple[bool, float]:
    """
    放量阴线: close < open 且 volume > MA(volume, vol_period) * min_vol_ratio
    用于过滤（返回True表示出现放量阴线，可能需要回避）
    """
    if len(closes) == 0 or len(opens) == 0 or len(volumes) < vol_period:
        return False, 0.0
    is_yin = closes[-1] < opens[-1]
    vol_ma = _calc_vol_ma(volumes[:-1], vol_period) if len(volumes) > vol_period else _calc_vol_ma(volumes, vol_period)
    if vol_ma <= 0:
        return False, 0.0
    ratio = volumes[-1] / vol_ma
    passed = is_yin and ratio >= min_vol_ratio
    score = min(ratio / (min_vol_ratio * 2.0), 1.0) if passed else 0.0
    return passed, score


def check_kline_long_lower(closes: List[float], opens: List[float],
                           highs: List[float], lows: List[float],
                           min_ratio: float = 2.0) -> Tuple[bool, float]:
    """
    长下影线: 下影长度 >= 实体长度 * min_ratio
    下影 = min(open, close) - low
    实体 = abs(close - open)
    """
    if len(closes) == 0 or len(opens) == 0 or len(highs) == 0 or len(lows) == 0:
        return False, 0.0
    c, o, h, l = closes[-1], opens[-1], highs[-1], lows[-1]
    body = abs(c - o)
    lower_shadow = min(c, o) - l
    if body <= 0:
        # 十字星情况，视为满足（下影存在即可）
        passed = lower_shadow > (h - l) * 0.3
        return passed, 0.8 if passed else 0.0
    ratio = lower_shadow / body
    passed = ratio >= min_ratio and lower_shadow > 0
    score = min(ratio / (min_ratio * 2.0), 1.0) if passed else 0.0
    return passed, score


def check_kline_doji(closes: List[float], opens: List[float],
                     highs: List[float], lows: List[float],
                     max_body_ratio: float = 0.1) -> Tuple[bool, float]:
    """
    十字星: 实体 / 总振幅 <= max_body_ratio
    """
    if len(closes) == 0 or len(opens) == 0 or len(highs) == 0 or len(lows) == 0:
        return False, 0.0
    c, o, h, l = closes[-1], opens[-1], highs[-1], lows[-1]
    amplitude = h - l
    if amplitude <= 0:
        return False, 0.0
    body = abs(c - o)
    ratio = body / amplitude
    passed = ratio <= max_body_ratio
    score = (1.0 - ratio / max_body_ratio) if passed else 0.0
    return passed, min(max(score, 0.0), 1.0)


def check_kline_big_yang(closes: List[float], opens: List[float],
                         min_pct: float = 5.0) -> Tuple[bool, float]:
    """
    大阳线(单根): (close - open) / open >= min_pct%
    """
    if len(closes) == 0 or len(opens) == 0:
        return False, 0.0
    o = opens[-1]
    if o <= 0:
        return False, 0.0
    chg = (closes[-1] - o) / o * 100.0
    passed = chg >= min_pct
    score = min(chg / (min_pct * 2.0), 1.0) if passed else 0.0
    return passed, score


def check_kline_limit_up(closes: List[float], prev_closes: List[float]) -> Tuple[bool, float]:
    """
    涨停K线: (close - prev_close) / prev_close >= 9.5%
    """
    if len(closes) < 1 or len(prev_closes) < 1:
        return False, 0.0
    # prev_closes[-1]即为前一日收盘
    if len(closes) < 2:
        return False, 0.0
    prev = closes[-2]
    if prev <= 0:
        return False, 0.0
    chg = (closes[-1] - prev) / prev * 100.0
    passed = chg >= 9.5
    return passed, 1.0 if passed else 0.0


def check_kline_combo(closes: List[float], opens: List[float],
                      volumes: List[float],
                      combo_type: str = "shrink_yin_2") -> Tuple[bool, float]:
    """
    K线组合判断：
    - shrink_yin_2: 连续2根缩量阴线
    - yang_yin_yang: 阳-阴-阳组合(看涨吞没变体)
    """
    if len(closes) < 3 or len(opens) < 3 or len(volumes) < 3:
        return False, 0.0

    if combo_type == "shrink_yin_2":
        # 最后两根都是缩量阴线
        vol_ma = sum(volumes[-5:-2]) / 3 if len(volumes) >= 5 else sum(volumes[:-2]) / max(len(volumes) - 2, 1)
        yin1 = closes[-2] < opens[-2] and volumes[-2] < vol_ma
        yin2 = closes[-1] < opens[-1] and volumes[-1] < vol_ma
        passed = yin1 and yin2
        return passed, 1.0 if passed else 0.0

    elif combo_type == "yang_yin_yang":
        # 阳-阴-阳
        yang1 = closes[-3] > opens[-3]
        yin = closes[-2] < opens[-2]
        yang2 = closes[-1] > opens[-1]
        passed = yang1 and yin and yang2
        return passed, 1.0 if passed else 0.0

    return False, 0.0