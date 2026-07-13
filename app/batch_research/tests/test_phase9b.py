"""Phase 9 test Part 2: IC/RankIC, layer analysis, correlation, report, integration"""

import math
import random
from datetime import datetime, timedelta

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy_ctastrategy.strategies.atr_rsi_strategy import AtrRsiStrategy

from vnpy.app.batch_research.task import BacktestResult, TaskStatus
from vnpy.app.batch_research.factor import (
    FactorEngine, ResultFactor,
    SharpeRatioFactor, TotalReturnFactor, CalmarRatioFactor,
    PriceMomentumFactor, VolatilityFactor, RSIFactor,
)


# ================================================================
# Helpers
# ================================================================

def make_mock_result(vt, ret=10.0, ann=5.0, sh=1.2, dd=-8.0, tc=50,
                     status=TaskStatus.SUCCESS):
    result = BacktestResult(vt_symbol=vt, task_id=f"t_{vt}",
                            strategy_name="T", status=status)
    if status == TaskStatus.SUCCESS:
        result.statistics = {
            "start_date": "2020-01-02", "end_date": "2021-06-30",
            "total_days": 365, "profit_days": 200, "loss_days": 165,
            "capital": 1_000_000,
            "end_balance": 1_000_000 * (1 + ret / 100),
            "total_return": ret, "annual_return": ann,
            "daily_return": ann / 240, "return_std": 1.5,
            "max_drawdown": dd * 10000, "max_ddpercent": dd,
            "max_drawdown_duration": 30, "sharpe_ratio": sh,
            "ewm_sharpe": sh * 0.9,
            "return_drawdown_ratio": abs(ret / dd) if dd else 0,
            "rgr_ratio": 1.5,
            "total_net_pnl": ret * 10000,
            "daily_net_pnl": ret * 10000 / 365,
            "total_commission": 5000, "daily_commission": 5000 / 365,
            "total_slippage": 2000, "daily_slippage": 2000 / 365,
            "total_turnover": 5_000_000, "daily_turnover": 5_000_000 / 365,
            "total_trade_count": tc, "daily_trade_count": tc / 365,
        }
    if status == TaskStatus.FAILED:
        result.error_msg = "mock error"
    return result


def make_bars(symbol="000001", n=300):
    rng = random.Random(hash(symbol) & 0xFFFF)
    bars, price, dt = [], 10.0, datetime(2020, 1, 2)
    for _ in range(n):
        while dt.weekday() >= 5:
            dt += timedelta(days=1)
        chg = rng.gauss(0, 0.015)
        o, c = price, round(max(0.1, price * (1 + chg)), 2)
        h = round(max(o, c) * (1 + abs(rng.gauss(0, 0.004))), 2)
        l = round(min(o, c) * (1 - abs(rng.gauss(0, 0.004))), 2)
        bars.append(BarData(gateway_name="CSV", symbol=symbol,
            exchange=Exchange.SZSE, datetime=dt, interval=Interval.DAILY,
            open_price=o, high_price=h, low_price=l, close_price=c,
            volume=float(rng.randint(500_000, 3_000_000))))
        price = c
        dt += timedelta(days=1)
    return bars


SYMBOLS = [
    ("000001.SZSE", 15.0, 1.8, -8.0,  60),
    ("600519.SSE",  25.0, 2.5, -5.0,  45),
    ("300750.SZSE", -3.0,-0.5,-12.0,  80),
    ("000858.SZSE",  8.0, 1.1, -6.5,  35),
    ("600036.SSE",  -5.0,-0.8,-15.0,  70),
    ("601318.SSE",  12.0, 1.4, -9.0,  55),
    ("600900.SSE",  20.0, 2.1, -4.0,  40),
    ("000333.SZSE",  6.0, 0.9, -7.5,  65),
    ("600028.SSE",  -8.0,-1.0,-18.0,  90),
    ("000002.SZSE", 18.0, 1.9, -6.0,  48),
]

MOCK_RESULTS = [make_mock_result(vt, ret, ret/2, sh, dd, tc)
                for vt, ret, sh, dd, tc in SYMBOLS]
BARS_MAP = {sym: make_bars(sym.split(".")[0], 300) for sym, *_ in SYMBOLS}


def std_engine(*factors):
    eng = FactorEngine()
    for f in factors:
        eng.register(f)
    df = eng.calculate(MOCK_RESULTS)
    return eng, df

# ================================================================
# IC / RankIC tests
# ================================================================

