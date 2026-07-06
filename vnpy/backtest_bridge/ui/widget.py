"""
backtest_bridge/ui/widget.py

BacktestBridgeWidget — 信号回测桥主窗口。
"""
from __future__ import annotations
from datetime import datetime
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine, EventEngine
from ..constant import APP_NAME, SignalSource, BridgeMode, PositionSizing, RunStatus
from ..event import EVENT_RUN_COMPLETED, EVENT_RUN_FAILED, EVENT_BATCH_COMPLETED
from ..model.signal_model import BacktestConfig, BacktestResult

_BG = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"; _FG = "#cdd6f4"
_MUT = "#6c7086"; _GRN = "#a6e3a1"; _YLW = "#f9e2af"; _RED = "#f38ba8"
_MAV = "#cba6f7"; _HEAD = "#313244"; _CYN = "#89dceb"; _ORG = "#fab387"
_TEA = "#94e2d5"; _BLUE = "#89b4fa"
_TBL = (
    "QTableWidget{background:#181825;color:#cdd6f4;border:1px solid #45475a;"
    "gridline-color:#45475a;font-size:10px;}"
    "QTableWidget::item{padding:3px 5px;}"
    "QTableWidget::item:alternate{background:#1e1e2e;}"
    "QTableWidget::item:selected{background:#45475a;}"
    "QHeaderView::section{background:#313244;color:#6c7086;border:none;"
    "border-bottom:1px solid #45475a;padding:3px 5px;font-size:9px;}"
)


def _lbl(t, s=""):
    w = QtWidgets.QLabel(t); w.setStyleSheet(s); return w


def _btn(t, color, slot):
    b = QtWidgets.QPushButton(t); b.setFixedHeight(32)
    b.setStyleSheet(
        f"QPushButton{{background:{color};color:#1e1e2e;font-weight:bold;"
        f"border:none;border-radius:4px;padding:0 10px;font-size:11px;}}"
        f"QPushButton:disabled{{background:#45475a;color:#6c7086;}}")
    b.clicked.connect(slot); return b


def _combo(items):
    c = QtWidgets.QComboBox(); c.addItems(items)
    c.setStyleSheet(
        f"QComboBox{{background:{_HEAD};color:{_FG};border:1px solid {_BORDER};"
        f"border-radius:3px;padding:3px 6px;font-size:10px;}}"
        f"QComboBox::drop-down{{border:none;}}"
        f"QAbstractItemView{{background:{_DARK};color:{_FG};"
        f"selection-background-color:{_HEAD};}}")
    return c


def _spin(mn, mx, val, dec=0, step=1.0):
    s = QtWidgets.QDoubleSpinBox() if dec > 0 else QtWidgets.QSpinBox()
    s.setRange(mn, mx); s.setValue(val)
    if dec > 0: s.setDecimals(dec); s.setSingleStep(step)
    s.setStyleSheet(
        f"QSpinBox,QDoubleSpinBox{{background:{_HEAD};color:{_FG};"
        f"border:1px solid {_BORDER};border-radius:3px;padding:3px;font-size:10px;}}"
        f"QSpinBox::up-button,QDoubleSpinBox::up-button,"
        f"QSpinBox::down-button,QDoubleSpinBox::down-button{{width:14px;background:{_BORDER};}}")
    return s


