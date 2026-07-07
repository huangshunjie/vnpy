"""Append Pipeline / Report / Knowledge / Governance / stats to engine.py"""
import pathlib
P = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\engine.py")

CHUNK2 = """
    # ==================================================================
    # Pipeline API
    # ==================================================================

    def create_pipeline(self, name: str, **kw) -> PipelineRecord:
        pl = self.pipeline.create_pipeline(name, **kw)
        from .event import EVENT_RO_PL_CREATED
        self._put(EVENT_RO_PL_CREATED, pl); return pl

    def get_pipeline(self, pipeline_id: str) -> Optional[PipelineRecord]:
        return self.pipeline.get_pipeline(pipeline_id)

    def list_pipelines(self, **kw) -> List[PipelineRecord]:
        return self.pipeline.list_pipelines(**kw)

    def delete_pipeline(self, pipeline_id: str) -> None:
        self.pipeline.delete_pipeline(pipeline_id)
        from .event import EVENT_RO_PL_DELETED
        self._put(EVENT_RO_PL_DELETED, pipeline_id)

    def add_pipeline_node(self, pipeline_id: str, name: str, **kw) -> Optional[DAGNode]:
        return self.pipeline.add_node(pipeline_id, name, **kw)

    def remove_pipeline_node(self, pipeline_id: str, node_id: str) -> None:
        self.pipeline.remove_node(pipeline_id, node_id)

    def start_pipeline(self, pipeline_id: str, **kw) -> Optional[PipelineRunRecord]:
        run = self.pipeline.start_pipeline(pipeline_id, **kw)
        if run:
            from .event import EVENT_RO_PL_STARTED
            self._put(EVENT_RO_PL_STARTED, run)
        return run

    def complete_pipeline(self, pipeline_id: str, **kw) -> None:
        self.pipeline.complete_pipeline(pipeline_id, **kw)
        from .event import EVENT_RO_PL_COMPLETED
        self._put(EVENT_RO_PL_COMPLETED, pipeline_id)

    def fail_pipeline(self, pipeline_id: str, **kw) -> None:
        self.pipeline.fail_pipeline(pipeline_id, **kw)
        from .event import EVENT_RO_PL_FAILED
        self._put(EVENT_RO_PL_FAILED, pipeline_id)

    def reset_pipeline(self, pipeline_id: str) -> None:
        self.pipeline.reset_pipeline(pipeline_id)

    def search_pipelines(self, keyword: str) -> List[PipelineRecord]:
        return self.pipeline.search_pipelines(keyword)

    def get_pipeline_execution_order(self, pipeline_id: str) -> List[str]:
        return self.pipeline.get_execution_order(pipeline_id)

    # ==================================================================
    # Report API
    # ==================================================================

    def create_report(self, title: str, **kw) -> ReportRecord:
        rpt = self.report.create_report(title, **kw)
        from .event import EVENT_RO_RPT_CREATED
        self._put(EVENT_RO_RPT_CREATED, rpt); return rpt

    def get_report(self, report_id: str) -> Optional[ReportRecord]:
        return self.report.get_report(report_id)

    def list_reports(self, **kw) -> List[ReportRecord]:
        return self.report.list_reports(**kw)

    def update_report(self, rpt: ReportRecord) -> None:
        self.report.update_report(rpt)
        from .event import EVENT_RO_RPT_UPDATED
        self._put(EVENT_RO_RPT_UPDATED, rpt)

    def delete_report(self, report_id: str) -> None:
        self.report.delete_report(report_id)
        from .event import EVENT_RO_RPT_DELETED
        self._put(EVENT_RO_RPT_DELETED, report_id)

    def publish_report(self, report_id: str) -> None:
        self.report.publish_report(report_id)
        from .event import EVENT_RO_RPT_PUBLISHED
        self._put(EVENT_RO_RPT_PUBLISHED, report_id)

    def add_report_section(self, report_id: str, title: str, **kw) -> Optional[ReportSection]:
        return self.report.add_section(report_id, title, **kw)

    def render_report_markdown(self, report_id: str) -> str:
        return self.report.render_markdown(report_id)

    def search_reports(self, keyword: str) -> List[ReportRecord]:
        return self.report.search_reports(keyword)

    # ==================================================================
    # Knowledge API
    # ==================================================================

    def create_note(self, title: str, **kw) -> KnowledgeNote:
        note = self.knowledge.create_note(title, **kw)
        from .event import EVENT_RO_KB_CREATED
        self._put(EVENT_RO_KB_CREATED, note); return note

    def get_note(self, note_id: str) -> Optional[KnowledgeNote]:
        return self.knowledge.get_note(note_id)

    def list_notes(self, **kw) -> List[KnowledgeNote]:
        return self.knowledge.list_notes(**kw)

    def update_note(self, note: KnowledgeNote) -> None:
        self.knowledge.update_note(note)
        from .event import EVENT_RO_KB_UPDATED
        self._put(EVENT_RO_KB_UPDATED, note)

    def delete_note(self, note_id: str) -> None:
        self.knowledge.delete_note(note_id)
        from .event import EVENT_RO_KB_DELETED
        self._put(EVENT_RO_KB_DELETED, note_id)

    def create_experience_card(self, title: str, **kw) -> ExperienceCard:
        return self.knowledge.create_card(title, **kw)

    def list_experience_cards(self, **kw) -> List[ExperienceCard]:
        return self.knowledge.list_cards(**kw)

    def create_failure_case(self, title: str, **kw) -> FailureCaseRecord:
        return self.knowledge.create_failure_case(title, **kw)

    def list_failure_cases(self, **kw) -> List[FailureCaseRecord]:
        return self.knowledge.list_failure_cases(**kw)

    def search_knowledge(self, keyword: str) -> Dict:
        return self.knowledge.search_all(keyword)

    # ==================================================================
    # Governance API
    # ==================================================================

    def submit_approval(self, title: str, **kw) -> ApprovalRequest:
        req = self.governance.submit_request(title, **kw)
        from .event import EVENT_RO_GOV_SUBMITTED
        self._put(EVENT_RO_GOV_SUBMITTED, req); return req

    def approve_request(self, request_id: str, approver: str, comment: str = "") -> None:
        self.governance.approve(request_id, approver, comment)
        from .event import EVENT_RO_GOV_APPROVED
        self._put(EVENT_RO_GOV_APPROVED, request_id)

    def reject_request(self, request_id: str, approver: str, comment: str = "") -> None:
        self.governance.reject(request_id, approver, comment)
        from .event import EVENT_RO_GOV_REJECTED
        self._put(EVENT_RO_GOV_REJECTED, request_id)

    def freeze_asset(self, **kw) -> FreezeRecord:
        rec = self.governance.freeze(**kw)
        from .event import EVENT_RO_GOV_FROZEN
        self._put(EVENT_RO_GOV_FROZEN, rec); return rec

    def unfreeze_asset(self, freeze_id: str, released_by: str = "") -> None:
        self.governance.unfreeze(freeze_id, released_by)
        from .event import EVENT_RO_GOV_RELEASED
        self._put(EVENT_RO_GOV_RELEASED, freeze_id)

    def is_asset_frozen(self, target_id: str) -> bool:
        return self.governance.is_frozen(target_id)

    def list_pending_approvals(self) -> List[ApprovalRequest]:
        return self.governance.pending_requests()

    def list_audit_logs(self, **kw) -> List[AuditLog]:
        return self.governance.list_audit_logs(**kw)

    def log_audit(self, actor: str, action: AuditAction, **kw) -> AuditLog:
        return self.governance.log_action(actor, action, **kw)

    # ==================================================================
    # 全平台统计
    # ==================================================================

    def get_platform_stats(self) -> Dict[str, Any]:
        return {
            "workspace":  self.workspace.stats(),
            "experiment": self.experiment.stats(),
            "registry":   self.registry.stats(),
            "pipeline":   self.pipeline.stats(),
            "report":     self.report.stats(),
            "knowledge":  self.knowledge.stats(),
            "governance": self.governance.stats(),
        }

    # ------------------------------------------------------------------
    # BaseEngine 接口
    # ------------------------------------------------------------------

    def close(self) -> None:
        pass
"""

txt = P.read_text(encoding="utf-8")
txt = txt.replace("    # PLACEHOLDER_PIPELINE_REPORT", CHUNK2)
P.write_text(txt, encoding="utf-8")
print("engine.py chunk2 OK, size:", P.stat().st_size)
