"""
quant_research/model/kline_feature_extended.py

扩展K线特征库 - 补充特征
将特征数量从20个扩展到60+个
"""
from .kline_feature_model import KLineFeatureDefinition, KLineFeatureType, FeatureComplexity


# ========================================================================
# 扩展K线特征库 (Extended Features)
# ========================================================================

EXTENDED_KLINE_FEATURES = {
    # ====================================================================
    # 更多收益类特征
    # ====================================================================
    "return_10": KLineFeatureDefinition(
        name="return_10",
        display_name="10日收益率",
        feature_type=KLineFeatureType.RETURN,
        description="10日累积收益率",
        formula="(close - close.shift(10)) / close.shift(10)",
        lookback_period=10,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    "return_20": KLineFeatureDefinition(
        name="return_20",
        display_name="20日收益率",
        feature_type=KLineFeatureType.RETURN,
        description="20日累积收益率",
        formula="(close - close.shift(20)) / close.shift(20)",
        lookback_period=20,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    "log_return_1": KLineFeatureDefinition(
        name="log_return_1",
        display_name="对数收益率",
        feature_type=KLineFeatureType.RETURN,
        description="1日对数收益率，更适合金融建模",
        formula="np.log(close / close.shift(1))",
        lookback_period=1,
        complexity=FeatureComplexity.SIMPLE,
        suitable_for_alpha=True,
    ),
    
    "overnight_return": KLineFeatureDefinition(
        name="overnight_return",
        display_name="隔夜收益",
        feature_type=KLineFeatureType.RETURN,
        description="当日开盘价相对前日收盘价的收益率",
        formula="(open - close.shift(1)) / close.shift(1)",
        lookback_period=1,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    # ====================================================================
    # 更多K线结构特征
    # ====================================================================
    "body_pct": KLineFeatureDefinition(
        name="body_pct",
        display_name="实体幅度",
        feature_type=KLineFeatureType.STRUCTURE,
        description="实体占开盘价的比例",
        formula="abs(close - open) / open",
        lookback_period=0,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    "upper_shadow_pct": KLineFeatureDefinition(
        name="upper_shadow_pct",
        display_name="上影线幅度",
        feature_type=KLineFeatureType.STRUCTURE,
        description="上影线占开盘价的比例",
        formula="(high - max(open, close)) / open",
        lookback_period=0,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    "lower_shadow_pct": KLineFeatureDefinition(
        name="lower_shadow_pct",
        display_name="下影线幅度",
        feature_type=KLineFeatureType.STRUCTURE,
        description="下影线占开盘价的比例",
        formula="(min(open, close) - low) / open",
        lookback_period=0,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    "is_green": KLineFeatureDefinition(
        name="is_green",
        display_name="是否阳线",
        feature_type=KLineFeatureType.STRUCTURE,
        description="收盘价高于开盘价为1，否则为0",
        formula="(close > open).astype(int)",
        lookback_period=0,
        complexity=FeatureComplexity.SIMPLE,
        suitable_for_alpha=False,
    ),
    
    "is_red": KLineFeatureDefinition(
        name="is_red",
        display_name="是否阴线",
        feature_type=KLineFeatureType.STRUCTURE,
        description="收盘价低于开盘价为1，否则为0",
        formula="(close < open).astype(int)",
        lookback_period=0,
        complexity=FeatureComplexity.SIMPLE,
        suitable_for_alpha=False,
    ),
    
    "is_doji": KLineFeatureDefinition(
        name="is_doji",
        display_name="是否十字星",
        feature_type=KLineFeatureType.PATTERN,
        description="实体比例小于0.1的K线",
        formula="(body_ratio < 0.1).astype(int)",
        lookback_period=0,
        complexity=FeatureComplexity.SIMPLE,
        dependencies=["body_ratio"],
        suitable_for_condition=True,
    ),
    
    "is_hammer": KLineFeatureDefinition(
        name="is_hammer",
        display_name="是否锤子线",
        feature_type=KLineFeatureType.PATTERN,
        description="下影线长、上影线短、实体小",
        formula="(lower_shadow_ratio > 0.4) & (upper_shadow_ratio < 0.2) & (body_ratio < 0.4)",
        lookback_period=0,
        complexity=FeatureComplexity.MEDIUM,
        dependencies=["lower_shadow_ratio", "upper_shadow_ratio", "body_ratio"],
        suitable_for_condition=True,
    ),
    
    # ====================================================================
    # 更多波动率特征
    # ====================================================================
    "atr_10": KLineFeatureDefinition(
        name="atr_10",
        display_name="ATR(10)",
        feature_type=KLineFeatureType.VOLATILITY,
        description="10日平均真实波幅",
        formula="ATR(10)",
        lookback_period=10,
        complexity=FeatureComplexity.MEDIUM,
    ),
    
    "volatility_10": KLineFeatureDefinition(
        name="volatility_10",
        display_name="10日波动率",
        feature_type=KLineFeatureType.VOLATILITY,
        description="10日收益率标准差（年化）",
        formula="returns.rolling(10).std() * np.sqrt(252)",
        lookback_period=10,
        complexity=FeatureComplexity.MEDIUM,
        dependencies=["return_1"],
    ),
    
    "volatility_percentile": KLineFeatureDefinition(
        name="volatility_percentile",
        display_name="波动率百分位",
        feature_type=KLineFeatureType.VOLATILITY,
        description="当前波动率在过去60日中的百分位",
        formula="volatility_20.rolling(60).rank(pct=True)",
        lookback_period=60,
        complexity=FeatureComplexity.COMPLEX,
        dependencies=["volatility_20"],
    ),
    
    "realized_volatility_5": KLineFeatureDefinition(
        name="realized_volatility_5",
        display_name="5日已实现波动率",
        feature_type=KLineFeatureType.VOLATILITY,
        description="过去5日高低价平均波幅",
        formula="((high - low) / close).rolling(5).mean()",
        lookback_period=5,
        complexity=FeatureComplexity.MEDIUM,
    ),
    
    # ====================================================================
    # 更多成交量特征
    # ====================================================================
    "volume_ratio_5": KLineFeatureDefinition(
        name="volume_ratio_5",
        display_name="5日量比",
        feature_type=KLineFeatureType.VOLUME,
        description="当前成交量 / 5日平均成交量",
        formula="volume / volume.rolling(5).mean()",
        lookback_period=5,
        complexity=FeatureComplexity.SIMPLE,
        suitable_for_condition=True,
    ),
    
    "volume_spike": KLineFeatureDefinition(
        name="volume_spike",
        display_name="放量突破",
        feature_type=KLineFeatureType.VOLUME,
        description="成交量超过20日均值的2倍",
        formula="(volume > volume.rolling(20).mean() * 2).astype(int)",
        lookback_period=20,
        complexity=FeatureComplexity.SIMPLE,
        suitable_for_condition=True,
    ),
    
    "volume_shrink": KLineFeatureDefinition(
        name="volume_shrink",
        display_name="缩量",
        feature_type=KLineFeatureType.VOLUME,
        description="成交量低于20日均值的50%",
        formula="(volume < volume.rolling(20).mean() * 0.5).astype(int)",
        lookback_period=20,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    "turnover_ratio": KLineFeatureDefinition(
        name="turnover_ratio",
        display_name="换手率比",
        feature_type=KLineFeatureType.VOLUME,
        description="当前换手率 / 20日平均换手率",
        formula="turnover_rate / turnover_rate.rolling(20).mean()",
        lookback_period=20,
        complexity=FeatureComplexity.SIMPLE,
        requires_amount=True,
    ),
    
    # ====================================================================
    # 更多趋势特征
    # ====================================================================
    "ma10": KLineFeatureDefinition(
        name="ma10",
        display_name="MA10",
        feature_type=KLineFeatureType.TREND,
        description="10日移动平均线",
        formula="close.rolling(10).mean()",
        lookback_period=10,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    "ma60": KLineFeatureDefinition(
        name="ma60",
        display_name="MA60",
        feature_type=KLineFeatureType.TREND,
        description="60日移动平均线",
        formula="close.rolling(60).mean()",
        lookback_period=60,
        complexity=FeatureComplexity.SIMPLE,
    ),
    
    "ma_slope_5": KLineFeatureDefinition(
        name="ma_slope_5",
        display_name="MA5斜率",
        feature_type=KLineFeatureType.TREND,
        description="MA5的变化率",
        formula="(ma5 - ma5.shift(5)) / ma5.shift(5)",
        lookback_period=10,
        complexity=FeatureComplexity.MEDIUM,
        dependencies=["ma5"],
    ),
    
    "ma_slope_20": KLineFeatureDefinition(
        name="ma_slope_20",
        display_name="MA20斜率",
        feature_type=KLineFeatureType.TREND,
        description="MA20的变化率",
        formula="(ma20 - ma20.shift(10)) / ma20.shift(10)",
        lookback_period=30,
        complexity=FeatureComplexity.MEDIUM,
        dependencies=["ma20"],
    ),
    
    "price_to_ma5": KLineFeatureDefinition(
        name="price_to_ma5",
        display_name="价格MA5乖离率",
        feature_type=KLineFeatureType.TREND,
        description="当前价格偏离MA5的程度",
        formula="(close - ma5) / ma5",
        lookback_period=5,
        complexity=FeatureComplexity.MEDIUM,
        dependencies=["ma5"],
    ),
    
    "price_to_ma20": KLineFeatureDefinition(
        name="price_to_ma20",
        display_name="价格MA20乖离率",
        feature_type=KLineFeatureType.TREND,
        description="当前价格偏离MA20的程度",
        formula="(close - ma20) / ma20",
        lookback_period=20,
        complexity=FeatureComplexity.MEDIUM,
        dependencies=["ma20"],
    ),
    
    "ma_alignment": KLineFeatureDefinition(
        name="ma_alignment",
        display_name="均线多头排列",
        feature_type=KLineFeatureType.TREND,
        description="MA5 > MA10 > MA20 > MA60",
        formula="((ma5 > ma10) & (ma10 > ma20) & (ma20 > ma60)).astype(int)",
        lookback_period=60,
        complexity=FeatureComplexity.COMPLEX,
        dependencies=["ma5", "ma10", "ma20", "ma60"],
        suitable_for_condition=True,
    ),
    
    "new_high_20": KLineFeatureDefinition(
        name="new_high_20",
        display_name="20日新高",
        feature_type=KLineFeatureType.TREND,
        description="创20日新高",
        formula="(close >= close.rolling(20).max()).astype(int)",
        lookback_period=20,
        complexity=FeatureComplexity.SIMPLE,
        suitable_for_condition=True,
    ),
    
    "new_low_20": KLineFeatureDefinition(
        name="new_low_20",
        display_name="20日新低",
        feature_type=KLineFeatureType.TREND,
        description="创20日新低",
        formula="(close <= close.rolling(20).min()).astype(int)",
        lookback_period=20,
        complexity=FeatureComplexity.SIMPLE,
        suitable_for_condition=True,
    ),
}
