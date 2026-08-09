"""
quant_research/behavior/volume_price_calculator.py

量价关系向量化计算引擎
为36种量价关系特征提供高性能 pandas 向量化计算
"""
from __future__ import annotations
from typing import Optional
import pandas as pd
import numpy as np


# ====================================================================
# 基础九宫格（9种）
# ====================================================================

def calc_vp_vol_up_price_up(df: pd.DataFrame, vol_period: int = 20,
                             vol_ratio: float = 1.3) -> pd.Series:
    """量增价升"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    return ((df['volume'] > vol_ma * vol_ratio) &
            (df['close'] > df['close'].shift(1))).astype(int)


def calc_vp_vol_up_price_flat(df: pd.DataFrame, vol_period: int = 20,
                               vol_ratio: float = 1.3,
                               flat_threshold: float = 0.005) -> pd.Series:
    """量增价平"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    chg = (df['close'] - df['close'].shift(1)).abs() / (df['close'].shift(1) + 1e-8)
    return ((df['volume'] > vol_ma * vol_ratio) &
            (chg < flat_threshold)).astype(int)


def calc_vp_vol_up_price_down(df: pd.DataFrame, vol_period: int = 20,
                               vol_ratio: float = 1.3) -> pd.Series:
    """量增价跌"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    return ((df['volume'] > vol_ma * vol_ratio) &
            (df['close'] < df['close'].shift(1))).astype(int)


def calc_vp_vol_flat_price_up(df: pd.DataFrame, vol_period: int = 20,
                               vol_lo: float = 0.8,
                               vol_hi: float = 1.2) -> pd.Series:
    """量平价升"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    return ((df['volume'] > vol_ma * vol_lo) &
            (df['volume'] < vol_ma * vol_hi) &
            (df['close'] > df['close'].shift(1))).astype(int)


def calc_vp_vol_flat_price_flat(df: pd.DataFrame, vol_period: int = 20,
                                 vol_lo: float = 0.8, vol_hi: float = 1.2,
                                 flat_threshold: float = 0.005) -> pd.Series:
    """量平价平"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    chg = (df['close'] - df['close'].shift(1)).abs() / (df['close'].shift(1) + 1e-8)
    return ((df['volume'] > vol_ma * vol_lo) &
            (df['volume'] < vol_ma * vol_hi) &
            (chg < flat_threshold)).astype(int)


def calc_vp_vol_flat_price_down(df: pd.DataFrame, vol_period: int = 20,
                                 vol_lo: float = 0.8,
                                 vol_hi: float = 1.2) -> pd.Series:
    """量平价跌"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    return ((df['volume'] > vol_ma * vol_lo) &
            (df['volume'] < vol_ma * vol_hi) &
            (df['close'] < df['close'].shift(1))).astype(int)


def calc_vp_vol_down_price_up(df: pd.DataFrame, vol_period: int = 20,
                               vol_ratio: float = 0.7) -> pd.Series:
    """量缩价升"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    return ((df['volume'] < vol_ma * vol_ratio) &
            (df['close'] > df['close'].shift(1))).astype(int)


def calc_vp_vol_down_price_flat(df: pd.DataFrame, vol_period: int = 20,
                                 vol_ratio: float = 0.7,
                                 flat_threshold: float = 0.005) -> pd.Series:
    """量缩价平"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    chg = (df['close'] - df['close'].shift(1)).abs() / (df['close'].shift(1) + 1e-8)
    return ((df['volume'] < vol_ma * vol_ratio) &
            (chg < flat_threshold)).astype(int)


