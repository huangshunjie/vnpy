"""
指数成分股管理对话框

在数据管理 App 中提供 UI，用于：
1. 查看当前已缓存的各指数成分股状态
2. 一键从 TuShare 更新单个/全部指数成分股
3. 查看成分股明细
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from vnpy.trader.ui import QtCore, QtWidgets

from vnpy.trader.index_constituents import (
    SUPPORTED_INDICES,
    get_index_symbols,
    get_index_meta,
    is_index_cached,
    update_index_from_tushare,
    update_all_indices,
    INDEX_STORE_DIR,
)


class IndexConstituentsDialog(QtWidgets.QDialog):
    """指数成分股管理对话框"""

    # 用于子线程通知主线程更新
    _signal_update_done = QtCore.Signal(str, str, bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._refresh_table()
        self._signal_update_done.connect(self._on_update_result)

    def _init_ui(self):
        self.setWindowTitle("指数成分股管理")
        self.setMinimumSize(700, 500)
        self.resize(800, 550)

        layout = QtWidgets.QVBoxLayout(self)

        # ─── 顶部说明 ───
        info_label = QtWidgets.QLabel(
            f"成分股数据存储在: {INDEX_STORE_DIR}\n"
            "点击「更新」按钮从 TuShare 拉取最新成分股数据，"
            "其他 App（行为研究、策略条件等）将共享使用。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #aaa; font-size: 12px; padding: 4px;")
        layout.addWidget(info_label)

        # ─── 指数状态表格 ───
        self._table = QtWidgets.QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "分类", "指数代码", "指数名称", "成分股数", "更新日期", "状态", "操作"
        ])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 80)
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeMode.Fixed)
        header.resizeSection(6, 160)
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table, 1)

        # ─── 底部按钮栏 ───
        btn_layout = QtWidgets.QHBoxLayout()

        self._btn_update_all = QtWidgets.QPushButton("🔄 更新全部成分股")
        self._btn_update_all.setFixedHeight(32)
        self._btn_update_all.clicked.connect(self._on_update_all)
        btn_layout.addWidget(self._btn_update_all)

        self._btn_refresh = QtWidgets.QPushButton("🔃 刷新状态")
        self._btn_refresh.setFixedHeight(32)
        self._btn_refresh.clicked.connect(self._refresh_table)
        btn_layout.addWidget(self._btn_refresh)

        btn_layout.addStretch()

        self._btn_view = QtWidgets.QPushButton("📋 查看成分股")
        self._btn_view.setFixedHeight(32)
        self._btn_view.clicked.connect(self._on_view_detail)
        btn_layout.addWidget(self._btn_view)

        self._btn_close = QtWidgets.QPushButton("关闭")
        self._btn_close.setFixedHeight(32)
        self._btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self._btn_close)

        layout.addLayout(btn_layout)

        # ─── 状态栏 ───
        self._status_label = QtWidgets.QLabel("就绪")
        self._status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._status_label)

    def _refresh_table(self):
        """刷新指数状态表格，按分类排序"""
        # 按分类排序
        _CAT_ORDER = ["规模指数", "板块指数", "风格策略", "行业主题"]
        sorted_items = sorted(
            SUPPORTED_INDICES.items(),
            key=lambda x: (
                _CAT_ORDER.index(x[1].get("category", ""))
                if x[1].get("category", "") in _CAT_ORDER
                else 99
            ),
        )

        self._table.setRowCount(len(sorted_items))
        prev_category = ""

        for row, (code, info) in enumerate(sorted_items):
            category = info.get("category", "其他")

            # 分类列：同分类只显示第一行
            if category != prev_category:
                cat_item = QtWidgets.QTableWidgetItem(category)
                cat_item.setForeground(QtCore.Qt.GlobalColor.cyan)
                font = cat_item.font()
                font.setBold(True)
                cat_item.setFont(font)
                self._table.setItem(row, 0, cat_item)
                prev_category = category
            else:
                self._table.setItem(row, 0, QtWidgets.QTableWidgetItem(""))

            # 指数代码
            self._table.setItem(row, 1, QtWidgets.QTableWidgetItem(code))
            # 指数名称
            self._table.setItem(row, 2, QtWidgets.QTableWidgetItem(info["name"]))

            # 检查缓存状态
            meta = get_index_meta(code)
            if meta:
                count = str(meta.get("count", 0))
                update_date = meta.get("update_date", "")
                status = "✅ 已缓存"
            else:
                count = "-"
                update_date = "-"
                status = "⚠️ 未下载"

            self._table.setItem(row, 3, QtWidgets.QTableWidgetItem(count))
            self._table.setItem(row, 4, QtWidgets.QTableWidgetItem(update_date))

            status_item = QtWidgets.QTableWidgetItem(status)
            if meta:
                status_item.setForeground(QtCore.Qt.GlobalColor.green)
            else:
                status_item.setForeground(QtCore.Qt.GlobalColor.yellow)
            self._table.setItem(row, 5, status_item)

            # 操作按钮
            btn_widget = QtWidgets.QWidget()
            btn_layout = QtWidgets.QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)

            update_btn = QtWidgets.QPushButton("更新")
            update_btn.setFixedWidth(60)
            update_btn.clicked.connect(
                lambda checked, c=code: self._on_update_single(c)
            )
            btn_layout.addWidget(update_btn)

            view_btn = QtWidgets.QPushButton("查看")
            view_btn.setFixedWidth(60)
            view_btn.setEnabled(meta is not None)
            view_btn.clicked.connect(
                lambda checked, c=code: self._show_detail(c)
            )
            btn_layout.addWidget(view_btn)

            self._table.setCellWidget(row, 6, btn_widget)

        self._table.resizeRowsToContents()

    def _on_update_single(self, index_code: str):
        """更新单个指数的成分股"""
        name = SUPPORTED_INDICES[index_code]["name"]
        self._status_label.setText(f"正在更新 {name}...")
        self._btn_update_all.setEnabled(False)
        QtWidgets.QApplication.processEvents()

        # 在主线程直接调用（TuShare 调用通常几秒内完成）
        success, msg = update_index_from_tushare(index_code)
        self._on_update_result(index_code, name, success, msg)
        self._btn_update_all.setEnabled(True)

    def _on_update_all(self):
        """更新全部指数成分股"""
        self._status_label.setText("正在更新全部指数成分股...")
        self._btn_update_all.setEnabled(False)
        QtWidgets.QApplication.processEvents()

        results = []
        for code, info in SUPPORTED_INDICES.items():
            self._status_label.setText(f"正在更新 {info['name']}...")
            QtWidgets.QApplication.processEvents()
            success, msg = update_index_from_tushare(code)
            results.append((code, info["name"], success, msg))

        # 汇总结果
        success_count = sum(1 for _, _, s, _ in results if s)
        fail_count = len(results) - success_count
        self._status_label.setText(
            f"更新完成：成功 {success_count} 个，失败 {fail_count} 个"
        )
        self._btn_update_all.setEnabled(True)
        self._refresh_table()

        # 弹出汇总
        detail_lines = []
        for code, name, success, msg in results:
            icon = "✅" if success else "❌"
            detail_lines.append(f"{icon} {name}({code}): {msg}")

        QtWidgets.QMessageBox.information(
            self,
            "更新结果",
            "\n".join(detail_lines),
        )

    def _on_update_result(self, code: str, name: str, success: bool, msg: str):
        """单个更新完成回调"""
        if success:
            self._status_label.setText(f"✅ {msg}")
        else:
            self._status_label.setText(f"❌ {msg}")
            QtWidgets.QMessageBox.warning(self, "更新失败", msg)
        self._refresh_table()

    def _on_view_detail(self):
        """查看选中行的成分股明细"""
        row = self._table.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.information(self, "提示", "请先选中一个指数")
            return
        item = self._table.item(row, 1)  # 指数代码在第1列
        if not item or not item.text():
            return
        code = item.text()
        self._show_detail(code)

    def _show_detail(self, index_code: str):
        """弹出成分股明细对话框"""
        symbols = get_index_symbols(index_code)
        if not symbols:
            QtWidgets.QMessageBox.information(
                self, "提示", "该指数尚无缓存数据，请先点击「更新」"
            )
            return

        from vnpy.trader.index_constituents import get_index_info
        data = get_index_info(index_code)
        name = SUPPORTED_INDICES.get(index_code, {}).get("name", index_code)

        dlg = _ConstituentDetailDialog(
            index_code=index_code,
            index_name=name,
            data=data,
            parent=self,
        )
        dlg.exec()


class _ConstituentDetailDialog(QtWidgets.QDialog):
    """成分股明细对话框"""

    def __init__(self, index_code: str, index_name: str, data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{index_name}（{index_code}）成分股明细")
        self.setMinimumSize(600, 500)
        self.resize(650, 600)

        layout = QtWidgets.QVBoxLayout(self)

        # 概要信息
        update_date = data.get("update_date", "未知")
        count = data.get("count", 0)
        info = QtWidgets.QLabel(
            f"指数: {index_name}（{index_code}）  |  "
            f"成分股: {count} 只  |  更新日期: {update_date}"
        )
        info.setStyleSheet("font-size: 13px; padding: 6px;")
        layout.addWidget(info)

        # 成分股表格
        constituents = data.get("constituents", [])
        table = QtWidgets.QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["代码", "交易所", "名称", "权重(%)"])
        table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        table.setRowCount(len(constituents))
        table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        table.setAlternatingRowColors(True)
        table.verticalHeader().setDefaultSectionSize(24)

        for row, c in enumerate(constituents):
            table.setItem(row, 0, QtWidgets.QTableWidgetItem(c.get("symbol", "")))
            table.setItem(row, 1, QtWidgets.QTableWidgetItem(c.get("exchange", "")))
            table.setItem(row, 2, QtWidgets.QTableWidgetItem(c.get("name", "")))
            weight = c.get("weight", 0)
            weight_item = QtWidgets.QTableWidgetItem(f"{weight:.4f}" if weight else "-")
            weight_item.setTextAlignment(
                QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
            table.setItem(row, 3, weight_item)

        layout.addWidget(table, 1)

        # 关闭按钮
        btn_close = QtWidgets.QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)