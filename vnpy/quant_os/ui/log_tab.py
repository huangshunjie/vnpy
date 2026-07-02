"""
quant_os/ui/log_tab.py

LogTab — 系统日志流（Phase 5 升级版）。

功能：
  - 实时显示所有 OS 级事件日志
  - 事件类型过滤（下拉菜单）
  - 清空日志
  - 自动滚动到底部
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"

_EVENT_COLORS = {
    "eQuantOS.log":               _FG,
    "eQuantOS.start":             _GRN,
    "eQuantOS.stop":              _RED,
    "eQuantOS.module.registered": _BLU,
    "eQuantOS.lifecycle.change":  _YLW,
    "eQuantOS.strategy.trigger":  _BLU,
}

_FILTER_OPTIONS = [
    ("全部事件",            ""),
    ("系统日志",            "eQuantOS.log"),
    ("OS 启动/停止",        "eQuantOS.start,eQuantOS.stop"),
    ("模块注册",            "eQuantOS.module.registered"),
    ("生命周期变更",        "eQuantOS.lifecycle.change"),
    ("策略触发",            "eQuantOS.strategy.trigger"),
]


class LogTab(QtWidgets.QWidget):
    """系统日志流 Tab（Phase 5 升级版）。"""

    def __init__(self, os_engine=None, parent=None) -> None:
        super().__init__(parent)
        self._os_engine   = os_engine
        self._all_lines:  list[tuple[str, str]] = []   # (event_type, formatted_line)
        self._auto_scroll = True
        self._init_ui()

    def set_os_engine(self, os_engine) -> None:
        self._os_engine = os_engine

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        root.addWidget(self._build_toolbar())

        self._txt = QtWidgets.QTextEdit()
        self._txt.setReadOnly(True)
        self._txt.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        root.addWidget(self._txt, stretch=1)

    def _build_toolbar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(38)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(10, 4, 10, 4)
        h.setSpacing(8)

        lbl = QtWidgets.QLabel("过滤：")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 12px;")
        h.addWidget(lbl)

        self._cmb_filter = QtWidgets.QComboBox()
        for label, _ in _FILTER_OPTIONS:
            self._cmb_filter.addItem(label)
        self._cmb_filter.setFixedWidth(160)
        self._cmb_filter.setStyleSheet(
            f"QComboBox {{ background: #11111b; color: {_FG};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 3px 8px; font-size: 12px; }}"
        )
        self._cmb_filter.currentIndexChanged.connect(self._apply_filter)
        h.addWidget(self._cmb_filter)

        self._chk_auto = QtWidgets.QCheckBox("自动滚动")
        self._chk_auto.setChecked(True)
        self._chk_auto.setStyleSheet(f"color: {_MUT}; font-size: 12px;")
        self._chk_auto.stateChanged.connect(
            lambda s: setattr(self, "_auto_scroll", bool(s))
        )
        h.addWidget(self._chk_auto)

        h.addStretch()

        btn_clear = QtWidgets.QPushButton("清空")
        btn_clear.setFixedSize(54, 26)
        btn_clear.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUT};"
            f" border: 1px solid {_BORDER}; border-radius: 3px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {_BORDER}33; }}"
        )
        btn_clear.clicked.connect(self._on_clear)
        h.addWidget(btn_clear)

        self._lbl_count = QtWidgets.QLabel("0 条")
        self._lbl_count.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        h.addWidget(self._lbl_count)

        return bar

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def append_event(self, event_type: str, data: dict) -> None:
        """追加一条事件日志。"""
        from datetime import datetime
        ts  = str(datetime.now())[:19]
        msg = data.get("message") or str(data)
        line = f"[{ts}] {event_type}  {msg}"
        self._all_lines.append((event_type, line))
        if len(self._all_lines) > 2000:
            self._all_lines.pop(0)

        # 判断是否通过当前过滤
        if self._passes_filter(event_type):
            color = _EVENT_COLORS.get(event_type, _FG)
            self._txt.append(
                f"<span style='color:{color}'>{self._html_esc(line)}</span>"
            )
            if self._auto_scroll:
                sb = self._txt.verticalScrollBar()
                sb.setValue(sb.maximum())

        self._lbl_count.setText(f"{len(self._all_lines)} 条")

    def append_log_msg(self, msg: str) -> None:
        """快捷：追加一条系统日志消息。"""
        self.append_event("eQuantOS.log", {"message": msg})

    def refresh_from_engine(self) -> None:
        """从 EventBus 历史重新加载日志。"""
        if self._os_engine is None:
            return
        self._all_lines.clear()
        records = self._os_engine.event_bus.get_history(limit=500)
        for r in records:
            from datetime import datetime
            ts   = str(r.ts)[:19]
            msg  = r.data.get("message") or str(r.data)
            line = f"[{ts}] {r.event_type}  {msg}"
            self._all_lines.append((r.event_type, line))
        self._apply_filter()

    def on_system_log(self, event_type: str, data: dict) -> None:
        """响应 EVENT_SYSTEM_LOG 事件回调（由 EventBus 调用）。"""
        self.append_event(event_type, data)

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    def _passes_filter(self, event_type: str) -> bool:
        idx   = self._cmb_filter.currentIndex()
        _, pattern = _FILTER_OPTIONS[idx]
        if not pattern:
            return True
        return event_type in pattern.split(",")

    def _apply_filter(self) -> None:
        idx = self._cmb_filter.currentIndex()
        _, pattern = _FILTER_OPTIONS[idx]
        self._txt.clear()
        for etype, line in self._all_lines:
            if not pattern or etype in pattern.split(","):
                color = _EVENT_COLORS.get(etype, _FG)
                self._txt.append(
                    f"<span style='color:{color}'>{self._html_esc(line)}</span>"
                )
        if self._auto_scroll:
            sb = self._txt.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _on_clear(self) -> None:
        self._all_lines.clear()
        self._txt.clear()
        self._lbl_count.setText("0 条")

    @staticmethod
    def _html_esc(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
