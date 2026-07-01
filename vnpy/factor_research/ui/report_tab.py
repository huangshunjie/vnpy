"""
factor_research/ui/report_tab.py

ReportTab -- Report Center Tab.

Layout:
┌──────────────────────────────────────────┐
│  [导出 Excel]  [打开文件夹]  path_label   │  ← toolbar
├──────────────────────────────────────────┤
│  QTabWidget with preview sheets:          │
│  元信息 | 概览 | IC统计 | IC Decay |       │
│  分层收益 | LongShort绩效 | 综合评分 | IC时序 │
└──────────────────────────────────────────┘

Data flow (zero new events):
  widget._on_plot_ready routes:
    "overview"  → report_tab.feed_overview(OverviewSummary)
    "ic"        → report_tab.feed_ic(IcStats)
    "decay"     → report_tab.feed_decay(DecayResult)
    "quantile"  → report_tab.feed_quantile(QuantileResult)
    "ic_series" → report_tab.feed_ic_series(IcStats)  (same payload)
    score_tab.feed_* triggers → after both ic+quantile arrive,
                                 report_tab auto-refreshes score preview

  ScoreTab passes its FactorScore to widget which calls
    report_tab.feed_score(FactorScore)  -- routed after score is ready.

Export path default: ~/factor_reports/<timestamp>.xlsx
"""

from __future__ import annotations

import math
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from vnpy.trader.ui import QtCore, QtWidgets

from ..engine.report_engine import ReportEngine
from ..model import (
    DecayResult,
    FactorScore,
    IcStats,
    OverviewSummary,
    QuantileResult,
)


