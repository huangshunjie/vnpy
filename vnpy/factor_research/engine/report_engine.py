"""
factor_research/engine/report_engine.py

ReportEngine -- Factor analysis report generator.

Responsibilities:
  - Accept computation results from all analysis stages.
  - Build structured DataFrames for each report section.
  - Export to multi-sheet Excel via pandas ExcelWriter + openpyxl.
  - No UI access, no database access.

Sheet layout:
  1. 概览          -- data source metadata
  2. IC统计        -- IC / RankIC scalar statistics
  3. IC Decay      -- IC mean per lag
  4. 分层收益      -- per-quantile annualized return + monotonicity
  5. LongShort绩效 -- long / short / L-S performance metrics
  6. 综合评分      -- 6-dimension scores + total + grade
  7. IC时序        -- full rolling IC time series
"""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ..model import (
    DecayResult,
    FactorScore,
    IcStats,
    OverviewSummary,
    QuantileResult,
)


class ReportEngine:
    """Factor research report engine."""

    # ------------------------------------------------------------------ #
    #  Build DataFrames
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_overview(summaries: list[OverviewSummary]) -> pd.DataFrame:
        rows = []
        for s in summaries:
            rows.append({
                "合约代码":   s.vt_symbol,
                "数据频率":   s.interval,
                "数据开始":   str(s.data_start) if s.data_start else "—",
                "数据结束":   str(s.data_end)   if s.data_end   else "—",
                "时间跨度(天)": s.date_range_days,
                "Bar 数量":   s.total_bars,
            })
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    @staticmethod
    def build_ic(stats: IcStats | None) -> pd.DataFrame:
        if stats is None:
            return pd.DataFrame()
        def _f(v: float) -> str:
            return f"{v:.6f}" if not math.isnan(v) else "—"
        rows = [
            {"指标": "IC 均值",        "数值": _f(stats.ic_mean)},
            {"指标": "IC 标准差",       "数值": _f(stats.ic_std)},
            {"指标": "ICIR",           "数值": _f(stats.icir)},
            {"指标": "IC 胜率",         "数值": f"{stats.ic_positive_rate:.2%}" if not math.isnan(stats.ic_positive_rate) else "—"},
            {"指标": "RankIC 均值",     "数值": _f(stats.rank_ic_mean)},
            {"指标": "RankIC 标准差",   "数值": _f(stats.rank_ic_std)},
            {"指标": "RankICIR",       "数值": _f(stats.rank_icir)},
            {"指标": "RankIC 胜率",     "数值": f"{stats.rank_ic_positive_rate:.2%}" if not math.isnan(stats.rank_ic_positive_rate) else "—"},
            {"指标": "样本量",          "数值": str(stats.sample_size)},
            {"指标": "合约数",          "数值": str(stats.n_symbols)},
            {"指标": "持有期(天)",      "数值": str(stats.lag)},
            {"指标": "合约代码",        "数值": stats.vt_symbol},
            {"指标": "因子名称",        "数值": stats.factor_name},
        ]
        return pd.DataFrame(rows)

    @staticmethod
    def build_decay(result: DecayResult | None) -> pd.DataFrame:
        if result is None or not result.is_valid():
            return pd.DataFrame()
        rows = []
        for p in result.points:
            rows.append({
                "持有期(天)":   p.lag,
                "IC 均值":      round(p.ic_mean,      6) if not math.isnan(p.ic_mean)      else None,
                "RankIC 均值":  round(p.rank_ic_mean, 6) if not math.isnan(p.rank_ic_mean) else None,
                "ICIR":         round(p.icir,          6) if not math.isnan(p.icir)          else None,
                "RankICIR":     round(p.rank_icir,     6) if not math.isnan(p.rank_icir)     else None,
                "样本量":       p.sample_size,
            })
        df = pd.DataFrame(rows)
        df.attrs["vt_symbol"]   = result.vt_symbol
        df.attrs["factor_name"] = result.factor_name
        df.attrs["n_symbols"]   = result.n_symbols
        return df

    @staticmethod
    def build_quantile(result: QuantileResult | None) -> pd.DataFrame:
        if result is None or not result.is_valid():
            return pd.DataFrame()
        rows = []
        for ql in result.quantile_labels:
            ann = result.annualized_returns.get(ql, float("nan"))
            rows.append({
                "档位":        ql,
                "年化收益":    f"{ann:.4%}" if not math.isnan(ann) else "—",
                "年化收益(数值)": round(ann, 6) if not math.isnan(ann) else None,
            })
        # L-S row
        ls_ann = result.long_short_annualized
        rows.append({
            "档位":        "Long-Short",
            "年化收益":    f"{ls_ann:.4%}" if not math.isnan(ls_ann) else "—",
            "年化收益(数值)": round(ls_ann, 6) if not math.isnan(ls_ann) else None,
        })
        df = pd.DataFrame(rows)
        nan = float("nan")
        # append summary rows; float nan keeps column dtype consistent
        meta = pd.DataFrame([{
            "档位": "单调性评分",
            "年化收益": f"{result.monotonicity_score:.4f}" if not math.isnan(result.monotonicity_score) else "—",
            "年化收益(数值)": nan,
        }, {
            "档位": "合约数",
            "年化收益": str(result.n_symbols),
            "年化收益(数值)": nan,
        }])
        return pd.concat([df, meta], ignore_index=True)

    @staticmethod
    def build_longshort(result: QuantileResult | None) -> pd.DataFrame:
        """Compute long/short/L-S performance metrics from QuantileResult."""
        if result is None or not result.is_valid():
            return pd.DataFrame()

        import numpy as np

        TRADING_DAYS = 252

        def _perf(label: str, ret_series: pd.Series | None, lag: int) -> dict:
            if ret_series is None or ret_series.empty:
                return {"组合": label, "年化收益": "—", "最大回撤": "—",
                        "Sharpe": "—", "Calmar": "—"}
            r   = ret_series.dropna().values
            if len(r) < 2:
                return {"组合": label, "年化收益": "—", "最大回撤": "—",
                        "Sharpe": "—", "Calmar": "—"}
            ann_f = TRADING_DAYS / lag
            tot   = float((1 + r).prod()) - 1
            ann   = (1 + tot) ** (ann_f / len(r)) - 1
            nav   = np.cumprod(1 + r)
            peak  = np.maximum.accumulate(nav)
            mdd   = float(np.min((nav - peak) / np.maximum(peak, 1e-12)))
            std   = float(np.std(r, ddof=1))
            sharpe  = float(np.mean(r)) / std * math.sqrt(ann_f) if std > 1e-12 else float("nan")
            calmar  = ann / abs(mdd) if mdd < -1e-6 else float("nan")
            return {
                "组合":    label,
                "年化收益": f"{ann:.4%}",
                "最大回撤": f"{mdd:.4%}",
                "Sharpe":  f"{sharpe:.4f}" if not math.isnan(sharpe) else "—",
                "Calmar":  f"{calmar:.4f}" if not math.isnan(calmar) else "—",
            }

        q_labels = result.quantile_labels
        long_ret  = result.quantile_returns.get(q_labels[-1])
        short_ret = result.quantile_returns.get(q_labels[0])

        # L-S: recover period returns from cumulative series
        ls_ret_series = None
        if result.long_short_series is not None and not result.long_short_series.empty:
            nav = (1 + result.long_short_series.dropna()).values
            if len(nav) > 1:
                r = pd.Series(
                    np.diff(nav) / np.maximum(nav[:-1], 1e-12),
                    index=result.long_short_series.dropna().index[1:],
                )
                ls_ret_series = r

        rows = [
            _perf(f"多头（{q_labels[-1]}）", long_ret,      result.lag),
            _perf(f"空头（{q_labels[0]}）",  short_ret,     result.lag),
            _perf("Long-Short",              ls_ret_series, result.lag),
        ]
        return pd.DataFrame(rows)

    @staticmethod
    def build_score(fs: FactorScore | None) -> pd.DataFrame:
        if fs is None or not fs.is_valid():
            return pd.DataFrame()
        rows = []
        for d in fs.dimensions:
            rows.append({
                "维度":        d.name,
                "原始值":      round(d.raw_value, 6) if not math.isnan(d.raw_value) else None,
                "得分(0-100)": round(d.score, 2),
                "权重":        d.weight,
                "说明":        d.description,
            })
        # summary rows
        rows.append({"维度": "综合得分", "原始值": round(fs.total_score, 2),
                     "得分(0-100)": round(fs.total_score, 2), "权重": None, "说明": ""})
        rows.append({"维度": "等级",    "原始值": None,
                     "得分(0-100)": None,          "权重": None, "说明": fs.grade})
        return pd.DataFrame(rows)

    @staticmethod
    def build_ic_series(stats: IcStats | None) -> pd.DataFrame:
        if stats is None or stats.ic_series is None:
            return pd.DataFrame()
        ic  = stats.ic_series.dropna().rename("IC")
        ric = stats.rank_ic_series.dropna().rename("RankIC") \
              if stats.rank_ic_series is not None else None
        if ric is not None:
            df = pd.concat([ic, ric], axis=1)
        else:
            df = ic.to_frame()
        df.index.name = "日期"
        return df.reset_index()

    # ------------------------------------------------------------------ #
    #  Export
    # ------------------------------------------------------------------ #

    @staticmethod
    def export_excel(
        path: str | Path,
        overview_df:  pd.DataFrame,
        ic_df:        pd.DataFrame,
        decay_df:     pd.DataFrame,
        quantile_df:  pd.DataFrame,
        longshort_df: pd.DataFrame,
        score_df:     pd.DataFrame,
        ic_series_df: pd.DataFrame,
        meta: dict[str, Any] | None = None,
    ) -> Path:
        """
        Write all DataFrames to a multi-sheet Excel file.

        Returns the resolved Path of the written file.
        Requires openpyxl (bundled with most pandas installs).
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        sheet_map = [
            ("概览",          overview_df),
            ("IC统计",        ic_df),
            ("IC Decay",      decay_df),
            ("分层收益",      quantile_df),
            ("LongShort绩效", longshort_df),
            ("综合评分",      score_df),
            ("IC时序",        ic_series_df),
        ]

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            # Meta sheet with generation timestamp
            meta_rows = [
                {"字段": "生成时间",  "值": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            ]
            if meta:
                for k, v in meta.items():
                    meta_rows.append({"字段": k, "值": str(v)})
            pd.DataFrame(meta_rows).to_excel(
                writer, sheet_name="元信息", index=False
            )

            for sheet_name, df in sheet_map:
                if df is not None and not df.empty:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    # Write placeholder so sheet always exists
                    pd.DataFrame([{"说明": "暂无数据"}]).to_excel(
                        writer, sheet_name=sheet_name, index=False
                    )

            # Auto-width for all sheets
            for sheet in writer.sheets.values():
                for col_cells in sheet.columns:
                    max_len = max(
                        (len(str(cell.value)) if cell.value is not None else 0)
                        for cell in col_cells
                    )
                    sheet.column_dimensions[
                        col_cells[0].column_letter
                    ].width = min(max_len + 4, 50)

        return path
