"""add_missing_engine_methods.py — 在 ResearchOpsEngine 末尾批量追加缺失代理方法"""
import pathlib, ast

P = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\main_engine.py")

METHODS = '''
    # ==================================================================
    # 补充代理 — Knowledge（Tab 直接调用的方法）
    # ==================================================================

    def archive_note(self, note_id: str) -> None:
        self.knowledge.archive_note(note_id)

    def create_card(self, title: str, **kw):
        return self.knowledge.create_card(title, **kw)

    def get_card(self, card_id: str):
        return self.knowledge.get_card(card_id)

    def list_cards(self, **kw):
        return self.knowledge.list_cards(**kw)

    def update_card(self, card) -> None:
        self.knowledge.update_card(card)

    def delete_card(self, card_id: str) -> None:
        self.knowledge.delete_card(card_id)

    def get_failure_case(self, case_id: str):
        return self.knowledge.get_failure_case(case_id)

    def update_failure_case(self, case) -> None:
        self.knowledge.update_failure_case(case)

    def delete_failure_case(self, case_id: str) -> None:
        self.knowledge.delete_failure_case(case_id)

    def resolve_case(self, case_id: str, **kw) -> None:
        self.knowledge.resolve_case(case_id, **kw)

    def search_all(self, keyword: str) -> dict:
        return self.knowledge.search_all(keyword)

    # ==================================================================
    # 补充代理 — Governance
    # ==================================================================

    def get_request(self, request_id: str):
        return self.governance.get_request(request_id)

    def list_requests(self, **kw):
        return self.governance.list_requests(**kw)

    def submit_request(self, title: str, **kw):
        return self.governance.submit_request(title, **kw)

    def approve(self, request_id: str, approver: str = "", comment: str = "") -> None:
        self.governance.approve(request_id, approver, comment)

    def reject(self, request_id: str, approver: str = "", comment: str = "") -> None:
        self.governance.reject(request_id, approver, comment)

    def freeze(self, **kw):
        return self.governance.freeze(**kw)

    def unfreeze(self, freeze_id: str, released_by: str = "") -> None:
        self.governance.unfreeze(freeze_id, released_by)

    def list_freezes(self, **kw):
        return self.governance.list_freezes(**kw)

    # ==================================================================
    # 补充代理 — Pipeline
    # ==================================================================

    def add_node(self, pipeline_id: str, name: str, **kw):
        return self.pipeline.add_node(pipeline_id, name, **kw)

    def pause_pipeline(self, pipeline_id: str) -> None:
        self.pipeline.pause_pipeline(pipeline_id)

    # ==================================================================
    # 补充代理 — Report
    # ==================================================================

    def add_section(self, report_id: str, title: str, **kw):
        return self.report.add_section(report_id, title, **kw)

    def remove_section(self, report_id: str, section_id: str) -> None:
        self.report.remove_section(report_id, section_id)

    def update_section(self, report_id: str, section) -> None:
        self.report.update_section(report_id, section)

    def render_markdown(self, report_id: str) -> str:
        return self.report.render_markdown(report_id)

    def unpublish_report(self, report_id: str) -> None:
        self.report.unpublish_report(report_id)

    def create_template(self, name: str, **kw):
        return self.report.create_template(name, **kw)

    def get_template(self, template_id: str):
        return self.report.get_template(template_id)

    def list_templates(self, **kw):
        return self.report.list_templates(**kw)

    def apply_template(self, report_id: str, template_id: str) -> None:
        self.report.apply_template(report_id, template_id)
'''

src = P.read_text(encoding="utf-8")

# 找 close() 方法，在其之前插入
insert_before = "    # ------------------------------------------------------------------\n    # BaseEngine 接口\n"
if insert_before not in src:
    insert_before = "    def close(self) -> None:"

if METHODS.strip()[:30] not in src:
    src = src.replace(insert_before, METHODS + "\n    " + insert_before.lstrip())

ast.parse(src)
P.write_text(src, encoding="utf-8")
print("Added", METHODS.count("def "), "proxy methods")
print("Total lines:", len(src.splitlines()))