class ReportTab(QtWidgets.QWidget):
    """Report Center Tab — preview + one-click Excel export."""

    _DEFAULT_DIR = Path.home() / "factor_reports"

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        # accumulated data from all stages
        self._overviews:  list[OverviewSummary] = []
        self._ic:         IcStats | None = None
        self._decay:      DecayResult | None = None
        self._quantile:   QuantileResult | None = None
        self._score:      FactorScore | None = None

        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_preview(), stretch=1)

    def _build_toolbar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget(self)
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.btn_export = QtWidgets.QPushButton("导出 Excel")
        self.btn_export.setFixedHeight(30)
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._on_export)

        self.btn_open_dir = QtWidgets.QPushButton("打开文件夹")
        self.btn_open_dir.setFixedHeight(30)
        self.btn_open_dir.clicked.connect(self._on_open_dir)

        self.lbl_path = QtWidgets.QLabel("尚未导出")
        self.lbl_path.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout.addWidget(self.btn_export)
        layout.addWidget(self.btn_open_dir)
        layout.addWidget(self.lbl_path, stretch=1)
        return bar

    def _build_preview(self) -> QtWidgets.QTabWidget:
        self._preview_tabs = QtWidgets.QTabWidget()

        # sheet names → must match export order
        self._sheet_names = [
            "元信息", "概览", "IC统计", "IC Decay",
            "分层收益", "LongShort绩效", "综合评分", "IC时序",
        ]
        self._tables: dict[str, QtWidgets.QTableWidget] = {}

        for name in self._sheet_names:
            tw = self._make_table()
            self._tables[name] = tw
            self._preview_tabs.addTab(tw, name)

        return self._preview_tabs

    @staticmethod
    def _make_table() -> QtWidgets.QTableWidget:
        tw = QtWidgets.QTableWidget()
        tw.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        tw.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        tw.setAlternatingRowColors(True)
        tw.horizontalHeader().setStretchLastSection(True)
        tw.verticalHeader().setVisible(False)
        return tw

    # ------------------------------------------------------------------ #
    #  Public feed interface
    # ------------------------------------------------------------------ #

    def feed_overview(self, summary: OverviewSummary) -> None:
        self._overviews.append(summary)
        self._refresh_sheet("概览",
                            ReportEngine.build_overview(self._overviews))
        self._update_export_btn()

    def feed_ic(self, stats: IcStats) -> None:
        self._ic = stats
        self._refresh_sheet("IC统计", ReportEngine.build_ic(stats))
        self._refresh_sheet("IC时序", ReportEngine.build_ic_series(stats))
        self._update_export_btn()

    def feed_decay(self, result: DecayResult) -> None:
        self._decay = result
        self._refresh_sheet("IC Decay", ReportEngine.build_decay(result))
        self._update_export_btn()

    def feed_quantile(self, result: QuantileResult) -> None:
        self._quantile = result
        self._refresh_sheet("分层收益",
                            ReportEngine.build_quantile(result))
        self._refresh_sheet("LongShort绩效",
                            ReportEngine.build_longshort(result))
        self._update_export_btn()

    def feed_score(self, fs: FactorScore) -> None:
        self._score = fs
        self._refresh_sheet("综合评分", ReportEngine.build_score(fs))
        self._update_export_btn()

    def clear(self) -> None:
        self._overviews.clear()
        self._ic       = None
        self._decay    = None
        self._quantile = None
        self._score    = None
        for tw in self._tables.values():
            tw.clearContents()
            tw.setRowCount(0)
            tw.setColumnCount(0)
        self.btn_export.setEnabled(False)
        self.lbl_path.setText("尚未导出")

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _refresh_sheet(self, name: str, df: pd.DataFrame) -> None:
        """Render a DataFrame into the named preview QTableWidget."""
        tw = self._tables.get(name)
        if tw is None or df is None:
            return
        tw.clearContents()
        if df.empty:
            tw.setRowCount(0)
            tw.setColumnCount(0)
            return

        cols = list(df.columns)
        tw.setColumnCount(len(cols))
        tw.setHorizontalHeaderLabels(cols)
        tw.setRowCount(len(df))

        for row_idx, row in df.iterrows():
            for col_idx, val in enumerate(row):
                cell_text = "" if (val is None or (isinstance(val, float) and math.isnan(val))) else str(val)
                item = QtWidgets.QTableWidgetItem(cell_text)
                item.setTextAlignment(
                    QtCore.Qt.AlignmentFlag.AlignLeft |
                    QtCore.Qt.AlignmentFlag.AlignVCenter
                )
                tw.setItem(int(row_idx), col_idx, item)

        tw.resizeColumnsToContents()

    def _update_export_btn(self) -> None:
        """Enable export button once at least IC stats are available."""
        self.btn_export.setEnabled(self._ic is not None)

    def _build_meta_df(self) -> pd.DataFrame:
        rows = [
            {"字段": "生成时间",  "值": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
        ]
        if self._ic:
            rows += [
                {"字段": "合约代码",  "值": self._ic.vt_symbol},
                {"字段": "因子名称",  "值": self._ic.factor_name},
                {"字段": "持有期",   "值": f"{self._ic.lag} 天"},
                {"字段": "合约数",   "值": str(self._ic.n_symbols)},
            ]
        if self._quantile:
            rows += [
                {"字段": "分层档数",  "值": str(self._quantile.n_quantiles)},
            ]
        if self._decay:
            rows += [
                {"字段": "Decay max_lag", "值": str(self._decay.max_lag)},
            ]
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------ #
    #  Button callbacks
    # ------------------------------------------------------------------ #

    def _on_export(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        factor    = (self._ic.factor_name if self._ic else "factor").replace(" ", "_")
        default_name = f"factor_report_{factor}_{timestamp}.xlsx"
        default_path = str(self._DEFAULT_DIR / default_name)

        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "导出因子分析报告",
            default_path,
            "Excel 文件 (*.xlsx)",
        )
        if not save_path:
            return

        try:
            meta_df = self._build_meta_df()

            out = ReportEngine.export_excel(
                path=save_path,
                overview_df  = ReportEngine.build_overview(self._overviews),
                ic_df        = ReportEngine.build_ic(self._ic),
                decay_df     = ReportEngine.build_decay(self._decay),
                quantile_df  = ReportEngine.build_quantile(self._quantile),
                longshort_df = ReportEngine.build_longshort(self._quantile),
                score_df     = ReportEngine.build_score(self._score),
                ic_series_df = ReportEngine.build_ic_series(self._ic),
                meta         = {r["字段"]: r["值"] for _, r in meta_df.iterrows()}
                               if not meta_df.empty else None,
            )
            self.lbl_path.setText(str(out))
            QtWidgets.QMessageBox.information(
                self, "导出成功",
                f"报告已保存到：\n{out}"
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "导出失败", f"写入 Excel 时发生错误：\n{exc}"
            )

    def _on_open_dir(self) -> None:
        path_text = self.lbl_path.text()
        if path_text and path_text != "尚未导出" and Path(path_text).exists():
            target = str(Path(path_text).parent)
        else:
            target = str(self._DEFAULT_DIR)
            self._DEFAULT_DIR.mkdir(parents=True, exist_ok=True)

        # cross-platform open folder
        import subprocess, sys
        if sys.platform == "win32":
            os.startfile(target)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
