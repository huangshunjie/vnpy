"""
quant_research/registry/report_registry.py  — Phase 9 完整实现
"""
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from ..model.report_model import ReportRecord, ReportSection
from ..constant import ReportFormat


class ReportRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, ReportRecord] = {}
        self._sec_counter: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, record: ReportRecord) -> ReportRecord:
        self._records[record.report_id] = record
        return record

    def get(self, report_id: str) -> Optional[ReportRecord]:
        return self._records.get(report_id)

    def list(self) -> List[ReportRecord]:
        return list(self._records.values())

    def update(self, record: ReportRecord) -> None:
        self._records[record.report_id] = record

    def delete(self, report_id: str) -> None:
        self._records.pop(report_id, None)

    def clear(self) -> None:
        self._records.clear()
        self._sec_counter.clear()

    # ------------------------------------------------------------------
    # 过滤 / 搜索
    # ------------------------------------------------------------------

    def filter(
        self,
        report_type:  Optional[str]  = None,
        report_format: Optional[ReportFormat] = None,
        author:       Optional[str]  = None,
        tag:          Optional[str]  = None,
        published:    Optional[bool] = None,
    ) -> List[ReportRecord]:
        result = list(self._records.values())
        if report_type is not None:
            result = [r for r in result if r.report_type == report_type]
        if report_format is not None:
            result = [r for r in result if r.report_format == report_format]
        if author is not None:
            result = [r for r in result
                      if author.lower() in r.author.lower()]
        if tag is not None:
            result = [r for r in result if tag in r.tags]
        if published is not None:
            result = [r for r in result if r.is_published == published]
        return result

    def search(self, keyword: str) -> List[ReportRecord]:
        kw = keyword.lower()
        return [
            r for r in self._records.values()
            if kw in r.title.lower()
            or kw in r.description.lower()
            or kw in r.summary.lower()
            or kw in r.author.lower()
            or kw in r.report_type.lower()
            or any(kw in t.lower() for t in r.tags)
        ]

    # ------------------------------------------------------------------
    # 章节管理
    # ------------------------------------------------------------------

    def add_section(
        self,
        report_id: str,
        title:     str,
        content:   str = "",
        order:     int = 0,
    ) -> Optional[ReportSection]:
        record = self._records.get(report_id)
        if record is None:
            return None
        count = self._sec_counter.get(report_id, 0) + 1
        self._sec_counter[report_id] = count
        sec = ReportSection(
            section_id = f"SEC-{report_id}-{count:03d}",
            title      = title,
            content    = content,
            order      = order if order else count,
        )
        record.sections.append(sec)
        record.sections.sort(key=lambda s: s.order)
        record.updated_at = datetime.now()
        return sec

    def update_section(
        self, report_id: str, section_id: str,
        title: str = "", content: str = "",
    ) -> None:
        record = self._records.get(report_id)
        if record is None:
            return
        for sec in record.sections:
            if sec.section_id == section_id:
                if title:
                    sec.title = title
                if content:
                    sec.content = content
                record.updated_at = datetime.now()
                break

    def remove_section(self, report_id: str, section_id: str) -> None:
        record = self._records.get(report_id)
        if record:
            record.sections = [s for s in record.sections
                               if s.section_id != section_id]
            record.updated_at = datetime.now()

    # ------------------------------------------------------------------
    # 发布 / 取消发布
    # ------------------------------------------------------------------

    def publish(self, report_id: str) -> None:
        record = self._records.get(report_id)
        if record:
            record.is_published = True
            record.published_at = datetime.now()
            record.updated_at   = datetime.now()

    def unpublish(self, report_id: str) -> None:
        record = self._records.get(report_id)
        if record:
            record.is_published = False
            record.published_at = None
            record.updated_at   = datetime.now()

    def increment_view(self, report_id: str) -> None:
        record = self._records.get(report_id)
        if record:
            record.view_count += 1
