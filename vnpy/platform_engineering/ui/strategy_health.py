"""
platform_engineering/ui/strategy_health.py
StrategyHealthTab — Phase 5
策略健康总览 + 四维评分卡 + 指标详情 + 告警建议
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QSplitter, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox, QLineEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QDoubleSpinBox, QScrollArea,
    QGridLayout,
)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QColor, QBrush, QPainter, QPen, QFont

if TYPE_CHECKING:
    from ..engine_main import PlatformEngine

from ..constant import HealthStatus, HealthLevel
from ..model.health import StrategyHealthRecord, HealthMetricSnapshot

STATUS_COLOR = {
    HealthStatus.HEALTHY:  "#52c41a",
    HealthStatus.WARNING:  "#faad14",
    HealthStatus.CRITICAL: "#ff4d4f",
    HealthStatus.RETIRE:   "#9c27b0",
    HealthStatus.UNKNOWN:  "#8c8c8c",
}
STATUS_ICON = {
    HealthStatus.HEALTHY:  "💚",
    HealthStatus.WARNING:  "⚠️",
    HealthStatus.CRITICAL: "🔴",
    HealthStatus.RETIRE:   "⛔",
    HealthStatus.UNKNOWN:  "❓",
}
LEVEL_COLOR = {
    HealthLevel.GREEN:  "#52c41a",
    HealthLevel.YELLOW: "#faad14",
    HealthLevel.RED:    "#ff4d4f",
}
DIM_COLOR = {
    "perf":  "#4a6cf7",
    "risk":  "#52c41a",
    "alpha": "#faad14",
    "exec":  "#722ed1",
}
ROLE_ID = Qt.UserRole


class ScoreRing(QWidget):
    """单维度评分环形图。"""
    def __init__(self, label: str, color: str, parent=None):
        super().__init__(parent)
        self._score = 0.0
        self._label = label
        self._color = color
        self.setFixedSize(110, 110)

    def set_score(self, score: float):
        self._score = max(0.0, min(100.0, score)); self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height(); m = 10
        rect = QRectF(m, m, w-2*m, h-2*m)
        p.setPen(QPen(QColor("#e8e8e8"), 10, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, 0, 360*16)
        span = int(self._score/100.0*360*16)
        p.setPen(QPen(QColor(self._color), 10, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, 90*16, -span)
        p.setPen(QColor(self._color))
        f = QFont(); f.setPointSize(14); f.setBold(True); p.setFont(f)
        p.drawText(QRectF(m, m, w-2*m, h-2*m-14), Qt.AlignCenter,
                   f"{self._score:.0f}")
        f2 = QFont(); f2.setPointSize(8); p.setFont(f2)
        p.setPen(QColor("#8c8c8c"))
        p.drawText(QRectF(0, h-18, w, 14), Qt.AlignCenter, self._label)
        p.end()


class DimScorePanel(QWidget):
    """四维评分面板（4个 ScoreRing）。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(8)
        self._rings = {}
        for key, label, color in [
            ("perf",  "性能",  DIM_COLOR["perf"]),
            ("risk",  "风险",  DIM_COLOR["risk"]),
            ("alpha", "Alpha", DIM_COLOR["alpha"]),
            ("exec",  "执行",  DIM_COLOR["exec"]),
        ]:
            ring = ScoreRing(label, color)
            self._rings[key] = ring
            lay.addWidget(ring)

    def update_scores(self, rec: StrategyHealthRecord):
        self._rings["perf"].set_score(rec.perf_score)
        self._rings["risk"].set_score(rec.risk_score)
        self._rings["alpha"].set_score(rec.alpha_score)
        self._rings["exec"].set_score(rec.exec_score)

    def clear(self):
        for r in self._rings.values(): r.set_score(0.0)


class RegisterStrategyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("注册策略")
        self.setMinimumWidth(380)
        root = QVBoxLayout(self)
        grp  = QGroupBox("策略信息")
        form = QFormLayout(grp)
        self._sid  = QLineEdit(); self._sid.setPlaceholderText("STR-001")
        form.addRow("策略 ID *", self._sid)
        self._name = QLineEdit()
        form.addRow("策略名称 *", self._name)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("注册")
        btns.button(QDialogButtonBox.Cancel).setText("取消")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        if not self._sid.text().strip():  self._sid.setFocus();  return
        if not self._name.text().strip(): self._name.setFocus(); return
        self.accept()

    def get_strategy_id(self)   -> str: return self._sid.text().strip()
    def get_strategy_name(self) -> str: return self._name.text().strip()


class UpdateSnapshotDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("更新指标快照")
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)

        def _spin(lo, hi, dec, val):
            s = QDoubleSpinBox()
            s.setRange(lo, hi); s.setDecimals(dec)
            s.setValue(val); return s

        grp  = QGroupBox("指标值（留空 = 不更新）")
        form = QFormLayout(grp)
        self._sharpe    = _spin(-5, 10, 2, 1.0);   form.addRow("Sharpe Ratio",    self._sharpe)
        self._maxdd     = _spin(0, 1,  3, 0.10);   form.addRow("最大回撤 (0-1)",   self._maxdd)
        self._winrate   = _spin(0, 1,  3, 0.55);   form.addRow("胜率 (0-1)",       self._winrate)
        self._risk_exp  = _spin(0, 2,  3, 0.20);   form.addRow("风险敞口 (0-1)",   self._risk_exp)
        self._ic        = _spin(-1, 1, 3, 0.05);   form.addRow("IC 均值",          self._ic)
        self._alpha_dec = _spin(0, 1,  3, 0.10);   form.addRow("Alpha 衰减 (0-1)", self._alpha_dec)
        self._delay     = _spin(0, 5000, 0, 200.0); form.addRow("订单延迟 (ms)",   self._delay)
        self._fill      = _spin(0, 1,  3, 0.98);   form.addRow("成交率 (0-1)",     self._fill)
        self._slip      = _spin(0, 200, 1, 5.0);   form.addRow("滑点 (bps)",       self._slip)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("更新")
        btns.button(QDialogButtonBox.Cancel).setText("取消")
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def get_snapshot(self) -> HealthMetricSnapshot:
        from datetime import datetime
        return HealthMetricSnapshot(
            sharpe        = self._sharpe.value(),
            max_drawdown  = self._maxdd.value(),
            win_rate      = self._winrate.value(),
            risk_exposure = self._risk_exp.value(),
            ic_mean       = self._ic.value(),
            alpha_decay   = self._alpha_dec.value(),
            order_delay_ms= self._delay.value(),
            fill_rate     = self._fill.value(),
            slippage_bps  = self._slip.value(),
            updated_at    = datetime.now(),
        )


class HealthList(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._on_select = None
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_reg = QPushButton("\u2795 \u6ce8\u518c\u7b56\u7565")
        self._btn_reg.setFixedHeight(26)
        self._btn_reg.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_reg.clicked.connect(self._on_register)
        tb.addWidget(self._btn_reg)
        self._status_combo = QComboBox(); self._status_combo.setFixedHeight(26)
        self._status_combo.addItem("\u5168\u90e8", None)
        for s in HealthStatus:
            self._status_combo.addItem(STATUS_ICON.get(s,"")+" "+s.value, s)
        self._status_combo.currentIndexChanged.connect(lambda _: self.refresh())
        tb.addWidget(self._status_combo, 1)
        tb.addStretch()
        root.addLayout(tb)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "\u7b56\u7565\u540d\u79f0","\u72b6\u6001","\u603b\u5206",
            "\u6027\u80fd","\u98ce\u9669"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.itemClicked.connect(self._on_click)
        root.addWidget(self._table)

    def set_select_callback(self, cb): self._on_select = cb

    def refresh(self):
        if not self._engine: return
        flt   = self._status_combo.currentData()
        items = self._engine.health.list_health(status=flt)
        self._table.setRowCount(0)
        for rec in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(rec.strategy_name))
            color = STATUS_COLOR.get(rec.status, "#8c8c8c")
            icon  = STATUS_ICON.get(rec.status, "")
            si = QTableWidgetItem(icon+" "+rec.status.value)
            si.setForeground(QBrush(QColor(color)))
            self._table.setItem(r, 1, si)
            sc = QTableWidgetItem(f"{rec.score:.1f}")
            sc.setForeground(QBrush(QColor(color)))
            sc.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(r, 2, sc)
            self._table.setItem(r, 3,
                QTableWidgetItem(f"{rec.perf_score:.1f}"))
            self._table.setItem(r, 4,
                QTableWidgetItem(f"{rec.risk_score:.1f}"))
            for c in range(5):
                self._table.item(r, c).setData(ROLE_ID, rec.strategy_id)

    def _on_click(self, item):
        if self._on_select: self._on_select(item.data(ROLE_ID))

    def _on_register(self):
        if not self._engine: return
        dlg = RegisterStrategyDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._engine.health.register_strategy(
                dlg.get_strategy_id(), dlg.get_strategy_name())
            self.refresh()


