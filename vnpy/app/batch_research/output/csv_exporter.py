"""
output/csv_exporter.py

CSVExporter  —  把 BatchBacktestResult 列表导出为 CSV 文件

特性：
- 编码：utf-8-sig（带 BOM，Excel 直接打开不乱码）
- 列头：cn_header 优先，否则使用 header
- None 值写空字符串，不写 0
- 可选追加聚合汇总行（SUMMARY）
- scope=VISIBLE → 只写当前可见列
- scope=ALL     → 全部非 ui_only 列
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .exporter import BaseExporter, ExportResult, ExportScope

if TYPE_CHECKING:
    from ..batch_result import BatchBacktestResult
    from ..column_definition import ColumnDefinition
    from ..column_manager import ColumnManager


class CSVExporter(BaseExporter):
    """
    CSV 导出器。

    用法::

        exporter = CSVExporter()
        result = exporter.export(
            bbr_list,
            Path("out.csv"),
            column_manager=cm,
            scope=ExportScope.ALL,
        )
        print(result)
    """

    def export(
        self,
        results: list["BatchBacktestResult"],
        filepath: Path | str,
        column_manager: "ColumnManager",
        scope: ExportScope = ExportScope.ALL,
        include_summary: bool = True,
        encoding: str = "utf-8-sig",
    ) -> ExportResult:
        """
        导出为 CSV 文件。

        :param results:          BatchBacktestResult 列表
        :param filepath:         目标 .csv 文件路径
        :param column_manager:   ColumnManager 实例
        :param scope:            ExportScope.VISIBLE / ExportScope.ALL
        :param include_summary:  True = 在末尾追加 SUMMARY 汇总行
        :param encoding:         文件编码，默认 utf-8-sig
        :return:                 ExportResult
        """
        self._encoding        = encoding
        self._include_summary = include_summary
        return super().export(results, filepath, column_manager, scope)

    def _write(
        self,
        rows: list[dict[str, Any]],
        cols: list["ColumnDefinition"],
        filepath: Path,
    ) -> ExportResult:
        filepath.parent.mkdir(parents=True, exist_ok=True)

        headers = [c.export_header for c in cols]
        keys    = [c.key for c in cols]

        with open(filepath, "w", newline="", encoding=self._encoding) as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for row in rows:
                writer.writerow([
                    self._format_display(row.get(key), col)
                    for key, col in zip(keys, cols)
                ])

            if getattr(self, "_include_summary", True):
                summary_row = self._build_summary_row(rows, keys, cols)
                writer.writerow(summary_row)

        file_size = filepath.stat().st_size
        return ExportResult(
            filepath=filepath,
            rows=len(rows),
            columns=len(cols),
            file_size=file_size,
            success=True,
        )

    @staticmethod
    def _build_summary_row(
        rows: list[dict[str, Any]],
        keys: list[str],
        cols: list["ColumnDefinition"],
    ) -> list[str]:
        """
        构建尾部汇总行：数值列计算均值，字符串列留空，第一列写 SUMMARY。
        """
        summary: list[str] = [""] * len(keys)
        if summary:
            summary[0] = "SUMMARY"

        numeric_fmts = {"pct", "float1", "float2", "float3", "int", "money"}

        for i, (key, col) in enumerate(zip(keys, cols)):
            if col.fmt not in numeric_fmts:
                continue
            vals = []
            for row in rows:
                v = row.get(key)
                if v is not None:
                    try:
                        vals.append(float(v))
                    except (TypeError, ValueError):
                        pass
            if vals:
                avg = sum(vals) / len(vals)
                summary[i] = CSVExporter._format_display(avg, col)

        return summary
