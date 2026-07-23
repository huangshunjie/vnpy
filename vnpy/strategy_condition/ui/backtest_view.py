"""
strategy_condition/ui/backtest_view.py
回测结果视图：指标统计卡片 + 逐笔交易明细表
"""
from __future__ import annotations
from typing import List, Optional

from vnpy.trader.ui import QtWidgets, QtCore, QtGui

from ..core.signal import SignalRecord, SignalBatch

_BG   = "#1e1e2e"; _PAN2 = "#11111b"; _BORD = "#45475a"
_FG   = "#cdd6f4"; _MUT  = "#6c7086"; _BLU  = "#89b4fa"
_GRN  = "#a6e3a1"; _YLW  = "#f9e2af"; _RED  = "#f38ba8"
_MAV  = "#cba6f7"


def _lbl(text: str, color: str = _FG, size: int = 13,
         bold: bool = False) -> QtWidgets.QLabel:
    w = QtWidgets.QLabel(text)
    w.setStyleSheet(
        f"color:{color};font-size:{size}px;"
        f"font-weight:{'bold' if bold else 'normal'};"
        f"background:transparent;border:none;")
    return w


def _card(title: str, value: str, color: str = _FG) -> QtWidgets.QWidget:
    """指标卡片控件"""
    w = QtWidgets.QWidget()
    w.setStyleSheet(
        f"background:{_PAN2};border:1px solid {_BORD};"
        f"border-radius:6px;")
    v = QtWidgets.QVBoxLayout(w)
    v.setContentsMargins(12, 8, 12, 8)
    v.setSpacing(2)
    v.addWidget(_lbl(title, _MUT, 11))
    v.addWidget(_lbl(value, color, 18, True))
    return w


