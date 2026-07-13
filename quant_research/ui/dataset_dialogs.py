"""
quant_research/ui/dataset_dialogs.py

DatasetCreateDialog — 注册 / 编辑数据集对话框
"""
from __future__ import annotations
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QVBoxLayout, QDoubleSpinBox, QSpinBox,
    QComboBox,
)
from PySide6.QtCore import Qt

from ..constant import DatasetStatus
from ..model.dataset_model import DatasetRecord


class _ListEditor(QPushButton):
    """简易列表编辑器：点击弹出文本框输入逗号分隔值。"""

    def __init__(self, placeholder: str, parent=None):
        super().__init__(parent)
        self._items: List[str] = []
        self._placeholder = placeholder
        self._refresh_text()
        self.clicked.connect(self._edit)

    def _refresh_text(self):
        if self._items:
            self.setText(", ".join(self._items[:3])
                         + (f" …+{len(self._items)-3}" if len(self._items) > 3 else ""))
        else:
            self.setText(self._placeholder)

    def _edit(self):
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            self, "编辑列表",
            "用英文逗号分隔多个值：",
            text=", ".join(self._items),
        )
        if ok:
            self._items = [x.strip() for x in text.split(",") if x.strip()]
            self._refresh_text()

    def set_items(self, items: List[str]):
        self._items = list(items)
        self._refresh_text()

    def get_items(self) -> List[str]:
        return list(self._items)


class DatasetCreateDialog(QDialog):
    """注册 / 编辑数据集对话框。"""

    def __init__(self, parent=None, record: Optional[DatasetRecord] = None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle("编辑数据集" if self._editing else "注册数据集")
        self.setMinimumWidth(520)
        self._init_ui()
        if self._editing:
            self._load_record()

    def _init_ui(self):
        root = QVBoxLayout(self)

        # ── 基本信息 ──────────────────────────────────────────────────
        info_grp = QGroupBox("基本信息")
        form = QFormLayout(info_grp)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("数据集名称（必填）")
        form.addRow("名称 *", self._name_edit)

        self._version_edit = QLineEdit("v1.0")
        form.addRow("版本", self._version_edit)

        self._source_edit = QLineEdit()
        self._source_edit.setPlaceholderText("数据来源（如 Wind / Tushare / 自采）")
        form.addRow("来源", self._source_edit)

        self._desc_edit = QPlainTextEdit()
        self._desc_edit.setPlaceholderText("描述")
        self._desc_edit.setFixedHeight(60)
        form.addRow("描述", self._desc_edit)

        self._status_combo = QComboBox()
        for s in DatasetStatus:
            self._status_combo.addItem(s.value, s)
        form.addRow("状态", self._status_combo)

        self._author_edit = QLineEdit()
        form.addRow("创建人", self._author_edit)

        root.addWidget(info_grp)

        # ── 时间范围 ──────────────────────────────────────────────────
        range_grp = QGroupBox("时间范围 & 规模")
        rf = QFormLayout(range_grp)

        self._start_edit = QLineEdit()
        self._start_edit.setPlaceholderText("YYYY-MM-DD")
        rf.addRow("开始日期", self._start_edit)

        self._end_edit = QLineEdit()
        self._end_edit.setPlaceholderText("YYYY-MM-DD")
        rf.addRow("结束日期", self._end_edit)

        self._row_spin = QSpinBox()
        self._row_spin.setRange(0, 2_000_000_000)
        self._row_spin.setSuffix("  行")
        rf.addRow("行数", self._row_spin)

        self._size_spin = QDoubleSpinBox()
        self._size_spin.setRange(0.0, 1_000_000.0)
        self._size_spin.setDecimals(2)
        self._size_spin.setSuffix("  MB")
        rf.addRow("大小", self._size_spin)

        root.addWidget(range_grp)

        # ── 标的 / 字段 / 标签 ────────────────────────────────────────
        ext_grp = QGroupBox("标的 / 字段 / 标签")
        ef = QFormLayout(ext_grp)

        self._symbols_btn = _ListEditor("点击编辑标的列表")
        ef.addRow("标的", self._symbols_btn)

        self._fields_btn = _ListEditor("点击编辑字段列表")
        ef.addRow("字段", self._fields_btn)

        self._tags_btn = _ListEditor("点击编辑标签")
        ef.addRow("标签", self._tags_btn)

        root.addWidget(ext_grp)

        # ── 按钮 ──────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_record(self):
        r = self._record
        self._name_edit.setText(r.name)
        self._version_edit.setText(r.version)
        self._source_edit.setText(r.source)
        self._desc_edit.setPlainText(r.description)
        idx = self._status_combo.findData(r.status)
        if idx >= 0:
            self._status_combo.setCurrentIndex(idx)
        self._author_edit.setText(r.created_by)
        self._start_edit.setText(r.start_date)
        self._end_edit.setText(r.end_date)
        self._row_spin.setValue(r.row_count)
        self._size_spin.setValue(r.size_mb)
        self._symbols_btn.set_items(r.symbols)
        self._fields_btn.set_items(r.fields)
        self._tags_btn.set_items(r.tags)

    def _on_accept(self):
        if not self._name_edit.text().strip():
            self._name_edit.setFocus()
            return
        self.accept()

    def get_name(self)        -> str:            return self._name_edit.text().strip()
    def get_version(self)     -> str:            return self._version_edit.text().strip() or "v1.0"
    def get_source(self)      -> str:            return self._source_edit.text().strip()
    def get_description(self) -> str:            return self._desc_edit.toPlainText().strip()
    def get_status(self)      -> DatasetStatus:  return self._status_combo.currentData()
    def get_author(self)      -> str:            return self._author_edit.text().strip()
    def get_start_date(self)  -> str:            return self._start_edit.text().strip()
    def get_end_date(self)    -> str:            return self._end_edit.text().strip()
    def get_row_count(self)   -> int:            return self._row_spin.value()
    def get_size_mb(self)     -> float:          return self._size_spin.value()
    def get_symbols(self)     -> List[str]:      return self._symbols_btn.get_items()
    def get_fields(self)      -> List[str]:      return self._fields_btn.get_items()
    def get_tags(self)        -> List[str]:      return self._tags_btn.get_items()
