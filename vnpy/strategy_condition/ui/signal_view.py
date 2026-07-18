"""
strategy_condition/ui/signal_view.py

三段式信号结果视图：
  第一部分：选股结果表（含导出CSV）
  第二部分：回测摘要卡片
  第三部分：触发明细表（可排序）
"""
from __future__ import annotations
from typing import Dict, List, Optional
import csv

from vnpy.trader.ui import QtWidgets, QtCore, QtGui

from ..core.signal import SignalRecord, SignalBatch
from ..constant import SignalType, SignalSource

_BG    = "#1e1e2e"; _PANEL = "#181825"; _PAN2 = "#11111b"
_BORD  = "#45475a"; _FG   = "#cdd6f4"; _MUT  = "#6c7086"
_BLU   = "#89b4fa"; _GRN  = "#a6e3a1"; _YLW  = "#f9e2af"
_RED   = "#f38ba8"; _MAV  = "#cba6f7"; _ORG  = "#fab387"

_TBL_SS = (
    f"QTableWidget{{background:{_PAN2};color:{_FG};"
    f"border:none;gridline-color:{_BORD};font-size:13px;}}"
    f"QTableWidget::item{{padding:3px 8px;}}"
    f"QTableWidget::item:selected{{background:{_BLU};color:#1e1e2e;}}"
    f"QHeaderView::section{{background:{_PANEL};color:{_MUT};"
    f"border:none;border-bottom:1px solid {_BORD};"
    f"padding:4px 8px;font-size:12px;font-weight:bold;}}"
    f"QScrollBar:vertical{{background:{_PAN2};width:8px;border:none;}}"
    f"QScrollBar::handle:vertical{{background:{_BORD};border-radius:4px;}}"
)


def _lbl(text: str, color: str = _FG, size: int = 13,
         bold: bool = False) -> QtWidgets.QLabel:
    w = QtWidgets.QLabel(text)
    w.setStyleSheet(
        f"color:{color};font-size:{size}px;"
        f"font-weight:{'bold' if bold else 'normal'};"
        f"background:transparent;border:none;")
    return w


def _hline() -> QtWidgets.QFrame:
    f = QtWidgets.QFrame()
    f.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    f.setStyleSheet(f"border:none;border-top:1px solid {_BORD};")
    return f


def _reason_cn(r: str) -> str:
    return {"trailing_stop": "追踪止盈", "take_profit": "固定止盈",
            "stop_loss": "止损", "max_hold": "持仓到期",
            "sell_tree": "卖出条件", "ma_break_down": "跌破均线",
            "macd_death_sell": "MACD死叉"}.get(r, r)


def _hit_rate_map(signals: List[SignalRecord]) -> Dict[str, str]:
    from collections import defaultdict
    wins: Dict[str, int] = defaultdict(int)
    total: Dict[str, int] = defaultdict(int)
    for s in signals:
        if s.pnl_pct is not None:
            total[s.symbol] += 1
            if s.pnl_pct > 0:
                wins[s.symbol] += 1
    return {sym: f"{wins.get(sym,0)}/{n}  ({wins.get(sym,0)/n*100:.0f}%)"
            for sym, n in total.items()}


# ── 统计卡片 ─────────────────────────────────────────────────────────

class _StatCard(QtWidgets.QWidget):
    def __init__(self, title: str, color: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background:{_PANEL};border:1px solid {color};"
            "border-radius:6px;min-height:68px;")
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(10, 6, 10, 6)
        v.setSpacing(2)
        v.addWidget(_lbl(title, color, 12, True))
        self._val = QtWidgets.QLabel("—")
        self._val.setStyleSheet(
            f"color:{color};font-size:20px;font-weight:bold;"
            "background:transparent;border:none;")
        self._val.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self._val)

    def set(self, text: str) -> None:
        self._val.setText(text)


# ── 可点击列头排序的 QTableWidget ─────────────────────────────────────

