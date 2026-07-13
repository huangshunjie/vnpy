"""
risk_engine_2/ui/drawdown_tab.py

DrawdownTab — 实时回撤曲线 + PnL 卡片（Phase 3 实现）。

顶部：PnL / 回撤关键指标卡片
中部：ASCII 文本 PnL 曲线（不依赖 matplotlib）
底部：回撤阈值配置表单
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..model.drawdown_model import DrawdownState

_DARK_BG  = "#1e1e2e"
_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"

_INPUT_STYLE = (
    "QDoubleSpinBox {{ background: #313244; color: #cdd6f4;"
    " border: 1px solid #45475a; border-radius: 3px;"
    " padding: 2px 6px; font-size: 12px; }}"
)


class DrawdownTab(QtWidgets.QWidget):
    """实时回撤 Tab（Phase 3）。"""

    thresholds_changed = QtCore.Signal(float, float, float, float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._state: DrawdownState | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_kpi_bar())

        mid = QtWidgets.QHBoxLayout()
        mid.setSpacing(6)
        mid.addWidget(self._build_chart_area(), stretch=1)
        mid.addWidget(self._build_config_panel(), stretch=0)
        root.addLayout(mid, stretch=1)

    # ------------------------------------------------------------------ #
    #  子区域构建
    # ------------------------------------------------------------------ #

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(72)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(24)

        metrics = [
            ("当前 PnL",     "—",  _FG),
            ("浮动 PnL",     "—",  _FG),
            ("已实现 PnL",   "—",  _GRN),
            ("峰值 PnL",     "—",  _BLU),
            ("当前回撤",     "—",  _YLW),
            ("当前回撤%",    "—",  _YLW),
            ("最大回撤",     "—",  _RED),
            ("最大回撤%",    "—",  _RED),
            ("当日亏损%",    "—",  _RED),
        ]
        self._kpi: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in metrics:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(1)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._kpi[name] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_chart_area(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(10, 8, 10, 8)

        lbl = QtWidgets.QLabel("PnL 时间序列（最近 60 个快照）")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._chart = QtWidgets.QTextEdit()
        self._chart.setReadOnly(True)
        self._chart.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_GRN};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._chart)
        return w

    def _build_config_panel(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("回撤阈值配置")
        box.setFixedWidth(230)
        box.setStyleSheet(
            f"QGroupBox {{ color: {_FG}; font-size: 12px; font-weight: bold;"
            f" border: 1px solid {_BORDER}; border-radius: 4px; margin-top: 6px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; padding: 0 4px; }}"
        )
        form = QtWidgets.QFormLayout(box)
        form.setContentsMargins(10, 18, 10, 10)
        form.setSpacing(7)
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        ls = f"color: {_MUT}; font-size: 11px;"

        self._spn_dd_warn  = self._dbl(0.01, 0.5, 0.05)
        self._spn_dd_limit = self._dbl(0.01, 0.5, 0.10)
        self._spn_dl_warn  = self._dbl(0.01, 0.5, 0.03)
        self._spn_dl_limit = self._dbl(0.01, 0.5, 0.05)

        form.addRow(self._lbl("回撤预警线：",  ls), self._spn_dd_warn)
        form.addRow(self._lbl("回撤硬限制：",  ls), self._spn_dd_limit)
        form.addRow(self._lbl("日亏损预警：",  ls), self._spn_dl_warn)
        form.addRow(self._lbl("日亏损限制：",  ls), self._spn_dl_limit)

        btn = QtWidgets.QPushButton("应用")
        btn.setStyleSheet(
            f"QPushButton {{ background: {_BLU}; color: #1e1e2e; border-radius: 4px;"
            f" padding: 5px; font-size: 12px; font-weight: bold; }}"
        )
        btn.clicked.connect(self._apply_thresholds)
        form.addRow(btn)
        return box

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_state(self, state: DrawdownState) -> None:
        """刷新回撤状态（每次 EVENT_RISK_DRAWDOWN 后调用）。"""
        self._state = state
        self._update_kpi(state)
        self._update_chart(state)

    def clear(self) -> None:
        for lbl in self._kpi.values():
            lbl.setText("—")
        self._chart.clear()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _update_kpi(self, s: DrawdownState) -> None:
        def fmt(v): return f"{v:+.2f}"
        def pct(v): return f"{v:.2%}"

        total_pnl = s.current_pnl
        pnl_color = _GRN if total_pnl >= 0 else _RED
        dd_color  = _RED if s.current_drawdown_pct >= 0.05 else (
                    _YLW if s.current_drawdown_pct > 0 else _GRN)
        max_color = _RED if s.max_drawdown_pct >= 0.10 else _YLW

        realized   = s.pnl_series[-1].realized_pnl   if s.pnl_series else 0.0
        unrealized = s.pnl_series[-1].unrealized_pnl if s.pnl_series else 0.0

        self._kpi["当前 PnL"  ].setText(fmt(total_pnl))
        self._kpi["当前 PnL"  ].setStyleSheet(
            f"color: {pnl_color}; font-size: 13px; font-weight: bold;"
        )
        self._kpi["浮动 PnL"  ].setText(fmt(unrealized))
        self._kpi["已实现 PnL"].setText(fmt(realized))
        self._kpi["峰值 PnL"  ].setText(fmt(s.peak_pnl))
        self._kpi["当前回撤"  ].setText(fmt(-s.current_drawdown))
        self._kpi["当前回撤%" ].setText(pct(s.current_drawdown_pct))
        self._kpi["当前回撤%" ].setStyleSheet(
            f"color: {dd_color}; font-size: 13px; font-weight: bold;"
        )
        self._kpi["最大回撤"  ].setText(fmt(-s.max_drawdown))
        self._kpi["最大回撤%" ].setText(pct(s.max_drawdown_pct))
        self._kpi["最大回撤%" ].setStyleSheet(
            f"color: {max_color}; font-size: 13px; font-weight: bold;"
        )
        dl_color = _RED if s.daily_loss_pct >= 0.05 else (
                   _YLW if s.daily_loss_pct >= 0.03 else _GRN)
        self._kpi["当日亏损%" ].setText(pct(s.daily_loss_pct))
        self._kpi["当日亏损%" ].setStyleSheet(
            f"color: {dl_color}; font-size: 13px; font-weight: bold;"
        )

    def _update_chart(self, s: DrawdownState) -> None:
        """用 ASCII 文本绘制 PnL 折线图（最近 60 个点）。"""
        series = s.pnl_series[-60:]
        if not series:
            self._chart.setText("暂无数据")
            return

        values = [snap.total_pnl for snap in series]
        lo, hi = min(values), max(values)
        span   = hi - lo if hi != lo else 1.0
        height = 12   # 行数

        rows = []
        for row_i in range(height, -1, -1):
            threshold = lo + span * row_i / height
            line = ""
            for v in values:
                norm = (v - lo) / span * height
                if abs(norm - row_i) <= 0.5:
                    line += "●"
                elif v >= threshold and row_i == 0:
                    line += "─"
                else:
                    line += " "
            label = f"{threshold:+9.1f} │{line}"
            rows.append(label)

        rows.append(f"{'':10} └{'─' * len(values)}")
        ts_row = "  ".join(
            s.ts_str for s in series[::max(1, len(series)//6)]
        )
        rows.append(f"{'':11}{ts_row}")

        self._chart.setText("\n".join(rows))

    def _apply_thresholds(self) -> None:
        self.thresholds_changed.emit(
            self._spn_dd_warn.value(),
            self._spn_dd_limit.value(),
            self._spn_dl_warn.value(),
            self._spn_dl_limit.value(),
        )

    @staticmethod
    def _lbl(text, style):
        l = QtWidgets.QLabel(text)
        l.setStyleSheet(style)
        return l

    @staticmethod
    def _dbl(lo, hi, val):
        spn = QtWidgets.QDoubleSpinBox()
        spn.setRange(lo, hi)
        spn.setValue(val)
        spn.setDecimals(2)
        spn.setSingleStep(0.01)
        spn.setStyleSheet(
            "QDoubleSpinBox { background: #313244; color: #cdd6f4;"
            " border: 1px solid #45475a; border-radius: 3px;"
            " padding: 2px 6px; font-size: 12px; }"
        )
        return spn
