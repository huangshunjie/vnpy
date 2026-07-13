"""Phase 7 test: StatisticsAnalyzer, CSVWriter, ExcelWriter - Part 1"""

import math
import copy
import random
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy_ctastrategy.backtesting import BacktestingMode

from vnpy.app.batch_research.task import BacktestResult, TaskStatus
from vnpy.app.batch_research.statistics.analyzer import StatisticsAnalyzer, ORDERED_COLUMNS
from vnpy.app.batch_research.statistics.metrics import (
    calculate_win_rate, calculate_avg_sharpe, calculate_calmar_ratio,
    calculate_profit_loss_ratio, enrich_statistics, build_aggregate_summary,
)
from vnpy.app.batch_research.output.csv_writer import CSVWriter
from vnpy.app.batch_research.output.excel_writer import ExcelWriter


# ================================================================
# Mock results factory
# ================================================================

def make_mock_result(
    vt_symbol: str,
    total_return: float = 10.0,
    annual_return: float = 5.0,
    sharpe: float = 1.2,
    max_ddpercent: float = -8.0,
    total_trade_count: int = 50,
    status: TaskStatus = TaskStatus.SUCCESS,
) -> BacktestResult:
    result = BacktestResult(
        vt_symbol=vt_symbol,
        task_id=f"t_{vt_symbol}",
        strategy_name="TestStrategy",
        status=status,
    )
    if status == TaskStatus.SUCCESS:
        result.statistics = {
            "start_date": "2020-01-02", "end_date": "2021-06-30",
            "total_days": 365, "profit_days": 200, "loss_days": 165,
            "capital": 1_000_000,
            "end_balance": 1_000_000 * (1 + total_return / 100),
            "total_return": total_return, "annual_return": annual_return,
            "daily_return": annual_return / 240, "return_std": 1.5,
            "max_drawdown": max_ddpercent * 10000,
            "max_ddpercent": max_ddpercent, "max_drawdown_duration": 30,
            "sharpe_ratio": sharpe, "ewm_sharpe": sharpe * 0.9,
            "return_drawdown_ratio": abs(total_return / max_ddpercent) if max_ddpercent else 0,
            "rgr_ratio": 1.5,
            "total_net_pnl": total_return * 10000,
            "daily_net_pnl": total_return * 10000 / 365,
            "total_commission": 5000, "daily_commission": 5000 / 365,
            "total_slippage": 2000,  "daily_slippage": 2000 / 365,
            "total_turnover": 5_000_000, "daily_turnover": 5_000_000 / 365,
            "total_trade_count": total_trade_count,
            "daily_trade_count": total_trade_count / 365,
        }
    if status == TaskStatus.FAILED:
        result.error_msg = "mock error"
    return result


MOCK_RESULTS = [
    make_mock_result("000001.SZSE", total_return=15.0, sharpe=1.8,  max_ddpercent=-8.0,  total_trade_count=60),
    make_mock_result("600519.SSE",  total_return=25.0, sharpe=2.5,  max_ddpercent=-5.0,  total_trade_count=45),
    make_mock_result("300750.SZSE", total_return=-3.0, sharpe=-0.5, max_ddpercent=-12.0, total_trade_count=80),
    make_mock_result("000858.SZSE", total_return=8.0,  sharpe=1.1,  max_ddpercent=-6.5,  total_trade_count=35),
    make_mock_result("600036.SSE",  total_return=-5.0, sharpe=-0.8, max_ddpercent=-15.0, total_trade_count=70),
    make_mock_result("688001.SSE",  status=TaskStatus.FAILED),
    make_mock_result("301500.SZSE", status=TaskStatus.SKIPPED),
]


# ================================================================
# Metrics tests
# ================================================================

def test_calculate_win_rate():
    wr = calculate_win_rate(MOCK_RESULTS)
    assert abs(wr - 60.0) < 0.01, f"Expected 60.0, got {wr}"
    print(f"PASS  calculate_win_rate: {wr:.1f}%")


def test_calculate_avg_sharpe():
    valid = [r for r in MOCK_RESULTS if r.statistics]
    avg = calculate_avg_sharpe(valid)
    expected = sum([1.8, 2.5, -0.5, 1.1, -0.8]) / 5
    assert abs(avg - expected) < 1e-6
    print(f"PASS  calculate_avg_sharpe: {avg:.4f}")


def test_calculate_profit_loss_ratio():
    valid = [r for r in MOCK_RESULTS if r.statistics]
    plr = calculate_profit_loss_ratio(valid)
    assert plr > 0
    print(f"PASS  calculate_profit_loss_ratio: {plr:.4f}")


