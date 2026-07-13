"""
risk_engine_2/ui/overview_tab.py

OverviewTab — 组合风险仪表盘（Phase 2 实现）。

展示：
  顶部卡片：NAV / 持仓数 / 杠杆 / Beta / 最大单票 / 最大行业
  中部：各标的权重列表
  底部：行业分布条形（ASCII 风格）
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..model.exposure_model import ExposureReport

_DARK_BG  = "#1e1e2e"
_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"

_POS_COLS = [
    ("合约",    100),
    ("行业",     80),
    ("持仓量",   80),
    ("均价",     90),
    ("最新价",   90),
    ("市值",    100),
    ("权重",     70),
    ("Beta",     60),
    ("Beta贡献", 80),
    ("浮动PnL", 100),
]


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    item = QtWidgets.QTableWidgetItem(str(text))
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    item.setForeground(QtGui.QColor(color))
    return item


class OverviewTab(QtWidgets.QWidget):
    """组合风险总览 Tab（Phase 2）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_kpi_bar())
        root.addWidget(self._build_position_table(), stretch=1)
        root.addWidget(self._build_industry_bar())

    # ------------------------------------------------------------------ #
    #  子区域构建
    # ------------------------------------------------------------------ #

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        """顶部 KPI 卡片。"""
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(72)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(24)

        metrics = [
            ("净值 NAV",      "—",   _FG),
            ("持仓标的数",    "0",   _FG),
            ("杠杆率",        "—",   _BLU),
            ("组合 Beta",     "—",   _BLU),
            ("最大单票",      "—",   _YLW),
            ("最大行业",      "—",   _YLW),
            ("总浮动 PnL",    "—",   _GRN),
        ]
        self._kpi_lbls: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in metrics:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(1)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._kpi_lbls[name] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_position_table(self) -> QtWidgets.QTableWidget:
        self._tbl = QtWidgets.QTableWidget(0, len(_POS_COLS))
        self._tbl.setHorizontalHeaderLabels([c[0] for c in _POS_COLS])
        for i, (_, w) in enumerate(_POS_COLS):
            self._tbl.setColumnWidth(i, w)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._tbl.setStyleSheet("font-size: 12px;")
        return self._tbl

    def _build_industry_bar(self) -> QtWidgets.QWidget:
        """底部行业分布（纯文本 bar chart）。"""
        w = QtWidgets.QWidget()
        w.setFixedHeight(90)
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(10, 6, 10, 6)

        lbl = QtWidgets.QLabel("行业分布")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._lbl_industry = QtWidgets.QLabel("—")
        self._lbl_industry.setStyleSheet(
            f"color: {_FG}; font-size: 11px; font-family: monospace;"
        )
        self._lbl_industry.setWordWrap(True)
        v.addWidget(self._lbl_industry)
        return w

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_exposure(self, report: ExposureReport) -> None:
        """刷新所有展示内容（每次 EVENT_RISK_UPDATE 后调用）。"""
        self._update_kpi(report)
        self._update_table(report)
        self._update_industry(report)

    def clear(self) -> None:
        self._tbl.setRowCount(0)
        for lbl in self._kpi_lbls.values():
            lbl.setText("—")

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _update_kpi(self, r: ExposureReport) -> None:
        lev_color = _RED if r.leverage > 2.0 else (_YLW if r.leverage > 1.5 else _BLU)
        beta_color = _RED if abs(r.portfolio_beta) > 1.2 else (
            _YLW if abs(r.portfolio_beta) > 0.8 else _BLU)

        self._kpi_lbls["净值 NAV"   ].setText(f"{r.nav:,.0f}")
        self._kpi_lbls["持仓标的数" ].setText(str(r.position_count))
        self._kpi_lbls["杠杆率"     ].setText(f"{r.leverage:.2f}x")
        self._kpi_lbls["杠杆率"     ].setStyleSheet(
            f"color: {lev_color}; font-size: 14px; font-weight: bold;"
        )
        self._kpi_lbls["组合 Beta"  ].setText(f"{r.portfolio_beta:.3f}")
        self._kpi_lbls["组合 Beta"  ].setStyleSheet(
            f"color: {beta_color}; font-size: 14px; font-weight: bold;"
        )
        sym_str = f"{r.max_single_symbol}  {r.max_single_weight:.1%}" \
                  if r.max_single_symbol else "—"
        self._kpi_lbls["最大单票"   ].setText(sym_str)
        ind_str = f"{r.max_industry_name}  {r.max_industry_weight:.1%}" \
                  if r.max_industry_name else "—"
        self._kpi_lbls["最大行业"   ].setText(ind_str)

    def _update_table(self, r: ExposureReport) -> None:
        """刷新持仓明细表格。"""
        from ..model.exposure_model import PositionSnapshot
        self._tbl.setRowCount(0)

        snapshot = getattr(r, "_snapshot", None)
        positions = getattr(snapshot, "positions", {}) if snapshot else {}

        for sym, w in sorted(r.symbol_weights.items(),
                              key=lambda kv: abs(kv[1]), reverse=True):
            row = self._tbl.rowCount()
            self._tbl.insertRow(row)
            beta   = r.beta_contributions.get(sym, 0.0)
            w_color = _RED if abs(w) > 0.25 else (_YLW if abs(w) > 0.15 else _FG)

            self._tbl.setItem(row, 0, _item(sym,            _FG))
            self._tbl.setItem(row, 1, _item("—",            _MUT))
            self._tbl.setItem(row, 2, _item("—",            _FG))
            self._tbl.setItem(row, 3, _item("—",            _FG))
            self._tbl.setItem(row, 4, _item("—",            _FG))
            self._tbl.setItem(row, 5, _item("—",            _FG))
            self._tbl.setItem(row, 6, _item(f"{w:.2%}",  w_color))
            self._tbl.setItem(row, 7, _item("1.0",          _MUT))
            self._tbl.setItem(row, 8, _item(f"{beta:.3f}",  _BLU))
            self._tbl.setItem(row, 9, _item("—",            _FG))

    def _update_industry(self, r: ExposureReport) -> None:
        """行业分布文本 bar chart。"""
        if not r.industry_weights:
            self._lbl_industry.setText("—")
            return

        lines = []
        sorted_inds = sorted(r.industry_weights.items(),
                              key=lambda kv: kv[1], reverse=True)
        for ind, w in sorted_inds[:6]:
            bar_len = int(w * 40)
            bar     = "█" * bar_len
            lines.append(f"{ind[:8]:8s} {bar} {w:.1%}")
        self._lbl_industry.setText("  ".join(lines[:3]) + "\n" + "  ".join(lines[3:]))