def calc_vp_vol_down_price_down(df: pd.DataFrame, vol_period: int = 20,
                                 vol_ratio: float = 0.7) -> pd.Series:
    """量缩价跌"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    return ((df['volume'] < vol_ma * vol_ratio) &
            (df['close'] < df['close'].shift(1))).astype(int)


# ====================================================================
# 极端形态（5种）
# ====================================================================

def calc_vp_sky_vol_sky_price(df: pd.DataFrame, lookback: int = 60) -> pd.Series:
    """天量天价"""
    vol_max = df['volume'].rolling(lookback).max()
    price_max = df['close'].rolling(lookback).max()
    return ((df['volume'] >= vol_max) &
            (df['close'] >= price_max)).astype(int)


def calc_vp_sky_vol_delayed_top(df: pd.DataFrame, lookback: int = 60,
                                 price_lookback: int = 10) -> pd.Series:
    """天量滞涨"""
    vol_max = df['volume'].rolling(lookback).max()
    price_high = df['high'].rolling(price_lookback).max()
    return ((df['volume'] >= vol_max) &
            (df['close'] < price_high)).astype(int)


def calc_vp_ground_vol_ground_price(df: pd.DataFrame, lookback: int = 60) -> pd.Series:
    """地量地价"""
    vol_min = df['volume'].rolling(lookback).min()
    price_min = df['close'].rolling(lookback).min()
    return ((df['volume'] <= vol_min) &
            (df['close'] <= price_min)).astype(int)


def calc_vp_ground_vol_delayed_bot(df: pd.DataFrame, vol_lookback: int = 60,
                                    price_lookback: int = 20,
                                    vol_tol: float = 1.1) -> pd.Series:
    """地量企稳"""
    vol_min = df['volume'].rolling(vol_lookback).min()
    price_min = df['low'].rolling(price_lookback).min()
    return ((df['volume'] <= vol_min * vol_tol) &
            (df['close'] > price_min)).astype(int)


def calc_vp_panic_shrink_bottom(df: pd.DataFrame, vol_period: int = 20,
                                 shrink_ratio: float = 0.4,
                                 prior_vol_ratio: float = 2.0,
                                 prior_drop_days: int = 5) -> pd.Series:
    """恐慌缩量见底：前期放量暴跌后量能骤缩"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    # 当前极度缩量
    cur_shrink = df['volume'] < vol_ma * shrink_ratio
    # 3天前有放量
    prior_vol = df['volume'].shift(3) > vol_ma.shift(3) * prior_vol_ratio
    # 3天前价格低于8天前（下跌过程）
    prior_drop = df['close'].shift(3) < df['close'].shift(8)
    return (cur_shrink & prior_vol & prior_drop).astype(int)


# ====================================================================
# 放量专题（5种）
# ====================================================================

def calc_vp_vol_break(df: pd.DataFrame, vol_period: int = 20,
                      vol_ratio: float = 2.0) -> pd.Series:
    """放量突破"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    price_high = df['high'].rolling(vol_period).max().shift(1)
    return ((df['volume'] > vol_ma * vol_ratio) &
            (df['close'] > price_high)).astype(int)


def calc_vp_vol_stall(df: pd.DataFrame, vol_period: int = 20,
                      vol_ratio: float = 2.0,
                      body_threshold: float = 0.01) -> pd.Series:
    """放量滞涨"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    ma20 = df['close'].rolling(vol_period).mean()
    body_pct = (df['close'] - df['open']).abs() / (df['open'] + 1e-8)
    return ((df['volume'] > vol_ma * vol_ratio) &
            (body_pct < body_threshold) &
            (df['close'] > ma20)).astype(int)


def calc_vp_vol_crash(df: pd.DataFrame, vol_period: int = 20,
                      vol_ratio: float = 2.0,
                      drop_threshold: float = -0.03) -> pd.Series:
    """放量杀跌"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    intraday_chg = (df['close'] - df['open']) / (df['open'] + 1e-8)
    return ((df['volume'] > vol_ma * vol_ratio) &
            (intraday_chg < drop_threshold)).astype(int)


def calc_vp_vol_retest(df: pd.DataFrame, vol_period: int = 20,
                       vol_ratio: float = 1.5) -> pd.Series:
    """放量回踩确认"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    ma20 = df['close'].rolling(vol_period).mean()
    # 放量
    vol_up = df['volume'] > vol_ma * vol_ratio
    # 低点触及MA20
    touch_ma = df['low'] <= ma20
    # 收盘站上MA20
    close_above = df['close'] > ma20
    # 5天前价格在MA20上方（之前是上涨趋势）
    prior_above = df['close'].shift(5) > ma20.shift(5)
    return (vol_up & touch_ma & close_above & prior_above).astype(int)


