"""
kline_behavior_lab/engine.py

K-Line Behavior Lab 引擎
桥接 quant_research 模块的核心功能
"""
from typing import Dict, Any
from vnpy.trader.engine import BaseEngine, MainEngine, EventEngine


class KLineBehaviorLabEngine(BaseEngine):
    """
    K线行为研究实验室引擎
    
    功能：
    - 桥接quant_research的behavior模块
    - 提供67个K线特征
    - 8个研究模板
    - 4种采样规则
    """
    
    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        super().__init__(main_engine, event_engine, "KLineBehaviorLab")
        
        # 导入核心引擎
        from vnpy.quant_research.behavior import (
            FeatureEngine,
            ConditionBuilder,
            SamplingEngine,
            get_global_registry
        )
        
        # 初始化核心引擎
        self.feature_engine = FeatureEngine()
        self.condition_builder = ConditionBuilder()
        self.sampling_engine = SamplingEngine()
        self.feature_registry = get_global_registry()
        
        # 通过main_engine记录日志
        feature_count = len(self.feature_registry.get_feature_names())
        self.main_engine.write_log(f"K-Line Behavior Lab initialized with {feature_count} features")
    
    def write_log(self, msg: str) -> None:
        """写日志"""
        self.main_engine.write_log(msg)

    def get_feature_count(self) -> int:
        """获取特征数量"""
        return len(self.feature_registry.get_feature_names())
    
    def get_template_count(self) -> int:
        """获取模板数量"""
        return len(self.condition_builder.get_condition_templates())
    
    def get_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        return {
            "features": self.get_feature_count(),
            "templates": self.get_template_count(),
            "version": "1.0.0"
        }