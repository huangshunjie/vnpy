"""
ui/stock_pool_dialog.py

StockPoolDialog -- stock pool management window (Phase 8 UI refresh).

New in Phase 8:
  - Search/filter bar at top of pool list
  - Per-item symbol count badge
  - Recent-pools tracking (top 3, pinned at list top)
  - Right-click context menu
  - Empty-state placeholder (first launch / search no-result)
  - Import preview via import_from_file_with_preview()
"""
from __future__ import annotations

import json
from pathlib import Path as _Path

from vnpy.trader.ui import QtCore, QtGui, QtWidgets

from ..manager.stock_pool_manager import StockPoolManager
from ..model.stock_pool_model import StockPoolModel
from .stock_pool_editor import StockPoolEditor

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------
_STYLE_LIST = """
QListWidget {
    background-color: #1A1A2E;
    color: #FFFFFF;
    font-size: 13px;
    border: 1px solid #3A3A3A;
    outline: none;
}
QListWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #2A2A3E;
}
QListWidget::item:selected {
    background-color: #2A5298;
    color: #FFFFFF;
}
QListWidget::item:hover { background-color: #1E3A5F; }
"""

_STYLE_SEARCH = (
    "QLineEdit { background:#12122A; color:#FFF; border:1px solid #3A3A3A;"
    " border-radius:3px; padding:4px 8px; font-size:12px; }"
    "QLineEdit:focus { border:1px solid #2A5298; }"
)

_STYLE_INFO = """
QLabel#info_name  { font-size: 15px; font-weight: bold; color: #FFFFFF; }
QLabel#info_count { font-size: 13px; color: #4FC3F7; }
QLabel#info_desc  { font-size: 12px; color: #AAAAAA; }
QLabel#info_time  { font-size: 11px; color: #888888; }
"""

_STYLE_BTN_PRIMARY = (
    "QPushButton { background:#1565C0; color:#fff; border:none;"
    " padding:5px 14px; border-radius:3px; }"
    "QPushButton:hover { background:#1976D2; }"
    "QPushButton:pressed { background:#0D47A1; }"
)
_STYLE_BTN_DANGER = (
    "QPushButton { background:#B71C1C; color:#fff; border:none;"
    " padding:5px 14px; border-radius:3px; }"
    "QPushButton:hover { background:#C62828; }"
    "QPushButton:pressed { background:#7F0000; }"
)

_RECENT_MAX   = 3     # max recently-used pools to remember
_RECENT_KEY   = "recent_pool_names"
_RECENT_PATH  = _Path.home() / ".vnpy" / "batch_research_recent.json"


