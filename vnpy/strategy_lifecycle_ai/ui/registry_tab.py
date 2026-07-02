"""
strategy_lifecycle_ai/ui/registry_tab.py  (Phase 1 Stub)

RegistryTab — 策略注册表面板（Phase 1：骨架占位）。
"""

from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets

_PANEL  = "#181825"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_MAV    = "#cba6f7"
_GRN    = "#a6e3a1"
_YLW    = "#f9e2af"
_RED    = "#f38ba8"

_PHASE_COLORS = {
    "registered": _MUT,
    "incubation": "#89b4fa",
    "live":       _GRN,
    "peak":       "#f9e2af",
    "decay":      "#fab387",
    "recovering": "#89dceb",
    "retired":    _RED,
    "archived":   _MUT,
}


class RegistryTab(QtWidgets.QWidget):
    """策略注册表面板（Phase 1 骨架）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QtWidgets.QLabel("Strategy Registry  策略注册表")
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 13px; font-weight: bold;")
        root.addWidget(title)

        self._table = QtWidgets.QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels([
            "策略 ID", "策略名称", "阶段", "评级",
            "Sharpe", "回撤", "注册时间"])
        self._table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(f"""
            QTableWidget {{ background: #11111b; color: {_FG};
                border: 1px solid {_BORDER}; gridline-color: {_BORDER};
                font-size: 11px; }}
            QHeaderView::section {{ background: #313244; color: {_MUT};
                padding: 4px; border: none; font-size: 10px; }}
            QTableWidget::item:alternate {{ background: #181825; }}
        """)
        root.addWidget(self._table, stretch=1)

        bar = QtWidgets.QHBoxLayout()
        btn = self._btn("Refresh  刷新", _MUT)
        btn.clicked.connect(self.refresh)
        bar.addWidget(btn)
        bar.addStretch()
        self._count_lbl = QtWidgets.QLabel("0 strategies")
        self._count_lbl.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        bar.addWidget(self._count_lbl)
        root.addLayout(bar)

    def _btn(self, text, color):
        b = QtWidgets.QPushButton(text)
        b.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {color};
                border: 1px solid {color}; border-radius: 4px;
                padding: 5px 16px; font-size: 11px; }}
            QPushButton:hover {{ background: {color}22; }}
        """)
        return b

    def refresh(self) -> None:
        if self._engine is None:
            return
        try:
            strategies = self._engine.get_all_strategies()
        except Exception:
            return
        self._table.setRowCount(0)
        for s in strategies:
            row = self._table.rowCount()
            self._table.insertRow(row)
            phase_color = _PHASE_COLORS.get(s.phase.value, _MUT)
            items = [
                s.strategy_id,
                s.strategy_name,
                s.phase.value.upper(),
                s.rating.value.upper(),
                f"{s.sharpe:.3f}",
                f"{s.max_drawdown:.2%}",
                str(s.registered_at)[:10],
            ]
            colors = [_FG, _FG, phase_color, _FG, _FG, _FG, _MUT]
            for col, (text, color) in enumerate(zip(items, colors)):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                from vnpy.trader.ui import QtGui
                item.setForeground(QtGui.QColor(color))
                self._table.setItem(row, col, item)
        self._count_lbl.setText(f"{len(strategies)} strategies")

    def update_from_event(self, data: dict) -> None:
        self.refresh()
