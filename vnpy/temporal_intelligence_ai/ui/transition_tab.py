"""
temporal_intelligence_ai/ui/transition_tab.py  (Phase 5)

Regime Transition Tab — 状态转移可视化面板。

布局：
  上方：转移总览卡片
  中部左：三类信号强度仪表盘
  中部右：Regime 概率分布柱状图
  中部：转移概率时间线
  下方：已确认转移事件列表
"""
from __future__ import annotations

from typing import Dict, List, Optional

from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine, EventEngine
from vnpy.event import Event

from ..event import APP_NAME, EVENT_TRANSITION_DETECTED
from ..constant import RegimeType

_BG     = "#1e1e2e"
_DARK   = "#181825"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_BLUE   = "#89b4fa"
_GRN    = "#a6e3a1"
_YLW    = "#f9e2af"
_RED    = "#f38ba8"
_MAV    = "#cba6f7"
_HEAD   = "#313244"
_CYN    = "#89dceb"
_ORG    = "#fab387"

_REGIME_COLORS: dict[str, str] = {
    RegimeType.BULL_QUIET.value:    _GRN,
    RegimeType.BULL_VOLATILE.value: _YLW,
    RegimeType.BEAR_QUIET.value:    _BLUE,
    RegimeType.BEAR_VOLATILE.value: _RED,
    RegimeType.SIDEWAYS.value:      _MAV,
    RegimeType.CRISIS.value:        _RED,
    RegimeType.UNKNOWN.value:       _MUT,
}


# ── 转移总览卡片 ──────────────────────────────────────────────────────

