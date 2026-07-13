"""
research_ops/ui/widget.py

ResearchOpsWidget — 主窗口（标准 VeighNa widget 签名）
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel,
)
from PySide6.QtCore import QTimer

from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine

from .stub_tabs import (
    DashboardTab, WorkspaceTab, ExperimentTab,
    RegistryTab, PipelineTab, ReportTab,
    KnowledgeTab, GovernanceTab,
)
from .log_tab import LogTab

APP_NAME = "ResearchOps"


class ResearchOpsWidget(QWidget):
    """ResearchOps Platform 2.0 主窗口。"""

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()
        self.main_engine   = main_engine
        self.event_engine  = event_engine
        self._engine       = main_engine.get_engine(APP_NAME)
        self._init_ui()

    # ── UI 构建 ───────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setWindowTitle("ResearchOps Platform 2.0 — 机构级量化研发操作系统")
        self.resize(1440, 900)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())

        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.North)
        self._tabs.setDocumentMode(True)
        self._tabs.setStyleSheet("""
            QTabBar::tab {
                min-width: 90px; padding: 8px 14px; font-size: 13px;
            }
            QTabBar::tab:selected {
                color: #4a6cf7; font-weight: bold;
                border-bottom: 2px solid #4a6cf7;
            }
        """)

        e = self._engine
        for icon, label, TabCls in [
            ("📊", "Dashboard",   DashboardTab),
            ("🗂", "Workspace",   WorkspaceTab),
            ("🧪", "Experiments", ExperimentTab),
            ("📦", "Registry",    RegistryTab),
            ("⚙",  "Pipeline",    PipelineTab),
            ("📄", "Reports",     ReportTab),
            ("💡", "Knowledge",   KnowledgeTab),
            ("🔒", "Governance",  GovernanceTab),
            ("📋", "Logs",        LogTab),
        ]:
            self._tabs.addTab(TabCls(e), f"{icon}  {label}")

        root.addWidget(self._tabs)
        root.addWidget(self._make_status_bar())

        self._timer = QTimer(self)
        self._timer.setInterval(5_000)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start()

    def _make_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(48)
        w.setStyleSheet(
            "background: qlineargradient("
            "x1:0,y1:0,x2:1,y2:0,stop:0 #1a1f36,stop:1 #4a6cf7);")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(18, 0, 18, 0)
        title = QLabel("⚙  ResearchOps Platform 2.0")
        title.setStyleSheet(
            "color:white;font-size:16px;font-weight:bold;")
        lay.addWidget(title)
        lay.addStretch()
        ver = QLabel("VeighNa 4.4 · ResearchOps 2.0")
        ver.setStyleSheet("color:rgba(255,255,255,0.6);font-size:12px;")
        lay.addWidget(ver)
        return w

    def _make_status_bar(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(24)
        w.setStyleSheet(
            "background:#f8f9fa;border-top:1px solid #dee2e6;")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 0, 12, 0)
        self._status_lbl = QLabel("就绪")
        self._status_lbl.setStyleSheet("color:#6c757d;font-size:11px;")
        lay.addWidget(self._status_lbl)
        lay.addStretch()
        build = QLabel("VeighNa 4.4 · ResearchOps 2.0")
        build.setStyleSheet("color:#adb5bd;font-size:11px;")
        lay.addWidget(build)
        return w

    def _refresh_status(self) -> None:
        if not self._engine:
            return
        try:
            s = self._engine.get_platform_stats()
            ws  = s.get("workspace",  {})
            exp = s.get("experiment", {})
            reg = s.get("registry",   {})
            self._status_lbl.setText(
                f"工作区: {ws.get('workspaces', 0)}"
                f"  |  实验: {exp.get('experiments', 0)}"
                f"  |  策略: {reg.get('strategies', 0)}"
                f"  |  模型: {reg.get('models', 0)}")
        except Exception:
            pass

    def set_status(self, msg: str) -> None:
        self._status_lbl.setText(msg)

    def closeEvent(self, event) -> None:
        self._timer.stop()
        super().closeEvent(event)
