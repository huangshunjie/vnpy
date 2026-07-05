"""
data_intelligence_ai/ui/quality_tab.py  (Phase 3)

QualityTab — 数据质量可视化面板。
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..constant import QualityStatus

_BG = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"; _FG = "#cdd6f4"
_MUT = "#6c7086"; _BLUE = "#89b4fa"; _GRN = "#a6e3a1"; _YLW = "#f9e2af"
_RED = "#f38ba8"; _MAV = "#cba6f7"; _HEAD = "#313244"; _CYN = "#89dceb"
_TEA = "#94e2d5"
_IS = ("QDoubleSpinBox,QSpinBox,QComboBox,QLineEdit{background:#313244;color:#cdd6f4;"
       "border:1px solid #45475a;border-radius:3px;padding:3px 6px;font-size:11px;}"
       "QComboBox::drop-down{border:none;}")
_LLBL = "color:#6c7086;font-size:11px;border:none;background:transparent;"
_TBL  = ("QTableWidget{background:#181825;color:#cdd6f4;border:1px solid #45475a;"
         "gridline-color:#45475a;font-size:11px;}"
         "QTableWidget::item{padding:3px 6px;}"
         "QTableWidget::item:alternate{background:#1e1e2e;}"
         "QTableWidget::item:selected{background:#45475a;}"
         "QHeaderView::section{background:#313244;color:#6c7086;border:none;"
         "border-bottom:1px solid #45475a;padding:4px 6px;font-size:10px;}")
_STATUS_COLOR = {
    QualityStatus.CLEAN:        _GRN,
    QualityStatus.MISSING:      _RED,
    QualityStatus.OUTLIER:      _YLW,
    QualityStatus.DELAYED:      _MAV,
    QualityStatus.INCONSISTENT: _CYN,
    QualityStatus.UNKNOWN:      _MUT,
}


def _lbl(t, s=""):
    w = QtWidgets.QLabel(t); w.setStyleSheet(s); return w

def _sep():
    s = QtWidgets.QFrame()
    s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    s.setStyleSheet("border:none;border-top:1px solid #45475a;background:transparent;")
    return s


class QualityTab(QtWidgets.QWidget):
    """数据质量可视化面板（Phase 3）。"""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine):
        self._engine = engine

    def _init_ui(self):
        self.setStyleSheet(f"background:{_BG};color:{_FG};")
        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(10, 10, 10, 10); h.setSpacing(10)
        h.addWidget(self._build_left(), stretch=0)
        h.addWidget(self._build_right(), stretch=1)

    def _build_left(self):
        panel = QtWidgets.QWidget(); panel.setFixedWidth(230)
        panel.setStyleSheet(
            f"background:{_DARK};border-radius:6px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(12, 14, 12, 14); vb.setSpacing(10)
        vb.addWidget(_lbl("数据质量控制",
                          f"color:{_YLW};font-weight:bold;font-size:12px;border:none;"))
        vb.addWidget(_sep())
        fm = QtWidgets.QFormLayout()
        fm.setContentsMargins(0, 0, 0, 0); fm.setVerticalSpacing(8)
        fm.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._feat_ed = QtWidgets.QLineEdit("close_ret")
        self._feat_ed.setStyleSheet(_IS)
        fm.addRow(_lbl("特征名:", _LLBL), self._feat_ed)
        self._sym_ed = QtWidgets.QLineEdit("BTCUSDT")
        self._sym_ed.setStyleSheet(_IS)
        fm.addRow(_lbl("标的:", _LLBL), self._sym_ed)
        self._val_sp = QtWidgets.QDoubleSpinBox()
        self._val_sp.setRange(-1e6, 1e6); self._val_sp.setValue(0.012)
        self._val_sp.setDecimals(6); self._val_sp.setStyleSheet(_IS)
        fm.addRow(_lbl("特征值:", _LLBL), self._val_sp)
        self._z_sp = QtWidgets.QDoubleSpinBox()
        self._z_sp.setRange(1.0, 10.0); self._z_sp.setValue(3.5)
        self._z_sp.setSingleStep(0.5); self._z_sp.setStyleSheet(_IS)
        fm.addRow(_lbl("Z阈值:", _LLBL), self._z_sp)
        vb.addLayout(fm); vb.addWidget(_sep())
        vb.addWidget(_lbl("漂移检测",
                          f"color:{_MUT};font-size:10px;border:none;"))
        fm2 = QtWidgets.QFormLayout()
        fm2.setContentsMargins(0, 0, 0, 0); fm2.setVerticalSpacing(6)
        fm2.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._drift_thresh = QtWidgets.QDoubleSpinBox()
        self._drift_thresh.setRange(0.05, 1.0); self._drift_thresh.setValue(0.30)
        self._drift_thresh.setSingleStep(0.05); self._drift_thresh.setStyleSheet(_IS)
        fm2.addRow(_lbl("漂移阈值:", _LLBL), self._drift_thresh)
        self._sim_n = QtWidgets.QSpinBox()
        self._sim_n.setRange(10, 200); self._sim_n.setValue(30)
        self._sim_n.setStyleSheet(_IS)
        fm2.addRow(_lbl("模拟样本:", _LLBL), self._sim_n)
        vb.addLayout(fm2); vb.addStretch()
        btn = QtWidgets.QPushButton(">> 执行质量检查")
        btn.setStyleSheet(
            f"QPushButton{{background:{_YLW};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:8px;font-size:12px;}}"
            f"QPushButton:hover{{background:#f9e2cf;}}")
        btn.clicked.connect(self._on_check); vb.addWidget(btn)
        btn2 = QtWidgets.QPushButton("模拟漂移检测")
        btn2.setStyleSheet(
            f"QPushButton{{background:transparent;color:{_MUT};"
            f"border:1px solid {_BORDER};border-radius:4px;"
            f"padding:6px;font-size:11px;}}"
            f"QPushButton:hover{{background:{_HEAD};}}")
        btn2.clicked.connect(self._on_simulate_drift); vb.addWidget(btn2)
        return panel

    def _build_right(self):
        panel = QtWidgets.QWidget(); panel.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(8)
        vb.addWidget(self._build_kpi_bar())
        vb.addWidget(self._build_report_table())
        vb.addWidget(self._build_drift_table())
        return panel

    def _build_kpi_bar(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(16, 10, 16, 10); h.setSpacing(18)
        self._kpi: dict = {}
        for key, txt, color in [
            ("checked",  "Total Checked", _FG),
            ("clean_pct","Clean %",       _GRN),
            ("avg_score","Avg Score",     _YLW),
            ("blockers", "Blockers",      _RED),
            ("issues",   "Total Issues",  _MAV),
            ("drifted",  "Drifted",       _CYN),
        ]:
            cell = QtWidgets.QWidget()
            cell.setStyleSheet("background:transparent;border:none;")
            cv = QtWidgets.QVBoxLayout(cell)
            cv.setContentsMargins(0, 0, 0, 0); cv.setSpacing(2)
            lk = QtWidgets.QLabel(txt)
            lk.setStyleSheet(
                f"color:{_MUT};font-size:9px;border:none;background:transparent;")
            lk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel("--")
            lv.setStyleSheet(
                f"color:{color};font-size:13px;font-weight:bold;"
                f"border:none;background:transparent;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lk); cv.addWidget(lv)
            self._kpi[key] = lv; h.addWidget(cell)
        h.addStretch(); return w

    def _build_report_table(self):
        w = QtWidgets.QWidget(); w.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(4)
        vb.addWidget(_lbl("Quality Reports",
                          f"color:{_YLW};font-size:11px;font-weight:bold;border:none;"))
        cols = ["Feature", "Symbol", "Status", "Score", "Issues", "Blocker", "Time"]
        self._tbl = QtWidgets.QTableWidget(0, len(cols))
        self._tbl.setHorizontalHeaderLabels(cols)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.setMaximumHeight(200)
        self._tbl.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.setStyleSheet(_TBL)
        vb.addWidget(self._tbl); return w

    def _build_drift_table(self):
        w = QtWidgets.QWidget(); w.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(4)
        vb.addWidget(_lbl("Drift Detection",
                          f"color:{_CYN};font-size:11px;font-weight:bold;border:none;"))
        cols = ["Feature", "Symbol", "Drifted", "Score",
                "MeanDrift", "StdRatio", "KS", "Time"]
        self._dtbl = QtWidgets.QTableWidget(0, len(cols))
        self._dtbl.setHorizontalHeaderLabels(cols)
        self._dtbl.verticalHeader().setVisible(False)
        self._dtbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._dtbl.setAlternatingRowColors(True)
        self._dtbl.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._dtbl.horizontalHeader().setStretchLastSection(True)
        self._dtbl.setStyleSheet(_TBL)
        vb.addWidget(self._dtbl); return w

    def _on_check(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Engine not connected.")
            return
        from ..utils.feature_utils import make_feature
        from ..constant import FeatureType
        feat = make_feature(
            self._feat_ed.text().strip() or "feature",
            FeatureType.PRICE,
            self._sym_ed.text().strip() or "BTC",
            self._val_sp.value(), version=1)
        try:
            report = self._engine.check_feature_quality(feat)
            self._append_report_row(report)
            self._refresh_kpi()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def _on_simulate_drift(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Engine not connected.")
            return
        import random
        n = self._sim_n.value()
        feat = self._feat_ed.text().strip() or "close_ret"
        sym  = self._sym_ed.text().strip() or "BTC"
        hist = [random.gauss(0.01, 0.005) for _ in range(n)]
        curr = [random.gauss(0.025, 0.01) for _ in range(n // 2)]
        try:
            dr = self._engine.check_drift(feat, sym, curr, hist)
            self._append_drift_row(dr)
            self._refresh_kpi()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def _append_report_row(self, r):
        row = self._tbl.rowCount(); self._tbl.insertRow(row)
        sc = _STATUS_COLOR.get(r.status, _FG)
        sc_color = _GRN if r.score >= 80 else (_YLW if r.score >= 50 else _RED)
        cells = [r.feature_name, r.symbol, r.status.value,
                 f"{r.score:.1f}", str(r.n_issues),
                 "YES" if r.has_blocker else "no",
                 str(r.checked_at)[:16]]
        for col, txt in enumerate(cells):
            it = QtWidgets.QTableWidgetItem(txt)
            it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if col == 2: it.setForeground(QtGui.QColor(sc))
            elif col == 3: it.setForeground(QtGui.QColor(sc_color))
            elif col == 5 and r.has_blocker:
                it.setForeground(QtGui.QColor(_RED))
            self._tbl.setItem(row, col, it)
        self._tbl.scrollToBottom()

    def _append_drift_row(self, dr):
        row = self._dtbl.rowCount(); self._dtbl.insertRow(row)
        dc = _RED if dr.is_drifted else _GRN
        cells = [dr.feature_name, dr.symbol,
                 "DRIFTED" if dr.is_drifted else "stable",
                 f"{dr.drift_score:.3f}", f"{dr.mean_drift:.3f}",
                 f"{dr.std_ratio:.3f}", f"{dr.ks_statistic:.3f}",
                 str(dr.checked_at)[:16]]
        for col, txt in enumerate(cells):
            it = QtWidgets.QTableWidgetItem(txt)
            it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if col == 2: it.setForeground(QtGui.QColor(dc))
            self._dtbl.setItem(row, col, it)
        self._dtbl.scrollToBottom()

    def _refresh_kpi(self):
        if self._engine is None: return
        s = self._engine.get_quality_state()
        self._kpi["checked"].setText(str(s.total_checked))
        self._kpi["clean_pct"].setText(f"{s.clean_pct:.1f}%")
        self._kpi["avg_score"].setText(f"{s.avg_score:.1f}")
        self._kpi["blockers"].setText(str(s.blocker_count))
        self._kpi["issues"].setText(str(s.total_issues))
        self._kpi["drifted"].setText(str(s.total_drifted))

    def refresh(self):
        self._refresh_kpi()
        if self._engine is None: return
        self._tbl.setRowCount(0)
        for r in self._engine.get_quality_reports(50):
            self._append_report_row(r)
        self._dtbl.setRowCount(0)
        for dr in self._engine.get_drift_reports(20):
            self._append_drift_row(dr)