class _OverviewCard(QtWidgets.QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(90)
        self.setStyleSheet(
            f"background:{_HEAD};border-radius:6px;border:1px solid {_BORDER};")
        hb = QtWidgets.QHBoxLayout(self)
        hb.setContentsMargins(16, 10, 16, 10)
        hb.setSpacing(28)
        self._fields: dict[str, QtWidgets.QLabel] = {}
        defs = [
            ("t_prob",   "转移概率",    _ORG),
            ("t_conf",   "置信度",      _CYN),
            ("regime",   "当前 Regime", _GRN),
            ("is_trans", "转移中",      _RED),
            ("events",   "确认事件",    _MAV),
        ]
        for key, title, color in defs:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(2)
            t = QtWidgets.QLabel(title)
            t.setStyleSheet(
                f"color:{_MUT};font-size:10px;border:none;background:transparent;")
            v = QtWidgets.QLabel("--")
            v.setStyleSheet(
                f"color:{color};font-size:18px;font-weight:bold;"
                f"border:none;background:transparent;")
            col.addWidget(t); col.addWidget(v)
            hb.addLayout(col)
            self._fields[key] = v
        hb.addStretch()

    def update_state(self, state) -> None:
        self._fields["t_prob"].setText(f"{state.transition_prob:.1%}")
        self._fields["t_conf"].setText(f"{state.transition_confidence:.1%}")
        rc = _REGIME_COLORS.get(state.current_regime.value, _MUT)
        self._fields["regime"].setStyleSheet(
            f"color:{rc};font-size:18px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._fields["regime"].setText(state.current_regime.value)
        trans_color = _RED if state.is_transitioning else _MUT
        self._fields["is_trans"].setText(
            "是" if state.is_transitioning else "否")
        self._fields["is_trans"].setStyleSheet(
            f"color:{trans_color};font-size:18px;font-weight:bold;"
            f"border:none;background:transparent;")


# ���� �ź�ǿ���Ǳ��� ��������������������������������������������������������������������������������������������������������

class _SignalGauge(QtWidgets.QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"background:{_HEAD};border-radius:6px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(self)
        vb.setContentsMargins(14, 10, 14, 10)
        vb.setSpacing(10)
        title = QtWidgets.QLabel("����ź�ǿ��")
        title.setStyleSheet(
            f"color:{_CYN};font-size:11px;font-weight:bold;"
            f"border:none;background:transparent;")
        vb.addWidget(title)
        self._rows: dict[str, tuple] = {}
        defs = [
            ("regime",     "Regime Shift",     _ORG),
            ("volatility", "Volatility Break", _YLW),
            ("liquidity",  "Liquidity Regime", _BLUE),
        ]
        for key, label, color in defs:
            row = QtWidgets.QHBoxLayout()
            lbl = QtWidgets.QLabel(label)
            lbl.setFixedWidth(130)
            lbl.setStyleSheet(
                f"color:{_MUT};font-size:10px;border:none;background:transparent;")
            bar = QtWidgets.QProgressBar()
            bar.setRange(0, 1000); bar.setValue(0)
            bar.setTextVisible(False); bar.setFixedHeight(10)
            bar.setStyleSheet(
                f"QProgressBar{{background:{_BORDER};border:none;border-radius:4px;}}"
                f"QProgressBar::chunk{{background:{color};border-radius:4px;}}")
            val_lbl = QtWidgets.QLabel("0.000")
            val_lbl.setFixedWidth(44)
            val_lbl.setStyleSheet(
                f"color:{color};font-size:10px;font-weight:bold;"
                f"border:none;background:transparent;")
            trig_lbl = QtWidgets.QLabel("��")
            trig_lbl.setFixedWidth(14)
            trig_lbl.setStyleSheet(
                f"color:{_MUT};font-size:12px;border:none;background:transparent;")
            row.addWidget(lbl); row.addWidget(bar)
            row.addWidget(val_lbl); row.addWidget(trig_lbl)
            vb.addLayout(row)
            self._rows[key] = (bar, val_lbl, trig_lbl, color)
        vb.addStretch()

    def update_state(self, state) -> None:
        for key, sig in [("regime", state.regime_signal),
                          ("volatility", state.volatility_signal),
                          ("liquidity", state.liquidity_signal)]:
            bar, val_lbl, trig_lbl, color = self._rows[key]
            bar.setValue(int(sig.strength * 1000))
            val_lbl.setText(f"{sig.strength:.3f}")
            if sig.is_triggered:
                trig_lbl.setText("��")
                trig_lbl.setStyleSheet(
                    f"color:{_RED};font-size:12px;border:none;background:transparent;")
            else:
                trig_lbl.setText("��")
                trig_lbl.setStyleSheet(
                    f"color:{_MUT};font-size:12px;border:none;background:transparent;")


# ���� Regime ������״ͼ ��������������������������������������������������������������������������������������������������

class _RegimeProbChart(QtWidgets.QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setStyleSheet(
            f"background:{_DARK};border-radius:4px;border:1px solid {_BORDER};")
        self._probs: Dict[str, float] = {}

    def set_probs(self, probs: Dict[str, float]) -> None:
        self._probs = probs
        self.update()

    def paintEvent(self, event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        painter.fillRect(0, 0, W, H, QtGui.QColor(_DARK))
        if not self._probs:
            painter.setPen(QtGui.QPen(QtGui.QColor(_MUT)))
            painter.setFont(QtGui.QFont("sans-serif", 10))
            painter.drawText(12, H // 2, "��������")
            painter.end()
            return
        items = sorted(self._probs.items(), key=lambda x: -x[1])
        n = len(items)
        pl, pr, pt, pb = 120, 60, 12, 12
        bh  = max(14, (H - pt - pb) // n - 4)
        bgap = 4
        painter.setFont(QtGui.QFont("monospace", 9))
        for i, (regime, prob) in enumerate(items):
            y     = pt + i * (bh + bgap)
            bw    = int((W - pl - pr) * prob)
            color = _REGIME_COLORS.get(regime, _MUT)
            painter.fillRect(pl, y, W - pl - pr, bh, QtGui.QColor(_HEAD))
            if bw > 0:
                painter.fillRect(pl, y, bw, bh, QtGui.QColor(color))
            painter.setPen(QtGui.QPen(QtGui.QColor(_MUT)))
            painter.drawText(4, y + bh - 2, regime)
            painter.setPen(QtGui.QPen(QtGui.QColor(color)))
            painter.drawText(pl + bw + 4, y + bh - 2, f"{prob:.1%}")
        painter.end()


# ���� ת�Ƹ���ʱ���� ��������������������������������������������������������������������������������������������������������

class _TransitionTimeline(QtWidgets.QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setStyleSheet(
            f"background:{_DARK};border-radius:4px;border:1px solid {_BORDER};")
        self._probs: List[float] = []

    def append_prob(self, prob: float) -> None:
        self._probs.append(prob)
        if len(self._probs) > 200:
            self._probs = self._probs[-200:]
        self.update()

    def paintEvent(self, event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        pl, pr, pt, pb = 32, 8, 6, 18
        dw, dh = W - pl - pr, H - pt - pb
        painter.fillRect(0, 0, W, H, QtGui.QColor(_DARK))
        thresh_y = pt + int(dh * (1 - 0.4))
        tpen = QtGui.QPen(QtGui.QColor(_ORG))
        tpen.setStyle(QtCore.Qt.PenStyle.DashLine)
        painter.setPen(tpen)
        painter.drawLine(pl, thresh_y, W - pr, thresh_y)
        painter.setPen(QtGui.QPen(QtGui.QColor(_MUT)))
        painter.setFont(QtGui.QFont("monospace", 7))
        painter.drawText(2, thresh_y + 4, "0.4")
        painter.drawText(2, pt + 8, "1.0")
        painter.drawText(2, H - pb + 4, "0.0")
        if len(self._probs) < 2:
            painter.end()
            return
        n   = len(self._probs)
        pen = QtGui.QPen(QtGui.QColor(_ORG))
        pen.setWidth(2)
        painter.setPen(pen)
        pts = []
        for i, p in enumerate(self._probs):
            x = pl + int(dw * i / (n - 1))
            y = pt + int(dh * (1.0 - max(0.0, min(1.0, p))))
            pts.append(QtCore.QPoint(x, y))
        for i in range(len(pts) - 1):
            painter.drawLine(pts[i], pts[i + 1])
        painter.end()


# ���� ת���¼��б� ������������������������������������������������������������������������������������������������������������

_EVENT_HEADERS = ["ʱ��", "����", "From Regime", "To Regime", "���Ŷ�", "����"]

class _EventTable(QtWidgets.QTableWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(0, len(_EVENT_HEADERS), parent)
        self.setHorizontalHeaderLabels(_EVENT_HEADERS)
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.setMaximumHeight(150)
        self.setStyleSheet(
            f"QTableWidget{{background:{_DARK};color:{_FG};"
            f"gridline-color:{_BORDER};border:none;font-size:11px;}}"
            f"QHeaderView::section{{background:{_HEAD};color:{_MUT};"
            f"border:none;padding:4px;font-size:10px;}}"
            f"QTableWidget::item{{padding:4px;}}"
            f"QTableWidget::item:selected{{background:{_HEAD};}}")

    def append_event(self, ev) -> None:
        row = self.rowCount()
        self.insertRow(row)
        conf_color = _GRN if ev.confidence >= 0.8 else (
            _YLW if ev.confidence >= 0.6 else _ORG)
        to_color = _REGIME_COLORS.get(ev.to_regime.value, _MUT)
        vals = [
            ev.timestamp.strftime("%H:%M:%S"),
            ev.transition_type.value,
            ev.from_regime.value,
            ev.to_regime.value,
            f"{ev.confidence:.1%}",
            ev.description,
        ]
        colors = [_MUT, _MAV, _FG, to_color, conf_color, _MUT]
        for col, (val, color) in enumerate(zip(vals, colors)):
            item = QtWidgets.QTableWidgetItem(val)
            item.setForeground(QtGui.QColor(color))
            self.setItem(row, col, item)
        self.scrollToBottom()


# ���� TransitionTab ����� ��������������������������������������������������������������������������������������������

class TransitionTab(QtWidgets.QWidget):
    """
    ״̬ת�� Tab ����塣
    ���� EVENT_TRANSITION_DETECTED��ʵʱ���������������
    """

    def __init__(self, main_engine: MainEngine,
                 event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine       = main_engine.get_engine(APP_NAME)
        self._init_ui()
        self._register_events()

    def _init_ui(self) -> None:
        self.setStyleSheet(f"background:{_DARK};")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self._overview = _OverviewCard()
        root.addWidget(self._overview)

        mid = QtWidgets.QHBoxLayout()
        mid.setSpacing(8)

        self._signal_gauge = _SignalGauge()
        self._signal_gauge.setFixedWidth(300)
        mid.addWidget(self._signal_gauge)

        prob_panel = QtWidgets.QVBoxLayout()
        prob_title = QtWidgets.QLabel("Regime ���ʷֲ�")
        prob_title.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        self._prob_chart = _RegimeProbChart()
        prob_panel.addWidget(prob_title)
        prob_panel.addWidget(self._prob_chart, stretch=1)
        mid.addLayout(prob_panel, stretch=1)

        root.addLayout(mid, stretch=1)

        tl_title = QtWidgets.QLabel("ת�Ƹ���ʱ����  Transition Probability Timeline")
        tl_title.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        root.addWidget(tl_title)

        self._timeline = _TransitionTimeline()
        root.addWidget(self._timeline)

        ctrl = QtWidgets.QHBoxLayout()
        btn_detect = QtWidgets.QPushButton("?  ִ��ת�Ƽ��")
        btn_detect.setStyleSheet(
            f"QPushButton{{background:{_CYN};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:7px 14px;font-size:11px;}}"
            f"QPushButton:hover{{background:#74c7ec;}}")
        btn_detect.clicked.connect(self._on_detect)

        self._ts_label = QtWidgets.QLabel("����⣺--")
        self._ts_label.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")

        ctrl.addWidget(btn_detect)
        ctrl.addStretch()
        ctrl.addWidget(self._ts_label)
        root.addLayout(ctrl)

        ev_title = QtWidgets.QLabel("��ȷ��ת���¼�")
        ev_title.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        root.addWidget(ev_title)

        self._event_table = _EventTable()
        root.addWidget(self._event_table)

    def _register_events(self) -> None:
        self._event_engine.register(
            EVENT_TRANSITION_DETECTED, self._on_transition_event)

    def _on_transition_event(self, event: Event) -> None:
        state = event.data
        if state is None:
            return
        QtCore.QTimer.singleShot(0, lambda: self._update_display(state))

    def _update_display(self, state) -> None:
        from datetime import datetime as _dt
        self._overview.update_state(state)
        self._signal_gauge.update_state(state)
        self._prob_chart.set_probs(state.regime_probs.probabilities)
        self._timeline.append_prob(state.transition_prob)

        if state.latest_event is not None:
            self._event_table.append_event(state.latest_event)

        if self._engine:
            hist = self._engine.get_transition_history()
            if hist:
                self._overview._fields["events"].setText(
                    str(len(hist.events)))

        self._ts_label.setText(
            f"����⣺{_dt.now().strftime('%H:%M:%S')}")

    def _on_detect(self) -> None:
        if self._engine:
            self._engine.detect_transition()

    def closeEvent(self, event) -> None:
        self._event_engine.unregister(
            EVENT_TRANSITION_DETECTED, self._on_transition_event)
        super().closeEvent(event)
