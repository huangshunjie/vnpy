"""
kline_behavior_lab/pattern_classifier.py

K线形态分类器 - 25个常见形态的统一判定接口
多标签模式：一根K线可以同时命中多个形态
"""
from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd


# 形态定义：(特征名, 中文名, 分类)
PATTERN_DEFINITIONS: List[Tuple[str, str, str]] = [
    # 基础方向类
    ("is_green", "阳线", "基础方向"),
    ("is_red", "阴线", "基础方向"),
    ("is_big_green", "大阳线", "基础方向"),
    ("is_big_red", "大阴线", "基础方向"),
    # 影线类
    ("long_upper_shadow", "长上影线", "影线"),
    ("long_lower_shadow", "长下影线", "影线"),
    ("is_hammer", "锤子线", "影线"),
    ("is_shooting_star", "射击之星", "影线"),
    # 特殊形态类
    ("is_doji", "十字星", "特殊形态"),
    ("is_dragonfly_doji", "蜻蜓十字", "特殊形态"),
    ("is_gravestone_doji", "墓碑十字", "特殊形态"),
    ("is_marubozu", "光头光脚", "特殊形态"),
    ("is_spinning_top", "纺锤线", "特殊形态"),
    # 反转组合类
    ("engulfing_bullish", "看涨吞没", "反转组合"),
    ("engulfing_bearish", "看跌吞没", "反转组合"),
    ("morning_star", "早晨之星", "反转组合"),
    ("evening_star", "黄昏之星", "反转组合"),
    ("piercing_line", "刺透形态", "反转组合"),
    ("dark_cloud_cover", "乌云盖顶", "反转组合"),
    # 连续形态类
    ("three_green_soldiers", "三连阳", "连续形态"),
    ("three_red_soldiers", "三连阴", "连续形态"),
    ("rising_three", "上升三法", "连续形态"),
    ("falling_three", "下降三法", "连续形态"),
    # 量价配合类
    ("volume_yang", "放量阳线", "量价配合"),
    ("volume_yin", "放量阴线", "量价配合"),
]


def get_pattern_names() -> List[str]:
    """获取所有形态特征名"""
    return [p[0] for p in PATTERN_DEFINITIONS]


def get_pattern_display_names() -> Dict[str, str]:
    """获取形态名 -> 中文名映射"""
    return {p[0]: p[1] for p in PATTERN_DEFINITIONS}


def get_pattern_categories() -> Dict[str, str]:
    """获取形态名 -> 分类映射"""
    return {p[0]: p[2] for p in PATTERN_DEFINITIONS}


