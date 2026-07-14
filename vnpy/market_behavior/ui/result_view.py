"""
market_behavior/ui/result_view.py  —  选股结果 + 回测报告 Tab（完整实现）
"""
from __future__ import annotations
from vnpy.trader.ui import QtWidgets, QtCore, QtGui

_BG    = "#1e1e2e"
_PANEL = "#181825"
_PAN2  = "#11111b"
_BORD  = "#45475a"
_FG    = "#cdd6f4"
_MUT   = "#6c7086"
_BLU   = "#89b4fa"
_GRN   = "#a6e3a1"
_YLW   = "#f9e2af"
_RED   = "#f38ba8"
_MAV   = "#cba6f7"
_ORG   = "#fab387"

def _lbl(text, color=_FG, size=14, bold=False):
    w = QtWidgets.QLabel(text)
    w.setStyleSheet(f"color:{color};font-size:{size}px;"
                    f"font-weight:{'bold' if bold else 'normal'};"
                    f"background:transparent;border:none;")
    return w

def _hline():
    f = QtWidgets.QFrame()
    f.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    f.setStyleSheet(f"border:none;border-top:1px solid {_BORD};")
    return f

_TBL_SS = (
    f"QTableWidget{{background:{_PAN2};color:{_FG};"
    f"border:none;gridline-color:{_BORD};font-size:14px;}}"
    f"QTableWidget::item{{padding:4px 8px;}}"
    f"QTableWidget::item:selected{{background:{_BLU};color:#1e1e2e;}}"
    f"QHeaderView::section{{background:{_PANEL};color:{_MUT};"
    f"border:none;border-bottom:1px solid {_BORD};"
    f"padding:4px 8px;font-size:14px;font-weight:bold;}}"
)


class StatCard(QtWidgets.QWidget):
    """顶部统计卡片。"""
    def __init__(self, title: str, color: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background:{_PANEL};border:1px solid {color};border-radius:6px;")
        self.setMinimumHeight(76)
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(2)
        self._title = _lbl(title, color, 14, True)
        v.addWidget(self._title)
        self._val = QtWidgets.QLabel("—")
        self._val.setStyleSheet(
            f"color:{color};font-size:22px;font-weight:bold;"
            f"background:transparent;border:none;")
        self._val.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self._val)

    def set_value(self, text: str):
        self._val.setText(text)


