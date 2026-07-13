"""
cross_market_ai/ui/structure_tab.py

Phase 2: Market Structure Mapping — 市场结构映射可视化面板。
"""
from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtWidgets, QtCore, QtGui

from ..constant import APP_NAME
from ..engine import CrossMarketEngine
from ..event import EVENT_CROSS_MARKET_MAPPING_COMPLETED


class StructureTab(QtWidgets.QWidget):
    """市场结构映射面板 — 五维结构向量计算与可视化。"""

    signal_mapped = QtCore.pyqtSignal(dict)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._cm_engine: CrossMarketEngine = main_engine.get_engine(APP_NAME)

        self._init_ui()
        self._register_events()

    # ── UI 构建 ───────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        # 左侧：控制面板
        root.addWidget(self._build_control_panel(), stretch=0)

        # 右侧：结果展示
        right = QtWidgets.QVBoxLayout()
        right.addWidget(self._build_vector_table(), stretch=1)
        right.addWidget(self._build_similarity_panel(), stretch=0)
        right.addWidget(self._build_ranking_panel(), stretch=1)

        right_widget = QtWidgets.QWidget()
        right_widget.setLayout(right)
        root.addWidget(right_widget, stretch=1)

    def _build_control_panel(self) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        frame.setFixedWidth(240)

        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QtWidgets.QLabel("Market Structure Mapper")
        title.setStyleSheet("font-weight: bold; color: #4fc3f7; font-size: 12px;")
        layout.addWidget(title)
        layout.addWidget(_hline())

        # 单市场映射
        layout.addWidget(QtWidgets.QLabel("目标市场:"))
        self._combo_market = QtWidgets.QComboBox()
        self._combo_market.addItems([
            "equity_cn", "futures_cn", "equity_us",
            "crypto", "forex", "fixed_income",
        ])
        layout.addWidget(self._combo_market)

        self._chk_force = QtWidgets.QCheckBox("强制刷新（忽略缓存）")
        layout.addWidget(self._chk_force)

        btn_map = QtWidgets.QPushButton("▶  计算结构向量")
        btn_map.setStyleSheet("background:#1565c0; color:white; padding:4px;")
        btn_map.clicked.connect(self._on_map_single)
        layout.addWidget(btn_map)

        layout.addWidget(_hline())

        # 批量映射
        btn_all = QtWidgets.QPushButton("▶▶  映射全部市场")
        btn_all.setStyleSheet("background:#2e7d32; color:white; padding:4px;")
        btn_all.clicked.connect(self._on_map_all)
        layout.addWidget(btn_all)

        layout.addWidget(_hline())

        # 相似度计算
        layout.addWidget(QtWidgets.QLabel("相似度对比 — 市场A:"))
        self._combo_sim_a = QtWidgets.QComboBox()
        self._combo_sim_a.addItems([
            "equity_cn", "futures_cn", "equity_us",
            "crypto", "forex", "fixed_income",
        ])
        layout.addWidget(self._combo_sim_a)

        layout.addWidget(QtWidgets.QLabel("相似度对比 — 市场B:"))
        self._combo_sim_b = QtWidgets.QComboBox()
        self._combo_sim_b.addItems([
            "futures_cn", "equity_cn", "equity_us",
            "crypto", "forex", "fixed_income",
        ])
        layout.addWidget(self._combo_sim_b)

        btn_sim = QtWidgets.QPushButton("计算结构相似度")
        btn_sim.clicked.connect(self._on_calc_similarity)
        layout.addWidget(btn_sim)

        layout.addWidget(_hline())

        # 排名
        layout.addWidget(QtWidgets.QLabel("按相似度排名 — 源市场:"))
        self._combo_rank_src = QtWidgets.QComboBox()
        self._combo_rank_src.addItems([
            "equity_cn", "futures_cn", "equity_us",
            "crypto", "forex", "fixed_income",
        ])
        layout.addWidget(self._combo_rank_src)

        btn_rank = QtWidgets.QPushButton("排名市场相似度")
        btn_rank.clicked.connect(self._on_rank_markets)
        layout.addWidget(btn_rank)

        layout.addStretch()
        return frame

    def _build_vector_table(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("市场结构向量 Vector(σ, liquidity, regime, noise, correlation)")
        layout = QtWidgets.QVBoxLayout(group)

        self._vector_table = QtWidgets.QTableWidget(0, 8)
        self._vector_table.setHorizontalHeaderLabels([
            "市场", "年化波动率", "价差(bps)", "深度评分",
            "散户占比", "噪音比率", "复杂度", "可迁移性先验",
        ])
        self._vector_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self._vector_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._vector_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._vector_table.setAlternatingRowColors(True)
        layout.addWidget(self._vector_table)
        return group

    def _build_similarity_panel(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("结构相似度 & 迁移可行性")
        layout = QtWidgets.QGridLayout(group)
        layout.setSpacing(8)

        self._lbl_sim_score  = _metric_label("-")
        self._lbl_feasible   = _metric_label("-")
        self._lbl_port_gap   = _metric_label("-")
        self._lbl_recommend  = QtWidgets.QLabel("-")
        self._lbl_recommend.setWordWrap(True)
        self._lbl_recommend.setStyleSheet("color: #ffcc02; font-size: 11px;")

        layout.addWidget(QtWidgets.QLabel("结构相似度:"), 0, 0)
        layout.addWidget(self._lbl_sim_score, 0, 1)
        layout.addWidget(QtWidgets.QLabel("迁移可行性:"), 0, 2)
        layout.addWidget(self._lbl_feasible, 0, 3)
        layout.addWidget(QtWidgets.QLabel("可迁移性差距:"), 1, 0)
        layout.addWidget(self._lbl_port_gap, 1, 1)
        layout.addWidget(QtWidgets.QLabel("建议:"), 1, 2)
        layout.addWidget(self._lbl_recommend, 1, 3)
        return group

    def _build_ranking_panel(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("市场相似度排名（Alpha 迁移候选）")
        layout = QtWidgets.QVBoxLayout(group)

        self._rank_table = QtWidgets.QTableWidget(0, 3)
        self._rank_table.setHorizontalHeaderLabels(["排名", "市场", "结构相似度"])
        self._rank_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self._rank_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._rank_table.setMaximumHeight(160)
        layout.addWidget(self._rank_table)
        return group

    # ── 事件注册 ──────────────────────────────────────────────────────

    def _register_events(self) -> None:
        self.signal_mapped.connect(self._on_mapping_event)
        self._event_engine.register(
            EVENT_CROSS_MARKET_MAPPING_COMPLETED, self.signal_mapped.emit
        )

    # ── 槽函数 ────────────────────────────────────────────────────────

    def _on_map_single(self) -> None:
        market_id = self._combo_market.currentText()
        force     = self._chk_force.isChecked()
        result    = self._cm_engine.map_structure(market_id, force_refresh=force)
        if result.get("status") == "ok":
            self._refresh_vector_table([result["vector"]])

    def _on_map_all(self) -> None:
        result = self._cm_engine.map_all_structures()
        if result.get("status") == "ok":
            vectors = list(result.get("vectors", {}).values())
            self._refresh_vector_table(vectors)

    def _on_calc_similarity(self) -> None:
        market_a = self._combo_sim_a.currentText()
        market_b = self._combo_sim_b.currentText()
        result   = self._cm_engine.get_structure_similarity(market_a, market_b)
        if result.get("status") == "ok":
            self._lbl_sim_score.setText(f"{result.get('similarity', 0):.4f}")
            self._lbl_feasible.setText(f"{result.get('feasibility_score', 0):.4f}")
            self._lbl_port_gap.setText(f"{result.get('portability_gap', 0):.4f}")
            rec = result.get("recommendation", "-")
            self._lbl_recommend.setText(rec)
            color = "#4caf50" if "HIGH" in rec else "#ff9800" if "MODERATE" in rec else "#f44336"
            self._lbl_recommend.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _on_rank_markets(self) -> None:
        source = self._combo_rank_src.currentText()
        result = self._cm_engine.rank_markets_by_similarity(source)
        if result.get("status") == "ok":
            ranked = result.get("ranked", [])
            self._rank_table.setRowCount(0)
            for i, item in enumerate(ranked):
                self._rank_table.insertRow(i)
                self._rank_table.setItem(i, 0, _cell(str(i + 1)))
                self._rank_table.setItem(i, 1, _cell(item["market_id"]))
                score = item["similarity"]
                score_item = _cell(f"{score:.4f}")
                color = "#4caf50" if score >= 0.7 else "#ff9800" if score >= 0.4 else "#f44336"
                score_item.setForeground(QtGui.QColor(color))
                self._rank_table.setItem(i, 2, score_item)

    def _on_mapping_event(self, data: dict) -> None:
        """接收映射完成事件，自动刷新表格。"""
        if data.get("status") == "ok":
            vectors_raw = data.get("vectors")
            if vectors_raw:
                self._refresh_vector_table(list(vectors_raw.values()))
            elif data.get("vector"):
                self._refresh_vector_table([data["vector"]])

    # ── 表格刷新 ──────────────────────────────────────────────────────

    def _refresh_vector_table(self, vectors: list[dict]) -> None:
        """将结构向量列表渲染到表格。"""
        existing = {
            self._vector_table.item(r, 0).text()
            for r in range(self._vector_table.rowCount())
            if self._vector_table.item(r, 0)
        }

        for vec in vectors:
            mid = vec.get("market_id", "")
            vol = vec.get("volatility", {})
            liq = vec.get("liquidity", {})
            par = vec.get("participant", {})
            noi = vec.get("noise", {})

            annual_vol   = vol.get("annual_vol", 0.0)
            spread_bps   = liq.get("bid_ask_spread_bps", 0.0)
            depth_score  = liq.get("depth_score", 0.0)
            retail_ratio = par.get("retail_ratio", 0.0)
            noise_ratio  = noi.get("noise_ratio", 0.0)
            complexity   = vec.get("complexity_score", 0.0)
            portability  = vec.get("portability_score", 0.0)

            if mid in existing:
                for r in range(self._vector_table.rowCount()):
                    if self._vector_table.item(r, 0) and \
                       self._vector_table.item(r, 0).text() == mid:
                        row = r
                        break
                else:
                    row = self._vector_table.rowCount()
                    self._vector_table.insertRow(row)
            else:
                row = self._vector_table.rowCount()
                self._vector_table.insertRow(row)
                existing.add(mid)

            values = [
                mid,
                f"{annual_vol:.4f}",
                f"{spread_bps:.2f}",
                f"{depth_score:.4f}",
                f"{retail_ratio:.4f}",
                f"{noise_ratio:.4f}",
                f"{complexity:.4f}",
                f"{portability:.4f}",
            ]
            for col, val in enumerate(values):
                item = _cell(val)
                if col == 6:
                    color = "#f44336" if complexity > 0.6 else "#ff9800" if complexity > 0.3 else "#4caf50"
                    item.setForeground(QtGui.QColor(color))
                if col == 7:
                    color = "#4caf50" if portability > 0.6 else "#ff9800" if portability > 0.3 else "#f44336"
                    item.setForeground(QtGui.QColor(color))
                self._vector_table.setItem(row, col, item)


# ── 小工具 ────────────────────────────────────────────────────────────

def _hline() -> QtWidgets.QFrame:
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return line


def _metric_label(text: str) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text)
    lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #4fc3f7;")
    return lbl


def _cell(text: str) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(text)
    item.setTextAlignment(QtCore.Qt.AlignCenter)
    return item