def calc_vp_vol_pulse(df: pd.DataFrame, short_period: int = 5,
                      pulse_ratio: float = 3.0) -> pd.Series:
    """脉冲放量"""
    vol_ma = df['volume'].rolling(short_period).mean()
    return (df['volume'] > vol_ma * pulse_ratio).astype(int)


# ====================================================================
# 缩量专题（5种）
# ====================================================================

def calc_vp_shrink_pullback(df: pd.DataFrame, vol_period: int = 10,
                             vol_ratio: float = 0.7,
                             ma_period: int = 20) -> pd.Series:
    """缩量回调"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    ma = df['close'].rolling(ma_period).mean()
    return ((df['volume'] < vol_ma * vol_ratio) &
            (df['close'] < df['close'].shift(1)) &
            (df['close'] > ma)).astype(int)


def calc_vp_shrink_drift_down(df: pd.DataFrame, vol_period: int = 20,
                               vol_ratio: float = 0.6) -> pd.Series:
    """缩量阴跌"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    ma20 = df['close'].rolling(vol_period).mean()
    return ((df['volume'] < vol_ma * vol_ratio) &
            (df['close'] < df['close'].shift(1)) &
            (df['close'] < ma20)).astype(int)


def calc_vp_shrink_breakout(df: pd.DataFrame, vol_period: int = 20,
                             vol_ratio: float = 0.8) -> pd.Series:
    """缩量突破"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    price_max = df['close'].rolling(vol_period).max()
    return ((df['volume'] < vol_ma * vol_ratio) &
            (df['close'] >= price_max)).astype(int)


def calc_vp_shrink_limit_up(df: pd.DataFrame, vol_period: int = 10,
                             vol_ratio: float = 0.5,
                             limit_threshold: float = 0.095) -> pd.Series:
    """缩量涨停"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    chg = (df['close'] - df['close'].shift(1)) / (df['close'].shift(1) + 1e-8)
    return ((df['volume'] < vol_ma * vol_ratio) &
            (chg > limit_threshold)).astype(int)


def calc_vp_shrink_limit_down(df: pd.DataFrame, vol_period: int = 10,
                               vol_ratio: float = 0.5,
                               limit_threshold: float = -0.095) -> pd.Series:
    """缩量跌停"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    chg = (df['close'] - df['close'].shift(1)) / (df['close'].shift(1) + 1e-8)
    return ((df['volume'] < vol_ma * vol_ratio) &
            (chg < limit_threshold)).astype(int)


# ====================================================================
# 量能结构（3种）
# ====================================================================

def calc_vp_flat_vol_push(df: pd.DataFrame, vol_period: int = 10,
                           vol_lo: float = 0.9, vol_hi: float = 1.1,
                           price_days: int = 3) -> pd.Series:
    """平量推升"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    return ((df['volume'] > vol_ma * vol_lo) &
            (df['volume'] < vol_ma * vol_hi) &
            (df['close'] > df['close'].shift(price_days)) &
            (df['close'].shift(1) > df['close'].shift(price_days + 1))).astype(int)


def calc_vp_vol_pile(df: pd.DataFrame, short_period: int = 5,
                     long_period: int = 20,
                     pile_ratio: float = 1.2) -> pd.Series:
    """堆量"""
    vol_ma_short = df['volume'].rolling(short_period).mean()
    vol_ma_long = df['volume'].rolling(long_period).mean()
    return ((vol_ma_short > vol_ma_long * pile_ratio) &
            (df['volume'] > df['volume'].shift(1)) &
            (df['volume'].shift(1) > df['volume'].shift(2))).astype(int)


