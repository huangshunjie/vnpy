"""
data_intelligence_ai/model/data_model.py  (Phase 1 Stub)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import DataType, QualityStatus


@dataclass
class DataRecord:
    """单条原始数据记录（stub）。"""
    record_id:   str        = ""
    data_type:   DataType   = DataType.MARKET
    symbol:      str        = ""
    timestamp:   datetime   = field(default_factory=datetime.now)
    value:       float      = 0.0
    source:      str        = ""
    quality:     QualityStatus = QualityStatus.UNKNOWN

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "data_type": self.data_type.value,
            "symbol":    self.symbol,
            "timestamp": str(self.timestamp)[:19],
            "value":     self.value,
            "source":    self.source,
            "quality":   self.quality.value,
        }


@dataclass
class DataState:
    """数据接入系统状态快照（stub）。"""
    total_records:  int   = 0
    type_counts:    dict  = field(default_factory=dict)
    updated_at:     datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "total_records": self.total_records,
            "type_counts":   self.type_counts,
            "updated_at":    str(self.updated_at)[:19],
        }
