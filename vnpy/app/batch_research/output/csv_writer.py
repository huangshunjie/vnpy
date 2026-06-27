"""
CSVWriter

Writes batch backtest results to a CSV file.

Each row = one symbol. Columns follow ORDERED_COLUMNS from StatisticsAnalyzer,
then any extra keys present in the data.

Features:
  - Automatic directory creation
  - Configurable encoding (default utf-8-sig for Excel compatibility)
  - Optional aggregate summary row appended at the bottom
  - Returns WriteResult with row/column counts and file size
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ..statistics.analyzer import ORDERED_COLUMNS, StatisticsAnalyzer
from ..statistics.metrics import build_aggregate_summary

if TYPE_CHECKING:
    from ..task import BacktestResult


@dataclass
class WriteResult:
    """Summary of a completed write operation."""
    filepath: Path
    rows_written: int
    columns: int
    file_size_bytes: int

    def __str__(self) -> str:
        kb = self.file_size_bytes / 1024
        return (
            f"WriteResult({self.filepath.name}: "
            f"{self.rows_written} rows x {self.columns} cols, "
            f"{kb:.1f} KB)"
        )


class CSVWriter:
    """
    Writes a list of BacktestResult objects to a CSV file.

    Usage::

        writer = CSVWriter()
        wr = writer.write(results, Path("output/batch_result.csv"))
        print(wr)
    """

    def write(
        self,
        results: list["BacktestResult"],
        filepath: Path | str,
        encoding: str = "utf-8-sig",
        enrich: bool = True,
        include_summary_row: bool = True,
        delimiter: str = ",",
    ) -> WriteResult:
        """
        Write results to a CSV file.

        :param results:             List of BacktestResult objects.
        :param filepath:            Output CSV file path (created if needed).
        :param encoding:            File encoding. 'utf-8-sig' adds BOM so
                                    Excel opens it correctly without garbling.
        :param enrich:              Run StatisticsAnalyzer.enrich() before writing
                                    to add calmar_ratio / profit_factor columns.
        :param include_summary_row: Append an aggregate summary row at the end.
        :param delimiter:           CSV delimiter (default comma).
        :return:                    WriteResult with counts and file size.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if not results:
            filepath.write_text("", encoding=encoding)
            return WriteResult(filepath=filepath, rows_written=0,
                               columns=0, file_size_bytes=0)

        analyzer = StatisticsAnalyzer()
        if enrich:
            analyzer.enrich(results)

        rows = [r.to_flat_dict() for r in results]

        # Build column order: ORDERED_COLUMNS first, then any extras
        all_keys: list[str] = list(
            dict.fromkeys(
                [c for c in ORDERED_COLUMNS if c in rows[0]]
                + [k for k in rows[0] if k not in ORDERED_COLUMNS]
            )
        )

        with open(filepath, "w", newline="", encoding=encoding) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=all_keys,
                delimiter=delimiter,
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(rows)

            if include_summary_row:
                summary = build_aggregate_summary(results)
                # Write aggregate summary as a final row with blank symbol column
                summary_row: dict = {k: "" for k in all_keys}
                summary_row["vt_symbol"] = "__SUMMARY__"
                for k, v in summary.items():
                    if k in all_keys:
                        summary_row[k] = v
                    # Also write to matching column if key exists without prefix
                    plain_key = k.replace("agg_", "")
                    if plain_key in all_keys and k not in all_keys:
                        summary_row[plain_key] = v
                writer.writerow(summary_row)

        file_size = filepath.stat().st_size
        return WriteResult(
            filepath=filepath,
            rows_written=len(rows),
            columns=len(all_keys),
            file_size_bytes=file_size,
        )
