"""
temporal_intelligence_ai/ui/validation_tab.py  (Phase 6)

Temporal Validation Tab — 时间验证可视化面板。

布局：
  上方：Temporal Health Score 大卡片
  中部左：验证指标仪表盘
  中部右：Health Score 历史折线图
  下方：工具栏 + 验证记录明细表格
"""
from __future__ import annotations

from typing import List, Optional

from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine, EventEngine
from vnpy.event import Event

from ..event import APP_NAME, EVENT_VALIDATION_UPDATED
from ..model.validation_model import ValidationRecord

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


def _health_color(score: float) -> str:
    if score >= 70:
        return _GRN
    if score >= 40:
        return _YLW
    return _RED


# ── Health Score 大卡片 ───────────────────────────────────────────────

class _HealthCard(QtWidgets.QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(110)
        self.setStyleSheet(
            f"background:{_HEAD};border-radius:8px;border:1px solid {_BORDER};")
        hb = QtWidgets.QHBoxLayout(self)
        hb.setContentsMargins(24, 14, 24, 14)
        hb.setSpacing(32)

        left = QtWidgets.QVBoxLayout()
        lbl_title = QtWidgets.QLabel("Temporal Health Score")
        lbl_title.setStyleSheet(
            f"color:{_MUT};font-size:11px;border:none;background:transparent;")
        self._score_lbl = QtWidgets.QLabel("--")
        self._score_lbl.setStyleSheet(
            f"color:{_GRN};font-size:42px;font-weight:bold;"
            f"border:none;background:transparent;")
        left.addWidget(lbl_title)
        left.addWidget(self._score_lbl)
        hb.addLayout(left)

        self._bar = QtWidgets.QProgressBar()
        self._bar.setRange(0, 100); self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedWidth(160); self._bar.setFixedHeight(12)
        self._bar.setStyleSheet(
            f"QProgressBar{{background:{_BORDER};border:none;border-radius:5px;}}"
            f"QProgressBar::chunk{{background:{_GRN};border-radius:5px;}}")
        hb.addWidget(self._bar,
                     alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)
        hb.addStretch()

        self._stats: dict[str, QtWidgets.QLabel] = {}
        right = QtWidgets.QGridLayout()
        right.setSpacing(10)
        for key, title, row, col in [
            ("records",  "总记录",   0, 0),
            ("realized", "已实现",   0, 2),
            ("dir_acc",  "方向准确", 1, 0),
            ("mae",      "MAE",      1, 2),
        ]:
            kt = QtWidgets.QLabel(title)
            kt.setStyleSheet(
                f"color:{_MUT};font-size:10px;border:none;background:transparent;")
            kv = QtWidgets.QLabel("--")
            kv.setStyleSheet(
                f"color:{_FG};font-size:13px;font-weight:bold;"
                f"border:none;background:transparent;")
            right.addWidget(kt, row, col)
            right.addWidget(kv, row, col + 1)
            self._stats[key] = kv
        hb.addLayout(right)

    def update_state(self, state) -> None:
        m     = state.metrics
        score = m.temporal_health
        color = _health_color(score)
        self._score_lbl.setText(f"{score:.1f}")
        self._score_lbl.setStyleSheet(
            f"color:{color};font-size:42px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._bar.setValue(int(score))
        self._bar.setStyleSheet(
            f"QProgressBar{{background:{_BORDER};border:none;border-radius:5px;}}"
            f"QProgressBar::chunk{{background:{color};border-radius:5px;}}")
        self._stats["records"].setText(str(m.n_records))
        self._stats["realized"].setText(str(m.n_realized))
        self._stats["dir_acc"].setText(f"{m.direction_acc:.1%}")
        self._stats["mae"].setText(f"{m.mae:.4f}")


# ���� ָ���Ǳ��� ����������������������������������������������������������������������������������������������������������������

class _MetricsDashboard(QtWidgets.QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"background:{_HEAD};border-radius:6px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(self)
        vb.setContentsMargins(14, 10, 14, 10)
        vb.setSpacing(8)
        title = QtWidgets.QLabel("��ָ֤���Ǳ���")
        title.setStyleSheet(
            f"color:{_CYN};font-size:11px;font-weight:bold;"
            f"border:none;background:transparent;")
        vb.addWidget(title)
        self._rows: dict[str, tuple] = {}
        defs = [
            ("mae",             "MAE",        _ORG, 0.0, 0.5),
            ("rmse",            "RMSE",       _YLW, 0.0, 0.5),
            ("mape",            "MAPE",       _RED, 0.0, 1.0),
            ("dir_acc",         "����׼ȷ��", _GRN, 0.0, 1.0),
            ("decay_align",     "˥�������", _MAV, 0.0, 1.0),
            ("memory_validity", "������Ч��", _CYN, 0.0, 1.0),
        ]
        for key, label, color, lo, hi in defs:
            row = QtWidgets.QHBoxLayout()
            lbl = QtWidgets.QLabel(label)
            lbl.setFixedWidth(90)
            lbl.setStyleSheet(
                f"color:{_MUT};font-size:10px;border:none;background:transparent;")
            bar = QtWidgets.QProgressBar()
            bar.setRange(0, 1000); bar.setValue(0)
            bar.setTextVisible(False); bar.setFixedHeight(8)
            bar.setStyleSheet(
                f"QProgressBar{{background:{_BORDER};border:none;border-radius:3px;}}"
                f"QProgressBar::chunk{{background:{color};border-radius:3px;}}")
            val_lbl = QtWidgets.QLabel("--")
            val_lbl.setFixedWidth(60)
            val_lbl.setStyleSheet(
                f"color:{color};font-size:10px;font-weight:bold;"
                f"border:none;background:transparent;")
            row.addWidget(lbl); row.addWidget(bar); row.addWidget(val_lbl)
            vb.addLayout(row)
            self._rows[key] = (bar, val_lbl, color, lo, hi)
        vb.addStretch()

    def update_state(self, state) -> None:
        m = state.metrics
        def pct(v, lo, hi):
            if hi == lo: return 500
            return int(max(0, min(1000, (v - lo) / (hi - lo) * 1000)))
        for key, val, disp in [
            ("mae",             m.mae,             f"{m.mae:.4f}"),
            ("rmse",            m.rmse,            f"{m.rmse:.4f}"),
            ("mape",            m.mape,            f"{m.mape:.1%}"),
            ("dir_acc",         m.direction_acc,   f"{m.direction_acc:.1%}"),
            ("decay_align",     m.decay_alignment, f"{m.decay_alignment:.1%}"),
            ("memory_validity", m.memory_validity, f"{m.memory_validity:.1%}"),
        ]:
            bar, lbl, color, lo, hi = self._rows[key]
            bar.setValue(pct(val, lo, hi))
            lbl.setText(disp)


# ���� Health Score ��ʷ����ͼ ��������������������������������������������������������������������������������������

class _HealthChart(QtWidgets.QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setStyleSheet(
            f"background:{_DARK};border-radius:4px;border:1px solid {_BORDER};")
        self._scores: List[float] = []

    def append_score(self, score: float) -> None:
        self._scores.append(score)
        if len(self._scores) > 200:
            self._scores = self._scores[-200:]
        self.update()

    def paintEvent(self, event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        pl, pr, pt, pb = 36, 8, 16, 22
        dw, dh = W - pl - pr, H - pt - pb
        painter.fillRect(0, 0, W, H, QtGui.QColor(_DARK))
        for thresh, color in [(70, _GRN), (40, _YLW)]:
            ty  = pt + int(dh * (1 - thresh / 100))
            tpen = QtGui.QPen(QtGui.QColor(color))
            tpen.setStyle(QtCore.Qt.PenStyle.DashLine)
            painter.setPen(tpen)
            painter.drawLine(pl, ty, W - pr, ty)
            painter.setPen(QtGui.QPen(QtGui.QColor(color)))
            painter.setFont(QtGui.QFont("monospace", 7))
            painter.drawText(2, ty + 4, str(thresh))
        painter.setPen(QtGui.QPen(QtGui.QColor(_MUT)))
        painter.setFont(QtGui.QFont("monospace", 7))
        painter.drawText(2, pt + 8, "100")
        painter.drawText(2, H - pb + 4, "0")
        painter.setPen(QtGui.QPen(QtGui.QColor(_CYN)))
        painter.setFont(QtGui.QFont("sans-serif", 9))
        painter.drawText(pl + 4, pt - 2, "Temporal Health Score ��ʷ")
        if len(self._scores) < 2:
            painter.end()
            return
        n = len(self._scores)
        pts = []
        for i, s in enumerate(self._scores):
            x = pl + int(dw * i / (n - 1))
            y = pt + int(dh * (1 - max(0, min(100, s)) / 100))
            pts.append(QtCore.QPoint(x, y))
        for i in range(len(pts) - 1):
            seg = (self._scores[i] + self._scores[i + 1]) / 2
            pen = QtGui.QPen(QtGui.QColor(_health_color(seg)))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(pts[i], pts[i + 1])
        painter.end()


# ���� Ԥ���¼�Ի��� ��������������������������������������������������������������������������������������������������������

class _PredictionDialog(QtWidgets.QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("�ύԤ���¼")
        self.setModal(True)
        self.setStyleSheet(
            f"background:{_DARK};color:{_FG};"
            f"QLabel{{border:none;background:transparent;}}")
        self.setFixedSize(400, 260)
        form = QtWidgets.QFormLayout(self)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)
        self._id_edit     = QtWidgets.QLineEdit()
        self._type_edit   = QtWidgets.QLineEdit()
        self._type_edit.setPlaceholderText("cycle / decay / dependency ...")
        self._pred_spin   = QtWidgets.QDoubleSpinBox()
        self._pred_spin.setRange(-100.0, 100.0)
        self._pred_spin.setDecimals(4)
        self._pred_spin.setValue(0.0)
        self._horizon_spin = QtWidgets.QSpinBox()
        self._horizon_spin.setRange(1, 500)
        self._horizon_spin.setValue(5)
        for w in (self._id_edit, self._type_edit,
                  self._pred_spin, self._horizon_spin):
            w.setStyleSheet(
                f"background:{_HEAD};color:{_FG};"
                f"border:1px solid {_BORDER};border-radius:3px;padding:4px;")
        form.addRow("Record ID",      self._id_edit)
        form.addRow("Signal Type",    self._type_edit)
        form.addRow("Ԥ��ֵ",          self._pred_spin)
        form.addRow("Horizon (bars)", self._horizon_spin)
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

    def get_record(self) -> Optional[ValidationRecord]:
        rid = self._id_edit.text().strip()
        if not rid:
            return None
        return ValidationRecord(
            record_id    = rid,
            signal_type  = self._type_edit.text().strip() or "manual",
            predicted    = self._pred_spin.value(),
            horizon_bars = self._horizon_spin.value(),
        )


# ���� ��֤��¼���� ������������������������������������������������������������������������������������������������������������

_REC_HEADERS = ["ID", "����", "Ԥ��ֵ", "ʵ��ֵ", "���", "����", "Horizon", "��ʵ��"]

class _RecordTable(QtWidgets.QTableWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(0, len(_REC_HEADERS), parent)
        self.setHorizontalHeaderLabels(_REC_HEADERS)
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.setMaximumHeight(180)
        self.setStyleSheet(
            f"QTableWidget{{background:{_DARK};color:{_FG};"
            f"gridline-color:{_BORDER};border:none;font-size:11px;}}"
            f"QHeaderView::section{{background:{_HEAD};color:{_MUT};"
            f"border:none;padding:4px;font-size:10px;}}"
            f"QTableWidget::item{{padding:4px;}}"
            f"QTableWidget::item:selected{{background:{_HEAD};}}")

    def refresh(self, records: list) -> None:
        self.setRowCount(0)
        for rec in records[-50:]:
            row = self.rowCount()
            self.insertRow(row)
            is_real = rec.is_realized and rec.realized is not None
            err_str = f"{rec.realized - rec.predicted:+.4f}" if is_real else "--"
            if is_real:
                dir_hit = (rec.predicted >= 0) == (rec.realized >= 0)
                dir_str = "?" if dir_hit else "?"
                dir_col = _GRN if dir_hit else _RED
            else:
                dir_str, dir_col = "--", _MUT
            real_str = f"{rec.realized:.4f}" if is_real else "--"
            vals   = [rec.record_id, rec.signal_type,
                      f"{rec.predicted:.4f}", real_str,
                      err_str, dir_str, str(rec.horizon_bars),
                      "��" if rec.is_realized else "��"]
            colors = [_FG, _MUT, _FG, _FG, _ORG, dir_col, _MUT,
                      _GRN if rec.is_realized else _MUT]
            for col, (val, color) in enumerate(zip(vals, colors)):
                item = QtWidgets.QTableWidgetItem(val)
                item.setForeground(QtGui.QColor(color))
                self.setItem(row, col, item)


# ���� ValidationTab ����� ��������������������������������������������������������������������������������������������

class ValidationTab(QtWidgets.QWidget):
    """
    ʱ����֤ Tab ����塣
    ���� EVENT_VALIDATION_UPDATED��ʵʱ���������������
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

        self._health_card = _HealthCard()
        root.addWidget(self._health_card)

        mid = QtWidgets.QHBoxLayout()
        mid.setSpacing(8)

        self._metrics_dash = _MetricsDashboard()
        self._metrics_dash.setFixedWidth(320)
        mid.addWidget(self._metrics_dash)

        chart_panel = QtWidgets.QVBoxLayout()
        chart_title = QtWidgets.QLabel("Health Score ��ʷ")
        chart_title.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        self._health_chart = _HealthChart()
        chart_panel.addWidget(chart_title)
        chart_panel.addWidget(self._health_chart, stretch=1)
        mid.addLayout(chart_panel, stretch=1)
        root.addLayout(mid, stretch=1)

        ctrl = QtWidgets.QHBoxLayout()
        btn_submit = QtWidgets.QPushButton("+ �ύԤ��")
        btn_submit.setStyleSheet(
            f"QPushButton{{background:{_MAV};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:7px 14px;font-size:11px;}}"
            f"QPushButton:hover{{background:#b4befe;}}")
        btn_submit.clicked.connect(self._on_submit)

        btn_validate = QtWidgets.QPushButton("?  ִ����֤����")
        btn_validate.setStyleSheet(
            f"QPushButton{{background:{_CYN};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:7px 14px;font-size:11px;}}"
            f"QPushButton:hover{{background:#74c7ec;}}")
        btn_validate.clicked.connect(self._on_validate)

        self._ts_label = QtWidgets.QLabel("�����֤��--")
        self._ts_label.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")

        ctrl.addWidget(btn_submit)
        ctrl.addWidget(btn_validate)
        ctrl.addStretch()
        ctrl.addWidget(self._ts_label)
        root.addLayout(ctrl)

        rec_title = QtWidgets.QLabel("��֤��¼��ϸ����� 50 ����")
        rec_title.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        root.addWidget(rec_title)

        self._record_table = _RecordTable()
        root.addWidget(self._record_table, stretch=1)

    def _register_events(self) -> None:
        self._event_engine.register(
            EVENT_VALIDATION_UPDATED, self._on_validation_event)

    def _on_validation_event(self, event: Event) -> None:
        state = event.data
        if state is None:
            return
        QtCore.QTimer.singleShot(0, lambda: self._update_display(state))

    def _update_display(self, state) -> None:
        from datetime import datetime as _dt
        self._health_card.update_state(state)
        self._metrics_dash.update_state(state)
        self._health_chart.append_score(state.metrics.temporal_health)
        if self._engine:
            records = self._engine.get_validation_records()
            self._record_table.refresh(records)
        self._ts_label.setText(
            f"�����֤��{_dt.now().strftime('%H:%M:%S')}")

    def _on_submit(self) -> None:
        dlg = _PredictionDialog(self)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            rec = dlg.get_record()
            if rec and self._engine:
                self._engine.submit_prediction(rec)

    def _on_validate(self) -> None:
        if self._engine:
            self._engine.run_validation()

    def closeEvent(self, event) -> None:
        self._event_engine.unregister(
            EVENT_VALIDATION_UPDATED, self._on_validation_event)
        super().closeEvent(event)
