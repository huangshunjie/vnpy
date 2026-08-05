"""
quant_research/ui/log_tab.py  — 完整实现

日志管理标签页 — 提供日志查看、筛选、导出等功能。
"""
from __future__ import annotations
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox, QLineEdit,
    QLabel, QGroupBox, QSplitter, QTextEdit, QCheckBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont

from vnpy.event import Event

from ..engine import ResearchEngine
from ..constant import LogLevel, LogSource
from ..event import EVENT_LOG_MESSAGE


LEVEL_COLORS = {
    LogLevel.DEBUG:    QColor("#6c757d"),
    LogLevel.INFO:     QColor("#0d6efd"),
    LogLevel.WARNING:  QColor("#ffc107"),
    LogLevel.ERROR:    QColor("#dc3545"),
    LogLevel.CRITICAL: QColor("#8b0000"),
}

COL_TIME, COL_LEVEL, COL_SOURCE, COL_CONTEXT, COL_MESSAGE = 0, 1, 2, 3, 4
HEADERS = ["时间", "级别", "来源", "上下文", "消息"]


class LogTab(QWidget):
    """日志管理标签页"""

    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._auto_scroll = True
        self._max_display = 500
        self._init_ui()
        self._register_events()
        self._start_auto_refresh()
        self._load_recent_logs()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # 工具栏
        toolbar = self._create_toolbar()
        root.addLayout(toolbar)

        # 日志表格和详情
        splitter = self._create_content()
        root.addWidget(splitter, 1)

        # 统计栏
        stats = self._create_stats()
        root.addLayout(stats)

    def _create_toolbar(self):
        toolbar = QHBoxLayout()
        
        toolbar.addWidget(QLabel("级别:"))
        self._level_combo = QComboBox()
        self._level_combo.addItem("全部", None)
        for level in LogLevel:
            self._level_combo.addItem(level.value.upper(), level)
        self._level_combo.currentIndexChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._level_combo)

        toolbar.addWidget(QLabel("来源:"))
        self._source_combo = QComboBox()
        self._source_combo.addItem("全部", None)
        for source in LogSource:
            self._source_combo.addItem(source.value.upper(), source)
        self._source_combo.currentIndexChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._source_combo)

        toolbar.addWidget(QLabel("搜索:"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("输入关键词...")
        self._search_edit.setFixedWidth(200)
        self._search_edit.textChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._search_edit)

        toolbar.addStretch()

        self._auto_scroll_check = QCheckBox("自动滚动")
        self._auto_scroll_check.setChecked(True)
        self._auto_scroll_check.toggled.connect(lambda c: setattr(self, '_auto_scroll', c))
        toolbar.addWidget(self._auto_scroll_check)

        for text, slot in [("刷新", self._refresh_logs), ("清空", self._clear_logs), ("导出", self._export_logs)]:
            btn = QPushButton(text)
            btn.setFixedWidth(60)
            btn.clicked.connect(slot)
            toolbar.addWidget(btn)

        return toolbar

    def _create_content(self):
        splitter = QSplitter(Qt.Vertical)

        self._log_table = QTableWidget(0, len(HEADERS))
        self._log_table.setHorizontalHeaderLabels(HEADERS)
        self._log_table.horizontalHeader().setSectionResizeMode(COL_MESSAGE, QHeaderView.Stretch)
        self._log_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._log_table.setAlternatingRowColors(True)
        self._log_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._log_table.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._log_table)

        detail_group = QGroupBox("日志详情")
        detail_layout = QVBoxLayout(detail_group)
        self._detail_edit = QTextEdit()
        self._detail_edit.setReadOnly(True)
        self._detail_edit.setMaximumHeight(150)
        detail_layout.addWidget(self._detail_edit)
        splitter.addWidget(detail_group)

        splitter.setSizes([400, 150])
        return splitter

    def _create_stats(self):
        stats = QHBoxLayout()
        self._total_label = QLabel("总计: 0")
        self._debug_label = QLabel("DEBUG: 0")
        self._info_label = QLabel("INFO: 0")
        self._warning_label = QLabel("WARNING: 0")
        self._error_label = QLabel("ERROR: 0")
        self._critical_label = QLabel("CRITICAL: 0")

        for lbl in [self._total_label, self._debug_label, self._info_label,
                    self._warning_label, self._error_label, self._critical_label]:
            lbl.setStyleSheet("padding: 4px 8px; background: #f8f9fa; border: 1px solid #dee2e6;")
            stats.addWidget(lbl)
        
        stats.addStretch()
        return stats

    def _register_events(self):
        self.engine.event_engine.register(EVENT_LOG_MESSAGE, self._on_log_event)

    def _start_auto_refresh(self):
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_stats)
        self._refresh_timer.start(5000)

    def _on_log_event(self, event: Event):
        log_record = event.data
        if self._should_display(log_record):
            self._add_log_row(log_record)
            if self._auto_scroll:
                self._log_table.scrollToBottom()
        self._refresh_stats()

    def _should_display(self, log_record) -> bool:
        level_filter = self._level_combo.currentData()
        if level_filter and log_record.level != level_filter:
            return False
        source_filter = self._source_combo.currentData()
        if source_filter and log_record.source != source_filter:
            return False
        keyword = self._search_edit.text().strip()
        if keyword and keyword.lower() not in log_record.message.lower():
            return False
        return True

    def _add_log_row(self, log_record):
        if self._log_table.rowCount() >= self._max_display:
            self._log_table.removeRow(0)

        row = self._log_table.rowCount()
        self._log_table.insertRow(row)

        time_item = QTableWidgetItem(log_record.timestamp.strftime("%H:%M:%S"))
        time_item.setData(Qt.UserRole, log_record)
        self._log_table.setItem(row, COL_TIME, time_item)

        level_item = QTableWidgetItem(log_record.level.value.upper())
        level_item.setForeground(LEVEL_COLORS.get(log_record.level, QColor("#000")))
        font = QFont()
        font.setBold(True)
        level_item.setFont(font)
        self._log_table.setItem(row, COL_LEVEL, level_item)

        self._log_table.setItem(row, COL_SOURCE, QTableWidgetItem(log_record.source.value.upper()))
        self._log_table.setItem(row, COL_CONTEXT, QTableWidgetItem(log_record.context_id or "-"))
        self._log_table.setItem(row, COL_MESSAGE, QTableWidgetItem(log_record.message))

    def _load_recent_logs(self):
        try:
            logs = self.engine.get_recent_logs(self._max_display)
            self._log_table.setRowCount(0)
            for log_record in logs:
                if self._should_display(log_record):
                    self._add_log_row(log_record)
            self._refresh_stats()
        except AttributeError:
            pass

    def _on_filter_changed(self):
        self._load_recent_logs()

    def _refresh_logs(self):
        self._load_recent_logs()

    def _clear_logs(self):
        try:
            self.engine.clear_logs()
        except AttributeError:
            pass
        self._log_table.setRowCount(0)
        self._detail_edit.clear()
        self._refresh_stats()

    def _export_logs(self):
        from PySide6.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出日志", 
            f"research_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )
        if not filename:
            return
        try:
            logs = self.engine.get_recent_logs(10000)
            with open(filename, 'w', encoding='utf-8') as f:
                for log in logs:
                    f.write(f"[{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
                           f"[{log.level.value.upper()}] [{log.source.value.upper()}] {log.message}\n")
            self.engine.log(LogLevel.INFO, LogSource.SYSTEM, f"日志已导出到: {filename}")
        except Exception as e:
            print(f"导出失败: {e}")

    def _on_selection_changed(self):
        selected = self._log_table.selectedItems()
        if not selected:
            self._detail_edit.clear()
            return
        row = selected[0].row()
        time_item = self._log_table.item(row, COL_TIME)
        if not time_item:
            return
        log_record = time_item.data(Qt.UserRole)
        if not log_record:
            return

        details = [
            f"日志 ID: {log_record.log_id}",
            f"时间: {log_record.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}",
            f"级别: {log_record.level.value.upper()}",
            f"来源: {log_record.source.value.upper()}",
        ]
        if log_record.context_id:
            details.append(f"上下文 ID: {log_record.context_id}")
        if log_record.user:
            details.append(f"用户: {log_record.user}")
        details.append(f"\n消息:\n{log_record.message}")
        if log_record.details:
            details.append(f"\n详情:\n{log_record.details}")
        self._detail_edit.setPlainText("\n".join(details))

    def _refresh_stats(self):
        try:
            stats = self.engine.get_log_statistics()
            self._total_label.setText(f"总计: {stats.get('total', 0)}")
            by_level = stats.get('by_level', {})
            self._debug_label.setText(f"DEBUG: {by_level.get(LogLevel.DEBUG, 0)}")
            self._info_label.setText(f"INFO: {by_level.get(LogLevel.INFO, 0)}")
            self._warning_label.setText(f"WARNING: {by_level.get(LogLevel.WARNING, 0)}")
            self._error_label.setText(f"ERROR: {by_level.get(LogLevel.ERROR, 0)}")
            self._critical_label.setText(f"CRITICAL: {by_level.get(LogLevel.CRITICAL, 0)}")
            
            # 高亮警告和错误
            self._warning_label.setStyleSheet(
                f"padding: 4px 8px; background: {'#fff3cd' if by_level.get(LogLevel.WARNING, 0) > 0 else '#f8f9fa'}; "
                f"border: 1px solid #dee2e6;"
            )
            self._error_label.setStyleSheet(
                f"padding: 4px 8px; background: {'#f8d7da' if by_level.get(LogLevel.ERROR, 0) > 0 else '#f8f9fa'}; "
                f"border: 1px solid #dee2e6;"
            )
            self._critical_label.setStyleSheet(
                f"padding: 4px 8px; background: {'#dc3545' if by_level.get(LogLevel.CRITICAL, 0) > 0 else '#f8f9fa'}; "
                f"color: {'white' if by_level.get(LogLevel.CRITICAL, 0) > 0 else 'black'}; border: 1px solid #dee2e6;"
            )
        except (AttributeError, TypeError):
            pass

    def append(self, msg: str) -> None:
        """向后兼容方法"""
        try:
            self.engine.log(LogLevel.INFO, LogSource.SYSTEM, msg)
        except AttributeError:
            pass
