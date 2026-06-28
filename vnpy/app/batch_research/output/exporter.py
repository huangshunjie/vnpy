"""
output/exporter.py

BaseExporter  —  所有导出器的抽象基类
ExportScope   —  导出范围枚举
ExportResult  —  导出操作结果描述

设计约定：
- 子类只实现 _write()，列过滤/序列化/格式化统一在基类处理
- ExportScope.VISIBLE → 当前用户可见列 + export_always 列
- ExportScope.ALL     → 全部非 ui_only 列（含隐藏列）
- None 值序列化为空字符串，不写 0
- 不依赖 Qt，不依赖数据库
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..batch_result import BatchBacktestResult
    from ..column_definition import ColumnDefinition
    from ..column_manager import ColumnManager


# ──────────────────────────────────────────────────── #
#  ExportScope
# ──────────────────────────────────────────────────── #

class ExportScope(Enum):
    """
    导出范围枚举。

    VISIBLE  当前用户可见列 + export_always 列（右键菜单"导出当前列"）
    ALL      全部非 ui_only 列，含隐藏列（工具栏"导出全量"）
    """
    VISIBLE = "visible"
    ALL     = "all"


# ──────────────────────────────────────────────────── #
#  ExportResult
# ──────────────────────────────────────────────────── #

@dataclass
class ExportResult:
    """导出操作的结果描述。"""
    filepath:  Path
    rows:      int
    columns:   int
    file_size: int
    success:   bool
    error_msg: str = ""

    def __str__(self) -> str:
        if self.success:
            kb = self.file_size / 1024
            return (
                f"导出成功：{self.filepath.name}"
                f"（{self.rows} 行 × {self.columns} 列，{kb:.1f} KB）"
            )
        return f"导出失败：{self.error_msg}"


# ──────────────────────────────────────────────────── #
#  BaseExporter
# ──────────────────────────────────────────────────── #

class BaseExporter(ABC):
    """
    所有导出器的抽象基类。

    子类只需实现 _write(rows, cols, filepath) 方法。
    列过滤、序列化、格式化统一在此基类处理。

    用法（子类）::

        class MyExporter(BaseExporter):
            def _write(self, rows, cols, filepath):
                ...
                return ExportResult(...)

    用法（调用方）::

        exporter = CSVExporter()
        result = exporter.export(
            bbr_list,
            Path("out.csv"),
            column_manager=cm,
            scope=ExportScope.ALL,
        )
    """

    def export(
        self,
        results: list["BatchBacktestResult"],
        filepath: Path | str,
        column_manager: "ColumnManager",
        scope: ExportScope = ExportScope.ALL,
    ) -> ExportResult:
        """
        统一导出入口。

        :param results:        BatchBacktestResult 列表
        :param filepath:       目标文件路径
        :param column_manager: ColumnManager 实例，提供当前列配置
        :param scope:          ExportScope.VISIBLE 或 ExportScope.ALL
        :return:               ExportResult
        """
        filepath = Path(filepath)
        if not results:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text("", encoding="utf-8-sig")
            return ExportResult(
                filepath=filepath, rows=0, columns=0,
                file_size=0, success=True,
            )

        cols = self._resolve_columns(column_manager, scope)
        rows = self._serialize(results, cols)
        try:
            return self._write(rows, cols, filepath)
        except Exception as e:
            return ExportResult(
                filepath=filepath, rows=0, columns=0,
                file_size=0, success=False, error_msg=str(e),
            )

    @abstractmethod
    def _write(
        self,
        rows: list[dict[str, Any]],
        cols: list["ColumnDefinition"],
        filepath: Path,
    ) -> ExportResult:
        """子类实现：把序列化后的 rows 写入 filepath，返回 ExportResult。"""
        ...

    # ── 内部辅助方法（子类可覆盖）──────────────────── #

    @staticmethod
    def _resolve_columns(
        column_manager: "ColumnManager",
        scope: ExportScope,
    ) -> list["ColumnDefinition"]:
        """从 ColumnManager 动态获取要导出的列列表。"""
        return column_manager.get_export_columns(scope.value)

    @staticmethod
    def _serialize(
        results: list["BatchBacktestResult"],
        cols: list["ColumnDefinition"],
    ) -> list[dict[str, Any]]:
        """
        把 BatchBacktestResult 列表序列化为 list[dict]。

        key   = ColumnDefinition.key
        value = 原始值（None 原样透传，写文件层负责转为空字符串）
        """
        rows: list[dict[str, Any]] = []
        for r in results:
            row: dict[str, Any] = {}
            for col in cols:
                row[col.key] = getattr(r, col.key, None)
            rows.append(row)
        return rows

    @staticmethod
    def _format_display(val: Any, col: "ColumnDefinition") -> str:
        """
        按列 fmt 类型把原始值格式化为显示字符串。
        val=None 时返回空字符串。
        供 CSV 等纯文本导出使用。
        """
        if val is None:
            return ""
        try:
            fmt = col.fmt
            if fmt == "pct":    return f"{float(val):.2f}"
            if fmt == "float1": return f"{float(val):.1f}"
            if fmt == "float2": return f"{float(val):.2f}"
            if fmt == "float3": return f"{float(val):.3f}"
            if fmt == "int":    return str(int(float(val)))
            if fmt == "money":  return f"{float(val):,.0f}"
            return str(val)
        except (TypeError, ValueError):
            return str(val)
