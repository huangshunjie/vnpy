"""
research_ops/engine/knowledge_engine.py  — Phase 1 骨架
负责：量化知识笔记 / 经验卡片 / 失败案例 / 全文检索。
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from ..constant import NoteType, Priority
from ..model.knowledge_model import KnowledgeNote, ExperienceCard, FailureCaseRecord
from ..repository.memory import InMemoryRepository
from ..utils.id_gen import gen_note_id, gen_card_id, gen_case_id


class KnowledgeEngine:
    def __init__(self) -> None:
        self._note_repo: InMemoryRepository = InMemoryRepository()
        self._card_repo: InMemoryRepository = InMemoryRepository()
        self._case_repo: InMemoryRepository = InMemoryRepository()

    # ------------------------------------------------------------------
    # KnowledgeNote
    # ------------------------------------------------------------------

    def create_note(
        self,
        title:       str,
        content:     str              = "",
        project_id:  str              = "",
        note_type:   NoteType         = NoteType.RESEARCH,
        priority:    Priority         = Priority.MEDIUM,
        author:      str              = "",
        tags:        Optional[List[str]] = None,
        related_ids: Optional[List[str]] = None,
        created_by:  str              = "",
    ) -> KnowledgeNote:
        now  = datetime.now()
        note = KnowledgeNote(
            note_id     = gen_note_id(),
            project_id  = project_id,
            title       = title,
            content     = content,
            note_type   = note_type,
            priority    = priority,
            author      = author,
            tags        = tags        or [],
            related_ids = related_ids or [],
            created_by  = created_by,
            created_at  = now,
            updated_at  = now,
        )
        self._note_repo.save(note)
        return note

    def get_note(self, note_id: str) -> Optional[KnowledgeNote]:
        return self._note_repo.get(note_id)

    def list_notes(
        self,
        project_id: Optional[str]     = None,
        note_type:  Optional[NoteType] = None,
    ) -> List[KnowledgeNote]:
        result = self._note_repo.list()
        if project_id: result = [n for n in result if n.project_id == project_id]
        if note_type:  result = [n for n in result if n.note_type  == note_type]
        return result

    def update_note(self, note: KnowledgeNote) -> None:
        note.updated_at = datetime.now()
        self._note_repo.save(note)

    def delete_note(self, note_id: str) -> None:
        self._note_repo.delete(note_id)

    def archive_note(self, note_id: str) -> None:
        note = self._note_repo.get(note_id)
        if note:
            note.is_archived = True
            note.updated_at  = datetime.now()
            self._note_repo.save(note)

    def search_notes(self, keyword: str) -> List[KnowledgeNote]:
        return self._note_repo.search(
            keyword, fields=["title", "content", "tags"])

    # ------------------------------------------------------------------
    # ExperienceCard
    # ------------------------------------------------------------------

    def create_card(
        self,
        title:          str,
        context:        str              = "",
        insight:        str              = "",
        lesson:         str              = "",
        project_id:     str              = "",
        author:         str              = "",
        tags:           Optional[List[str]] = None,
        experiment_ids: Optional[List[str]] = None,
        strategy_ids:   Optional[List[str]] = None,
        applicable_to:  Optional[List[str]] = None,
        created_by:     str              = "",
    ) -> ExperienceCard:
        now  = datetime.now()
        card = ExperienceCard(
            card_id        = gen_card_id(),
            project_id     = project_id,
            title          = title,
            context        = context,
            insight        = insight,
            lesson         = lesson,
            applicable_to  = applicable_to  or [],
            author         = author,
            tags           = tags           or [],
            experiment_ids = experiment_ids or [],
            strategy_ids   = strategy_ids   or [],
            created_by     = created_by,
            created_at     = now,
            updated_at     = now,
        )
        self._card_repo.save(card)
        return card

    def get_card(self, card_id: str) -> Optional[ExperienceCard]:
        return self._card_repo.get(card_id)

    def list_cards(self, project_id: Optional[str] = None) -> List[ExperienceCard]:
        if project_id:
            return self._card_repo.query(project_id=project_id)
        return self._card_repo.list()

    def update_card(self, card: ExperienceCard) -> None:
        card.updated_at = datetime.now()
        self._card_repo.save(card)

    def delete_card(self, card_id: str) -> None:
        self._card_repo.delete(card_id)

    def search_cards(self, keyword: str) -> List[ExperienceCard]:
        return self._card_repo.search(
            keyword, fields=["title", "context", "insight", "lesson", "tags"])

    # ------------------------------------------------------------------
    # FailureCaseRecord
    # ------------------------------------------------------------------

    def create_failure_case(
        self,
        title:       str,
        symptom:     str              = "",
        root_cause:  str              = "",
        impact:      str              = "",
        resolution:  str              = "",
        prevention:  str              = "",
        project_id:  str              = "",
        author:      str              = "",
        severity:    str              = "medium",
        tags:        Optional[List[str]] = None,
        related_ids: Optional[List[str]] = None,
        created_by:  str              = "",
    ) -> FailureCaseRecord:
        now  = datetime.now()
        case = FailureCaseRecord(
            case_id     = gen_case_id(),
            project_id  = project_id,
            title       = title,
            symptom     = symptom,
            root_cause  = root_cause,
            impact      = impact,
            resolution  = resolution,
            prevention  = prevention,
            author      = author,
            severity    = severity,
            tags        = tags        or [],
            related_ids = related_ids or [],
            created_by  = created_by,
            created_at  = now,
            updated_at  = now,
        )
        self._case_repo.save(case)
        return case

    def get_failure_case(self, case_id: str) -> Optional[FailureCaseRecord]:
        return self._case_repo.get(case_id)

    def list_failure_cases(
        self, project_id: Optional[str] = None, resolved: Optional[bool] = None
    ) -> List[FailureCaseRecord]:
        result = self._case_repo.list()
        if project_id is not None:
            result = [c for c in result if c.project_id == project_id]
        if resolved is not None:
            result = [c for c in result if c.is_resolved == resolved]
        return result

    def resolve_case(self, case_id: str) -> None:
        case = self._case_repo.get(case_id)
        if case:
            case.is_resolved = True
            case.resolved_at = datetime.now()
            case.updated_at  = datetime.now()
            self._case_repo.save(case)

    def update_failure_case(self, case: FailureCaseRecord) -> None:
        case.updated_at = datetime.now()
        self._case_repo.save(case)

    def delete_failure_case(self, case_id: str) -> None:
        self._case_repo.delete(case_id)

    def search_failure_cases(self, keyword: str) -> List[FailureCaseRecord]:
        return self._case_repo.search(
            keyword, fields=["title", "symptom", "root_cause", "tags"])

    # ------------------------------------------------------------------
    # 全文搜索（跨三种类型）
    # ------------------------------------------------------------------

    def search_all(self, keyword: str) -> dict:
        return {
            "notes":         self.search_notes(keyword),
            "cards":         self.search_cards(keyword),
            "failure_cases": self.search_failure_cases(keyword),
        }

    def stats(self) -> dict:
        return {
            "notes":          self._note_repo.count(),
            "experience_cards": self._card_repo.count(),
            "failure_cases":  self._case_repo.count(),
            "unresolved_cases": len(self.list_failure_cases(resolved=False)),
        }
