"""
research_ops/ui/widget.py

ResearchOpsWidget — Phase 1 主窗口骨架（14 个 Tab）。
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QStatusBar,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from vnpy.event import EventEngine

from ..main_engine import ResearchOpsEngine
from .stub_tabs import (
    DashboardTab, WorkspaceTab, ExperimentTab,
    RegistryTab, PipelineTab, ReportTab,
    KnowledgeTab, GovernanceTab,
)
from .log_tab import LogTab


class ResearchOpsWidget(QWidget):
    """
    ResearchOps Platform 2.0 主窗口。
    包含 10 个 Tab（Phase 1 均为骨架，后续 Phase 逐步实现）。
    """

    widget_name = "ResearchOpsWidget"

    def __init__(self, engine: ResearchOpsEngine, event_engine: EventEngine):
        super().__init__()
        self._engine       = engine
        self._event_engine = event_engine
        self._init_ui()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _init_ui(self):
        self.setWindowTitle("ResearchOps Platform 2.0 — 机构级量化研发操作系统")
        self.resize(1440, 900)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 顶部标题栏
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet(
            "background: qlineargradient("
            "x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #1a1f36, stop:1 #4a6cf7);"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(18, 0, 18, 0)
        title_lbl = QLabel("⚙  ResearchOps Platform 2.0")
        title_lbl.setStyleSheet(
            "color: white; font-size: 16px; font-weight: bold;"
        )
        h_lay.addWidget(title_lbl)
        h_lay.addStretch()
        ver_lbl = QLabel("Phase 2 · Workspace System")
        ver_lbl.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 12px;")
        h_lay.addWidget(ver_lbl)
        root.addWidget(header)

        # ── Tab 区
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.North)
        self._tabs.setDocumentMode(True)
        self._tabs.setStyleSheet("""
            QTabBar::tab {
                min-width: 90px;
                padding: 8px 14px;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                color: #4a6cf7;
                font-weight: bold;
                border-bottom: 2px solid #4a6cf7;
            }
        """)
        self._build_tabs()
        root.addWidget(self._tabs)

        # ── 底部状态栏
        status = QWidget()
        status.setFixedHeight(24)
        status.setStyleSheet("background: #f8f9fa; border-top: 1px solid #dee2e6;")
        s_lay = QHBoxLayout(status)
        s_lay.setContentsMargins(12, 0, 12, 0)
        self._status_lbl = QLabel("就绪")
        self._status_lbl.setStyleSheet("color: #6c757d; font-size: 11px;")
        s_lay.addWidget(self._status_lbl)
        s_lay.addStretch()
        build_lbl = QLabel("VeighNa 4.4 · ResearchOps 2.0 · Phase 2")
        build_lbl.setStyleSheet("color: #adb5bd; font-size: 11px;")
        s_lay.addWidget(build_lbl)
        root.addWidget(status)

    def _build_tabs(self):
        """注册所有 Tab。Phase 1 全为骨架，后续 Phase 逐步替换。"""
        e = self._engine
        tabs = [
            ("Dashboard",   DashboardTab(e),   "📊"),
            ("Workspace",   WorkspaceTab(e),   "🗂"),
            ("Experiments", ExperimentTab(e),  "🧪"),
            ("Registry",    RegistryTab(e),    "📦"),
            ("Pipeline",    PipelineTab(e),    "⚙"),
            ("Reports",     ReportTab(e),      "📄"),
            ("Knowledge",   KnowledgeTab(e),   "💡"),
            ("Governance",  GovernanceTab(e),  "🔒"),
            ("Logs",        LogTab(e),         "📋"),
        ]
        for label, widget, icon in tabs:
            self._tabs.addTab(widget, f"{icon}  {label}")

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def set_status(self, msg: str) -> None:
        self._status_lbl.setText(msg)

    def switch_tab(self, index: int) -> None:
        if 0 <= index < self._tabs.count():
            self._tabs.setCurrentIndex(index)
