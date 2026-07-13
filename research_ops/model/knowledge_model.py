"""
research_ops/model/knowledge_model.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from ..constant import NoteType, Priority


@dataclass
class KnowledgeNote:
    note_id:      str       = ""
    project_id:   str       = ""
    title:        str       = ""
    content:      str       = ""
    note_type:    NoteType  = NoteType.RESEARCH
    priority:     Priority  = Priority.MEDIUM
    author:       str       = ""
    tags:         List[str] = field(default_factory=list)
    related_ids:  List[str] = field(default_factory=list)
    is_archived:  bool      = False
    view_count:   int       = 0
    created_at:   datetime  = field(default_factory=datetime.now)
    updated_at:   datetime  = field(default_factory=datetime.now)
    created_by:   str       = ""

    def to_dict(self) -> dict:
        return {
            "note_id":   self.note_id,
            "title":     self.title,
            "note_type": self.note_type.value,
            "priority":  self.priority.value,
            "author":    self.author,
            "tags":      self.tags,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ExperienceCard:
    card_id:      str       = ""
    project_id:   str       = ""
    title:        str       = ""
    context:      str       = ""
    insight:      str       = ""
    lesson:       str       = ""
    applicable_to: List[str] = field(default_factory=list)
    author:       str       = ""
    tags:         List[str] = field(default_factory=list)
    experiment_ids: List[str] = field(default_factory=list)
    strategy_ids: List[str] = field(default_factory=list)
    created_at:   datetime  = field(default_factory=datetime.now)
    updated_at:   datetime  = field(default_factory=datetime.now)
    created_by:   str       = ""

    def to_dict(self) -> dict:
        return {
            "card_id":    self.card_id,
            "title":      self.title,
            "author":     self.author,
            "tags":       self.tags,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class FailureCaseRecord:
    case_id:       str       = ""
    project_id:    str       = ""
    title:         str       = ""
    symptom:       str       = ""
    root_cause:    str       = ""
    impact:        str       = ""
    resolution:    str       = ""
    prevention:    str       = ""
    author:        str       = ""
    severity:      str       = "medium"
    tags:          List[str] = field(default_factory=list)
    related_ids:   List[str] = field(default_factory=list)
    is_resolved:   bool      = False
    resolved_at:   Optional[datetime] = None
    created_at:    datetime  = field(default_factory=datetime.now)
    updated_at:    datetime  = field(default_factory=datetime.now)
    created_by:    str       = ""

    def to_dict(self) -> dict:
        return {
            "case_id":    self.case_id,
            "title":      self.title,
            "severity":   self.severity,
            "is_resolved": self.is_resolved,
            "created_at": self.created_at.isoformat(),
        }
