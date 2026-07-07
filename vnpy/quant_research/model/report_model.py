"""
quant_research/model/report_model.py  — Phase 9 扩展版
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..constant import ReportFormat

REPORT_TYPES = [
    "research",     # 研究报告
    "backtest",     # 回测报告
    "strategy",     # 策略分析
    "factor",       # 因子分析
    "model",        # 模型评估
    "risk",         # 风险报告
    "daily",        # 日报
    "weekly",       # 周报
    "custom",       # 自定义
]


@dataclass
class ReportSection:
    """报告章节（用于结构化内容）。"""
    section_id: str              = ""
    title:      str              = ""
    content:    str              = ""
    order:      int              = 0
    metadata:   Dict[str, Any]   = field(default_factory=dict)


@dataclass
class ReportRecord:
    report_id:      str              = ""
    title:          str              = ""
    description:    str              = ""
    report_type:    str              = "research"
    report_format:  ReportFormat     = ReportFormat.MARKDOWN
    author:         str              = ""

    # 关联资源
    experiment_id:  Optional[str]    = None
    strategy_id:    Optional[str]    = None
    backtest_id:    Optional[str]    = None
    feature_ids:    List[str]        = field(default_factory=list)
    model_ids:      List[str]        = field(default_factory=list)
    artifact_ids:   List[str]        = field(default_factory=list)

    # 内容
    summary:        str              = ""
    sections:       List[ReportSection] = field(default_factory=list)
    output_path:    str              = ""

    # 元信息
    tags:           List[str]        = field(default_factory=list)
    is_published:   bool             = False
    published_at:   Optional[datetime] = None
    view_count:     int              = 0

    created_at:     datetime         = field(default_factory=datetime.now)
    updated_at:     datetime         = field(default_factory=datetime.now)
    created_by:     str              = ""

    def to_dict(self) -> dict:
        return {
            "report_id":   self.report_id,
            "title":       self.title,
            "report_type": self.report_type,
            "format":      self.report_format.value,
            "author":      self.author,
            "is_published":self.is_published,
            "created_at":  self.created_at.isoformat(),
            "updated_at":  self.updated_at.isoformat(),
        }
