"""
temporal_intelligence_ai/ui/dependency_tab.py

Time Dependency Tab — 时间依赖可视化面板（Phase 4）。

布局：
  上方：时间维度分解卡片（短/中/长期权重 + 综合记忆强度）
  中部左：自相关柱状图（ACF 图，QPainter 手绘）
  中部右：依赖矩阵热力图
  下方：工具栏 + 互相关摘要表格
"""
from __future__ import annotations

from typing import Dict, List, Optional

from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine, EventEngine
from vnpy.event import Event

from ..event import APP_NAME, EVENT_TEMPORAL_ANALYSIS_COMPLETED
from ..constant import SignalHorizon

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


# ── 时间维度分解卡片 ──────────────────────────────────────────────────

class _HorizonCard(QtWidgets.QWidget):

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
            ("memory",   "综合记忆强度",    _CYN),
            ("dominant", "主导时间维度",    _MAV),
            ("short",    "短期 t-1~5",      _GRN),
            ("mid",      "中期 t-5~20",     _YLW),
            ("long",     "长期 t-20+",      _BLUE),
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
        bars_col = QtWidgets.QVBoxLayout()
        bars_col.setSpacing(4)
        self._bars: dict[str, QtWidgets.QProgressBar] = {}
        for bkey, color, lbl in [
            ("sb", _GRN, "S"), ("mb", _YLW, "M"), ("lb", _BLUE, "L")
        ]:
            row = QtWidgets.QHBoxLayout()
            ll = QtWidgets.QLabel(lbl)
            ll.setFixedWidth(12)
            ll.setStyleSheet(
                f"color:{color};font-size:10px;font-weight:bold;"
                f"border:none;background:transparent;")
            b = QtWidgets.QProgressBar()
            b.setRange(0, 1000); b.setValue(0)
            b.setTextVisible(False); b.setFixedHeight(6)
            b.setStyleSheet(
                f"QProgressBar{{background:{_BORDER};border:none;border-radius:2px;}}"
                f"QProgressBar::chunk{{background:{color};border-radius:2px;}}")
            row.addWidget(ll); row.addWidget(b)
            bars_col.addLayout(row)
            self._bars[bkey] = b
        hb.addLayout(bars_col)

    def update_state(self, state) -> None:
        h = state.horizon_decomp
        self._fields["memory"].setText(f"{state.overall_memory:.1%}")
        self._fields["dominant"].setText(h.dominant_horizon.value)
        self._fields["short"].setText(f"{h.short_term_weight:.1%}")
        self._fields["mid"].setText(f"{h.mid_term_weight:.1%}")
        self._fields["long"].setText(f"{h.long_term_weight:.1%}")
        self._bars["sb"].setValue(int(h.short_term_weight * 1000))
        self._bars["mb"].setValue(int(h.mid_term_weight * 1000))
        self._bars["lb"].setValue(int(h.long_term_weight * 1000))


# ���� ACF ��״ͼ ����������������������������������������������������������������������������������������������������������������

