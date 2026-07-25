"""
strategy_condition/indicators/volume_advanced.py
成交量升级：上涨阶段量能、分层量能(VolumeLayerFactor)、缩量回调、
放量阴线过滤、量价背离、成交量趋势、资金介入强度
"""
from __future__ import annotations
from typing import List, Tuple


def _calc_ma(data: List[float], period: int) -> float:
    if len(data) < period:
        return 0.0
    return sum(data[-period:]) / period


def check_volume_upphase(closes: List[float], volumes: List[float],
                          n: int = 20, min_ratio: float = 1.3) -> Tuple[bool, float]:
    """
    上涨阶段量能：上涨日平均成交量 / 下跌日平均成交量 >= min_ratio
    表明资金在上涨时积极参与
    """
    if len(closes) < n + 1 or len(volumes) < n:
        return False, 0.0
    up_vols = []
    dn_vols = []
    for i in range(-n, 0):
        if closes[i] > closes[i - 1]:
            up_vols.append(volumes[len(volumes) + i])
        else:
            dn_vols.append(volumes[len(volumes) + i])
    if not up_vols or not dn_vols:
        return len(up_vols) > 0, 0.5
    avg_up = sum(up_vols) / len(up_vols)
    avg_dn = sum(dn_vols) / len(dn_vols)
    if avg_dn <= 0:
        return True, 1.0
    ratio = avg_up / avg_dn
    passed = ratio >= min_ratio
    score = min(ratio / (min_ratio * 2.0), 1.0) if passed else 0.0
    return passed, score


def check_volume_layer(closes: List[float], volumes: List[float],
                       up_window: int = 10, dn_window: int = 5,
                       max_ratio: float = 0.6) -> Tuple[bool, float]:
    """
    分层量能(VolumeLayerFactor):
    计算上涨阶段平均成交量 vs 调整阶段平均成交量
    判断: 调整量 < 上涨量 * max_ratio

    逻辑：
    - 先找最近上涨阶段(连续上涨或大部分上涨的窗口)的平均量
    - 再看最近调整阶段(最后dn_window根K线)的平均量
    - 如果调整期缩量明显，说明主力未出货
    """
    total_len = up_window + dn_window
    if len(closes) < total_len + 1 or len(volumes) < total_len:
        return False, 0.0

    # 上涨阶段：倒数 dn_window+1 ~ dn_window+up_window 区间
    up_start = -(dn_window + up_window)
    up_end = -dn_window
    up_vols = volumes[up_start:up_end] if up_end != 0 else volumes[up_start:]

    # 调整阶段：最后 dn_window 根
    dn_vols = volumes[-dn_window:]

    avg_up = sum(up_vols) / len(up_vols) if up_vols else 0
    avg_dn = sum(dn_vols) / len(dn_vols) if dn_vols else 0

    if avg_up <= 0:
        return False, 0.0

    ratio = avg_dn / avg_up
    passed = ratio < max_ratio
    # score: ratio越小(缩量越明显)分越高
    score = max(1.0 - ratio / max_ratio, 0.0) if passed else 0.0
    return passed, score


def check_shrink_pullback_vol(closes: List[float], volumes: List[float],
                              pullback_days: int = 5,
                              vol_period: int = 20,
                              max_ratio: float = 0.7) -> Tuple[bool, float]:
    """
    缩量回调(维度)：
    最近pullback_days日平均量 / 过去vol_period日平均量 <= max_ratio
    """
    if len(volumes) < vol_period + pullback_days:
        return False, 0.0
    recent_avg = sum(volumes[-pullback_days:]) / pullback_days
    hist_avg = sum(volumes[-(vol_period + pullback_days):-pullback_days]) / vol_period
    if hist_avg <= 0:
        return False, 0.0
    ratio = recent_avg / hist_avg
    passed = ratio <= max_ratio
    score = max(1.0 - ratio / max_ratio, 0.0) if passed else 0.0
    return passed, score


