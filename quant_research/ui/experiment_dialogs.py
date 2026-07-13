"""
quant_research/ui/experiment_dialogs.py

ExperimentCreateDialog  — 新建 / 编辑实验对话框
ExperimentCompareDialog — 多实验 metrics 对比对话框
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QHeaderView, QAbstractItemView,
    QComboBox, QScrollArea, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ..constant import ExperimentStatus
from ..model.experiment_model import ExperimentRecord


# ──────────────────────────────────────────────────────────────────────
# TagEditor: 简易标签输入控件
# ──────────────────────────────────────────────────────────────────────

class TagEditor(QWidget):
    """显示已有标签 + 输入新标签的轻量控件。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags: List[str] = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._display = QLineEdit()
        self._display.setReadOnly(True)
        self._display.setPlaceholderText("标签（用逗号分隔）")
        layout.addWidget(self._display)

        self._input = QLineEdit()
        self._input.setPlaceholderText("新标签")
        self._input.setFixedWidth(120)
        layout.addWidget(self._input)

        btn = QPushButton("+ 添加")
        btn.setFixedWidth(64)
        btn.clicked.connect(self._add_tag)
        layout.addWidget(btn)

    def _add_tag(self):
        tag = self._input.text().strip()
        if tag and tag not in self._tags:
            self._tags.append(tag)
            self._refresh()
        self._input.clear()

    def _refresh(self):
        self._display.setText(", ".join(self._tags))

    def set_tags(self, tags: List[str]):
        self._tags = list(tags)
        self._refresh()

    def get_tags(self) -> List[str]:
        return list(self._tags)


# ──────────────────────────────────────────────────────────────────────
# ParamsEditor: 参数 key-value 编辑表格
# ──────────────────────────────────────────────────────────────────────

