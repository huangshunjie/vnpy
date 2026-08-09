"""
kline_behavior_lab/ui/pattern_stats_tab.py

形态统计 Tab - 统计条件触发后 T+1~T+5 各天K线形态出现概率
多标签模式：各形态独立计算，百分比之和可超过100%
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QPushButton, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QBrush

from ..pattern_classifier import (
    PATTERN_DEFINITIONS,
    get_pattern_display_names,
    get_pattern_categories,
    classify_bars_vectorized,
)


# 观察天数
OBSERVATION_DAYS = [1, 2, 3, 4, 5]


class PatternStatsTab(QWidget):
    """
    形态统计 Tab

    显示条件触发后 T+1 ~ T+5 各天K线形态出现的概率（多标签统计）
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stats_data: Optional[pd.DataFrame] = None
        self._total_events: int = 0
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 顶部信息栏
        header_layout = QHBoxLayout()

        self.title_label = QLabel("📊 形态统计")
        self.title_label.setFont(QFont("", 12, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #e0e0e0;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.info_label = QLabel("等待研究完成...")
        self.info_label.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        header_layout.addWidget(self.info_label)

        self.refresh_btn = QPushButton("🔄 刷新统计")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
        """)
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        header_layout.addWidget(self.refresh_btn)

        layout.addLayout(header_layout)

        # 说明文字
        note_label = QLabel(
            "注: 多标签统计，各形态独立计算，同一根K线可命中多个形态，百分比之和可超过100%"
        )
        note_label.setStyleSheet("color: #888888; font-size: 10px; padding: 2px 0;")
        layout.addWidget(note_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #333333;")
        layout.addWidget(line)

        # 主表格
        self.table = QTableWidget()
        self._setup_table()
        layout.addWidget(self.table)

        self.setLayout(layout)

    def _setup_table(self):
        """配置表格"""
        pattern_count = len(PATTERN_DEFINITIONS)
        col_count = 1 + len(OBSERVATION_DAYS)  # 形态名 + T+1~T+5

        self.table.setRowCount(pattern_count)
        self.table.setColumnCount(col_count)

        # 表头
        headers = ["K线形态"] + [f"T+{d}" for d in OBSERVATION_DAYS]
        self.table.setHorizontalHeaderLabels(headers)

        # 表头样式
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for i in range(1, col_count):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        # 纵向表头隐藏
        self.table.verticalHeader().setVisible(False)

        # 填充形态名列
        for row, (feat_name, cn_name, category) in enumerate(PATTERN_DEFINITIONS):
            # 形态名（带分类颜色）
            item = QTableWidgetItem(f"  {cn_name}")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # 按分类着色
            color = self._get_category_color(category)
            item.setForeground(QBrush(QColor(color)))
            item.setFont(QFont("", 10))
            self.table.setItem(row, 0, item)

            # 数据列初始化为 "-"
            for col in range(1, col_count):
                cell = QTableWidgetItem("-")
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setForeground(QBrush(QColor("#666666")))
                self.table.setItem(row, col, cell)

        # 行高
        self.table.verticalHeader().setDefaultSectionSize(28)

        # 表格样式
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                gridline-color: #333333;
                color: #e0e0e0;
                border: 1px solid #333333;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 4px 8px;
            }
            QTableWidget::item:selected {
                background-color: #264f78;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #e0e0e0;
                padding: 6px;
                border: 1px solid #333333;
                font-weight: bold;
                font-size: 11px;
            }
        """)

        # 允许排序
        self.table.setSortingEnabled(True)

    def _get_category_color(self, category: str) -> str:
        """按分类返回颜色"""
        colors = {
            "基础方向": "#4fc3f7",
            "影线": "#ffb74d",
            "特殊形态": "#ce93d8",
            "反转组合": "#ef5350",
            "连续形态": "#66bb6a",
            "量价配合": "#ffd54f",
        }
        return colors.get(category, "#e0e0e0")

    def update_stats(self, events_bars: Dict[str, pd.DataFrame], event_indices: Dict[str, List[int]]):
        """
        更新形态统计结果

        Args:
            events_bars: {symbol: DataFrame} 各标的的完整K线数据
            event_indices: {symbol: [idx1, idx2, ...]} 各标的中条件触发日在DataFrame中的行索引
        """
        if not events_bars or not event_indices:
            self.info_label.setText("无事件数据")
            return

        # 统计每个形态在每个观察日的命中次数
        pattern_names = [p[0] for p in PATTERN_DEFINITIONS]
        hit_counts = {p: {d: 0 for d in OBSERVATION_DAYS} for p in pattern_names}
        total_valid = {d: 0 for d in OBSERVATION_DAYS}

        for symbol, df in events_bars.items():
            if symbol not in event_indices or df.empty:
                continue

            # 向量化计算所有形态
            pattern_df = classify_bars_vectorized(df)

            indices = event_indices[symbol]
            max_idx = len(df) - 1

            for trigger_idx in indices:
                for day_offset in OBSERVATION_DAYS:
                    target_idx = trigger_idx + day_offset
                    if target_idx > max_idx:
                        continue

                    total_valid[day_offset] += 1

                    for pattern_name in pattern_names:
                        if pattern_df.iloc[target_idx][pattern_name]:
                            hit_counts[pattern_name][day_offset] += 1

        # 计算百分比
        self._total_events = max(total_valid.values()) if total_valid else 0

        # 更新表格
        self.table.setSortingEnabled(False)

        for row, (feat_name, cn_name, category) in enumerate(PATTERN_DEFINITIONS):
            for col_idx, day_offset in enumerate(OBSERVATION_DAYS):
                col = col_idx + 1
                valid_count = total_valid[day_offset]
                if valid_count > 0:
                    pct = hit_counts[feat_name][day_offset] / valid_count * 100.0
                    item = self.table.item(row, col)
                    item.setText(f"{pct:.1f}%")
                    item.setData(Qt.ItemDataRole.UserRole, pct)  # 用于排序

                    # 着色
                    color = self._pct_to_color(pct)
                    item.setForeground(QBrush(QColor(color)))

        self.table.setSortingEnabled(True)

        # 更新信息栏
        self.info_label.setText(
            f"触发总数: {self._total_events}次 | "
            f"统计形态: {len(pattern_names)}个 | "
            f"观察期: T+1 ~ T+5"
        )
        self.info_label.setStyleSheet("color: #66bb6a; font-size: 11px;")

    def _pct_to_color(self, pct: float) -> str:
        """根据百分比返回颜色"""
        if pct >= 60:
            return "#4caf50"  # 绿色 - 高概率
        elif pct >= 40:
            return "#8bc34a"  # 浅绿
        elif pct >= 25:
            return "#e0e0e0"  # 白色 - 中等
        elif pct >= 10:
            return "#bdbdbd"  # 浅灰
        else:
            return "#666666"  # 深灰 - 低概率

    def _on_refresh_clicked(self):
        """刷新按钮点击"""
        # 通过父组件获取最新研究结果并刷新
        parent = self.parent()
        if parent and hasattr(parent, "refresh_pattern_stats"):
            parent.refresh_pattern_stats()

    def clear_stats(self):
        """清空统计数据"""
        for row in range(self.table.rowCount()):
            for col in range(1, self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setText("-")
                    item.setForeground(QBrush(QColor("#666666")))
                    item.setData(Qt.ItemDataRole.UserRole, 0.0)

        self.info_label.setText("等待研究完成...")
        self.info_label.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        self._total_events = 0