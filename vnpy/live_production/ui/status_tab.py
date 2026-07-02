"""
live_production/ui/status_tab.py

StatusTab — 系统状态面板（Phase 2）。

布局：
  顶部：当前交易状态大字显示 + 运行时长
  中部：左侧状态机流向图 / 右侧状态转换历史
  底部：快捷操作按钮栏
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import TradingState

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"

_STATE_COLOR = {
    TradingState.INIT.value:     _MUT,
    TradingState.RUNNING.value:  _GRN,
    TradingState.DEGRADED.value: _YLW,
    TradingState.RECOVERY.value: _BLU,
    TradingState.STOPPED.value:  _RED,
}

_STATE_ZH = {
    TradingState.INIT.value:     "初始化 INIT",
    TradingState.RUNNING.value:  "运行中 RUNNING",
    TradingState.DEGRADED.value: "降级运行 DEGRADED",
    TradingState.RECOVERY.value: "恢复中 RECOVERY",
    TradingState.STOPPED.value:  "已停止 STOPPED",
}


class StatusTab(QtWidgets.QWidget):
    """系统状态面板（Phase 2）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._flow_labels: dict[str, QtWidgets.QLabel] = {}
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
        root.addWidget(self._build_state_banner())

        mid = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        mid.addWidget(self._build_flow_panel())
        mid.addWidget(self._build_history_panel())
        mid.setSizes([360, 800])
        root.addWidget(mid, stretch=1)

        root.addWidget(self._build_action_bar())

    def _build_state_banner(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(64)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 6px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(24, 8, 24, 8)

        self._lbl_state = QtWidgets.QLabel("初始化 INIT")
        self._lbl_state.setStyleSheet(
            f"color: {_MUT}; font-size: 22px; font-weight: bold;")
        h.addWidget(self._lbl_state)
        h.addStretch()

        col = QtWidgets.QVBoxLayout()
        self._lbl_uptime = QtWidgets.QLabel("运行时长  —")
        self._lbl_uptime.setStyleSheet(f"color: {_MUT}; font-size: 12px;")
        self._lbl_transitions = QtWidgets.QLabel("状态转换  0 次")
        self._lbl_transitions.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        col.addWidget(self._lbl_uptime)
        col.addWidget(self._lbl_transitions)
        h.addLayout(col)
        return bar

    def _build_flow_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(6)

        title = QtWidgets.QLabel("状态机  State Machine")
        title.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(title)

        flow = [
            (TradingState.INIT,     "初始化  INIT",     _MUT, "系统启动前"),
            (TradingState.RUNNING,  "运行中  RUNNING",  _GRN, "正常实盘"),
            (TradingState.DEGRADED, "降级  DEGRADED",   _YLW, "模块异常"),
            (TradingState.RECOVERY, "恢复中  RECOVERY", _BLU, "恢复执行中"),
            (TradingState.STOPPED,  "已停止  STOPPED",  _RED, "系统停止"),
        ]
        for i, (st, label, color, desc) in enumerate(flow):
            card = QtWidgets.QWidget()
            card.setStyleSheet(
                f"background: #11111b; border-radius: 4px;"
                f" border: 1px solid {_BORDER};"
            )
            card.setFixedHeight(48)
            ch = QtWidgets.QHBoxLayout(card)
            ch.setContentsMargins(10, 4, 10, 4)

            lbl_name = QtWidgets.QLabel(label)
            lbl_name.setStyleSheet(
                f"color: {color}; font-size: 12px; font-weight: bold; border: none;")
            lbl_desc = QtWidgets.QLabel(desc)
            lbl_desc.setStyleSheet(
                f"color: {_MUT}; font-size: 10px; border: none;")
            ch.addWidget(lbl_name)
            ch.addStretch()
            ch.addWidget(lbl_desc)
            v.addWidget(card)
            self._flow_labels[st.value] = lbl_name

            if i < len(flow) - 1:
                arr = QtWidgets.QLabel("  ↓")
                arr.setStyleSheet(f"color: {_BORDER}; font-size: 11px;")
                v.addWidget(arr)

        v.addStretch()
        return w

    def _build_history_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        top = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel("状态转换历史  Transition History")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        top.addWidget(lbl)
        top.addStretch()

        btn_clear = QtWidgets.QPushButton("清空")
        btn_clear.setFixedSize(46, 22)
        btn_clear.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUT};"
            f" border: 1px solid {_BORDER}; border-radius: 3px; font-size: 11px; }}"
        )
        btn_clear.clicked.connect(self._on_clear_history)
        top.addWidget(btn_clear)
        v.addLayout(top)

        self._txt_history = QtWidgets.QTextEdit()
        self._txt_history.setReadOnly(True)
        self._txt_history.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt_history, stretch=1)
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

        h.addWidget(_btn("降级运行 Degrade",     _YLW, self._on_degrade))
        h.addWidget(_btn("开始恢复 Recovery",    _BLU, self._on_recovery))
        h.addWidget(_btn("恢复成功 Rec.Success", _GRN, self._on_rec_success))
        h.addWidget(_btn("恢复失败 Rec.Fail",    _RED, self._on_rec_fail))
        h.addWidget(_btn("消除降级 Clear",       _GRN, self._on_clear_degraded))
        h.addWidget(_btn("重置 Reset",           _MUT, self._on_reset))
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
        sm   = self._engine.state_manager
        summ = sm.summary()
        st   = sm.state.value

        color = _STATE_COLOR.get(st, _MUT)
        zh    = _STATE_ZH.get(st, st.upper())
        self._lbl_state.setText(zh)
        self._lbl_state.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: bold;")

        uptime = self._engine.uptime_seconds
        self._lbl_uptime.setText(f"运行时长  {uptime:.0f}s")
        self._lbl_transitions.setText(
            f"状态转换  {summ['transitions']} 次")

        self._highlight_flow(st)
        self._reload_history(sm)

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _on_degrade(self) -> None:
        if self._engine:
            self._engine.mark_degraded("手动触发降级")
            self.refresh()

    def _on_recovery(self) -> None:
        if self._engine:
            self._engine.start_recovery("手动进入恢复")
            self.refresh()

    def _on_rec_success(self) -> None:
        if self._engine:
            self._engine.recovery_success("手动恢复成功")
            self.refresh()

    def _on_rec_fail(self) -> None:
        if self._engine:
            self._engine.recovery_fail("手动恢复失败")
            self.refresh()

    def _on_clear_degraded(self) -> None:
        if self._engine:
            self._engine.clear_degraded("手动消除降级")
            self.refresh()

    def _on_reset(self) -> None:
        if self._engine:
            self._engine.reset("手动重置")
            self.refresh()

    def _on_clear_history(self) -> None:
        self._txt_history.clear()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _highlight_flow(self, active: str) -> None:
        for st_val, lbl in self._flow_labels.items():
            if st_val == active:
                color = _STATE_COLOR.get(st_val, _FG)
                lbl.setStyleSheet(
                    f"color: {color}; font-size: 13px;"
                    f" font-weight: bold; border: none;")
            else:
                lbl.setStyleSheet(
                    f"color: {_MUT}; font-size: 12px;"
                    f" font-weight: normal; border: none;")

    def _reload_history(self, sm) -> None:
        lines = sm.get_history_lines(limit=200)
        self._txt_history.setPlainText("\n".join(lines))
        sb = self._txt_history.verticalScrollBar()
        sb.setValue(sb.maximum())
