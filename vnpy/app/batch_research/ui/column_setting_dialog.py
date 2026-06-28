"""
ui/column_setting_dialog.py

ColumnSettingDialog  —  列设置对话框

功能：
  - 左侧：分组树形列表，勾选/取消勾选列的可见性
  - 右侧：搜索框 + 当前可见列预览（按顺序）
  - 支持拖拽调整列顺序
  - 底部：全部显示 / 恢复默认 / 确认 / 取消

设计约定：
  - 不直接修改 ColumnManager，只在确认时一次性写入
  - 取消时撤销所有临时更改
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vnpy.trader.ui import QtCore, QtWidgets

if TYPE_CHECKING:
    from ..column_manager import ColumnManager
    from ..column_definition import ColumnDefinition

_GROUP_LABELS: dict[str, str] = {
    "basic":   "基本信息",
    "return":  "收益指标",
    "risk":    "风险指标",
    "trade":   "交易指标",
    "capital": "资金/成本",
    "factor":  "因子分析",
}


class ColumnSettingDialog(QtWidgets.QDialog):
    """
    列设置对话框。

    从 ColumnManager 读取当前状态；
    用户确认后将变更写回 ColumnManager 并持久化。

    用法::

        dlg = ColumnSettingDialog(column_manager, parent=widget)
        if dlg.exec() == QDialog.Accepted:
            pass  # ColumnManager 已更新
    """

    def __init__(
        self,
        column_manager: "ColumnManager",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("列设置")
        self.setMinimumSize(620, 480)
        self.resize(700, 520)

        self._cm = column_manager
        # 临时状态：{key: visible}，对话框内的草稿
        self._draft: dict[str, bool] = {
            s.key: s.visible
            for s in column_manager._states
            if s.definition.group != "meta" and not s.definition.pinned
        }

        self._init_ui()
        self._populate_tree()
        self._refresh_preview()

    # ── UI 构建 ────────────────────────────────── #

    def _init_ui(self) -> None:
        # 左：分组树
        left = QtWidgets.QWidget()
        left.setFixedWidth(280)
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        search_label = QtWidgets.QLabel("搜索列：")
        self._search_edit = QtWidgets.QLineEdit()
        self._search_edit.setPlaceholderText("输入列名搜索…")
        self._search_edit.textChanged.connect(self._on_search)

        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderLabel("列（勾选=显示）")
        self._tree.setRootIsDecorated(True)
        self._tree.itemChanged.connect(self._on_item_changed)

        left_layout.addWidget(search_label)
        left_layout.addWidget(self._search_edit)
        left_layout.addWidget(self._tree)

        # 右：当前可见列预览
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        right_layout.addWidget(QtWidgets.QLabel("当前可见列（按顺序）："))
        self._preview_list = QtWidgets.QListWidget()
        self._preview_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self._preview_list.setDragDropMode(
            QtWidgets.QAbstractItemView.DragDropMode.InternalMove
        )
        self._preview_list.setToolTip("可拖拽调整列顺序")
        right_layout.addWidget(self._preview_list)

        # 底部按钮
        btn_show_all = QtWidgets.QPushButton("全部显示")
        btn_show_all.clicked.connect(self._on_show_all)
        btn_reset = QtWidgets.QPushButton("恢复默认")
        btn_reset.clicked.connect(self._on_reset)
        btn_ok = QtWidgets.QPushButton("确认")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._on_accept)
        btn_cancel = QtWidgets.QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(btn_show_all)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(splitter)
        main_layout.addLayout(btn_row)

    # ── 数据填充 ──────────────────────────────── #

    def _populate_tree(self, filter_text: str = "") -> None:
        self._tree.blockSignals(True)
        self._tree.clear()

        groups: dict[str, QtWidgets.QTreeWidgetItem] = {}
        all_cols = self._cm.get_all_columns()

        for col in all_cols:
            if col.pinned or col.group == "meta":
                continue

            label = col.cn_header or col.header
            if filter_text and filter_text.lower() not in label.lower():
                continue

            group_key = col.group
            if group_key not in groups:
                group_item = QtWidgets.QTreeWidgetItem(self._tree)
                group_item.setText(0, _GROUP_LABELS.get(group_key, group_key))
                group_item.setFlags(
                    group_item.flags()
                    | QtCore.Qt.ItemFlag.ItemIsAutoTristate
                    | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                )
                groups[group_key] = group_item

            item = QtWidgets.QTreeWidgetItem(groups[group_key])
            item.setText(0, label)
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, col.key)
            item.setToolTip(0, col.tooltip or label)
            checked = self._draft.get(col.key, col.default_visible)
            item.setCheckState(
                0,
                QtCore.Qt.CheckState.Checked
                if checked
                else QtCore.Qt.CheckState.Unchecked,
            )
            item.setFlags(
                item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable
            )

        self._tree.expandAll()
        self._tree.blockSignals(False)

    def _refresh_preview(self) -> None:
        self._preview_list.blockSignals(True)
        self._preview_list.clear()

        # 固定列
        for s in self._cm._states:
            if s.definition.pinned and s.definition.group != "meta":
                item = QtWidgets.QListWidgetItem(
                    f"[固定] {s.definition.cn_header or s.definition.header}"
                )
                item.setData(QtCore.Qt.ItemDataRole.UserRole, s.key)
                item.setForeground(QtCore.Qt.GlobalColor.gray)
                self._preview_list.addItem(item)

        # 可见列（按当前 order 排序）
        for s in self._cm._states:
            if s.definition.pinned or s.definition.group == "meta":
                continue
            if self._draft.get(s.key, False):
                label = s.definition.cn_header or s.definition.header
                item = QtWidgets.QListWidgetItem(label)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, s.key)
                self._preview_list.addItem(item)

        self._preview_list.blockSignals(False)

    # ── 事件处理 ──────────────────────────────── #

    def _on_item_changed(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        key = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not key:
            return
        self._draft[key] = (
            item.checkState(0) == QtCore.Qt.CheckState.Checked
        )
        self._refresh_preview()

    def _on_search(self, text: str) -> None:
        self._populate_tree(filter_text=text.strip())

    def _on_show_all(self) -> None:
        for key in self._draft:
            self._draft[key] = True
        self._populate_tree(filter_text=self._search_edit.text().strip())
        self._refresh_preview()

    def _on_reset(self) -> None:
        for s in self._cm._states:
            if not s.definition.pinned and s.definition.group != "meta":
                self._draft[s.key] = s.definition.default_visible
        self._populate_tree(filter_text=self._search_edit.text().strip())
        self._refresh_preview()

    def _on_accept(self) -> None:
        # 1. 写入可见性
        for key, visible in self._draft.items():
            self._cm.set_visible(key, visible)

        # 2. 写入顺序（从预览列表读取）
        ordered_keys: list[str] = []
        for i in range(self._preview_list.count()):
            item = self._preview_list.item(i)
            key = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if key:
                ordered_keys.append(key)

        if ordered_keys:
            # 把所有未在 preview 中的 key 追加到末尾
            all_keys = [s.key for s in self._cm._states]
            remaining = [k for k in all_keys if k not in ordered_keys]
            self._cm.reorder(ordered_keys + remaining)

        # 3. 持久化
        self._cm.save()
        self.accept()
