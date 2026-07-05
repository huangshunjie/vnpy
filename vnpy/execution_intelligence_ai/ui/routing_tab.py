"""
execution_intelligence_ai/ui/routing_tab.py  (Phase 4)

RoutingTab — 执行路由可视化面板。
左栏：路由参数 | 右侧：场所排名表 + 路由决策记录
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..constant import RoutingMode
from ..model.routing_model import VenueProfile, VenueScore, RoutingState

_PANEL="#1e1e2e";_DARK="#181825";_BORDER="#45475a";_FG="#cdd6f4"
_MUT="#6c7086";_BLUE="#89b4fa";_GRN="#a6e3a1";_YLW="#f9e2af"
_RED="#f38ba8";_MAV="#cba6f7";_HEAD="#313244";_PNK="#f5c2e7"
_INPUT=(f"QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox{{background:{_HEAD};color:{_FG};"
        f"border:1px solid {_BORDER};border-radius:3px;padding:3px 6px;font-size:11px;}}"
        f"QComboBox::drop-down{{border:none;}}")
_LLBL=f"color:{_MUT};font-size:11px;border:none;background:transparent;"

def _lbl(t,s=""): w=QtWidgets.QLabel(t); w.setStyleSheet(s); return w
def _sep():
    s=QtWidgets.QFrame(); s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    s.setStyleSheet(f"border:none;border-top:1px solid {_BORDER};background:transparent;")
    return s


class RoutingTab(QtWidgets.QWidget):
    """执行路由可视化面板（Phase 4）。"""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine):
        self._engine = engine

    def _init_ui(self):
        self.setStyleSheet(f"background:{_PANEL};color:{_FG};")
        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(10,10,10,10); h.setSpacing(10)
        h.addWidget(self._build_left(),  stretch=0)
        h.addWidget(self._build_right(), stretch=1)

    # ── 左栏 ─────────────────────────────────────────────────────────
    def _build_left(self):
        panel = QtWidgets.QWidget(); panel.setFixedWidth(250)
        panel.setStyleSheet(f"background:{_DARK};border-radius:6px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(panel); vb.setContentsMargins(12,14,12,14); vb.setSpacing(10)

        vb.addWidget(_lbl("路由参数设置",
            f"color:{_MAV};font-weight:bold;font-size:12px;border:none;"))
        vb.addWidget(_sep())

        fm = QtWidgets.QFormLayout()
        fm.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        fm.setVerticalSpacing(8); fm.setContentsMargins(0,0,0,0)

        self._eid_edit = QtWidgets.QLineEdit(); self._eid_edit.setPlaceholderText("执行ID")
        self._eid_edit.setStyleSheet(_INPUT)
        fm.addRow(_lbl("执行ID：",_LLBL), self._eid_edit)

        self._sym_edit = QtWidgets.QLineEdit(); self._sym_edit.setPlaceholderText("如 000001")
        self._sym_edit.setStyleSheet(_INPUT)
        fm.addRow(_lbl("标的：",_LLBL), self._sym_edit)

        self._size_spin = QtWidgets.QDoubleSpinBox()
        self._size_spin.setRange(1,1e9); self._size_spin.setValue(10000)
        self._size_spin.setDecimals(0); self._size_spin.setSingleStep(1000)
        self._size_spin.setStyleSheet(_INPUT)
        fm.addRow(_lbl("订单量：",_LLBL), self._size_spin)

        self._mode_combo = QtWidgets.QComboBox()
        for m in RoutingMode: self._mode_combo.addItem(m.value, m)
        self._mode_combo.setStyleSheet(_INPUT)
        fm.addRow(_lbl("路由策略：",_LLBL), self._mode_combo)

        vb.addLayout(fm); vb.addWidget(_sep())

        # 策略说明
        self._hint = QtWidgets.QLabel()
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(f"color:{_MUT};font-size:10px;border:none;background:{_HEAD};border-radius:3px;padding:6px;")
        self._mode_combo.currentIndexChanged.connect(self._update_hint)
        vb.addWidget(self._hint)

        vb.addStretch()

        # 操作按钮
        btn_rank = QtWidgets.QPushButton("▶  刷新场所排名")
        btn_rank.setStyleSheet(f"QPushButton{{background:{_BLUE};color:#1e1e2e;font-weight:bold;border:none;border-radius:4px;padding:8px;font-size:12px;}}QPushButton:hover{{background:#74c7ec;}}")
        btn_rank.clicked.connect(self._on_refresh_ranking); vb.addWidget(btn_rank)

        btn_route = QtWidgets.QPushButton("路由单个切片（测试）")
        btn_route.setStyleSheet(f"QPushButton{{background:transparent;color:{_MUT};border:1px solid {_BORDER};border-radius:4px;padding:6px;font-size:11px;}}QPushButton:hover{{background:{_HEAD};}}")
        btn_route.clicked.connect(self._on_test_route); vb.addWidget(btn_route)

        self._update_hint()
        return panel

    # ── 右栏 ─────────────────────────────────────────────────────────
    def _build_right(self):
        panel = QtWidgets.QWidget(); panel.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(panel); vb.setContentsMargins(0,0,0,0); vb.setSpacing(8)
        vb.addWidget(self._build_venue_table())
        vb.addWidget(self._build_decision_table())
        return panel

    def _build_venue_table(self):
        grp = QtWidgets.QGroupBox("场所排名  Venue Ranking")
        grp.setStyleSheet(f"QGroupBox{{color:{_MAV};border:1px solid {_BORDER};border-radius:4px;margin-top:8px;font-size:11px;background:{_DARK};}}QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}")
        vb = QtWidgets.QVBoxLayout(grp); vb.setContentsMargins(8,14,8,8)
        cols=["排名","场所ID","名称","类型","综合评分","总成本(bp)","滑点(bp)","延迟(ms)","成交率","状态"]
        self._venue_tbl = QtWidgets.QTableWidget(0, len(cols))
        self._venue_tbl.setHorizontalHeaderLabels(cols)
        self._venue_tbl.verticalHeader().setVisible(False)
        self._venue_tbl.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._venue_tbl.setAlternatingRowColors(True)
        self._venue_tbl.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._venue_tbl.horizontalHeader().setStretchLastSection(True)
        self._venue_tbl.setMaximumHeight(200)
        self._venue_tbl.setStyleSheet(self._tbl_style())
        vb.addWidget(self._venue_tbl)
        return grp

    def _build_decision_table(self):
        grp = QtWidgets.QGroupBox("路由决策记录  Routing Decisions")
        grp.setStyleSheet(f"QGroupBox{{color:{_MAV};border:1px solid {_BORDER};border-radius:4px;margin-top:8px;font-size:11px;background:{_DARK};}}QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}")
        vb = QtWidgets.QVBoxLayout(grp); vb.setContentsMargins(8,14,8,8)
        cols=["执行ID","切片ID","标的","路由模式","选定场所","场所名称",
              "预期成本(bp)","预期延迟(ms)","实现成本(bp)","决策时间"]
        self._dec_tbl = QtWidgets.QTableWidget(0, len(cols))
        self._dec_tbl.setHorizontalHeaderLabels(cols)
        self._dec_tbl.verticalHeader().setVisible(False)
        self._dec_tbl.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._dec_tbl.setAlternatingRowColors(True)
        self._dec_tbl.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._dec_tbl.horizontalHeader().setStretchLastSection(True)
        self._dec_tbl.setStyleSheet(self._tbl_style())
        vb.addWidget(self._dec_tbl)
        return grp

    def _tbl_style(self):
        return (f"QTableWidget{{background:{_DARK};color:{_FG};border:1px solid {_BORDER};"
                f"gridline-color:{_BORDER};font-size:11px;}}"
                f"QTableWidget::item{{padding:3px 6px;}}"
                f"QTableWidget::item:alternate{{background:#181825;}}"
                f"QTableWidget::item:selected{{background:#45475a;}}"
                f"QHeaderView::section{{background:{_HEAD};color:{_MUT};border:none;"
                f"border-bottom:1px solid {_BORDER};padding:4px 6px;font-size:10px;}}")

    # ── hints ─────────────────────────────────────────────────────────
    _HINTS = {
        RoutingMode.BALANCED:     "Balanced: 多因子加权（成本40%+滑点25%+延迟15%+成交猇20%） 综合最优，默认推荐",
        RoutingMode.BEST_PRICE:   "Best Price: 选综合执行成本（佣金+滑点+价差/2）最低的场所 适合成本优先场景",
        RoutingMode.MIN_SLIPPAGE: "Min Slippage: 选历史平均滑点最低的场所 适合大单冲击敏感场景",
        RoutingMode.FASTEST:      "Fastest: 选延迟最低的场所 适合高频/时间敏感订单",
    }
    def _update_hint(self):
        m = self._mode_combo.currentData()
        if m: self._hint.setText(self._HINTS.get(m, ""))

    # ── slots ─────────────────────────────────────────────────────────
    def _on_refresh_ranking(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self,"引擎未就绪","Engine 未连接。"); return
        mode = self._mode_combo.currentData()
        try:
            ranking = self._engine.get_venue_ranking(mode)
            venues  = self._engine.get_venues()
            venue_map = {v.venue_id: v for v in venues}
            self._fill_venue_table(ranking, venue_map)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self,"刷新失败",str(e))

    def _on_test_route(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self,"引擎未就绪","Engine 未连接。"); return
        import uuid
        eid   = self._eid_edit.text().strip() or f"RTE_{uuid.uuid4().hex[:6].upper()}"
        sym   = self._sym_edit.text().strip() or "DEMO"
        size  = self._size_spin.value()
        mode  = self._mode_combo.currentData()
        sid   = f"{eid}_S0000"
        try:
            state = self._engine.route_slice(eid, sid, sym, size, mode)
            self._add_decision_row(state)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self,"路由失败",str(e))

    # ── fill tables ───────────────────────────────────────────────────
    def _fill_venue_table(self, ranking: list, venue_map: dict):
        self._venue_tbl.setRowCount(0)
        for rank, vs in enumerate(ranking, 1):
            vp = venue_map.get(vs.venue_id)
            row = self._venue_tbl.rowCount(); self._venue_tbl.insertRow(row)
            type_color = {
                "exchange": _GRN, "broker": _BLUE, "darkpool": _MAV
            }.get(vp.venue_type if vp else "broker", _FG)
            avail_txt = "✓" if (vp and vp.is_available) else "✗"
            avail_c   = _GRN if (vp and vp.is_available) else _RED
            cells = [
                str(rank),
                vs.venue_id,
                vp.name if vp else "--",
                vp.venue_type if vp else "--",
                f"{vs.score:.4f}",
                f"{vs.cost_bps:.2f}",
                f"{vp.avg_slippage_bps:.2f}" if vp else "--",
                f"{vs.latency_ms:.1f}",
                f"{vs.fill_rate:.2%}",
                avail_txt,
            ]
            for col, txt in enumerate(cells):
                it = QtWidgets.QTableWidgetItem(txt)
                it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if col == 3: it.setForeground(QtGui.QColor(type_color))
                elif col == 4:
                    c = _GRN if rank == 1 else (_YLW if rank == 2 else _MUT)
                    it.setForeground(QtGui.QColor(c))
                elif col == 9: it.setForeground(QtGui.QColor(avail_c))
                self._venue_tbl.setItem(row, col, it)

    def _add_decision_row(self, state: RoutingState):
        row = self._dec_tbl.rowCount(); self._dec_tbl.insertRow(row)
        cells = [
            state.execution_id[:14],
            state.slice_id[-8:] if len(state.slice_id) > 8 else state.slice_id,
            state.symbol,
            state.routing_mode.value,
            state.selected_venue_id,
            state.selected_venue_name,
            f"{state.expected_cost_bps:.2f}",
            f"{state.expected_latency_ms:.1f}",
            f"{state.realized_cost_bps:.2f}" if state.realized_cost_bps else "--",
            str(state.decided_at)[:16],
        ]
        for col, txt in enumerate(cells):
            it = QtWidgets.QTableWidgetItem(txt)
            it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self._dec_tbl.setItem(row, col, it)
        self._dec_tbl.scrollToBottom()

    # ── refresh ───────────────────────────────────────────────────────
    def refresh(self):
        self._on_refresh_ranking()