def test_ic_spearman():
    import pandas as pd
    eng, df = std_engine(SharpeRatioFactor(), TotalReturnFactor(), CalmarRatioFactor())
    ic = eng.cross_section_ic(df, return_col="total_return", method="spearman")
    assert isinstance(ic, pd.Series)
    val = ic["sharpe_ratio"]
    assert not math.isnan(val) and -1.0 <= val <= 1.0
    print(f"PASS  IC spearman  sharpe_IC={val:.4f}")


def test_ic_pearson():
    eng, df = std_engine(SharpeRatioFactor())
    ic = eng.cross_section_ic(df, return_col="total_return", method="pearson")
    val = ic["sharpe_ratio"]
    assert not math.isnan(val) and -1.0 <= val <= 1.0
    print(f"PASS  IC pearson  sharpe_IC={val:.4f}")


def test_rank_ic_alias():
    eng, df = std_engine(SharpeRatioFactor())
    s1 = eng.rank_ic(df)
    s2 = eng.cross_section_ic(df, method="spearman")
    assert abs(s1["sharpe_ratio"] - s2["sharpe_ratio"]) < 1e-9
    print("PASS  rank_ic() alias")


def test_ic_missing_col_raises():
    eng, df = std_engine(SharpeRatioFactor())
    try:
        eng.cross_section_ic(df, return_col="nonexistent")
        assert False
    except ValueError as e:
        assert "return_col" in str(e)
    print("PASS  IC raises for missing return_col")


def test_ic_all_finite():
    eng, df = std_engine(SharpeRatioFactor(), TotalReturnFactor(), CalmarRatioFactor())
    ic = eng.rank_ic(df, return_col="total_return")
    for name, val in ic.items():
        assert not math.isnan(val), f"{name}: NaN"
        assert -1 <= val <= 1, f"{name}: out of range {val}"
    print(f"PASS  IC finite for all factors  {ic.round(3).to_dict()}")


def test_ic_empty_when_no_factor_cols():
    import pandas as pd
    eng, df = std_engine(SharpeRatioFactor())
    df2 = df.drop(columns=["sharpe_ratio"])
    ic = eng.cross_section_ic(df2, return_col="total_return")
    assert isinstance(ic, pd.Series) and len(ic) == 0
    print("PASS  IC empty when factor col absent")


# ================================================================
# Layer analysis tests
# ================================================================

def test_layer_basic():
    import pandas as pd
    eng, df = std_engine(SharpeRatioFactor())
    ld = eng.layer_analysis(df, return_col="total_return",
                            n_layers=5, factor_col="sharpe_ratio")
    assert isinstance(ld, pd.DataFrame)
    assert len(ld) == 5
    assert sum(ld["count"]) == len(MOCK_RESULTS)
    print(f"PASS  layer_analysis(n=5)  layers={len(ld)}")


def test_layer_3():
    eng, df = std_engine(TotalReturnFactor())
    ld = eng.layer_analysis(df, return_col="sharpe_ratio",
                            n_layers=3, factor_col="total_return")
    assert len(ld) == 3
    print("PASS  layer_analysis(n=3)")


def test_layer_default_factor():
    eng, df = std_engine(SharpeRatioFactor(), TotalReturnFactor())
    ld = eng.layer_analysis(df, n_layers=3)
    assert len(ld) == 3
    print("PASS  layer_analysis default factor_col")


def test_layer_monotonic():
    eng, df = std_engine(SharpeRatioFactor())
    ld = eng.layer_analysis(df, return_col="total_return",
                            n_layers=5, factor_col="sharpe_ratio")
    returns = ld["mean_return"].tolist()
    assert returns[-1] >= returns[0], f"Not monotonic: {returns}"
    print(f"PASS  layer monotonic  returns={[round(r,1) for r in returns]}")


def test_layer_symbols_partition():
    eng, df = std_engine(SharpeRatioFactor())
    ld = eng.layer_analysis(df, n_layers=5, factor_col="sharpe_ratio")
    all_syms = []
    for _, row in ld.iterrows():
        all_syms.extend(row["symbols"])
    assert len(all_syms) == len(MOCK_RESULTS)
    assert len(set(all_syms)) == len(MOCK_RESULTS)
    print("PASS  layer symbols partition")


def test_layer_insufficient_rows_raises():
    eng, df = std_engine(SharpeRatioFactor())
    try:
        eng.layer_analysis(df.iloc[:2], n_layers=5)
        assert False
    except ValueError:
        pass
    print("PASS  layer raises for insufficient rows")


def test_layer_missing_col_raises():
    eng, df = std_engine(SharpeRatioFactor())
    try:
        eng.layer_analysis(df, factor_col="ghost_col")
        assert False
    except ValueError:
        pass
    print("PASS  layer raises for missing column")