def calc_vp_vol_pit(df: pd.DataFrame, vol_period: int = 20,
                    shrink_ratio: float = 0.6,
                    recover_ratio: float = 1.3) -> pd.Series:
    """凹量（量坑）"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    # 今天放量回升
    today_recover = df['volume'] > df['volume'].shift(1) * recover_ratio
    # 昨天和前天极度缩量
    yesterday_shrink = df['volume'].shift(1) < vol_ma.shift(1) * shrink_ratio
    day_before_shrink = df['volume'].shift(2) < vol_ma.shift(2) * shrink_ratio
    return (today_recover & yesterday_shrink & day_before_shrink).astype(int)


# ====================================================================
# 量价背离（2种）
# ====================================================================

def calc_vp_divergence_top(df: pd.DataFrame, lookback: int = 20,
                            vol_decay: float = 0.8) -> pd.Series:
    """量价顶背离"""
    price_max = df['close'].rolling(lookback).max()
    vol_max = df['volume'].rolling(lookback).max()
    return ((df['close'] >= price_max) &
            (df['volume'] < vol_max * vol_decay)).astype(int)


def calc_vp_divergence_bottom(df: pd.DataFrame, lookback: int = 20,
                               vol_recover: float = 1.2) -> pd.Series:
    """量价底背离"""
    price_min = df['close'].rolling(lookback).min()
    vol_min = df['volume'].rolling(lookback).min()
    return ((df['close'] <= price_min) &
            (df['volume'] > vol_min * vol_recover)).astype(int)


# ====================================================================
# 缺口量价（4种）
# ====================================================================

def calc_vp_gap_up_vol_up(df: pd.DataFrame, gap_pct: float = 0.01,
                           vol_period: int = 20,
                           vol_ratio: float = 1.5) -> pd.Series:
    """放量跳空上涨"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    gap = df['open'] > df['close'].shift(1) * (1 + gap_pct)
    vol_up = df['volume'] > vol_ma * vol_ratio
    return (gap & vol_up).astype(int)


def calc_vp_gap_down_vol_up(df: pd.DataFrame, gap_pct: float = 0.01,
                             vol_period: int = 20,
                             vol_ratio: float = 1.5) -> pd.Series:
    """放量跳空下跌"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    gap = df['open'] < df['close'].shift(1) * (1 - gap_pct)
    vol_up = df['volume'] > vol_ma * vol_ratio
    return (gap & vol_up).astype(int)


def calc_vp_gap_up_vol_down(df: pd.DataFrame, gap_pct: float = 0.01,
                             vol_period: int = 20,
                             vol_ratio: float = 0.7) -> pd.Series:
    """缩量跳空上涨"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    gap = df['open'] > df['close'].shift(1) * (1 + gap_pct)
    vol_down = df['volume'] < vol_ma * vol_ratio
    return (gap & vol_down).astype(int)


def calc_vp_gap_down_vol_down(df: pd.DataFrame, gap_pct: float = 0.01,
                               vol_period: int = 20,
                               vol_ratio: float = 0.7) -> pd.Series:
    """缩量跳空下跌"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    gap = df['open'] < df['close'].shift(1) * (1 - gap_pct)
    vol_down = df['volume'] < vol_ma * vol_ratio
    return (gap & vol_down).astype(int)


# ====================================================================
# 主力行为（3种）
# ====================================================================

def calc_vp_fake_vol_churn(df: pd.DataFrame, vol_period: int = 20,
                            vol_ratio: float = 2.5,
                            body_threshold: float = 0.2,
                            ma_period: int = 60,
                            price_above: float = 1.1) -> pd.Series:
    """高位对倒放量"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    ma_long = df['close'].rolling(ma_period).mean()
    body_ratio = (df['close'] - df['open']).abs() / (df['high'] - df['low'] + 1e-8)
    return ((df['volume'] > vol_ma * vol_ratio) &
            (body_ratio < body_threshold) &
            (df['close'] > ma_long * price_above)).astype(int)