def check_volume_yin_filter(closes: List[float], opens: List[float],
                            volumes: List[float],
                            vol_period: int = 5,
                            min_vol_ratio: float = 1.5) -> Tuple[bool, float]:
    """
    放量阴线过滤：当日为放量阴线时返回False（用于排除）
    close < open 且 volume > MA(volume) * min_vol_ratio => 危险信号
    返回True = 安全(没有放量阴线), False = 出现放量阴线
    """
    if not closes or not opens or len(volumes) < vol_period + 1:
        return True, 1.0  # 数据不足时默认安全
    is_yin = closes[-1] < opens[-1]
    if not is_yin:
        return True, 1.0  # 不是阴线，安全
    vol_ma = sum(volumes[-(vol_period + 1):-1]) / vol_period
    if vol_ma <= 0:
        return True, 1.0
    ratio = volumes[-1] / vol_ma
    has_volyin = ratio >= min_vol_ratio
    # 返回True表示没有放量阴线（安全）
    passed = not has_volyin
    score = 1.0 if passed else 0.0
    return passed, score


def check_volume_divergence(closes: List[float], volumes: List[float],
                            n: int = 10) -> Tuple[bool, float]:
    """
    量价背离检测：价格创新高但成交量萎缩
    返回True表示存在背离（看跌信号，用于过滤）
    """
    if len(closes) < n * 2 or len(volumes) < n * 2:
        return False, 0.0
    # 前半段vs后半段
    price_first = max(closes[-n * 2:-n])
    price_second = max(closes[-n:])
    vol_first = sum(volumes[-n * 2:-n]) / n
    vol_second = sum(volumes[-n:]) / n

    # 价格新高但量能下降
    price_up = price_second > price_first
    vol_down = vol_second < vol_first * 0.8
    passed = price_up and vol_down
    if not passed:
        return False, 0.0
    score = min((vol_first - vol_second) / vol_first, 1.0)
    return True, max(score, 0.0)


def check_volume_trend(volumes: List[float], n: int = 10,
                       direction: str = "up") -> Tuple[bool, float]:
    """
    成交量趋势：近N日成交量MA是否上升/下降
    direction: "up" 量能放大趋势, "down" 量能缩小趋势
    """
    if len(volumes) < n + 5:
        return False, 0.0
    ma_recent = sum(volumes[-n:]) / n
    ma_prev = sum(volumes[-(n + 5):-5]) / n
    if ma_prev <= 0:
        return False, 0.0
    change = (ma_recent - ma_prev) / ma_prev
    if direction == "up":
        passed = change > 0.1  # 量能增长10%以上
        score = min(change / 0.5, 1.0) if passed else 0.0
    else:
        passed = change < -0.1  # 量能缩小10%以上
        score = min(abs(change) / 0.5, 1.0) if passed else 0.0
    return passed, score


def check_fund_intensity(closes: List[float], volumes: List[float],
                         n: int = 10, min_score: float = 0.5) -> Tuple[bool, float]:
    """
    资金介入强度：综合上涨量能比、量价协同等因素
    score =上涨日量占比 * 上涨日涨幅贡献占比
    """
    if len(closes) < n + 1 or len(volumes) < n:
        return False, 0.0
    up_vol = 0.0
    total_vol = 0.0
    up_chg = 0.0
    total_chg = 0.0
    for i in range(-n, 0):
        v = volumes[len(volumes) + i]
        chg = closes[i] - closes[i - 1]
        total_vol += v
        total_chg += abs(chg)
        if chg > 0:
            up_vol += v
            up_chg += chg
    if total_vol <= 0 or total_chg <= 0:
        return False, 0.0
    vol_ratio = up_vol / total_vol
    chg_ratio = up_chg / total_chg
    score = vol_ratio * chg_ratio * 2.0  # 归一化到0~1附近
    score = min(score, 1.0)
    passed = score >= min_score
    return passed, score if passed else 0.0