"""
temporal_intelligence_ai/ui/decay_tab.py

Alpha Decay Tab — Alpha 衰减可视化面板（Phase 3）。

布局：
  上方：衰减总览卡片（活跃 Alpha 数 / 平均强度 / 到期数）
  中部：衰减曲线画布（QPainter 绘制，三模式叠加显示）
  下方：Alpha 列表表格（每行一个 Alpha 的实时衰减状态）
"""
from __future__ import annotations

from typing import Dict, List, Optional

from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine, EventEngine
from vnpy.event import Event

from ..event import APP_NAME, EVENT_ALPHA_DECAY_UPDATED
from ..constant import DecayMode
from ..datasource.alpha_loader import AlphaRecord
from ..utils.decay_utils import half_life_to_rate

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

_STRENGTH_COLORS = [
    (0.75, _GRN),
    (0.50, _YLW),
    (0.25, _ORG),
    (0.00, _RED),
]


def _strength_color(v: float) -> str:
    for threshold, color in _STRENGTH_COLORS:
        if v >= threshold:
            return color
    return _RED


# ── 衰减曲线画布 ──────────────────────────────────────────────────────

class _DecayCurveCanvas(QtWidgets.QWidget):
    """衰减曲线绘图区（QPainter 手绘折线）。"""

    _PALETTE = [_GRN, _BLUE, _YLW, _MAV, _ORG, _CYN, _RED, _FG]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setStyleSheet(
            f"background:{_DARK};border-radius:4px;border:1px solid {_BORDER};")
        self._curves: Dict[str, List[float]] = {}

    def set_curves(self, curves: Dict[str, List[float]]) -> None:
        self._curves = curves
        self.update()

    def paintEvent(self, event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        pl, pr, pt, pb = 44, 12, 12, 28
        dw, dh = W - pl - pr, H - pt - pb

        painter.fillRect(0, 0, W, H, QtGui.QColor(_DARK))

        grid_pen = QtGui.QPen(QtGui.QColor(_BORDER))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        for i in range(5):
            y = pt + int(dh * i / 4)
            painter.drawLine(pl, y, W - pr, y)

        label_pen = QtGui.QPen(QtGui.QColor(_MUT))
        painter.setPen(label_pen)
        painter.setFont(QtGui.QFont("monospace", 8))
        for i in range(5):
            val = 1.0 - i * 0.25
            y   = pt + int(dh * i / 4)
            painter.drawText(2, y + 4, f"{val:.2f}")

        hl_y = pt + int(dh * 0.5)
        hl_pen = QtGui.QPen(QtGui.QColor(_MUT))
        hl_pen.setStyle(QtCore.Qt.PenStyle.DashLine)
        painter.setPen(hl_pen)
        painter.drawLine(pl, hl_y, W - pr, hl_y)
        painter.setPen(label_pen)
        painter.drawText(W - pr - 28, hl_y - 2, "T½")

        exp_y = pt + int(dh * 0.95)
        exp_pen = QtGui.QPen(QtGui.QColor(_RED))
        exp_pen.setStyle(QtCore.Qt.PenStyle.DotLine)
        painter.setPen(exp_pen)
        painter.drawLine(pl, exp_y, W - pr, exp_y)

        if not self._curves:
            painter.setPen(QtGui.QPen(QtGui.QColor(_MUT)))
            painter.setFont(QtGui.QFont("sans-serif", 11))
            painter.drawText(pl + 10, H // 2,
                             "暂无曲线 — 请注册 Alpha 并执行衰减计算")
            painter.end()
            return

        for idx, (alpha_id, strengths) in enumerate(self._curves.items()):
            if not strengths:
                continue
            color = self._PALETTE[idx % len(self._PALETTE)]
            pen   = QtGui.QPen(QtGui.QColor(color))
            pen.setWidth(2)
            painter.setPen(pen)
            n   = len(strengths)
            pts = []
            for i, s in enumerate(strengths):
                x = pl + int(dw * i / max(n - 1, 1))
                y = pt + int(dh * (1.0 - max(0.0, min(1.0, s))))
                pts.append(QtCore.QPoint(x, y))
            for i in range(len(pts) - 1):
                painter.drawLine(pts[i], pts[i + 1])
            if pts:
                short_id = (alpha_id[:12] + "..") if len(alpha_id) > 14 else alpha_id
                painter.setFont(QtGui.QFont("monospace", 8))
                painter.drawText(pts[0].x() + 2, pts[0].y() - 4, short_id)

        painter.setPen(label_pen)
        painter.setFont(QtGui.QFont("monospace", 8))
        painter.drawText(pl, H - 4, "now")
        painter.drawText(W - pr - 16, H - 4, "+end")
        painter.end()


# ���� ������Ƭ ��������������������������������������������������������������������������������������������������������������������

class _OverviewCard(QtWidgets.QWidget):
    """����˥��������Ƭ��"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setStyleSheet(
            f"background:{_HEAD};border-radius:6px;border:1px solid {_BORDER};")
        hb = QtWidgets.QHBoxLayout(self)
        hb.setContentsMargins(16, 10, 16, 10)
        hb.setSpacing(32)
        self._fields: dict[str, QtWidgets.QLabel] = {}
        defs = [
            ("active",  "��Ծ Alpha", _GRN),
            ("avg",     "ƽ��ǿ��",   _CYN),
            ("min",     "���ǿ��",   _ORG),
            ("expired", "�ѵ���",     _RED),
        ]
        for key, title, color in defs:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(2)
            t_lbl = QtWidgets.QLabel(title)
            t_lbl.setStyleSheet(
                f"color:{_MUT};font-size:10px;border:none;background:transparent;")
            v_lbl = QtWidgets.QLabel("--")
            v_lbl.setStyleSheet(
                f"color:{color};font-size:20px;font-weight:bold;"
                f"border:none;background:transparent;")
            col.addWidget(t_lbl)
            col.addWidget(v_lbl)
            hb.addLayout(col)
            self._fields[key] = v_lbl
        hb.addStretch()

    def update_summary(self, summary: dict) -> None:
        self._fields["active"].setText(str(summary.get("active_alphas", 0)))
        avg = summary.get("avg_strength", 0.0)
        mn  = summary.get("min_strength", 0.0)
        self._fields["avg"].setText(f"{avg:.1%}")
        self._fields["avg"].setStyleSheet(
            f"color:{_strength_color(avg)};font-size:20px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._fields["min"].setText(f"{mn:.1%}")
        self._fields["min"].setStyleSheet(
            f"color:{_strength_color(mn)};font-size:20px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._fields["expired"].setText(str(summary.get("expired_count", 0)))


# ���� Alpha ע��Ի��� ����������������������������������������������������������������������������������������������������

class _RegisterDialog(QtWidgets.QDialog):
    """����ע�� Alpha �źŶԻ���"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ע�� Alpha �ź�")
        self.setModal(True)
        self.setStyleSheet(
            f"background:{_DARK};color:{_FG};"
            f"QLabel{{border:none;background:transparent;}}")
        self.setFixedSize(380, 240)
        form = QtWidgets.QFormLayout(self)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)
        self._id_edit  = QtWidgets.QLineEdit()
        self._hl_spin  = QtWidgets.QDoubleSpinBox()
        self._hl_spin.setRange(1.0, 500.0)
        self._hl_spin.setValue(20.0)
        self._hl_spin.setSuffix("  bars")
        self._bar_spin = QtWidgets.QSpinBox()
        self._bar_spin.setRange(0, 100000)
        self._bar_spin.setValue(0)
        for w in (self._id_edit, self._hl_spin, self._bar_spin):
            w.setStyleSheet(
                f"background:{_HEAD};color:{_FG};"
                f"border:1px solid {_BORDER};border-radius:3px;padding:4px;")
        form.addRow("Alpha ID", self._id_edit)
        form.addRow("��˥�� (bars)", self._hl_spin)
        form.addRow("���� Bar", self._bar_spin)
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        btns.setStyleSheet(
            f"QPushButton{{background:{_CYN};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:6px 16px;}}"
            f"QPushButton:hover{{background:#74c7ec;}}")
        form.addRow(btns)

    def get_record(self) -> Optional[AlphaRecord]:
        alpha_id = self._id_edit.text().strip()
        if not alpha_id:
            return None
        rate = half_life_to_rate(self._hl_spin.value())
        return AlphaRecord(
            alpha_id        = alpha_id,
            created_bar     = self._bar_spin.value(),
            base_decay_rate = rate,
        )


