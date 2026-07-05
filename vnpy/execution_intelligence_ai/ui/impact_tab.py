"""
execution_intelligence_ai/ui/impact_tab.py  (Phase 3)

ImpactTab — 市场冲击模型可视化面板。
左栏：参数 | 右侧：KPI + ASCII曲线图 + 历史表
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..model.impact_model import ImpactParams, ImpactState

_PANEL="#1e1e2e"; _DARK="#181825"; _BORDER="#45475a"; _FG="#cdd6f4"
_MUT="#6c7086"; _BLUE="#89b4fa"; _GRN="#a6e3a1"; _YLW="#f9e2af"
_RED="#f38ba8"; _MAV="#cba6f7"; _HEAD="#313244"; _PNK="#f5c2e7"
_LEVEL_COLOR={"negligible":_GRN,"low":_BLUE,"medium":_YLW,"high":_PNK,"severe":_RED}
_INPUT=(f"QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox{{background:{_HEAD};color:{_FG};"
        f"border:1px solid {_BORDER};border-radius:3px;padding:3px 6px;font-size:11px;}}"
        f"QComboBox::drop-down{{border:none;}}")
_LLBL=f"color:{_MUT};font-size:11px;border:none;background:transparent;"

def _lbl(t,s=""): w=QtWidgets.QLabel(t); w.setStyleSheet(s); return w
def _sep():
    s=QtWidgets.QFrame(); s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    s.setStyleSheet(f"border:none;border-top:1px solid {_BORDER};background:transparent;")
    return s


class ImpactTab(QtWidgets.QWidget):
    """市场冲击模型面板（Phase 3）。"""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._last_state = None
        self._init_ui()

    def set_engine(self, engine):
        self._engine = engine

    def _init_ui(self):
        self.setStyleSheet(f"background:{_PANEL};color:{_FG};")
        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(10,10,10,10); h.setSpacing(10)
        h.addWidget(self._build_left(), stretch=0)
        h.addWidget(self._build_right(), stretch=1)

    def _build_left(self):
        panel = QtWidgets.QWidget(); panel.setFixedWidth(260)
        panel.setStyleSheet(f"background:{_DARK};border-radius:6px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(panel); vb.setContentsMargins(12,14,12,14); vb.setSpacing(10)
        vb.addWidget(_lbl("冲击模型参数", f"color:{_MAV};font-weight:bold;font-size:12px;border:none;"))
        vb.addWidget(_sep())
        fm = QtWidgets.QFormLayout(); fm.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        fm.setVerticalSpacing(8); fm.setContentsMargins(0,0,0,0)

        self._sym = QtWidgets.QLineEdit(); self._sym.setPlaceholderText("如 000001"); self._sym.setStyleSheet(_INPUT)
        fm.addRow(_lbl("标的：",_LLBL), self._sym)

        self._order_spin = QtWidgets.QDoubleSpinBox()
        self._order_spin.setRange(1,1e9); self._order_spin.setValue(50000)
        self._order_spin.setDecimals(0); self._order_spin.setSingleStep(1000); self._order_spin.setStyleSheet(_INPUT)
        fm.addRow(_lbl("订单量：",_LLBL), self._order_spin)

        self._adv_spin = QtWidgets.QDoubleSpinBox()
        self._adv_spin.setRange(1,1e9); self._adv_spin.setValue(1000000)
        self._adv_spin.setDecimals(0); self._adv_spin.setSingleStep(100000); self._adv_spin.setStyleSheet(_INPUT)
        fm.addRow(_lbl("日均量(ADV)：",_LLBL), self._adv_spin)

        self._vol_spin = QtWidgets.QDoubleSpinBox()
        self._vol_spin.setRange(0.001,0.5); self._vol_spin.setValue(0.02)
        self._vol_spin.setSingleStep(0.005); self._vol_spin.setDecimals(4); self._vol_spin.setStyleSheet(_INPUT)
        fm.addRow(_lbl("波动率(σ)：",_LLBL), self._vol_spin)

        self._spread_spin = QtWidgets.QDoubleSpinBox()
        self._spread_spin.setRange(0.1,200.0); self._spread_spin.setValue(5.0)
        self._spread_spin.setSingleStep(0.5); self._spread_spin.setDecimals(1)
        self._spread_spin.setSuffix(" bp"); self._spread_spin.setStyleSheet(_INPUT)
        fm.addRow(_lbl("买卖价差：",_LLBL), self._spread_spin)

        self._model_combo = QtWidgets.QComboBox()
        self._model_combo.addItem("Square-Root（行业标准）","sqrt")
        self._model_combo.addItem("Almgren-Chriss（AC分解）","almgren_chriss")
        self._model_combo.addItem("Linear（线性基准）","linear")
        self._model_combo.setStyleSheet(_INPUT)
        fm.addRow(_lbl("冲击模型：",_LLBL), self._model_combo)

        self._eta_spin = QtWidgets.QDoubleSpinBox()
        self._eta_spin.setRange(0.01,2.0); self._eta_spin.setValue(0.2)
        self._eta_spin.setSingleStep(0.05); self._eta_spin.setDecimals(3); self._eta_spin.setStyleSheet(_INPUT)
        fm.addRow(_lbl("η（临时）：",_LLBL), self._eta_spin)

        self._gamma_spin = QtWidgets.QDoubleSpinBox()
        self._gamma_spin.setRange(0.01,2.0); self._gamma_spin.setValue(0.1)
        self._gamma_spin.setSingleStep(0.05); self._gamma_spin.setDecimals(3); self._gamma_spin.setStyleSheet(_INPUT)
        fm.addRow(_lbl("γ（永久）：",_LLBL), self._gamma_spin)

        vb.addLayout(fm); vb.addWidget(_sep()); vb.addStretch()

        btn = QtWidgets.QPushButton("▶  估算市场冲击")
        btn.setStyleSheet(f"QPushButton{{background:{_BLUE};color:#1e1e2e;font-weight:bold;border:none;border-radius:4px;padding:8px;font-size:12px;}}QPushButton:hover{{background:#74c7ec;}}")
        btn.clicked.connect(self._on_estimate); vb.addWidget(btn)

        btn2 = QtWidgets.QPushButton("生成三模型对比图")
        btn2.setStyleSheet(f"QPushButton{{background:transparent;color:{_MUT};border:1px solid {_BORDER};border-radius:4px;padding:6px;font-size:11px;}}QPushButton:hover{{background:{_HEAD};}}")
        btn2.clicked.connect(self._on_draw_curve); vb.addWidget(btn2)
        return panel

    def _build_right(self):
        panel = QtWidgets.QWidget(); panel.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(panel); vb.setContentsMargins(0,0,0,0); vb.setSpacing(8)
        vb.addWidget(self._build_kpi_bar())
        vb.addWidget(self._build_curve_area())
        vb.addWidget(self._build_hist_table())
        return panel

    def _build_kpi_bar(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w); h.setContentsMargins(12,8,12,8); h.setSpacing(20)
        self._kpi: dict = {}
        for key,txt in [("total_bp","总冲击(bp)"),("temp_bp","临时(bp)"),
                         ("perm_bp","永久(bp)"),("liq","流动性"),
                         ("level","等级"),("ratio","量/ADV")]:
            cell=QtWidgets.QWidget(); cell.setStyleSheet("background:transparent;border:none;")
            cv=QtWidgets.QVBoxLayout(cell); cv.setContentsMargins(0,0,0,0); cv.setSpacing(2)
            lk=QtWidgets.QLabel(txt); lk.setStyleSheet(f"color:{_MUT};font-size:9px;border:none;background:transparent;"); lk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv=QtWidgets.QLabel("--"); lv.setStyleSheet(f"color:{_FG};font-size:13px;font-weight:bold;border:none;background:transparent;"); lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lk); cv.addWidget(lv); self._kpi[key]=lv; h.addWidget(cell)
        h.addStretch()
        return w

    def _build_curve_area(self):
        grp=QtWidgets.QGroupBox("冲击曲线  Impact Curve  ( 订单量/ADV  vs  冲击 bp )")
        grp.setStyleSheet(f"QGroupBox{{color:{_MAV};border:1px solid {_BORDER};border-radius:4px;margin-top:8px;font-size:11px;background:{_DARK};}}QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}")
        vb=QtWidgets.QVBoxLayout(grp); vb.setContentsMargins(10,14,10,10)
        self._curve_text=QtWidgets.QPlainTextEdit()
        self._curve_text.setReadOnly(True); self._curve_text.setFixedHeight(180)
        self._curve_text.setFont(QtGui.QFont("Consolas",9))
        self._curve_text.setStyleSheet(f"QPlainTextEdit{{background:{_PANEL};color:{_GRN};border:1px solid {_BORDER};border-radius:3px;}}")
        self._curve_text.setPlainText("  点击「估算市场冲击」或「生成三模型对比图」查看结果")
        vb.addWidget(self._curve_text)
        return grp

    def _build_hist_table(self):
        w=QtWidgets.QWidget(); w.setStyleSheet("background:transparent;")
        vb=QtWidgets.QVBoxLayout(w); vb.setContentsMargins(0,0,0,0); vb.setSpacing(4)
        vb.addWidget(_lbl("历史冲击记录",f"color:{_MAV};font-size:11px;font-weight:bold;border:none;"))
        cols=["执行ID","标的","订单量","ADV","量/ADV","估算(bp)","实现(bp)","等级","时间"]
        self._hist=QtWidgets.QTableWidget(0,len(cols)); self._hist.setHorizontalHeaderLabels(cols)
        self._hist.verticalHeader().setVisible(False)
        self._hist.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._hist.setAlternatingRowColors(True)
        self._hist.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._hist.horizontalHeader().setStretchLastSection(True)
        self._hist.setStyleSheet(f"QTableWidget{{background:{_DARK};color:{_FG};border:1px solid {_BORDER};gridline-color:{_BORDER};font-size:11px;}}QTableWidget::item{{padding:3px 6px;}}QTableWidget::item:alternate{{background:#181825;}}QTableWidget::item:selected{{background:#45475a;}}QHeaderView::section{{background:{_HEAD};color:{_MUT};border:none;border-bottom:1px solid {_BORDER};padding:4px 6px;font-size:10px;}}")
        vb.addWidget(self._hist)
        return w

    # ── Slots ──────────────────────────────────────────────────────────
    def _on_estimate(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self,"引擎未就绪","Engine 未连接。"); return
        sym=self._sym.text().strip() or "DEMO"
        size=self._order_spin.value(); adv=self._adv_spin.value()
        vol=self._vol_spin.value(); spread=self._spread_spin.value()
        model=self._model_combo.currentData()
        eta=self._eta_spin.value(); gamma=self._gamma_spin.value()
        self._engine.set_impact_params(ImpactParams(
            model=model,eta=eta,gamma=gamma,adv=adv,spread_bps=spread))
        import uuid; eid=f"IMP_{uuid.uuid4().hex[:8].upper()}"
        try:
            state=self._engine.estimate_impact(
                execution_id=eid,symbol=sym,order_size=size,
                volatility=vol,adv=adv,spread_bps=spread,model=model)
            self._last_state=state; self._fill_kpi(state)
            pts=self._engine.get_impact_curve(adv,vol,model,n_points=20)
            self._curve_text.setPlainText(
                self._ascii_chart(pts,state.order_size_ratio,state.estimated_bp,
                    f"Model:{model}  σ={vol:.3f}  ADV={adv:,.0f}"))
            self._add_hist_row(state)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self,"估算失败",str(e))

    def _on_draw_curve(self):
        if self._engine is None: return
        adv=self._adv_spin.value(); vol=self._vol_spin.value()
        try:
            curves=self._engine.get_multi_model_curves(adv,vol,n_points=15)
            lines=["  三种模型冲击曲线对比", ""]
            for name,pts in curves.items():
                if not pts: continue
                max_bp=max(p["impact_bp"] for p in pts)
                bar_vals=[int(p["impact_bp"]/max_bp*20) if max_bp>0 else 0 for p in pts]
                lines.append(f"  {name:<18} | "+"".join("█"*v for v in bar_vals[:12])+f"  max={max_bp:.1f}bp")
            lines+=["","  x轴：订单量/ADV（从小到大）","  y轴：估算冲击基点（bp）"]
            self._curve_text.setPlainText("\n".join(lines))
        except Exception as e:
            self._curve_text.setPlainText(f"曲线生成失败: {e}")

    def _fill_kpi(self, s: ImpactState):
        self._kpi["total_bp"].setText(f"{s.estimated_bp:.2f}")
        self._kpi["temp_bp"].setText(f"{s.temporary_bp:.2f}")
        self._kpi["perm_bp"].setText(f"{s.permanent_bp:.2f}")
        self._kpi["liq"].setText(f"{s.liquidity_score:.3f}")
        self._kpi["ratio"].setText(f"{s.order_size_ratio:.4f}")
        lvl=s.impact_level.value; c=_LEVEL_COLOR.get(lvl,_FG)
        self._kpi["level"].setText(lvl.upper())
        self._kpi["level"].setStyleSheet(f"color:{c};font-size:13px;font-weight:bold;border:none;background:transparent;")

    def _add_hist_row(self, s: ImpactState):
        row=self._hist.rowCount(); self._hist.insertRow(row)
        cells=[s.execution_id[:12],s.symbol,f"{s.order_size:,.0f}",f"{s.adv:,.0f}",
               f"{s.order_size_ratio:.4f}",f"{s.estimated_bp:.2f}",
               f"{s.realized_bp:.2f}" if s.realized_bp else "--",
               s.impact_level.value,str(s.estimated_at)[:16]]
        for col,txt in enumerate(cells):
            it=QtWidgets.QTableWidgetItem(txt); it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if col==7: it.setForeground(QtGui.QColor(_LEVEL_COLOR.get(s.impact_level.value,_FG)))
            self._hist.setItem(row,col,it)
        self._hist.scrollToBottom()

    @staticmethod
    def _ascii_chart(points,marker_ratio=-1,marker_bp=0,title="",width=50,height=8):
        if not points: return ""
        ratios=[p["ratio"] for p in points]; bps=[p["impact_bp"] for p in points]
        max_bp=max(bps) if bps else 1
        rows=[[" "]*width for _ in range(height)]
        for j,bp in enumerate(bps):
            x=int(j/len(bps)*(width-1)); y=int(bp/max(max_bp,1e-9)*(height-1))
            y=height-1-y; rows[max(0,min(y,height-1))][x]="·"
        if 0<marker_ratio<=ratios[-1]:
            mx=int((marker_ratio-ratios[0])/max(ratios[-1]-ratios[0],1e-9)*(width-1))
            my=int(marker_bp/max(max_bp,1e-9)*(height-1)); my=height-1-my
            mx=min(max(mx,0),width-1); my=min(max(my,0),height-1); rows[my][mx]="★"
        lines=[f"  {title}",f"  {max_bp:6.1f}bp ┐"]
        for row in rows: lines.append("          │"+"".join(row))
        lines.append("      0bp ┘"+"─"*width)
        lines.append(f"           0{' '*(width-8)}{ratios[-1]:.2f}×ADV")
        if marker_ratio>0: lines.append(f"  ★ 当前: {marker_ratio:.4f}×ADV  冲击={marker_bp:.2f}bp")
        return "\n".join(lines)

    def refresh(self):
        if self._engine is None or self._last_state is None: return
        s=self._engine.get_impact_state(self._last_state.execution_id)
        if s: self._last_state=s; self._fill_kpi(s)
