"""
platform_engineering/ui/widget.py
PlatformEngineeringWidget — 主窗口
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QFrame, QPushButton,
)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont

from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine

from .stub_tabs import (
    DashboardTab, ObservabilityTab, TaskTab, DeploymentTab,
    StrategyHealthTab, ConfigTab, ApiTab, SecurityTab, LogTab,
)

APP_NAME = "platform_engineering"


class PlatformEngineeringWidget(QWidget):
    """Quant Platform Engineering 主窗口。"""

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()
        self.main_engine  = main_engine
        self.event_engine = event_engine
        self._engine      = main_engine.get_engine(APP_NAME)

        self.setWindowTitle("Quant Platform Engineering System")
        self.setMinimumSize(1200, 700)
        self._init_ui()
        self._start_engine()

    # ── UI ────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#dee2e6;")
        root.addWidget(sep)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.setTabPosition(QTabWidget.West)

        for label, TabCls in [
            ("📊  Dashboard",       DashboardTab),
            ("🔭  Observability",   ObservabilityTab),
            ("⚙️  Tasks",            TaskTab),
            ("🚀  Deployment",      DeploymentTab),
            ("💓  Strategy Health", StrategyHealthTab),
            ("🗂️  Configuration",    ConfigTab),
            ("🌐  API Gateway",     ApiTab),
            ("🔐  Security",        SecurityTab),
            ("📋  Logs",            LogTab),
        ]:
            self._tabs.addTab(TabCls(engine=self._engine), label)

        root.addWidget(self._tabs, 1)
        root.addWidget(self._make_status_bar())

        self._timer = QTimer(self)
        self._timer.setInterval(5_000)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start()

    def _make_header(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:#1a1f36;")
        w.setFixedHeight(48)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)

        logo = QLabel("⚙  Quant Platform Engineering")
        logo.setStyleSheet(
            "color:#ffffff;font-size:15px;font-weight:bold;background:transparent;")
        lay.addWidget(logo)
        lay.addStretch()

        self._health_badge = QLabel("● GREEN")
        self._health_badge.setStyleSheet(
            "color:#52c41a;font-size:12px;background:transparent;"
            "padding:2px 10px;border:1px solid #52c41a;border-radius:10px;")
        lay.addWidget(self._health_badge)

        btn = QPushButton("🔄 刷新")
        btn.setFixedSize(72, 28)
        btn.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;"
            "font-size:12px;border:none;")
        btn.clicked.connect(self._refresh_status)
        lay.addWidget(btn)
        return w

    def _make_status_bar(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(26)
        w.setStyleSheet("background:#f8f9fa;border-top:1px solid #dee2e6;")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(10, 0, 10, 0)
        self._status_lbl = QLabel("就绪")
        self._status_lbl.setStyleSheet("color:#6c757d;font-size:11px;")
        lay.addWidget(self._status_lbl)
        lay.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet("color:#6c757d;font-size:11px;")
        lay.addWidget(self._stats_lbl)
        return w

    # ── engine ────────────────────────────────────────────────────

    def _start_engine(self) -> None:
        try:
            if self._engine:
                self._engine.start()
            self._set_status("PlatformEngine 已启动")
        except Exception as e:
            self._set_status(f"启动失败: {e}")

    def _refresh_status(self) -> None:
        if not self._engine:
            return
        try:
            s      = self._engine.get_platform_stats()
            obs    = s.get("observability", {})
            level  = obs.get("health_level", "green").upper()
            score  = obs.get("health_score", 100.0)
            alerts = obs.get("active_alerts", 0)
            tasks  = s.get("tasks", {})

            color = {"GREEN": "#52c41a", "YELLOW": "#faad14",
                     "RED": "#ff4d4f"}.get(level, "#52c41a")
            self._health_badge.setText(f"● {level}")
            self._health_badge.setStyleSheet(
                f"color:{color};font-size:12px;background:transparent;"
                f"padding:2px 10px;border:1px solid {color};border-radius:10px;")
            self._stats_lbl.setText(
                f"健康分: {score:.0f}  |  告警: {alerts}"
                f"  |  运行任务: {tasks.get('running', 0)}"
                f"  |  待处理: {tasks.get('pending', 0)}")
        except Exception as e:
            self._set_status(f"刷新失败: {e}")

    def _set_status(self, msg: str) -> None:
        self._status_lbl.setText(msg)

    def closeEvent(self, event) -> None:
        self._timer.stop()
        if self._engine:
            self._engine.stop()
        super().closeEvent(event)
