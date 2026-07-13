"""
platform_engineering/model/deployment.py
策略部署模型。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from ..constant import DeployStage, DeployAction


@dataclass
class DeployVersion:
    version_id:   str      = ""
    version_tag:  str      = ""
    stage:        DeployStage = DeployStage.RESEARCH
    config_snapshot: Dict  = field(default_factory=dict)
    commit_hash:  str      = ""
    note:         str      = ""
    created_by:   str      = ""
    created_at:   datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "version_id":  self.version_id,
            "version_tag": self.version_tag,
            "stage":       self.stage.value,
            "commit_hash": self.commit_hash,
            "created_at":  self.created_at.isoformat(),
        }


@dataclass
class DeploymentRecord:
    deploy_id:     str        = ""
    strategy_id:   str        = ""
    strategy_name: str        = ""
    current_stage: DeployStage = DeployStage.RESEARCH
    current_version: str      = ""
    versions:      List[DeployVersion] = field(default_factory=list)
    approver:      str        = ""
    approve_note:  str        = ""
    is_frozen:     bool       = False
    tags:          List[str]  = field(default_factory=list)
    created_by:    str        = ""
    approved_at:   Optional[datetime] = None
    live_at:       Optional[datetime] = None
    paused_at:     Optional[datetime] = None
    retired_at:    Optional[datetime] = None
    created_at:    datetime   = field(default_factory=datetime.now)
    updated_at:    datetime   = field(default_factory=datetime.now)

    def latest_version(self) -> Optional[DeployVersion]:
        return self.versions[-1] if self.versions else None

    def to_dict(self) -> dict:
        return {
            "deploy_id":      self.deploy_id,
            "strategy_name":  self.strategy_name,
            "current_stage":  self.current_stage.value,
            "current_version": self.current_version,
            "is_frozen":      self.is_frozen,
            "created_at":     self.created_at.isoformat(),
        }
