"""
platform_engineering/ui/monitor.py
ObservabilityTab — Phase 2
四层实时指标表格 + 告警管理 + 规则列表
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox, QScrollArea,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush, QFont

if TYPE_CHECKING:
    from ..engine_main import PlatformEngine

from ..constant import MetricLayer, AlertSeverity, HealthLevel
from ..model.metric import MetricPoint, AlertRecord

LAYER_COLOR = {
    MetricLayer.DATA:     "#1890ff",
    MetricLayer.STRATEGY: "#52c41a",
    MetricLayer.TRADING:  "#faad14",
    MetricLayer.SYSTEM:   "#722ed1",
}
SEV_COLOR = {
    AlertSeverity.INFO:     "#1890ff",
    AlertSeverity.WARNING:  "#faad14",
    AlertSeverity.ERROR:    "#ff4d4f",
    AlertSeverity.CRITICAL: "#9c27b0",
}
ROLE_LAYER = Qt.UserRole


class MetricTable(QWidget):
    """单层实时指标表格。"""

    def __init__(self, layer: MetricLayer, parent=None):
        super().__init__(parent)
        self._layer = layer
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["\u6307\u6807\u540d\u79f0", "\u5f53\u524d\u5024", "\u5355\u4f4d", "\u66f4\u65b0\u65f6\u95f4"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        root.addWidget(self._table)

    def refresh(self, series_list) -> None:
        layer_series = [s for s in series_list if s.layer == self._layer]
        self._table.setRowCount(0)
        color = LAYER_COLOR.get(self._layer, "#1a1f36")
        for s in layer_series:
            pt = s.latest()
            if not pt:
                continue
            r = self._table.rowCount()
            self._table.insertRow(r)
            ni = QTableWidgetItem(pt.name)
            ni.setForeground(QBrush(QColor(color)))
            self._table.setItem(r, 0, ni)
            vi = QTableWidgetItem(f"{pt.value:.4g}")
            vi.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(r, 1, vi)
            self._table.setItem(r, 2, QTableWidgetItem(pt.unit))
            self._table.setItem(r, 3,
                QTableWidgetItem(pt.timestamp.strftime("%H:%M:%S")))


class AlertTable(QWidget):
    """告警列表 + 手动解除。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = None
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        tb = QHBoxLayout()
        self._combo = QComboBox()
        self._combo.addItem("\u6d3b\u8dc3\u544a\u8b66", True)
        self._combo.addItem("\u5168\u90e8\u544a\u8b66", False)
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._refresh)
        tb.addWidget(self._combo)
        self._btn_resolve = QPushButton("\u2713  \u624b\u52a8\u89e3\u9664")
        self._btn_resolve.setFixedHeight(26)
        self._btn_resolve.setStyleSheet(
            "background:#52c41a;color:#fff;border-radius:4px;border:none;")
        self._btn_resolve.clicked.connect(self._on_resolve)
        tb.addWidget(self._btn_resolve)
        tb.addStretch()
        self._count_lbl = QLabel("0 \u6761")
        self._count_lbl.setStyleSheet("font-size:14px;color:#8c8c8c;")
        tb.addWidget(self._count_lbl)
        root.addLayout(tb)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "\u7ea7\u522b", "\u540d\u79f0", "\u6d88\u606f", "\u5c42\u6b21", "\u65f6\u95f4"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        root.addWidget(self._table)
        self._alerts = []

    def set_engine(self, engine) -> None:
        self._engine = engine

    def _refresh(self):
        if not self._engine:
            return
        active_only = self._combo.currentData()
        self._alerts = self._engine.observability.list_alerts(active_only=active_only)
        self._table.setRowCount(0)
        for alert in self._alerts:
            r = self._table.rowCount()
            self._table.insertRow(r)
            color = SEV_COLOR.get(alert.severity, "#faad14")
            si = QTableWidgetItem(alert.severity.value.upper())
            si.setForeground(QBrush(QColor(color)))
            self._table.setItem(r, 0, si)
            self._table.setItem(r, 1, QTableWidgetItem(alert.name))
            self._table.setItem(r, 2, QTableWidgetItem(alert.message))
            li = QTableWidgetItem(alert.layer.value)
            li.setForeground(QBrush(QColor(LAYER_COLOR.get(alert.layer, "#1a1f36"))))
            self._table.setItem(r, 3, li)
            self._table.setItem(r, 4,
                QTableWidgetItem(alert.created_at.strftime("%H:%M:%S")))
            for c in range(5):
                self._table.item(r, c).setData(Qt.UserRole, alert.alert_id)
        self._count_lbl.setText(f"{len(self._alerts)} \u6761")

    def _on_resolve(self):
        if not self._engine:
            return
        items = self._table.selectedItems()
        if not items:
            return
        alert_id = items[0].data(Qt.UserRole)
        self._engine.observability.resolve_alert(alert_id)
        self._refresh()

    def refresh(self):
        self._refresh()


class RuleTable(QWidget):
    """告警规则列表（只读）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "\u540d\u79f0", "\u6307\u6807", "\u5c42\u6b21",
            "\u9608\u5024", "\u7ea7\u522b"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        root.addWidget(self._table)

    def refresh(self, rules) -> None:
        self._table.setRowCount(0)
        for rule in rules:
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(rule.name))
            self._table.setItem(r, 1, QTableWidgetItem(rule.metric_name))
            li = QTableWidgetItem(rule.layer.value)
            li.setForeground(QBrush(QColor(LAYER_COLOR.get(rule.layer, "#1a1f36"))))
            self._table.setItem(r, 2, li)
            self._table.setItem(r, 3,
                QTableWidgetItem(f"{rule.comparator} {rule.threshold}"))
            color = SEV_COLOR.get(rule.severity, "#faad14")
            si = QTableWidgetItem(rule.severity.value.upper())
            si.setForeground(QBrush(QColor(color)))
            self._table.setItem(r, 4, si)


class ObservabilityTab(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(5_000)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        hdr = QHBoxLayout()
        title = QLabel("\U0001f52d  Quant Observability Platform")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        btn = QPushButton("\U0001f504 \u5237\u65b0")
        btn.setFixedSize(68, 26)
        btn.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;"
            "font-size:14px;border:none;")
        btn.clicked.connect(self._refresh)
        hdr.addWidget(btn)
        root.addLayout(hdr)

        self._sub = QTabWidget(); self._sub.setDocumentMode(True)

        # four layer tabs
        self._metric_tabs: dict = {}
        layer_labels = {
            MetricLayer.DATA:     "\U0001f4ca  Data",
            MetricLayer.STRATEGY: "\U0001f4c8  Strategy",
            MetricLayer.TRADING:  "\u26a1  Trading",
            MetricLayer.SYSTEM:   "\U0001f4bb  System",
        }
        for layer, label in layer_labels.items():
            mt = MetricTable(layer)
            self._metric_tabs[layer] = mt
            self._sub.addTab(mt, label)

        # alerts tab
        self._alert_table = AlertTable()
        if self._engine:
            self._alert_table.set_engine(self._engine)
        self._sub.addTab(self._alert_table, "\U0001f514  \u544a\u8b66")

        # rules tab
        self._rule_table = RuleTable()
        self._sub.addTab(self._rule_table, "\U0001f4cb  \u89c4\u5219")

        root.addWidget(self._sub, 1)

    def _refresh(self):
        if not self._engine:
            return
        try:
            series = self._engine.observability.list_series()
            for mt in self._metric_tabs.values():
                mt.refresh(series)
            self._alert_table.refresh()
            rules = self._engine.observability.list_rules()
            self._rule_table.refresh(rules)
        except Exception:
            pass

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
