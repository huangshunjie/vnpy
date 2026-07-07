"""
quant_research/model/artifact_model.py  — Phase 10 扩展版
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..constant import ArtifactType

ARTIFACT_TYPE_LABELS = {
    ArtifactType.MODEL:  "模型文件",
    ArtifactType.REPORT: "报告",
    ArtifactType.CSV:    "CSV 数据",
    ArtifactType.EXCEL:  "Excel",
    ArtifactType.IMAGE:  "图片",
    ArtifactType.LOG:    "日志",
    ArtifactType.CONFIG: "配置",
    ArtifactType.OTHER:  "其他",
}


@dataclass
class ArtifactRecord:
    artifact_id:    str           = ""
    name:           str           = ""
    artifact_type:  ArtifactType  = ArtifactType.OTHER
    description:    str           = ""
    file_path:      str           = ""
    file_size_kb:   float         = 0.0
    checksum:       str           = ""
    version:        str           = "v1.0"
    author:         str           = ""

    # 关联
    experiment_id:  Optional[str] = None
    pipeline_id:    Optional[str] = None
    strategy_id:    Optional[str] = None
    model_id:       Optional[str] = None
    backtest_id:    Optional[str] = None
    report_id:      Optional[str] = None

    # 元信息
    metadata:       Dict[str, Any] = field(default_factory=dict)
    tags:           List[str]      = field(default_factory=list)
    is_archived:    bool           = False
    download_count: int            = 0

    created_at:     datetime       = field(default_factory=datetime.now)
    updated_at:     datetime       = field(default_factory=datetime.now)
    created_by:     str            = ""

    def to_dict(self) -> dict:
        return {
            "artifact_id":   self.artifact_id,
            "name":          self.name,
            "artifact_type": self.artifact_type.value,
            "version":       self.version,
            "author":        self.author,
            "file_path":     self.file_path,
            "file_size_kb":  round(self.file_size_kb, 2),
            "is_archived":   self.is_archived,
            "created_at":    self.created_at.isoformat(),
            "updated_at":    self.updated_at.isoformat(),
        }