class ParamsEditor(QWidget):
    """参数字典编辑器（key / value 两列表格）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["参数名", "值"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setMinimumHeight(120)
        layout.addWidget(self._table)

        btn_bar = QHBoxLayout()
        add_btn = QPushButton("+ 添加行")
        del_btn = QPushButton("- 删除行")
        add_btn.clicked.connect(self._add_row)
        del_btn.clicked.connect(self._del_row)
        btn_bar.addWidget(add_btn)
        btn_bar.addWidget(del_btn)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

    def _add_row(self):
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._table.setItem(r, 0, QTableWidgetItem(""))
        self._table.setItem(r, 1, QTableWidgetItem(""))

    def _del_row(self):
        rows = {idx.row() for idx in self._table.selectedIndexes()}
        for r in sorted(rows, reverse=True):
            self._table.removeRow(r)

    def set_params(self, params: Dict[str, Any]):
        self._table.setRowCount(0)
        for k, v in params.items():
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(str(k)))
            self._table.setItem(r, 1, QTableWidgetItem(str(v)))

    def get_params(self) -> Dict[str, Any]:
        result = {}
        for r in range(self._table.rowCount()):
            k_item = self._table.item(r, 0)
            v_item = self._table.item(r, 1)
            if k_item and k_item.text().strip():
                key = k_item.text().strip()
                raw = v_item.text().strip() if v_item else ""
                try:
                    result[key] = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    result[key] = raw
        return result


# ──────────────────────────────────────────────────────────────────────
# ExperimentCreateDialog
# ──────────────────────────────────────────────────────────────────────

class ExperimentCreateDialog(QDialog):
    """新建 / 编辑实验对话框。"""

    def __init__(
        self,
        parent=None,
        record: Optional[ExperimentRecord] = None,
    ):
        super().__init__(parent)
        self._record = record
        self._editing = record is not None
        self.setWindowTitle("编辑实验" if self._editing else "新建实验")
        self.setMinimumWidth(560)
        self._init_ui()
        if self._editing:
            self._load_record()

    def _init_ui(self):
        root = QVBoxLayout(self)

        # ── 基本信息 ──────────────────────────────────────────────────
        info_group = QGroupBox("基本信息")
        form = QFormLayout(info_group)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("实验名称（必填）")
        form.addRow("名称 *", self._name_edit)

        self._desc_edit = QPlainTextEdit()
        self._desc_edit.setPlaceholderText("实验描述")
        self._desc_edit.setFixedHeight(72)
        form.addRow("描述", self._desc_edit)

        self._status_combo = QComboBox()
        for s in ExperimentStatus:
            self._status_combo.addItem(s.value, s)
        form.addRow("状态", self._status_combo)

        self._author_edit = QLineEdit()
        self._author_edit.setPlaceholderText("创建人")
        form.addRow("创建人", self._author_edit)

        self._parent_edit = QLineEdit()
        self._parent_edit.setPlaceholderText("可选，父实验 ID")
        form.addRow("父实验 ID", self._parent_edit)

        root.addWidget(info_group)

        # ── 标签 ──────────────────────────────────────────────────────
        tag_group = QGroupBox("标签")
        tag_layout = QVBoxLayout(tag_group)
        self._tag_editor = TagEditor()
        tag_layout.addWidget(self._tag_editor)
        root.addWidget(tag_group)

        # ── 参数 ──────────────────────────────────────────────────────
        param_group = QGroupBox("超参数")
        param_layout = QVBoxLayout(param_group)
        self._params_editor = ParamsEditor()
        param_layout.addWidget(self._params_editor)
        root.addWidget(param_group)

        # ── 备注 ──────────────────────────────────────────────────────
        note_group = QGroupBox("备注")
        note_layout = QVBoxLayout(note_group)
        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setPlaceholderText("实验备注（支持 Markdown）")
        self._notes_edit.setFixedHeight(80)
        note_layout.addWidget(self._notes_edit)
        root.addWidget(note_group)

        # ── 按钮 ──────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Ok).setText("确认")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_record(self):
        r = self._record
        self._name_edit.setText(r.name)
        self._desc_edit.setPlainText(r.description)
        idx = self._status_combo.findData(r.status)
        if idx >= 0:
            self._status_combo.setCurrentIndex(idx)
        self._author_edit.setText(r.created_by)
        self._parent_edit.setText(r.parent_id or "")
        self._tag_editor.set_tags(r.tags)
        self._params_editor.set_params(r.params)
        self._notes_edit.setPlainText(r.notes)

    def _on_accept(self):
        if not self._name_edit.text().strip():
            self._name_edit.setFocus()
            self._name_edit.setPlaceholderText("⚠ 名称不能为空")
            return
        self.accept()

    # ── 数据读取接口 ──────────────────────────────────────────────────

    def get_name(self) -> str:
        return self._name_edit.text().strip()

    def get_description(self) -> str:
        return self._desc_edit.toPlainText().strip()

    def get_status(self) -> ExperimentStatus:
        return self._status_combo.currentData()

    def get_author(self) -> str:
        return self._author_edit.text().strip()

    def get_parent_id(self) -> Optional[str]:
        v = self._parent_edit.text().strip()
        return v if v else None

    def get_tags(self) -> List[str]:
        return self._tag_editor.get_tags()

    def get_params(self) -> Dict[str, Any]:
        return self._params_editor.get_params()

    def get_notes(self) -> str:
        return self._notes_edit.toPlainText().strip()


class ExperimentCompareDialog(QDialog):
    """多实验 metrics / params 横向对比对话框。"""

    def __init__(self, records: list, parent=None):
        super().__init__(parent)
        self._records = records
        self.setWindowTitle(f'实验对比（{len(records)} 个）')
        self.resize(900, 560)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)

        ids = '  |  '.join(r.experiment_id for r in self._records)
        header = QLabel(f'对比实验：{ids}')
        header.setWordWrap(True)
        root.addWidget(header)

        from PySide6.QtWidgets import QTabWidget
        tabs = QTabWidget()

        metrics_tab = QWidget()
        mv = QVBoxLayout(metrics_tab)
        mv.addWidget(self._build_compare_table('metrics'))
        tabs.addTab(metrics_tab, 'Metrics 指标')

        params_tab = QWidget()
        pv = QVBoxLayout(params_tab)
        pv.addWidget(self._build_compare_table('params'))
        tabs.addTab(params_tab, 'Params 参数')

        info_tab = QWidget()
        iv = QVBoxLayout(info_tab)
        iv.addWidget(self._build_info_table())
        tabs.addTab(info_tab, '基本信息')

        root.addWidget(tabs)

        btn = QPushButton('关闭')
        btn.clicked.connect(self.accept)
        root.addWidget(btn)

    def _build_compare_table(self, field: str) -> QTableWidget:
        all_keys: list = []
        for r in self._records:
            d = getattr(r, field, {})
            for k in d:
                if k not in all_keys:
                    all_keys.append(k)

        n_cols = 1 + len(self._records)
        table = QTableWidget(len(all_keys), n_cols)
        headers = ['指标'] + [r.experiment_id for r in self._records]
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)

        for row, key in enumerate(all_keys):
            table.setItem(row, 0, QTableWidgetItem(key))
            values = []
            for col, record in enumerate(self._records):
                d = getattr(record, field, {})
                raw = d.get(key, '—')
                if isinstance(raw, float):
                    text = f'{raw:.6f}'
                else:
                    text = str(raw)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, col + 1, item)
                values.append(raw)

            num_vals = [v for v in values if isinstance(v, (int, float))]
            if len(num_vals) >= 2:
                best  = max(num_vals)
                worst = min(num_vals)
                for col, record in enumerate(self._records):
                    d = getattr(record, field, {})
                    v = d.get(key)
                    item = table.item(row, col + 1)
                    if item and isinstance(v, (int, float)):
                        if v == best:
                            item.setBackground(QColor('#d4edda'))
                        elif v == worst:
                            item.setBackground(QColor('#f8d7da'))

        return table

    def _build_info_table(self) -> QTableWidget:
        fields = [
            ('ID',      'experiment_id'),
            ('名称',    'name'),
            ('状态',    'status'),
            ('标签',    'tags'),
            ('创建人',  'created_by'),
            ('创建时间','created_at'),
        ]
        n_cols = 1 + len(self._records)
        table = QTableWidget(len(fields), n_cols)
        table.setHorizontalHeaderLabels(
            ['字段'] + [r.experiment_id for r in self._records])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)

        for row, (label, attr) in enumerate(fields):
            table.setItem(row, 0, QTableWidgetItem(label))
            for col, record in enumerate(self._records):
                val = getattr(record, attr, '—')
                if hasattr(val, 'value'):
                    val = val.value
                elif isinstance(val, list):
                    val = ', '.join(str(x) for x in val)
                elif hasattr(val, 'isoformat'):
                    val = val.strftime('%Y-%m-%d %H:%M')
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, col + 1, item)

        return table