class _AcfChart(QtWidgets.QWidget):
    """����غ��� ACF ��״ͼ��QPainter �ֻ档"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setStyleSheet(
            f"background:{_DARK};border-radius:4px;border:1px solid {_BORDER};")
        self._lags:   List[int]   = []
        self._corrs:  List[float] = []
        self._thresh: float       = 0.2
        self._title:  str         = "ACF"

    def set_data(self, title: str, lags: List[int],
                 corrs: List[float], thresh: float) -> None:
        self._title  = title
        self._lags   = lags
        self._corrs  = corrs
        self._thresh = thresh
        self.update()

    def paintEvent(self, event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        pl, pr, pt, pb = 38, 8, 24, 24
        dw, dh = W - pl - pr, H - pt - pb

        painter.fillRect(0, 0, W, H, QtGui.QColor(_DARK))

        mid_y = pt + dh // 2
        painter.setPen(QtGui.QPen(QtGui.QColor(_BORDER)))
        painter.drawLine(pl, mid_y, W - pr, mid_y)

        thresh_h = int(dh * 0.5 * self._thresh)
        tpen = QtGui.QPen(QtGui.QColor(_RED))
        tpen.setStyle(QtCore.Qt.PenStyle.DashLine)
        painter.setPen(tpen)
        painter.drawLine(pl, mid_y - thresh_h, W - pr, mid_y - thresh_h)
        painter.drawLine(pl, mid_y + thresh_h, W - pr, mid_y + thresh_h)

        painter.setPen(QtGui.QPen(QtGui.QColor(_MUT)))
        painter.setFont(QtGui.QFont("monospace", 7))
        painter.drawText(2, pt + 6, "+1")
        painter.drawText(2, mid_y + 4, " 0")
        painter.drawText(2, H - pb + 4, "-1")

        painter.setPen(QtGui.QPen(QtGui.QColor(_CYN)))
        painter.setFont(QtGui.QFont("sans-serif", 9))
        painter.drawText(pl + 4, pt - 4, self._title)

        if not self._lags:
            painter.setPen(QtGui.QPen(QtGui.QColor(_MUT)))
            painter.drawText(pl + 8, mid_y, "��������")
            painter.end()
            return

        n     = len(self._lags)
        bar_w = max(2, (dw - 4) // n - 1)

        for i, (lag, corr) in enumerate(zip(self._lags, self._corrs)):
            x     = pl + i * (bar_w + 1)
            h_bar = int(abs(corr) * dh * 0.5)
            col   = _GRN if abs(corr) > self._thresh else _MUT
            if corr >= 0:
                painter.fillRect(x, mid_y - h_bar, bar_w, h_bar, QtGui.QColor(col))
            else:
                painter.fillRect(x, mid_y, bar_w, h_bar, QtGui.QColor(col))

        painter.setPen(QtGui.QPen(QtGui.QColor(_MUT)))
        painter.setFont(QtGui.QFont("monospace", 7))
        for i, lag in enumerate(self._lags):
            if lag % 5 == 0:
                x = pl + i * (bar_w + 1)
                painter.drawText(x, H - 2, str(lag))

        painter.end()


# ���� ������������ͼ ��������������������������������������������������������������������������������������������������������

class _MatrixHeatmap(QtWidgets.QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setStyleSheet(
            f"background:{_DARK};border-radius:4px;border:1px solid {_BORDER};")
        self._ids:    List[str]               = []
        self._matrix: Dict[str, Dict[str, float]] = {}

    def set_data(self, ids: List[str], matrix: Dict[str, Dict[str, float]]) -> None:
        self._ids    = ids
        self._matrix = matrix
        self.update()

    def paintEvent(self, event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        painter.fillRect(0, 0, W, H, QtGui.QColor(_DARK))
        if not self._ids:
            painter.setPen(QtGui.QPen(QtGui.QColor(_MUT)))
            painter.setFont(QtGui.QFont("sans-serif", 10))
            painter.drawText(12, H // 2, "�����ź� �� ��ע���źŲ�ִ�з���")
            painter.end()
            return
        n    = len(self._ids)
        pad  = 48
        cw   = max(8, (W - pad) // n)
        ch   = max(8, (H - pad) // n)
        painter.setFont(QtGui.QFont("monospace", 7))
        for i, a in enumerate(self._ids):
            for j, b in enumerate(self._ids):
                x   = pad + j * cw
                y   = pad + i * ch
                val = 1.0 if a == b else self._matrix.get(a, {}).get(b, 0.0)
                iv  = int(max(0.0, min(1.0, abs(val))) * 255)
                r   = iv if val < 0 else 0
                g   = iv if val >= 0 else 0
                bc  = max(0, 100 - iv // 2)
                painter.fillRect(x, y, cw - 1, ch - 1, QtGui.QColor(r, g, bc))
                if cw > 28 and ch > 14:
                    painter.setPen(QtGui.QPen(QtGui.QColor(_FG)))
                    painter.drawText(x + 2, y + ch - 3, f"{val:.2f}")
        painter.setPen(QtGui.QPen(QtGui.QColor(_MUT)))
        for i, sid in enumerate(self._ids):
            short = sid[:6] + ".." if len(sid) > 8 else sid
            painter.drawText(2, pad + i * ch + ch // 2 + 4, short)
            painter.drawText(pad + i * cw + 2, pad - 4, short)
        painter.end()


# ���� �ź�ע��Ի��� ����������������������������������������������������������������������������������������������������������

class _SignalDialog(QtWidgets.QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ע���ź�����")
        self.setModal(True)
        self.setStyleSheet(
            f"background:{_DARK};color:{_FG};"
            f"QLabel{{border:none;background:transparent;}}")
        self.setFixedSize(480, 280)
        form = QtWidgets.QFormLayout(self)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)
        self._id_edit   = QtWidgets.QLineEdit()
        self._data_edit = QtWidgets.QPlainTextEdit()
        self._data_edit.setPlaceholderText(
            "���ŷָ����������У����磺1.0, 1.02, 0.99, 1.05, ...")
        self._data_edit.setFixedHeight(100)
        for w in (self._id_edit, self._data_edit):
            w.setStyleSheet(
                f"background:{_HEAD};color:{_FG};"
                f"border:1px solid {_BORDER};border-radius:3px;padding:4px;")
        form.addRow("Signal ID", self._id_edit)
        form.addRow("��������",  self._data_edit)
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

    def get_signal(self) -> Optional[tuple]:
        sid = self._id_edit.text().strip()
        if not sid:
            return None
        raw = self._data_edit.toPlainText().strip()
        try:
            series = [float(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            return None
        return (sid, series) if len(series) >= 10 else None


# ���� �����ժҪ���� ��������������������������������������������������������������������������������������������������������

_CC_HEADERS = ["Signal A", "Signal B", "����/�ͺ�", "��ֵ���", "����ǿ��"]

class _CrossCorrTable(QtWidgets.QTableWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(0, len(_CC_HEADERS), parent)
        self.setHorizontalHeaderLabels(_CC_HEADERS)
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.setMaximumHeight(140)
        self.setStyleSheet(
            f"QTableWidget{{background:{_DARK};color:{_FG};"
            f"gridline-color:{_BORDER};border:none;font-size:11px;}}"
            f"QHeaderView::section{{background:{_HEAD};color:{_MUT};"
            f"border:none;padding:4px;font-size:10px;}}"
            f"QTableWidget::item{{padding:4px;}}"
            f"QTableWidget::item:selected{{background:{_HEAD};}}")

    def update_results(self, results: list) -> None:
        self.setRowCount(0)
        for cc in results:
            row = self.rowCount()
            self.insertRow(row)
            lead_str   = f"+{cc.lead_lag}" if cc.lead_lag > 0 else str(cc.lead_lag)
            lead_color = _GRN if cc.lead_lag > 0 else (_RED if cc.lead_lag < 0 else _MUT)
            dep_color  = _GRN if cc.dependency_strength > 0.5 else (
                         _YLW if cc.dependency_strength > 0.25 else _MUT)
            vals   = [cc.signal_a, cc.signal_b, lead_str,
                      f"{cc.peak_corr:+.3f}", f"{cc.dependency_strength:.3f}"]
            colors = [_FG, _FG, lead_color, _FG, dep_color]
            for col, (val, col_color) in enumerate(zip(vals, colors)):
                item = QtWidgets.QTableWidgetItem(val)
                item.setForeground(QtGui.QColor(col_color))
                self.setItem(row, col, item)


# ���� DependencyTab ����� ��������������������������������������������������������������������������������������������

class DependencyTab(QtWidgets.QWidget):
    """
    ʱ������ Tab ����塣

    ���� EVENT_TEMPORAL_ANALYSIS_COMPLETED��ʵʱ���������������
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

        self._horizon_card = _HorizonCard()
        root.addWidget(self._horizon_card)

        mid = QtWidgets.QHBoxLayout()
        mid.setSpacing(8)

        acf_panel = QtWidgets.QVBoxLayout()
        acf_title = QtWidgets.QLabel("����غ��� ACF")
        acf_title.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        self._sig_selector = QtWidgets.QComboBox()
        self._sig_selector.setStyleSheet(
            f"QComboBox{{background:{_HEAD};color:{_FG};"
            f"border:1px solid {_BORDER};border-radius:3px;padding:3px;}}"
            f"QComboBox::drop-down{{border:none;}}"
            f"QComboBox QAbstractItemView{{background:{_HEAD};color:{_FG};}}")
        self._sig_selector.currentTextChanged.connect(self._on_signal_selected)
        self._acf_chart = _AcfChart()
        acf_panel.addWidget(acf_title)
        acf_panel.addWidget(self._sig_selector)
        acf_panel.addWidget(self._acf_chart, stretch=1)
        mid.addLayout(acf_panel, stretch=1)

        mat_panel = QtWidgets.QVBoxLayout()
        mat_title = QtWidgets.QLabel("��������  Dependency Matrix")
        mat_title.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        self._matrix_heatmap = _MatrixHeatmap()
        mat_panel.addWidget(mat_title)
        mat_panel.addWidget(self._matrix_heatmap, stretch=1)
        mid.addLayout(mat_panel, stretch=1)

        root.addLayout(mid, stretch=1)

        ctrl = QtWidgets.QHBoxLayout()
        btn_register = QtWidgets.QPushButton("+ ע���ź�")
        btn_register.setStyleSheet(
            f"QPushButton{{background:{_MAV};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:7px 14px;font-size:11px;}}"
            f"QPushButton:hover{{background:#b4befe;}}")
        btn_register.clicked.connect(self._on_register)

        btn_analyze = QtWidgets.QPushButton("?  ִ����������")
        btn_analyze.setStyleSheet(
            f"QPushButton{{background:{_CYN};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:7px 14px;font-size:11px;}}"
            f"QPushButton:hover{{background:#74c7ec;}}")
        btn_analyze.clicked.connect(self._on_analyze)

        self._ts_label = QtWidgets.QLabel("��������--")
        self._ts_label.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")

        ctrl.addWidget(btn_register)
        ctrl.addWidget(btn_analyze)
        ctrl.addStretch()
        ctrl.addWidget(self._ts_label)
        root.addLayout(ctrl)

        cc_title = QtWidgets.QLabel("�����ժҪ  Cross-Correlation Summary")
        cc_title.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        root.addWidget(cc_title)

        self._cc_table = _CrossCorrTable()
        root.addWidget(self._cc_table, stretch=1)

    def _register_events(self) -> None:
        self._event_engine.register(
            EVENT_TEMPORAL_ANALYSIS_COMPLETED, self._on_dep_event)

    def _on_dep_event(self, event: Event) -> None:
        state = event.data
        if state is None:
            return
        QtCore.QTimer.singleShot(0, lambda: self._update_display(state))

    def _update_display(self, state) -> None:
        from datetime import datetime as _dt
        import math
        self._horizon_card.update_state(state)
        ids = state.signal_ids
        self._matrix_heatmap.set_data(ids, state.dep_matrix.matrix)

        current = self._sig_selector.currentText()
        self._sig_selector.blockSignals(True)
        self._sig_selector.clear()
        self._sig_selector.addItems(ids)
        if current in ids:
            self._sig_selector.setCurrentText(current)
        self._sig_selector.blockSignals(False)

        sid = self._sig_selector.currentText()
        self._refresh_acf(state, sid, math)
        self._cc_table.update_results(state.crosscorr_results)
        self._ts_label.setText(
            f"��������{_dt.now().strftime('%H:%M:%S')}")

    def _refresh_acf(self, state, sid: str, math_mod=None) -> None:
        if not sid or sid not in state.autocorr_results:
            return
        import math as _math
        acr    = state.autocorr_results[sid]
        thresh = 1.96 / _math.sqrt(max(1, len(acr.lags)))
        self._acf_chart.set_data(
            title  = f"ACF �� {sid}",
            lags   = [lc.lag for lc in acr.lags],
            corrs  = [lc.correlation for lc in acr.lags],
            thresh = thresh,
        )

    def _on_signal_selected(self, sid: str) -> None:
        if not self._engine:
            return
        dep_state = self._engine.get_dependency_state()
        if dep_state and sid in dep_state.autocorr_results:
            self._refresh_acf(dep_state, sid)

    def _on_register(self) -> None:
        dlg = _SignalDialog(self)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            result = dlg.get_signal()
            if result and self._engine:
                sid, series = result
                self._engine.register_signal(sid, series)

    def _on_analyze(self) -> None:
        if self._engine:
            self._engine.analyze_dependency()

    def closeEvent(self, event) -> None:
        self._event_engine.unregister(
            EVENT_TEMPORAL_ANALYSIS_COMPLETED, self._on_dep_event)
        super().closeEvent(event)
