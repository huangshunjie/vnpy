"""
portfolio_engine/ui/attribution_tab.py

AttributionTab — 回撤归因 Tab（Phase 3 实现）。

布局：
┌────────────────────────────────────────────────────────┐
│  顶部摘要行：最大回撤区间 / 总回撤 / 市场贡献            │
├────────────────────────┬───────────────────────────────┤
│  左：净值曲线（标注     │  右：槽位贡献条形图            │
│      peak/trough区间）  │      （正负着色）              │
└────────────────────────┴───────────────────────────────┘
│  底部：槽位贡献明细表格                                  │
└────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import math

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

_BG      = "#1e1e2e"
_FG      = "#cdd6f4"
_NAV_CLR = "#4fc3f7"
_PEAK    = "#a6e3a1"   # 峰值标注色
_TROUGH  = "#f38ba8"   # 谷值标注色
_POS_CLR = "#a6e3a1"   # 正贡献（减少回撤）
_NEG_CLR = "#f38ba8"   # 负贡献（加剧回撤）


class AttributionTab(QtWidgets.QWidget):
    """回撤归因 Tab（Phase 3 实现）。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._nav_series = None
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # 顶部摘要行
        root.addWidget(self._build_summary_bar())

        # 占位
        self._placeholder = QtWidgets.QLabel("运行分析后将在此显示回撤归因")
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #6c7086; font-size: 13px;")
        root.addWidget(self._placeholder, stretch=1)

        # 主内容区
        self._content = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(self._content)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)

        # 上区：图表行
        charts_row = QtWidgets.QHBoxLayout()
        charts_row.setSpacing(4)

        # 左：净值曲线（带区间标注）
        self._nav_glw = pg.GraphicsLayoutWidget()
        self._nav_glw.setBackground(_BG)
        self._nav_plot = self._nav_glw.addPlot(title="净值曲线（最大回撤区间）")
        self._nav_plot.setLabel("left", "净值")
        self._nav_plot.showGrid(x=True, y=True, alpha=0.2)
        charts_row.addWidget(self._nav_glw, stretch=3)

        # 右：槽位贡献条形图
        self._bar_glw = pg.GraphicsLayoutWidget()
        self._bar_glw.setBackground(_BG)
        self._bar_plot = self._bar_glw.addPlot(title="槽位回撤贡献")
        self._bar_plot.setLabel("left", "贡献")
        self._bar_plot.showGrid(y=True, alpha=0.2)
        self._bar_plot.addLine(
            y=0, pen=pg.mkPen("#45475a", width=1)
        )
        charts_row.addWidget(self._bar_glw, stretch=2)

        v.addLayout(charts_row, stretch=3)

        # 下区：明细表格
        tbl_header = QtWidgets.QLabel("槽位贡献明细")
        tbl_header.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: bold;")
        v.addWidget(tbl_header)

        self._detail_table = QtWidgets.QTableWidget(0, 5)
        self._detail_table.setHorizontalHeaderLabels(
            ["槽位", "权重", "区间累计收益", "回撤贡献", "贡献占比"]
        )
        hdr = self._detail_table.horizontalHeader()
        hdr.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._detail_table.verticalHeader().setVisible(False)
        self._detail_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._detail_table.setFixedHeight(160)
        self._detail_table.setStyleSheet("font-size: 12px;")
        v.addWidget(self._detail_table, stretch=2)

        self._content.hide()
        root.addWidget(self._content, stretch=1)

    def _build_summary_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setStyleSheet("background: #181825; border-radius: 4px;")
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(24)

        def _add_metric(label_text: str) -> QtWidgets.QLabel:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(0)
            lbl_name = QtWidgets.QLabel(label_text)
            lbl_name.setStyleSheet("color: #6c7086; font-size: 10px;")
            lbl_name.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lbl_val = QtWidgets.QLabel("—")
            lbl_val.setStyleSheet(
                f"color: {_FG}; font-size: 14px; font-weight: bold;"
            )
            lbl_val.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl_name)
            col.addWidget(lbl_val)
            layout.addLayout(col)
            return lbl_val

        self._lbl_peak     = _add_metric("回撤开始（峰值）")
        self._lbl_trough   = _add_metric("回撤结束（谷值）")
        self._lbl_total_dd = _add_metric("区间总回撤")
        self._lbl_mkt      = _add_metric("市场系统性贡献")
        return bar

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_attribution(self, result, nav_series=None) -> None:
        """
        接收 AttributionResult（+ 可选净值序列），刷新所有图表和表格。
        """
        self._update_summary(result)

        if nav_series is not None:
            self._nav_series = nav_series
            self._draw_nav(nav_series, result)

        self._draw_contribution_bars(result)
        self._fill_detail_table(result)

        self._placeholder.hide()
        self._content.show()

    def clear(self) -> None:
        self._lbl_peak.setText("—")
        self._lbl_trough.setText("—")
        self._lbl_total_dd.setText("—")
        self._lbl_mkt.setText("—")
        self._nav_plot.clear()
        self._bar_plot.clear()
        self._bar_plot.addLine(y=0, pen=pg.mkPen("#45475a", width=1))
        self._detail_table.setRowCount(0)
        self._nav_series = None
        self._content.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  内部方法
    # ------------------------------------------------------------------ #

    def _update_summary(self, result) -> None:
        if result.drawdown_start:
            self._lbl_peak.setText(
                result.drawdown_start.strftime("%Y-%m-%d")
            )
            self._lbl_peak.setStyleSheet(
                f"color: {_PEAK}; font-size: 14px; font-weight: bold;"
            )
        if result.drawdown_end:
            self._lbl_trough.setText(
                result.drawdown_end.strftime("%Y-%m-%d")
            )
            self._lbl_trough.setStyleSheet(
                f"color: {_TROUGH}; font-size: 14px; font-weight: bold;"
            )

        dd = result.total_drawdown
        if not math.isnan(dd):
            self._lbl_total_dd.setText(f"{dd:.2%}")
            self._lbl_total_dd.setStyleSheet(
                f"color: {_TROUGH}; font-size: 14px; font-weight: bold;"
            )

        mkt = result.market_contribution
        if not math.isnan(mkt):
            color = _NEG_CLR if mkt < 0 else _POS_CLR
            self._lbl_mkt.setText(f"{mkt:.2%}")
            self._lbl_mkt.setStyleSheet(
                f"color: {color}; font-size: 14px; font-weight: bold;"
            )

    def _draw_nav(self, nav_series, result) -> None:
        import pandas as pd
        self._nav_plot.clear()
        nav = nav_series.dropna()
        if nav.empty:
            return

        xs = [ts.timestamp() for ts in pd.to_datetime(nav.index)]
        ys = nav.values.tolist()
        self._nav_plot.plot(xs, ys, pen=pg.mkPen(_NAV_CLR, width=2))

        # 标注最大回撤区间
        if result.drawdown_start and result.drawdown_end:
            x0 = result.drawdown_start.timestamp()
            x1 = result.drawdown_end.timestamp()

            # 区间阴影
            yr   = [min(ys) * 0.995, max(ys) * 1.005]
            fill = pg.LinearRegionItem(
                values=[x0, x1],
                brush=pg.mkBrush(_TROUGH + "33"),
                movable=False,
            )
            self._nav_plot.addItem(fill)

            # Peak / Trough 竖线
            self._nav_plot.addLine(
                x=x0,
                pen=pg.mkPen(_PEAK, width=1,
                             style=QtCore.Qt.PenStyle.DashLine),
                label="Peak",
                labelOpts={"color": _PEAK, "position": 0.9},
            )
            self._nav_plot.addLine(
                x=x1,
                pen=pg.mkPen(_TROUGH, width=1,
                             style=QtCore.Qt.PenStyle.DashLine),
                label="Trough",
                labelOpts={"color": _TROUGH, "position": 0.9},
            )

    def _draw_contribution_bars(self, result) -> None:
        self._bar_plot.clear()
        self._bar_plot.addLine(y=0, pen=pg.mkPen("#45475a", width=1))

        contribs = [
            sc for sc in result.slot_contributions
            if not math.isnan(sc.contribution)
        ]
        if not contribs:
            return

        contribs_sorted = sorted(contribs, key=lambda x: x.contribution)
        names  = [sc.slot_name   for sc in contribs_sorted]
        values = [sc.contribution for sc in contribs_sorted]
        n      = len(names)

        brushes = [
            pg.mkBrush(_NEG_CLR if v < 0 else _POS_CLR)
            for v in values
        ]
        bar = pg.BarGraphItem(
            x=list(range(n)),
            height=values,
            width=0.6,
            brushes=brushes,
        )
        self._bar_plot.addItem(bar)
        ax = self._bar_plot.getAxis("bottom")
        ax.setTicks([[(i, names[i]) for i in range(n)]])
        self._bar_plot.setXRange(-0.5, n - 0.5)

    def _fill_detail_table(self, result) -> None:
        self._detail_table.setRowCount(0)

        total_dd = result.total_drawdown
        for sc in sorted(
            result.slot_contributions, key=lambda x: x.contribution
        ):
            row = self._detail_table.rowCount()
            self._detail_table.insertRow(row)

            contrib = sc.contribution
            cum_ret = getattr(sc, "cumulative_return", float("nan"))
            pct_of_total = (
                contrib / total_dd
                if not math.isnan(total_dd) and abs(total_dd) > 1e-10
                else float("nan")
            )

            color = _NEG_CLR if contrib < 0 else _POS_CLR

            self._detail_table.setItem(row, 0, _item(sc.slot_name))
            self._detail_table.setItem(row, 1, _item(f"{sc.weight:.2%}"))
            self._detail_table.setItem(
                row, 2,
                _item(f"{cum_ret:.2%}" if not math.isnan(cum_ret) else "—")
            )
            contrib_item = _item(
                f"{contrib:.2%}" if not math.isnan(contrib) else "—"
            )
            contrib_item.setForeground(pg.mkColor(color))
            self._detail_table.setItem(row, 3, contrib_item)
            self._detail_table.setItem(
                row, 4,
                _item(f"{pct_of_total:.1%}" if not math.isnan(pct_of_total) else "—")
            )


def _item(text: str) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(str(text))
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    return item
