"""
execution_intelligence_ai/ui/feedback_tab.py  (Phase 5)

FeedbackTab — 执行质量反馈面板。
左栏：反馈录入 | 右侧：KPI评分卡 + 执行报告 + 历史统计
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui

_PANEL="#1e1e2e";_DARK="#181825";_BORDER="#45475a";_FG="#cdd6f4"
_MUT="#6c7086";_BLUE="#89b4fa";_GRN="#a6e3a1";_YLW="#f9e2af"
_RED="#f38ba8";_MAV="#cba6f7";_HEAD="#313244";_PNK="#f5c2e7"
_INPUT=(f"QLineEdit,QSpinBox,QDoubleSpinBox{{background:{_HEAD};color:{_FG};"
        f"border:1px solid {_BORDER};border-radius:3px;padding:3px 6px;font-size:11px;}}")
_LLBL=f"color:{_MUT};font-size:11px;border:none;background:transparent;"

def _lbl(t,s=""): w=QtWidgets.QLabel(t); w.setStyleSheet(s); return w
def _sep():
    s=QtWidgets.QFrame(); s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    s.setStyleSheet(f"border:none;border-top:1px solid {_BORDER};background:transparent;")
    return s


class FeedbackTab(QtWidgets.QWidget):
    """执行质量反馈面板（Phase 5）。"""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._current_report = None
        self._init_ui()

    def set_engine(self, engine): self._engine = engine

    def _init_ui(self):
        self.setStyleSheet(f"background:{_PANEL};color:{_FG};")
        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(10,10,10,10); h.setSpacing(10)
        h.addWidget(self._build_left(), stretch=0)
        h.addWidget(self._build_right(), stretch=1)

    def _build_left(self):
        panel = QtWidgets.QWidget(); panel.setFixedWidth(250)
        panel.setStyleSheet(f"background:{_DARK};border-radius:6px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(panel); vb.setContentsMargins(12,14,12,14); vb.setSpacing(10)
        vb.addWidget(_lbl("反馈录入", f"color:{_MAV};font-weight:bold;font-size:12px;border:none;"))
        vb.addWidget(_sep())
        fm = QtWidgets.QFormLayout(); fm.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        fm.setVerticalSpacing(8); fm.setContentsMargins(0,0,0,0)

        self._eid = QtWidgets.QLineEdit(); self._eid.setPlaceholderText("执行ID"); self._eid.setStyleSheet(_INPUT)
        fm.addRow(_lbl("执行ID：",_LLBL), self._eid)
        self._sid = QtWidgets.QLineEdit(); self._sid.setPlaceholderText("切片ID"); self._sid.setStyleSheet(_INPUT)
        fm.addRow(_lbl("切片ID：",_LLBL), self._sid)
        self._seq = QtWidgets.QSpinBox(); self._seq.setRange(0,9999); self._seq.setStyleSheet(_INPUT)
        fm.addRow(_lbl("序号：",_LLBL), self._seq)
        self._pvol = QtWidgets.QDoubleSpinBox()
        self._pvol.setRange(1,1e9); self._pvol.setValue(1000); self._pvol.setDecimals(0); self._pvol.setStyleSheet(_INPUT)
        fm.addRow(_lbl("计划量：",_LLBL), self._pvol)
        self._fvol = QtWidgets.QDoubleSpinBox()
        self._fvol.setRange(0,1e9); self._fvol.setValue(1000); self._fvol.setDecimals(0); self._fvol.setStyleSheet(_INPUT)
        fm.addRow(_lbl("成交量：",_LLBL), self._fvol)
        self._pprice = QtWidgets.QDoubleSpinBox()
        self._pprice.setRange(0,1e6); self._pprice.setValue(10.0); self._pprice.setDecimals(4); self._pprice.setStyleSheet(_INPUT)
        fm.addRow(_lbl("计划价：",_LLBL), self._pprice)
        self._fprice = QtWidgets.QDoubleSpinBox()
        self._fprice.setRange(0,1e6); self._fprice.setValue(10.05); self._fprice.setDecimals(4); self._fprice.setStyleSheet(_INPUT)
        fm.addRow(_lbl("成交价：",_LLBL), self._fprice)
        self._lat = QtWidgets.QDoubleSpinBox()
        self._lat.setRange(0,10000); self._lat.setValue(8.0); self._lat.setDecimals(1)
        self._lat.setSuffix(" ms"); self._lat.setStyleSheet(_INPUT)
        fm.addRow(_lbl("延迟：",_LLBL), self._lat)
        vb.addLayout(fm); vb.addWidget(_sep())

        fm2 = QtWidgets.QFormLayout(); fm2.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        fm2.setVerticalSpacing(8); fm2.setContentsMargins(0,0,0,0)
        self._impact_spin = QtWidgets.QDoubleSpinBox()
        self._impact_spin.setRange(0,500); self._impact_spin.setValue(0.0)
        self._impact_spin.setDecimals(2); self._impact_spin.setSuffix(" bp"); self._impact_spin.setStyleSheet(_INPUT)
        fm2.addRow(_lbl("实现冲击：",_LLBL), self._impact_spin)
        self._vwap_spin = QtWidgets.QDoubleSpinBox()
        self._vwap_spin.setRange(0,1e6); self._vwap_spin.setValue(0.0)
        self._vwap_spin.setDecimals(4); self._vwap_spin.setStyleSheet(_INPUT)
        fm2.addRow(_lbl("市场VWAP：",_LLBL), self._vwap_spin)
        vb.addLayout(fm2); vb.addStretch()

        btn1 = QtWidgets.QPushButton("+ 记录切片成交")
        btn1.setStyleSheet(f"QPushButton{{background:{_HEAD};color:{_FG};border:1px solid {_BORDER};border-radius:4px;padding:7px;font-size:11px;}}QPushButton:hover{{background:#45475a;}}")
        btn1.clicked.connect(self._on_record_slice); vb.addWidget(btn1)
        btn2 = QtWidgets.QPushButton(">> 生成执行报告")
        btn2.setStyleSheet(f"QPushButton{{background:{_BLUE};color:#1e1e2e;font-weight:bold;border:none;border-radius:4px;padding:8px;font-size:12px;}}QPushButton:hover{{background:#74c7ec;}}")
        btn2.clicked.connect(self._on_complete); vb.addWidget(btn2)
        return panel

    def _build_right(self):
        panel = QtWidgets.QWidget(); panel.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(panel); vb.setContentsMargins(0,0,0,0); vb.setSpacing(8)
        vb.addWidget(self._build_score_bar())
        vb.addWidget(self._build_kpi_row())
        vb.addWidget(self._build_report_area())
        vb.addWidget(self._build_history_table())
        return panel

    def _build_score_bar(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w); h.setContentsMargins(16,10,16,10); h.setSpacing(16)
        self._score_lbl = QtWidgets.QLabel("--")
        self._score_lbl.setStyleSheet(f"color:{_BLUE};font-size:36px;font-weight:bold;border:none;background:transparent;")
        self._score_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._score_lbl.setFixedWidth(80); h.addWidget(self._score_lbl)
        stxt = QtWidgets.QLabel("质量\n评分")
        stxt.setStyleSheet(f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        h.addWidget(stxt)
        vsep = QtWidgets.QFrame(); vsep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        vsep.setStyleSheet(f"border:none;border-left:1px solid {_BORDER};background:transparent;")
        h.addWidget(vsep)
        self._kpi_bar: dict = {}
        for key,txt in [("fill_rate","成交率"),("slippage","滑点(bp)"),
                         ("cost","总成本(bp)"),("latency","延迟(ms)"),("duration","时长(s)")]:
            cell=QtWidgets.QWidget(); cell.setStyleSheet("background:transparent;border:none;")
            cv=QtWidgets.QVBoxLayout(cell); cv.setContentsMargins(0,0,0,0); cv.setSpacing(2)
            lk=QtWidgets.QLabel(txt); lk.setStyleSheet(f"color:{_MUT};font-size:9px;border:none;background:transparent;"); lk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv=QtWidgets.QLabel("--"); lv.setStyleSheet(f"color:{_FG};font-size:13px;font-weight:bold;border:none;background:transparent;"); lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lk); cv.addWidget(lv); self._kpi_bar[key]=lv; h.addWidget(cell)
        h.addStretch(); return w

    def _build_kpi_row(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w); h.setContentsMargins(12,8,12,8); h.setSpacing(20)
        self._kpi2: dict = {}
        for key,txt in [("n_slices","切片数"),("n_filled","已成交"),("n_partial","部分成交"),
                         ("n_cancelled","未成交"),("vwap_dev","VWAP偏差(bp)"),("impact","实现冲击(bp)")]:
            cell=QtWidgets.QWidget(); cell.setStyleSheet("background:transparent;border:none;")
            cv=QtWidgets.QVBoxLayout(cell); cv.setContentsMargins(0,0,0,0); cv.setSpacing(2)
            lk=QtWidgets.QLabel(txt); lk.setStyleSheet(f"color:{_MUT};font-size:9px;border:none;background:transparent;"); lk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv=QtWidgets.QLabel("--"); lv.setStyleSheet(f"color:{_FG};font-size:11px;font-weight:bold;border:none;background:transparent;"); lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lk); cv.addWidget(lv); self._kpi2[key]=lv; h.addWidget(cell)
        h.addStretch(); return w

    def _build_report_area(self):
        grp=QtWidgets.QGroupBox("闭环建议  Recommendations")
        grp.setStyleSheet(f"QGroupBox{{color:{_MAV};border:1px solid {_BORDER};border-radius:4px;margin-top:8px;font-size:11px;background:{_DARK};}}QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}")
        vb=QtWidgets.QVBoxLayout(grp); vb.setContentsMargins(10,14,10,10)
        self._rec_text=QtWidgets.QPlainTextEdit()
        self._rec_text.setReadOnly(True); self._rec_text.setMaximumHeight(120)
        self._rec_text.setFont(QtGui.QFont("Consolas",10))
        self._rec_text.setStyleSheet(f"QPlainTextEdit{{background:{_PANEL};color:{_YLW};border:1px solid {_BORDER};border-radius:3px;}}")
        self._rec_text.setPlainText("  点击「生成执行报告」查看质量分析与调参建议")
        vb.addWidget(self._rec_text); return grp

    def _build_history_table(self):
        w=QtWidgets.QWidget(); w.setStyleSheet("background:transparent;")
        vb=QtWidgets.QVBoxLayout(w); vb.setContentsMargins(0,0,0,0); vb.setSpacing(4)
        vb.addWidget(_lbl("历史执行报告",f"color:{_MAV};font-size:11px;font-weight:bold;border:none;"))
        cols=["执行ID","标的","策略","成交率","滑点(bp)","总成本(bp)","延迟(ms)","质量分","建议数","时间"]
        self._hist=QtWidgets.QTableWidget(0,len(cols)); self._hist.setHorizontalHeaderLabels(cols)
        self._hist.verticalHeader().setVisible(False)
        self._hist.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._hist.setAlternatingRowColors(True)
        self._hist.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._hist.horizontalHeader().setStretchLastSection(True)
        self._hist.setStyleSheet(f"QTableWidget{{background:{_DARK};color:{_FG};border:1px solid {_BORDER};gridline-color:{_BORDER};font-size:11px;}}QTableWidget::item{{padding:3px 6px;}}QTableWidget::item:alternate{{background:#181825;}}QTableWidget::item:selected{{background:#45475a;}}QHeaderView::section{{background:{_HEAD};color:{_MUT};border:none;border-bottom:1px solid {_BORDER};padding:4px 6px;font-size:10px;}}")
        vb.addWidget(self._hist); return w

    # ── slots ─────────────────────────────────────────────────────────
    def _on_record_slice(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self,"引擎未就绪","Engine 未连接。"); return
        eid = self._eid.text().strip()
        if not eid:
            QtWidgets.QMessageBox.warning(self,"参数缺失","请输入执行ID。"); return
        try:
            sf = self._engine.record_slice_feedback(
                execution_id=eid,
                slice_id=self._sid.text().strip() or f"{eid}_S0000",
                sequence=self._seq.value(),
                planned_volume=self._pvol.value(),
                filled_volume=self._fvol.value(),
                planned_price=self._pprice.value(),
                filled_price=self._fprice.value(),
                latency_ms=self._lat.value(),
            )
            self._rec_text.appendPlainText(
                f"[切片] {sf.slice_id}  fill={sf.fill_rate:.1%}  "
                f"slip={sf.slippage_bps:.2f}bp  lat={sf.latency_ms:.1f}ms")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self,"记录失败",str(e))

    def _on_complete(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self,"引擎未就绪","Engine 未连接。"); return
        eid = self._eid.text().strip()
        if not eid:
            QtWidgets.QMessageBox.warning(self,"参数缺失","请输入执行ID。"); return
        try:
            report = self._engine.complete_execution(
                eid,
                realized_impact_bps=self._impact_spin.value(),
                market_vwap=self._vwap_spin.value())
            self._current_report = report
            self._fill_kpis(report); self._fill_recs(report); self._add_hist_row(report)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self,"报告生成失败",str(e))

    def _fill_kpis(self, report):
        fb = report.feedback; score = fb.quality_score
        c = _GRN if score>=75 else (_YLW if score>=50 else _RED)
        self._score_lbl.setText(f"{score:.0f}")
        self._score_lbl.setStyleSheet(f"color:{c};font-size:36px;font-weight:bold;border:none;background:transparent;")
        self._kpi_bar["fill_rate"].setText(f"{fb.fill_rate:.1%}")
        self._kpi_bar["slippage"].setText(f"{fb.slippage_bps:.2f}")
        self._kpi_bar["cost"].setText(f"{fb.total_cost_bps:.2f}")
        self._kpi_bar["latency"].setText(f"{fb.avg_latency_ms:.1f}")
        self._kpi_bar["duration"].setText(f"{fb.execution_duration_s:.1f}")
        self._kpi2["n_slices"].setText(str(fb.n_slices))
        self._kpi2["n_filled"].setText(str(fb.n_filled))
        self._kpi2["n_partial"].setText(str(fb.n_partial))
        self._kpi2["n_cancelled"].setText(str(fb.n_cancelled))
        self._kpi2["vwap_dev"].setText(f"{fb.vwap_deviation_bps:.2f}")
        self._kpi2["impact"].setText(f"{fb.market_impact_bps:.2f}")

    def _fill_recs(self, report):
        self._rec_text.clear()
        lines = [f"  执行ID: {report.execution_id}",
                 f"  策略:   {report.strategy}",
                 f"  质量分: {report.feedback.quality_score:.1f} / 100", ""]
        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"  [{i}] {rec}")
        if report.next_params:
            lines += ["", f"  建议参数: {report.next_params}"]
        self._rec_text.setPlainText("\n".join(lines))

    def _add_hist_row(self, report):
        fb = report.feedback; score = fb.quality_score
        sc = _GRN if score>=75 else (_YLW if score>=50 else _RED)
        row = self._hist.rowCount(); self._hist.insertRow(row)
        cells = [report.execution_id[:14], report.symbol, report.strategy,
                 f"{fb.fill_rate:.1%}", f"{fb.slippage_bps:.2f}",
                 f"{fb.total_cost_bps:.2f}", f"{fb.avg_latency_ms:.1f}",
                 f"{score:.1f}", str(len(report.recommendations)),
                 str(report.generated_at)[:16]]
        for col, txt in enumerate(cells):
            it = QtWidgets.QTableWidgetItem(txt)
            it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if col == 7: it.setForeground(QtGui.QColor(sc))
            self._hist.setItem(row, col, it)
        self._hist.scrollToBottom()

    def refresh(self):
        if self._engine is None: return