# ���� Alpha �б����� ��������������������������������������������������������������������������������������������������������

_TABLE_HEADERS = [
    "Alpha ID", "ģʽ", "�ۺ�ǿ��", "ָ��ǿ��",
    "Regimeǿ��", "������ǿ��", "��˥��", "Age(bars)",
    "Regime", "����", "����"
]


class _AlphaTable(QtWidgets.QTableWidget):
    """Alpha ˥��״̬ʵʱ����"""

    def __init__(self, parent=None) -> None:
        super().__init__(0, len(_TABLE_HEADERS), parent)
        self.setHorizontalHeaderLabels(_TABLE_HEADERS)
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.setStyleSheet(
            f"QTableWidget{{background:{_DARK};color:{_FG};"
            f"gridline-color:{_BORDER};border:none;font-size:11px;}}"
            f"QHeaderView::section{{background:{_HEAD};color:{_MUT};"
            f"border:none;padding:4px;font-size:10px;}}"
            f"QTableWidget::item{{padding:4px;}}"
            f"QTableWidget::item:selected{{background:{_HEAD};}}")

    def update_state(self, state) -> None:
        alpha_id = state.alpha_id
        m = state.metrics
        row = self._find_row(alpha_id)
        if row < 0:
            row = self.rowCount()
            self.insertRow(row)
        color = _strength_color(m.combined_strength)
        values = [
            alpha_id, state.mode.value,
            f"{m.combined_strength:.3f}", f"{m.exponential_strength:.3f}",
            f"{m.regime_strength:.3f}",   f"{m.volatility_strength:.3f}",
            f"{m.half_life:.1f}",         str(m.age_bars),
            state.regime.value,           state.cycle_phase.value,
            "��" if state.is_expired else "��",
        ]
        for col, val in enumerate(values):
            item = QtWidgets.QTableWidgetItem(val)
            if col == 2:
                item.setForeground(QtGui.QColor(color))
            if state.is_expired:
                item.setForeground(QtGui.QColor(_MUT))
            self.setItem(row, col, item)

    def _find_row(self, alpha_id: str) -> int:
        for r in range(self.rowCount()):
            item = self.item(r, 0)
            if item and item.text() == alpha_id:
                return r
        return -1


