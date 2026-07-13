"""
risk_engine_2/ui/alert_tab.py

AlertTab — 实时预警面板 + 历史记录（Phase 3 实现）。

顶部：未确认预警横幅（红色高亮）
中部：历史预警记录表格
底部：批量确认 + 清除按钮
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import RiskLevel, RiskAction
from ..model.drawdown_model import AlertRecord

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

_LEVEL_COLOR = {
    RiskLevel.NORMAL:   _GRN,
    RiskLevel.WARNING:  _YLW,
    RiskLevel.CRITICAL: _ORG,
    RiskLevel.BREACH:   _RED,
}

_ACTION_COLOR = {
    RiskAction.ALERT:           _BLU,
    RiskAction.BLOCK:           _ORG,
    RiskAction.REDUCE_POSITION: _YLW,
    RiskAction.HALT_TRADING:    _RED,
}

_COLS = [
    ("时间",      70),
    ("类型",      100),
    ("等级",      65),
    ("动作",      100),
    ("触发值",     80),
    ("阈值",       70),
    ("消息",      320),
    ("已确认",     65),
]


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    item = QtWidgets.QTableWidgetItem(str(text))
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    item.setForeground(QtGui.QColor(color))
    return item


class AlertTab(QtWidgets.QWidget):
    """预警面板 Tab（Phase 3）。"""

    acknowledge_requested = QtCore.Signal(str)   # alert_id
    ack_all_requested     = QtCore.Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._records: list[AlertRecord] = []
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # 未确认预警横幅
        self._banner = QtWidgets.QLabel("暂无未确认预警")
        self._banner.setStyleSheet(
            f"background: {_PANEL_BG}; color: {_MUT}; font-size: 12px;"
            f" font-weight: bold; border-radius: 4px; padding: 6px 12px;"
        )
        self._banner.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._banner.setFixedHeight(38)
        root.addWidget(self._banner)

        # 汇总行
        root.addWidget(self._build_summary_bar())

        # 历史记录表格
        root.addWidget(self._build_table(), stretch=1)

        # 底部按钮
        root.addWidget(self._build_buttons())

    # ------------------------------------------------------------------ #
    #  子区域构建
    # ------------------------------------------------------------------ #

    def _build_summary_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 4, 12, 4)
        h.setSpacing(20)
        cards = [
            ("总预警数",   "0", _FG),
            ("未确认",     "0", _RED),
            ("CRITICAL",   "0", _ORG),
            ("BREACH",     "0", _RED),
            ("自动动作",   "0", _YLW),
        ]
        self._sum: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in cards:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(0)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._sum[name] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_table(self) -> QtWidgets.QTableWidget:
        self._tbl = QtWidgets.QTableWidget(0, len(_COLS))
        self._tbl.setHorizontalHeaderLabels([c[0] for c in _COLS])
        for i, (_, w) in enumerate(_COLS):
            self._tbl.setColumnWidth(i, w)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._tbl.setStyleSheet("font-size: 12px;")
        self._tbl.doubleClicked.connect(self._on_row_double_click)
        return self._tbl

    def _build_buttons(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        btn_ack = QtWidgets.QPushButton("全部确认")
        btn_ack.setStyleSheet(
            f"QPushButton {{ background: {_BLU}; color: #1e1e2e; border-radius: 4px;"
            f" padding: 5px 12px; font-size: 12px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: #b4befe; }}"
        )
        btn_ack.clicked.connect(self.ack_all_requested.emit)

        btn_clear = QtWidgets.QPushButton("清除已确认")
        btn_clear.setStyleSheet(
            f"QPushButton {{ background: #313244; color: {_MUT}; border-radius: 4px;"
            f" padding: 5px 12px; font-size: 12px; }}"
        )
        btn_clear.clicked.connect(self._clear_acknowledged)

        h.addWidget(btn_ack)
        h.addWidget(btn_clear)
        h.addStretch()
        return w

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def add_alert(self, record: AlertRecord) -> None:
        """追加单条预警（实时模式）。"""
        self._records.append(record)
        self._append_row(record)
        self._refresh_summary()
        self._refresh_banner()

    def refresh_all(self, records: list[AlertRecord]) -> None:
        """全量刷新。"""
        self._tbl.setRowCount(0)
        self._records = list(records)
        for rec in sorted(records, key=lambda r: r.triggered_at, reverse=True):
            self._append_row(rec)
        self._refresh_summary()
        self._refresh_banner()

    def mark_acknowledged(self, alert_id: str) -> None:
        """更新表格中已确认状态。"""
        for row in range(self._tbl.rowCount()):
            if self._tbl.item(row, 0) and self._tbl.item(row, 0).toolTip() == alert_id:
                self._tbl.setItem(row, 7, _item("✔", _GRN))
        self._refresh_banner()

    def clear(self) -> None:
        self._records.clear()
        self._tbl.setRowCount(0)
        self._refresh_summary()
        self._banner.setText("暂无未确认预警")
        self._banner.setStyleSheet(
            f"background: {_PANEL_BG}; color: {_MUT}; font-size: 12px;"
            f" font-weight: bold; border-radius: 4px; padding: 6px 12px;"
        )

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _append_row(self, rec: AlertRecord) -> None:
        row = self._tbl.rowCount()
        self._tbl.insertRow(row)

        lv_color  = _LEVEL_COLOR.get(rec.risk_level,  _FG)
        act_color = _ACTION_COLOR.get(rec.action, _FG)

        ts_item = _item(rec.ts_str, _MUT)
        ts_item.setToolTip(rec.alert_id)      # 用 toolTip 存 alert_id
        self._tbl.setItem(row, 0, ts_item)
        self._tbl.setItem(row, 1, _item(rec.alert_type.value,      _FG))
        self._tbl.setItem(row, 2, _item(rec.level_str,          lv_color))
        self._tbl.setItem(row, 3, _item(rec.action.value,      act_color))
        self._tbl.setItem(row, 4, _item(f"{rec.triggered_value:.4%}", lv_color))
        self._tbl.setItem(row, 5, _item(f"{rec.threshold:.4%}",   _MUT))
        self._tbl.setItem(row, 6, _item(rec.message,              _FG))
        ack_str   = "✔" if rec.acknowledged else "—"
        ack_color = _GRN if rec.acknowledged else _MUT
        self._tbl.setItem(row, 7, _item(ack_str, ack_color))
        self._tbl.scrollToBottom()

    def _refresh_summary(self) -> None:
        n       = len(self._records)
        unack   = sum(1 for r in self._records if not r.acknowledged)
        crits   = sum(1 for r in self._records if r.risk_level == RiskLevel.CRITICAL)
        breach  = sum(1 for r in self._records if r.risk_level == RiskLevel.BREACH)
        auto    = sum(1 for r in self._records
                      if r.action in (RiskAction.HALT_TRADING, RiskAction.REDUCE_POSITION))
        self._sum["总预警数"].setText(str(n))
        self._sum["未确认"  ].setText(str(unack))
        self._sum["CRITICAL"].setText(str(crits))
        self._sum["BREACH"  ].setText(str(breach))
        self._sum["自动动作"].setText(str(auto))

    def _refresh_banner(self) -> None:
        unack = [r for r in self._records if not r.acknowledged]
        if not unack:
            self._banner.setText("暂无未确认预警")
            self._banner.setStyleSheet(
                f"background: {_PANEL_BG}; color: {_MUT}; font-size: 12px;"
                f" font-weight: bold; border-radius: 4px; padding: 6px 12px;"
            )
        else:
            latest = unack[-1]
            color  = _LEVEL_COLOR.get(latest.risk_level, _YLW)
            self._banner.setText(
                f"[{latest.level_str.upper()}] {latest.message}"
                f"  —  共 {len(unack)} 条未确认"
            )
            self._banner.setStyleSheet(
                f"background: #2a1f2e; color: {color}; font-size: 12px;"
                f" font-weight: bold; border: 1px solid {color};"
                f" border-radius: 4px; padding: 6px 12px;"
            )

    def _clear_acknowledged(self) -> None:
        self._records = [r for r in self._records if not r.acknowledged]
        self._tbl.setRowCount(0)
        for rec in self._records:
            self._append_row(rec)
        self._refresh_summary()

    def _on_row_double_click(self, index) -> None:
        row = index.row()
        item = self._tbl.item(row, 0)
        if item:
            alert_id = item.toolTip()
            if alert_id:
                self.acknowledge_requested.emit(alert_id)
