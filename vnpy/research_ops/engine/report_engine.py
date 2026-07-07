"""
research_ops/engine/report_engine.py  — Phase 1 骨架
负责：报告 CRUD / 章节管理 / Markdown 渲染 / 模板管理 / 发布。
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from ..constant import ReportFormat, ReportType
from ..model.report_model import ReportRecord, ReportSection, ReportTemplate
from ..repository.memory import InMemoryRepository
from ..utils.id_gen import gen_report_id, gen_section_id, gen_template_id


class ReportEngine:
    def __init__(self) -> None:
        self._rpt_repo:  InMemoryRepository = InMemoryRepository()
        self._tmpl_repo: InMemoryRepository = InMemoryRepository()

    # ------------------------------------------------------------------
    # Report CRUD
    # ------------------------------------------------------------------

    def create_report(
        self,
        title:         str,
        project_id:    str        = "",
        report_type:   ReportType = ReportType.RESEARCH,
        report_format: ReportFormat = ReportFormat.MARKDOWN,
        description:   str        = "",
        author:        str        = "",
        summary:       str        = "",
        experiment_id: Optional[str] = None,
        strategy_id:   Optional[str] = None,
        backtest_id:   Optional[str] = None,
        feature_ids:   Optional[List[str]] = None,
        model_ids:     Optional[List[str]] = None,
        output_path:   str        = "",
        tags:          Optional[List[str]] = None,
        created_by:    str        = "",
    ) -> ReportRecord:
        now = datetime.now()
        rpt = ReportRecord(
            report_id     = gen_report_id(),
            project_id    = project_id,
            title         = title,
            description   = description,
            report_type   = report_type,
            report_format = report_format,
            author        = author,
            summary       = summary,
            experiment_id = experiment_id,
            strategy_id   = strategy_id,
            backtest_id   = backtest_id,
            feature_ids   = feature_ids or [],
            model_ids     = model_ids   or [],
            output_path   = output_path,
            tags          = tags or [],
            created_by    = created_by,
            created_at    = now,
            updated_at    = now,
        )
        self._rpt_repo.save(rpt)
        return rpt

    def get_report(self, report_id: str) -> Optional[ReportRecord]:
        return self._rpt_repo.get(report_id)

    def list_reports(
        self,
        project_id:  Optional[str]        = None,
        report_type: Optional[ReportType] = None,
    ) -> List[ReportRecord]:
        result = self._rpt_repo.list()
        if project_id:
            result = [r for r in result if r.project_id == project_id]
        if report_type:
            result = [r for r in result if r.report_type == report_type]
        return result

    def update_report(self, rpt: ReportRecord) -> None:
        rpt.updated_at = datetime.now()
        self._rpt_repo.save(rpt)

    def delete_report(self, report_id: str) -> None:
        self._rpt_repo.delete(report_id)

    def publish_report(self, report_id: str) -> None:
        rpt = self._rpt_repo.get(report_id)
        if rpt:
            rpt.is_published = True
            rpt.published_at = datetime.now()
            rpt.updated_at   = datetime.now()
            self._rpt_repo.save(rpt)

    def unpublish_report(self, report_id: str) -> None:
        rpt = self._rpt_repo.get(report_id)
        if rpt:
            rpt.is_published = False
            rpt.published_at = None
            rpt.updated_at   = datetime.now()
            self._rpt_repo.save(rpt)

    def search_reports(self, keyword: str) -> List[ReportRecord]:
        return self._rpt_repo.search(
            keyword, fields=["title", "description", "summary", "tags"])

    # ------------------------------------------------------------------
    # Section 管理
    # ------------------------------------------------------------------

    def add_section(
        self,
        report_id: str,
        title:     str,
        content:   str = "",
        order:     int = 0,
    ) -> Optional[ReportSection]:
        rpt = self._rpt_repo.get(report_id)
        if not rpt:
            return None
        sec = ReportSection(
            section_id = gen_section_id(),
            report_id  = report_id,
            title      = title,
            content    = content,
            order      = order or (len(rpt.sections) + 1),
        )
        rpt.sections.append(sec)
        rpt.sections.sort(key=lambda s: s.order)
        rpt.updated_at = datetime.now()
        self._rpt_repo.save(rpt)
        return sec

    def update_section(
        self,
        report_id:  str,
        section_id: str,
        title:      str = "",
        content:    str = "",
    ) -> None:
        rpt = self._rpt_repo.get(report_id)
        if not rpt:
            return
        for sec in rpt.sections:
            if sec.section_id == section_id:
                if title:   sec.title   = title
                if content: sec.content = content
        rpt.updated_at = datetime.now()
        self._rpt_repo.save(rpt)

    def remove_section(self, report_id: str, section_id: str) -> None:
        rpt = self._rpt_repo.get(report_id)
        if rpt:
            rpt.sections = [s for s in rpt.sections
                            if s.section_id != section_id]
            rpt.updated_at = datetime.now()
            self._rpt_repo.save(rpt)

    # ------------------------------------------------------------------
    # Markdown 渲染（Phase 1 基础实现）
    # ------------------------------------------------------------------

    def render_markdown(self, report_id: str) -> str:
        rpt = self._rpt_repo.get(report_id)
        if not rpt:
            return ""
        lines = [
            f"# {rpt.title}",
            f"> **作者**：{rpt.author}  **类型**：{rpt.report_type.value}",
            "",
            "---",
            "",
        ]
        if rpt.summary:
            lines += ["## 摘要", "", rpt.summary, ""]
        for sec in sorted(rpt.sections, key=lambda s: s.order):
            lines += [f"## {sec.title}", "", sec.content, ""]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Template
    # ------------------------------------------------------------------

    def create_template(
        self,
        name:        str,
        content:     str        = "",
        description: str        = "",
        report_type: ReportType = ReportType.CUSTOM,
        created_by:  str        = "",
    ) -> ReportTemplate:
        tmpl = ReportTemplate(
            template_id = gen_template_id(),
            name        = name,
            description = description,
            content     = content,
            report_type = report_type,
            created_by  = created_by,
        )
        self._tmpl_repo.save(tmpl)
        return tmpl

    def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        return self._tmpl_repo.get(template_id)

    def list_templates(self) -> List[ReportTemplate]:
        return self._tmpl_repo.list()

    def apply_template(
        self, template_id: str, report_id: str
    ) -> None:
        tmpl = self._tmpl_repo.get(template_id)
        rpt  = self._rpt_repo.get(report_id)
        if tmpl and rpt:
            rpt.summary    = tmpl.content
            rpt.updated_at = datetime.now()
            self._rpt_repo.save(rpt)

    def stats(self) -> dict:
        rpts = self._rpt_repo.list()
        return {
            "reports":   len(rpts),
            "published": sum(1 for r in rpts if r.is_published),
            "drafts":    sum(1 for r in rpts if not r.is_published),
            "templates": self._tmpl_repo.count(),
        }
