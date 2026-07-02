"""
quant_os/ui/control_tab.py

ControlTab — 系统控制面板（Phase 5）。

布局：
  顶部：系统健康状态 Verdict 栏 + 运行时长
  中部：左侧全局控制按钮 / 右侧控制日志
  底部：模块级快捷控制（选中模块 → 隔离 / 降级 / 健康检查）
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..engine.system_controller import SystemHealth

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_ORG      = "#fab387"

_HEALTH_COLOR = {
    SystemHealth.HEALTHY.value:  _GRN,
    SystemHealth.DEGRADED.value: _YLW,
    SystemHealth.CRITICAL.value: _RED,
    SystemHealth.STOPPED.value:  _MUT,
}


class ControlTab(QtWidgets.QWidget):
    """系统控制面板（Phase 5）。"""

    def __init__(self, os_engine=None, parent=None) -> None:
        super().__init__(parent)
        self._os_engine = os_engine
        self._init_ui()

    def set_os_engine(self, os_engine) -> None:
        self._os_engine = os_engine

    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self._build_health_bar())

        mid = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        mid.addWidget(self._build_control_panel())
        mid.addWidget(self._build_log_panel())
        mid.setSizes([320, 800])
        root.addWidget(mid, stretch=1)

        root.addWidget(self._build_module_bar())

    def _build_health_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(58)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 6px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(20, 8, 20, 8)

        self._lbl_health = QtWidgets.QLabel("系统健康状态  —  未运行")
        self._lbl_health.setStyleSheet(
            f"color: {_MUT}; font-size: 18px; font-weight: bold;")
        h.addWidget(self._lbl_health)
        h.addStretch()

        self._lbl_uptime = QtWidgets.QLabel("")
        self._lbl_uptime.setStyleSheet(f"color: {_MUT}; font-size: 12px;")
        h.addWidget(self._lbl_uptime)
        return bar

    def _build_control_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(10)

        title = QtWidgets.QLabel("全局控制")
        title.setStyleSheet(
            f"color: {_BLU}; font-size: 13px; font-weight: bold;")
        v.addWidget(title)

        btn_defs = [
            ("▶  启动系统",   _GRN, self._on_start_system),
            ("⏸  暂停系统",   _YLW, self._on_pause_system),
            ("▶  恢复系统",   _BLU, self._on_resume_system),
            ("■  停止系统",   _RED, self._on_stop_system),
        ]
        for label, color, slot in btn_defs:
            btn = QtWidgets.QPushButton(label)
            btn.setFixedHeight(36)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {color};"
                f" border: 1px solid {color}; border-radius: 4px;"
                f" padding: 4px 0px; font-size: 13px; font-weight: bold; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            btn.clicked.connect(slot)
            v.addWidget(btn)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {_BORDER};")
        v.addWidget(sep)

        btn_hc = QtWidgets.QPushButton("健康检查")
        btn_hc.setFixedHeight(32)
        btn_hc.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUT};"
            f" border: 1px solid {_BORDER}; border-radius: 4px;"
            f" padding: 4px 0px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {_BORDER}33; }}"
        )
        btn_hc.clicked.connect(self._on_health_check)
        v.addWidget(btn_hc)

        v.addStretch()
        return w

    def _build_log_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        top = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel("控制操作日志")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        top.addWidget(lbl)
        top.addStretch()
        btn_clear = QtWidgets.QPushButton("清空")
        btn_clear.setFixedSize(46, 22)
        btn_clear.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUT};"
            f" border: 1px solid {_BORDER}; border-radius: 3px; font-size: 11px; }}"
        )
        btn_clear.clicked.connect(self._on_clear_log)
        top.addWidget(btn_clear)
        v.addLayout(top)

        self._txt_ctrl_log = QtWidgets.QTextEdit()
        self._txt_ctrl_log.setReadOnly(True)
        self._txt_ctrl_log.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt_ctrl_log, stretch=1)
        return w

    def _build_module_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(46)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(8)

        lbl = QtWidgets.QLabel("模块快捷控制：")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 12px;")
        h.addWidget(lbl)

        self._cmb_module = QtWidgets.QComboBox()
        self._cmb_module.setFixedWidth(180)
        self._cmb_module.setStyleSheet(
            f"QComboBox {{ background: #11111b; color: {_FG};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 3px 8px; font-size: 12px; }}"
        )
        h.addWidget(self._cmb_module)

        def _mbtn(label, color, slot):
            b = QtWidgets.QPushButton(label)
            b.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {color};"
                f" border: 1px solid {color}; border-radius: 3px;"
                f" padding: 4px 10px; font-size: 12px; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            b.clicked.connect(slot)
            return b

        h.addWidget(_mbtn("启动", _GRN,  self._on_module_start))
        h.addWidget(_mbtn("停止", _ORG,  self._on_module_stop))
        h.addWidget(_mbtn("暂停", _YLW,  self._on_module_pause))
        h.addWidget(_mbtn("恢复", _BLU,  self._on_module_resume))
        h.addWidget(_mbtn("隔离", _RED,  self._on_module_isolate))
        h.addStretch()

        btn_r = QtWidgets.QPushButton("刷新")
        btn_r.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUT};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 4px 10px; font-size: 12px; }}"
        )
        btn_r.clicked.connect(self.refresh)
        h.addWidget(btn_r)
        return bar

    # ------------------------------------------------------------------ #
    #  公개接口
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        if self._os_engine is None:
            return
        self._update_health()
        self._update_module_combo()
        self._update_ctrl_log()

    def on_system_event(self, event_type: str, data: dict) -> None:
        self.refresh()

    # ------------------------------------------------------------------ #
    #  全局控制回调
    # ------------------------------------------------------------------ #

    def _on_start_system(self) -> None:
        if self._os_engine:
            self._os_engine.start_system()
            self.refresh()

    def _on_stop_system(self) -> None:
        if self._os_engine:
            self._os_engine.stop_system()
            self.refresh()

    def _on_pause_system(self) -> None:
        if self._os_engine:
            self._os_engine.pause_system()
            self.refresh()

    def _on_resume_system(self) -> None:
        if self._os_engine:
            self._os_engine.resume_system()
            self.refresh()

    def _on_health_check(self) -> None:
        if self._os_engine:
            self._os_engine.health_check()
            self.refresh()

    def _on_clear_log(self) -> None:
        self._txt_ctrl_log.clear()

    # ------------------------------------------------------------------ #
    #  模块控制回调
    # ------------------------------------------------------------------ #

    def _current_module(self) -> str | None:
        return self._cmb_module.currentText() or None

    def _on_module_start(self) -> None:
        m = self._current_module()
        if m and self._os_engine:
            self._os_engine.start_module(m)
            self.refresh()

    def _on_module_stop(self) -> None:
        m = self._current_module()
        if m and self._os_engine:
            self._os_engine.stop_module(m)
            self.refresh()

    def _on_module_pause(self) -> None:
        m = self._current_module()
        if m and self._os_engine:
            self._os_engine.pause_module(m)
            self.refresh()

    def _on_module_resume(self) -> None:
        m = self._current_module()
        if m and self._os_engine:
            self._os_engine.resume_module(m)
            self.refresh()

    def _on_module_isolate(self) -> None:
        m = self._current_module()
        if m and self._os_engine:
            self._os_engine.isolate_module(m, "手动隔离")
            self.refresh()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _update_health(self) -> None:
        ctrl = self._os_engine.system_controller
        h    = ctrl.health
        color = _HEALTH_COLOR.get(h.value, _MUT)
        self._lbl_health.setText(f"系统健康  {h.value.upper()}")
        self._lbl_health.setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: bold;")
        uptime = self._os_engine.uptime_seconds
        self._lbl_uptime.setText(f"运行时长 {uptime:.0f}s")

    def _update_module_combo(self) -> None:
        current = self._cmb_module.currentText()
        self._cmb_module.clear()
        for m in self._os_engine.registry.get_all():
            self._cmb_module.addItem(m.name)
        idx = self._cmb_module.findText(current)
        if idx >= 0:
            self._cmb_module.setCurrentIndex(idx)

    def _update_ctrl_log(self) -> None:
        ctrl = self._os_engine.system_controller
        lines = ctrl.get_control_log_lines(limit=200)
        self._txt_ctrl_log.setPlainText("\n".join(lines))
        sb = self._txt_ctrl_log.verticalScrollBar()
        sb.setValue(sb.maximum())