def test_calculate_calmar_ratio():
    valid = [r for r in MOCK_RESULTS if r.statistics]
    calmar = calculate_calmar_ratio(valid)
    assert not math.isnan(calmar) and not math.isinf(calmar)
    print(f"PASS  calculate_calmar_ratio: {calmar:.4f}")


def test_enrich_statistics():
    stats = {
        "annual_return": 20.0, "max_ddpercent": -10.0,
        "total_net_pnl": 200_000, "total_commission": 5_000, "total_slippage": 2_000,
    }
    enriched = enrich_statistics(stats)
    assert "calmar_ratio" in enriched and "profit_factor" in enriched
    assert abs(enriched["calmar_ratio"] - 2.0) < 1e-4
    assert enriched["profit_factor"] > 0
    print(f"PASS  enrich_statistics: calmar={enriched['calmar_ratio']:.4f}, "
          f"profit_factor={enriched['profit_factor']:.4f}")


def test_build_aggregate_summary():
    summary = build_aggregate_summary(MOCK_RESULTS)
    assert summary["agg_total_symbols"] == 7
    assert summary["agg_success_symbols"] == 5
    assert summary["agg_failed_symbols"] == 1
    assert summary["agg_skipped_symbols"] == 1
    assert 0 <= summary["agg_win_rate"] <= 100
    assert summary["agg_total_trades"] > 0
    print(f"PASS  build_aggregate_summary  win={summary['agg_win_rate']}%  "
          f"trades={summary['agg_total_trades']}")


# ================================================================
# StatisticsAnalyzer tests
# ================================================================

def test_analyzer_enrich():
    results = copy.deepcopy(MOCK_RESULTS)
    analyzer = StatisticsAnalyzer()
    returned = analyzer.enrich(results)
    assert returned is results
    for r in results:
        if r.statistics:
            assert "calmar_ratio" in r.statistics
            assert "profit_factor" in r.statistics
    print("PASS  StatisticsAnalyzer.enrich()")


def test_analyzer_summarize():
    analyzer = StatisticsAnalyzer()
    summary = analyzer.summarize(MOCK_RESULTS)
    assert "agg_total_symbols" in summary
    assert "agg_win_rate" in summary
    print(f"PASS  StatisticsAnalyzer.summarize()  win={summary['agg_win_rate']:.1f}%")


def test_analyzer_top_n():
    results = copy.deepcopy(MOCK_RESULTS)
    analyzer = StatisticsAnalyzer()
    top3 = analyzer.top_n(results, n=3, by="sharpe_ratio")
    assert len(top3) == 3
    sharpes = [r.sharpe_ratio for r in top3]
    assert sharpes == sorted(sharpes, reverse=True)
    assert top3[0].vt_symbol == "600519.SSE"
    print(f"PASS  StatisticsAnalyzer.top_n(3): {[r.vt_symbol for r in top3]}")


def test_analyzer_filters():
    results = copy.deepcopy(MOCK_RESULTS)
    analyzer = StatisticsAnalyzer()

    by_trades = analyzer.filter_by_min_trades(results, min_trades=50)
    assert all(r.total_trade_count >= 50 for r in by_trades)

    by_sharpe = analyzer.filter_by_min_sharpe(results, min_sharpe=1.0)
    assert all(r.sharpe_ratio >= 1.0 for r in by_sharpe)

    by_dd = analyzer.filter_by_max_drawdown(results, max_ddpercent=-10.0)
    assert all(r.max_ddpercent >= -10.0 for r in by_dd)

    print(f"PASS  StatisticsAnalyzer filters: "
          f"min_trades={len(by_trades)}, min_sharpe={len(by_sharpe)}, max_dd={len(by_dd)}")


def test_analyzer_to_dataframe():
    import pandas as pd
    results = copy.deepcopy(MOCK_RESULTS)
    analyzer = StatisticsAnalyzer()
    df = analyzer.to_dataframe(results)

    assert isinstance(df, pd.DataFrame)
    # to_dataframe includes ALL results (SUCCESS + FAILED + SKIPPED)
    assert len(df) == len(MOCK_RESULTS)
    assert "vt_symbol" in df.columns
    assert "calmar_ratio" in df.columns   # added by enrich=True
    # Success rows must be sorted descending by sharpe_ratio among themselves
    success_df = df[df["status"] == "success"]
    # FAILED/SKIPPED rows have sharpe=0.0 and may appear anywhere in the sort;
    # check only that success rows appear in descending sharpe order
    success_sharpes = success_df["sharpe_ratio"].tolist()
    assert success_sharpes == sorted(success_sharpes, reverse=True), (
        f"Success rows not sorted by sharpe: {success_sharpes}"
    )
    print(f"PASS  StatisticsAnalyzer.to_dataframe()  shape={df.shape}")


