"""
ConditionInsightManager — 条件智能分析管理器

负责：
1. 注册和存储所有条件的 Insight 数据
2. 按 ConditionIndicator 查询
3. 支持 JSON 批量导入/导出
4. 支持未来插件扩展
"""
from __future__ import annotations
from typing import Dict, Optional
import json
from pathlib import Path

from ..constant import ConditionIndicator
from .schema import ConditionInsight


class ConditionInsightManager:
    """
    全局条件 Insight 管理器（单例模式）

    使用方法：
        mgr = ConditionInsightManager.instance()
        insight = mgr.get(ConditionIndicator.VOLUME_PRICE_UP)
    """
    _instance: Optional["ConditionInsightManager"] = None

    def __init__(self):
        self._registry: Dict[ConditionIndicator, ConditionInsight] = {}

    @classmethod
    def instance(cls) -> "ConditionInsightManager":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load_builtin()
        return cls._instance

    def register(self, indicator: ConditionIndicator,
                 insight: ConditionInsight) -> None:
        """注册一个条件的 Insight"""
        self._registry[indicator] = insight

    def get(self, indicator: ConditionIndicator) -> Optional[ConditionInsight]:
        """获取指定条件的 Insight，未注册返回 None"""
        return self._registry.get(indicator)

    def has(self, indicator: ConditionIndicator) -> bool:
        return indicator in self._registry

    # 别名，兼容两种调用方式
    get_insight = get

    def all_indicators(self) -> list:
        return list(self._registry.keys())

    def count(self) -> int:
        return len(self._registry)

    def list_categories(self) -> list:
        """列出所有已注册 Insight 的分类（去重）"""
        cats = set()
        for insight in self._registry.values():
            if insight.category:
                cats.add(insight.category)
        return sorted(cats)

    # ── JSON 导入/导出 ──

    def export_json(self, path: str) -> None:
        """导出全部 Insight 为 JSON 文件"""
        data = {}
        for ind, insight in self._registry.items():
            data[ind.value] = insight.to_dict()
        Path(path).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def import_json(self, path: str) -> int:
        """从 JSON 文件导入 Insight，返回导入数量"""
        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text)
        count = 0
        for key, val in data.items():
            try:
                ind = ConditionIndicator(key)
                self._registry[ind] = ConditionInsight.from_dict(val)
                count += 1
            except (ValueError, KeyError):
                continue
        return count

    # ── 内置数据加载 ──

    def _load_builtin(self) -> None:
        """加载内置的 Insight 数据"""
        from .templates import BUILTIN_INSIGHTS
        for indicator, insight in BUILTIN_INSIGHTS.items():
            self._registry[indicator] = insight