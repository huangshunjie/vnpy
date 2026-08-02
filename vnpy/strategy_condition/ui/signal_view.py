"""
strategy_condition/ui/signal_view.py

三段式信号结果视图：
  第一部分：选股结果表（含导出CSV）
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


class _StatCard(QtWidgets.QWidget):
    """单个统计卡片"""
    def __init__(self, title: str, color: str = _FG):
        super().__init__()
        self.setStyleSheet(
            f"background:{_PANEL};border:1px solid {_BORD};border-radius:6px;")
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(2)
        v.addWidget(_lbl(title, _MUT, 11))
        self._val = _lbl("—", color, 18, True)
        v.addWidget(self._val)

    def set_value(self, text: str, color: Optional[str] = None) -> None:
        self._val.setText(text)
        if color:
            self._val.setStyleSheet(
                f"color:{color};font-size:18px;font-weight:bold;"
                f"background:transparent;border:none;")


class _NumericItem(QtWidgets.QTableWidgetItem):
    """自定义 QTableWidgetItem，重写 __lt__ 使排序按 UserRole 数值进行"""
    def __lt__(self, other: QtWidgets.QTableWidgetItem) -> bool:
        left_data = self.data(QtCore.Qt.ItemDataRole.UserRole)
        right_data = other.data(QtCore.Qt.ItemDataRole.UserRole)

        # 如果两侧都有数值，做数值比较
        if left_data is not None and right_data is not None:
            try:
                return float(left_data) < float(right_data)
            except (TypeError, ValueError):
                pass

        # 退回文本比较（避免调用 super().__lt__ 引发 PyQt 递归）
        return (self.text() or "") < (other.text() or "")


class _SortableTable(QtWidgets.QTableWidget):
    """可点击排序的表格，按UserRole中的数值排序"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSortingEnabled(True)

    def add_row(self, cells) -> None:
        """cells: [(text, color, sort_key_or_None), ...]"""
        row = self.rowCount()
        self.insertRow(row)
        for col, (text, color, sort_key) in enumerate(cells):
            item = _NumericItem()
            item.setText(text)
            if sort_key is not None:
                item.setData(QtCore.Qt.ItemDataRole.UserRole, float(sort_key))
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            item.setForeground(QtGui.QColor(color))
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.setItem(row, col, item)


# ══════════════════════════════════════════════════════════════════════
# 主视图
# ══════════════════════════════════════════════════════════════════════

