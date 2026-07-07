import pathlib, sys

ROOT = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops")

# 检查 main_engine.py 文件中方法是否写入
src = (ROOT / "main_engine.py").read_text(encoding="utf-8")
expected = [
    "approve", "reject", "archive_note", "pause_pipeline",
    "list_requests", "list_freezes", "render_markdown", "unpublish_report",
    "add_node", "freeze", "unfreeze", "get_request", "submit_request",
    "create_card", "get_card", "list_cards", "update_card", "delete_card",
    "get_failure_case", "update_failure_case", "delete_failure_case",
    "resolve_case", "search_all", "add_section", "remove_section",
    "update_section", "create_template", "get_template", "list_templates",
    "apply_template", "stats", "update_run",
]
missing = [m for m in expected if f"def {m}" not in src]
present = [m for m in expected if f"def {m}" in src]

print(f"Present ({len(present)}):", present)
if missing:
    print(f"MISSING ({len(missing)}):", missing)
    sys.exit(1)
else:
    print("All methods present in file: OK")

# 确认语法正确
import ast
ast.parse(src)
print("Syntax: OK")

# 动态导入确认运行时也能找到
sys.path.insert(0, str(ROOT.parent.parent))

# 清除缓存
for k in list(sys.modules.keys()):
    if "research_ops" in k:
        del sys.modules[k]

from vnpy.research_ops.main_engine import ResearchOpsEngine
engine_methods = set(m for m in dir(ResearchOpsEngine) if not m.startswith("_"))
rt_missing = [m for m in expected if m not in engine_methods]
if rt_missing:
    print(f"Runtime MISSING ({len(rt_missing)}):", rt_missing)
    sys.exit(1)
else:
    print(f"Runtime check: OK  ({len(engine_methods)} public methods total)")

print("\n=== All checks PASSED ===")
