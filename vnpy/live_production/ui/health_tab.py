"""
live_production/ui/health_tab.py

HealthTab — 实时健康监控面板（Phase 5）。

布局：
  顶部：健康等级大字 + 综合分数
  中部：6 个指标卡片（延迟/P95/订单成功率/行情延迟/心跳/健康分）
  下方：告警列表 | 历史快照表
  底部：操作栏（手动评估 / 刷新 / 阈值设置入口）
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import SystemHealthState

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_ORG      = "#fab387"

_STATE_COLOR = {
    SystemHealthState.HEALTHY.value:  _GRN,
    SystemHealthState.WARNING.value:  _YLW,
    SystemHealthState.CRITICAL.value: _RED,
    SystemHealthState.UNKNOWN.value:  _MUT,
}
_STATE_ZH = {
    SystemHealthState.HEALTHY.value:  "健康  HEALTHY",
    SystemHealthState.WARNING.value:  "警告  WARNING",
    SystemHealthState.CRITICAL.value: "严重  CRITICAL",
    SystemHealthState.UNKNOWN.value:  "未知  UNKNOWN",
}

_HIST_COLS = [
    ("时间",        130),
    ("状态",         80),
    ("分数",         60),
    ("延迟ms",       70),
    ("P95ms",        70),
    ("订单成功率",   80),
    ("行情延迟s",    70),
    ("心跳",         50),
    ("告警数",       60),
]


def _item(text, color=_FG):
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    it.setForeground(QtGui.QColor(color))
    return it


class _MetricCard(QtWidgets.QWidget):
    """单个指标卡片。"""

    def __init__(self, title: str, unit: str = "", warn_dir: str = "high",
                 parent=None) -> None:
        super().__init__(parent)
        self._warn_dir = warn_dir   # "high" = 高于阈值变红, "low" = 低于变红
        self.setFixedHeight(70)
        self.setStyleSheet(
            f"background: #11111b; border-radius: 6px;"
            f" border: 1px solid {_BORDER};"
        )
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(10, 6, 10, 6)
        v.setSpacing(2)

        self._lbl_title = QtWidgets.QLabel(title)
        self._lbl_title.setStyleSheet(
            f"color: {_MUT}; font-size: 10px; border: none;")
        self._lbl_value = QtWidgets.QLabel("---")
        self._lbl_value.setStyleSheet(
            f"color: {_FG}; font-size: 18px; font-weight: bold; border: none;")
        self._lbl_unit = QtWidgets.QLabel(unit)
        self._lbl_unit.setStyleSheet(
            f"color: {_MUT}; font-size: 9px; border: none;")

        h = QtWidgets.QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(self._lbl_value)
        h.addWidget(self._lbl_unit)
        h.addStretch()

        v.addWidget(self._lbl_title)
        v.addLayout(h)

    def update(self, value: str, color: str = _FG) -> None:
        self._lbl_value.setText(value)
        self._lbl_value.setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: bold; border: none;")


class HealthTab(QtWidgets.QWidget):
    """实时健康监控面板（Phase 5）。"""

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
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_banner())
        root.addWidget(self._build_cards())

        mid = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        mid.addWidget(self._build_alert_panel())
        mid.addWidget(self._build_history_panel())
        mid.setSizes([380, 820])
        root.addWidget(mid, stretch=1)

        root.addWidget(self._build_action_bar())

    def _build_banner(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(64)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 6px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(24, 8, 24, 8)

        self._lbl_state = QtWidgets.QLabel("未知  UNKNOWN")
        self._lbl_state.setStyleSheet(
            f"color: {_MUT}; font-size: 22px; font-weight: bold;")
        h.addWidget(self._lbl_state)
        h.addStretch()

        col = QtWidgets.QVBoxLayout()
        self._lbl_score = QtWidgets.QLabel("综合分  ---")
        self._lbl_score.setStyleSheet(
            f"color: {_MUT}; font-size: 13px; font-weight: bold;")
        self._lbl_alerts = QtWidgets.QLabel("告警  0 条")
        self._lbl_alerts.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        col.addWidget(self._lbl_score)
        col.addWidget(self._lbl_alerts)
        h.addLayout(col)
        return bar

    def _build_cards(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(84)
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)

        self._card_latency  = _MetricCard("网关延迟 Latency",   "ms",  "high")
        self._card_p95      = _MetricCard("P95 延迟",            "ms",  "high")
        self._card_rate     = _MetricCard("订单成功率 OrderRate", "%",   "low")
        self._card_delay    = _MetricCard("行情延迟 DataDelay",  "s",   "high")
        self._card_hb       = _MetricCard("心跳 Heartbeat",      "",    "low")
        self._card_score    = _MetricCard("健康分 Score",        "/1",  "low")

        for card in (self._card_latency, self._card_p95, self._card_rate,
                     self._card_delay, self._card_hb, self._card_score):
            h.addWidget(card, stretch=1)
        return w

    def _build_alert_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        top = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel("当前告警  Active Alerts")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        top.addWidget(lbl)
        top.addStretch()
        v.addLayout(top)

        self._lst_alerts = QtWidgets.QListWidget()
        self._lst_alerts.setStyleSheet(
            f"QListWidget {{ background: #11111b; color: {_RED};"
            f" font-size: 11px; border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._lst_alerts, stretch=1)
        return w

    def _build_history_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        lbl = QtWidgets.QLabel("历史快照  Health History")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._tbl = QtWidgets.QTableWidget(0, len(_HIST_COLS))
        self._tbl.setHorizontalHeaderLabels([c[0] for c in _HIST_COLS])
        for i, (_, w_) in enumerate(_HIST_COLS):
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

        h.addWidget(_btn("立即评估 Evaluate", _BLU,  self._on_evaluate))
        h.addWidget(_btn("模拟心跳 Heartbeat", _GRN, self._on_heartbeat))
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
        hm   = self._engine.health_monitor
        summ = hm.summary()
        snap = hm.current

        # 顶部 banner
        state = summ["health_state"]
        color = _STATE_COLOR.get(state, _MUT)
        zh    = _STATE_ZH.get(state, state.upper())
        self._lbl_state.setText(zh)
        self._lbl_state.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: bold;")
        self._lbl_score.setText(
            f"综合分  {summ['health_score']:.3f}")
        self._lbl_score.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: bold;")
        n_alerts = len(summ["alerts"])
        self._lbl_alerts.setText(f"告警  {n_alerts} 条")
        self._lbl_alerts.setStyleSheet(
            f"color: {_RED if n_alerts else _MUT}; font-size: 11px;")

        # 指标卡片
        t = hm._thresholds
        lat = summ["latency_ms"]
        lat_c = (_RED if lat >= t.latency_crit_ms
                 else _YLW if lat >= t.latency_warn_ms else _GRN)
        self._card_latency.update(f"{lat:.0f}", lat_c)
        self._card_p95.update(f"{summ['latency_p95_ms']:.0f}", _FG)

        rate = summ["order_success_rate"]
        rate_c = (_RED if rate < t.order_rate_crit
                  else _YLW if rate < t.order_rate_warn else _GRN)
        self._card_rate.update(f"{rate:.1%}", rate_c)

        dd = summ["data_delay_s"]
        dd_c = (_RED if dd >= t.data_delay_crit_s
                else _YLW if dd >= t.data_delay_warn_s else _GRN)
        self._card_delay.update(f"{dd:.1f}", dd_c)

        hb = summ["heartbeat_ok"]
        self._card_hb.update("OK" if hb else "FAIL", _GRN if hb else _RED)

        score = summ["health_score"]
        sc_c  = _RED if score < t.health_score_crit else (
                _YLW if score < t.health_score_warn else _GRN)
        self._card_score.update(f"{score:.3f}", sc_c)

        # 告警列表
        self._lst_alerts.clear()
        for a in summ["alerts"]:
            self._lst_alerts.addItem(a)

        # 历史表
        history = hm.get_history(limit=200)
        self._tbl.setRowCount(0)
        for s in reversed(history):
            row = self._tbl.rowCount()
            self._tbl.insertRow(row)
            sc  = _STATE_COLOR.get(s.health_state.value, _MUT)
            hbc = _GRN if s.heartbeat_ok else _RED
            self._tbl.setItem(row, 0, _item(str(s.snapshot_at)[:19],       _MUT))
            self._tbl.setItem(row, 1, _item(s.health_state.value,           sc))
            self._tbl.setItem(row, 2, _item(f"{s.health_score:.3f}",        sc))
            self._tbl.setItem(row, 3, _item(f"{s.latency_ms:.0f}",          _FG))
            self._tbl.setItem(row, 4, _item(f"{s.latency_p95_ms:.0f}",      _FG))
            self._tbl.setItem(row, 5, _item(f"{s.order_success_rate:.1%}",  _FG))
            self._tbl.setItem(row, 6, _item(f"{s.data_delay_s:.1f}",        _FG))
            self._tbl.setItem(row, 7, _item("OK" if s.heartbeat_ok else "FAIL", hbc))
            self._tbl.setItem(row, 8, _item(str(len(s.alerts)),
                _RED if s.alerts else _MUT))

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _on_evaluate(self) -> None:
        if self._engine:
            self._engine.evaluate_health()
            self.refresh()

    def _on_heartbeat(self) -> None:
        if self._engine:
            self._engine.record_heartbeat(ok=True)
            self._engine.evaluate_health()
            self.refresh()