class SignalView(QtWidgets.QWidget):
    """
    信号结果视图：只保留选股结果
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

        # ── 第一部分：只保留选股结果 ────────────────────────────────────────
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
        self._scan_table.setColumnCount(11)
        self._scan_table.setHorizontalHeaderLabels(
            ["代码", "买入时间", "买入价", "策略名称",
             "回测笔数", "命中数", "命中率", "平均收益%", "总收益率", "综合评分", "最近买入日"])
        self._scan_table.setStyleSheet(_TBL_SS)
        # 设置列宽
        for i, w in enumerate([110, 110, 70, 100, 65, 60, 65, 75, 75, 70, 110]):
            self._scan_table.setColumnWidth(i, w)
        self._scan_table.horizontalHeader().setStretchLastSection(True)
        self._scan_table.verticalHeader().setVisible(False)
        self._scan_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._scan_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._scan_table.clicked.connect(self._on_scan_row_clicked)
        v1.addWidget(self._scan_table)
        splitter.addWidget(sec1)

        splitter.setSizes([500])
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
        else:
            self._scan_sigs = list(batch.signals)
            self._bt_sigs   = []
            self._hit_map   = {}
            self._fill_scan_only()

    def load_signals(self, signals: list) -> None:
        self._scan_sigs = list(signals)
        self._fill_scan_only()

    def clear(self) -> None:
        self._scan_table.setRowCount(0)
        self._scan_count_lbl.setText("共 0 只")

    # ── 填充第一部分 ─────────────────────────────────────────────────

    def _fill_scan_only(self) -> None:
        t = self._scan_table
        t.setRowCount(0)
        for s in self._scan_sigs:
            self._add_scan_row(s)
        self._scan_count_lbl.setText(f"共 {len(self._scan_sigs)} 只")

    def _fill_scan_from_bt(self) -> None:
        t = self._scan_table
        t.setRowCount(0)
        added = set()
        for s in self._bt_sigs:
            sym = s.symbol
            if sym not in added:
                self._add_scan_row(s)
                added.add(sym)
        self._scan_count_lbl.setText(f"共 {len(added)} 只")

    def _add_scan_row(self, rec: SignalRecord) -> None:
        from collections import defaultdict
        
        dt_str = str(rec.dt)
        if " 00:00:00" in dt_str:
            dt_str = dt_str[:10]
        else:
            dt_str = dt_str[:16]
        
        # 计算统计信息
        total_cnt = 0
        hit_cnt = 0
        hit_rate = ""
        if self._hit_map and rec.symbol in self._hit_map:
            # _hit_map 已经是 "hit/total (pct%)" 格式，解析出各部分
            text = self._hit_map[rec.symbol]
            if "/" in text:
                hit_part, rest = text.split("/", 1)
                hit_cnt = int(hit_part)
                total_cnt = int(rest.split("(", 1)[0])
                hit_rate = text.split("(")[-1].rstrip(")")
        
        # 最近买入日期
        latest_dt_str = dt_str
        if self._bt_sigs:
            # 找这只股票最新的买入日期
            sym_signals = [s for s in self._bt_sigs if s.symbol == rec.symbol]
            if sym_signals:
                latest_sig = max(sym_signals, key=lambda s: s.dt)
                ld = str(latest_sig.dt)
                if " 00:00:00" in ld:
                    latest_dt_str = ld[:10]
                else:
                    latest_dt_str = ld[:16]
        
        # 颜色判断：命中率越高越绿
        pct = 0.0
        avg_ret = 0.0
        total_ret = 0.0
        score = 0.0
        color_score = _FG
        
        if total_cnt > 0:
            pct = hit_cnt / total_cnt
            
            # 计算平均收益和总收益率
            sym_signals = [s for s in self._bt_sigs if s.symbol == rec.symbol]
            if sym_signals:
                total_pct = sum(s.pnl_pct for s in sym_signals if s.pnl_pct is not None)
                avg_ret = total_pct / len(sym_signals) * 100
                # 总收益率 = (1+每个单次收益率) 相乘 - 1，复利计算
                compound = 1.0
                for s in sym_signals:
                    if s.pnl_pct is not None:
                        compound *= (1 + s.pnl_pct)
                total_ret = (compound - 1) * 100
            
            # 综合评分 = 命中率 × (1 + 平均收益) × sqrt(回测笔数)
            # 综合考虑命中率、平均收益、样本数量
            score = pct * (1 + avg_ret/100) * (total_cnt ** 0.5) * 100
        
        # 颜色：命中率绿色红色，评分同样颜色
        color_pct = _GRN if pct >= 0.5 else _RED if pct < 0.3 else _FG
        color_avg = _GRN if avg_ret > 0 else _RED if avg_ret < 0 else _FG
        color_total = _GRN if total_ret > 0 else _RED if total_ret < 0 else _FG
        color_score = _GRN if score >= 20 else _RED if score < 5 else _FG
        
        row = [
            (rec.symbol, _FG, None),
            (dt_str, _FG, None),
            (f"{rec.price:.2f}", _FG, rec.price),
            (rec.strategy_name, _FG, None),
            (str(total_cnt), _FG, total_cnt),
            (str(hit_cnt), _FG, hit_cnt),
            (f"{pct*100:.0f}%", color_pct, pct),
            (f"{avg_ret:.2f}", color_avg, avg_ret),
            (f"{total_ret:.1f}%", color_total, total_ret),
            (f"{score:.1f}", color_score, score),
            (latest_dt_str, _MUT, None),
        ]
        self._scan_table.add_row(row)

    # ── 导出 CSV ──────────────────────────────────────────────────────

    def _export_scan_csv(self) -> None:
        if not self._scan_sigs:
            self._show_msg("没有选股结果可导出")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出选股结果", "", "CSV Files (*.csv);;All Files (*)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["代码", "买入时间", "买入价", "策略名称", "回测笔数", "命中数", "命中率",
                       "平均收益%", "总收益率", "综合评分", "最近买入日"])
            for s in self._scan_sigs:
                dt_str = str(s.dt)
                if " 00:00:00" in dt_str:
                    dt_str = dt_str[:10]
                else:
                    dt_str = dt_str[:16]
                
                # 计算统计信息
                total_cnt = 0
                hit_cnt = 0
                hit_rate_pct = 0.0
                avg_ret = 0.0
                total_ret = 0.0
                score = 0.0
                hit_rate_str = ""
                if self._hit_map and s.symbol in self._hit_map:
                    text = self._hit_map[s.symbol]
                    if "/" in text:
                        hit_part, rest = text.split("/", 1)
                        hit_cnt = int(hit_part)
                        total_cnt = int(rest.split("(", 1)[0])
                        hit_rate_str = text.split("(")[-1].rstrip(")")
                        hit_rate_pct = hit_cnt / total_cnt
                
                # 计算平均收益和总收益率
                if total_cnt > 0 and self._bt_sigs:
                    sym_signals = [sig for sig in self._bt_sigs if sig.symbol == s.symbol]
                    if sym_signals:
                        total_pct = sum(sig.pnl_pct for sig in sym_signals if sig.pnl_pct is not None)
                        avg_ret = total_pct / len(sym_signals) * 100
                        # 复利计算总收益率
                        compound = 1.0
                        for sig in sym_signals:
                            if sig.pnl_pct is not None:
                                compound *= (1 + sig.pnl_pct)
                        total_ret = (compound - 1) * 100
                        # 综合评分
                        score = hit_rate_pct * (1 + avg_ret/100) * (total_cnt ** 0.5) * 100
                
                # 最近买入日期
                latest_dt_str = dt_str
                if self._bt_sigs:
                    sym_signals = [sig for sig in self._bt_sigs if sig.symbol == s.symbol]
                    if sym_signals:
                        latest_sig = max(sym_signals, key=lambda sig: sig.dt)
                        ld = str(latest_sig.dt)
                        if " 00:00:00" in ld:
                            latest_dt_str = ld[:10]
                        else:
                            latest_dt_str = ld[:16]
                
                w.writerow([s.symbol, dt_str, f"{s.price:.4f}",
                           s.strategy_name, str(total_cnt), str(hit_cnt), hit_rate_str,
                           f"{avg_ret:.2f}", f"{total_ret:.1f}%", f"{score:.1f}", latest_dt_str])
        self._show_msg(f"已导出到 {path}")

    # ── 点击事件 ──────────────────────────────────────────────────────

    def _on_scan_row_clicked(self, index) -> None:
        row = index.row()
        sym_item = self._scan_table.item(row, 0)
        if not sym_item:
            return
        sym = sym_item.text()
        # 找到对应的信号记录转发给点击处理
        found = None
        for s in self._scan_sigs:
            if s.symbol == sym:
                found = s
                break
        if not found and self._bt_sigs:
            for s in self._bt_sigs:
                if s.symbol == sym:
                    found = s
                    break
        if found:
            self.signal_selected.emit(found)

    def _show_msg(self, msg: str) -> None:
        QtWidgets.QMessageBox.information(self, "提示", msg)


def _hit_rate_map(signals: List[SignalRecord]) -> Dict[str, str]:
    """按symbol统计命中率"""
    from collections import defaultdict
    cnt = defaultdict(int)
    hit = defaultdict(int)
    for s in signals:
        cnt[s.symbol] += 1
        if s.pnl_pct and s.pnl_pct > 0:
            hit[s.symbol] += 1
    result: Dict[str, str] = {}
    for sym, total in cnt.items():
        h = hit[sym]
        pct = h / total * 100
        result[sym] = f"{h}/{total} ({pct:.0f}%)"
    return result
