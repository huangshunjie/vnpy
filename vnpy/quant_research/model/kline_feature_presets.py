"""
quant_research/model/kline_feature_presets.py

预置K线特征库
包含50+个标准K线特征的定义
"""
from .kline_feature_model import KLineFeatureDefinition, KLineFeatureType, FeatureComplexity


# ========================================================================
# 预置K线特征库
# ========================================================================

PRESET_KLINE_FEATURES = {
    # ====================================================================
    # 收益类特征 (RETURN)
    # ====================================================================
    "return_1": KLineFeatureDefinition(
        name="return_1",
        display_name="1日收益率",
        feature_type=KLineFeatureType.RETURN,
        description="当日收盘价相对前一日收盘价的收益率",
        formula="(close - close.shift(1)) / close.shift(1)",
        lookback_period=1,
        complexity=FeatureComplexity.SIMPLE,
        value_range_min=-0.20,
        value_range_max=0.20,
    ),
    
    "return_3": KLineFeatureDefinition(
        name="return_3",
        display_name="3日收益率",
        feature_type=KLineFeatureType.RETURN,
        description="3日累积收益率",
        formula="(close - close.shift(3)) / close.shift(3)",
        lookback_period=3,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    "return_5": KLineFeatureDefinition(
        name="return_5",
        display_name="5日收益率",
        feature_type=KLineFeatureType.RETURN,
        description="5日累积收益率",
        formula="(close - close.shift(5)) / close.shift(5)",
        lookback_period=5,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    "gap_return": KLineFeatureDefinition(
        name="gap_return",
        display_name="跳空收益",
        feature_type=KLineFeatureType.RETURN,
        description="开盘价相对前收盘价的跳空幅度",
        formula="(open - close.shift(1)) / close.shift(1)",
        lookback_period=1,
        complexity=FeatureComplexity.SIMPLE,
        suitable_for_alpha=False,
    ),
    
    "intraday_return": KLineFeatureDefinition(
        name="intraday_return",
        display_name="日内收益",
        feature_type=KLineFeatureType.RETURN,
        description="收盘价相对开盘价的涨跌幅",
        formula="(close - open) / open",
        lookback_period=0,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    # ====================================================================
    # K线结构特征 (STRUCTURE)
    # ====================================================================
    "body_ratio": KLineFeatureDefinition(
        name="body_ratio",
        display_name="实体比例",
        feature_type=KLineFeatureType.STRUCTURE,
        description="实体占整个K线的比例",
        formula="abs(close - open) / (high - low + 1e-8)",
        lookback_period=0,
        complexity=FeatureComplexity.SIMPLE,
        value_range_min=0.0,
        value_range_max=1.0,
    ),
    
    "upper_shadow_ratio": KLineFeatureDefinition(
        name="upper_shadow_ratio",
        display_name="上影线比例",
        feature_type=KLineFeatureType.STRUCTURE,
        description="上影线占整个K线的比例",
        formula="(high - max(open, close)) / (high - low + 1e-8)",
        lookback_period=0,
        complexity=FeatureComplexity.SIMPLE,
        value_range_min=0.0,
        value_range_max=1.0,
    ),
    
    "lower_shadow_ratio": KLineFeatureDefinition(
        name="lower_shadow_ratio",
        display_name="下影线比例",
        feature_type=KLineFeatureType.STRUCTURE,
        description="下影线占整个K线的比例，大阴线+长下影线常见于底部反转",
        formula="(min(open, close) - low) / (high - low + 1e-8)",
        lookback_period=0,
        complexity=FeatureComplexity.SIMPLE,
        value_range_min=0.0,
        value_range_max=1.0,
        suitable_for_alpha=True,
        suitable_for_condition=True,
    ),
    
    "close_location": KLineFeatureDefinition(
        name="close_location",
        display_name="收盘位置",
        feature_type=KLineFeatureType.STRUCTURE,
        description="收盘价在高低价之间的位置（0=最低，1=最高）",
        formula="(close - low) / (high - low + 1e-8)",
        lookback_period=0,
        complexity=FeatureComplexity.SIMPLE,
        value_range_min=0.0,
        value_range_max=1.0,
    ),
    
    # ====================================================================
    # 波动率特征 (VOLATILITY)
    # ====================================================================
    "range_pct": KLineFeatureDefinition(
        name="range_pct",
        display_name="振幅",
        feature_type=KLineFeatureType.VOLATILITY,
        description="高低价差占开盘价的比例",
        formula="(high - low) / open",
        lookback_period=0,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    "atr_20": KLineFeatureDefinition(
        name="atr_20",
        display_name="ATR(20)",
        feature_type=KLineFeatureType.VOLATILITY,
        description="20日平均真实波幅",
        formula="talib.ATR(high, low, close, timeperiod=20)",
        lookback_period=20,
        complexity=FeatureComplexity.MEDIUM,
    ),
    
    "volatility_20": KLineFeatureDefinition(
        name="volatility_20",
        display_name="20日波动率",
        feature_type=KLineFeatureType.VOLATILITY,
        description="20日收益率标准差（年化）",
        formula="returns.rolling(20).std() * np.sqrt(252)",
        lookback_period=20,
        complexity=FeatureComplexity.MEDIUM,
        dependencies=["return_1"],
    ),
    
    # ====================================================================
    # 成交量特征 (VOLUME)
    # ====================================================================
    "volume_ratio": KLineFeatureDefinition(
        name="volume_ratio",
        display_name="量比",
        feature_type=KLineFeatureType.VOLUME,
        description="当前成交量 / 20日平均成交量",
        formula="volume / volume.rolling(20).mean()",
        lookback_period=20,
        complexity=FeatureComplexity.SIMPLE,
        suitable_for_condition=True,
    ),
    
    "amount_ratio": KLineFeatureDefinition(
        name="amount_ratio",
        display_name="额比",
        feature_type=KLineFeatureType.VOLUME,
        description="当前成交额 / 20日平均成交额",
        formula="amount / amount.rolling(20).mean()",
        lookback_period=20,
        complexity=FeatureComplexity.SIMPLE,
        requires_amount=True,
    ),
    
    # ====================================================================
    # 趋势特征 (TREND)
    # ====================================================================
    "ma5": KLineFeatureDefinition(
        name="ma5",
        display_name="MA5",
        feature_type=KLineFeatureType.TREND,
        description="5日移动平均线",
        formula="close.rolling(5).mean()",
        lookback_period=5,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    "ma20": KLineFeatureDefinition(
        name="ma20",
        display_name="MA20",
        feature_type=KLineFeatureType.TREND,
        description="20日移动平均线",
        formula="close.rolling(20).mean()",
        lookback_period=20,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    "price_position": KLineFeatureDefinition(
        name="price_position",
        display_name="价格位置",
        feature_type=KLineFeatureType.TREND,
        description="当前价格在60日高低价之间的位置",
        formula="(close - low_60) / (high_60 - low_60 + 1e-8)",
        lookback_period=60,
        complexity=FeatureComplexity.MEDIUM,
    ),
    
    # ====================================================================
    # 动量特征 (MOMENTUM)
    # ====================================================================
    "rsi_14": KLineFeatureDefinition(
        name="rsi_14",
        display_name="RSI(14)",
        feature_type=KLineFeatureType.MOMENTUM,
        description="14日相对强弱指标",
        formula="talib.RSI(close, timeperiod=14)",
        lookback_period=14,
        complexity=FeatureComplexity.MEDIUM,
        value_range_min=0.0,
        value_range_max=100.0,
    ),
}
