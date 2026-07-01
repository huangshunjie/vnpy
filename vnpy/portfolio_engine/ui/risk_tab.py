"""
portfolio_engine/ui/risk_tab.py

RiskTab — 风险暴露 Tab（Phase 3 实现）。

布局（上下分区）：
┌──────────────────────────────────────────────────────────┐
│  顶部指标行：Beta / Alpha / TE / IR / 分散度              │
├────────────────────────┬─────────────────────────────────┤
│  左上：滚动波动率曲线   │  右上：因子暴露条形图            │
├────────────────────────┼─────────────────────────────────┤
│  左下：相关矩阵热力图   │  右下：行业/策略类型饼图         │
└────────────────────────┴─────────────────────────────────┘
"""

from __future__ import annotations

import math

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

_BG     = "#1e1e2e"
_FG     = "#cdd6f4"
_COLORS = [
    "#4fc3f7", "#a6e3a1", "#f38ba8", "#fab387",
    "#cba6f7", "#f9e2af", "#89dceb", "#b4befe",
]
_HEAT_LOW  = "#313244"   # dark = low correlation
_HEAT_HIGH = "#f38ba8"   # red  = high correlation

_TOP_METRICS = [
    ("Beta",   "portfolio_beta",    "{:.3f}"),
    ("Alpha",  "portfolio_alpha",   "{:.2%}"),
    ("跟踪误差", "tracking_error",  "{:.2%}"),
    ("信息比率", "information_ratio", "{:.3f}"),
]


