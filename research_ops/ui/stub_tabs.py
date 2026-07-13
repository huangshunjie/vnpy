"""
research_ops/ui/stub_tabs.py
所有占位 Tab，Phase 2~9 全部替换为完整实现。
"""
from __future__ import annotations

from .workspace_tab   import WorkspaceTab    # Phase 2
from .experiment_tab  import ExperimentTab   # Phase 3
from .registry_tab    import RegistryTab     # Phase 4
from .pipeline_tab    import PipelineTab     # Phase 5
from .report_tab      import ReportTab       # Phase 6
from .knowledge_tab   import KnowledgeTab    # Phase 7
from .dashboard_tab   import DashboardTab    # Phase 8
from .governance_tab  import GovernanceTab   # Phase 9

__all__ = [
    "WorkspaceTab",
    "ExperimentTab",
    "RegistryTab",
    "PipelineTab",
    "ReportTab",
    "KnowledgeTab",
    "DashboardTab",
    "GovernanceTab",
]
