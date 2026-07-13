"""
data_intelligence_ai/model/feature_model.py  (Phase 2)

FeatureRecord    — 单条特征记录（含版本、谱系）
FeatureLineage   — 特征谱系追踪
FeatureVersion   — 特征版本记录
FeatureState     — Feature Store 当前状态快照
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import FeatureType, DataType


@dataclass
class FeatureLineage:
    """特征谱系：记录特征来源与派生关系。"""
    feature_name:  str       = ""
    source_type:   DataType  = DataType.MARKET
    source_id:     str       = ""        # 原始数据 record_id
    compute_fn:    str       = ""        # 计算函数名
    dependencies:  list[str] = field(default_factory=list)   # 依赖的其他特征名
    created_at:    datetime  = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "feature_name": self.feature_name,
            "source_type":  self.source_type.value,
            "source_id":    self.source_id,
            "compute_fn":   self.compute_fn,
            "dependencies": self.dependencies,
            "created_at":   str(self.created_at)[:19],
        }


@dataclass
class FeatureVersion:
    """单个特征的版本记录。"""
    feature_name:   str          = ""
    symbol:         str          = ""
    version:        int          = 1
    value:          float        = 0.0
    previous_value: float        = 0.0
    delta:          float        = 0.0
    is_active:      bool         = True
    overwritten_by: str          = ""   # 被哪个版本覆写
    source_record:  str          = ""
    created_at:     datetime     = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "feature_name":   self.feature_name,
            "symbol":         self.symbol,
            "version":        self.version,
            "value":          round(self.value,          8),
            "previous_value": round(self.previous_value, 8),
            "delta":          round(self.delta,          8),
            "is_active":      self.is_active,
            "source_record":  self.source_record,
            "created_at":     str(self.created_at)[:19],
        }


@dataclass
class FeatureRecord:
    """
    单条特征记录（Phase 2 完整版）。

    结构：(feature_name, timestamp, symbol, value)
    + version, type, source, lineage
    """
    feature_id:    str         = ""
    feature_name:  str         = ""
    feature_type:  FeatureType = FeatureType.PRICE
    symbol:        str         = ""
    timestamp:     datetime    = field(default_factory=datetime.now)
    value:         float       = 0.0
    version:       int         = 1
    source:        str         = ""   # source module / data type
    source_record: str         = ""   # original DataRecord.record_id
    lineage:       FeatureLineage | None = None
    metadata:      dict        = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "feature_id":   self.feature_id,
            "feature_name": self.feature_name,
            "feature_type": self.feature_type.value,
            "symbol":       self.symbol,
            "timestamp":    str(self.timestamp)[:19],
            "value":        round(self.value, 8),
            "version":      self.version,
            "source":       self.source,
            "source_record":self.source_record,
            "lineage":      self.lineage.to_dict() if self.lineage else {},
            "metadata":     self.metadata,
        }


@dataclass
class FeatureState:
    """Feature Store 当前状态快照（Phase 2）。"""
    total_features:   int   = 0
    active_features:  int   = 0
    type_counts:      dict  = field(default_factory=dict)
    symbol_counts:    dict  = field(default_factory=dict)
    latest_version:   int   = 1
    total_versions:   int   = 0
    overwrite_count:  int   = 0

    # 近期写入速率（每分钟）
    write_rate:       float = 0.0
    updated_at:       datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "total_features":  self.total_features,
            "active_features": self.active_features,
            "type_counts":     self.type_counts,
            "symbol_counts":   self.symbol_counts,
            "latest_version":  self.latest_version,
            "total_versions":  self.total_versions,
            "overwrite_count": self.overwrite_count,
            "write_rate":      round(self.write_rate, 2),
            "updated_at":      str(self.updated_at)[:19],
        }
