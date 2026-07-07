"""patch_pl_stats.py — 扩展 PipelineEngine.stats() 加入 total_nodes"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\engine\pipeline_engine.py"
)
src = P.read_text(encoding="utf-8")

OLD = '''        return {
            "pipelines":    len(pls),
            "running":      sum(1 for p in pls if p.status == PipelineStatus.RUNNING),
            "completed":    sum(1 for p in pls if p.status == PipelineStatus.COMPLETED),
            "failed":       sum(1 for p in pls if p.status == PipelineStatus.FAILED),
            "total_runs":   sum(p.run_count for p in pls),
        }'''

NEW = '''        return {
            "pipelines":    len(pls),
            "running":      sum(1 for p in pls if p.status == PipelineStatus.RUNNING),
            "completed":    sum(1 for p in pls if p.status == PipelineStatus.COMPLETED),
            "failed":       sum(1 for p in pls if p.status == PipelineStatus.FAILED),
            "paused":       sum(1 for p in pls if p.status == PipelineStatus.PAUSED),
            "total_runs":   sum(p.run_count for p in pls),
            "total_nodes":  sum(len(p.nodes) for p in pls),
        }'''

assert OLD in src, "pattern not found"
src = src.replace(OLD, NEW)
ast.parse(src)
P.write_text(src, encoding="utf-8")
print("stats() patched OK")
