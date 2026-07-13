"""
live_production/ui/failover_tab.py

FailoverTab — 故障切换面板（Phase 4）。

布局：
  顶部：KPI 栏（当前模式 / 风控接管状态 / 切换次数）
  中部：左侧模式流向图 / 右侧切换历史表
  底部：操作按钮栏
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import FailoverMode
from ..engine.failover_engine import FailoverReason

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_ORG      = "#fab387"

_MODE_COLOR = {
    FailoverMode.FULL.value:      _GRN,
    FailoverMode.PARTIAL.value:   _YLW,
    FailoverMode.SAFE_MODE.value: _RED,
}
_MODE_ZH = {
    FailoverMode.FULL.value:      "全功能  FULL",
    FailoverMode.PARTIAL.value:   "部分降级  PARTIAL",
    FailoverMode.SAFE_MODE.value: "安全模式  SAFE MODE",
}

_REC_COLS = [
    ("ID",          70),
    ("从 From",     100),
    ("到 To",       100),
    ("原因 Reason", 130),
    ("风控接管",    60),
    ("时间",        140),
    ("详情 Detail", 200),
]


def _item(text, color=_FG):
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    it.setForeground(QtGui.QColor(color))
    return it


def _item_left(text, color=_FG):
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
    it.setForeground(QtGui.QColor(color))
    return it


class FailoverTab(QtWidgets.QWidget):
    """故障切换面板（Phase 4）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._flow_cards: dict[str, QtWidgets.QWidget] = {}
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self._build_kpi_bar())

        mid = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        mid.addWidget(self._build_flow_panel())
        mid.addWidget(self._build_history_panel())
        mid.setSizes([300, 900])
        root.addWidget(mid, stretch=1)

        root.addWidget(self._build_action_bar())

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(66)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(20, 6, 20, 6)
        h.setSpacing(32)

        kpis = [
            ("当前模式 Mode",      "FULL",  _GRN),
            ("风控接管 Risk",       "OFF",   _MUT),
            ("总切换次数 Switches", "0",     _FG),
            ("降级次数 Down",       "0",     _YLW),
            ("恢复次数 Up",         "0",     _GRN),
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
                f"color: {color}; font-size: 14px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._kpi[name] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_flow_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(8)

        title = QtWidgets.QLabel("降级模式  Failover Mode")
        title.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(title)

        flow = [
            (FailoverMode.FULL,      "全功能  FULL",          _GRN, "所有模块正常运行"),
            (FailoverMode.PARTIAL,   "部分降级  PARTIAL",     _YLW, "部分功能受限"),
            (FailoverMode.SAFE_MODE, "安全模式  SAFE MODE",   _RED, "仅平仓，禁止开仓"),
        ]
        for i, (mode, label, color, desc) in enumerate(flow):
            card = QtWidgets.QWidget()
            card.setObjectName(mode.value)
            card.setStyleSheet(
                f"background: #11111b; border-radius: 4px;"
                f" border: 1px solid {_BORDER};"
            )
            card.setFixedHeight(52)
            ch = QtWidgets.QHBoxLayout(card)
            ch.setContentsMargins(12, 6, 12, 6)

            lname = QtWidgets.QLabel(label)
            lname.setStyleSheet(
                f"color: {color}; font-size: 12px; font-weight: bold; border: none;")
            ldesc = QtWidgets.QLabel(desc)
            ldesc.setStyleSheet(
                f"color: {_MUT}; font-size: 10px; border: none;")
            ch.addWidget(lname)
            ch.addStretch()
            ch.addWidget(ldesc)
            v.addWidget(card)
            self._flow_cards[mode.value] = card

            if i < len(flow) - 1:
                arr = QtWidgets.QLabel("  ↓")
                arr.setStyleSheet(f"color: {_BORDER}; font-size: 11px;")
                v.addWidget(arr)

        # 风控接管状态
        v.addSpacing(12)
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(
            f"border: none; border-top: 1px solid {_BORDER};")
        v.addWidget(sep)

        self._lbl_risk = QtWidgets.QLabel("风控接管  OFF")
        self._lbl_risk.setStyleSheet(
            f"color: {_MUT}; font-size: 13px; font-weight: bold;")
        self._lbl_risk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self._lbl_risk)
        v.addStretch()
        return w

    def _build_history_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        lbl = QtWidgets.QLabel("切换历史  Switch History")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._tbl = QtWidgets.QTableWidget(0, len(_REC_COLS))
        self._tbl.setHorizontalHeaderLabels([c[0] for c in _REC_COLS])
        for i, (_, w_) in enumerate(_REC_COLS):
            self._tbl.setColumnWidth(i, w_)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl.setStyleSheet("font-size: 11px;")
        v.addWidget(self._tbl, stretch=1)
        return w

    def _build_action_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(46)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(8)

        def _btn(label, color, slot):
            b = QtWidgets.QPushButton(label)
            b.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {color};"
                f" border: 1px solid {color}; border-radius: 3px;"
                f" padding: 4px 12px; font-size: 12px; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            b.clicked.connect(slot)
            return b

        h.addWidget(_btn("降级一步 Downgrade",   _YLW, self._on_downgrade))
        h.addWidget(_btn("恢复一步 Upgrade",     _GRN, self._on_upgrade))
        h.addWidget(_btn("恢复全部 Full",        _GRN, self._on_upgrade_full))
        h.addWidget(_btn("风控接管 Risk Takeover", _RED, self._on_risk_takeover))
        h.addWidget(_btn("解除风控 Release",     _BLU, self._on_release_risk))
        h.addStretch()

        btn_r = QtWidgets.QPushButton("刷新 Refresh")
        btn_r.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUT};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 4px 12px; font-size: 12px; }}"
        )
        btn_r.clicked.connect(self.refresh)
        h.addWidget(btn_r)
        return bar

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        if self._engine is None:
            return
        fe   = self._engine.failover_engine
        summ = fe.summary()
        mode = summ["mode"]

        color = _MODE_COLOR.get(mode, _MUT)
        self._kpi["当前模式 Mode"].setText(_MODE_ZH.get(mode, mode.upper()))
        self._kpi["当前模式 Mode"].setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: bold;")

        risk_on = summ["risk_takeover"]
        self._kpi["风控接管 Risk"].setText("ON" if risk_on else "OFF")
        self._kpi["风控接管 Risk"].setStyleSheet(
            f"color: {_RED if risk_on else _MUT};"
            f" font-size: 14px; font-weight: bold;")

        self._kpi["总切换次数 Switches"].setText(str(summ["total_switches"]))
        self._kpi["降级次数 Down"].setText(str(summ["downgrades"]))
        self._kpi["恢复次数 Up"].setText(str(summ["upgrades"]))

        self._lbl_risk.setText(f"风控接管  {'ON' if risk_on else 'OFF'}")
        self._lbl_risk.setStyleSheet(
            f"color: {_RED if risk_on else _MUT};"
            f" font-size: 13px; font-weight: bold;")

        self._highlight_flow(mode)
        self._refresh_records(fe.get_records(limit=200))

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _on_downgrade(self) -> None:
        if self._engine:
            self._engine.downgrade(FailoverReason.MANUAL, "手动降级")
            self.refresh()

    def _on_upgrade(self) -> None:
        if self._engine:
            self._engine.upgrade(FailoverReason.MANUAL, "手动恢复")
            self.refresh()

    def _on_upgrade_full(self) -> None:
        if self._engine:
            self._engine.upgrade_full(FailoverReason.MANUAL, "手动全恢复")
            self.refresh()

    def _on_risk_takeover(self) -> None:
        if self._engine:
            self._engine.trigger_risk_takeover("手动风控接管")
            self.refresh()

    def _on_release_risk(self) -> None:
        if self._engine:
            self._engine.release_risk_takeover("手动解除风控")
            self.refresh()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _highlight_flow(self, active: str) -> None:
        for mode_val, card in self._flow_cards.items():
            if mode_val == active:
                color = _MODE_COLOR.get(mode_val, _BLU)
                card.setStyleSheet(
                    f"background: #11111b; border-radius: 4px;"
                    f" border: 2px solid {color};")
            else:
                card.setStyleSheet(
                    f"background: #11111b; border-radius: 4px;"
                    f" border: 1px solid {_BORDER};")

    def _refresh_records(self, records: list) -> None:
        self._tbl.setRowCount(0)
        for rec in reversed(records):
            row = self._tbl.rowCount()
            self._tbl.insertRow(row)
            fm_color = _MODE_COLOR.get(rec.to_mode.value, _MUT)
            risk_col = _RED if rec.risk_takeover else _MUT
            self._tbl.setItem(row, 0, _item(rec.record_id,         _MUT))
            self._tbl.setItem(row, 1, _item(rec.from_mode.value,
                _MODE_COLOR.get(rec.from_mode.value, _MUT)))
            self._tbl.setItem(row, 2, _item(rec.to_mode.value,    fm_color))
            self._tbl.setItem(row, 3, _item(rec.reason.value,      _BLU))
            self._tbl.setItem(row, 4, _item("YES" if rec.risk_takeover else "NO", risk_col))
            self._tbl.setItem(row, 5, _item(str(rec.ts)[:19],      _MUT))
            self._tbl.setItem(row, 6, _item_left(rec.detail or "---", _MUT))