class RiskTab(QtWidgets.QWidget):
    """风险暴露 Tab（Phase 3 实现）。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._plot_items: list = []
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # 顶部指标行
        root.addWidget(self._build_metrics_bar())

        # 占位
        self._placeholder = QtWidgets.QLabel("运行分析后将在此显示风险暴露")
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #6c7086; font-size: 13px;")
        root.addWidget(self._placeholder, stretch=1)

        # 主内容区（2×2 网格）
        self._content = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(self._content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)

        # 左上：滚动波动率
        self._vol_glw = pg.GraphicsLayoutWidget()
        self._vol_glw.setBackground(_BG)
        self._vol_plot = self._vol_glw.addPlot(title="滚动年化波动率（21日）")
        self._vol_plot.setLabel("left", "年化波动率")
        self._vol_plot.showGrid(x=True, y=True, alpha=0.2)
        grid.addWidget(self._vol_glw, 0, 0)

        # 右上：因子暴露条形图
        self._factor_glw = pg.GraphicsLayoutWidget()
        self._factor_glw.setBackground(_BG)
        self._factor_plot = self._factor_glw.addPlot(title="因子暴露")
        self._factor_plot.setLabel("left", "暴露值")
        self._factor_plot.showGrid(y=True, alpha=0.2)
        grid.addWidget(self._factor_glw, 0, 1)

        # 左下：相关矩阵热力图（用 QTableWidget 模拟）
        left_bottom = QtWidgets.QVBoxLayout()
        lbl_corr = QtWidgets.QLabel("策略相关矩阵")
        lbl_corr.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: bold;")
        left_bottom.addWidget(lbl_corr)
        self._corr_table = QtWidgets.QTableWidget(0, 0)
        self._corr_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self._corr_table.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self._corr_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._corr_table.setStyleSheet("font-size: 11px;")
        left_bottom.addWidget(self._corr_table, stretch=1)
        left_w = QtWidgets.QWidget()
        left_w.setLayout(left_bottom)
        grid.addWidget(left_w, 1, 0)

        # 右下：行业/策略类型分布条形图
        self._sector_glw = pg.GraphicsLayoutWidget()
        self._sector_glw.setBackground(_BG)
        self._sector_plot = self._sector_glw.addPlot(title="策略类型分布")
        self._sector_plot.setLabel("left", "权重")
        self._sector_plot.showGrid(y=True, alpha=0.2)
        grid.addWidget(self._sector_glw, 1, 1)

        grid.setRowStretch(0, 3)
        grid.setRowStretch(1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self._content.hide()
        root.addWidget(self._content, stretch=1)

    def _build_metrics_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setStyleSheet("background: #181825; border-radius: 4px;")
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(16)

        self._metric_labels: dict[str, QtWidgets.QLabel] = {}
        for label, key, _ in _TOP_METRICS:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(0)
            lbl_name = QtWidgets.QLabel(label)
            lbl_name.setStyleSheet("color: #6c7086; font-size: 10px;")
            lbl_name.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lbl_val = QtWidgets.QLabel("—")
            lbl_val.setStyleSheet(f"color: {_FG}; font-size: 14px; font-weight: bold;")
            lbl_val.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl_name)
            col.addWidget(lbl_val)
            self._metric_labels[key] = lbl_val
            layout.addLayout(col)

        # 分散度单独显示（来自 factor_exposures）
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(0)
        lbl_name = QtWidgets.QLabel("分散度")
        lbl_name.setStyleSheet("color: #6c7086; font-size: 10px;")
        lbl_name.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._lbl_divers = QtWidgets.QLabel("—")
        self._lbl_divers.setStyleSheet(
            f"color: {_FG}; font-size: 14px; font-weight: bold;"
        )
        self._lbl_divers.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        col.addWidget(lbl_name)
        col.addWidget(self._lbl_divers)
        layout.addLayout(col)

        return bar

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_risk(self, exposure) -> None:
        """接收 RiskExposure，刷新所有子图和指标行。"""
        self._update_metrics(exposure)

        if exposure.rolling_vol_series is not None:
            self._draw_rolling_vol(exposure.rolling_vol_series)

        if exposure.factor_exposures:
            self._draw_factor_bars(exposure.factor_exposures)

        if exposure.correlation_matrix is not None and \
                not exposure.correlation_matrix.empty:
            self._draw_corr_matrix(exposure.correlation_matrix)

        if exposure.sector_weights:
            self._draw_sector_bars(exposure.sector_weights)

        self._placeholder.hide()
        self._content.show()

    def clear(self) -> None:
        for lbl in self._metric_labels.values():
            lbl.setText("—")
        self._lbl_divers.setText("—")
        self._vol_plot.clear()
        self._factor_plot.clear()
        self._sector_plot.clear()
        self._corr_table.setRowCount(0)
        self._corr_table.setColumnCount(0)
        self._content.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  内部绘图方法
    # ------------------------------------------------------------------ #

    def _update_metrics(self, exposure) -> None:
        for _, key, fmt in _TOP_METRICS:
            val = getattr(exposure, key, float("nan"))
            lbl = self._metric_labels[key]
            if val is None or (isinstance(val, float) and math.isnan(val)):
                lbl.setText("—")
                lbl.setStyleSheet(
                    f"color: {_FG}; font-size: 14px; font-weight: bold;"
                )
                continue
            text  = fmt.format(val)
            color = _FG
            if key == "portfolio_beta":
                # β 越接近 0，颜色越绿；绝对值越大越橙
                color = "#a6e3a1" if abs(val) < 0.3 else (
                    "#f9e2af" if abs(val) < 0.7 else "#f38ba8"
                )
            elif key in ("portfolio_alpha", "information_ratio"):
                color = "#a6e3a1" if val >= 0 else "#f38ba8"
            lbl.setText(text)
            lbl.setStyleSheet(
                f"color: {color}; font-size: 14px; font-weight: bold;"
            )

        # 分散度
        d = exposure.factor_exposures.get("Diversification", float("nan")) \
            if exposure.factor_exposures else float("nan")
        if not math.isnan(d):
            color = "#a6e3a1" if d >= 0.7 else (
                "#f9e2af" if d >= 0.4 else "#f38ba8"
            )
            self._lbl_divers.setText(f"{d:.3f}")
            self._lbl_divers.setStyleSheet(
                f"color: {color}; font-size: 14px; font-weight: bold;"
            )

    def _draw_rolling_vol(self, rv_series) -> None:
        import pandas as pd
        self._vol_plot.clear()
        rv = rv_series.dropna()
        if rv.empty:
            return
        xs = [ts.timestamp() for ts in pd.to_datetime(rv.index)]
        ys = rv.values.tolist()
        self._vol_plot.plot(xs, ys, pen=pg.mkPen("#fab387", width=1.5))

    def _draw_factor_bars(self, factor_exposures: dict[str, float]) -> None:
        self._factor_plot.clear()
        items = [
            (k, v) for k, v in factor_exposures.items()
            if not math.isnan(v)
        ]
        if not items:
            return
        names  = [it[0] for it in items]
        values = [it[1] for it in items]
        n = len(names)
        colors = [_COLORS[i % len(_COLORS)] for i in range(n)]
        bar = pg.BarGraphItem(
            x=list(range(n)),
            height=values,
            width=0.6,
            brushes=[pg.mkBrush(c) for c in colors],
        )
        self._factor_plot.addItem(bar)
        ax = self._factor_plot.getAxis("bottom")
        ax.setTicks([[(i, names[i]) for i in range(n)]])
        self._factor_plot.setXRange(-0.5, n - 0.5)

    def _draw_corr_matrix(self, corr_df) -> None:
        names = list(corr_df.columns)
        n = len(names)
        self._corr_table.setRowCount(n)
        self._corr_table.setColumnCount(n)
        self._corr_table.setHorizontalHeaderLabels(names)
        self._corr_table.setVerticalHeaderLabels(names)

        for i in range(n):
            for j in range(n):
                val = float(corr_df.iloc[i, j])
                item = QtWidgets.QTableWidgetItem(f"{val:.2f}")
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

                # 热力着色：abs(corr) 越大越红
                intensity = min(abs(val), 1.0)
                # 从 #313244 (dark) → #f38ba8 (red)
                r = int(0x31 + intensity * (0xf3 - 0x31))
                g = int(0x32 + intensity * (0x8b - 0x32))
                b = int(0x44 + intensity * (0xa8 - 0x44))
                bg = QtGui.QColor(r, g, b)
                # 对角线用金色
                if i == j:
                    bg = QtGui.QColor("#f9e2af")

                item.setBackground(bg)
                # 深色背景用白字
                luma = 0.299 * r + 0.587 * g + 0.114 * b
                item.setForeground(
                    QtGui.QColor("#cdd6f4") if luma < 128 else QtGui.QColor("#1e1e2e")
                )
                self._corr_table.setItem(i, j, item)

    def _draw_sector_bars(self, sector_weights: dict[str, float]) -> None:
        self._sector_plot.clear()
        items = sorted(sector_weights.items(), key=lambda x: x[1], reverse=True)
        if not items:
            return
        names  = [it[0] for it in items]
        values = [it[1] for it in items]
        n = len(names)
        colors = [_COLORS[i % len(_COLORS)] for i in range(n)]
        bar = pg.BarGraphItem(
            x=list(range(n)),
            height=values,
            width=0.6,
            brushes=[pg.mkBrush(c) for c in colors],
        )
        self._sector_plot.addItem(bar)
        ax = self._sector_plot.getAxis("bottom")
        ax.setTicks([[(i, names[i]) for i in range(n)]])
        self._sector_plot.setXRange(-0.5, n - 0.5)
        self._sector_plot.setYRange(0, max(values) * 1.2 if values else 1)