def calc_vp_washout_vol(df: pd.DataFrame, vol_period: int = 20,
                         vol_ratio: float = 1.5,
                         lower_shadow_threshold: float = 0.6) -> pd.Series:
    """洗盘放量"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    ma20 = df['close'].rolling(vol_period).mean()
    lower_ratio = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-8)
    return ((df['volume'] > vol_ma * vol_ratio) &
            (lower_ratio > lower_shadow_threshold) &
            (df['close'] > df['open']) &
            (df['close'] > ma20)).astype(int)


def calc_vp_test_vol(df: pd.DataFrame, vol_period: int = 20,
                     vol_ratio: float = 1.5,
                     upper_shadow_threshold: float = 0.5,
                     ma_period: int = 60) -> pd.Series:
    """试盘放量"""
    vol_ma = df['volume'].rolling(vol_period).mean()
    ma_long = df['close'].rolling(ma_period).mean()
    upper_ratio = (df['high'] - df['close']) / (df['high'] - df['low'] + 1e-8)
    return ((df['volume'] > vol_ma * vol_ratio) &
            (upper_ratio > upper_shadow_threshold) &
            (df['close'] < ma_long)).astype(int)


# ====================================================================
# 统一接口：特征名 → 计算函数映射
# ====================================================================

VP_CALCULATOR_MAP = {
    # 基础九宫格
    "vp_vol_up_price_up": calc_vp_vol_up_price_up,
    "vp_vol_up_price_flat": calc_vp_vol_up_price_flat,
    "vp_vol_up_price_down": calc_vp_vol_up_price_down,
    "vp_vol_flat_price_up": calc_vp_vol_flat_price_up,
    "vp_vol_flat_price_flat": calc_vp_vol_flat_price_flat,
    "vp_vol_flat_price_down": calc_vp_vol_flat_price_down,
    "vp_vol_down_price_up": calc_vp_vol_down_price_up,
    "vp_vol_down_price_flat": calc_vp_vol_down_price_flat,
    "vp_vol_down_price_down": calc_vp_vol_down_price_down,
    # 极端形态
    "vp_sky_vol_sky_price": calc_vp_sky_vol_sky_price,
    "vp_sky_vol_delayed_top": calc_vp_sky_vol_delayed_top,
    "vp_ground_vol_ground_price": calc_vp_ground_vol_ground_price,
    "vp_ground_vol_delayed_bot": calc_vp_ground_vol_delayed_bot,
    "vp_panic_shrink_bottom": calc_vp_panic_shrink_bottom,
    # 放量专题
    "vp_vol_break": calc_vp_vol_break,
    "vp_vol_stall": calc_vp_vol_stall,
    "vp_vol_crash": calc_vp_vol_crash,
    "vp_vol_retest": calc_vp_vol_retest,
    "vp_vol_pulse": calc_vp_vol_pulse,
    # 缩量专题
    "vp_shrink_pullback": calc_vp_shrink_pullback,
    "vp_shrink_drift_down": calc_vp_shrink_drift_down,
    "vp_shrink_breakout": calc_vp_shrink_breakout,
    "vp_shrink_limit_up": calc_vp_shrink_limit_up,
    "vp_shrink_limit_down": calc_vp_shrink_limit_down,
    # 量能结构
    "vp_flat_vol_push": calc_vp_flat_vol_push,
    "vp_vol_pile": calc_vp_vol_pile,
    "vp_vol_pit": calc_vp_vol_pit,
    # 背离
    "vp_divergence_top": calc_vp_divergence_top,
    "vp_divergence_bottom": calc_vp_divergence_bottom,
    # 缺口量价
    "vp_gap_up_vol_up": calc_vp_gap_up_vol_up,
    "vp_gap_down_vol_up": calc_vp_gap_down_vol_up,
    "vp_gap_up_vol_down": calc_vp_gap_up_vol_down,
    "vp_gap_down_vol_down": calc_vp_gap_down_vol_down,
    # 主力行为
    "vp_fake_vol_churn": calc_vp_fake_vol_churn,
    "vp_washout_vol": calc_vp_washout_vol,
    "vp_test_vol": calc_vp_test_vol,
}


def calculate_volume_price_feature(df: pd.DataFrame, feature_name: str) -> pd.Series:
    """
    统一计算接口：根据特征名计算量价关系特征

    Args:
        df: K线数据，必须包含 open, high, low, close, volume 列
        feature_name: 特征名（vp_ 前缀）

    Returns:
        pd.Series: 布尔型(0/1)或数值型结果

    Raises:
        ValueError: 未知的特征名
    """
    calc_func = VP_CALCULATOR_MAP.get(feature_name)
    if calc_func is None:
        raise ValueError(f"未知的量价关系特征: {feature_name}")
    return calc_func(df)