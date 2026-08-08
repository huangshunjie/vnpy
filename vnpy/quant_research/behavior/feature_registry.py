"""
quant_research/behavior/feature_registry.py

特征注册中心
管理所有K线特征的定义、依赖关系和版本
"""
from __future__ import annotations
from typing import Dict, List, Optional, Set
from datetime import datetime

from ..model.kline_feature_model import (
    KLineFeatureDefinition,
    KLineFeatureType,
    FeatureComplexity
)
from ..model.kline_feature_presets import (
    PRESET_KLINE_FEATURES,
    get_feature_by_category,
    get_simple_features,
    get_condition_suitable_features,
    get_alpha_suitable_features,
    get_feature_summary
)


class FeatureRegistry:
    """
    K线特征注册中心
    
    职责：
    1. 管理所有预置和自定义特征定义
    2. 特征依赖关系解析
    3. 特征版本管理
    4. 特征查询和筛选
    """
    
    VERSION = "v1.0.0"
    
    def __init__(self):
        # 加载预置特征
        self._features: Dict[str, KLineFeatureDefinition] = {}
        self._load_preset_features()
        
        # 依赖关系缓存
        self._dependency_cache: Dict[str, List[str]] = {}
        
        # 自定义特征计数
        self._custom_feature_count = 0
    
    def _load_preset_features(self) -> None:
        """加载预置特征"""
        self._features.update(PRESET_KLINE_FEATURES)
        print(f"[FeatureRegistry] 已加载 {len(self._features)} 个预置特征")
    
    def register_feature(self, feature: KLineFeatureDefinition) -> None:
        """
        注册新特征
        
        Args:
            feature: 特征定义
        """
        if not feature.name:
            raise ValueError("特征名称不能为空")
        
        if feature.name in self._features:
            print(f"[警告] 特征 {feature.name} 已存在，将被覆盖")
        
        self._features[feature.name] = feature
        
        # 清空依赖缓存
        self._dependency_cache.clear()
        
        if not feature.author or feature.author == "system":
            self._custom_feature_count += 1
        
        print(f"[FeatureRegistry] 注册特征: {feature.name} ({feature.display_name})")
    
    def register_custom_feature(
        self,
        name: str,
        display_name: str,
        formula: str,
        feature_type: KLineFeatureType = KLineFeatureType.RETURN,
        description: str = "",
        dependencies: List[str] = None,
        **kwargs
    ) -> KLineFeatureDefinition:
        """
        快捷注册自定义特征
        
        Args:
            name: 特征名称
            display_name: 显示名称
            formula: 计算公式
            feature_type: 特征类型
            description: 描述
            dependencies: 依赖特征列表
            **kwargs: 其他参数
            
        Returns:
            创建的特征定义
        """
        feature = KLineFeatureDefinition(
            name=name,
            display_name=display_name,
            formula=formula,
            feature_type=feature_type,
            description=description or f"自定义特征: {display_name}",
            dependencies=dependencies or [],
            author="custom",
            created_at=datetime.now(),
            **kwargs
        )
        
        self.register_feature(feature)
        return feature
    
    def get_feature(self, name: str) -> Optional[KLineFeatureDefinition]:
        """获取特征定义"""
        return self._features.get(name)
    
    def has_feature(self, name: str) -> bool:
        """检查特征是否存在"""
        return name in self._features
    
    def list_features(
        self,
        feature_type: Optional[KLineFeatureType] = None,
        complexity: Optional[FeatureComplexity] = None,
        suitable_for_condition: Optional[bool] = None,
        suitable_for_alpha: Optional[bool] = None
    ) -> List[KLineFeatureDefinition]:
        """
        列出特征（支持多维度筛选）
        
        Args:
            feature_type: 按类型筛选
            complexity: 按复杂度筛选
            suitable_for_condition: 是否适合做条件
            suitable_for_alpha: 是否适合做因子
            
        Returns:
            符合条件的特征列表
        """
        features = list(self._features.values())
        
        if feature_type is not None:
            features = [f for f in features if f.feature_type == feature_type]
        
        if complexity is not None:
            features = [f for f in features if f.complexity == complexity]
        
        if suitable_for_condition is not None:
            features = [f for f in features if f.suitable_for_condition == suitable_for_condition]
        
        if suitable_for_alpha is not None:
            features = [f for f in features if f.suitable_for_alpha == suitable_for_alpha]
        
        return features
    
    def get_feature_names(self, **kwargs) -> List[str]:
        """获取特征名称列表（支持筛选）"""
        features = self.list_features(**kwargs)
        return [f.name for f in features]
    
    def resolve_dependencies(self, features: List[str]) -> List[str]:
        """
        解析特征依赖关系
        
        Args:
            features: 特征名称列表
            
        Returns:
            包含所有依赖的特征列表（按计算顺序排序）
        """
        # 检查缓存
        cache_key = ",".join(sorted(features))
        if cache_key in self._dependency_cache:
            return self._dependency_cache[cache_key].copy()
        
        result: List[str] = []
        visited: Set[str] = set()
        
        def visit(feature_name: str):
            if feature_name in visited:
                return
            
            visited.add(feature_name)
            
            # 获取特征定义
            feature_def = self.get_feature(feature_name)
            if not feature_def:
                print(f"[警告] 未知特征: {feature_name}")
                return
            
            # 先处理依赖
            if feature_def.dependencies:
                for dep in feature_def.dependencies:
                    visit(dep)
            
            # 再添加自己
            if feature_name not in result:
                result.append(feature_name)
        
        for feature in features:
            visit(feature)
        
        # 缓存结果
        self._dependency_cache[cache_key] = result.copy()
        
        return result
    
    def get_dependency_tree(self, feature_name: str) -> Dict:
        """
        获取特征的依赖树
        
        Args:
            feature_name: 特征名称
            
        Returns:
            依赖树字典
        """
        feature_def = self.get_feature(feature_name)
        if not feature_def:
            return {}
        
        tree = {
            "name": feature_name,
            "display_name": feature_def.display_name,
            "complexity": feature_def.complexity.value,
            "dependencies": []
        }
        
        if feature_def.dependencies:
            for dep in feature_def.dependencies:
                tree["dependencies"].append(self.get_dependency_tree(dep))
        
        return tree
    
    def validate_features(self, features: List[str]) -> tuple[bool, List[str]]:
        """
        验证特征列表
        
        Args:
            features: 特征名称列表
            
        Returns:
            (是否全部有效, 无效特征列表)
        """
        invalid_features = []
        
        for feature in features:
            if not self.has_feature(feature):
                invalid_features.append(feature)
        
        return len(invalid_features) == 0, invalid_features
    
    def get_statistics(self) -> Dict:
        """获取特征库统计信息"""
        stats = {
            "total_features": len(self._features),
            "preset_features": len(self._features) - self._custom_feature_count,
            "custom_features": self._custom_feature_count,
            "by_type": {},
            "by_complexity": {},
            "suitable_for_condition": 0,
            "suitable_for_alpha": 0,
            "has_dependencies": 0,
            "realtime_supported": 0,
        }
        
        for feature in self._features.values():
            # 按类型统计
            type_name = feature.feature_type.value
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1
            
            # 按复杂度统计
            complexity_name = feature.complexity.value
            stats["by_complexity"][complexity_name] = stats["by_complexity"].get(complexity_name, 0) + 1
            
            # 其他统计
            if feature.suitable_for_condition:
                stats["suitable_for_condition"] += 1
            
            if feature.suitable_for_alpha:
                stats["suitable_for_alpha"] += 1
            
            if feature.dependencies:
                stats["has_dependencies"] += 1
            
            if feature.realtime_supported:
                stats["realtime_supported"] += 1
        
        return stats
    
    def search_features(self, keyword: str) -> List[KLineFeatureDefinition]:
        """
        搜索特征
        
        Args:
            keyword: 关键词（搜索名称和描述）
            
        Returns:
            匹配的特征列表
        """
        keyword_lower = keyword.lower()
        results = []
        
        for feature in self._features.values():
            if (keyword_lower in feature.name.lower() or
                keyword_lower in feature.display_name.lower() or
                keyword_lower in feature.description.lower()):
                results.append(feature)
        
        return results
    
    def export_feature_list(self, output_format: str = "markdown") -> str:
        """
        导出特征列表
        
        Args:
            output_format: 输出格式 (markdown/csv/json)
            
        Returns:
            格式化的特征列表
        """
        if output_format == "markdown":
            return self._export_markdown()
        elif output_format == "csv":
            return self._export_csv()
        elif output_format == "json":
            return self._export_json()
        else:
            raise ValueError(f"不支持的格式: {output_format}")
    
    def _export_markdown(self) -> str:
        """导出为Markdown格式"""
        lines = ["# K线特征库", "", f"总计: {len(self._features)} 个特征", ""]
        
        # 按类型分组
        for feature_type in KLineFeatureType:
            features = self.list_features(feature_type=feature_type)
            if not features:
                continue
            
            lines.append(f"## {feature_type.value.upper()}")
            lines.append("")
            lines.append("| 名称 | 显示名称 | 描述 | 复杂度 | 回看周期 |")
            lines.append("|------|---------|------|--------|----------|")
            
            for f in features:
                lines.append(f"| {f.name} | {f.display_name} | {f.description[:30]}... | {f.complexity.value} | {f.lookback_period} |")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _export_csv(self) -> str:
        """导出为CSV格式"""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow([
            "名称", "显示名称", "类型", "描述", "公式",
            "复杂度", "回看周期", "依赖", "适合条件", "适合因子"
        ])
        
        # 写入数据
        for feature in self._features.values():
            writer.writerow([
                feature.name,
                feature.display_name,
                feature.feature_type.value,
                feature.description,
                feature.formula,
                feature.complexity.value,
                feature.lookback_period,
                ",".join(feature.dependencies) if feature.dependencies else "",
                "是" if feature.suitable_for_condition else "否",
                "是" if feature.suitable_for_alpha else "否",
            ])
        
        return output.getvalue()
    
    def _export_json(self) -> str:
        """导出为JSON格式"""
        import json
        
        data = {
            "version": self.VERSION,
            "total": len(self._features),
            "features": []
        }
        
        for feature in self._features.values():
            data["features"].append({
                "name": feature.name,
                "display_name": feature.display_name,
                "type": feature.feature_type.value,
                "description": feature.description,
                "formula": feature.formula,
                "complexity": feature.complexity.value,
                "lookback_period": feature.lookback_period,
                "dependencies": feature.dependencies,
                "suitable_for_condition": feature.suitable_for_condition,
                "suitable_for_alpha": feature.suitable_for_alpha,
            })
        
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def clear_cache(self) -> None:
        """清空依赖缓存"""
        self._dependency_cache.clear()


# ========================================================================
# 全局单例
# ========================================================================

_global_registry: Optional[FeatureRegistry] = None


def get_global_registry() -> FeatureRegistry:
    """获取全局特征注册中心实例"""
    global _global_registry
    if _global_registry is None:
        _global_registry = FeatureRegistry()
    return _global_registry


def reset_global_registry() -> None:
    """重置全局注册中心"""
    global _global_registry
    _global_registry = None