def classify_single_bar(
    o: float, h: float, l: float, c: float, v: float,
    prev_o: float = 0, prev_h: float = 0, prev_l: float = 0,
    prev_c: float = 0, prev_v: float = 0,
    prev2_o: float = 0, prev2_h: float = 0, prev2_l: float = 0,
    prev2_c: float = 0, prev2_v: float = 0,
    vol_ma5: float = 0,
) -> Dict[str, bool]:
    """
    对单根K线（及前2根辅助数据）判定所有25个形态

    Args:
        o, h, l, c, v: 当前K线 OHLCV
        prev_*: 前一根K线数据
        prev2_*: 前两根K线数据
        vol_ma5: 5日成交量均值

    Returns:
        Dict[pattern_name, bool] 各形态是否命中
    """
    results: Dict[str, bool] = {}

    amplitude = h - l
    body = abs(c - o)
    upper_shadow = h - max(c, o)
    lower_shadow = min(c, o) - l

    # 防除零
    safe_amp = amplitude if amplitude > 0 else 1e-10
    safe_body = body if body > 0 else 1e-10
    safe_open = o if o > 0 else 1e-10
    safe_vol_ma = vol_ma5 if vol_ma5 > 0 else 1e-10

    body_ratio = body / safe_amp
    upper_ratio = upper_shadow / safe_amp
    lower_ratio = lower_shadow / safe_amp

    change_pct = (c - o) / safe_open * 100.0

    # ========== 基础方向类 ==========
    results["is_green"] = c > o
    results["is_red"] = c < o
    results["is_big_green"] = change_pct >= 3.0 and body_ratio > 0.6
    results["is_big_red"] = change_pct <= -3.0 and body_ratio > 0.6

    # ========== 影线类 ==========
    results["long_upper_shadow"] = upper_shadow >= safe_body * 2.0
    results["long_lower_shadow"] = lower_shadow >= safe_body * 2.0
    results["is_hammer"] = (
        lower_ratio > 0.4 and upper_ratio < 0.2 and body_ratio < 0.4
    )
    results["is_shooting_star"] = (
        upper_ratio > 0.4 and lower_ratio < 0.2 and body_ratio < 0.4
    )

    # ========== 特殊形态类 ==========
    results["is_doji"] = body_ratio <= 0.1
    results["is_dragonfly_doji"] = (
        body_ratio <= 0.1 and lower_ratio > 0.4 and upper_ratio < 0.1
    )
    results["is_gravestone_doji"] = (
        body_ratio <= 0.1 and upper_ratio > 0.4 and lower_ratio < 0.1
    )
    results["is_marubozu"] = (
        upper_ratio < 0.05 and lower_ratio < 0.05 and body_ratio > 0.9
    )
    results["is_spinning_top"] = (
        body_ratio < 0.3 and upper_ratio > 0.25 and lower_ratio > 0.25
    )

    # ========== 反转组合类（需要前一根/前两根数据） ==========
    prev_body = abs(prev_c - prev_o)
    prev_is_red = prev_c < prev_o
    prev_is_green = prev_c > prev_o

    # 看涨吞没
    results["engulfing_bullish"] = (
        prev_is_red and c > o and
        o <= prev_c and c >= prev_o and body > prev_body
    )
    # 看跌吞没
    results["engulfing_bearish"] = (
        prev_is_green and c < o and
        o >= prev_c and c <= prev_o and body > prev_body
    )

    # 早晨之星（需要前两根）
    prev2_is_red = prev2_c < prev2_o
    prev_is_doji = abs(prev_c - prev_o) / (max(prev_h - prev_l, 1e-10)) <= 0.15
    results["morning_star"] = (
        prev2_is_red and prev_is_doji and c > o and
        c > (prev2_o + prev2_c) / 2
    )
    # 黄昏之星
    prev2_is_green = prev2_c > prev2_o
    results["evening_star"] = (
        prev2_is_green and prev_is_doji and c < o and
        c < (prev2_o + prev2_c) / 2
    )

    # 刺透形态
    prev_mid = (prev_o + prev_c) / 2
    results["piercing_line"] = (
        prev_is_red and c > o and o < prev_c and c > prev_mid
    )
    # 乌云盖顶
    results["dark_cloud_cover"] = (
        prev_is_green and c < o and o > prev_c and c < prev_mid
    )

    # ========== 连续形态类 ==========
    results["three_green_soldiers"] = (
        prev2_c > prev2_o and prev_c > prev_o and c > o
    )
    results["three_red_soldiers"] = (
        prev2_c < prev2_o and prev_c < prev_o and c < o
    )

    # 上升三法（简化：大阳+小阴+大阳）
    prev2_big_green = (prev2_c - prev2_o) / max(prev2_o, 1e-10) * 100 >= 2.0
    prev_small_red = prev_c < prev_o and abs(prev_c - prev_o) / max(prev_o, 1e-10) * 100 < 1.5
    cur_big_green = change_pct >= 2.0
    results["rising_three"] = prev2_big_green and prev_small_red and cur_big_green

    # 下降三法（简化：大阴+小阳+大阴）
    prev2_big_red = (prev2_c - prev2_o) / max(prev2_o, 1e-10) * 100 <= -2.0
    prev_small_green = prev_c > prev_o and abs(prev_c - prev_o) / max(prev_o, 1e-10) * 100 < 1.5
    cur_big_red = change_pct <= -2.0
    results["falling_three"] = prev2_big_red and prev_small_green and cur_big_red

    # ========== 量价配合类 ==========
    vol_ratio = v / safe_vol_ma
    results["volume_yang"] = c > o and vol_ratio >= 1.5
    results["volume_yin"] = c < o and vol_ratio >= 1.5

    return results