class ResultViewTab(QtWidgets.QWidget):
    # 双击/右键触发回测时发出：symbol
    sig_backtest_symbol = QtCore.Signal(str)

    """
    结果视图 Tab。
    上半：选股结果表格（代码 / 强度 / 评分 / 标签 / 最新收盘）
    下半：回测摘要卡片 + 触发明细表格
    """

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"background:{_BG};")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        root.addWidget(_lbl("筛选结果 & 回测报告  Results", _MAV, 15, True))
        root.addWidget(_hline())

        # ── 选股结果表格 ──────────────────────────────────────────
        screen_hdr = QtWidgets.QHBoxLayout()
        screen_hdr.addWidget(_lbl("选股结果  Screening Results", _BLU, 14, True))
        screen_hdr.addStretch()
        self._screen_count = _lbl("共 0 只", _MUT)
        screen_hdr.addWidget(self._screen_count)
        btn_export = QtWidgets.QPushButton("导出 CSV")
        btn_export.setStyleSheet(
            f"QPushButton{{background:{_PANEL};color:{_BLU};"
            f"border:1px solid {_BLU};border-radius:4px;"
            f"padding:4px 12px;font-size:14px;}}"
            f"QPushButton:hover{{background:{_BLU};color:#1e1e2e;}}")
        btn_export.clicked.connect(self._export_csv)
        screen_hdr.addWidget(btn_export)

        self._btn_bt = QtWidgets.QPushButton("回测选中  ◆")
        self._btn_bt.setStyleSheet(
            f"QPushButton{{background:{_GRN};color:#1e1e2e;"
            f"border:none;border-radius:4px;"
            f"padding:4px 14px;font-size:14px;font-weight:bold;}}"
            f"QPushButton:hover{{background:#c0f0bc;}}"
            f"QPushButton:disabled{{background:#313244;color:#6c7086;}}")
        self._btn_bt.setToolTip("对选中股票运行历史回测（也可双击行）")
        self._btn_bt.clicked.connect(self._on_backtest_selected)
        screen_hdr.addWidget(self._btn_bt)
        root.addLayout(screen_hdr)

        self._screen_table = QtWidgets.QTableWidget()
        self._screen_table.setColumnCount(7)
        self._screen_table.setHorizontalHeaderLabels(
            ["代码", "综合强度", "评分", "上涨%", "突破", "涨停", "标签"])
        self._screen_table.setStyleSheet(_TBL_SS)
        self._screen_table.horizontalHeader().setStretchLastSection(True)
        self._screen_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._screen_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._screen_table.verticalHeader().setVisible(False)
        self._screen_table.setFixedHeight(220)
        self._screen_table.doubleClicked.connect(self._on_row_double_clicked)
        self._screen_table.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._screen_table.customContextMenuRequested.connect(
            self._on_context_menu)
        root.addWidget(self._screen_table)

        root.addWidget(_hline())

        # ── 回测摘要卡片 ──────────────────────────────────────────
        root.addWidget(_lbl("回测摘要  Backtest Summary", _GRN, 14, True))
        cards_row = QtWidgets.QHBoxLayout()
        cards_row.setSpacing(10)
        self._cards = {}
        for key, title, color in [
            ("trigger_count", "触发次数",   _BLU),
            ("hit_rate",      "胜  率",     _GRN),
            ("avg_return",    "平均收益",   _GRN),
            ("sharpe",        "夏普比率",   _YLW),
            ("max_drawdown",  "最大回撤",   _RED),
            ("avg_score",     "平均评分",   _MAV),
        ]:
            card = StatCard(title, color)
            self._cards[key] = card
            cards_row.addWidget(card, stretch=1)
        root.addLayout(cards_row)

        root.addWidget(_hline())

        # ── 触发明细表格 ──────────────────────────────────────────
        root.addWidget(_lbl("触发明细  Trigger Detail", _YLW, 14, True))
        self._detail_table = QtWidgets.QTableWidget()
        self._detail_table.setColumnCount(5)
        self._detail_table.setHorizontalHeaderLabels(
            ["触发日期", "股票代码", "触发价", f"持有收益", "评分"])
        self._detail_table.setStyleSheet(_TBL_SS)
        self._detail_table.horizontalHeader().setStretchLastSection(True)
        self._detail_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._detail_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._detail_table.verticalHeader().setVisible(False)
        root.addWidget(self._detail_table, stretch=1)

    # ── 对外接口 ────────────────────────────────────────────────────

    def show_screen_results(self, results: list, factor_map: dict):
        """
        显示选股结果。
        results: list of ScreenResult
        factor_map: {symbol: {factor_type: FactorResult}}
        """
        self._screen_table.setRowCount(0)
        for r in results:
            row = self._screen_table.rowCount()
            self._screen_table.insertRow(row)
            fm = factor_map.get(r.symbol, {})
            ks  = fm.get("kline_strength")
            rd  = fm.get("rise_days")
            bk  = fm.get("breakout_count")
            lu  = fm.get("limit_up_count")
            lbs = r.details.get("labels", [])

            items = [
                (r.symbol,                          _FG),
                (f"{ks.value:.3f}" if ks else "—",  _GRN if ks and ks.value > 0.5 else _FG),
                (f"{r.score:.3f}",                  _BLU),
                (f"{rd.value*100:.0f}%" if rd else "—", _FG),
                (f"{bk.value:.1f}" if bk else "—",  _FG),
                (f"{int(lu.value)}" if lu else "—", _MAV if lu and lu.value > 0 else _FG),
                (", ".join(lbs) if lbs else "—",    _MUT),
            ]
            for col, (text, color) in enumerate(items):
                item = QtWidgets.QTableWidgetItem(text)
                item.setForeground(QtGui.QColor(color))
                self._screen_table.setItem(row, col, item)

        self._screen_count.setText(f"共 {len(results)} 只")
        self._screen_table.resizeColumnsToContents()

    def show_backtest_report(self, report: dict, triggers: list, hold_days: int):
        """显示回测摘要 + 触发明细。"""
        mapping = {
            "trigger_count": str(report.get("trigger_count", "—")),
            "hit_rate":      report.get("hit_rate",  "N/A"),
            "avg_return":    report.get("avg_return", "N/A"),
            "sharpe":        report.get("sharpe",     "N/A"),
            "max_drawdown":  report.get("max_drawdown","N/A"),
            "avg_score":     report.get("avg_score",  "N/A"),
        }
        for key, val in mapping.items():
            if key in self._cards:
                self._cards[key].set_value(str(val))

        # 更新持有收益列头
        self._detail_table.setHorizontalHeaderLabels(
            ["触发日期", "股票代码", "触发价", f"{hold_days}日收益", "评分"])

        self._detail_table.setRowCount(0)
        for t in triggers:
            row = self._detail_table.rowCount()
            self._detail_table.insertRow(row)
            ret  = t.forward_returns.get(hold_days, 0)
            ret_color = _GRN if ret >= 0 else _RED
            items = [
                (str(t.trigger_dt)[:10], _MUT),
                (t.symbol,               _FG),
                (f"{t.trigger_price:.2f}", _FG),
                (f"{ret*100:+.2f}%",     ret_color),
                (f"{t.score:.3f}",       _BLU),
            ]
            for col, (text, color) in enumerate(items):
                item = QtWidgets.QTableWidgetItem(text)
                item.setForeground(QtGui.QColor(color))
                self._detail_table.setItem(row, col, item)

        self._detail_table.resizeColumnsToContents()

    def clear(self):
        self._screen_table.setRowCount(0)
        self._detail_table.setRowCount(0)
        for card in self._cards.values():
            card.set_value("—")
        self._screen_count.setText("共 0 只")

    def _export_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出选股结果", "screen_results.csv",
            "CSV Files (*.csv)")
        if not path:
            return
        try:
            import csv
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                headers = ["代码", "综合强度", "评分", "上涨%", "突破", "涨停", "标签"]
                writer.writerow(headers)
                for row in range(self._screen_table.rowCount()):
                    writer.writerow([
                        self._screen_table.item(row, col).text()
                        if self._screen_table.item(row, col) else ""
                        for col in range(self._screen_table.columnCount())
                    ])
            QtWidgets.QMessageBox.information(self, "导出成功", f"已保存到：{path}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "导出失败", str(e))

    def _selected_symbol(self) -> str:
        """返回当前选中行的股票代码，无选中返回空字符串。"""
        row = self._screen_table.currentRow()
        if row < 0:
            return ""
        item = self._screen_table.item(row, 0)
        return item.text() if item else ""

    def _on_row_double_clicked(self, index) -> None:
        sym = self._selected_symbol()
        if sym:
            self.sig_backtest_symbol.emit(sym)

    def _on_backtest_selected(self) -> None:
        sym = self._selected_symbol()
        if not sym:
            QtWidgets.QMessageBox.information(self, "提示", "请先在上方表格中点击选中一只股票。")
            return
        self.sig_backtest_symbol.emit(sym)

    def _on_context_menu(self, pos) -> None:
        sym = self._selected_symbol()
        if not sym:
            return
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:#181825;color:#cdd6f4;border:1px solid #45475a;}}"
            f"QMenu::item:selected{{background:#89b4fa;color:#1e1e2e;}}")
        act_bt  = menu.addAction(f"对 {sym} 运行历史回测")
        act_pat = menu.addAction(f"查看 {sym} K线形态")
        act_fac = menu.addAction(f"查看 {sym} 因子详情")
        action  = menu.exec(self._screen_table.viewport().mapToGlobal(pos))
        if action == act_bt:
            self.sig_backtest_symbol.emit(sym)
        elif action == act_pat:
            self.sig_backtest_symbol.emit("__pattern__:" + sym)
        elif action == act_fac:
            self.sig_backtest_symbol.emit("__factor__:" + sym)