class BacktestBridgeWidget(QtWidgets.QMainWindow):
    """Backtest Bridge 主窗口。"""

    widget_name = APP_NAME

    def __init__(self, main_engine: MainEngine,
                 event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine       = main_engine.get_engine(APP_NAME)
        self._init_ui()
        self._init_menu()
        self._register_events()

    def _init_ui(self):
        self.setWindowTitle("Backtest Bridge  信号回测桥")
        self.resize(1440, 860)
        self.setStyleSheet(f"background:{_BG};color:{_FG};")
        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        h = QtWidgets.QHBoxLayout(central)
        h.setContentsMargins(8,8,8,8); h.setSpacing(8)
        h.addWidget(self._build_left(),  stretch=0)
        h.addWidget(self._build_right(), stretch=1)

    def _build_left(self):
        panel = QtWidgets.QWidget(); panel.setFixedWidth(240)
        panel.setStyleSheet(
            f"background:{_DARK};border-radius:6px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(12,14,12,14); vb.setSpacing(8)
        vb.addWidget(_lbl("Signal Configuration",
                          f"color:{_CYN};font-weight:bold;font-size:12px;border:none;"))

        def row(label, widget):
            r = QtWidgets.QWidget()
            r.setStyleSheet("background:transparent;border:none;")
            rh = QtWidgets.QHBoxLayout(r); rh.setContentsMargins(0,0,0,0)
            lk = _lbl(label, f"color:{_MUT};font-size:10px;border:none;")
            lk.setFixedWidth(88)
            rh.addWidget(lk); rh.addWidget(widget); vb.addWidget(r)

        self._cb_source = _combo([s.value for s in SignalSource])
        self._cb_mode   = _combo([m.value for m in BridgeMode])
        self._cb_sizing = _combo([p.value for p in PositionSizing])
        row("Signal Source", self._cb_source)
        row("Bridge Mode",   self._cb_mode)
        row("Sizing",        self._cb_sizing)

        vb.addWidget(_lbl("Backtest Params",
                          f"color:{_YLW};font-size:10px;font-weight:bold;border:none;"))
        self._edit_symbol = QtWidgets.QLineEdit("BTCUSDT.BINANCE")
        self._edit_symbol.setStyleSheet(
            f"background:{_HEAD};color:{_FG};border:1px solid {_BORDER};"
            f"border-radius:3px;padding:4px;font-size:10px;")
        row("Symbol", self._edit_symbol)

        self._spin_capital = _spin(10000, 100_000_000, 1_000_000)
        self._spin_rate    = _spin(0.0, 0.01, 0.0002, dec=4, step=0.0001)
        self._spin_slip    = _spin(0.0, 100.0, 0.5, dec=1, step=0.1)
        self._spin_maxpos  = _spin(0.01, 100.0, 1.0, dec=2, step=0.1)
        self._spin_thr     = _spin(0.0, 1.0, 0.1, dec=2, step=0.01)
        row("Capital",    self._spin_capital)
        row("Rate",       self._spin_rate)
        row("Slippage",   self._spin_slip)
        row("Max Pos",    self._spin_maxpos)
        row("Sig Thresh", self._spin_thr)

        vb.addWidget(_lbl("Date Range",
                          f"color:{_YLW};font-size:10px;font-weight:bold;border:none;"))
        self._edit_start = QtWidgets.QLineEdit("2022-01-01")
        self._edit_end   = QtWidgets.QLineEdit("2023-12-31")
        for w in (self._edit_start, self._edit_end):
            w.setStyleSheet(
                f"background:{_HEAD};color:{_FG};border:1px solid {_BORDER};"
                f"border-radius:3px;padding:4px;font-size:10px;")
        row("Start", self._edit_start)
        row("End",   self._edit_end)

        vb.addStretch()
        vb.addWidget(_btn("Run Backtest",   _GRN,  self._on_run))
        vb.addWidget(_btn("Batch Compare",  _BLUE, self._on_batch))
        vb.addWidget(_btn("Reset Signals",  _MUT,  self._on_reset_signals))
        return panel

    def _build_right(self):
        w = QtWidgets.QWidget()
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(0,0,0,0); vb.setSpacing(8)
        vb.addWidget(self._build_results_table(), stretch=2)
        vb.addWidget(self._build_bottom(),        stretch=1)
        return w

    def _build_results_table(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(10,8,10,8); vb.setSpacing(6)
        hdr = QtWidgets.QHBoxLayout()
        hdr.addWidget(_lbl("Backtest Results",
                           f"color:{_GRN};font-size:11px;font-weight:bold;border:none;"))
        hdr.addStretch()
        self._status_lbl = _lbl("Ready", f"color:{_MUT};font-size:10px;border:none;")
        hdr.addWidget(self._status_lbl)
        vb.addLayout(hdr)
        cols = ["Run ID","Name","Return %","Annual %","MaxDD %",
                "Sharpe","Calmar","Trades","WinRate","Signals","Status"]
        self._result_tbl = QtWidgets.QTableWidget(0, len(cols))
        self._result_tbl.setHorizontalHeaderLabels(cols)
        self._result_tbl.verticalHeader().setVisible(False)
        self._result_tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._result_tbl.setAlternatingRowColors(True)
        self._result_tbl.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._result_tbl.horizontalHeader().setStretchLastSection(True)
        self._result_tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._result_tbl.setStyleSheet(_TBL)
        vb.addWidget(self._result_tbl)
        return w

    def _build_bottom(self):
        w = QtWidgets.QWidget(); w.setStyleSheet("background:transparent;")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0,0,0,0); h.setSpacing(8)
        h.addWidget(self._build_stats_panel(), stretch=1)
        h.addWidget(self._build_log_panel(),   stretch=1)
        return w

    def _build_stats_panel(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_DARK};border-radius:4px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(10,8,10,8); vb.setSpacing(4)
        vb.addWidget(_lbl("Best Result",
                          f"color:{_MAV};font-size:10px;font-weight:bold;border:none;"))
        self._stats_text = QtWidgets.QPlainTextEdit()
        self._stats_text.setReadOnly(True)
        self._stats_text.setFont(QtGui.QFont("Consolas", 9))
        self._stats_text.setStyleSheet(
            f"QPlainTextEdit{{background:{_BG};color:{_TEA};"
            f"border:1px solid {_BORDER};border-radius:3px;}}")
        self._stats_text.setPlainText("  No results yet.")
        vb.addWidget(self._stats_text)
        return w

    def _build_log_panel(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_DARK};border-radius:4px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(10,8,10,8); vb.setSpacing(4)
        vb.addWidget(_lbl("Engine Log",
                          f"color:{_YLW};font-size:10px;font-weight:bold;border:none;"))
        self._log_text = QtWidgets.QPlainTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setFont(QtGui.QFont("Consolas", 9))
        self._log_text.setStyleSheet(
            f"QPlainTextEdit{{background:{_BG};color:{_MUT};"
            f"border:1px solid {_BORDER};border-radius:3px;}}")
        vb.addWidget(self._log_text)
        return w

    def _init_menu(self):
        mb = self.menuBar()
        mb.setStyleSheet(
            f"QMenuBar{{background:{_DARK};color:{_FG};border:none;}}"
            f"QMenuBar::item:selected{{background:{_HEAD};}}"
            f"QMenu{{background:{_DARK};color:{_FG};border:1px solid {_BORDER};}}"
            f"QMenu::item:selected{{background:{_HEAD};}}")
        m = mb.addMenu("Bridge")
        m.addAction("Run Backtest").triggered.connect(self._on_run)
        m.addAction("Batch Compare (4 modes)").triggered.connect(self._on_batch)
        m.addSeparator()
        m.addAction("Reset Signals").triggered.connect(self._on_reset_signals)
        m.addAction("Clear Results").triggered.connect(self._on_clear_results)
        m.addSeparator()
        m.addAction("Close").triggered.connect(self.close)

    def _register_events(self):
        self._event_engine.register(EVENT_RUN_COMPLETED,  self._on_run_event)
        self._event_engine.register(EVENT_RUN_FAILED,     self._on_run_event)
        self._event_engine.register(EVENT_BATCH_COMPLETED,self._on_batch_event)

    def _on_run_event(self, event):
        d = event.data or {}
        self._append_log(
            f"Run {d.get('run_id','')} [{d.get('status','')}] "
            f"return={float(d.get('total_return',0)):.2%} "
            f"sharpe={float(d.get('sharpe_ratio',0)):.3f}")
        self._refresh_best()

    def _on_batch_event(self, event):
        d = event.data or {}
        self._append_log(
            f"Batch {d.get('batch_id','')} done "
            f"{d.get('completed',0)}/{d.get('total_runs',0)} runs")
        self._refresh_best()
        self._status_lbl.setText("Batch done")
        self._status_lbl.setStyleSheet(f"color:{_GRN};font-size:10px;border:none;")

    def _parse_dates(self):
        start = datetime.strptime(self._edit_start.text().strip(), "%Y-%m-%d")
        end   = datetime.strptime(self._edit_end.text().strip(),   "%Y-%m-%d")
        return start, end

    def _on_run(self):
        if self._engine is None: return
        try: start, end = self._parse_dates()
        except ValueError as e: self._append_log(f"Date err: {e}"); return
        symbol = self._edit_symbol.text().strip() or "BTCUSDT.BINANCE"
        cfg = BacktestConfig(
            config_id      = f"UI_{symbol}",
            name           = f"{self._cb_mode.currentText()}/{symbol}",
            vt_symbol      = symbol,
            start          = start, end = end,
            capital        = float(self._spin_capital.value()),
            rate           = float(self._spin_rate.value()),
            slippage       = float(self._spin_slip.value()),
            mode           = BridgeMode(self._cb_mode.currentText()),
            signal_source  = SignalSource(self._cb_source.currentText()),
            sizing         = PositionSizing(self._cb_sizing.currentText()),
            max_pos        = float(self._spin_maxpos.value()),
            signal_threshold=float(self._spin_thr.value()),
        )
        self._status_lbl.setText("Running...")
        self._status_lbl.setStyleSheet(f"color:{_YLW};font-size:10px;border:none;")
        self._engine.init(); self._engine.start()
        self._engine.generate_test_signals(symbol.split(".")[0], start, end)
        r = self._engine.run(cfg)
        self._append_result_row(r); self._refresh_best()
        self._status_lbl.setText("Done")
        self._status_lbl.setStyleSheet(f"color:{_GRN};font-size:10px;border:none;")

    def _on_batch(self):
        if self._engine is None: return
        try: start, end = self._parse_dates()
        except ValueError as e: self._append_log(f"Date err: {e}"); return
        symbol  = self._edit_symbol.text().strip() or "BTCUSDT.BINANCE"
        capital = float(self._spin_capital.value())
        self._status_lbl.setText("Batch running...")
        self._status_lbl.setStyleSheet(f"color:{_YLW};font-size:10px;border:none;")
        self._engine.init(); self._engine.start()
        batch = self._engine.quick_compare(symbol, start, end, capital)
        for r in batch.results:
            self._append_result_row(r)
        self._refresh_best()
        self._status_lbl.setText(f"Batch done ({len(batch.results)} runs)")
        self._status_lbl.setStyleSheet(f"color:{_GRN};font-size:10px;border:none;")

    def _on_reset_signals(self):
        if self._engine: self._engine.clear_signals(); self._append_log("Signals cleared.")

    def _on_clear_results(self):
        self._result_tbl.setRowCount(0)
        self._stats_text.setPlainText("  No results yet.")

    def _append_result_row(self, r: BacktestResult):
        tbl = self._result_tbl
        for row in range(tbl.rowCount()):
            if tbl.item(row, 0) and tbl.item(row, 0).text() == r.run_id:
                return
        row = tbl.rowCount(); tbl.insertRow(row)
        sc    = _GRN if r.status == RunStatus.COMPLETED else _RED
        ret_c = _GRN if r.total_return > 0 else _RED
        cells = [
            r.run_id, r.name,
            f"{r.total_return:.2%}", f"{r.annual_return:.2%}",
            f"{r.max_drawdown:.2%}", f"{r.sharpe_ratio:.3f}",
            f"{r.calmar_ratio:.3f}", str(r.total_trades),
            f"{r.win_rate:.1%}", f"{r.signals_used}/{r.signals_total}",
            r.status.value,
        ]
        for col, txt in enumerate(cells):
            it = QtWidgets.QTableWidgetItem(txt)
            it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if col == 2: it.setForeground(QtGui.QColor(ret_c))
            if col == 10: it.setForeground(QtGui.QColor(sc))
            tbl.setItem(row, col, it)
        tbl.scrollToBottom()

    def _refresh_best(self):
        if self._engine is None: return
        best = self._engine.get_best("sharpe_ratio", 1)
        if not best: return
        r = best[0]
        lines = [
            f"  Best Run:      {r.run_id}",
            f"  Name:          {r.name}",
            f"  Status:        {r.status.value}",
            f"  Total Return:  {r.total_return:.2%}",
            f"  Annual Return: {r.annual_return:.2%}",
            f"  Max Drawdown:  {r.max_drawdown:.2%}",
            f"  Sharpe Ratio:  {r.sharpe_ratio:.4f}",
            f"  Calmar Ratio:  {r.calmar_ratio:.4f}",
            f"  Total Trades:  {r.total_trades}",
            f"  Win Rate:      {r.win_rate:.1%}",
            f"  Profit Factor: {r.profit_factor:.3f}",
            f"  End Balance:   {r.end_balance:,.0f}",
            f"  Signals Used:  {r.signals_used}/{r.signals_total}",
            f"  Duration:      {r.duration_s:.1f}s",
        ]
        self._stats_text.setPlainText("\n".join(lines))

    def _append_log(self, msg: str):
        ts = str(datetime.now())[11:19]
        self._log_text.appendPlainText(f"  [{ts}] {msg}")
        sb = self._log_text.verticalScrollBar(); sb.setValue(sb.maximum())

    def closeEvent(self, event):
        try:
            self._event_engine.unregister(EVENT_RUN_COMPLETED,  self._on_run_event)
            self._event_engine.unregister(EVENT_RUN_FAILED,     self._on_run_event)
            self._event_engine.unregister(EVENT_BATCH_COMPLETED,self._on_batch_event)
        except Exception:
            pass
        super().closeEvent(event)
