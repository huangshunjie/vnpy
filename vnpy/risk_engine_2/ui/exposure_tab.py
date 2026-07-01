"""
risk_engine_2/ui/exposure_tab.py

ExposureTab — 因子暴露 + 风格漂移检测（Phase 5 实现）。

左侧：因子暴露水平面板（文本热图）
右侧：持仓权重分布 + 风格漂移历史记录
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

_DRIFT_COLS = [
    ("时间",        70),
    ("因子",       110),
    ("当前暴露",    90),
    ("前次暴露",    90),
    ("漂移幅度",    90),
    ("阈值",        70),
    ("状态",        70),
]


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    item = QtWidgets.QTableWidgetItem(str(text))
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    item.setForeground(QtGui.QColor(color))
    return item


class ExposureTab(QtWidgets.QWidget):
    """风险暴露 Tab（Phase 5）。"""

    drift_threshold_changed = QtCore.Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._factor_exposures: dict[str, float] = {}
        self._drift_records: list[dict] = []
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # 左侧：因子暴露面板
        root.addWidget(self._build_factor_panel(), stretch=1)
        # 右侧：风格漂移历史
        root.addWidget(self._build_drift_panel(), stretch=1)

    # ------------------------------------------------------------------ #
    #  子区域构建
    # ------------------------------------------------------------------ #

    def _build_factor_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        # 顶部：阈值配置
        cfg = QtWidgets.QWidget()
        cfg.setFixedHeight(44)
        cfg.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(cfg)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(8)

        h.addWidget(self._lbl("漂移阈值：", f"color:{_MUT};font-size:11px;"))
        self._spn_thresh = QtWidgets.QDoubleSpinBox()
        self._spn_thresh.setRange(0.01, 1.0)
        self._spn_thresh.setValue(0.15)
        self._spn_thresh.setDecimals(2)
        self._spn_thresh.setSingleStep(0.01)
        self._spn_thresh.setStyleSheet(
            "QDoubleSpinBox { background:#313244; color:#cdd6f4;"
            " border:1px solid #45475a; border-radius:3px; padding:2px 6px;"
            " font-size:12px; }"
        )
        btn_apply = QtWidgets.QPushButton("应用")
        btn_apply.setFixedWidth(60)
        btn_apply.setStyleSheet(
            f"QPushButton {{ background:{_BLU}; color:#1e1e2e; border-radius:3px;"
            f" padding:3px; font-size:11px; font-weight:bold; }}"
        )
        btn_apply.clicked.connect(
            lambda: self.drift_threshold_changed.emit(self._spn_thresh.value())
        )
        h.addWidget(self._spn_thresh)
        h.addWidget(btn_apply)
        h.addStretch()
        v.addWidget(cfg)

        # 因子暴露文本热图
        lbl = QtWidgets.QLabel("当前组合因子暴露（来自 Factor Research）")
        lbl.setStyleSheet(f"color:{_MUT};font-size:10px;padding-left:4px;")
        v.addWidget(lbl)

        self._txt_exposure = QtWidgets.QTextEdit()
        self._txt_exposure.setReadOnly(True)
        self._txt_exposure.setStyleSheet(
            f"QTextEdit {{ background:#11111b; color:{_FG};"
            f" font-size:12px; font-family:monospace;"
            f" border:1px solid {_BORDER}; border-radius:3px; }}"
        )
        v.addWidget(self._txt_exposure, stretch=1)
        return w

    def _build_drift_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)

        # 汇总条
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"background:{_PANEL_BG}; border-radius:4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(10, 4, 10, 4)
        h.setSpacing(20)

        cards = [("监控因子数","0",_FG),("漂移事件","0",_YLW),("最大漂移","—",_RED)]
        self._drift_sum: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in cards:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(0)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color:{_MUT};font-size:10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(f"color:{color};font-size:13px;font-weight:bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln); col.addWidget(lv)
            self._drift_sum[name] = lv
            h.addLayout(col)
        h.addStretch()
        v.addWidget(bar)

        lbl = QtWidgets.QLabel("风格漂移历史记录（双击确认）")
        lbl.setStyleSheet(f"color:{_MUT};font-size:10px;padding-left:4px;")
        v.addWidget(lbl)

        self._tbl = QtWidgets.QTableWidget(0, len(_DRIFT_COLS))
        self._tbl.setHorizontalHeaderLabels([c[0] for c in _DRIFT_COLS])
        for i, (_, w_) in enumerate(_DRIFT_COLS):
            self._tbl.setColumnWidth(i, w_)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._tbl.setStyleSheet("font-size:12px;")
        v.addWidget(self._tbl, stretch=1)
        return w

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_factor_exposures(self, exposures: dict[str, float]) -> None:
        """刷新因子暴露热图（每次 EVENT_RISK_FACTOR_EXPOSURE 后调用）。"""
        self._factor_exposures.update(exposures)
        self._render_exposure_chart()
        self._drift_sum["监控因子数"].setText(str(len(self._factor_exposures)))

    def add_drift_record(self, drift_info: dict) -> None:
        """追加一条风格漂移记录（每次 EVENT_RISK_STYLE_DRIFT 后调用）。"""
        self._drift_records.append(drift_info)
        self._append_drift_row(drift_info)
        self._drift_sum["漂移事件"].setText(str(len(self._drift_records)))
        max_d = max((r.get("drift", 0.0) for r in self._drift_records), default=0.0)
        self._drift_sum["最大漂移"].setText(f"{max_d:.4f}")

    def clear(self) -> None:
        self._factor_exposures.clear()
        self._drift_records.clear()
        self._tbl.setRowCount(0)
        self._txt_exposure.clear()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _render_exposure_chart(self) -> None:
        """ASCII 横向热图：按暴露绝对值排序。"""
        if not self._factor_exposures:
            self._txt_exposure.setText("暂无因子暴露数据。\n等待 Factor Research Engine 推送...\n")
            return

        sorted_exp = sorted(
            self._factor_exposures.items(),
            key=lambda kv: abs(kv[1]),
            reverse=True,
        )
        max_abs = max(abs(v) for _, v in sorted_exp) or 1.0
        width   = 28
        lines   = ["  因子暴露热图", "  " + "─" * 50]
        for name, val in sorted_exp:
            bar_len = int(abs(val) / max_abs * width)
            if val >= 0:
                bar   = "█" * bar_len
                color_tag = "+"
            else:
                bar   = "░" * bar_len
                color_tag = "-"
            sign = "+" if val >= 0 else "-"
            lines.append(
                f"  {name[:16]:16s} │{bar:<{width}} {sign}{abs(val):.4f}"
            )
        lines.append("  " + "─" * 50)
        self._txt_exposure.setText("\n".join(lines))

    def _append_drift_row(self, info: dict) -> None:
        from datetime import datetime
        row = self._tbl.rowCount()
        self._tbl.insertRow(row)

        drift = float(info.get("drift", 0.0))
        thresh = float(info.get("threshold", 0.15))
        ratio  = drift / thresh if thresh > 0 else 0.0
        d_color = _RED if ratio >= 2.0 else (_YLW if ratio >= 1.0 else _FG)

        ts = datetime.now().strftime("%H:%M:%S")
        self._tbl.setItem(row, 0, _item(ts,                                _MUT))
        self._tbl.setItem(row, 1, _item(str(info.get("factor", "?")),       _FG))
        self._tbl.setItem(row, 2, _item(f"{info.get('current',0):.4f}",    _BLU))
        self._tbl.setItem(row, 3, _item(f"{info.get('previous',0):.4f}",   _MUT))
        self._tbl.setItem(row, 4, _item(f"{drift:.4f}",                  d_color))
        self._tbl.setItem(row, 5, _item(f"{thresh:.4f}",                   _MUT))
        status = "超阈值" if ratio >= 1.0 else "正常"
        s_color = _RED if ratio >= 1.0 else _GRN
        self._tbl.setItem(row, 6, _item(status,                           s_color))
        self._tbl.scrollToBottom()

    @staticmethod
    def _lbl(text: str, style: str) -> QtWidgets.QLabel:
        l = QtWidgets.QLabel(text)
        l.setStyleSheet(style)
        return l
