"""write_pe_health_ui1.py — append ScoreCard + RegisterDialog + HealthList"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\strategy_health.py"
)

CODE = '''

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
        self._btn_reg = QPushButton("\\u2795 \\u6ce8\\u518c\\u7b56\\u7565")
        self._btn_reg.setFixedHeight(26)
        self._btn_reg.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_reg.clicked.connect(self._on_register)
        tb.addWidget(self._btn_reg)
        self._status_combo = QComboBox(); self._status_combo.setFixedHeight(26)
        self._status_combo.addItem("\\u5168\\u90e8", None)
        for s in HealthStatus:
            self._status_combo.addItem(STATUS_ICON.get(s,"")+" "+s.value, s)
        self._status_combo.currentIndexChanged.connect(lambda _: self.refresh())
        tb.addWidget(self._status_combo, 1)
        tb.addStretch()
        root.addLayout(tb)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "\\u7b56\\u7565\\u540d\\u79f0","\\u72b6\\u6001","\\u603b\\u5206",
            "\\u6027\\u80fd","\\u98ce\\u9669"])
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
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("HealthList OK, lines:", len(full.splitlines()))
