"""
portfolio_engine/utils/export_utils.py

导出工具（Excel / CSV）。
Phase 4：实现 export_excel / export_csv，供 ReportTab 调用。

Excel 报告 Sheet 布局：
  Sheet 1 "净值曲线"    : datetime + portfolio_nav (+ benchmark_nav 可选)
  Sheet 2 "绩效统计"    : 指标名 / 数值 / 说明
  Sheet 3 "权重分配"    : slot_name / weight / volatility / risk_contrib
  Sheet 4 "风险暴露"    : Beta / Alpha / TE / IR / 因子暴露 / 行业暴露
  Sheet 5 "调仓历史"    : 时间 / 槽位 / 前权重 / 后权重 / Delta
  Sheet 6 "回撤归因"    : 槽位 / 贡献 / 权重 / 累计收益
"""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ..model.performance_model import PerformanceStats
    from ..model.allocation_model import AllocationResult
    from ..model.risk_model import RiskExposure
    from ..model.attribution_model import AttributionResult
    from ..engine.rebalance_engine import RebalanceRecord


def export_excel(
    path: Path,
    performance: "PerformanceStats | None" = None,
    allocation:  "AllocationResult | None" = None,
    risk:        "RiskExposure | None"     = None,
    attribution: "AttributionResult | None" = None,
    rebalance_history: "list[RebalanceRecord] | None" = None,
    nav_df:      pd.DataFrame | None       = None,
) -> Path:
    """
    导出组合报告到 Excel 文件（.xlsx）。

    openpyxl 是 VeighNa Studio 自带依赖，直接可用。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(str(path), engine="openpyxl") as writer:

        # ── Sheet 1：净值曲线 ───────────────────────────────────────────
        nav_data = _build_nav_df(performance, nav_df)
        if nav_data is not None and not nav_data.empty:
            nav_data.to_excel(writer, sheet_name="净值曲线", index=True)

        # ── Sheet 2：绩效统计 ───────────────────────────────────────────
        perf_data = _build_perf_df(performance)
        if perf_data is not None:
            perf_data.to_excel(writer, sheet_name="绩效统计", index=False)

        # ── Sheet 3：权重分配 ───────────────────────────────────────────
        alloc_data = _build_alloc_df(allocation)
        if alloc_data is not None:
            alloc_data.to_excel(writer, sheet_name="权重分配", index=False)

        # ── Sheet 4：风险暴露 ───────────────────────────────────────────
        risk_data = _build_risk_df(risk)
        if risk_data is not None:
            risk_data.to_excel(writer, sheet_name="风险暴露", index=False)

        # ── Sheet 5：调仓历史 ───────────────────────────────────────────
        reb_data = _build_rebalance_df(rebalance_history)
        if reb_data is not None and not reb_data.empty:
            reb_data.to_excel(writer, sheet_name="调仓历史", index=False)

        # ── Sheet 6：回撤归因 ───────────────────────────────────────────
        attr_data = _build_attribution_df(attribution)
        if attr_data is not None and not attr_data.empty:
            attr_data.to_excel(writer, sheet_name="回撤归因", index=False)

    return path


def export_csv(series: pd.Series | pd.DataFrame, path: Path) -> Path:
    """导出单个序列 / DataFrame 为 CSV（UTF-8-BOM，Excel 可直接打开）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(series, pd.Series):
        series = series.to_frame(name=series.name or "value")
    series.to_csv(str(path), encoding="utf-8-sig")
    return path


# ──────────────────────────────────────────────────────────────────────────────
#  内部构建函数
# ──────────────────────────────────────────────────────────────────────────────

def _build_nav_df(
    performance: "PerformanceStats | None",
    nav_df: pd.DataFrame | None,
) -> pd.DataFrame | None:
    """构建净值曲线 DataFrame。"""
    if nav_df is not None and not nav_df.empty:
        return nav_df

    if performance is None or performance.nav_series is None:
        return None

    nav = performance.nav_series.dropna()
    if nav.empty:
        return None

    df = pd.DataFrame({"净值": nav})
    df.index.name = "日期"
    return df


def _build_perf_df(performance: "PerformanceStats | None") -> pd.DataFrame | None:
    """构建绩效统计表。"""
    if performance is None:
        return None

    rows = [
        ("组合名称",   performance.portfolio_name,                   ""),
        ("计算时间",   performance.computed_at.strftime("%Y-%m-%d %H:%M:%S"), ""),
        ("总收益率",   _pct(performance.total_return),              "区间累计收益"),
        ("年化收益率", _pct(performance.annual_return),             "252 交易日年化"),
        ("Sharpe 比率", _num(performance.sharpe_ratio, 3),          "年化 Sharpe（rf=0）"),
        ("最大回撤",   _pct(performance.max_drawdown),              "负数"),
        ("Calmar 比率", _num(performance.calmar_ratio, 3),          "年化收益 / |MDD|"),
        ("年化波动率", _pct(performance.volatility),               "日收益率标准差×√252"),
        ("日胜率",     _pct(performance.win_rate),                  "r>0 的占比"),
    ]
    return pd.DataFrame(rows, columns=["指标", "数值", "说明"])


