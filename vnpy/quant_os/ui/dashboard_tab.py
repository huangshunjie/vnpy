"""
quant_os/ui/dashboard_tab.py

DashboardTab — 系统总览仪表盘（Phase 5）。

展示整个 Quant OS 的一页式全景状态：
  顶部：大字 Alpha 总数 / 运行策略 / 模块健康 / 触发次数
  中部：6 大模块状态卡片网格
  底部：最近系统日志流（只读）
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..engine.system_controller import SystemHealth
from ..constant import ModuleState

_PANEL_BG = "#181825"
_CARD_BG  = "#11111b"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_ORG      = "#fab387"
_PRP      = "#cba6f7"

_HEALTH_COLOR = {
    SystemHealth.HEALTHY.value:  _GRN,
    SystemHealth.DEGRADED.value: _YLW,
    SystemHealth.CRITICAL.value: _RED,
    SystemHealth.STOPPED.value:  _MUT,
}
_STATE_COLOR = {
    ModuleState.INIT.value:    _MUT,
    ModuleState.RUNNING.value: _GRN,
    ModuleState.PAUSED.value:  _YLW,
    ModuleState.STOPPED.value: _ORG,
    ModuleState.ERROR.value:   _RED,
}

_MODULE_ICONS = {
    "factor":     "F",
    "strategy":   "S",
    "portfolio":  "P",
    "execution":  "E",
    "risk":       "R",
    "validation": "V",
}


class DashboardTab(QtWidgets.QWidget):
    """系统总览仪表盘（Phase 5）。"""

    def __init__(self, os_engine=None, parent=None) -> None:
        super().__init__(parent)
        self._os_engine = os_engine
        self._card_widgets: list[tuple[str, QtWidgets.QLabel, QtWidgets.QLabel]] = []
        self._init_ui()

    def set_os_engine(self, os_engine) -> None:
        self._os_engine = os_engine

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        root.addWidget(self._build_top_kpi())
        root.addWidget(self._build_module_grid())

        sp = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        sp.addWidget(self._build_log_stream())
        root.addWidget(sp, stretch=1)

    def _build_top_kpi(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(80)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 6px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(20, 8, 20, 8)
        h.setSpacing(0)

        kpis = [
            ("系统健康",      "STOPPED", _MUT),
            ("已注册模块",    "0",       _FG),
            ("运行中模块",    "0",       _GRN),
            ("Alpha Live",   "0",       _BLU),
            ("Strategy Live","0",       _PRP),
            ("触发总次数",    "0",       _YLW),
            ("运行时长(s)",   "0",       _MUT),
        ]
        self._top_kpi: dict[str, QtWidgets.QLabel] = {}
        for i, (name, val, color) in enumerate(kpis):
            if i > 0:
                sep = QtWidgets.QFrame()
                sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
                sep.setStyleSheet(f"color: {_BORDER};")
                h.addWidget(sep)

            col = QtWidgets.QVBoxLayout()
            col.setSpacing(2)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(
                f"color: {color}; font-size: 16px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._top_kpi[name] = lv

            wrapper = QtWidgets.QWidget()
            wrapper.setLayout(col)
            h.addWidget(wrapper, stretch=1)

        return bar

    def _build_module_grid(self) -> QtWidgets.QWidget:
        """6 大模块状态卡片（2行 × 3列）。"""
        w = QtWidgets.QWidget()
        w.setFixedHeight(130)
        w.setStyleSheet(f"background: transparent;")
        grid = QtWidgets.QGridLayout(w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)

        module_defs = [
            ("因子研究 Factor Research",   "factor"),
            ("策略引擎 Strategy Engine",   "strategy"),
            ("组合引擎 Portfolio Engine",  "portfolio"),
            ("执行引擎 Execution Engine",  "execution"),
            ("风控引擎 Risk Engine",       "risk"),
            ("验证引擎 Validation Engine", "validation"),
        ]
        self._module_cards: dict[str, dict] = {}
        for idx, (display_name, mtype) in enumerate(module_defs):
            row, col = divmod(idx, 3)
            card, lbl_state, lbl_detail = self._make_module_card(
                display_name, mtype
            )
            grid.addWidget(card, row, col)
            self._module_cards[mtype] = {
                "widget":     card,
                "lbl_state":  lbl_state,
                "lbl_detail": lbl_detail,
            }
        return w

    def _make_module_card(
        self, name: str, mtype: str
    ) -> tuple[QtWidgets.QWidget, QtWidgets.QLabel, QtWidgets.QLabel]:
        card = QtWidgets.QWidget()
        card.setStyleSheet(
            f"background: {_CARD_BG}; border-radius: 6px;"
            f" border: 1px solid {_BORDER};"
        )
        v = QtWidgets.QVBoxLayout(card)
        v.setContentsMargins(10, 6, 10, 6)
        v.setSpacing(2)

        icon_char = _MODULE_ICONS.get(mtype, "?")
        top = QtWidgets.QHBoxLayout()
        lbl_icon = QtWidgets.QLabel(icon_char)
        lbl_icon.setStyleSheet(
            f"color: {_BLU}; font-size: 14px; font-weight: bold;"
            f" border: none;"
        )
        lbl_name = QtWidgets.QLabel(name)
        lbl_name.setStyleSheet(f"color: {_FG}; font-size: 11px; border: none;")
        top.addWidget(lbl_icon)
        top.addWidget(lbl_name)
        top.addStretch()

        lbl_state = QtWidgets.QLabel("INIT")
        lbl_state.setStyleSheet(
            f"color: {_MUT}; font-size: 12px; font-weight: bold; border: none;"
        )
        lbl_detail = QtWidgets.QLabel("—")
        lbl_detail.setStyleSheet(
            f"color: {_MUT}; font-size: 10px; border: none;"
        )

        v.addLayout(top)
        v.addWidget(lbl_state)
        v.addWidget(lbl_detail)
        return card, lbl_state, lbl_detail

    def _build_log_stream(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        top = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel("最近系统日志")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        top.addWidget(lbl)
        top.addStretch()
        v.addLayout(top)

        self._txt_dash_log = QtWidgets.QTextEdit()
        self._txt_dash_log.setReadOnly(True)
        self._txt_dash_log.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt_dash_log, stretch=1)
        return w

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        if self._os_engine is None:
            return
        summ = self._os_engine.get_summary()
        self._update_top_kpi(summ)
        self._update_module_cards()
        self._update_log_stream()

    def append_log(self, msg: str) -> None:
        self._txt_dash_log.append(msg)
        sb = self._txt_dash_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_system_event(self, event_type: str, data: dict) -> None:
        self.refresh()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _update_top_kpi(self, summ: dict) -> None:
        health = summ.get("system_health", "stopped")
        h_col  = _HEALTH_COLOR.get(health, _MUT)
        mods   = summ.get("modules", {})
        lc     = summ.get("lifecycle", {})
        orch   = summ.get("orchestrator", {})

        self._top_kpi["系统健康"      ].setText(health.upper())
        self._top_kpi["系统健康"      ].setStyleSheet(
            f"color: {h_col}; font-size: 16px; font-weight: bold;")
        self._top_kpi["已注册模块"    ].setText(str(mods.get("total", 0)))
        self._top_kpi["运行中模块"    ].setText(str(mods.get("running", 0) if isinstance(mods, dict) else 0))
        self._top_kpi["Alpha Live"   ].setText(
            str(lc.get("alpha", {}).get("by_state", {}).get("live", 0)))
        self._top_kpi["Strategy Live"].setText(
            str(lc.get("strategy", {}).get("by_state", {}).get("live_trading", 0)))
        self._top_kpi["触发总次数"    ].setText(
            str(orch.get("triggers", {}).get("total", 0)))
        self._top_kpi["运行时长(s)"   ].setText(
            f"{summ.get('uptime', 0):.0f}")

    def _update_module_cards(self) -> None:
        modules = self._os_engine.registry.get_all()
        module_by_type: dict[str, list] = {}
        for m in modules:
            mt = m.module_type.value
            module_by_type.setdefault(mt, []).append(m)

        for mtype, card_info in self._module_cards.items():
            mlist = module_by_type.get(mtype, [])
            if not mlist:
                card_info["lbl_state" ].setText("—")
                card_info["lbl_detail"].setText("未注册")
                continue
            # 取第一个（通常每类只有一个）
            m     = mlist[0]
            sc    = _STATE_COLOR.get(m.state.value, _FG)
            card_info["lbl_state" ].setText(m.state.value.upper())
            card_info["lbl_state" ].setStyleSheet(
                f"color: {sc}; font-size: 12px; font-weight: bold; border: none;")
            uptime = f"运行 {m.uptime_seconds:.0f}s" if m.started_at else ""
            detail = f"{m.name}"
            if m.error_count:
                detail += f"  ERR={m.error_count}"
            if uptime:
                detail += f"  {uptime}"
            card_info["lbl_detail"].setText(detail)

    def _update_log_stream(self) -> None:
        records = self._os_engine.event_bus.get_history(limit=30)
        lines   = [r.to_line() for r in records
                   if "eQuantOS.log" in r.event_type]
        if lines:
            self._txt_dash_log.setPlainText("\n".join(lines[-20:]))
            sb = self._txt_dash_log.verticalScrollBar()
            sb.setValue(sb.maximum())
