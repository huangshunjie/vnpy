"""fix_research_ops_stats.py — 一次性修复所有 stats 字段 + update_run + experiment_tab"""
import pathlib, ast

ROOT = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops")

# ── 1. knowledge_engine.stats() 补齐字段 ──────────────────────────
kp = ROOT / "engine" / "knowledge_engine.py"
src = kp.read_text(encoding="utf-8")
src = src.replace(
    '    def stats(self) -> dict:\n'
    '        return {\n'
    '            "notes":          self._note_repo.count(),\n'
    '            "experience_cards": self._card_repo.count(),\n'
    '            "failure_cases":  self._case_repo.count(),\n'
    '            "unresolved_cases": len(self.list_failure_cases(resolved=False)),\n'
    '        }',
    '    def stats(self) -> dict:\n'
    '        notes = self._note_repo.list()\n'
    '        return {\n'
    '            "notes":           self._note_repo.count(),\n'
    '            "archived_notes":  sum(1 for n in notes if getattr(n, "is_archived", False)),\n'
    '            "experience_cards": self._card_repo.count(),\n'
    '            "cards":           self._card_repo.count(),\n'
    '            "failure_cases":   self._case_repo.count(),\n'
    '            "unresolved_cases": len(self.list_failure_cases(resolved=False)),\n'
    '            "open_cases":      len(self.list_failure_cases(resolved=False)),\n'
    '        }'
)
ast.parse(src)
kp.write_text(src, encoding="utf-8")
print("knowledge_engine.stats(): OK")

# ── 2. report_engine.stats() 补齐字段 ────────────────────────────
rp = ROOT / "engine" / "report_engine.py"
src = rp.read_text(encoding="utf-8")
src = src.replace(
    '    def stats(self) -> dict:\n'
    '        rpts = self._rpt_repo.list()\n'
    '        return {\n'
    '            "reports":    len(rpts),\n'
    '            "published":  sum(1 for r in rpts if r.is_published),\n'
    '            "templates":  self._tmpl_repo.count(),\n'
    '        }',
    '    def stats(self) -> dict:\n'
    '        rpts = self._rpt_repo.list()\n'
    '        return {\n'
    '            "reports":   len(rpts),\n'
    '            "published": sum(1 for r in rpts if r.is_published),\n'
    '            "drafts":    sum(1 for r in rpts if not r.is_published),\n'
    '            "templates": self._tmpl_repo.count(),\n'
    '        }'
)
ast.parse(src)
rp.write_text(src, encoding="utf-8")
print("report_engine.stats():    OK")

# ── 3. ExperimentEngine.update_run() 公开方法 ─────────────────────
ep = ROOT / "engine" / "experiment_engine.py"
src = ep.read_text(encoding="utf-8")
if "def update_run" not in src:
    src = src.replace(
        "    def get_run(self, run_id: str) -> Optional[RunRecord]:",
        "    def update_run(self, run: RunRecord) -> None:\n"
        "        run.updated_at = datetime.now() if hasattr(run, 'updated_at') else None\n"
        "        self._run_repo.save(run)\n\n"
        "    def get_run(self, run_id: str) -> Optional[RunRecord]:"
    )
    ast.parse(src)
    ep.write_text(src, encoding="utf-8")
    print("experiment_engine.update_run(): added")
else:
    print("experiment_engine.update_run(): already exists")

# ── 4. ResearchOpsEngine.stats() + update_run() ──────────────────
mp = ROOT / "main_engine.py"
src = mp.read_text(encoding="utf-8")

# 加 update_run 代理（如果不存在）
if "def update_run" not in src:
    src = src.replace(
        "    def get_run(self, run_id: str) -> Optional[RunRecord]:",
        "    def update_run(self, run) -> None:\n"
        "        self.experiment.update_run(run)\n\n"
        "    def get_run(self, run_id: str) -> Optional[RunRecord]:"
    )

# 加各子引擎 stats 代理（放在 get_platform_stats 之前）
stats_methods = '''
    # ==================================================================
    # Per-subsystem stats() — called by each Tab's _refresh_stats()
    # ==================================================================

    def stats(self) -> dict:
        """默认 stats：返回 experiment 子引擎统计（ExperimentTab 使用）。"""
        return self.experiment.stats()

    def workspace_stats(self) -> dict:
        return self.workspace.stats()

    def experiment_stats(self) -> dict:
        return self.experiment.stats()

    def registry_stats(self) -> dict:
        return self.registry.stats()

    def pipeline_stats(self) -> dict:
        return self.pipeline.stats()

    def report_stats(self) -> dict:
        return self.report.stats()

    def knowledge_stats(self) -> dict:
        return self.knowledge.stats()

    def governance_stats(self) -> dict:
        return self.governance.stats()

'''

if "def stats(self)" not in src:
    src = src.replace(
        "    # ==================================================================\n"
        "    # 全平台统计\n"
        "    # ==================================================================",
        stats_methods +
        "    # ==================================================================\n"
        "    # 全平台统计\n"
        "    # =================================================================="
    )

ast.parse(src)
mp.write_text(src, encoding="utf-8")
print("main_engine stats/update_run: OK")

# ── 5. experiment_tab.py: _run_repo.save → update_run() ──────────
tp = ROOT / "ui" / "experiment_tab.py"
src = tp.read_text(encoding="utf-8")
src = src.replace(
    "self._engine.experiment._run_repo.save(run)",
    "self._engine.update_run(run)"
)
ast.parse(src)
tp.write_text(src, encoding="utf-8")
print("experiment_tab._run_repo.save: fixed")

print("\n=== All fixes applied ===")
