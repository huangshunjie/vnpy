"""
quant_research/model/kline_feature_extended2.py

扩展K线特征库 - 第二部分
包含反转、动量、形态识别特征
"""
from .kline_feature_model import KLineFeatureDefinition, KLineFeatureType, FeatureComplexity


EXTENDED_KLINE_FEATURES_2 = {
    # ====================================================================
    # 反转特征 (REVERSAL)
    # ====================================================================
    "pullback_from_high": KLineFeatureDefinition(
        name="pullback_from_high",
        display_name="从高点回撤幅度",
        feature_type=KLineFeatureType.REVERSAL,
        description="当前价格相对20日最高价的回撤",
        formula="(close - close.rolling(20).max()) / close.rolling(20).max()",
        lookback_period=20,
        complexity=FeatureComplexity.MEDIUM,
        value_range_min=-1.0,
        value_range_max=0.0,
    ),
    
    "bounce_from_low": KLineFeatureDefinition(
        name="bounce_from_low",
        display_name="从低点反弹幅度",
        feature_type=KLineFeatureType.REVERSAL,
        description="当前价格相对20日最低价的反弹",
        formula="(close - close.rolling(20).min()) / close.rolling(20).min()",
        lookback_period=20,
        complexity=FeatureComplexity.MEDIUM,
        value_range_min=0.0,
        value_range_max=1.0,
    ),
    
    "reversal_score": KLineFeatureDefinition(
        name="reversal_score",
        display_name="反转信号得分",
        feature_type=KLineFeatureType.REVERSAL,
        description="综合反转信号：大阴线+长下影+放量",
        formula="(return_1 < -0.03) & (lower_shadow_ratio > 0.4) & (volume_ratio > 1.5)",
        lookback_period=20,
        complexity=FeatureComplexity.COMPLEX,
        dependencies=["return_1", "lower_shadow_ratio", "volume_ratio"],
        suitable_for_condition=True,
    ),
    
    "v_reversal": KLineFeatureDefinition(
        name="v_reversal",
        display_name="V型反转",
        feature_type=KLineFeatureType.REVERSAL,
        description="快速下跌后快速反弹",
        formula="(return_5 < -0.10) & (return_1 > 0.03)",
        lookback_period=5,
        complexity=FeatureComplexity.MEDIUM,
        dependencies=["return_1", "return_5"],
        suitable_for_condition=True,
    ),
    
    # ====================================================================
    # 更多动量特征 (MOMENTUM)
    # ====================================================================
    "rsi_6": KLineFeatureDefinition(
        name="rsi_6",
        display_name="RSI(6)",
        feature_type=KLineFeatureType.MOMENTUM,
        description="6日相对强弱指标",
        formula="RSI(6)",
        lookback_period=6,
        complexity=FeatureComplexity.MEDIUM,
        value_range_min=0.0,
        value_range_max=100.0,
    ),
    
    "rsi_oversold": KLineFeatureDefinition(
        name="rsi_oversold",
        display_name="RSI超卖",
        feature_type=KLineFeatureType.MOMENTUM,
        description="RSI低于30",
        formula="(rsi_14 < 30).astype(int)",
        lookback_period=14,
        complexity=FeatureComplexity.MEDIUM,
        dependencies=["rsi_14"],
        suitable_for_condition=True,
    ),
    
    "rsi_overbought": KLineFeatureDefinition(
        name="rsi_overbought",
        display_name="RSI超买",
        feature_type=KLineFeatureType.MOMENTUM,
        description="RSI高于70",
        formula="(rsi_14 > 70).astype(int)",
        lookback_period=14,
        complexity=FeatureComplexity.MEDIUM,
        dependencies=["rsi_14"],
        suitable_for_condition=True,
    ),
    
    "macd": KLineFeatureDefinition(
        name="macd",
        display_name="MACD",
        feature_type=KLineFeatureType.MOMENTUM,
        description="MACD指标差离值",
        formula="EMA(12) - EMA(26)",
        lookback_period=26,
        complexity=FeatureComplexity.MEDIUM,
    ),
    
    "macd_signal": KLineFeatureDefinition(
        name="macd_signal",
        display_name="MACD信号线",
        feature_type=KLineFeatureType.MOMENTUM,
        description="MACD的9日EMA",
        formula="EMA(macd, 9)",
        lookback_period=35,
        complexity=FeatureComplexity.MEDIUM,
        dependencies=["macd"],
    ),
    
    "macd_histogram": KLineFeatureDefinition(
        name="macd_histogram",
        display_name="MACD柱状图",
        feature_type=KLineFeatureType.MOMENTUM,
        description="MACD与信号线的差值",
        formula="macd - macd_signal",
        lookback_period=35,
        complexity=FeatureComplexity.COMPLEX,
        dependencies=["macd", "macd_signal"],
    ),
    
    "momentum_5": KLineFeatureDefinition(
        name="momentum_5",
        display_name="5日动量",
        feature_type=KLineFeatureType.MOMENTUM,
        description="5日价格动量",
        formula="close - close.shift(5)",
        lookback_period=5,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    "momentum_10": KLineFeatureDefinition(
        name="momentum_10",
        display_name="10日动量",
        feature_type=KLineFeatureType.MOMENTUM,
        description="10日价格动量",
        formula="close - close.shift(10)",
        lookback_period=10,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    # ====================================================================
    # 形态识别特征 (PATTERN)
    # ====================================================================
    "is_big_red": KLineFeatureDefinition(
        name="is_big_red",
        display_name="大阴线",
        feature_type=KLineFeatureType.PATTERN,
        description="跌幅超过3%且实体比例大于0.6",
        formula="(return_1 < -0.03) & (body_ratio > 0.6)",
        lookback_period=1,
        complexity=FeatureComplexity.MEDIUM,
        dependencies=["return_1", "body_ratio"],
        suitable_for_condition=True,
    ),
    
    "is_big_green": KLineFeatureDefinition(
        name="is_big_green",
        display_name="大阳线",
        feature_type=KLineFeatureType.PATTERN,
        description="涨幅超过3%且实体比例大于0.6",
        formula="(return_1 > 0.03) & (body_ratio > 0.6)",
        lookback_period=1,
        complexity=FeatureComplexity.MEDIUM,
        dependencies=["return_1", "body_ratio"],
        suitable_for_condition=True,
    ),
    
    "is_shooting_star": KLineFeatureDefinition(
        name="is_shooting_star",
        display_name="射击之星",
        feature_type=KLineFeatureType.PATTERN,
        description="长上影线、短下影线、小实体",
        formula="(upper_shadow_ratio > 0.4) & (lower_shadow_ratio < 0.2) & (body_ratio < 0.4)",
        lookback_period=0,
        complexity=FeatureComplexity.MEDIUM,
        dependencies=["upper_shadow_ratio", "lower_shadow_ratio", "body_ratio"],
        suitable_for_condition=True,
    ),
    
    "three_red_soldiers": KLineFeatureDefinition(
        name="three_red_soldiers",
        display_name="三连阴",
        feature_type=KLineFeatureType.PATTERN,
        description="连续3根阴线",
        formula="(close < open) & (close.shift(1) < open.shift(1)) & (close.shift(2) < open.shift(2))",
        lookback_period=2,
        complexity=FeatureComplexity.MEDIUM,
        suitable_for_condition=True,
    ),
    
    "three_green_soldiers": KLineFeatureDefinition(
        name="three_green_soldiers",
        display_name="三连阳",
        feature_type=KLineFeatureType.PATTERN,
        description="连续3根阳线",
        formula="(close > open) & (close.shift(1) > open.shift(1)) & (close.shift(2) > open.shift(2))",
        lookback_period=2,
        complexity=FeatureComplexity.MEDIUM,
        suitable_for_condition=True,
    ),
    
    "morning_star": KLineFeatureDefinition(
        name="morning_star",
        display_name="早晨之星",
        feature_type=KLineFeatureType.PATTERN,
        description="底部反转形态：阴线+十字星+阳线",
        formula="(is_red.shift(2)) & (is_doji.shift(1)) & (is_green)",
        lookback_period=2,
        complexity=FeatureComplexity.COMPLEX,
        dependencies=["is_red", "is_doji", "is_green"],
        suitable_for_condition=True,
    ),
    
    "engulfing_bullish": KLineFeatureDefinition(
        name="engulfing_bullish",
        display_name="看涨吞没",
        feature_type=KLineFeatureType.PATTERN,
        description="大阳线吞没前一根阴线",
        formula="(close > open) & (close.shift(1) < open.shift(1)) & (open < close.shift(1)) & (close > open.shift(1))",
        lookback_period=1,
        complexity=FeatureComplexity.MEDIUM,
        suitable_for_condition=True,
    ),
    
    # ====================================================================
    # 截面特征 (CROSS_SECTIONAL) - 需要横截面数据
    # ====================================================================
    "relative_strength": KLineFeatureDefinition(
        name="relative_strength",
        display_name="相对强度",
        feature_type=KLineFeatureType.CROSS_SECTIONAL,
        description="相对市场的强度（需要市场数据）",
        formula="return_20 - market_return_20",
        lookback_period=20,
        complexity=FeatureComplexity.COMPLEX,
        dependencies=["return_20"],
        realtime_supported=False,
    ),
    
    "volume_rank": KLineFeatureDefinition(
        name="volume_rank",
        display_name="成交量排名",
        feature_type=KLineFeatureType.CROSS_SECTIONAL,
        description="成交量在市场中的百分位排名",
        formula="volume.rank(pct=True)",
        lookback_period=0,
        complexity=FeatureComplexity.SIMPLE,
        realtime_supported=False,
    ),
}
