"""
screening/model/template.py

选股模板与版本管理数据模型（Phase 1）。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..constant import TemplateCategory


@dataclass
class TemplateVersion:
    """模板单个历史版本快照。"""
    version: int
    snapshot: Dict[str, Any]              # 完整模板配置的 dict 序列化
    comment: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "snapshot": self.snapshot,
            "comment": self.comment,
            "created_at": str(self.created_at)[:19],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TemplateVersion":
        return cls(
            version=int(d["version"]),
            snapshot=dict(d.get("snapshot", {})),
            comment=d.get("comment", ""),
        )


@dataclass
class ScreeningTemplate:
    """
    选股模板：将 Universe 配置、条件树、因子配置打包成可复用的模板，
    并支持多版本管理。
    """
    template_id: str
    name: str
    category: TemplateCategory = TemplateCategory.CUSTOM
    description: str = ""

    universe_config: Dict[str, Any] = field(default_factory=dict)
    condition_tree: Dict[str, Any] = field(default_factory=dict)
    factor_config: Dict[str, Any] = field(default_factory=dict)
    risk_config: Dict[str, Any] = field(default_factory=dict)
    portfolio_config: Dict[str, Any] = field(default_factory=dict)

    current_version: int = 1
    versions: List[TemplateVersion] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    author: str = ""
    tags: List[str] = field(default_factory=list)

    def snapshot(self, comment: str = "") -> TemplateVersion:
        """将当前配置保存为一个新版本快照。"""
        self.current_version += 1
        ver = TemplateVersion(
            version=self.current_version,
            snapshot=self.to_dict(),
            comment=comment,
        )
        self.versions.append(ver)
        self.updated_at = datetime.now()
        return ver

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "universe_config": dict(self.universe_config),
            "condition_tree": dict(self.condition_tree),
            "factor_config": dict(self.factor_config),
            "risk_config": dict(self.risk_config),
            "portfolio_config": dict(self.portfolio_config),
            "current_version": self.current_version,
            "created_at": str(self.created_at)[:19],
            "updated_at": str(self.updated_at)[:19],
            "author": self.author,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ScreeningTemplate":
        return cls(
            template_id=d["template_id"],
            name=d["name"],
            category=TemplateCategory(d.get("category", TemplateCategory.CUSTOM.value)),
            description=d.get("description", ""),
            universe_config=dict(d.get("universe_config", {})),
            condition_tree=dict(d.get("condition_tree", {})),
            factor_config=dict(d.get("factor_config", {})),
            risk_config=dict(d.get("risk_config", {})),
            portfolio_config=dict(d.get("portfolio_config", {})),
            current_version=int(d.get("current_version", 1)),
            author=d.get("author", ""),
            tags=list(d.get("tags", [])),
        )
