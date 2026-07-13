"""
screening/ui/result_widget.py

Result Widget — 选股结果展示面板（Phase 5）。

实现：
  - 股票评分结果表格（代码/综合评分/排名/百分位/因子贡献）
  - Top N / Top % 快速筛选
  - 导出 CSV
  - 实时刷新
"""

from __future__ import annotations
import csv
import os
from typing import List, Optional

from vnpy.trader.ui import QtWidgets, QtCore

from ..model.screening_result import ScreeningResult, StockScore

_PANEL  = "#181825"
_PANEL2 = "#11111b"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_YLW    = "#f9e2af"
_GRN    = "#a6e3a1"
_RED    = "#f38ba8"
_BLU    = "#89b4fa"
_ORG    = "#fab387"

_LABEL  = f"color:{_FG};font-size:11px;"
_INPUT  = (f"background:{_PANEL2};color:{_FG};border:1px solid {_BORDER};"
           f"border-radius:3px;padding:3px 6px;font-size:11px;")

_HDR_COLS = ["排名", "代码", "综合评分", "百分位", "通过条件", "通过风险过滤"]

_TABLE_STYLE = f"""
    QTableWidget {{
        background: {_PANEL2};
        color: {_FG};
        gridline-color: {_BORDER};
        font-size: 11px;
        border: none;
    }}
    QHeaderView::section {{
        background: #313244;
        color: {_YLW};
        font-size: 11px;
        font-weight: bold;
        border: 1px solid {_BORDER};
        padding: 4px;
    }}
    QTableWidget::item:selected {{
        background: #45475a;
    }}
"""


def _sb(text, color=_MUT):
    b = QtWidgets.QPushButton(text)
    b.setStyleSheet(
        f"QPushButton{{background:#313244;color:{color};"
        f"border:1px solid {_BORDER};border-radius:3px;padding:3px 10px;font-size:11px;}}"
        f"QPushButton:hover{{background:#45475a;}}"
    )
    return b