class DetailPanel(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._sid    = None
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8,0,0,0); root.setSpacing(8)

        # title row
        hdr = QHBoxLayout()
        self._title = QLabel("\u8bf7\u9009\u62e9\u7b56\u7565")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title); hdr.addStretch()
        self._status_badge = QLabel("")
        self._status_badge.setStyleSheet(
            "font-size:14px;padding:2px 10px;border-radius:10px;")
        hdr.addWidget(self._status_badge)
        root.addLayout(hdr)

        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        root.addWidget(self._bar)

        # update snapshot button
        tb = QHBoxLayout()
        self._btn_update = QPushButton("\U0001f4ca  \u66f4\u65b0\u6307\u6807\u5feb\u7167")
        self._btn_update.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_update.setFixedHeight(28)
        self._btn_update.clicked.connect(self._on_update_snapshot)
        tb.addWidget(self._btn_update); tb.addStretch()
        self._score_lbl = QLabel("\u603b\u5206: \u2014")
        self._score_lbl.setStyleSheet("font-size:18px;font-weight:bold;color:#4a6cf7;")
        tb.addWidget(self._score_lbl)
        root.addLayout(tb)

        # four dim rings
        self._dim_panel = DimScorePanel()
        root.addWidget(self._dim_panel)

        # metric table
        mg = QGroupBox("\u6307\u6807\u5feb\u7167")
        ml = QVBoxLayout(mg)
        self._metric_table = QTableWidget(0, 2)
        self._metric_table.setHorizontalHeaderLabels(["\u6307\u6807","\u5f53\u524d\u5024"])
        self._metric_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._metric_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._metric_table.setAlternatingRowColors(True)
        self._metric_table.verticalHeader().setVisible(False)
        self._metric_table.setFixedHeight(220)
        ml.addWidget(self._metric_table)
        root.addWidget(mg)

        # warnings
        wg = QGroupBox("\u544a\u8b66\u4e0e\u5efa\u8bae")
        wl = QVBoxLayout(wg)
        self._warn_scroll = QScrollArea()
        self._warn_scroll.setWidgetResizable(True)
        self._warn_scroll.setFrameShape(QFrame.NoFrame)
        self._warn_scroll.setFixedHeight(120)
        self._warn_container = QWidget()
        self._warn_layout    = QVBoxLayout(self._warn_container)
        self._warn_layout.setAlignment(Qt.AlignTop)
        self._warn_scroll.setWidget(self._warn_container)
        wl.addWidget(self._warn_scroll)
        root.addWidget(wg, 1)

    def load(self, strategy_id: str):
        self._sid = strategy_id
        rec = self._engine.health.get_health(strategy_id)
        if rec: self._render(rec)

    def _render(self, rec: StrategyHealthRecord):
        color = STATUS_COLOR.get(rec.status, "#8c8c8c")
        icon  = STATUS_ICON.get(rec.status, "")
        self._title.setText(rec.strategy_name)
        self._bar.setStyleSheet(f"background:{color};border-radius:2px;")
        self._status_badge.setText(icon+" "+rec.status.value.upper())
        self._status_badge.setStyleSheet(
            f"font-size:14px;padding:2px 10px;border-radius:10px;"
            f"background:{color}22;color:{color};border:1px solid {color}44;")
        self._score_lbl.setText(f"\u603b\u5206: {rec.score:.1f}")
        self._score_lbl.setStyleSheet(
            f"font-size:18px;font-weight:bold;color:{color};")
        self._dim_panel.update_scores(rec)

        # metric table
        self._metric_table.setRowCount(0)
        snap = rec.snapshot
        rows = []
        if snap:
            rows = [
                ("Sharpe Ratio",        snap.sharpe,         ""),
                ("\u6700\u5927\u56de\u64a4",   snap.max_drawdown,   "%",  100),
                ("\u80dc\u7387",              snap.win_rate,       "%",  100),
                ("IC \u5747\u5024",          snap.ic_mean,        ""),
                ("Alpha \u8870\u51cf",        snap.alpha_decay,    "%",  100),
                ("\u98ce\u9669\u655e\u53e3",        snap.risk_exposure,  "%",  100),
                ("\u8ba2\u5355\u5ef6\u8fdf (ms)",   snap.order_delay_ms, "ms"),
                ("\u6210\u4ea4\u7387",          snap.fill_rate,      "%",  100),
                ("\u6ed1\u70b9 (bps)",        snap.slippage_bps,   "bps"),
            ]
        for row in rows:
            name   = row[0]
            val    = row[1]
            unit   = row[2]
            mult   = row[3] if len(row) > 3 else 1
            r = self._metric_table.rowCount()
            self._metric_table.insertRow(r)
            ki = QTableWidgetItem(name)
            ki.setForeground(QBrush(QColor("#8c8c8c")))
            self._metric_table.setItem(r, 0, ki)
            if val is None:
                self._metric_table.setItem(r, 1, QTableWidgetItem("\u2014"))
            else:
                display = f"{val*mult:.2f}{unit}"
                self._metric_table.setItem(r, 1, QTableWidgetItem(display))

        # warnings
        while self._warn_layout.count():
            item = self._warn_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        if not rec.warnings:
            ok = QLabel("\u2705  \u65e0\u544a\u8b66\uff0c\u7b56\u7565\u8fd0\u884c\u6b63\u5e38")
            ok.setStyleSheet("color:#52c41a;font-size:14px;padding:4px;")
            self._warn_layout.addWidget(ok)
        else:
            for w in rec.warnings:
                lbl = QLabel("\u26a0\ufe0f  " + w)
                lbl.setStyleSheet(
                    "color:#faad14;font-size:14px;padding:2px 4px;"
                    "background:#fffbe6;border-radius:4px;margin-bottom:2px;")
                lbl.setWordWrap(True)
                self._warn_layout.addWidget(lbl)

    def _on_update_snapshot(self):
        if not self._sid: return
        dlg = UpdateSnapshotDialog(self)
        if dlg.exec() == QDialog.Accepted:
            snap = dlg.get_snapshot()
            self._engine.health.update_snapshot(self._sid, snap)
            self.load(self._sid)


