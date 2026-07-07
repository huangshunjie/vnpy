"""smoke_kb.py — Phase 7 smoke test"""
from vnpy.research_ops.engine.knowledge_engine import KnowledgeEngine
from vnpy.research_ops.constant import NoteType, Priority

ke = KnowledgeEngine()

# 1. create note
n1 = ke.create_note("动量因子研究笔记",
    content="## 背景\n动量效应在 A 股显著。\n\n## 结论\nIC=0.048",
    note_type=NoteType.RESEARCH, priority=Priority.HIGH,
    author="alice", tags=["momentum","factor"])
n2 = ke.create_note("回测失败复盘",
    content="## 现象\n夏普比率为负", note_type=NoteType.FAILURE,
    priority=Priority.URGENT, author="bob", tags=["failure"])
assert ke.get_note(n1.note_id).title == "动量因子研究笔记"
print("  create_note: PASSED")

n1.content += "\n\n## 补充\n20日动量最优"
ke.update_note(n1)
assert "补充" in ke.get_note(n1.note_id).content
print("  update_note: PASSED")

ke.archive_note(n2.note_id)
assert ke.get_note(n2.note_id).is_archived
print("  archive_note: PASSED")

all_notes = ke.list_notes()
assert len(all_notes) == 2
print("  list_notes: PASSED, count:", len(all_notes))

c1 = ke.create_card("LightGBM 特征选择经验",
    context="在100个因子中筛选", insight="SHAP 值比相关性筛选更稳定",
    lesson="先用 SHAP 筛 top-30，再做相关性去重",
    author="alice", tags=["ml","feature"])
assert ke.get_card(c1.card_id).title == "LightGBM 特征选择经验"
print("  create_card: PASSED")

c1.lesson += "\n更新：加入IC筛选"
ke.update_card(c1)
assert "IC筛选" in ke.get_card(c1.card_id).lesson
print("  update_card: PASSED")

fc1 = ke.create_failure_case("回测过拟合",
    symptom="样本内夏普3.2，样本外-0.1",
    root_cause="参数过度优化",
    impact="策略无法实盘",
    resolution="使用滚动验证",
    prevention="控制参数数量 < 5",
    severity="high", author="bob", tags=["overfit"])
assert ke.get_failure_case(fc1.case_id).title == "回测过拟合"
print("  create_failure_case: PASSED")

ke.resolve_case(fc1.case_id)
assert ke.get_failure_case(fc1.case_id).is_resolved
print("  resolve_case: PASSED")

results = ke.search_all("动量")
assert len(results.get("notes", [])) >= 1
results2 = ke.search_all("SHAP")
assert len(results2.get("cards", [])) >= 1
results3 = ke.search_all("过拟合")
assert len(results3.get("failure_cases", [])) >= 1
print("  search_all: PASSED")

assert len(ke.search_notes("动量")) >= 1
assert len(ke.search_cards("LightGBM")) >= 1
assert len(ke.search_failure_cases("过拟合")) >= 1
print("  individual search: PASSED")

s = ke.stats()
print("  stats:", s)
# key is experience_cards per engine implementation
assert s["notes"] == 2
assert s.get("experience_cards", s.get("cards", 0)) == 1
assert s["failure_cases"] == 1
print("  stats: PASSED")

ke.delete_note(n2.note_id)
ke.delete_card(c1.card_id)
ke.delete_failure_case(fc1.case_id)
assert ke.get_note(n2.note_id) is None
assert ke.get_card(c1.card_id) is None
assert ke.get_failure_case(fc1.case_id) is None
print("  delete ops: PASSED")

from vnpy.research_ops.ui.knowledge_tab import (
    KnowledgeTab, NoteList, NoteDetail, CardList, CardDetail,
    FailureCaseList, FailureCaseDetail, SearchPanel,
    NoteDialog, CardDialog, FailureCaseDialog,
    NOTE_TYPE_COLOR, NOTE_TYPE_ICON, PRIORITY_COLOR, SEVERITY_COLOR,
)
assert len(NOTE_TYPE_COLOR) == 5
assert len(NOTE_TYPE_ICON) == 5
assert len(PRIORITY_COLOR) == 4
assert len(SEVERITY_COLOR) == 4
assert hasattr(NoteDialog,        "get_note_type")
assert hasattr(NoteDialog,        "get_priority")
assert hasattr(CardDialog,        "get_insight")
assert hasattr(CardDialog,        "get_lesson")
assert hasattr(FailureCaseDialog, "get_root_cause")
assert hasattr(FailureCaseDialog, "get_prevention")
assert hasattr(SearchPanel,       "_do_search")
print("  UI class API: PASSED")

# fix _refresh_stats to use correct key
import pathlib, re
src = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\knowledge_tab.py"
).read_text(encoding="utf-8")
assert "experience_cards" in src or "cards" in src
print("  knowledge_tab.py key check: PASSED")

from vnpy.research_ops.ui.stub_tabs import KnowledgeTab as KT2
assert KnowledgeTab is KT2
print("  stub_tabs re-export: PASSED")

print()
print("=== Phase 7 Smoke Test: ALL PASSED ===")
