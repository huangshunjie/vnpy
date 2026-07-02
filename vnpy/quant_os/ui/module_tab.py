"""
quant_os/ui/module_tab.py

ModuleTab — 模块注册中心 UI（Phase 2 实现）。

布局：
  顶部：模块统计 KPI 卡片（总数 / 运行中 / 错误数）
  中部：模块状态表格（名称 / 类型 / 状态 / 注册时间 / 运行时长 / 事件数）
  底部：模块操作按钮栏（启动 / 停止 / 暂停 / 恢复 / 标记错误）
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import ModuleState

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
    "init":    _MUT,
    "running": _GRN,
    "paused":  _YLW,
    "stopped": _ORG,
    "error":   _RED,
}

_TABLE_COLS = [
    ("模块名称",   140),
    ("类型",        80),
    ("状态",        70),
    ("注册时间",   140),
    ("启动时间",   140),
    ("运行时长(s)", 90),
    ("事件数",      60),
    ("错误数",      60),
    ("描述",       180),
]


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    it.setForeground(QtGui.QColor(color))
    return it


def _item_left(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
    )
    it.setForeground(QtGui.QColor(color))
    return it


class ModuleTab(QtWidgets.QWidget):
    """模块注册中心 Tab（Phase 2）。"""

    def __init__(self, os_engine=None, parent=None) -> None:
        super().__init__(parent)
        self._os_engine = os_engine
        self._init_ui()

    def set_os_engine(self, os_engine) -> None:
        self._os_engine = os_engine

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_kpi_bar())
        root.addWidget(self._build_table(), stretch=1)
        root.addWidget(self._build_action_bar())

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(66)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(16, 6, 16, 6)
        h.setSpacing(28)

        kpis = [
            ("已注册模块",  "0",  _FG),
            ("运行中",       "0",  _GRN),
            ("已停止",       "0",  _ORG),
            ("异常模块",     "0",  _RED),
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
                f"color: {color}; font-size: 14px; font-weight: bold;"
            )
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._kpi[name] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_table(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        lbl = QtWidgets.QLabel("已注册模块列表")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._tbl = QtWidgets.QTableWidget(0, len(_TABLE_COLS))
        self._tbl.setHorizontalHeaderLabels([c[0] for c in _TABLE_COLS])
        for i, (_, w_) in enumerate(_TABLE_COLS):
            self._tbl.setColumnWidth(i, w_)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._tbl.setStyleSheet("font-size: 12px;")
        v.addWidget(self._tbl, stretch=1)
        return w

    def _build_action_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(46)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(10)

        btn_defs = [
            ("启动模块",   _GRN,  self._on_start),
            ("停止模块",   _ORG,  self._on_stop),
            ("暂停模块",   _YLW,  self._on_pause),
            ("恢复运行",   _BLU,  self._on_resume),
            ("标记错误",   _RED,  self._on_error),
        ]
        for label, color, slot in btn_defs:
            btn = QtWidgets.QPushButton(label)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {color};"
                f" border: 1px solid {color}; border-radius: 3px;"
                f" padding: 4px 14px; font-size: 12px; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            btn.clicked.connect(slot)
            h.addWidget(btn)

        h.addStretch()

        self._btn_refresh = QtWidgets.QPushButton("刷新")
        self._btn_refresh.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUT};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 4px 14px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {_BORDER}33; }}"
        )
        self._btn_refresh.clicked.connect(self.refresh)
        h.addWidget(self._btn_refresh)
        return bar

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        """从 OSEngine 拉取最新模块信息并刷新表格。"""
        if self._os_engine is None:
            return
        modules = self._os_engine.registry.get_all()
        self._refresh_table(modules)
        self._refresh_kpi(modules)

    def on_module_registered(self, event_type: str, data: dict) -> None:
        """响应 EVENT_MODULE_REGISTERED，追加一行。"""
        self.refresh()

    def on_lifecycle_change(self, event_type: str, data: dict) -> None:
        """响应 EVENT_LIFECYCLE_CHANGE，刷新对应行状态。"""
        self.refresh()

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _selected_module_name(self) -> str | None:
        rows = self._tbl.selectedItems()
        if not rows:
            return None
        row = self._tbl.currentRow()
        item = self._tbl.item(row, 0)
        return item.text() if item else None

    def _on_start(self) -> None:
        name = self._selected_module_name()
        if name and self._os_engine:
            self._os_engine.start_module(name)
            self.refresh()

    def _on_stop(self) -> None:
        name = self._selected_module_name()
        if name and self._os_engine:
            self._os_engine.stop_module(name)
            self.refresh()

    def _on_pause(self) -> None:
        name = self._selected_module_name()
        if name and self._os_engine:
            self._os_engine.pause_module(name)
            self.refresh()

    def _on_resume(self) -> None:
        name = self._selected_module_name()
        if name and self._os_engine:
            self._os_engine.resume_module(name)
            self.refresh()

    def _on_error(self) -> None:
        name = self._selected_module_name()
        if name and self._os_engine:
            self._os_engine.mark_error(name, "手动标记错误")
            self.refresh()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _refresh_table(self, modules) -> None:
        self._tbl.setRowCount(0)
        for m in modules:
            row = self._tbl.rowCount()
            self._tbl.insertRow(row)
            state_color = _STATE_COLOR.get(m.state.value, _FG)
            uptime = f"{m.uptime_seconds:.0f}" if m.started_at else "—"
            self._tbl.setItem(row, 0, _item_left(m.name,                _FG))
            self._tbl.setItem(row, 1, _item(m.module_type.value,        _MUT))
            self._tbl.setItem(row, 2, _item(m.state.value.upper(),      state_color))
            self._tbl.setItem(row, 3, _item(str(m.registered_at)[:19],  _MUT))
            self._tbl.setItem(row, 4, _item(str(m.started_at)[:19] if m.started_at else "—", _MUT))
            self._tbl.setItem(row, 5, _item(uptime,                     _FG))
            self._tbl.setItem(row, 6, _item(str(m.event_count),         _FG))
            self._tbl.setItem(row, 7, _item(str(m.error_count),
                _RED if m.error_count > 0 else _MUT))
            self._tbl.setItem(row, 8, _item_left(m.description or "—",  _MUT))

    def _refresh_kpi(self, modules) -> None:
        total   = len(modules)
        running = sum(1 for m in modules if m.state == ModuleState.RUNNING)
        stopped = sum(1 for m in modules if m.state == ModuleState.STOPPED)
        errors  = sum(1 for m in modules if m.state == ModuleState.ERROR)

        self._kpi["已注册模块"].setText(str(total))
        self._kpi["运行中"    ].setText(str(running))
        self._kpi["已停止"    ].setText(str(stopped))
        self._kpi["异常模块"  ].setText(str(errors))
        self._kpi["异常模块"  ].setStyleSheet(
            f"color: {_RED if errors > 0 else _MUT};"
            f" font-size: 14px; font-weight: bold;"
        )
