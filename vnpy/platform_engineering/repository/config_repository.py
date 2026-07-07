"""
platform_engineering/repository/config_repository.py
配置内存存储。
"""
from __future__ import annotations
from typing import Dict, List, Optional
from ..model.config import ConfigRecord, ConfigVersion
from ..constant import ConfigType


class ConfigRepository:
    def __init__(self) -> None:
        self._configs: Dict[str, ConfigRecord] = {}

    def save(self, config: ConfigRecord) -> None:
        self._configs[config.config_id] = config

    def get(self, config_id: str) -> Optional[ConfigRecord]:
        return self._configs.get(config_id)

    def list(self, config_type: Optional[ConfigType] = None) -> List[ConfigRecord]:
        items = list(self._configs.values())
        if config_type:
            items = [c for c in items if c.config_type == config_type]
        return sorted(items, key=lambda c: c.updated_at, reverse=True)

    def delete(self, config_id: str) -> None:
        self._configs.pop(config_id, None)

    def search(self, keyword: str) -> List[ConfigRecord]:
        kw = keyword.lower()
        return [c for c in self._configs.values()
                if kw in c.name.lower()
                or kw in (c.description or "").lower()
                or any(kw in t for t in c.tags)]

    def stats(self) -> dict:
        items = list(self._configs.values())
        return {
            "total":  len(items),
            "locked": sum(1 for c in items if c.is_locked),
            "by_type": {
                ct.value: sum(1 for c in items if c.config_type == ct)
                for ct in ConfigType
            },
        }
