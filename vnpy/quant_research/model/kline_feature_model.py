"""
quant_research/model/kline_feature_model.py

K线特征扩展模型
扩展FeatureRecord，专门用于K线行为特征
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class KLineFeatureType(Enum):
    """K线特征类型"""
    RETURN = "return"              # 收益特征
    STRUCTURE = "structure"        # K线结构（实体、影线）
    VOLATILITY = "volatility"      # 波动率
    VOLUME = "volume"              # 成交量/金额
    TREND = "trend"                # 趋势特征
    PATTERN = "pattern"            # 形态识别
    MOMENTUM = "momentum"          # 动量
    REVERSAL = "reversal"          # 反转
    CROSS_SECTIONAL = "cross"      # 截面特征


class FeatureComplexity(Enum):
    """特征计算复杂度"""
    SIMPLE = "simple"              # 简单（单根K线）
    MEDIUM = "medium"              # 中等（需要历史数据）
    COMPLEX = "complex"            # 复杂（需要多个依赖特征）


@dataclass
class KLineFeatureDefinition:
    """
    K线特征定义（预置特征库）
    用于批量注册标准K线特征
    """
    name: str = ""
    display_name: str = ""         # 显示名称（中文）
    feature_type: KLineFeatureType = KLineFeatureType.RETURN
    description: str = ""
    formula: str = ""              # 计算公式
    
    # 计算参数
    lookback_period: int = 0       # 回看周期
    complexity: FeatureComplexity = FeatureComplexity.SIMPLE
    dependencies: List[str] = field(default_factory=list)
    
    # 数据要求
    requires_ohlcv: bool = True
    requires_amount: bool = False
    requires_limit: bool = False
    requires_market_cap: bool = False
    
    # 实时计算支持
    realtime_supported: bool = True
    calculation_delay: int = 0
    
    # 数值范围和归一化
    value_range_min: Optional[float] = None
    value_range_max: Optional[float] = None
    normalize_method: str = "none"
    
    # 用途标记
    suitable_for_alpha: bool = True
    suitable_for_condition: bool = True
    suitable_for_filter: bool = True
    
    # 版本和作者
    version: str = "v1.0"
    author: str = "system"
    created_at: datetime = field(default_factory=datetime.now)


def get_feature_definition(feature_name: str) -> Optional[KLineFeatureDefinition]:
    """获取特征定义"""
    from .kline_feature_presets import PRESET_KLINE_FEATURES
    return PRESET_KLINE_FEATURES.get(feature_name)


def get_features_by_type(feature_type: KLineFeatureType) -> List[KLineFeatureDefinition]:
    """按类型获取特征列表"""
    from .kline_feature_presets import PRESET_KLINE_FEATURES
    return [f for f in PRESET_KLINE_FEATURES.values() if f.feature_type == feature_type]


def get_all_feature_names() -> List[str]:
    """获取所有预置特征名称"""
    from .kline_feature_presets import PRESET_KLINE_FEATURES
    return list(PRESET_KLINE_FEATURES.keys())