class StrategyHealthTab(QWidget):
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
        root.setContentsMargins(12,12,12,12); root.setSpacing(8)

        hdr = QHBoxLayout()
        title = QLabel("\U0001f493  Strategy Health Monitor")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet("font-size:14px;color:#8c8c8c;")
        hdr.addWidget(self._stats_lbl)
        btn = QPushButton("\U0001f504 \u5237\u65b0")
        btn.setFixedSize(68, 26)
        btn.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;"
            "font-size:14px;border:none;")
        btn.clicked.connect(self._refresh)
        hdr.addWidget(btn)
        root.addLayout(hdr)

        sp = QSplitter(Qt.Horizontal)
        self._health_list  = HealthList(self._engine)
        self._detail_panel = DetailPanel(self._engine)
        self._health_list.set_select_callback(self._on_selected)
        sp.addWidget(self._health_list)
        sp.addWidget(self._detail_panel)
        sp.setSizes([300, 900])
        sp.setStretchFactor(0, 0); sp.setStretchFactor(1, 1)
        root.addWidget(sp, 1)

        self._status_bar = QLabel("\u5c31\u7eea")
        self._status_bar.setStyleSheet("font-size:14px;color:#6c757d;")
        root.addWidget(self._status_bar)

    def _on_selected(self, sid: str):
        self._detail_panel.load(sid)

    def _refresh(self):
        self._health_list.refresh()
        if self._engine:
            s = self._engine.health.stats()
            self._stats_lbl.setText(
                f"\u603b\u8ba1: {s.get('total',0)}"
                f"  \u5065\u5eb7: {s.get('healthy',0)}"
                f"  \u544a\u8b66: {s.get('warning',0)}"
                f"  \u4e25\u91cd: {s.get('critical',0)}"
                f"  \u9000\u5f39: {s.get('retire',0)}"
                f"  \u5747\u5206: {s.get('avg_score',0.0):.1f}")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
