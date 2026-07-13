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

# 中英文双语列标题映射
COLUMN_DISPLAY_NAMES: dict[str, str] = {
    "vt_symbol":             "股票代码/vt_symbol",
    "strategy_name":         "策略名称/strategy_name",
    "status":                "状态/status",
    "start_date":            "开始日期/start_date",
    "end_date":              "结束日期/end_date",
    "total_days":            "总交易天数/total_days",
    "profit_days":           "盈利天数/profit_days",
    "loss_days":             "亏损天数/loss_days",
    "capital":               "初始资金/capital",
    "end_balance":           "结束资金/end_balance",
    "total_return":          "总收益率%/total_return",
    "annual_return":         "年化收益率%/annual_return",
    "daily_return":          "日均收益率%/daily_return",
    "return_std":            "收益率标准差%/return_std",
    "max_drawdown":          "最大回撤额/max_drawdown",
    "max_ddpercent":         "最大回撤%/max_ddpercent",
    "max_drawdown_duration": "最大回撤持续天数/max_drawdown_duration",
    "sharpe_ratio":          "夏普比率/sharpe_ratio",
    "ewm_sharpe":            "EWM夏普比率/ewm_sharpe",
    "return_drawdown_ratio": "收益回撤比/return_drawdown_ratio",
    "rgr_ratio":             "RGR比率/rgr_ratio",
    "calmar_ratio":          "卡玛比率/calmar_ratio",
    "profit_factor":         "盈利因子/profit_factor",
    "total_trade_count":     "总交易次数/total_trade_count",
    "daily_trade_count":     "日均交易次数/daily_trade_count",
    "total_net_pnl":         "总净盈亏/total_net_pnl",
    "daily_net_pnl":         "日均净盈亏/daily_net_pnl",
    "total_commission":      "总手续费/total_commission",
    "daily_commission":      "日均手续费/daily_commission",
    "total_slippage":        "总滑点/total_slippage",
    "daily_slippage":        "日均滑点/daily_slippage",
    "total_turnover":        "总成交额/total_turnover",
    "daily_turnover":        "日均成交额/daily_turnover",
    "task_id":               "任务ID/task_id",
    "elapsed_seconds":       "耗时(秒)/elapsed_seconds",
    "error_msg":             "错误信息/error_msg",
}

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

        # Map each internal key to its bilingual display name for the header row
        display_keys: list[str] = [
            COLUMN_DISPLAY_NAMES.get(k, k) for k in all_keys
        ]
        # Reverse map: display_name -> internal_key (for summary row lookup)
        display_to_key: dict[str, str] = dict(zip(display_keys, all_keys))

        with open(filepath, "w", newline="", encoding=encoding) as f:
            writer = csv.writer(f, delimiter=delimiter)

            # Write bilingual header
            writer.writerow(display_keys)

            # Write data rows (values ordered by all_keys)
            for row in rows:
                writer.writerow([row.get(k, "") for k in all_keys])

            if include_summary_row:
                summary = build_aggregate_summary(results)
                summary_row: list = [""] * len(all_keys)
                key_index = {k: i for i, k in enumerate(all_keys)}
                summary_row[0] = "SUMMARY"
                for k, v in summary.items():
                    if k in key_index:
                        summary_row[key_index[k]] = v
                    plain_key = k.replace("agg_", "")
                    if plain_key in key_index and k not in key_index:
                        summary_row[key_index[plain_key]] = v
                writer.writerow(summary_row)

        file_size = filepath.stat().st_size
        return WriteResult(
            filepath=filepath,
            rows_written=len(rows),
            columns=len(all_keys),
            file_size_bytes=file_size,
        )
