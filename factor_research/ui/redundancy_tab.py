"""
factor_research/ui/redundancy_tab.py

RedundancyTab -- Factor redundancy analysis Tab.

Layout:
  toolbar (threshold spinbox + clear + info)
  top-row: pairs table (left) | uniqueness rank table (right)
  bottom:  suggestion text area

Data flow:
  widget routes "correlation" event to both CorrelationTab and RedundancyTab.
  feed_ic() accumulates IcStats; analysis reruns on every new factor.
"""

from __future__ import annotations

from pyqtgraph.Qt import QtCore, QtWidgets

from ..engine.redundancy_engine import CorrelationResult, RedundancyEngine
from ..model import IcStats

_DEFAULT_THRESHOLD = 0.70
_FG = "#cdd6f4"


class RedundancyTab(QtWidgets.QWidget):
    """Factor redundancy analysis Tab."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._ic_list:   list[IcStats] = []
        self._result:    CorrelationResult | None = None
        self._threshold: float = _DEFAULT_THRESHOLD
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self._build_toolbar())

        self._placeholder = QtWidgets.QLabel(
            "每运行一个因子后，其 IC 序列将在此累积。\n"
            "积累 \u2265 2 个因子后自动显示冗余分析结果。"
        )
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #6c7086; font-size: 13px;")
        root.addWidget(self._placeholder, stretch=1)

        self._content = QtWidgets.QWidget()
        self._content.hide()
        root.addWidget(self._content, stretch=1)

        cl = QtWidgets.QVBoxLayout(self._content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(6)

        tables_row = QtWidgets.QHBoxLayout()

        pair_group = QtWidgets.QGroupBox("因子对相关性")
        pl = QtWidgets.QVBoxLayout(pair_group)
        self.tbl_pairs = self._make_table(["因子 A", "因子 B", "Pearson r", "判定"])
        pl.addWidget(self.tbl_pairs)
        tables_row.addWidget(pair_group, stretch=3)

        uniq_group = QtWidgets.QGroupBox("因子唯一性排名（越小越独特）")
        ul = QtWidgets.QVBoxLayout(uniq_group)
        self.tbl_unique = self._make_table(["因子名称", "平均 |r|", "状态"])
        ul.addWidget(self.tbl_unique)
        tables_row.addWidget(uniq_group, stretch=2)

        cl.addLayout(tables_row, stretch=3)

        sug_group = QtWidgets.QGroupBox("分析建议")
        sl = QtWidgets.QVBoxLayout(sug_group)
        self.txt_suggestion = QtWidgets.QTextEdit()
        self.txt_suggestion.setReadOnly(True)
        self.txt_suggestion.setMaximumHeight(120)
        self.txt_suggestion.setStyleSheet(
            "background: #181825; color: #cdd6f4; font-size: 12px;"
        )
        sl.addWidget(self.txt_suggestion)
        cl.addWidget(sug_group, stretch=1)

    def _build_toolbar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        btn_clear = QtWidgets.QPushButton("清空")
        btn_clear.setFixedHeight(26)
        btn_clear.clicked.connect(self.clear)

        self.spin_threshold = QtWidgets.QDoubleSpinBox()
        self.spin_threshold.setRange(0.50, 0.99)
        self.spin_threshold.setSingleStep(0.05)
        self.spin_threshold.setValue(_DEFAULT_THRESHOLD)
        self.spin_threshold.setDecimals(2)
        self.spin_threshold.setFixedWidth(70)
        self.spin_threshold.setToolTip("|r| \u2265 此值视为高度相关")
        self.spin_threshold.valueChanged.connect(self._on_threshold_changed)

        self.lbl_count = QtWidgets.QLabel("已积累 0 个因子")
        self.lbl_count.setStyleSheet(f"color:{_FG};")
        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setStyleSheet("color: #6c7086; font-size: 11px;")

        layout.addWidget(btn_clear)
        layout.addWidget(QtWidgets.QLabel("冗余阈值"))
        layout.addWidget(self.spin_threshold)
        layout.addWidget(self.lbl_count)
        layout.addStretch()
        layout.addWidget(self.lbl_info)
        return bar

    @staticmethod
    def _make_table(headers: list[str]) -> QtWidgets.QTableWidget:
        tw = QtWidgets.QTableWidget()
        tw.setColumnCount(len(headers))
        tw.setHorizontalHeaderLabels(headers)
        tw.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        tw.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        tw.setAlternatingRowColors(True)
        tw.verticalHeader().setVisible(False)
        tw.horizontalHeader().setStretchLastSection(True)
        return tw

    # ------------------------------------------------------------------ #
    #  Public interface
    # ------------------------------------------------------------------ #

    def feed_ic(self, stats: IcStats) -> None:
        """Accumulate one factor's IcStats. Replace if same factor_name."""
        if stats.ic_series is None or stats.ic_series.dropna().empty:
            return
        self._ic_list = [s for s in self._ic_list
                         if s.factor_name != stats.factor_name]
        self._ic_list.append(stats)
        self._recompute()

    def clear(self) -> None:
        self._ic_list.clear()
        self._result = None
        for tw in (self.tbl_pairs, self.tbl_unique):
            tw.setRowCount(0)
        self.lbl_count.setText("已积累 0 个因子")
        self.lbl_info.setText("")
        self.txt_suggestion.clear()
        self._content.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  Internal
    # ------------------------------------------------------------------ #

    def _on_threshold_changed(self, value: float) -> None:
        self._threshold = value
        if self._result is not None:
            self._recompute()

    def _recompute(self) -> None:
        n = len(self._ic_list)
        self.lbl_count.setText(f"已积累 {n} 个因子")
        if n < 1:
            return
        self._result = RedundancyEngine.compute(
            self._ic_list, threshold=self._threshold
        )
        self._render(self._result)

    def _render(self, result: CorrelationResult) -> None:
        # ── pairs table ──────────────────────────────────────────────
        pairs = result.redundant_pairs
        self.tbl_pairs.setRowCount(len(pairs))
        for row, pair in enumerate(pairs):
            is_red = pair.is_redundant
            cells = [
                pair.factor_a,
                pair.factor_b,
                f"{pair.correlation:+.4f}",
                "\u26a0 冗余" if is_red else "\u2713 正常",
            ]
            for col, text in enumerate(cells):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if is_red:
                    item.setBackground(QtCore.Qt.GlobalColor.darkRed)
                self.tbl_pairs.setItem(row, col, item)
        self.tbl_pairs.resizeColumnsToContents()

        # ── uniqueness table ─────────────────────────────────────────
        ranked = RedundancyEngine.uniqueness_rank(result)
        self.tbl_unique.setRowCount(len(ranked))
        for row, (name, mean_corr) in enumerate(ranked):
            is_dup = mean_corr >= self._threshold
            cells = [name, f"{mean_corr:.4f}", "\u26a0 高冗余" if is_dup else "\u2713 独特"]
            for col, text in enumerate(cells):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if is_dup and col == 2:
                    item.setForeground(QtCore.Qt.GlobalColor.red)
                self.tbl_unique.setItem(row, col, item)
        self.tbl_unique.resizeColumnsToContents()

        # ── info label ────────────────────────────────────────────────
        n_red = len(RedundancyEngine.redundant_only(result))
        n_tot = len(pairs)
        self.lbl_info.setText(
            f"{len(result.factor_names)} 个因子  "
            f"冗余对 {n_red}/{n_tot}  "
            f"对齐样本 {result.n_samples} 期"
        )

        # ── suggestion ────────────────────────────────────────────────
        self.txt_suggestion.setPlainText(self._build_suggestion(result))
        self._placeholder.hide()
        self._content.show()

    def _build_suggestion(self, result: CorrelationResult) -> str:
        lines: list[str] = []
        n         = len(result.factor_names)
        red_pairs = RedundancyEngine.redundant_only(result)
        ranked    = RedundancyEngine.uniqueness_rank(result)

        if n == 1:
            lines.append("当前仅有 1 个因子，无法进行冗余分析。请继续运行更多因子。")
            return "\n".join(lines)

        if not red_pairs:
            lines.append(
                f"\u2713 全部 {len(result.redundant_pairs)} 对因子的 |r| < "
                f"{self._threshold:.2f}，未发现冗余因子对。"
            )
        else:
            lines.append(
                f"\u26a0 发现 {len(red_pairs)} 对高度相关因子"
                f"（|r| \u2265 {self._threshold:.2f}）："
            )
            seen: set[str] = set()
            for p in red_pairs:
                lines.append(
                    f"  \u2022 {p.factor_a}  \u2194  {p.factor_b}  "
                    f"r = {p.correlation:+.4f}"
                )
                u_a  = result.uniqueness.get(p.factor_a, 1.0)
                u_b  = result.uniqueness.get(p.factor_b, 1.0)
                keep = p.factor_a if u_a <= u_b else p.factor_b
                drop = p.factor_b if u_a <= u_b else p.factor_a
                if drop not in seen:
                    lines.append(
                        f"    \u2192 建议保留 {keep}"
                        f"（平均|r|={result.uniqueness.get(keep, 0):.4f}），"
                        f"考虑剔除 {drop}"
                        f"（平均|r|={result.uniqueness.get(drop, 0):.4f}）"
                    )
                    seen.add(drop)

        lines.append("")
        lines.append("因子唯一性排名（越小越独特）：")
        for i, (name, val) in enumerate(ranked, 1):
            lines.append(f"  {i}. {name}  平均|r|={val:.4f}")

        return "\n".join(lines)