def _build_alloc_df(allocation: "AllocationResult | None") -> pd.DataFrame | None:
    """构建权重分配表。"""
    if allocation is None or not allocation.weights:
        return None

    rows = []
    for name, w in allocation.weights.items():
        vol = allocation.volatilities.get(name, float("nan"))
        rc  = allocation.risk_contribs.get(name, float("nan"))
        rows.append({
            "槽位":   name,
            "权重":   _pct(w),
            "年化波动率": _pct(vol),
            "风险贡献":  _num(rc, 4) if not math.isnan(rc) else "—",
            "权重方法":  allocation.method.value,
        })
    rows.append({
        "槽位": "合计",
        "权重": _pct(sum(allocation.weights.values())),
        "年化波动率": "",
        "风险贡献": "",
        "权重方法": "",
    })
    return pd.DataFrame(rows)


def _build_risk_df(risk: "RiskExposure | None") -> pd.DataFrame | None:
    """构建风险暴露表（标量指标 + 因子暴露 + 行业暴露）。"""
    if risk is None:
        return None

    rows = [
        ("Beta",       _num(risk.portfolio_beta, 4),   "市场 Beta"),
        ("Alpha（年化）", _pct(risk.portfolio_alpha),   "Jensen Alpha"),
        ("跟踪误差",   _pct(risk.tracking_error),       "年化 TE vs 基准"),
        ("信息比率",   _num(risk.information_ratio, 3), "IR = ActiveRet / TE"),
        ("最大回撤",   _pct(risk.max_drawdown),         ""),
        ("MDD 开始",   _dt(risk.drawdown_start),        "峰值日期"),
        ("MDD 结束",   _dt(risk.drawdown_end),          "谷值日期"),
    ]
    for fname, fval in (risk.factor_exposures or {}).items():
        rows.append((f"因子：{fname}", _num(fval, 4), "代理指标"))
    for sname, sw in (risk.sector_weights or {}).items():
        rows.append((f"板块：{sname}", _pct(sw), "权重占比"))
    for slot, vol in (risk.slot_volatilities or {}).items():
        rows.append((f"槽位波动率：{slot}", _pct(vol), "21日滚动"))

    return pd.DataFrame(rows, columns=["指标", "数值", "说明"])


def _build_rebalance_df(
    history: "list[RebalanceRecord] | None",
) -> pd.DataFrame | None:
    """构建调仓历史表（展开为每槽位一行）。"""
    if not history:
        return None

    rows = []
    for rec in history:
        all_slots = sorted(
            set(list(rec.prev_weights.keys()) | list(rec.new_weights.keys()))
        )
        for slot in all_slots:
            prev  = rec.prev_weights.get(slot, 0.0)
            new   = rec.new_weights.get(slot, 0.0)
            delta = rec.delta.get(slot, new - prev)
            rows.append({
                "调仓时间": rec.triggered_at.strftime("%Y-%m-%d"),
                "槽位":     slot,
                "调仓前权重": _pct(prev),
                "调仓后权重": _pct(new),
                "Delta":    f"{delta:+.2%}",
                "原因":     rec.reason,
            })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _build_attribution_df(
    attribution: "AttributionResult | None",
) -> pd.DataFrame | None:
    """构建回撤归因表。"""
    if attribution is None or not attribution.slot_contributions:
        return None

    rows = []
    total_dd = attribution.total_drawdown

    for sc in sorted(attribution.slot_contributions, key=lambda x: x.contribution):
        pct_of_total = (
            sc.contribution / total_dd
            if not math.isnan(total_dd) and abs(total_dd) > 1e-10
            else float("nan")
        )
        rows.append({
            "槽位":       sc.slot_name,
            "权重":       _pct(sc.weight),
            "区间累计收益": _pct(sc.cumulative_return)
                if not math.isnan(sc.cumulative_return) else "—",
            "回撤贡献":   _pct(sc.contribution)
                if not math.isnan(sc.contribution) else "—",
            "贡献占比":   _pct(pct_of_total)
                if not math.isnan(pct_of_total) else "—",
        })

    # 汇总行
    valid_contribs = [sc.contribution for sc in attribution.slot_contributions
                      if not math.isnan(sc.contribution)]
    rows.append({
        "槽位":       "合计",
        "权重":       _pct(sum(sc.weight for sc in attribution.slot_contributions)),
        "区间累计收益": "",
        "回撤贡献":   _pct(sum(valid_contribs)) if valid_contribs else "—",
        "贡献占比":   "",
    })
    rows.append({
        "槽位":       "（总回撤）",
        "权重":       "",
        "区间累计收益": "",
        "回撤贡献":   _pct(total_dd) if not math.isnan(total_dd) else "—",
        "贡献占比":   "100%",
    })
    rows.append({
        "槽位":       "（市场系统性贡献）",
        "权重":       "",
        "区间累计收益": "",
        "回撤贡献":   _pct(attribution.market_contribution)
            if not math.isnan(attribution.market_contribution) else "—",
        "贡献占比":   "",
    })

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────────
#  格式化工具
# ──────────────────────────────────────────────────────────────────────────────

def _pct(v: float) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.2%}"


def _num(v: float, decimals: int = 4) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{decimals}f}"


def _dt(v: datetime | None) -> str:
    if v is None:
        return "—"
    return v.strftime("%Y-%m-%d")