def test_analyzer_print_summary():
    results = copy.deepcopy(MOCK_RESULTS)
    StatisticsAnalyzer().print_summary(results, top_n=3)
    print("PASS  StatisticsAnalyzer.print_summary() smoke test")


# ================================================================
# CSVWriter tests
# ================================================================

def test_csv_writer_basic():
    import csv as _csv
    results = copy.deepcopy(MOCK_RESULTS)
    with tempfile.TemporaryDirectory() as tmpdir:
        fp = Path(tmpdir) / "results.csv"
        wr = CSVWriter().write(results, fp)
        assert fp.exists() and wr.rows_written == len(results) and wr.file_size_bytes > 0
        with open(fp, encoding="utf-8-sig") as f:
            rows = list(_csv.DictReader(f))
        data_rows = [r for r in rows if r.get("vt_symbol") != "__SUMMARY__"]
        assert len(data_rows) == len(results)
    print(f"PASS  CSVWriter basic  {wr}")


def test_csv_writer_column_order():
    import csv as _csv
    results = copy.deepcopy(MOCK_RESULTS[:3])
    with tempfile.TemporaryDirectory() as tmpdir:
        fp = Path(tmpdir) / "ordered.csv"
        CSVWriter().write(results, fp, include_summary_row=False)
        with open(fp, encoding="utf-8-sig") as f:
            header = list(_csv.DictReader(f).fieldnames or [])
        first_cols = [c for c in ORDERED_COLUMNS if c in header]
        assert header[:len(first_cols)] == first_cols
    print("PASS  CSVWriter column order")


def test_csv_writer_no_summary_row():
    import csv as _csv
    results = copy.deepcopy(MOCK_RESULTS[:3])
    with tempfile.TemporaryDirectory() as tmpdir:
        fp = Path(tmpdir) / "no_summary.csv"
        CSVWriter().write(results, fp, include_summary_row=False)
        with open(fp, encoding="utf-8-sig") as f:
            rows = list(_csv.DictReader(f))
        assert all(r.get("vt_symbol") != "__SUMMARY__" for r in rows)
        assert len(rows) == 3
    print("PASS  CSVWriter no summary row")


def test_csv_writer_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        fp = Path(tmpdir) / "empty.csv"
        wr = CSVWriter().write([], fp)
        assert wr.rows_written == 0 and fp.exists()
    print("PASS  CSVWriter empty results")


def test_csv_writer_creates_dirs():
    results = copy.deepcopy(MOCK_RESULTS[:2])
    with tempfile.TemporaryDirectory() as tmpdir:
        fp = Path(tmpdir) / "sub" / "deep" / "out.csv"
        CSVWriter().write(results, fp)
        assert fp.exists()
    print("PASS  CSVWriter creates parent dirs")


def test_csv_writer_calmar_enriched():
    import csv as _csv
    results = copy.deepcopy(MOCK_RESULTS[:3])
    with tempfile.TemporaryDirectory() as tmpdir:
        fp = Path(tmpdir) / "enriched.csv"
        CSVWriter().write(results, fp, enrich=True, include_summary_row=False)
        with open(fp, encoding="utf-8-sig") as f:
            header = list(_csv.DictReader(f).fieldnames or [])
        assert "calmar_ratio" in header
    print("PASS  CSVWriter calmar_ratio column present")


if __name__ == "__main__":
    print("=" * 65)
    print("Phase 7 Test Part 1: Metrics + Analyzer + CSVWriter")
    print("=" * 65)

    print("\n--- Metrics ---")
    test_calculate_win_rate()
    test_calculate_avg_sharpe()
    test_calculate_profit_loss_ratio()
    test_calculate_calmar_ratio()
    test_enrich_statistics()
    test_build_aggregate_summary()

    print("\n--- StatisticsAnalyzer ---")
    test_analyzer_enrich()
    test_analyzer_summarize()
    test_analyzer_top_n()
    test_analyzer_filters()
    test_analyzer_to_dataframe()
    test_analyzer_print_summary()

    print("\n--- CSVWriter ---")
    test_csv_writer_basic()
    test_csv_writer_column_order()
    test_csv_writer_no_summary_row()
    test_csv_writer_empty()
    test_csv_writer_creates_dirs()
    test_csv_writer_calmar_enriched()

    print()
    print("=" * 65)
    print("Phase 7 Part 1 ALL TESTS PASSED")
    print("=" * 65)