class TradeTableModel(QtCore.QAbstractTableModel):
    """逐笔交易明细数据模型"""

    HEADERS = ["代码", "买入日", "卖出日", "持仓天", "买入价", "卖出价", "收益%", "退出原因"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._records: List[SignalRecord] = []

    def load(self, records: List[SignalRecord]) -> None:
        self.beginResetModel()
        self._records = records
        self.endResetModel()

    def rowCount(self, _=None) -> int: return len(self._records)
    def columnCount(self, _=None) -> int: return len(self.HEADERS)

    def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if orientation == QtCore.Qt.Orientation.Horizontal:
                return self.HEADERS[section]
        if role == QtCore.Qt.ItemDataRole.ForegroundRole:
            return QtGui.QColor(_MUT)
        return None

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        rec = self._records[index.row()]
        col = index.column()

        def format_datetime(dt):
            """智能格式化：日线只显示日期，分钟线显示日期+时间"""
            s = str(dt)
            if " 00:00:00" in s:
                return s[:10]
            else:
                # 去掉末尾的 seconds 部分，只保留 YYYY-MM-DD HH:MM
                return s[:16]

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            pnl = f"{rec.pnl_pct*100:.2f}%" if rec.pnl_pct is not None else "—"
            buy_date_str = format_datetime(rec.dt) if rec.dt else "—"
            exit_date_str = format_datetime(rec.exit_dt) if rec.exit_dt else "—"
            vals = [
                rec.symbol,
                buy_date_str,
                exit_date_str,
                str(rec.hold_days),
                f"{rec.price:.2f}",
                f"{rec.exit_price:.2f}" if rec.exit_price else "—",
                pnl,
                rec.exit_reason or "—",
            ]
            return vals[col]

        if role == QtCore.Qt.ItemDataRole.ForegroundRole:
            if col == 6 and rec.pnl_pct is not None:
                return QtGui.QColor(_GRN if rec.pnl_pct > 0 else _RED)
            if col == 7:
                colors = {"stop_loss": _RED, "take_profit": _GRN,
                          "trailing_stop": _GRN, "max_hold": _YLW}
                return QtGui.QColor(colors.get(rec.exit_reason, _MUT))
            return QtGui.QColor(_FG)

        if role == QtCore.Qt.ItemDataRole.BackgroundRole:
            return QtGui.QColor(_PAN2 if index.row() % 2 == 0 else "#1a1a2e")

        return None


class BacktestView(QtWidgets.QWidget):
    """回测结果视图：指标卡片 + 逐笔交易明细"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        # ── 指标卡片行 ────────────────────────────────────────────────
        self._card_row = QtWidgets.QHBoxLayout()
        self._card_row.setSpacing(8)
        self._cards: dict = {}
        for key, title in [
            ("hit_rate",    "胜率"),
            ("avg_return",  "平均收益%"),
            ("max_return",  "最大收益%"),
            ("min_return",  "最大亏损%"),
            ("count",       "交易笔数"),
        ]:
            c = _card(title, "—", _FG)
            self._cards[key] = c
            self._card_row.addWidget(c)
        v.addLayout(self._card_row)

        # 退出原因分布
        self._exit_lbl = _lbl("退出原因：—", _MUT, 12)
        v.addWidget(self._exit_lbl)

        # ── 逐笔明细表 ────────────────────────────────────────────────
        v.addWidget(_lbl("逐笔交易明细", _YLW, 13, True))
        self._model = TradeTableModel()
        self._table = QtWidgets.QTableView()
        self._table.setModel(self._model)
        self._table.setStyleSheet(
            f"QTableView{{background:{_PAN2};color:{_FG};"
            f"border:1px solid {_BORD};border-radius:4px;"
            f"gridline-color:{_BORD};font-size:13px;"
            f"selection-background-color:{_BLU};}}"
            f"QHeaderView::section{{background:{_BG};color:{_MUT};"
            f"border:none;border-bottom:1px solid {_BORD};"
            f"padding:4px 8px;font-size:12px;}}"
            f"QScrollBar:vertical{{background:{_PAN2};width:8px;border:none;}}"
            f"QScrollBar::handle:vertical{{background:{_BORD};border-radius:4px;}}"
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        for i, w in enumerate([70, 90, 90, 60, 70, 70, 80, 100]):
            self._table.setColumnWidth(i, w)
        v.addWidget(self._table, 1)

    def load_batch(self, batch: SignalBatch) -> None:
        """加载回测结果批次"""
        m = batch.backtest_metrics()
        if not m.get("valid"):
            self._reset_cards()
            self._model.load([])
            return

        def _fmt_card(key, val_key, fmt="{:.1f}"):
            raw = m.get(val_key)
            text = fmt.format(raw) if raw is not None else "—"
            color = _FG
            if val_key == "hit_rate":
                color = _GRN if raw and raw >= 0.5 else _RED
            elif val_key in ("avg_return", "max_return"):
                color = _GRN if raw and raw > 0 else _RED
            elif val_key == "min_return":
                color = _RED if raw and raw < 0 else _GRN
            w = self._cards[key]
            lbl = w.findChildren(QtWidgets.QLabel)
            if len(lbl) >= 2:
                lbl[1].setText(text)
                lbl[1].setStyleSheet(
                    f"color:{color};font-size:18px;font-weight:bold;"
                    f"background:transparent;border:none;")

        _fmt_card("hit_rate",   "hit_rate",   "{:.1%}")
        _fmt_card("avg_return", "avg_return",  "{:.2f}%")
        _fmt_card("max_return", "max_return",  "{:.2f}%")
        _fmt_card("min_return", "min_return",  "{:.2f}%")
        _fmt_card("count",      "count",       "{}")

        reasons = m.get("exit_reasons", {})
        reason_text = "  ".join(f"{k}:{v}" for k, v in reasons.items())
        self._exit_lbl.setText(f"退出原因：{reason_text or '—'}")

        finished = [s for s in batch.signals if s.pnl_pct is not None]
        self._model.load(finished)

    def _reset_cards(self) -> None:
        for w in self._cards.values():
            lbls = w.findChildren(QtWidgets.QLabel)
            if len(lbls) >= 2:
                lbls[1].setText("—")
        self._exit_lbl.setText("退出原因：—")
