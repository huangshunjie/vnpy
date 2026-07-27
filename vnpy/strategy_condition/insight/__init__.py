"""
Condition Insight — 条件智能分析助手模块

提供每个策略条件的专业级量化研究说明，包括：
- 条件功能描述
- 计算公式
- 参数说明与推荐
- 使用场景
- 组合建议
- 风险提示
- 量化经验
"""
from .schema import ConditionInsight, ConditionRole, ParamInsight
from .manager import ConditionInsightManager

__all__ = [
    "ConditionInsight",
    "ConditionRole",
    "ParamInsight",
    "ConditionInsightManager",
]