# ---------------------------------------------------------------------------
# _RecentPools  — lightweight recent-list helper
# ---------------------------------------------------------------------------
class _RecentPools:
    """Persist and manage a short list of recently selected pool names."""

    def __init__(self, max_len: int = _RECENT_MAX) -> None:
        self._max   = max_len
        self._names: list[str] = []
        self._load()

    def push(self, name: str) -> None:
        """Record *name* as most-recently used."""
        if name in self._names:
            self._names.remove(name)
        self._names.insert(0, name)
        self._names = self._names[: self._max]
        self._save()

    def names(self) -> list[str]:
        """Return recent names, most-recent first."""
        return list(self._names)

    def prune(self, existing: set[str]) -> None:
        """Remove names that no longer exist in *existing*."""
        self._names = [n for n in self._names if n in existing]

    def _load(self) -> None:
        try:
            if _RECENT_PATH.exists():
                data = json.loads(_RECENT_PATH.read_text(encoding="utf-8"))
                self._names = data.get(_RECENT_KEY, [])[: self._max]
        except Exception:
            self._names = []

    def _save(self) -> None:
        try:
            _RECENT_PATH.parent.mkdir(parents=True, exist_ok=True)
            _RECENT_PATH.write_text(
                json.dumps({_RECENT_KEY: self._names}, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# _PoolListItem  — QListWidgetItem with embedded count badge
# ---------------------------------------------------------------------------
class _PoolListItem(QtWidgets.QListWidgetItem):
    """List item that stores pool name and displays a count badge."""

    _BADGE_STYLE = "color:#4FC3F7; font-size:11px;"

    def __init__(
        self,
        name: str,
        count: int,
        is_recent: bool = False,
    ) -> None:
        badge = f"  [{count}]"
        super().__init__(name + badge)
        self._pool_name = name
        self.setToolTip(f"{name}  ({count} 只股票)")
        if is_recent:
            self.setForeground(QtGui.QColor("#FFD54F"))

    @property
    def pool_name(self) -> str:
        return self._pool_name


# ---------------------------------------------------------------------------
# _PoolInfoPanel
# ---------------------------------------------------------------------------
class _PoolInfoPanel(QtWidgets.QWidget):
    """右侧信息面板：显示选中股票池的名称、数量、描述、更新时间。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(_STYLE_INFO)

        self._lbl_name  = QtWidgets.QLabel("—")
        self._lbl_name.setObjectName("info_name")
        self._lbl_count = QtWidgets.QLabel("")
        self._lbl_count.setObjectName("info_count")

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet("color: #3A3A3A;")

        lbl_desc_title = QtWidgets.QLabel("描述：")
        lbl_desc_title.setStyleSheet("color:#888; font-size:11px;")
        self._lbl_desc  = QtWidgets.QLabel("—")
        self._lbl_desc.setObjectName("info_desc")
        self._lbl_desc.setWordWrap(True)

        lbl_time_title = QtWidgets.QLabel("更新时间：")
        lbl_time_title.setStyleSheet("color:#888; font-size:11px;")
        self._lbl_time  = QtWidgets.QLabel("—")
        self._lbl_time.setObjectName("info_time")

        form = QtWidgets.QFormLayout()
        form.setVerticalSpacing(8)
        form.setContentsMargins(12, 12, 12, 12)
        form.addRow(self._lbl_name)
        form.addRow(self._lbl_count)
        form.addRow(sep)
        form.addRow(lbl_desc_title, self._lbl_desc)
        form.addRow(lbl_time_title, self._lbl_time)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addLayout(form)
        vbox.addStretch()

    def update(self, pool: StockPoolModel | None) -> None:
        if pool is None:
            self._lbl_name.setText("—")
            self._lbl_count.setText("")
            self._lbl_desc.setText("—")
            self._lbl_time.setText("—")
        else:
            self._lbl_name.setText(pool.name)
            self._lbl_count.setText(f"共 {pool.count} 只股票")
            self._lbl_desc.setText(pool.description or "无描述")
            self._lbl_time.setText(pool.update_time)

class StockPoolDialog(QtWidgets.QDialog):
    """股票池管理窗口（第八阶段 UI 升级）。"""

    def __init__(
        self,
        manager: StockPoolManager,
        initial_name: str = "",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._manager        = manager
        self._selected_name  = ""
        self._recent         = _RecentPools()
        self.setWindowTitle("股票池管理")
        self.setMinimumSize(800, 540)
        self._init_ui()
        self._refresh_list(select_name=initial_name or "")

    # ---- public API ----------------------------------------

    def get_selected_symbols(self) -> list[str]:
        return self._manager.get_symbols(self._selected_name)

    def get_selected_name(self) -> str:
        return self._selected_name

    # ---- UI construction -----------------------------------

    def _init_ui(self) -> None:
        # ---- search bar ----
        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("搜索股票池名称...")
        self._search.setStyleSheet(_STYLE_SEARCH)
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_search_changed)

        # ---- pool list ----
        self._list = QtWidgets.QListWidget()
        self._list.setStyleSheet(_STYLE_LIST)
        self._list.setMinimumWidth(220)
        self._list.currentRowChanged.connect(self._on_selection_changed)
        self._list.doubleClicked.connect(self._on_edit)
        self._list.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._list.customContextMenuRequested.connect(self._on_context_menu)

        # ---- empty-state label ----
        empty_lbl = QtWidgets.QLabel()
        empty_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        empty_lbl.setStyleSheet("color:#555; font-size:13px;")
        empty_lbl.setWordWrap(True)
        self._empty_lbl = empty_lbl

        # ---- stacked: list vs empty placeholder ----
        self._stack = QtWidgets.QStackedWidget()
        self._stack.addWidget(self._list)     # index 0 = list
        self._stack.addWidget(empty_lbl)      # index 1 = empty state

        list_label = QtWidgets.QLabel("股票池列表")
        list_label.setStyleSheet("color:#AAAAAA; font-size:11px;")

        left_vbox = QtWidgets.QVBoxLayout()
        left_vbox.setContentsMargins(0, 0, 0, 0)
        left_vbox.setSpacing(4)
        left_vbox.addWidget(list_label)
        left_vbox.addWidget(self._search)
        left_vbox.addWidget(self._stack, 1)

        left_w = QtWidgets.QWidget()
        left_w.setLayout(left_vbox)

        # ---- right: info panel + toolbar ----
        self._info = _PoolInfoPanel()
        self._info.setMinimumWidth(280)

        toolbar_box = self._init_toolbar()

        right_vbox = QtWidgets.QVBoxLayout()
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.setSpacing(8)
        right_vbox.addWidget(self._info, 1)
        right_vbox.addLayout(toolbar_box)

        right_w = QtWidgets.QWidget()
        right_w.setLayout(right_vbox)

        # ---- splitter ----
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(left_w)
        splitter.addWidget(right_w)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setHandleWidth(6)

        # ---- dialog buttons ----
        self._btn_ok = QtWidgets.QPushButton("确定")
        self._btn_ok.setStyleSheet(_STYLE_BTN_PRIMARY)
        self._btn_ok.setEnabled(False)
        self._btn_ok.clicked.connect(self._on_accept)

        btn_cancel = QtWidgets.QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._btn_ok)
        btn_row.addWidget(btn_cancel)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)
        root.addWidget(splitter, 1)
        root.addLayout(btn_row)
    def _init_toolbar(self) -> QtWidgets.QVBoxLayout:
        btn_cfg = [
            ("新建",     self._on_new,        False),
            ("编辑",     self._on_edit,       True),
            ("复制",     self._on_copy,       True),
            ("删除",     self._on_delete,     True),
            None,
            ("导入 CSV", self._on_import_csv, False),
            ("导出 CSV", self._on_export_csv, True),
        ]
        self._need_selection_btns: list[QtWidgets.QPushButton] = []
        vbox = QtWidgets.QVBoxLayout()
        vbox.setSpacing(4)
        for item in btn_cfg:
            if item is None:
                sep = QtWidgets.QFrame()
                sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
                sep.setStyleSheet("color:#3A3A3A;")
                vbox.addWidget(sep)
                continue
            label, slot, needs_sel = item
            btn = QtWidgets.QPushButton(label)
            if label == "删除":
                btn.setStyleSheet(_STYLE_BTN_DANGER)
            btn.clicked.connect(slot)
            btn.setEnabled(not needs_sel)
            if needs_sel:
                self._need_selection_btns.append(btn)
            vbox.addWidget(btn)
        return vbox

    # ---- list management -----------------------------------

    def _refresh_list(self, select_name: str = "") -> None:
        """Reload pool list; recent pools appear first in gold, rest sorted."""
        self._list.blockSignals(True)
        self._list.clear()

        all_names  = self._manager.list_pools()
        name_set   = set(all_names)
        self._recent.prune(name_set)
        recent_set = set(self._recent.names())

        # recent first (in recency order), then remainder alphabetically
        ordered = self._recent.names() + [
            n for n in all_names if n not in recent_set
        ]

        query = self._search.text().strip().lower() if hasattr(self, "_search") else ""
        visible = [n for n in ordered if query in n.lower()] if query else ordered

        for name in visible:
            pool  = self._manager.get_pool(name)
            count = pool.count if pool else 0
            item  = _PoolListItem(name, count, is_recent=(name in recent_set))
            self._list.addItem(item)

        self._list.blockSignals(False)

        # update empty-state visibility
        self._update_empty_state(visible, query)

        # restore selection
        target = select_name or self._selected_name
        self._select_by_name(target or (visible[0] if visible else ""))

    def _update_empty_state(self, visible: list[str], query: str) -> None:
        """Switch stack to list or empty-state placeholder."""
        if visible:
            self._stack.setCurrentIndex(0)
        else:
            if query:
                self._empty_lbl.setText(
                    f"搜索 「{query}」 无结果。\n请尝试其他关键字。"
                )
            else:
                self._empty_lbl.setText(
                    "还没有股票池。\n点击「新建」或「导入 CSV」开始。"
                )
            self._stack.setCurrentIndex(1)

    def _select_by_name(self, name: str) -> None:
        """Select the list item whose pool_name matches *name*."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            if isinstance(item, _PoolListItem) and item.pool_name == name:
                self._list.setCurrentRow(i)
                return
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
        else:
            self._on_selection_changed(-1)

    def _on_search_changed(self, _text: str) -> None:
        """Re-filter list whenever the search box changes."""
        self._refresh_list()

    def _on_selection_changed(self, row: int) -> None:
        if row < 0:
            self._selected_name = ""
            self._info.update(None)
            self._btn_ok.setEnabled(False)
            for btn in self._need_selection_btns:
                btn.setEnabled(False)
            return
        item = self._list.item(row)
        if not isinstance(item, _PoolListItem):
            return
        self._selected_name = item.pool_name
        pool = self._manager.get_pool(self._selected_name)
        self._info.update(pool)
        self._btn_ok.setEnabled(True)
        for btn in self._need_selection_btns:
            btn.setEnabled(True)
    # ---- slots --------------------------------------------

    def _on_new(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(
            self, "新建股票池", "请输入股票池名称："
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        if self._manager.exists(name):
            QtWidgets.QMessageBox.warning(
                self, "名称已存在", f"股票池 '{name}' 已存在，请更换名称。"
            )
            return
        syms = self._run_editor(StockPoolModel(name=name))
        if syms is None:
            return
        try:
            self._manager.create_pool(name, syms)
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "创建失败", str(e))
            return
        self._refresh_list(select_name=name)

    def _on_edit(self) -> None:
        if not self._selected_name:
            return
        pool = self._manager.get_pool(self._selected_name)
        if pool is None:
            return
        syms = self._run_editor(pool)
        if syms is None:
            return
        self._manager.update_symbols(self._selected_name, syms)
        self._refresh_list(select_name=self._selected_name)

    def _on_copy(self) -> None:
        if not self._selected_name:
            return
        default = f"{self._selected_name}_副本"
        name, ok = QtWidgets.QInputDialog.getText(
            self, "复制股票池", "请输入新名称：", text=default,
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        if self._manager.exists(name):
            QtWidgets.QMessageBox.warning(
                self, "名称已存在", f"股票池 '{name}' 已存在。"
            )
            return
        try:
            self._manager.copy_pool(self._selected_name, name)
        except (KeyError, ValueError) as e:
            QtWidgets.QMessageBox.warning(self, "复制失败", str(e))
            return
        self._refresh_list(select_name=name)

    def _on_delete(self) -> None:
        if not self._selected_name:
            return
        pool = self._manager.get_pool(self._selected_name)
        n    = pool.count if pool else 0
        reply = QtWidgets.QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除股票池 '{self._selected_name}'（{n} 只股票）？\n\n此操作不可恢复。",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self._manager.delete_pool(self._selected_name)
        self._selected_name = ""
        self._refresh_list()

    def _on_context_menu(self, pos: QtCore.QPoint) -> None:
        """Show right-click context menu on the pool list."""
        item = self._list.itemAt(pos)
        has_sel = isinstance(item, _PoolListItem)

        menu = QtWidgets.QMenu(self)
        act_new    = menu.addAction("新建...")
        act_edit   = menu.addAction("编辑...")
        act_copy   = menu.addAction("复制...")
        menu.addSeparator()
        act_delete = menu.addAction("删除")
        menu.addSeparator()
        act_import = menu.addAction("导入 CSV...")
        act_export = menu.addAction("导出 CSV...")

        act_edit.setEnabled(has_sel)
        act_copy.setEnabled(has_sel)
        act_delete.setEnabled(has_sel)
        act_export.setEnabled(has_sel)

        act_new.triggered.connect(self._on_new)
        act_edit.triggered.connect(self._on_edit)
        act_copy.triggered.connect(self._on_copy)
        act_delete.triggered.connect(self._on_delete)
        act_import.triggered.connect(self._on_import_csv)
        act_export.triggered.connect(self._on_export_csv)

        menu.exec(self._list.mapToGlobal(pos))

    def _on_import_csv(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "导入股票池", "",
            "CSV / TXT 文件 (*.csv *.txt);;All Files (*)",
        )
        if not path:
            return
        default_name = _Path(path).stem
        name, ok = QtWidgets.QInputDialog.getText(
            self, "导入股票池", "请输入股票池名称：", text=default_name,
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        overwrite = False
        if self._manager.exists(name):
            reply = QtWidgets.QMessageBox.question(
                self, "名称已存在",
                f"股票池 '{name}' 已存在，是否覆盖？",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if reply != QtWidgets.QMessageBox.StandardButton.Yes:
                return
            overwrite = True
        try:
            ir = self._manager.import_from_file_with_preview(
                name, _Path(path), overwrite=overwrite
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "导入失败", str(e))
            return
        action = "覆盖" if ir.overwritten else "导入"
        detail = ir.parse_result.summary()
        QtWidgets.QMessageBox.information(
            self, f"{action}成功",
            f"已{action}到「{name}」。\n{detail}",
        )
        self._refresh_list(select_name=name)

    def _on_export_csv(self) -> None:
        if not self._selected_name:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出股票池",
            f"{self._selected_name}.csv",
            "CSV 文件 (*.csv);;TXT 文件 (*.txt)",
        )
        if not path:
            return
        try:
            n = self._manager.export_to_file(self._selected_name, _Path(path))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "导出失败", str(e))
            return
        QtWidgets.QMessageBox.information(
            self, "导出成功", f"已导出 {n} 只股票到：{path}",
        )

    def _run_editor(self, pool: StockPoolModel) -> list[str] | None:
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(f"编辑股票池——{pool.name}")
        dlg.setMinimumSize(560, 480)
        editor = StockPoolEditor(dlg)
        editor.set_symbols(list(pool.symbols))
        btn_ok     = QtWidgets.QPushButton("确定")
        btn_ok.setStyleSheet(_STYLE_BTN_PRIMARY)
        btn_cancel = QtWidgets.QPushButton("取消")
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        vbox = QtWidgets.QVBoxLayout(dlg)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(8)
        vbox.addWidget(editor, 1)
        vbox.addLayout(btn_row)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return None
        return editor.get_symbols()

    def _on_accept(self) -> None:
        if not self._selected_name:
            return
        self._recent.push(self._selected_name)
        self._manager.set_current(self._selected_name)
        self.accept()
