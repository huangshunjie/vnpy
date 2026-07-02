"""
market_regime_ai/ui/regime_tab.py  (Phase 2)

RegimeTab — 市场状态识别面板。
"""

from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui

_BG     = "#1e1e2e"
_PANEL  = "#181825"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_GRN    = "#a6e3a1"
_RED    = "#f38ba8"
_YLW    = "#f9e2af"
_MAV    = "#cba6f7"
_ORG    = "#fab387"
_CYN    = "#89dceb"

_REGIME_COLORS = {
    "bull":     _GRN,
    "bear":     _RED,
    "sideways": _YLW,
    "high_vol": _ORG,
    "low_liq":  _CYN,
    "unknown":  _MUT,
}

_REGIME_LABELS = {
    "bull":     "Bull Market  牛市",
    "bear":     "Bear Market  熊市",
    "sideways": "Sideways  震荡",
    "high_vol": "High Volatility  高波动",
    "low_liq":  "Low Liquidity  低流动性",
    "unknown":  "Unknown  未知",
}


class RegimeTab(QtWidgets.QWidget):
    """状态识别面板（Phase 2）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        root.addWidget(self._build_status_card())
        mid = QtWidgets.QHBoxLayout()
        mid.setSpacing(10)
        mid.addWidget(self._build_scores_panel(), stretch=1)
        mid.addWidget(self._build_history_panel(), stretch=2)
        root.addLayout(mid)
        root.addWidget(self._build_action_bar())

    def _build_status_card(self) -> QtWidgets.QWidget:
        card = QtWidgets.QWidget()
        card.setFixedHeight(110)
        card.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px;"
            f" border: 1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(card)
        h.setContentsMargins(20, 12, 20, 12)
        h.setSpacing(40)
        self._regime_big    = self._stat_block("当前状态", "UNKNOWN", _MUT, big=True)
        self._conf_block    = self._stat_block("置信度", "---", _MUT)
        self._conf_lv_block = self._stat_block("置信级别", "---", _MUT)
        self._rec_block     = self._stat_block("策略建议", "NEUTRAL", _MUT)
        self._dur_block     = self._stat_block("持续 Bars", "0", _MUT)
        self._stab_block    = self._stat_block("稳定性", "---", _MUT)
        for w in [self._regime_big, self._conf_block, self._conf_lv_block,
                  self._rec_block, self._dur_block, self._stab_block]:
            h.addWidget(w)
        h.addStretch()
        return card

    def _stat_block(self, title, value, color, big=False):
        w = QtWidgets.QWidget()
        w.setStyleSheet("border: none; background: transparent;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        tl = QtWidgets.QLabel(title)
        tl.setStyleSheet(f"color: {_MUT}; font-size: 9px; border: none;")
        size = "18px" if big else "14px"
        vl = QtWidgets.QLabel(value)
        vl.setStyleSheet(
            f"color: {color}; font-size: {size}; font-weight: bold; border: none;")
        v.addWidget(tl)
        v.addWidget(vl)
        w._vl = vl
        return w

    def _build_scores_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px;"
            f" border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        title = QtWidgets.QLabel("Factor Scores  因子评分")
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(title)
        v.addWidget(self._sep())
        self._score_bars: dict[str, tuple] = {}
        for key, label in [
            ("bull",     "Bull Market"),
            ("bear",     "Bear Market"),
            ("sideways", "Sideways"),
            ("high_vol", "High Vol"),
            ("low_liq",  "Low Liq"),
        ]:
            row, bar, lbl = self._score_row(label, _REGIME_COLORS[key])
            v.addWidget(row)
            self._score_bars[key] = (bar, lbl)
        v.addStretch()
        return panel

    def _score_row(self, label, color):
        row = QtWidgets.QWidget()
        row.setStyleSheet("background: transparent; border: none;")
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        lbl_name = QtWidgets.QLabel(label)
        lbl_name.setFixedWidth(72)
        lbl_name.setStyleSheet(f"color: {_MUT}; font-size: 10px; border: none;")
        bar = QtWidgets.QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setFixedHeight(10)
        bar.setStyleSheet(f"""
            QProgressBar {{ background: #11111b; border-radius: 5px;
                border: 1px solid {_BORDER}; }}
            QProgressBar::chunk {{ background: {color}; border-radius: 5px; }}
        """)
        val_lbl = QtWidgets.QLabel("0.00")
        val_lbl.setFixedWidth(36)
        val_lbl.setStyleSheet(f"color: {_FG}; font-size: 10px; border: none;")
        val_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        h.addWidget(lbl_name)
        h.addWidget(bar, stretch=1)
        h.addWidget(val_lbl)
        return row, bar, val_lbl

    def _build_history_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px;"
            f" border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        title = QtWidgets.QLabel("Regime History  状态切换历史")
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(title)
        v.addWidget(self._sep())
        self._history_table = QtWidgets.QTableWidget(0, 5)
        self._history_table.setHorizontalHeaderLabels(
            ["状态", "置信度", "持续 Bars", "开始时间", "结束时间"])
        self._history_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._history_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._history_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._history_table.verticalHeader().setVisible(False)
        self._history_table.setAlternatingRowColors(True)
        self._history_table.setStyleSheet(f"""
            QTableWidget {{ background: #11111b; color: {_FG};
                border: 1px solid {_BORDER}; gridline-color: {_BORDER}; font-size: 11px; }}
            QHeaderView::section {{ background: #313244; color: {_MUT};
                padding: 4px; border: none; font-size: 10px; }}
            QTableWidget::item:alternate {{ background: #181825; }}
        """)
        v.addWidget(self._history_table, stretch=1)
        return panel

    def _build_action_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(44)
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        detect_btn = self._btn("Detect Regime  检测状态", _MAV)
        detect_btn.clicked.connect(self._on_detect)
        refresh_btn = self._btn("Refresh  刷新", _MUT)
        refresh_btn.clicked.connect(self.refresh)
        h.addWidget(detect_btn)
        h.addWidget(refresh_btn)
        h.addStretch()
        self._status_lbl = QtWidgets.QLabel("")
        self._status_lbl.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        h.addWidget(self._status_lbl)
        return bar

    def _btn(self, text, color):
        btn = QtWidgets.QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {color};
                border: 1px solid {color}; border-radius: 4px;
                padding: 6px 18px; font-size: 12px; }}
            QPushButton:hover {{ background: {color}22; }}
            QPushButton:pressed {{ background: {color}44; }}
        """)
        return btn

    def _sep(self):
        s = QtWidgets.QFrame()
        s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border: none; border-top: 1px solid {_BORDER};")
        return s

    # ------------------------------------------------------------------ #
    #  刷新逻辑
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        if self._engine is None:
            return
        try:
            state = self._engine.get_regime_state()
        except Exception:
            return
        self._update_status_card(state)
        self._update_score_bars(state.factor_scores)
        try:
            records = self._engine.get_regime_history(limit=20)
            self._update_history_table(records)
        except Exception:
            pass

    def _update_status_card(self, state) -> None:
        regime = state.regime.value
        color  = _REGIME_COLORS.get(regime, _MUT)
        label  = _REGIME_LABELS.get(regime, regime.upper())
        self._regime_big._vl.setText(label)
        self._regime_big._vl.setStyleSheet(
            f"color: {color}; font-size: 16px; font-weight: bold; border: none;")
        conf = state.confidence_score
        self._conf_block._vl.setText(f"{conf:.1%}")
        self._conf_block._vl.setStyleSheet(
            f"color: {self._conf_color(conf)}; font-size: 14px;"
            f" font-weight: bold; border: none;")
        self._conf_lv_block._vl.setText(state.confidence.value.upper())
        self._rec_block._vl.setText(state.recommendation.value.upper())
        self._dur_block._vl.setText(str(state.duration_bars))
        self._stab_block._vl.setText(f"{state.stability:.1%}")

    def _update_score_bars(self, scores: dict) -> None:
        for key, (bar, lbl) in self._score_bars.items():
            val = scores.get(key, 0.0)
            bar.setValue(int(val * 100))
            lbl.setText(f"{val:.2f}")

    def _update_history_table(self, records: list[dict]) -> None:
        self._history_table.setRowCount(0)
        for rec in reversed(records):
            row = self._history_table.rowCount()
            self._history_table.insertRow(row)
            regime = rec.get("regime", "")
            color  = _REGIME_COLORS.get(regime, _MUT)
            items  = [
                rec.get("regime", "").upper(),
                f"{rec.get('confidence_score', 0):.1%}",
                str(rec.get("duration_bars", 0)),
                str(rec.get("started_at", ""))[:16],
                str(rec.get("ended_at", "") or "active")[:16],
            ]
            for col, text in enumerate(items):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if col == 0:
                    item.setForeground(QtGui.QColor(color))
                self._history_table.setItem(row, col, item)

    @staticmethod
    def _conf_color(conf: float) -> str:
        if conf >= 0.75:
            return _GRN
        if conf >= 0.50:
            return _YLW
        return _RED

    # ------------------------------------------------------------------ #
    #  事件 / 操作
    # ------------------------------------------------------------------ #

    def _on_detect(self) -> None:
        if self._engine is None:
            return
        try:
            self._engine.detect_regime()
            self.refresh()
            self._status_lbl.setText("Detection complete.")
        except Exception as e:
            self._status_lbl.setText(f"Error: {e}")

    def update_from_event(self, state_dict: dict) -> None:
        """被 widget.py 调用，从事件数据直接刷新。"""
        try:
            self._update_score_bars(state_dict.get("factor_scores", {}))
            regime = state_dict.get("regime", "unknown")
            color  = _REGIME_COLORS.get(regime, _MUT)
            label  = _REGIME_LABELS.get(regime, regime.upper())
            self._regime_big._vl.setText(label)
            self._regime_big._vl.setStyleSheet(
                f"color: {color}; font-size: 16px; font-weight: bold; border: none;")
            conf = float(state_dict.get("confidence_score", 0.0))
            self._conf_block._vl.setText(f"{conf:.1%}")
            self._stab_block._vl.setText(
                f"{float(state_dict.get('stability', 0.0)):.1%}")
            self._dur_block._vl.setText(
                str(state_dict.get("duration_bars", 0)))
        except Exception:
            pass