class _SortableTable(QtWidgets.QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSortingEnabled(False)
        self.horizontalHeader().sectionClicked.connect(self._on_hdr)
        self._sort_col = -1
        self._sort_asc = True

    def _on_hdr(self, col: int) -> None:
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = False
        self.sortItems(col,
            QtCore.Qt.SortOrder.AscendingOrder if self._sort_asc
            else QtCore.Qt.SortOrder.DescendingOrder)

    def add_row(self, cells) -> None:
        """cells: [(text, color, sort_key_or_None), ...]"""
        row = self.rowCount()
        self.insertRow(row)
        for col, (text, color, sort_key) in enumerate(cells):
            item = QtWidgets.QTableWidgetItem(text)
            item.setForeground(QtGui.QColor(color))
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            if sort_key is not None:
                item.setData(QtCore.Qt.ItemDataRole.UserRole, sort_key)
            self.setItem(row, col, item)


# ══════════════════════════════════════════════════════════════════════
# 主视图
# ══════════════════════════════════════════════════════════════════════

class SignalView(QtWidgets.QWidget):
    """
    三段式信号结果视图。
    load_batch / load_signals / clear 接口与旧版保持兼容。
    """
    signal_selected = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._batch:     object                    = None
        self._bt_sigs:   List[SignalRecord]        = []
        self._scan_sigs: List[SignalRecord]        = []
        self._hit_map:   Dict[str, str]            = {}
        self._init_ui()

    # ── 构建 UI ──────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setStyleSheet(f"background:{_BG};")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 8)
        root.setSpacing(8)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        splitter.setHandleWidth(5)
        splitter.setStyleSheet(
            "QSplitter::handle{background:#313244;}"
            "QSplitter::handle:hover{background:#89b4fa;}"
        )

        # ── 第一部分：选股结果 ────────────────────────────────────────
        sec1 = QtWidgets.QWidget(); sec1.setStyleSheet(f"background:{_BG};")
        v1 = QtWidgets.QVBoxLayout(sec1)
        v1.setContentsMargins(0, 0, 0, 0); v1.setSpacing(4)

        hdr1 = QtWidgets.QHBoxLayout()
        hdr1.addWidget(_lbl("◌ 选股结果  Screening Results", _BLU, 13, True))
        hdr1.addStretch()
        self._scan_count_lbl = _lbl("共 0 只", _MUT, 12)
        hdr1.addWidget(self._scan_count_lbl)
        self._btn_export_scan = QtWidgets.QPushButton("导出 CSV")
        self._btn_export_scan.setStyleSheet(
            f"QPushButton{{background:{_PANEL};color:{_BLU};"
            f"border:1px solid {_BLU};border-radius:4px;"
            f"padding:3px 10px;font-size:12px;}}"
            f"QPushButton:hover{{background:{_BLU};color:#1e1e2e;}}"
        )
        self._btn_export_scan.clicked.connect(self._export_scan_csv)
        hdr1.addWidget(self._btn_export_scan)
        v1.addLayout(hdr1)

        self._scan_table = _SortableTable()
        self._scan_table.setColumnCount(5)
        self._scan_table.setHorizontalHeaderLabels(
            ["代码", "时间", "买入价",
             "策略", "类型"])
        self._scan_table.setStyleSheet(_TBL_SS)
        self._scan_table.horizontalHeader().setStretchLastSection(True)
        self._scan_table.verticalHeader().setVisible(False)
        self._scan_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._scan_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._scan_table.clicked.connect(self._on_scan_row_clicked)
        v1.addWidget(self._scan_table)
        splitter.addWidget(sec1)

        # ── 第二部分：回测摘要 ────────────────────────────────────────
        sec2 = QtWidgets.QWidget(); sec2.setStyleSheet(f"background:{_BG};")
        v2 = QtWidgets.QVBoxLayout(sec2)
        v2.setContentsMargins(0, 4, 0, 0); v2.setSpacing(6)
        v2.addWidget(_lbl("◌ 回测摘要  Backtest Summary", _GRN, 13, True))

        cards_row = QtWidgets.QHBoxLayout(); cards_row.setSpacing(8)
        self._cards: Dict[str, _StatCard] = {}
        for key, title, color in [
            ("count",    "回测笔数",  _BLU),
            ("hit_rate", "命中率",         _GRN),
            ("avg_ret",  "平均收益",   _GRN),
            ("max_ret",  "最大盈利",   _GRN),
            ("min_ret",  "最大亏损",   _RED),
            ("exit_tp",  "止盈退出",   _YLW),
            ("exit_sl",  "止损退出",   _RED),
            ("exit_mh",  "持仓到期",   _ORG),
        ]:
            card = _StatCard(title, color)
            self._cards[key] = card
            cards_row.addWidget(card, stretch=1)
        v2.addLayout(cards_row)
        splitter.addWidget(sec2)

        # ── 第三部分：触发明细 ────────────────────────────────────────
        sec3 = QtWidgets.QWidget(); sec3.setStyleSheet(f"background:{_BG};")
        v3 = QtWidgets.QVBoxLayout(sec3)
        v3.setContentsMargins(0, 4, 0, 0); v3.setSpacing(4)

        hdr3 = QtWidgets.QHBoxLayout()
        hdr3.addWidget(_lbl("◌ 触发明细  Trigger Detail", _YLW, 13, True))
        hdr3.addStretch()
        self._detail_count_lbl = _lbl("共 0 笔", _MUT, 12)
        hdr3.addWidget(self._detail_count_lbl)

        self._sort_cb = QtWidgets.QComboBox()
        self._sort_cb.addItems([
            "按收益% 降序",
            "按收益% 升序",
            "按持仓天 升序",
            "按代码 A→Z",
        ])
        self._sort_cb.setFixedWidth(130)
        self._sort_cb.setEnabled(False)
        self._sort_cb.setStyleSheet(
            f"QComboBox{{background:{_PAN2};color:{_FG};"
            f"border:1px solid {_BORD};border-radius:4px;"
            f"padding:2px 8px;font-size:12px;}}"
            f"QComboBox QAbstractItemView{{background:{_PAN2};color:{_FG};}}"
        )
        self._sort_cb.currentIndexChanged.connect(self._on_sort_changed)
        hdr3.addWidget(_lbl("排序：", _MUT, 12))
        hdr3.addWidget(self._sort_cb)

        self._btn_export_bt = QtWidgets.QPushButton("导出 CSV")
        self._btn_export_bt.setStyleSheet(
            f"QPushButton{{background:{_PANEL};color:{_YLW};"
            f"border:1px solid {_YLW};border-radius:4px;"
            f"padding:3px 10px;font-size:12px;}}"
            f"QPushButton:hover{{background:{_YLW};color:#1e1e2e;}}"
        )
        self._btn_export_bt.clicked.connect(self._export_bt_csv)
        hdr3.addWidget(self._btn_export_bt)
        v3.addLayout(hdr3)

        self._detail_table = _SortableTable()
        self._detail_table.setColumnCount(9)
        self._detail_table.setHorizontalHeaderLabels([
            "代码", "买入日", "卖出日",
            "持仓天", "买入价", "卖出价",
            "收益%", "命中率", "退出原因",
        ])
        self._detail_table.setStyleSheet(_TBL_SS)
        self._detail_table.horizontalHeader().setStretchLastSection(True)
        self._detail_table.verticalHeader().setVisible(False)
        self._detail_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._detail_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._detail_table.clicked.connect(self._on_detail_row_clicked)
        v3.addWidget(self._detail_table)
        splitter.addWidget(sec3)

        splitter.setSizes([200, 130, 400])
        root.addWidget(splitter, 1)

    # ── 数据加载（对外接口） ─────────────────────────────────────────

    def load_batch(self, batch: SignalBatch) -> None:
        self._batch = batch
        is_bt = (batch.source == SignalSource.BACKTEST or
                 any(s.pnl_pct is not None for s in batch.signals))
        if is_bt:
            self._bt_sigs   = [s for s in batch.signals if s.pnl_pct is not None]
            self._scan_sigs = []
            self._hit_map   = _hit_rate_map(self._bt_sigs)
            self._fill_scan_from_bt()
            self._fill_summary(batch)
            self._fill_detail(self._bt_sigs)
            self._sort_cb.setEnabled(True)
        else:
            self._scan_sigs = list(batch.signals)
            self._bt_sigs   = []
            self._hit_map   = {}
            self._fill_scan_only()
            self._clear_summary()
            self._fill_detail([])
            self._sort_cb.setEnabled(False)

    def load_signals(self, signals: list) -> None:
        self._scan_sigs = list(signals)
        self._fill_scan_only()

    def clear(self) -> None:
        self._scan_table.setRowCount(0)
        self._detail_table.setRowCount(0)
        self._clear_summary()
        self._scan_count_lbl.setText("共 0 只")
        self._detail_count_lbl.setText("共 0 笔")

    # ── 填充第一部分 ─────────────────────────────────────────────────

    def _fill_scan_only(self) -> None:
        t = self._scan_table
        t.setColumnCount(5)
        t.setHorizontalHeaderLabels([
            "代码", "时间", "买入价",
            "策略", "类型"])
        t.setRowCount(0)
        for s in self._scan_sigs:
            t.add_row([
                (s.symbol,         _FG,  s.symbol),
                (str(s.dt)[:10],   _MUT, str(s.dt)[:10]),
                (f"{s.price:.2f}", _FG,  s.price),
                (s.strategy_name,  _BLU, s.strategy_name),
                (s.signal_type.value,
                 _GRN if s.signal_type == SignalType.BUY else _RED,
                 s.signal_type.value),
            ])
        t.resizeColumnsToContents()
        self._scan_count_lbl.setText(f"共 {len(self._scan_sigs)} 只")

    def _fill_scan_from_bt(self) -> None:
        """回测模式：按股票聚合，显示回测笔数/命中率/平均收益/最近买入日。"""
        t = self._scan_table
        t.setColumnCount(5)
        t.setHorizontalHeaderLabels([
            "代码", "回测笔数",
            "命中率", "平均收益%",
            "最近买入日"])
        t.setRowCount(0)
        from collections import defaultdict
        by_sym: Dict[str, list] = defaultdict(list)
        for s in self._bt_sigs:
            by_sym[s.symbol].append(s)
        rows = []
        for sym, sigs in by_sym.items():
            n     = len(sigs)
            wins  = sum(1 for s in sigs if s.pnl_pct > 0)
            hr    = wins / n * 100
            avg_r = sum(s.pnl_pct for s in sigs) / n * 100
            latest = max(str(s.dt)[:10] for s in sigs)
            rows.append((sym, n, hr, avg_r, latest))
        rows.sort(key=lambda r: r[3], reverse=True)
        for sym, n, hr, avg_r, latest in rows:
            hr_c = _GRN if hr >= 60 else (_RED if hr < 40 else _YLW)
            ar_c = _GRN if avg_r > 0 else _RED
            t.add_row([
                (sym,              _FG,  sym),
                (str(n),           _BLU, n),
                (f"{hr:.0f}%",     hr_c, hr),
                (f"{avg_r:+.2f}%", ar_c, avg_r),
                (latest,           _MUT, latest),
            ])
        t.resizeColumnsToContents()
        self._scan_count_lbl.setText(f"共 {len(rows)} 只")

    # ── 填充第二部分 ─────────────────────────────────────────────────

    def _fill_summary(self, batch: SignalBatch) -> None:
        m = batch.backtest_metrics()
        if not m["valid"]:
            self._clear_summary(); return
        exits = m.get("exit_reasons", {})
        self._cards["count"].set(str(m["count"]))
        self._cards["hit_rate"].set(f"{m['hit_rate']*100:.1f}%")
        self._cards["avg_ret"].set(f"{m['avg_return']:+.2f}%")
        self._cards["max_ret"].set(f"{m['max_return']:+.2f}%")
        self._cards["min_ret"].set(f"{m['min_return']:+.2f}%")
        self._cards["exit_tp"].set(
            str(exits.get("trailing_stop", 0) + exits.get("take_profit", 0)))
        self._cards["exit_sl"].set(str(exits.get("stop_loss", 0)))
        self._cards["exit_mh"].set(str(exits.get("max_hold", 0)))

    def _clear_summary(self) -> None:
        for c in self._cards.values():
            c.set("—")

    # ── 填充第三部分 ─────────────────────────────────────────────────

    def _fill_detail(self, sigs: List[SignalRecord]) -> None:
        t = self._detail_table
        t.setRowCount(0)
        for s in sigs:
            exit_dt  = str(s.exit_dt)[:10]   if s.exit_dt    else "—"
            exit_px  = f"{s.exit_price:.2f}"  if s.exit_price else "—"
            pnl_pct  = s.pnl_pct * 100        if s.pnl_pct is not None else 0.0
            pnl_str  = f"{pnl_pct:+.2f}%"
            pnl_c    = _GRN if pnl_pct > 0 else _RED
            hr_str   = self._hit_map.get(s.symbol, "—")
            rsn      = _reason_cn(s.exit_reason)
            rsn_c    = {"\u8ffd\u8e2a\u6b62\u76c8": _GRN,
                        "\u56fa\u5b9a\u6b62\u76c8": _GRN,
                        "\u6b62\u635f": _RED,
                        "\u6301\u4ed3\u5230\u671f": _ORG}.get(rsn, _MUT)
            t.add_row([
                (s.symbol,          _FG,   s.symbol),
                (str(s.dt)[:10],    _MUT,  str(s.dt)[:10]),
                (exit_dt,           _MUT,  exit_dt),
                (str(s.hold_days),  _FG,   s.hold_days),
                (f"{s.price:.2f}",  _FG,   s.price),
                (exit_px,           _FG,   s.exit_price or 0.0),
                (pnl_str,           pnl_c, pnl_pct),
                (hr_str,            _YLW,  hr_str),
                (rsn,               rsn_c, rsn),
            ])
        t.resizeColumnsToContents()
        self._detail_count_lbl.setText(f"共 {len(sigs)} 笔")

    # ── 排序 ────────────────────────────────────────────────────────

    def _on_sort_changed(self, idx: int) -> None:
        if not self._bt_sigs:
            return
        sigs = list(self._bt_sigs)
        if   idx == 0: sigs.sort(key=lambda s: s.pnl_pct or 0, reverse=True)
        elif idx == 1: sigs.sort(key=lambda s: s.pnl_pct or 0)
        elif idx == 2: sigs.sort(key=lambda s: s.hold_days)
        elif idx == 3: sigs.sort(key=lambda s: s.symbol)
        self._hit_map = _hit_rate_map(sigs)
        self._fill_detail(sigs)

    # ── 行点击 ──────────────────────────────────────────────────────

    def _on_scan_row_clicked(self, index: QtCore.QModelIndex) -> None:
        row  = index.row()
        item = self._scan_table.item(row, 0)
        if item and self._bt_sigs:
            sym  = item.text()
            recs = [s for s in self._bt_sigs if s.symbol == sym]
            if recs:
                self.signal_selected.emit(recs[0])

    def _on_detail_row_clicked(self, index: QtCore.QModelIndex) -> None:
        row   = index.row()
        s_item = self._detail_table.item(row, 0)
        d_item = self._detail_table.item(row, 1)
        if s_item and self._bt_sigs:
            sym = s_item.text()
            dt  = d_item.text() if d_item else ""
            for s in self._bt_sigs:
                if s.symbol == sym and str(s.dt)[:10] == dt:
                    self.signal_selected.emit(s)
                    break

    # ── 导出 ────────────────────────────────────────────────────────

    def _export_scan_csv(self) -> None:
        self._export_table(self._scan_table, "scan_results.csv")

    def _export_bt_csv(self) -> None:
        self._export_table(self._detail_table, "backtest_detail.csv")

    def _export_table(self, table: QtWidgets.QTableWidget,
                      default_name: str) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出", default_name, "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow([table.horizontalHeaderItem(c).text()
                             for c in range(table.columnCount())])
                for row in range(table.rowCount()):
                    w.writerow([
                        (table.item(row, col).text()
                         if table.item(row, col) else "")
                        for col in range(table.columnCount())
                    ])
            QtWidgets.QMessageBox.information(
                self, "导出成功", f"已保存到：{path}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "导出失败", str(e))


# 向后兼容
SignalResultView = SignalView