class ResultWidget(QtWidgets.QWidget):
    """选股结果展示面板（Phase 5 完整实现）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._current_result: Optional[ScreeningResult] = None
        self._init_ui()

    def _sep(self):
        s = QtWidgets.QFrame()
        s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border:none;border-top:1px solid {_BORDER};")
        return s

    def _init_ui(self) -> None:
        self.setStyleSheet(f"background:{_PANEL};")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QtWidgets.QLabel("Stock Result  选股结果")
        title.setStyleSheet(f"color:{_YLW};font-size:13px;font-weight:bold;")
        root.addWidget(title)
        root.addWidget(self._sep())

        # ── 统计信息栏 ────────────────────────────────────────────────
        info_row = QtWidgets.QHBoxLayout()
        self._lbl_total   = QtWidgets.QLabel("Universe: --")
        self._lbl_passed  = QtWidgets.QLabel("通过条件: --")
        self._lbl_final   = QtWidgets.QLabel("最终入选: --")
        self._lbl_elapsed = QtWidgets.QLabel("耗时: --")
        for lbl in [self._lbl_total, self._lbl_passed,
                    self._lbl_final, self._lbl_elapsed]:
            lbl.setStyleSheet(f"color:{_MUT};font-size:10px;")
            info_row.addWidget(lbl)
        info_row.addStretch()
        root.addLayout(info_row)

        # ── 筛选控件 ──────────────────────────────────────────────────
        filter_row = QtWidgets.QHBoxLayout()
        filter_row.addWidget(QtWidgets.QLabel("显示 Top", styleSheet=_LABEL))
        self._top_n_spin = QtWidgets.QSpinBox()
        self._top_n_spin.setRange(1, 9999)
        self._top_n_spin.setValue(50)
        self._top_n_spin.setFixedWidth(70)
        self._top_n_spin.setStyleSheet(_INPUT)
        filter_row.addWidget(self._top_n_spin)
        filter_row.addWidget(QtWidgets.QLabel("只  /  前", styleSheet=_LABEL))
        self._top_pct_spin = QtWidgets.QDoubleSpinBox()
        self._top_pct_spin.setRange(1.0, 100.0)
        self._top_pct_spin.setValue(20.0)
        self._top_pct_spin.setSuffix("%")
        self._top_pct_spin.setDecimals(0)
        self._top_pct_spin.setFixedWidth(70)
        self._top_pct_spin.setStyleSheet(_INPUT)
        filter_row.addWidget(self._top_pct_spin)

        btn_topn  = _sb("Top N", _BLU)
        btn_toppct = _sb("Top %", _ORG)
        btn_all   = _sb("全部", _MUT)
        btn_export = _sb("导出CSV", _GRN)

        btn_topn.clicked.connect(self._on_top_n)
        btn_toppct.clicked.connect(self._on_top_pct)
        btn_all.clicked.connect(self._on_show_all)
        btn_export.clicked.connect(self._on_export)

        for b in [btn_topn, btn_toppct, btn_all, btn_export]:
            filter_row.addWidget(b)
        filter_row.addStretch()
        root.addLayout(filter_row)

        # ── 结果表格 ──────────────────────────────────────────────────
        self._table = QtWidgets.QTableWidget(0, len(_HDR_COLS))
        self._table.setHorizontalHeaderLabels(_HDR_COLS)
        self._table.setStyleSheet(_TABLE_STYLE)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(True)
        root.addWidget(self._table)

        # ── 状态栏 ────────────────────────────────────────────────────
        self._status_lbl = QtWidgets.QLabel("等待选股结果…")
        self._status_lbl.setStyleSheet(f"color:{_MUT};font-size:10px;")
        root.addWidget(self._status_lbl)

    # ── 数据刷新 ──────────────────────────────────────────────────────

    def update_result(self, result: Optional[ScreeningResult]) -> None:
        """刷新整个结果表格。"""
        self._current_result = result
        if result is None:
            self._table.setRowCount(0)
            self._set_status("无结果")
            return

        self._lbl_total.setText(f"Universe: {result.total_universe}")
        self._lbl_passed.setText(f"通过条件: {result.total_passed_condition}")
        self._lbl_final.setText(f"最终入选: {result.final_count}")
        self._lbl_elapsed.setText(f"耗时: {result.elapsed_seconds:.2f}s")

        self._fill_table(result.stocks)
        self._set_status(
            f"共 {result.final_count} 只  |  "
            f"RunID: {result.run_id}  |  "
            f"{str(result.generated_at)[:19]}"
        )

    def _fill_table(self, stocks: List[StockScore]) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(stocks))

        for row, ss in enumerate(stocks):
            rank_item  = QtWidgets.QTableWidgetItem(str(ss.rank))
            sym_item   = QtWidgets.QTableWidgetItem(ss.symbol)
            score_item = QtWidgets.QTableWidgetItem(f"{ss.composite_score:.2f}")
            pct_item   = QtWidgets.QTableWidgetItem(f"{ss.percentile:.1%}")
            cond_item  = QtWidgets.QTableWidgetItem("✓" if ss.passed_condition else "✗")
            risk_item  = QtWidgets.QTableWidgetItem("✓" if ss.passed_risk_filter else "✗")

            # 评分着色
            score_color = self._score_color(ss.composite_score)
            score_item.setForeground(
                QtWidgets.QApplication.palette().text() if not score_color
                else self._make_color(score_color)
            )

            for col, item in enumerate(
                [rank_item, sym_item, score_item, pct_item, cond_item, risk_item]
            ):
                item.setTextAlignment(
                    QtCore.Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, col, item)

        self._table.setSortingEnabled(True)
        self._table.resizeColumnsToContents()

    def _score_color(self, score: float) -> str:
        if score >= 75:
            return _GRN
        if score >= 50:
            return _YLW
        if score >= 25:
            return _ORG
        return _RED

    def _make_color(self, hex_color: str):
        from vnpy.trader.ui import QtGui
        return QtGui.QColor(hex_color)

    # ── 按钮回调 ──────────────────────────────────────────────────────

    def _on_top_n(self) -> None:
        if self._current_result:
            n = self._top_n_spin.value()
            self._fill_table(self._current_result.get_top_n(n))
            self._set_status(f"显示 Top {n}")

    def _on_top_pct(self) -> None:
        if self._current_result:
            pct = self._top_pct_spin.value() / 100.0
            stocks = self._current_result.get_top_pct(pct)
            self._fill_table(stocks)
            self._set_status(f"显示 Top {self._top_pct_spin.value():.0f}%  ({len(stocks)} 只)")

    def _on_show_all(self) -> None:
        if self._current_result:
            self._fill_table(self._current_result.stocks)
            self._set_status(f"显示全部 {self._current_result.final_count} 只")

    def _on_export(self) -> None:
        if not self._current_result or not self._current_result.stocks:
            self._set_status("无数据可导出")
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出选股结果", "screening_result.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["排名", "代码", "综合评分", "百分位",
                                  "通过条件", "通过风险过滤"])
                for ss in self._current_result.stocks:
                    writer.writerow([
                        ss.rank, ss.symbol,
                        f"{ss.composite_score:.2f}",
                        f"{ss.percentile:.4f}",
                        "Y" if ss.passed_condition else "N",
                        "Y" if ss.passed_risk_filter else "N",
                    ])
            self._set_status(f"已导出到：{os.path.basename(path)}", _GRN)
        except Exception as e:
            self._set_status(f"导出失败：{e}", _RED)

    def _set_status(self, msg: str, color: str = _MUT) -> None:
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color:{color};font-size:10px;")
