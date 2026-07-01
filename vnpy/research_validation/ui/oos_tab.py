"""
research_validation/ui/oos_tab.py

OOSTab — Out-of-Sample Testing 结果展示（Phase 2 实现）。

顶部：IS / OOS 对比 KPI 卡片（IC / Sharpe / 过拟合比率）
中部：IS vs OOS 指标对比面板 + 过拟合评估
底部：前视偏差检测结果
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

_DARK_BG  = "#1e1e2e"
_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_ORG      = "#fab387"


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    it.setForeground(QtGui.QColor(color))
    return it


class OOSTab(QtWidgets.QWidget):
    """Out-of-Sample Testing 结果展示 Tab（Phase 2）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._result = None
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_kpi_bar())

        mid = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        mid.addWidget(self._build_compare_panel())
        mid.addWidget(self._build_verdict_panel())
        mid.setSizes([520, 360])
        root.addWidget(mid, stretch=1)

        root.addWidget(self._build_lookahead_bar())

    # ------------------------------------------------------------------ #
    #  子区域构建
    # ------------------------------------------------------------------ #

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(72)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(14, 6, 14, 6)
        h.setSpacing(24)

        kpis = [
            ("IS IC",          "—", _FG),
            ("OOS IC",         "—", _BLU),
            ("IS Sharpe",      "—", _FG),
            ("OOS Sharpe",     "—", _BLU),
            ("过拟合比率",      "—", _YLW),
            ("IS 样本数",      "—", _MUT),
            ("OOS 样本数",     "—", _MUT),
            ("Alpha 评判",     "待验证", _MUT),
        ]
        self._kpi: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in kpis:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(1)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(
                f"color: {color}; font-size: 12px; font-weight: bold;"
            )
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._kpi[name] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_compare_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(4)

        lbl = QtWidgets.QLabel("样本内 vs 样本外 详细对比")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        tbl = QtWidgets.QTableWidget(6, 3)
        tbl.setHorizontalHeaderLabels(["指标", "样本内（IS）", "样本外（OOS）"])
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setColumnWidth(0, 120)
        tbl.setColumnWidth(1, 110)
        tbl.setColumnWidth(2, 110)
        tbl.setStyleSheet("font-size: 12px;")
        self._tbl_compare = tbl

        rows = ["IC 均值", "IC 标准差", "IC IR", "IC t-stat",
                "IC 胜率", "Sharpe Ratio"]
        for i, r in enumerate(rows):
            tbl.setItem(i, 0, _item(r, _MUT))
            tbl.setItem(i, 1, _item("—", _FG))
            tbl.setItem(i, 2, _item("—", _BLU))

        v.addWidget(tbl, stretch=1)
        return w

    def _build_verdict_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(8)

        lbl = QtWidgets.QLabel("Alpha 真实性评估")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        # 大号判断标签
        self._lbl_verdict = QtWidgets.QLabel("—")
        self._lbl_verdict.setStyleSheet(
            f"color: {_MUT}; font-size: 20px; font-weight: bold;"
        )
        self._lbl_verdict.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self._lbl_verdict)

        # 过拟合比率 bar
        self._txt_detail = QtWidgets.QTextEdit()
        self._txt_detail.setReadOnly(True)
        self._txt_detail.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt_detail, stretch=1)
        return w

    def _build_lookahead_bar(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(40)
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(12, 6, 12, 6)

        lbl_title = QtWidgets.QLabel("前视偏差检测：")
        lbl_title.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        h.addWidget(lbl_title)

        self._lbl_lookahead = QtWidgets.QLabel("未检测")
        self._lbl_lookahead.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        h.addWidget(self._lbl_lookahead)
        h.addStretch()
        return w

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_result(self, result) -> None:
        """接收 OOSResult 并刷新 UI。"""
        self._result = result
        self._update_kpi(result)
        self._update_compare(result)
        self._update_verdict(result)

    def set_lookahead_status(self, violations: list[dict]) -> None:
        """刷新前视偏差检测状态。"""
        if not violations:
            self._lbl_lookahead.setText("✔ 无前视偏差")
            self._lbl_lookahead.setStyleSheet(
                f"color: {_GRN}; font-size: 11px; font-weight: bold;"
            )
        else:
            self._lbl_lookahead.setText(
                f"⚠ 发现 {len(violations)} 处前视偏差！"
            )
            self._lbl_lookahead.setStyleSheet(
                f"color: {_RED}; font-size: 11px; font-weight: bold;"
            )

    def clear(self) -> None:
        self._result = None
        for lbl in self._kpi.values():
            lbl.setText("—")
        for row in range(self._tbl_compare.rowCount()):
            self._tbl_compare.setItem(row, 1, _item("—", _FG))
            self._tbl_compare.setItem(row, 2, _item("—", _BLU))
        self._lbl_verdict.setText("—")
        self._txt_detail.clear()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _update_kpi(self, r) -> None:
        oos_ic_color = _GRN if r.oos_ic > 0.02 else (
                       _YLW if r.oos_ic > 0 else _RED)
        of_ratio = r.overfit_ratio
        of_color = _GRN if of_ratio <= 1.5 else (
                   _YLW if of_ratio <= 3.0 else _RED)
        if of_ratio == float("inf"):
            of_str = "∞"
        else:
            of_str = f"{of_ratio:.2f}x"

        alpha_ok = r.oos_ic > 0.01 and of_ratio <= 3.0
        al_color = _GRN if alpha_ok else _RED

        self._kpi["IS IC"      ].setText(f"{r.is_ic:.4f}")
        self._kpi["OOS IC"     ].setText(f"{r.oos_ic:.4f}")
        self._kpi["OOS IC"     ].setStyleSheet(
            f"color: {oos_ic_color}; font-size: 12px; font-weight: bold;"
        )
        self._kpi["IS Sharpe"  ].setText(f"{r.is_sharpe:.3f}")
        self._kpi["OOS Sharpe" ].setText(f"{r.oos_sharpe:.3f}")
        self._kpi["过拟合比率" ].setText(of_str)
        self._kpi["过拟合比率" ].setStyleSheet(
            f"color: {of_color}; font-size: 12px; font-weight: bold;"
        )
        is_n  = getattr(r, "is_n",  "—")
        oos_n = getattr(r, "oos_n", "—")
        self._kpi["IS 样本数"  ].setText(str(is_n))
        self._kpi["OOS 样本数" ].setText(str(oos_n))
        self._kpi["Alpha 评判" ].setText("真实" if alpha_ok else "可疑")
        self._kpi["Alpha 评判" ].setStyleSheet(
            f"color: {al_color}; font-size: 12px; font-weight: bold;"
        )

    def _update_compare(self, r) -> None:
        is_s  = getattr(r, "is_stats",  {})
        oos_s = getattr(r, "oos_stats", {})

        def _fill(row: int, key: str, fmt: str = ".4f") -> None:
            iv = is_s.get(key,  None)
            ov = oos_s.get(key, None)
            is_better = (iv is not None and ov is not None and abs(iv) >= abs(ov))
            self._tbl_compare.setItem(
                row, 1,
                _item(format(iv, fmt) if iv is not None else "—", _FG),
            )
            ov_color = _GRN if (ov and ov > 0) else _RED
            self._tbl_compare.setItem(
                row, 2,
                _item(format(ov, fmt) if ov is not None else "—", ov_color),
            )

        _fill(0, "mean",     ".4f")
        _fill(1, "std",      ".4f")
        _fill(2, "ir",       ".3f")
        _fill(3, "t_stat",   ".2f")
        _fill(4, "win_rate", ".1%")

        # Sharpe
        self._tbl_compare.setItem(5, 1, _item(f"{r.is_sharpe:.3f}",  _FG))
        self._tbl_compare.setItem(
            5, 2,
            _item(
                f"{r.oos_sharpe:.3f}",
                _GRN if r.oos_sharpe > 0 else _RED,
            ),
        )

    def _update_verdict(self, r) -> None:
        of_ratio = r.overfit_ratio
        alpha_ok = r.oos_ic > 0.01 and of_ratio <= 3.0

        if alpha_ok:
            verdict = "✔  Alpha 真实"
            color   = _GRN
        elif r.oos_ic <= 0:
            verdict = "✘  Alpha 无效"
            color   = _RED
        else:
            verdict = "⚠  存在过拟合"
            color   = _YLW

        self._lbl_verdict.setText(verdict)
        self._lbl_verdict.setStyleSheet(
            f"color: {color}; font-size: 20px; font-weight: bold;"
        )

        # 详细文字说明
        is_period  = r.is_period  or ("—", "—")
        oos_period = r.oos_period or ("—", "—")
        of_str     = "∞" if of_ratio == float("inf") else f"{of_ratio:.2f}x"
        lines = [
            f"  IS  区间：{str(is_period[0])[:10]} ~ {str(is_period[1])[:10]}",
            f"  OOS 区间：{str(oos_period[0])[:10]} ~ {str(oos_period[1])[:10]}",
            f"",
            f"  IS  IC = {r.is_ic:.4f}   Sharpe = {r.is_sharpe:.3f}",
            f"  OOS IC = {r.oos_ic:.4f}   Sharpe = {r.oos_sharpe:.3f}",
            f"",
            f"  过拟合比率（IS/OOS）= {of_str}",
            f"  （≤ 1.5 = 优秀  ≤ 3.0 = 可接受  > 3.0 = 过拟合）",
        ]
        self._txt_detail.setText("\n".join(lines))
