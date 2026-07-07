"""smoke_rpt.py — Phase 6 smoke test"""
from vnpy.research_ops.engine.report_engine import ReportEngine
from vnpy.research_ops.constant import ReportType

re = ReportEngine()

r1 = re.create_report("因子研究报告 2024Q4", report_type=ReportType.FACTOR,
    author="alice", summary="动量因子研究", tags=["factor","momentum"])
r2 = re.create_report("周报 2024-W52", report_type=ReportType.WEEKLY,
    author="bob", tags=["weekly"])
assert re.get_report(r1.report_id).title == "因子研究报告 2024Q4"
print("  create_report: PASSED")

s1 = re.add_section(r1.report_id, "研究背景",  content="## 研究背景\n本报告...", order=1)
s2 = re.add_section(r1.report_id, "因子定义",  content="## 因子定义\n动量因子...", order=2)
s3 = re.add_section(r1.report_id, "实证结果",  content="## 实证结果\nIC=0.048",  order=3)
assert s1 is not None
assert len(re.get_report(r1.report_id).sections) == 3
print("  add_section: PASSED")

re.update_section(r1.report_id, s2.section_id,
    title="因子定义（更新）", content="## 因子定义\n20日动量 = close/close.shift(20)-1")
upd = next(s for s in re.get_report(r1.report_id).sections
           if s.section_id == s2.section_id)
assert upd.title == "因子定义（更新）"
print("  update_section: PASSED")

md = re.render_markdown(r1.report_id)
assert len(md) > 0
print("  render_markdown: PASSED, chars:", len(md))

re.publish_report(r1.report_id)
assert re.get_report(r1.report_id).is_published
re.unpublish_report(r1.report_id)
assert not re.get_report(r1.report_id).is_published
print("  publish/unpublish: PASSED")

tmpl = re.create_template(
    name="研究报告模板",
    content="# 标题\n## 摘要\n## 方法\n## 结果\n## 结论",
    description="通用研究报告模板",
    report_type=ReportType.RESEARCH)
assert re.get_template(tmpl.template_id).name == "研究报告模板"
# apply_template 将模板 content 写入 report.summary
re.apply_template(tmpl.template_id, r2.report_id)
rpt2 = re.get_report(r2.report_id)
assert rpt2.summary is not None and len(rpt2.summary) > 0
print("  create_template + apply_template: PASSED, summary:", len(rpt2.summary))

results = re.search_reports("因子")
assert any(r.report_id == r1.report_id for r in results)
print("  search_reports: PASSED")

re.remove_section(r1.report_id, s3.section_id)
assert len(re.get_report(r1.report_id).sections) == 2
print("  remove_section: PASSED")

s = re.stats()
assert s["reports"] == 2
assert s["templates"] >= 1
print("  stats:", s)
print("  stats: PASSED")

re.delete_report(r2.report_id)
assert re.get_report(r2.report_id) is None
print("  delete_report: PASSED")

from vnpy.research_ops.ui.report_tab import _md_to_html
html = _md_to_html("# Hello\n**bold** and *italic*")
assert "<h1" in html and "<b>" in html
print("  _md_to_html: PASSED")

from vnpy.research_ops.ui.report_tab import (
    ReportTab, ReportDialog, TemplateDialog, SectionDialog,
    MarkdownEditor, TemplatePanel, ReportDetail, ReportList,
    RPT_TYPE_ICON, RPT_TYPE_COLOR,
)
assert len(RPT_TYPE_ICON) == 8
assert len(RPT_TYPE_COLOR) == 8
assert hasattr(ReportDialog,   "get_title")
assert hasattr(ReportDialog,   "get_report_type")
assert hasattr(TemplateDialog, "get_content")
assert hasattr(SectionDialog,  "get_order")
assert hasattr(MarkdownEditor, "set_content")
assert hasattr(MarkdownEditor, "get_content")
assert hasattr(TemplatePanel,  "apply_requested")
print("  UI class API: PASSED")

from vnpy.research_ops.ui.stub_tabs import ReportTab as RT2
assert ReportTab is RT2
print("  stub_tabs re-export: PASSED")

print()
print("=== Phase 6 Smoke Test: ALL PASSED ===")
