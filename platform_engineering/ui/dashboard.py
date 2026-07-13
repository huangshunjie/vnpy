"""
platform_engineering/ui/dashboard.py
DashboardTab — Phase 2
健康分环形图 + 四层KPI卡片 + 统计概览 + 告警面板
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGridLayout, QFrame, QPushButton, QScrollArea,
    QAbstractItemView, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QFont

if TYPE_CHECKING:
    from ..engine_main import PlatformEngine

from ..constant import MetricLayer, AlertSeverity, HealthLevel
from ..model.metric import AlertRecord

LEVEL_COLOR = {
    HealthLevel.GREEN:  "#52c41a",
    HealthLevel.YELLOW: "#faad14",
    HealthLevel.RED:    "#ff4d4f",
}
SEV_COLOR = {
    AlertSeverity.INFO:     "#1890ff",
    AlertSeverity.WARNING:  "#faad14",
    AlertSeverity.ERROR:    "#ff4d4f",
    AlertSeverity.CRITICAL: "#9c27b0",
}
LAYER_COLOR = {
    MetricLayer.DATA:     "#1890ff",
    MetricLayer.STRATEGY: "#52c41a",
    MetricLayer.TRADING:  "#faad14",
    MetricLayer.SYSTEM:   "#722ed1",
}
LAYER_ICON = {
    MetricLayer.DATA:     "\U0001f4ca",
    MetricLayer.STRATEGY: "\U0001f4c8",
    MetricLayer.TRADING:  "\u26a1",
    MetricLayer.SYSTEM:   "\U0001f4bb",
}


class HealthRingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._score = 100.0
        self._level = HealthLevel.GREEN
        self.setMinimumSize(160, 160)
        self.setMaximumSize(200, 200)

    def update_score(self, score: float, level: HealthLevel) -> None:
        self._score = score; self._level = level; self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin = 16
        rect = QRectF(margin, margin, w - 2*margin, h - 2*margin)
        pen_bg = QPen(QColor("#e8e8e8"), 14, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen_bg); painter.drawArc(rect, 0, 360 * 16)
        color = LEVEL_COLOR.get(self._level, "#52c41a")
        span  = int(self._score / 100.0 * 360 * 16)
        pen_fg = QPen(QColor(color), 14, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen_fg); painter.drawArc(rect, 90 * 16, -span)
        painter.setPen(QColor(color))
        font = QFont(); font.setPointSize(22); font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, f"{self._score:.0f}")
        painter.end()


class LayerScoreCard(QFrame):
    def __init__(self, layer: MetricLayer, parent=None):
        super().__init__(parent)
        self._layer = layer
        color = LAYER_COLOR[layer]
        self.setStyleSheet(
            f"QFrame{{background:#fff;border-radius:8px;"
            f"border-left:4px solid {color};"
            f"border-top:1px solid #f0f0f0;"
            f"border-right:1px solid #f0f0f0;"
            f"border-bottom:1px solid #f0f0f0;}}")
        self.setFixedHeight(68)
        lay = QHBoxLayout(self); lay.setContentsMargins(12, 6, 12, 6)
        icon = QLabel(LAYER_ICON[layer])
        icon.setStyleSheet("font-size:22px;background:transparent;border:none;")
        lay.addWidget(icon)
        texts = QVBoxLayout(); texts.setSpacing(2)
        self._score_lbl = QLabel("100")
        self._score_lbl.setStyleSheet(
            f"font-size:20px;font-weight:bold;color:{color};"
            "background:transparent;border:none;")
        self._name_lbl = QLabel(layer.value.upper())
        self._name_lbl.setStyleSheet(
            "font-size:10px;color:#8c8c8c;background:transparent;border:none;")
        texts.addWidget(self._score_lbl); texts.addWidget(self._name_lbl)
        lay.addLayout(texts); lay.addStretch()
        self._badge = QLabel("GREEN")
        self._badge.setStyleSheet(
            "font-size:10px;padding:2px 6px;border-radius:8px;"
            "background:#f6ffed;color:#52c41a;border:none;")
        lay.addWidget(self._badge)

    def update_score(self, score: float, level: HealthLevel) -> None:
        color = LEVEL_COLOR.get(level, "#52c41a")
        lc    = LAYER_COLOR[self._layer]
        self._score_lbl.setText(f"{score:.0f}")
        self._score_lbl.setStyleSheet(
            f"font-size:20px;font-weight:bold;color:{lc};"
            "background:transparent;border:none;")
        self._badge.setText(level.value.upper())
        bg_map = {
            HealthLevel.GREEN:  "#f6ffed",
            HealthLevel.YELLOW: "#fffbe6",
            HealthLevel.RED:    "#fff2f0",
        }
        self._badge.setStyleSheet(
            f"font-size:10px;padding:2px 6px;border-radius:8px;"
            f"background:{bg_map.get(level,'#f6ffed')};color:{color};border:none;")


class StatCard(QFrame):
    def __init__(self, label: str, icon: str, color: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame{background:#fff;border-radius:8px;border:1px solid #f0f0f0;}")
        self.setFixedHeight(80)
        lay = QVBoxLayout(self); lay.setContentsMargins(14, 8, 14, 8); lay.setSpacing(2)
        top = QHBoxLayout()
        ilbl = QLabel(icon)
        ilbl.setStyleSheet(
            f"font-size:18px;color:{color};background:transparent;border:none;")
        top.addWidget(ilbl); top.addStretch()
        lay.addLayout(top)
        self._val = QLabel("\u2014")
        self._val.setStyleSheet(
            f"font-size:22px;font-weight:bold;color:{color};"
            "background:transparent;border:none;")
        lay.addWidget(self._val)
        lbl = QLabel(label)
        lbl.setStyleSheet(
            "font-size:11px;color:#8c8c8c;background:transparent;border:none;")
        lay.addWidget(lbl)

    def set_value(self, v) -> None:
        self._val.setText(str(v))


class AlertRow(QFrame):
    def __init__(self, alert: AlertRecord, parent=None):
        super().__init__(parent)
        color = SEV_COLOR.get(alert.severity, "#faad14")
        self.setStyleSheet(
            f"QFrame{{background:#fff;border-radius:6px;"
            f"border-left:3px solid {color};"
            f"border-top:1px solid #f5f5f5;"
            f"border-right:1px solid #f5f5f5;"
            f"border-bottom:1px solid #f5f5f5;margin-bottom:3px;}}")
        lay = QHBoxLayout(self); lay.setContentsMargins(10, 6, 10, 6)
        sev = QLabel(alert.severity.value.upper())
        sev.setStyleSheet(
            f"font-size:10px;font-weight:bold;color:{color};"
            f"background:{color}1a;padding:1px 6px;border-radius:6px;border:none;")
        sev.setFixedWidth(64); lay.addWidget(sev)
        msg = QLabel(alert.message)
        msg.setStyleSheet(
            "font-size:12px;color:#262626;background:transparent;border:none;")
        msg.setWordWrap(True); lay.addWidget(msg, 1)
        ts = QLabel(alert.created_at.strftime("%H:%M:%S"))
        ts.setStyleSheet(
            "font-size:10px;color:#bfbfbf;background:transparent;border:none;")
        lay.addWidget(ts)


class DashboardTab(QWidget):
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
        root.setSpacing(12)

        # header
        hdr = QHBoxLayout()
        title = QLabel("Platform Health Dashboard")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        self._last_update = QLabel("")
        self._last_update.setStyleSheet("font-size:11px;color:#8c8c8c;")
        hdr.addWidget(self._last_update)
        btn = QPushButton("\U0001f504 \u5237\u65b0")
        btn.setFixedSize(68, 26)
        btn.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;"
            "font-size:12px;border:none;")
        btn.clicked.connect(self._refresh)
        hdr.addWidget(btn)
        root.addLayout(hdr)

        body = QHBoxLayout(); body.setSpacing(12)
        left = QVBoxLayout(); left.setSpacing(10)

        # ring + layer cards
        ring_row = QHBoxLayout(); ring_row.setSpacing(12)
        self._ring = HealthRingWidget()
        ring_row.addWidget(self._ring)
        ring_right = QVBoxLayout(); ring_right.setSpacing(6)
        self._layer_cards: dict = {}
        for layer in MetricLayer:
            card = LayerScoreCard(layer)
            self._layer_cards[layer] = card
            ring_right.addWidget(card)
        ring_row.addLayout(ring_right, 1)
        left.addLayout(ring_row)

        # stat cards grid
        sg = QGridLayout(); sg.setSpacing(8)
        self._stat_cards: dict = {}
        card_defs = [
            ("deploy_total", "\u90e8\u7f72\u603b\u6570", "\U0001f680", "#4a6cf7"),
            ("deploy_live",  "\u751f\u4ea7\u8fd0\u884c", "\u2705",     "#52c41a"),
            ("task_running", "\u8fd0\u884c\u4efb\u52a1", "\u2699\ufe0f","#faad14"),
            ("task_pending", "\u5f85\u5904\u7406",        "\u23f3",     "#8c8c8c"),
            ("task_failed",  "\u5931\u8d25\u4efb\u52a1", "\u274c",     "#ff4d4f"),
            ("health_warn",  "\u7b56\u7565\u544a\u8b66", "\U0001f493","#faad14"),
            ("configs",      "\u914d\u7f6e\u9879",        "\U0001f5c2\ufe0f","#722ed1"),
            ("users",        "\u7528\u6237\u6570",        "\U0001f464", "#13c2c2"),
        ]
        for i, (key, label, icon, color) in enumerate(card_defs):
            card = StatCard(label, icon, color)
            self._stat_cards[key] = card
            sg.addWidget(card, i // 4, i % 4)
        left.addLayout(sg)
        body.addLayout(left, 3)

        # right: alert panel
        right = QVBoxLayout(); right.setSpacing(6)
        alert_hdr = QHBoxLayout()
        atitle = QLabel("\U0001f514 \u6d3b\u8dc3\u544a\u8b66")
        atitle.setStyleSheet("font-size:13px;font-weight:bold;color:#1a1f36;")
        alert_hdr.addWidget(atitle); alert_hdr.addStretch()
        self._alert_count = QLabel("0")
        self._alert_count.setStyleSheet(
            "background:#52c41a;color:#fff;border-radius:8px;"
            "padding:1px 7px;font-size:11px;")
        alert_hdr.addWidget(self._alert_count)
        right.addLayout(alert_hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:#f8f9fa;border-radius:6px;")
        self._alert_container = QWidget()
        self._alert_layout    = QVBoxLayout(self._alert_container)
        self._alert_layout.setAlignment(Qt.AlignTop)
        self._alert_layout.setSpacing(0)
        scroll.setWidget(self._alert_container)
        right.addWidget(scroll, 1)

        self._no_alert_lbl = QLabel("\u2705 \u6240\u6709\u7cfb\u7edf\u8fd0\u884c\u6b63\u5e38")
        self._no_alert_lbl.setAlignment(Qt.AlignCenter)
        self._no_alert_lbl.setStyleSheet(
            "font-size:13px;color:#52c41a;padding:20px;")
        self._alert_layout.addWidget(self._no_alert_lbl)

        body.addLayout(right, 2)
        root.addLayout(body, 1)

    def _refresh(self):
        if not self._engine:
            return
        try:
            oe = self._engine.observability
            sc = oe.get_health_score()
            self._ring.update_score(sc.score, sc.level)

            layer_map = {
                MetricLayer.DATA:     sc.data_score,
                MetricLayer.STRATEGY: sc.strategy_score,
                MetricLayer.TRADING:  sc.trading_score,
                MetricLayer.SYSTEM:   sc.system_score,
            }
            for layer, card in self._layer_cards.items():
                s = layer_map[layer]
                lv = (HealthLevel.GREEN if s >= 80 else
                      HealthLevel.YELLOW if s >= 50 else HealthLevel.RED)
                card.update_score(s, lv)

            ts  = self._engine.tasks.stats()
            ds  = self._engine.deployment.stats()
            hs  = self._engine.health.stats()
            cs  = self._engine.config.stats()
            ss  = self._engine.security.stats()
            by_stage = ds.get("by_stage", {})

            self._stat_cards["deploy_total"].set_value(ds.get("total", 0))
            self._stat_cards["deploy_live"].set_value(
                by_stage.get("production", 0))
            self._stat_cards["task_running"].set_value(ts.get("running", 0))
            self._stat_cards["task_pending"].set_value(ts.get("pending", 0))
            self._stat_cards["task_failed"].set_value(ts.get("failed", 0))
            self._stat_cards["health_warn"].set_value(
                hs.get("warning", 0) + hs.get("critical", 0))
            self._stat_cards["configs"].set_value(cs.get("total", 0))
            self._stat_cards["users"].set_value(ss.get("users", 0))

            alerts = oe.list_alerts(active_only=True)
            self._rebuild_alerts(alerts)
            self._last_update.setText(
                "\u66f4\u65b0: " + sc.updated_at.strftime("%H:%M:%S"))
        except Exception:
            pass

    def _rebuild_alerts(self, alerts):
        while self._alert_layout.count():
            item = self._alert_layout.takeAt(0)
            if item.widget() and item.widget() is not self._no_alert_lbl:
                item.widget().deleteLater()
        if not alerts:
            self._alert_count.setText("0")
            self._alert_count.setStyleSheet(
                "background:#52c41a;color:#fff;border-radius:8px;"
                "padding:1px 7px;font-size:11px;")
            self._alert_layout.addWidget(self._no_alert_lbl)
            self._no_alert_lbl.show()
        else:
            self._no_alert_lbl.hide()
            self._alert_count.setText(str(len(alerts)))
            self._alert_count.setStyleSheet(
                "background:#ff4d4f;color:#fff;border-radius:8px;"
                "padding:1px 7px;font-size:11px;")
            for alert in sorted(
                    alerts, key=lambda a: a.created_at, reverse=True)[:30]:
                row = AlertRow(alert)
                self._alert_layout.addWidget(row)

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
