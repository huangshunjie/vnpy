"""
platform_engineering/model/config.py
配置版本化管理模型。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..constant import ConfigType


@dataclass
class ConfigVersion:
    version_id:  str      = ""
    version_tag: str      = ""
    data:        Dict[str, Any] = field(default_factory=dict)
    note:        str      = ""
    created_by:  str      = ""
    created_at:  datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "version_id":  self.version_id,
            "version_tag": self.version_tag,
            "note":        self.note,
            "created_by":  self.created_by,
            "created_at":  self.created_at.isoformat(),
        }


@dataclass
class ConfigRecord:
    config_id:    str        = ""
    name:         str        = ""
    config_type:  ConfigType = ConfigType.STRATEGY
    current_data: Dict[str, Any] = field(default_factory=dict)
    versions:     List[ConfigVersion] = field(default_factory=list)
    description:  str        = ""
    owner:        str        = ""
    tags:         List[str]  = field(default_factory=list)
    is_locked:    bool       = False
    created_by:   str        = ""
    created_at:   datetime   = field(default_factory=datetime.now)
    updated_at:   datetime   = field(default_factory=datetime.now)

    def current_version(self) -> Optional[ConfigVersion]:
        return self.versions[-1] if self.versions else None

    def to_dict(self) -> dict:
        return {
            "config_id":   self.config_id,
            "name":        self.name,
            "config_type": self.config_type.value,
            "is_locked":   self.is_locked,
            "owner":       self.owner,
            "versions":    len(self.versions),
            "created_at":  self.created_at.isoformat(),
        }