# ���� DecayTab ����� ������������������������������������������������������������������������������������������������������

class DecayTab(QtWidgets.QWidget):
    """
    Alpha Decay Tab ����塣

    ���� EVENT_ALPHA_DECAY_UPDATED��ʵʱ�������������
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

        curve_title = QtWidgets.QLabel("Alpha ˥������  Decay Curves")
        curve_title.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        root.addWidget(curve_title)

        self._canvas = _DecayCurveCanvas()
        root.addWidget(self._canvas, stretch=1)

        ctrl = QtWidgets.QHBoxLayout()
        mode_label = QtWidgets.QLabel("˥��ģʽ��")
        mode_label.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        self._mode_combo = QtWidgets.QComboBox()
        self._mode_combo.addItems([m.value for m in DecayMode])
        self._mode_combo.setStyleSheet(
            f"QComboBox{{background:{_HEAD};color:{_FG};"
            f"border:1px solid {_BORDER};border-radius:3px;padding:4px;}}"
            f"QComboBox::drop-down{{border:none;}}"
            f"QComboBox QAbstractItemView{{background:{_HEAD};color:{_FG};}}")
        ctrl.addWidget(mode_label)
        ctrl.addWidget(self._mode_combo)
        ctrl.addStretch()

        btn_register = QtWidgets.QPushButton("+ ע�� Alpha")
        btn_register.setStyleSheet(
            f"QPushButton{{background:{_MAV};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:7px 14px;font-size:11px;}}"
            f"QPushButton:hover{{background:#b4befe;}}")
        btn_register.clicked.connect(self._on_register)

        btn_compute = QtWidgets.QPushButton("?  ִ��˥������")
        btn_compute.setStyleSheet(
            f"QPushButton{{background:{_CYN};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:7px 14px;font-size:11px;}}"
            f"QPushButton:hover{{background:#74c7ec;}}")
        btn_compute.clicked.connect(self._on_compute)

        self._ts_label = QtWidgets.QLabel("�����㣺--")
        self._ts_label.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")

        ctrl.addWidget(btn_register)
        ctrl.addWidget(btn_compute)
        ctrl.addWidget(self._ts_label)
        root.addLayout(ctrl)

        table_title = QtWidgets.QLabel("Alpha ˥��״̬��ϸ")
        table_title.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        root.addWidget(table_title)

        self._table = _AlphaTable()
        root.addWidget(self._table, stretch=1)

    def _register_events(self) -> None:
        self._event_engine.register(
            EVENT_ALPHA_DECAY_UPDATED, self._on_decay_event)

    def _on_decay_event(self, event: Event) -> None:
        state = event.data
        if state is None:
            return
        QtCore.QTimer.singleShot(0, lambda: self._update_display(state))

    def _update_display(self, state) -> None:
        from datetime import datetime as _dt
        self._table.update_state(state)
        if self._engine:
            curves_raw = self._engine.get_decay_curves()
            self._canvas.set_curves(
                {aid: c.strengths() for aid, c in curves_raw.items()})
            summary = self._engine.get_summary().get("decay", {})
            self._overview.update_summary(summary)
        self._ts_label.setText(
            f"�����㣺{_dt.now().strftime('%H:%M:%S')}")

    def _on_register(self) -> None:
        dlg = _RegisterDialog(self)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            record = dlg.get_record()
            if record and self._engine:
                self._engine.register_alpha(record)

    def _on_compute(self) -> None:
        if self._engine:
            mode_val = self._mode_combo.currentText()
            try:
                mode = DecayMode(mode_val)
            except ValueError:
                mode = DecayMode.EXPONENTIAL
            self._engine.configure_decay(mode=mode)
            self._engine.compute_decay()

    def closeEvent(self, event) -> None:
        self._event_engine.unregister(
            EVENT_ALPHA_DECAY_UPDATED, self._on_decay_event)
        super().closeEvent(event)
