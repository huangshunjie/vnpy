"""
screening/ui/backtest_widget.py
Backtest Widget — Phase 7
"""
from __future__ import annotations
from typing import Optional
from vnpy.trader.ui import QtWidgets, QtCore
from ..engine.backtest_engine import BacktestConfig, BacktestResult

_PANEL="#181825"; _PANEL2="#11111b"; _BORDER="#45475a"; _FG="#cdd6f4"
_MUT="#6c7086"; _BLU="#89b4fa"; _GRN="#a6e3a1"; _RED="#f38ba8"
_YLW="#f9e2af"; _ORG="#fab387"; _MAV="#cba6f7"
_LABEL=f"color:{_FG};font-size:11px;"
_INPUT=(f"background:{_PANEL2};color:{_FG};border:1px solid {_BORDER};"
        f"border-radius:3px;padding:3px 6px;font-size:11px;")
_SECTION=f"color:{_BLU};font-size:11px;font-weight:bold;"

def _sb(text, color=_MUT):
    b=QtWidgets.QPushButton(text)
    b.setStyleSheet(
        f"QPushButton{{background:#313244;color:{color};"
        f"border:1px solid {_BORDER};border-radius:3px;padding:4px 12px;font-size:11px;}}"
        f"QPushButton:hover{{background:#45475a;}}")
    return b

_METRIC_STYLE = (f"background:{_PANEL2};color:{_FG};border:1px solid {_BORDER};"
                 f"border-radius:4px;padding:8px 12px;font-size:12px;font-weight:bold;")


class MetricCard(QtWidgets.QWidget):
    """单个绩效指标卡片。"""
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{_PANEL2};border:1px solid {_BORDER};border-radius:4px;")
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(10, 8, 10, 8); v.setSpacing(2)
        self._lbl = QtWidgets.QLabel(label)
        self._lbl.setStyleSheet(f"color:{_MUT};font-size:10px;border:none;")
        self._val = QtWidgets.QLabel("--")
        self._val.setStyleSheet(f"color:{_FG};font-size:14px;font-weight:bold;border:none;")
        v.addWidget(self._lbl); v.addWidget(self._val)
        self.setFixedWidth(130)

    def set_value(self, value: str, color: str = _FG):
        self._val.setText(value)
        self._val.setStyleSheet(
            f"color:{color};font-size:14px;font-weight:bold;border:none;")


