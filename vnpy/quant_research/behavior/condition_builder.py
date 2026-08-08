"""
quant_research/behavior/condition_builder.py

条件构建器
提供友好的条件表达式构建和验证工具
桥接strategy_condition模块
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any
import re
import pandas as pd

from .feature_registry import get_global_registry


class ConditionBuilder:
    """
    条件构建器
    
    核心功能：
    1. 构建和验证条件表达式
    2. 解析表达式中的特征依赖
    3. 提供条件模板
    4. 桥接strategy_condition模块（预留）
    """
    
    def __init__(self):
        self.registry = get_global_registry()
        self._operators = {
            '>': 'greater_than',
            '<': 'less_than',
            '>=': 'greater_equal',
            '<=': 'less_equal',
            '==': 'equal',
            '!=': 'not_equal',
            '&': 'and',
            '|': 'or',
        }
    
    def build_simple_condition(
        self,
        feature: str,
        operator: str,
        value: float
    ) -> str:
        """
        构建简单条件
        
        Args:
            feature: 特征名称
            operator: 操作符 (>, <, >=, <=, ==, !=)
            value: 阈值
            
        Returns:
            条件表达式字符串
            
        Example:
            >>> builder.build_simple_condition('return_1', '<', -0.03)
            'return_1 < -0.03'
        """
        if not self.registry.has_feature(feature):
            raise ValueError(f"未知特征: {feature}")
        
        if operator not in self._operators:
            raise ValueError(f"不支持的操作符: {operator}")
        
        return f"{feature} {operator} {value}"
    
    def build_compound_condition(
        self,
        conditions: List[str],
        logic: str = 'AND'
    ) -> str:
        """
        构建复合条件
        
        Args:
            conditions: 简单条件列表
            logic: 逻辑操作符 ('AND' 或 'OR')
            
        Returns:
            复合条件表达式
            
        Example:
            >>> conditions = [
            ...     'return_1 < -0.03',
            ...     'lower_shadow_ratio > 0.4',
            ...     'volume_ratio > 1.5'
            ... ]
            >>> builder.build_compound_condition(conditions, 'AND')
            '(return_1 < -0.03) & (lower_shadow_ratio > 0.4) & (volume_ratio > 1.5)'
        """
        if not conditions:
            raise ValueError("条件列表不能为空")
        
        logic = logic.upper()
        if logic not in ['AND', 'OR']:
            raise ValueError("逻辑操作符必须是 'AND' 或 'OR'")
        
        separator = ' & ' if logic == 'AND' else ' | '
        
        # 为每个条件加括号
        wrapped_conditions = [f"({c})" for c in conditions]
        
        return separator.join(wrapped_conditions)
    
    def validate_expression(
        self,
        expression: str,
        data: Optional[pd.DataFrame] = None
    ) -> Tuple[bool, str, List[str]]:
        """
        验证条件表达式
        
        Args:
            expression: 条件表达式
            data: 测试数据（可选）
            
        Returns:
            (是否有效, 错误信息, 依赖特征列表)
            
        Example:
            >>> valid, error, features = builder.validate_expression(
            ...     '(return_1 < -0.03) & (volume_ratio > 1.5)'
            ... )
        """
        # 1. 提取特征名称
        features = self.extract_features(expression)
        
        # 2. 验证特征存在性
        valid, invalid_features = self.registry.validate_features(features)
        if not valid:
            return False, f"未知特征: {invalid_features}", []
        
        # 3. 语法检查（基础）
        try:
            # 检查括号匹配
            if expression.count('(') != expression.count(')'):
                return False, "括号不匹配", features
            
            # 如果提供了测试数据，尝试执行
            if data is not None:
                # 准备命名空间
                namespace = {'np': pd.np if hasattr(pd, 'np') else None, 'pd': pd}
                for f in features:
                    if f in data.columns:
                        namespace[f] = data[f]
                    else:
                        # 使用模拟数据
                        namespace[f] = pd.Series([1.0] * len(data))
                
                # 尝试执行
                result = eval(expression, {"__builtins__": {}}, namespace)
                
                # 检查结果类型
                if not isinstance(result, (pd.Series, bool)):
                    return False, "表达式结果类型错误，应返回布尔值或Series", features
            
            return True, "", features
            
        except SyntaxError as e:
            return False, f"语法错误: {str(e)}", features
        except Exception as e:
            return False, f"表达式错误: {str(e)}", features
    
    def extract_features(self, expression: str) -> List[str]:
        """
        从表达式中提取特征名称
        
        Args:
            expression: 条件表达式
            
        Returns:
            特征名称列表
            
        Example:
            >>> builder.extract_features('(return_1 < -0.03) & (volume_ratio > 1.5)')
            ['return_1', 'volume_ratio']
        """
        # 获取所有已知特征
        all_features = self.registry.get_feature_names()
        
        # 在表达式中查找特征
        found_features = []
        for feature in all_features:
            # 使用单词边界匹配，避免部分匹配
            pattern = r'\b' + re.escape(feature) + r'\b'
            if re.search(pattern, expression):
                found_features.append(feature)
        
        return found_features
    
    def parse_expression(self, expression: str) -> Dict[str, Any]:
        """
        解析表达式结构
        
        Args:
            expression: 条件表达式
            
        Returns:
            解析结果字典
        """
        features = self.extract_features(expression)
        
        # 统计操作符
        operators_used = {}
        for op_symbol in self._operators.keys():
            count = expression.count(op_symbol)
            if count > 0:
                operators_used[op_symbol] = count
        
        # 估算复杂度
        complexity = len(features) + len(operators_used)
        
        return {
            "features": features,
            "feature_count": len(features),
            "operators": operators_used,
            "complexity": complexity,
            "length": len(expression),
        }
    
    def get_condition_templates(self) -> List[Dict[str, str]]:
        """
        获取常用条件模板
        
        Returns:
            模板列表
        """
        return [
            {
                "name": "大阴线底部反转",
                "expression": "(return_1 < -0.03) & (lower_shadow_ratio > 0.4) & (volume_ratio > 1.5)",
                "description": "大跌+长下影线+放量",
                "category": "反转",
            },
            {
                "name": "突破新高",
                "expression": "(new_high_20 == 1) & (volume_ratio > 1.2) & (ma_slope_20 > 0)",
                "description": "创20日新高+放量+均线向上",
                "category": "突破",
            },
            {
                "name": "RSI超卖",
                "expression": "(rsi_14 < 30) & (rsi_14 > rsi_14.shift(1))",
                "description": "RSI低于30后开始反弹",
                "category": "反转",
            },
            {
                "name": "回踩均线支撑",
                "expression": "(ma_slope_20 > 0) & (price_to_ma20 > -0.03) & (price_to_ma20 < 0.01)",
                "description": "上升趋势中回踩MA20",
                "category": "回调",
            },
            {
                "name": "放量突破",
                "expression": "(volume_spike == 1) & (is_green == 1) & (body_ratio > 0.5)",
                "description": "成交量突增+阳线+实体比例大",
                "category": "成交量",
            },
            {
                "name": "锤子线",
                "expression": "(is_hammer == 1) & (volume_ratio > 1.0) & (return_1 < -0.02)",
                "description": "锤子线形态+放量+下跌",
                "category": "形态",
            },
            {
                "name": "均线多头排列",
                "expression": "(ma_alignment == 1) & (close > ma5) & (volume_ratio > 0.8)",
                "description": "均线多头排列+价格在均线上方",
                "category": "趋势",
            },
            {
                "name": "缩量盘整",
                "expression": "(volume_shrink == 1) & (abs(return_1) < 0.02) & (ma_slope_20 > 0)",
                "description": "缩量+窄幅波动+均线向上",
                "category": "盘整",
            },
        ]
    
    def suggest_features(self, keyword: str) -> List[str]:
        """
        根据关键词建议特征
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            相关特征名称列表
        """
        features = self.registry.search_features(keyword)
        return [f.name for f in features]
    
    def format_expression(self, expression: str, indent: int = 0) -> str:
        """
        格式化条件表达式（美化显示）
        
        Args:
            expression: 条件表达式
            indent: 缩进级别
            
        Returns:
            格式化后的表达式
        """
        # 简单格式化：在 & 和 | 处换行
        formatted = expression.replace(' & ', '\n  & ')
        formatted = formatted.replace(' | ', '\n  | ')
        
        if indent > 0:
            lines = formatted.split('\n')
            indent_str = '  ' * indent
            formatted = '\n'.join(indent_str + line for line in lines)
        
        return formatted
    
    def evaluate_on_data(
        self,
        expression: str,
        data: pd.DataFrame
    ) -> pd.Series:
        """
        在数据上评估条件
        
        Args:
            expression: 条件表达式
            data: K线数据（需包含所需特征）
            
        Returns:
            布尔Series
        """
        # 验证表达式
        valid, error, features = self.validate_expression(expression, data)
        if not valid:
            raise ValueError(f"条件表达式无效: {error}")
        
        # 准备命名空间
        namespace = {'np': pd.np if hasattr(pd, 'np') else None, 'pd': pd}
        
        # 添加特征
        for feature in features:
            if feature in data.columns:
                namespace[feature] = data[feature]
            else:
                raise ValueError(f"数据中缺少特征: {feature}")
        
        # 添加OHLCV
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in data.columns:
                namespace[col] = data[col]
        
        # 执行表达式
        try:
            result = eval(expression, {"__builtins__": {}}, namespace)
            
            if isinstance(result, pd.Series):
                return result.fillna(False).astype(bool)
            else:
                return pd.Series([bool(result)] * len(data), index=data.index)
        except Exception as e:
            raise ValueError(f"表达式执行失败: {e}")
    
    def explain_condition(self, expression: str) -> str:
        """
        解释条件表达式（生成人类可读描述）
        
        Args:
            expression: 条件表达式
            
        Returns:
            人类可读的描述
        """
        parse_result = self.parse_expression(expression)
        
        explanation = f"条件包含 {parse_result['feature_count']} 个特征：\n"
        
        for feature_name in parse_result['features']:
            feature_def = self.registry.get_feature(feature_name)
            if feature_def:
                explanation += f"  - {feature_name}: {feature_def.display_name} ({feature_def.description})\n"
        
        explanation += f"\n复杂度: {parse_result['complexity']}"
        
        return explanation


# ========================================================================
# 便捷函数
# ========================================================================

def quick_condition(feature: str, operator: str, value: float) -> str:
    """快速构建简单条件"""
    builder = ConditionBuilder()
    return builder.build_simple_condition(feature, operator, value)


def validate_condition(expression: str) -> Tuple[bool, str]:
    """快速验证条件"""
    builder = ConditionBuilder()
    valid, error, _ = builder.validate_expression(expression)
    return valid, error
