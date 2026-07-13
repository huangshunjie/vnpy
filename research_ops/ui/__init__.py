"""
research_ops/ui/__init__.py
"""
from .widget    import ResearchOpsWidget
from .log_tab   import LogTab
from .stub_tabs import (
    DashboardTab, WorkspaceTab, ExperimentTab,
    RegistryTab, PipelineTab, ReportTab,
    KnowledgeTab, GovernanceTab,
)

__all__ = [
    "ResearchOpsWidget",
    "LogTab",
    "DashboardTab", "WorkspaceTab", "ExperimentTab",
    "RegistryTab",  "PipelineTab",  "ReportTab",
    "KnowledgeTab", "GovernanceTab",
]