class BacktestWidget(QtWidgets.QWidget):
    """回测配置与结果展示面板（Phase 7）。"""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._last_result: Optional[BacktestResult] = None
        self._init_ui()

    def _sep(self):
        s=QtWidgets.QFrame(); s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border:none;border-top:1px solid {_BORDER};"); return s

    def _sec(self, t):
        l=QtWidgets.QLabel(t); l.setStyleSheet(_SECTION); return l

    def _init_ui(self):
        self.setStyleSheet(f"background:{_PANEL};")
        root=QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12,12,12,12); root.setSpacing(8)

        t=QtWidgets.QLabel("Backtest  回测分析")
        t.setStyleSheet(f"color:{_BLU};font-size:13px;font-weight:bold;")
        root.addWidget(t); root.addWidget(self._sep())

        # ── 回测参数 ──────────────────────────────────────────────────
        root.addWidget(self._sec("回测参数"))
        grid = QtWidgets.QGridLayout(); grid.setSpacing(6)

        self._start_edit = QtWidgets.QLineEdit("2021-01-01")
        self._start_edit.setStyleSheet(_INPUT); self._start_edit.setFixedWidth(110)
        self._end_edit = QtWidgets.QLineEdit("")
        self._end_edit.setStyleSheet(_INPUT); self._end_edit.setFixedWidth(110)
        self._end_edit.setPlaceholderText("今日")
        self._topn_spin = QtWidgets.QSpinBox()
        self._topn_spin.setRange(1,200); self._topn_spin.setValue(20)
        self._topn_spin.setFixedWidth(70); self._topn_spin.setStyleSheet(_INPUT)
        self._rb_spin = QtWidgets.QSpinBox()
        self._rb_spin.setRange(1,60); self._rb_spin.setValue(20)
        self._rb_spin.setSuffix(" 日"); self._rb_spin.setFixedWidth(80)
        self._rb_spin.setStyleSheet(_INPUT)
        self._comm_spin = QtWidgets.QDoubleSpinBox()
        self._comm_spin.setRange(0,0.01); self._comm_spin.setDecimals(4)
        self._comm_spin.setValue(0.0003); self._comm_spin.setFixedWidth(90)
        self._comm_spin.setStyleSheet(_INPUT)
        self._rf_spin = QtWidgets.QDoubleSpinBox()
        self._rf_spin.setRange(0,0.1); self._rf_spin.setDecimals(3)
        self._rf_spin.setValue(0.02); self._rf_spin.setSuffix(" 年化")
        self._rf_spin.setFixedWidth(100); self._rf_spin.setStyleSheet(_INPUT)

        labels_widgets = [
            ("开始日期", self._start_edit), ("结束日期", self._end_edit),
            ("Top N 持仓", self._topn_spin), ("调仓周期", self._rb_spin),
            ("手续费率", self._comm_spin), ("无风险利率", self._rf_spin),
        ]
        for i, (lbl, wgt) in enumerate(labels_widgets):
            row, col = divmod(i, 2)
            grid.addWidget(QtWidgets.QLabel(lbl+":", styleSheet=_LABEL), row, col*2)
            grid.addWidget(wgt, row, col*2+1)
        root.addLayout(grid)

        br = QtWidgets.QHBoxLayout()
        btn_run = _sb("▶  运行回测", _GRN); btn_run.clicked.connect(self._on_run)
        btn_exp = _sb("↑  导出CSV", _BLU); btn_exp.clicked.connect(self._on_export)
        br.addWidget(btn_run); br.addWidget(btn_exp); br.addStretch()
        root.addLayout(br)
        root.addWidget(self._sep())

        # ── 绩效指标卡片 ──────────────────────────────────────────────
        root.addWidget(self._sec("绩效指标"))
        cards_row = QtWidgets.QHBoxLayout()
        self._c_ret    = MetricCard("累计收益")
        self._c_ann    = MetricCard("年化收益")
        self._c_dd     = MetricCard("最大回撤")
        self._c_sharpe = MetricCard("Sharpe")
        self._c_calmar = MetricCard("Calmar")
        self._c_win    = MetricCard("胜率")
        for c in [self._c_ret, self._c_ann, self._c_dd,
                  self._c_sharpe, self._c_calmar, self._c_win]:
            cards_row.addWidget(c)
        cards_row.addStretch()
        root.addLayout(cards_row)
        root.addWidget(self._sep())

        # ── 净值曲线（文本模拟）───────────────────────────────────────
        root.addWidget(self._sec("净值曲线（最近 60 日）"))
        self._nav_text = QtWidgets.QPlainTextEdit()
        self._nav_text.setReadOnly(True)
        self._nav_text.setStyleSheet(
            f"background:{_PANEL2};color:{_MUT};border:1px solid {_BORDER};"
            f"border-radius:3px;font-family:monospace;font-size:10px;")
        self._nav_text.setMaximumHeight(110)
        self._nav_text.setPlaceholderText("回测完成后显示净值曲线…")
        root.addWidget(self._nav_text)

        # ── 状态栏 ────────────────────────────────────────────────────
        self._sl = QtWidgets.QLabel("等待回测…")
        self._sl.setStyleSheet(f"color:{_MUT};font-size:10px;")
        root.addWidget(self._sl)
        root.addStretch()

    # ── 事件回调 ──────────────────────────────────────────────────────

    def _on_run(self):
        if not self._engine:
            self._sl.setText("引擎未连接"); return
        cfg = self.get_config()
        self._engine.backtest_engine.set_config(cfg)
        screening_result = self._engine.scoring_engine.get_last_result()
        if screening_result and screening_result.stocks:
            symbols = [s.symbol for s in screening_result.stocks]
            scores  = {s.symbol: s.composite_score for s in screening_result.stocks}
        else:
            self._sl.setText("请先运行选股流程再回测")
            return
        self._sl.setText("回测运行中…")
        QtWidgets.QApplication.processEvents()
        result = self._engine.backtest_engine.run_backtest(symbols, scores)
        if result:
            self.update_result(result)
        else:
            self._sl.setText("回测失败，请检查数据")

    def _on_export(self):
        if not self._last_result or not self._last_result.daily_records:
            self._sl.setText("无数据可导出"); return
        import csv, os
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出回测净值", "backtest_nav.csv", "CSV Files (*.csv)")
        if not path: return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["日期", "净值", "日盈亏", "换手"])
                for r in self._last_result.daily_records:
                    w.writerow([r.date, f"{r.nav:.4f}", f"{r.pnl:.6f}",
                                 f"{r.turnover:.1f}"])
            self._sl.setText(f"已导出：{os.path.basename(path)}")
        except Exception as e:
            self._sl.setText(f"导出失败：{e}")

    # ── 数据刷新 ──────────────────────────────────────────────────────

    def update_result(self, result: BacktestResult) -> None:
        self._last_result = result

        def pct(v): return f"{v:.2%}"
        def num(v): return f"{v:.2f}"

        ret_color = _GRN if result.total_return >= 0 else _RED
        self._c_ret.set_value(pct(result.total_return), ret_color)
        ann_color = _GRN if result.annual_return >= 0 else _RED
        self._c_ann.set_value(pct(result.annual_return), ann_color)
        dd_color = _RED if result.max_drawdown_pct > 0.2 else _YLW
        self._c_dd.set_value(pct(result.max_drawdown_pct), dd_color)
        sh_color = _GRN if result.sharpe_ratio > 1.0 else (_YLW if result.sharpe_ratio > 0 else _RED)
        self._c_sharpe.set_value(num(result.sharpe_ratio), sh_color)
        self._c_calmar.set_value(num(result.calmar_ratio),
                                  _GRN if result.calmar_ratio > 1.0 else _MUT)
        self._c_win.set_value(pct(result.win_rate),
                               _GRN if result.win_rate > 0.5 else _MUT)

        # 文字版净值图（ASCII 折线）
        self._render_nav_text(result)

        self._sl.setText(
            f"RunID: {result.run_id}  |  "
            f"{result.total_days} 日  |  {str(result.generated_at)[:19]}"
        )

    def _render_nav_text(self, result: BacktestResult) -> None:
        """用 ASCII 折线展示最近60日净值。"""
        records = result.daily_records[-60:]
        if not records:
            return
        navs = [r.nav for r in records]
        mn, mx = min(navs), max(navs)
        H = 6  # 行高
        rng = mx - mn if mx > mn else 1e-9
        lines = []
        for row in range(H, -1, -1):
            threshold = mn + rng * row / H
            line = ""
            for nav in navs:
                line += "█" if nav >= threshold else " "
            label = f"{threshold:.3f} |" if row % 2 == 0 else "       |"
            lines.append(label + line)
        lines.append("       +" + "-" * len(navs))
        lines.append(f"       {records[0].date[:7]}{'':>20}{records[-1].date[:7]}")
        self._nav_text.setPlainText("\n".join(lines))

    def get_config(self) -> BacktestConfig:
        return BacktestConfig(
            start_date=self._start_edit.text().strip() or "2021-01-01",
            end_date=self._end_edit.text().strip(),
            top_n=self._topn_spin.value(),
            rebalance_days=self._rb_spin.value(),
            commission=self._comm_spin.value(),
            risk_free_rate=self._rf_spin.value(),
        )
