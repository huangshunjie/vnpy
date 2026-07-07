"""scan_missing_engine_methods.py — 找出所有 Tab 调用但主引擎没有的方法"""
import pathlib, re, ast

ROOT = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops")

# 获取主引擎所有公开方法
import sys; sys.path.insert(0, str(ROOT.parent.parent))
from vnpy.research_ops.main_engine import ResearchOpsEngine
engine_methods = set(m for m in dir(ResearchOpsEngine) if not m.startswith("_"))

# 扫描所有 Tab 对 self._engine.xxx() 的调用
call_pat = re.compile(r'self\._engine\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
missing = {}

for p in sorted((ROOT / "ui").glob("*_tab.py")):
    src = p.read_text(encoding="utf-8", errors="ignore")
    calls = set(call_pat.findall(src))
    for c in sorted(calls):
        if c not in engine_methods and c not in ("event_engine", "experiment", "registry"):
            missing.setdefault(c, []).append(p.name)

print("=== Missing methods on ResearchOpsEngine ===")
for method, tabs in sorted(missing.items()):
    print(f"  {method:35s}  <- {', '.join(tabs)}")
