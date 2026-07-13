"""
research_ops/model/report_model.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..constant import ReportFormat, ReportType


@dataclass
class ReportSection:
    section_id: str           = ""
    report_id:  str           = ""
    title:      str           = ""
    content:    str           = ""
    order:      int           = 0
    metadata:   Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportTemplate:
    template_id:  str       = ""
    name:         str       = ""
    description:  str       = ""
    content:      str       = ""
    report_type:  ReportType = ReportType.CUSTOM
    created_at:   datetime  = field(default_factory=datetime.now)
    created_by:   str       = ""


@dataclass
class ReportRecord:
    report_id:      str        = ""
    project_id:     str        = ""
    title:          str        = ""
    description:    str        = ""
    report_type:    ReportType = ReportType.RESEARCH
    report_format:  ReportFormat = ReportFormat.MARKDOWN
    author:         str        = ""
    summary:        str        = ""
    sections:       List[ReportSection] = field(default_factory=list)
    experiment_id:  Optional[str] = None
    strategy_id:    Optional[str] = None
    backtest_id:    Optional[str] = None
    feature_ids:    List[str]  = field(default_factory=list)
    model_ids:      List[str]  = field(default_factory=list)
    output_path:    str        = ""
    is_published:   bool       = False
    published_at:   Optional[datetime] = None
    view_count:     int        = 0
    tags:           List[str]  = field(default_factory=list)
    created_at:     datetime   = field(default_factory=datetime.now)
    updated_at:     datetime   = field(default_factory=datetime.now)
    created_by:     str        = ""

    def to_dict(self) -> dict:
        return {
            "report_id":   self.report_id,
            "title":       self.title,
            "report_type": self.report_type.value,
            "format":      self.report_format.value,
            "author":      self.author,
            "is_published": self.is_published,
            "created_at":  self.created_at.isoformat(),
        }