# ================================================================
# Correlation matrix tests
# ================================================================

def test_corr_matrix():
    import pandas as pd
    eng = FactorEngine()
    for f in (SharpeRatioFactor(), TotalReturnFactor(), CalmarRatioFactor()):
        eng.register(f)
    df = eng.calculate(MOCK_RESULTS)
    corr = eng.correlation_matrix(df, method="spearman")
    assert isinstance(corr, pd.DataFrame)
    assert corr.shape == (3, 3)
    for name in eng.factor_names:
        assert abs(corr.loc[name, name] - 1.0) < 1e-9
    print(f"PASS  correlation_matrix  shape={corr.shape}")


def test_corr_matrix_empty():
    import pandas as pd
    eng, _ = std_engine(SharpeRatioFactor())
    df_no_factor = pd.DataFrame({"other": [1, 2]})
    corr = eng.correlation_matrix(df_no_factor)
    assert corr.empty
    print("PASS  corr_matrix empty when no factor cols")


# ================================================================
# report smoke test
# ================================================================

def test_report_smoke():
    eng = FactorEngine()
    for f in (SharpeRatioFactor(), TotalReturnFactor(), CalmarRatioFactor(),
              PriceMomentumFactor(60), VolatilityFactor(60)):
        eng.register(f)
    df = eng.calculate(MOCK_RESULTS, bars_map=BARS_MAP)
    eng.report(df, return_col="total_return", n_layers=5)
    print("\nPASS  report() smoke test")


# ================================================================
# Integration: BatchBacktestingEngine -> FactorEngine
# ================================================================

def test_integration():
    from vnpy.app.batch_research.batch_engine import BatchBacktestingEngine

    syms = list(BARS_MAP.keys())[:6]
    batch = BatchBacktestingEngine()
    batch.set_parameters(
        strategy_class=AtrRsiStrategy,
        start=datetime(2020, 1, 1), end=datetime(2021, 6, 30),
        capital=1_000_000, rate=1e-4, slippage=0.02,
        size=1.0, pricetick=0.01,
        strategy_setting={"atr_length": 22, "atr_ma_length": 10},
    )
    batch.set_stock_pool(syms)
    for vt in syms:
        batch.set_bars(vt, BARS_MAP[vt])
    results = batch.run_backtesting(show_progress=False)

    feng = FactorEngine()
    for f in (SharpeRatioFactor(), CalmarRatioFactor(), TotalReturnFactor(),
              PriceMomentumFactor(60), VolatilityFactor(60), RSIFactor(14)):
        feng.register(f)

    bm = {vt: BARS_MAP[vt] for vt in syms}
    df = feng.calculate(results, bars_map=bm)

    assert len(df) == len(syms)
    assert "sharpe_ratio" in df.columns
    assert "price_momentum_60b" in df.columns

    ic = feng.rank_ic(df)
    for val in ic.dropna():
        assert -1 <= val <= 1

    valid = df["sharpe_ratio"].notna().sum()
    if valid >= 3:
        ld = feng.layer_analysis(df, n_layers=3, factor_col="sharpe_ratio")
        assert len(ld) == 3

    corr = feng.correlation_matrix(df)
    assert not corr.empty

    feng.report(df, return_col="total_return", n_layers=3)
    print(f"\nPASS  integration  shape={df.shape}  IC={ic.round(3).to_dict()}")


# ================================================================
# Entry point
# ================================================================

if __name__ == "__main__":
    print("=" * 65)
    print("Phase 9 Test Part 2: IC + Layer + Corr + Report + Integration")
    print("=" * 65)

    print("\n--- IC / RankIC ---")
    test_ic_spearman()
    test_ic_pearson()
    test_rank_ic_alias()
    test_ic_missing_col_raises()
    test_ic_all_finite()
    test_ic_empty_when_no_factor_cols()

    print("\n--- Layer Analysis ---")
    test_layer_basic()
    test_layer_3()
    test_layer_default_factor()
    test_layer_monotonic()
    test_layer_symbols_partition()
    test_layer_insufficient_rows_raises()
    test_layer_missing_col_raises()

    print("\n--- Correlation Matrix ---")
    test_corr_matrix()
    test_corr_matrix_empty()

    print("\n--- Report ---")
    test_report_smoke()

    print("\n--- Integration ---")
    test_integration()

    print()
    print("=" * 65)
    print("Phase 9 Part 2 ALL TESTS PASSED")
    print("=" * 65)

