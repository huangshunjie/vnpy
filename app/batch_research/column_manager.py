"""
column_manager.py

ColumnManager  —  运行时列状态管理器

职责：
- 维护每列的 visible / width / order（运行时可变状态）
- 提供表格列构建接口（get_visible_columns / get_export_columns）
- 持久化到 ~/.vnpy/batch_research_columns.json
- 构建表头右键菜单（build_header_menu）
- 支持变更通知回调

设计约定：
- 不依赖 Qt（build_header_menu 除外，延迟导入）
- ColumnDefinition 是不可变的，_ColumnState 持有可变状态
- pinned=True 的列不可隐藏，始终出现在可见列列表
- group="meta" 的列不在 UI 显示，export_always=True 时写入导出文件
- 持久化格式：{key: {visible, width, order}}，未持久化的列使用 COLUMN_REGISTRY 默认值
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from .column_definition import ColumnDefinition
from .column_registry import COLUMN_REGISTRY

if TYPE_CHECKING:
    pass

# 持久化文件路径
_SETTINGS_PATH = Path.home() / ".vnpy" / "batch_research_columns.json"


@dataclass
class _ColumnState:
    """单列的运行时可变状态。"""
    definition: ColumnDefinition
    visible:    bool
    width:      int
    order:      int

    @property
    def key(self) -> str:
        return self.definition.key


class ColumnManager:
    """
    运行时列状态管理器。

    用法::

        cm = ColumnManager()
        visible_cols = cm.get_visible_columns()    # 供表格使用
        export_cols  = cm.get_export_columns("all") # 供导出使用

        # 监听变更（表格调用此回调刷新列头）
        cm.register_on_change(table.rebuild_header)

        # 修改列状态
        cm.set_visible("calmar_ratio", True)
        cm.set_width("sharpe_ratio", 100)
    """

    def __init__(self) -> None:
        self._states: list[_ColumnState] = []
        self._callbacks: list[Callable[[], None]] = []
        self._init_states()
        self._load()

    # ── 初始化 ──────────────────────────────────── #

    def _init_states(self) -> None:
        """按 COLUMN_REGISTRY 顺序初始化所有列状态（默认值）。"""
        self._states = [
            _ColumnState(
                definition=col,
                visible=col.default_visible and col.group != "meta",
                width=col.width,
                order=i,
            )
            for i, col in enumerate(COLUMN_REGISTRY)
        ]

    # ── 持久化 ──────────────────────────────────── #

    def _load(self) -> None:
        """从持久化文件加载用户配置，覆盖默认值。"""
        if not _SETTINGS_PATH.exists():
            return
        try:
            data: dict = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return

        state_map = {s.key: s for s in self._states}
        for key, saved in data.items():
            if key not in state_map:
                continue
            st = state_map[key]
            # pinned 列不允许被持久化数据强制隐藏
            if not st.definition.pinned:
                st.visible = bool(saved.get("visible", st.visible))
            st.width = int(saved.get("width", st.width))
            st.order = int(saved.get("order", st.order))

        # 按持久化的 order 重排
        self._states.sort(key=lambda s: s.order)
        # 修正 order 为连续整数，防止持久化数据中有空洞
        for i, s in enumerate(self._states):
            s.order = i

    def save(self) -> None:
        """把当前列状态持久化到文件。"""
        _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            s.key: {
                "visible": s.visible,
                "width":   s.width,
                "order":   s.order,
            }
            for s in self._states
        }
        _SETTINGS_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── 列查询 ──────────────────────────────────── #

    def get_visible_columns(self) -> list[ColumnDefinition]:
        """
        返回当前 UI 可见列列表（含 pinned 列），按 order 排序。

        group="meta" 的列始终排除。
        """
        return [
            s.definition
            for s in self._states
            if (s.visible or s.definition.pinned)
            and s.definition.group != "meta"
        ]

    def get_all_columns(self) -> list[ColumnDefinition]:
        """返回全部已注册列（含隐藏列，不含 meta 组），按 order 排序。"""
        return [
            s.definition
            for s in self._states
            if s.definition.group != "meta"
        ]

    def get_export_columns(self, scope: str = "all") -> list[ColumnDefinition]:
        """
        返回要写入导出文件的列列表。

        :param scope: "visible" = 当前可见列 + export_always 列
                      "all"     = 全部非 ui_only 列（含隐藏列）
        """
        if scope == "visible":
            keys_in_scope = {s.key for s in self._states if s.visible or s.definition.pinned}
            return [
                s.definition
                for s in self._states
                if (s.key in keys_in_scope or s.definition.export_always)
                and not s.definition.ui_only
            ]
        # "all"
        return [
            s.definition
            for s in self._states
            if not s.definition.ui_only
        ]

    def is_visible(self, key: str) -> bool:
        """查询指定列是否当前可见。"""
        st = self._find(key)
        return st.visible if st else False

    def get_width(self, key: str) -> int:
        """查询指定列当前宽度（像素）。"""
        st = self._find(key)
        return st.width if st else 100

    def get_definition(self, key: str) -> ColumnDefinition | None:
        """按 key 获取 ColumnDefinition。"""
        st = self._find(key)
        return st.definition if st else None

    # ── 列修改 ──────────────────────────────────── #

    def set_visible(self, key: str, visible: bool) -> None:
        """设置列可见性（pinned 列忽略此调用）。"""
        st = self._find(key)
        if st is None or st.definition.pinned:
            return
        if st.visible != visible:
            st.visible = visible
            self._notify()

    def set_width(self, key: str, width: int) -> None:
        """设置列宽度（像素）。"""
        st = self._find(key)
        if st is None:
            return
        st.width = max(30, width)

    def reorder(self, keys: list[str]) -> None:
        """
        按给定 key 顺序重排所有列。

        keys 中不包含的列追加到末尾（保持其相对顺序）。
        """
        key_index = {k: i for i, k in enumerate(keys)}
        n = len(keys)
        for s in self._states:
            if s.key in key_index:
                s.order = key_index[s.key]
            else:
                s.order = n
                n += 1
        self._states.sort(key=lambda s: s.order)
        for i, s in enumerate(self._states):
            s.order = i
        self._notify()

    def reset_to_default(self) -> None:
        """恢复所有列到注册表默认状态，并删除持久化文件。"""
        self._init_states()
        if _SETTINGS_PATH.exists():
            _SETTINGS_PATH.unlink()
        self._notify()

    def show_all(self) -> None:
        """显示全部非 meta 列（pinned 外的所有列设为可见）。"""
        for s in self._states:
            if s.definition.group != "meta":
                s.visible = True
        self._notify()

    def toggle_group(self, group: str, visible: bool) -> None:
        """批量切换某分组的所有列可见性。"""
        changed = False
        for s in self._states:
            if s.definition.group == group and not s.definition.pinned:
                if s.visible != visible:
                    s.visible = visible
                    changed = True
        if changed:
            self._notify()

    # ── 右键菜单构建（轻 Qt 依赖）─────────────────── #

    def build_header_menu(self, parent=None):
        """
        构建表头右键菜单（QMenu）。

        菜单结构：
          [分组名]
            ✓ 列名1  （可点击切换）
              列名2
          ──
          [全部显示]
          [恢复默认]

        返回 QMenu 实例，调用方负责 exec_()。
        """
        from vnpy.trader.ui import QtWidgets  # noqa: PLC0415

        menu = QtWidgets.QMenu(parent)

        groups_seen: list[str] = []
        group_actions: dict[str, list] = {}

        for s in self._states:
            col = s.definition
            if col.group == "meta" or col.pinned:
                continue
            if col.group not in groups_seen:
                groups_seen.append(col.group)
                group_actions[col.group] = []

            action = QtWidgets.QAction(
                col.cn_header or col.header, menu
            )
            action.setCheckable(True)
            action.setChecked(s.visible)

            key = col.key

            def _toggle(checked: bool, _key: str = key) -> None:
                self.set_visible(_key, checked)
                self.save()

            action.toggled.connect(_toggle)
            group_actions[col.group].append(action)

        _GROUP_LABELS = {
            "basic":   "基本信息",
            "return":  "收益指标",
            "risk":    "风险指标",
            "trade":   "交易指标",
            "capital": "资金/成本",
            "factor":  "因子分析",
        }

        for group in groups_seen:
            sub = menu.addMenu(_GROUP_LABELS.get(group, group))
            for action in group_actions[group]:
                sub.addAction(action)

        menu.addSeparator()

        show_all_action = QtWidgets.QAction("全部显示", menu)
        show_all_action.triggered.connect(lambda: (self.show_all(), self.save()))
        menu.addAction(show_all_action)

        reset_action = QtWidgets.QAction("恢复默认", menu)
        reset_action.triggered.connect(self.reset_to_default)
        menu.addAction(reset_action)

        return menu

    # ── 变更通知 ─────────────────────────────────── #

    def register_on_change(self, callback: Callable[[], None]) -> None:
        """注册列状态变更回调（可注册多个）。"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_on_change(self, callback: Callable[[], None]) -> None:
        """注销变更回调。"""
        self._callbacks = [c for c in self._callbacks if c is not callback]

    def _notify(self) -> None:
        for cb in list(self._callbacks):
            try:
                cb()
            except Exception:
                pass

    # ── 内部工具 ─────────────────────────────────── #

    def _find(self, key: str) -> _ColumnState | None:
        for s in self._states:
            if s.key == key:
                return s
        return None

    def __len__(self) -> int:
        return len(self._states)

    def __repr__(self) -> str:
        visible = len(self.get_visible_columns())
        return f"ColumnManager(total={len(self._states)}, visible={visible})"
