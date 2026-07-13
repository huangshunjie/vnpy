"""
factor_research/ui/overview_tab.py
OverviewTab - 因子概览 Tab（方案A：全量汇总表）
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtGui, QtWidgets
from ..model import OverviewSummary

_SUM_COLS = [
    ("合约代码",   "vt_symbol",       QtCore.Qt.AlignmentFlag.AlignLeft),
    ("数据开始",   "data_start",      QtCore.Qt.AlignmentFlag.AlignCenter),
    ("数据结束",   "data_end",        QtCore.Qt.AlignmentFlag.AlignCenter),
    ("Bar 数",    "total_bars",      QtCore.Qt.AlignmentFlag.AlignRight),
    ("跨度(天)",  "date_range_days", QtCore.Qt.AlignmentFlag.AlignRight),
    ("最大缺失率", "max_missing_pct", QtCore.Qt.AlignmentFlag.AlignRight),
]
_DETAIL_COLS = [
    ("字段",   QtCore.Qt.AlignmentFlag.AlignLeft),
    ("均值",   QtCore.Qt.AlignmentFlag.AlignRight),
    ("标准差", QtCore.Qt.AlignmentFlag.AlignRight),
    ("最小值", QtCore.Qt.AlignmentFlag.AlignRight),
    ("最大值", QtCore.Qt.AlignmentFlag.AlignRight),
    ("缺失数", QtCore.Qt.AlignmentFlag.AlignRight),
    ("缺失率", QtCore.Qt.AlignmentFlag.AlignRight),
]
_COLOR_WARN = QtGui.QColor("#7A4A00")
_COLOR_BAD  = QtGui.QColor("#5A1010")
_BAR_MIN    = 250

class _SortItem(QtWidgets.QTableWidgetItem):
    def __init__(self, display, raw):
        super().__init__(display)
        self._raw = raw
    def __lt__(self, other):
        if isinstance(other, _SortItem):
            try:
                return float(self._raw) < float(other._raw)
            except (TypeError, ValueError):
                pass
        return (self.text() or "") < (other.text() or "")

class OverviewTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._summaries = []
        self._sort_col = -1
        self._sort_asc = True
        self._init_ui()

    def _init_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_summary_table(), stretch=3)
        root.addWidget(self._build_detail_group(), stretch=1)

    def _build_toolbar(self):
        bar = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.lbl_count = QtWidgets.QLabel("共 0 只合约")
        self.lbl_count.setStyleSheet("font-weight: bold;")
        self.edit_search = QtWidgets.QLineEdit()
        self.edit_search.setPlaceholderText("搜索合约代码")
        self.edit_search.setFixedWidth(160)
        self.edit_search.textChanged.connect(self._on_search)
        lbl_hint = QtWidgets.QLabel("  黄色：Bar数<250    红色：最大缺失率>1%")
        lbl_hint.setStyleSheet("color: #888888; font-size: 11px;")
        btn_export = QtWidgets.QPushButton("导出 CSV")
        btn_export.setFixedHeight(26)
        btn_export.clicked.connect(self._export_csv)
        lay.addWidget(self.lbl_count)
        lay.addWidget(QtWidgets.QLabel("搜索："))
        lay.addWidget(self.edit_search)
        lay.addWidget(lbl_hint)
        lay.addStretch()
        lay.addWidget(btn_export)
        return bar

    def _build_summary_table(self):
        self._placeholder = QtWidgets.QLabel("暂无数据\n请在左侧配置区填写参数后点击「运行」")
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #666666; font-size: 13px;")
        self.sum_table = QtWidgets.QTableWidget()
        self.sum_table.setColumnCount(len(_SUM_COLS))
        self.sum_table.setHorizontalHeaderLabels([c[0] for c in _SUM_COLS])
        self.sum_table.verticalHeader().setVisible(False)
        self.sum_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sum_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.sum_table.setAlternatingRowColors(False)
        self.sum_table.horizontalHeader().setStretchLastSection(True)
        self.sum_table.verticalHeader().setDefaultSectionSize(24)
        self.sum_table.setSortingEnabled(False)
        self.sum_table.horizontalHeader().setSortIndicatorShown(False)
        self.sum_table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.sum_table.currentCellChanged.connect(self._on_row_selected)
        self.sum_table.hide()
        container = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._placeholder)
        lay.addWidget(self.sum_table)
        return container

    def _build_detail_group(self):
        group = QtWidgets.QGroupBox("OHLCV 统计详情")
        self._detail_group = group
        lay = QtWidgets.QVBoxLayout(group)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)
        self._detail_info_lbl = QtWidgets.QLabel("点击上方合约行查看详情")
        self._detail_info_lbl.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        self._detail_info_lbl.setWordWrap(True)
        lay.addWidget(self._detail_info_lbl)
        self.detail_table = QtWidgets.QTableWidget(0, len(_DETAIL_COLS))
        self.detail_table.setHorizontalHeaderLabels([c[0] for c in _DETAIL_COLS])
        self.detail_table.verticalHeader().setVisible(False)
        self.detail_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.detail_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.detail_table.setAlternatingRowColors(True)
        self.detail_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.detail_table.verticalHeader().setDefaultSectionSize(22)
        lay.addWidget(self.detail_table)
        return group
    def update_summary(self, summary):
        self._summaries.append(summary)
        self._append_row(summary)
        self.lbl_count.setText("共 {} 只合约".format(len(self._summaries)))
        if self.sum_table.isHidden():
            self._placeholder.hide()
            self.sum_table.show()

    def clear(self):
        self._summaries.clear()
        self.sum_table.setRowCount(0)
        self.sum_table.hide()
        self._placeholder.show()
        self.detail_table.setRowCount(0)
        self._detail_info_lbl.setText("点击上方合约行查看详情")
        self.lbl_count.setText("共 0 只合约")
        self._sort_col = -1

    def _append_row(self, s):
        row = self.sum_table.rowCount()
        self.sum_table.insertRow(row)
        self.sum_table.setRowHeight(row, 24)
        max_miss = max(
            (st.missing_pct for st in s.column_stats if st.name != "open_interest"),
            default=0.0,
        )
        if max_miss > 0.01:
            bg = _COLOR_BAD
        elif s.total_bars < _BAR_MIN:
            bg = _COLOR_WARN
        else:
            bg = None
        values = [
            (s.vt_symbol,                                 s.vt_symbol),
            (str(s.data_start) if s.data_start else "-",  str(s.data_start or "")),
            (str(s.data_end)   if s.data_end   else "-",  str(s.data_end   or "")),
            (str(s.total_bars),                            s.total_bars),
            (str(s.date_range_days),                       s.date_range_days),
            ("{:.2%}".format(max_miss),                    max_miss),
        ]
        for col, ((display, raw), (_, _, align)) in enumerate(zip(values, _SUM_COLS)):
            item = _SortItem(display, raw)
            item.setTextAlignment(int(align | QtCore.Qt.AlignmentFlag.AlignVCenter))
            if bg is not None:
                item.setBackground(bg)
            if col == 0:
                item.setData(QtCore.Qt.ItemDataRole.UserRole, s)
            self.sum_table.setItem(row, col, item)

    def _on_row_selected(self, current_row, *_):
        if current_row < 0:
            return
        item = self.sum_table.item(current_row, 0)
        if item is None:
            return
        summary = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if summary is None:
            return
        self._render_detail(summary)

    def _render_detail(self, s):
        self._detail_info_lbl.setText(
            "{}    {} ~ {}    {} bars    跨度 {} 天".format(
                s.vt_symbol, s.data_start, s.data_end,
                s.total_bars, s.date_range_days,
            )
        )
        rows = [st for st in s.column_stats if st.name != "open_interest"]
        self.detail_table.setRowCount(len(rows))
        for row_idx, stat in enumerate(rows):
            vals = [
                stat.name,
                "{:,.4f}".format(stat.mean),
                "{:,.4f}".format(stat.std),
                "{:,.4f}".format(stat.min_val),
                "{:,.4f}".format(stat.max_val),
                str(stat.missing_count),
                "{:.2%}".format(stat.missing_pct),
            ]
            for col_idx, (val, (_, align)) in enumerate(zip(vals, _DETAIL_COLS)):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(int(align | QtCore.Qt.AlignmentFlag.AlignVCenter))
                if stat.missing_pct > 0.01 and col_idx in (5, 6):
                    item.setForeground(QtGui.QColor("#FF5555"))
                self.detail_table.setItem(row_idx, col_idx, item)

    def _on_search(self, text):
        keyword = text.strip().lower()
        for row in range(self.sum_table.rowCount()):
            item = self.sum_table.item(row, 0)
            hidden = bool(keyword and item and keyword not in item.text().lower())
            self.sum_table.setRowHidden(row, hidden)

    def _on_header_clicked(self, logical_index):
        if self._sort_col == logical_index:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = logical_index
            self._sort_asc = False
        order = (
            QtCore.Qt.SortOrder.AscendingOrder
            if self._sort_asc else QtCore.Qt.SortOrder.DescendingOrder
        )
        self.sum_table.horizontalHeader().setSortIndicatorShown(True)
        self.sum_table.horizontalHeader().setSortIndicator(logical_index, order)
        self._manual_sort(logical_index, self._sort_asc)

    def _manual_sort(self, col, ascending):
        n_rows = self.sum_table.rowCount()
        n_cols = self.sum_table.columnCount()
        if n_rows == 0:
            return
        all_rows = [
            [self.sum_table.takeItem(r, c) for c in range(n_cols)]
            for r in range(n_rows)
        ]
        def _key(row_items):
            item = row_items[col]
            if item is None:
                return (1, 0.0, "")
            if isinstance(item, _SortItem):
                try:
                    return (0, float(item._raw), "")
                except (TypeError, ValueError):
                    pass
            return (0, 0.0, item.text() or "")
        all_rows.sort(key=_key, reverse=not ascending)
        for r, row_items in enumerate(all_rows):
            for c, item in enumerate(row_items):
                if item is not None:
                    self.sum_table.setItem(r, c, item)

    def _export_csv(self):
        if not self._summaries:
            QtWidgets.QMessageBox.information(self, "提示", "暂无数据可导出")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出合约概览 CSV", "", "CSV 文件 (*.csv)"
        )
        if not path:
            return
        import csv
        headers = [c[0] for c in _SUM_COLS]
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for s in self._summaries:
                    max_miss = max(
                        (st.missing_pct for st in s.column_stats
                         if st.name != "open_interest"),
                        default=0.0,
                    )
                    writer.writerow([
                        s.vt_symbol,
                        str(s.data_start) if s.data_start else "",
                        str(s.data_end)   if s.data_end   else "",
                        s.total_bars,
                        s.date_range_days,
                        "{:.4%}".format(max_miss),
                    ])
            QtWidgets.QMessageBox.information(self, "导出成功", "已保存到：\n" + path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "导出失败", str(exc))