def classify_bars_vectorized(df: pd.DataFrame) -> pd.DataFrame:
    """
    向量化批量计算所有形态标签

    Args:
        df: 包含 open, high, low, close, volume 列的DataFrame

    Returns:
        DataFrame，每列为一个形态的 bool 标签
    """
    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    c = df["close"].values
    v = df["volume"].values

    amplitude = h - l
    body = np.abs(c - o)
    upper_shadow = h - np.maximum(c, o)
    lower_shadow = np.minimum(c, o) - l

    safe_amp = np.where(amplitude > 0, amplitude, 1e-10)
    safe_body = np.where(body > 0, body, 1e-10)
    safe_open = np.where(o > 0, o, 1e-10)

    body_ratio = body / safe_amp
    upper_ratio = upper_shadow / safe_amp
    lower_ratio = lower_shadow / safe_amp
    change_pct = (c - o) / safe_open * 100.0

    # 5日量均
    vol_ma5 = pd.Series(v).rolling(5, min_periods=1).mean().values
    safe_vol_ma = np.where(vol_ma5 > 0, vol_ma5, 1e-10)
    vol_ratio = v / safe_vol_ma

    # 前一根/前两根数据
    prev_o = np.roll(o, 1); prev_o[0] = o[0]
    prev_h = np.roll(h, 1); prev_h[0] = h[0]
    prev_l = np.roll(l, 1); prev_l[0] = l[0]
    prev_c = np.roll(c, 1); prev_c[0] = c[0]
    prev2_o = np.roll(o, 2); prev2_o[:2] = o[0]
    prev2_c = np.roll(c, 2); prev2_c[:2] = c[0]
    prev2_h = np.roll(h, 2); prev2_h[:2] = h[0]
    prev2_l = np.roll(l, 2); prev2_l[:2] = l[0]

    prev_body = np.abs(prev_c - prev_o)
    prev_amp = np.roll(amplitude, 1); prev_amp[0] = amplitude[0]
    safe_prev_amp = np.where(prev_amp > 0, prev_amp, 1e-10)
    prev_body_ratio = prev_body / safe_prev_amp

    prev_is_red = prev_c < prev_o
    prev_is_green = prev_c > prev_o
    prev2_is_red = prev2_c < prev2_o
    prev2_is_green = prev2_c > prev2_o
    prev_is_doji = prev_body_ratio <= 0.15

    prev_mid = (prev_o + prev_c) / 2.0

    result = pd.DataFrame(index=df.index)

    # 基础方向
    result["is_green"] = c > o
    result["is_red"] = c < o
    result["is_big_green"] = (change_pct >= 3.0) & (body_ratio > 0.6)
    result["is_big_red"] = (change_pct <= -3.0) & (body_ratio > 0.6)

    # 影线
    result["long_upper_shadow"] = upper_shadow >= safe_body * 2.0
    result["long_lower_shadow"] = lower_shadow >= safe_body * 2.0
    result["is_hammer"] = (lower_ratio > 0.4) & (upper_ratio < 0.2) & (body_ratio < 0.4)
    result["is_shooting_star"] = (upper_ratio > 0.4) & (lower_ratio < 0.2) & (body_ratio < 0.4)

    # 特殊形态
    result["is_doji"] = body_ratio <= 0.1
    result["is_dragonfly_doji"] = (body_ratio <= 0.1) & (lower_ratio > 0.4) & (upper_ratio < 0.1)
    result["is_gravestone_doji"] = (body_ratio <= 0.1) & (upper_ratio > 0.4) & (lower_ratio < 0.1)
    result["is_marubozu"] = (upper_ratio < 0.05) & (lower_ratio < 0.05) & (body_ratio > 0.9)
    result["is_spinning_top"] = (body_ratio < 0.3) & (upper_ratio > 0.25) & (lower_ratio > 0.25)

    # 反转组合
    result["engulfing_bullish"] = (
        prev_is_red & (c > o) &
        (o <= prev_c) & (c >= prev_o) & (body > prev_body)
    )
    result["engulfing_bearish"] = (
        prev_is_green & (c < o) &
        (o >= prev_c) & (c <= prev_o) & (body > prev_body)
    )
    result["morning_star"] = (
        prev2_is_red & prev_is_doji & (c > o) &
        (c > (prev2_o + prev2_c) / 2)
    )
    result["evening_star"] = (
        prev2_is_green & prev_is_doji & (c < o) &
        (c < (prev2_o + prev2_c) / 2)
    )
    result["piercing_line"] = prev_is_red & (c > o) & (o < prev_c) & (c > prev_mid)
    result["dark_cloud_cover"] = prev_is_green & (c < o) & (o > prev_c) & (c < prev_mid)

    # 连续形态
    result["three_green_soldiers"] = (prev2_c > prev2_o) & (prev_c > prev_o) & (c > o)
    result["three_red_soldiers"] = (prev2_c < prev2_o) & (prev_c < prev_o) & (c < o)

    safe_prev2_o = np.where(prev2_o > 0, prev2_o, 1e-10)
    safe_prev_o = np.where(prev_o > 0, prev_o, 1e-10)
    prev2_chg = (prev2_c - prev2_o) / safe_prev2_o * 100
    prev_chg = (prev_c - prev_o) / safe_prev_o * 100

    result["rising_three"] = (prev2_chg >= 2.0) & (prev_chg < 0) & (np.abs(prev_chg) < 1.5) & (change_pct >= 2.0)
    result["falling_three"] = (prev2_chg <= -2.0) & (prev_chg > 0) & (np.abs(prev_chg) < 1.5) & (change_pct <= -2.0)

    # 量价配合
    result["volume_yang"] = (c > o) & (vol_ratio >= 1.5)
    result["volume_yin"] = (c < o) & (vol_ratio >= 1.5)

    return result