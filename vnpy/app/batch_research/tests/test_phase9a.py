"""Phase 9 test Part 1: FactorTemplate + built-in factors + FactorEngine basics"""

import math
import random
from datetime import datetime, timedelta

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData

from vnpy.app.batch_research.task import BacktestResult, TaskStatus
from vnpy.app.batch_research.factor import (
    FactorEngine, FactorTemplate, ResultFactor, BarFactor,
    SharpeRatioFactor, TotalReturnFactor, AnnualReturnFactor,
    MaxDrawdownFactor, CalmarRatioFactor, ReturnDrawdownRatioFactor,
    EwmSharpeFactor, ProfitFactorFactor,
    PriceMomentumFactor, VolatilityFactor, RSIFactor,
    TradingFrequencyFactor,
)


# ================================================================
# Helpers
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
        strategy_name="Test",
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
            "return_drawdown_ratio": abs(total_return / max_ddpercent) if max_ddpercent else 0.0,
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


def make_bars(symbol: str = "000001", n: int = 300) -> list[BarData]:
    rng = random.Random(hash(symbol) & 0xFFFF)
    bars: list[BarData] = []
    price = 10.0
    dt = datetime(2020, 1, 2)
    for _ in range(n):
        while dt.weekday() >= 5:
            dt += timedelta(days=1)
        chg = rng.gauss(0, 0.015)
        o = price
        c = round(max(0.1, price * (1 + chg)), 2)
        h = round(max(o, c) * (1 + abs(rng.gauss(0, 0.004))), 2)
        l = round(min(o, c) * (1 - abs(rng.gauss(0, 0.004))), 2)
        bars.append(BarData(
            gateway_name="CSV", symbol=symbol,
            exchange=Exchange.SZSE, datetime=dt,
            interval=Interval.DAILY,
            open_price=o, high_price=h, low_price=l, close_price=c,
            volume=float(rng.randint(500_000, 3_000_000)),
        ))
        price = c
        dt += timedelta(days=1)
    return bars


SYMBOLS = [
    ("000001.SZSE", 15.0,  1.8,  -8.0,  60),
    ("600519.SSE",  25.0,  2.5,  -5.0,  45),
    ("300750.SZSE", -3.0,  -0.5, -12.0, 80),
    ("000858.SZSE", 8.0,   1.1,  -6.5,  35),
    ("600036.SSE",  -5.0,  -0.8, -15.0, 70),
    ("601318.SSE",  12.0,  1.4,  -9.0,  55),
    ("600900.SSE",  20.0,  2.1,  -4.0,  40),
    ("000333.SZSE", 6.0,   0.9,  -7.5,  65),
    ("600028.SSE",  -8.0,  -1.0, -18.0, 90),
    ("000002.SZSE", 18.0,  1.9,  -6.0,  48),
]

MOCK_RESULTS = [
    make_mock_result(vt, ret, ret / 2, sh, dd, tc)
    for vt, ret, sh, dd, tc in SYMBOLS
]

BARS_MAP = {sym: make_bars(sym.split(".")[0], 300) for sym, *_ in SYMBOLS}


# ================================================================
# FactorTemplate
# ================================================================

def test_factor_template_abstract():
    try:
        FactorTemplate()
        assert False, "should raise"
    except TypeError:
        pass
    print("PASS  FactorTemplate is abstract")


def test_custom_result_factor():
    class MyFactor(ResultFactor):
        factor_name = "test_x2"
        def _extract(self, r): return r.total_return * 2

    series = MyFactor().calculate(MOCK_RESULTS)
    assert series.name == "test_x2"
    assert len(series) == len([r for r in MOCK_RESULTS if r.statistics])
    for r in MOCK_RESULTS:
        if r.statistics:
            assert abs(series[r.vt_symbol] - r.total_return * 2) < 1e-9
    print(f"PASS  custom ResultFactor  n={len(series)}")


def test_custom_bar_factor():
    class LastClose(BarFactor):
        factor_name = "last_close"
        def _compute_for_symbol(self, vt, bars):
            return bars[-1].close_price if bars else None

    series = LastClose().calculate(MOCK_RESULTS, bars_map=BARS_MAP)
    assert len(series) == len(MOCK_RESULTS)
    assert all(v > 0 for v in series)
    print(f"PASS  custom BarFactor  n={len(series)}")


def test_failed_skipped_excluded_from_result_factor():
    results = MOCK_RESULTS + [
        make_mock_result("fail.SSE", status=TaskStatus.FAILED),
        make_mock_result("skip.SSE", status=TaskStatus.SKIPPED),
    ]
    series = SharpeRatioFactor().calculate(results)
    assert "fail.SSE" not in series.index
    assert "skip.SSE" not in series.index
    print(f"PASS  FAILED/SKIPPED excluded from ResultFactor  n={len(series)}")


# ================================================================
# Built-in ResultFactors
# ================================================================

def test_builtin_result_factors():
    factors = [
        SharpeRatioFactor(), TotalReturnFactor(), AnnualReturnFactor(),
        MaxDrawdownFactor(), CalmarRatioFactor(), ReturnDrawdownRatioFactor(),
        EwmSharpeFactor(), TradingFrequencyFactor(),
    ]
    for f in factors:
        series = f.calculate(MOCK_RESULTS)
        assert len(series) > 0, f"{f.factor_name}: empty"
        assert series.name == f.factor_name
        assert all(not math.isnan(v) and not math.isinf(v) for v in series)
        print(f"  OK  {f.factor_name:<32}  n={len(series)}")
    print("PASS  all built-in ResultFactors")


def test_calmar_excludes_zero_dd():
    results = [make_mock_result("zero.SSE", max_ddpercent=0.0)]
    series = CalmarRatioFactor().calculate(results)
    assert "zero.SSE" not in series.index
    print("PASS  CalmarRatioFactor excludes zero drawdown")


# ================================================================
# Built-in BarFactors
# ================================================================

def test_price_momentum():
    f = PriceMomentumFactor(60)
    assert f.factor_name == "price_momentum_60b"
    series = f.calculate(MOCK_RESULTS, bars_map=BARS_MAP)
    assert len(series) == len(MOCK_RESULTS)
    assert all(not math.isnan(v) and not math.isinf(v) for v in series)
    print(f"PASS  PriceMomentumFactor(60)  n={len(series)}")


def test_volatility():
    f = VolatilityFactor(60)
    assert f.factor_name == "volatility_60b"
    series = f.calculate(MOCK_RESULTS, bars_map=BARS_MAP)
    assert len(series) == len(MOCK_RESULTS)
    assert all(v > 0 for v in series)
    print(f"PASS  VolatilityFactor(60)  n={len(series)}")


def test_rsi():
    f = RSIFactor(14)
    assert f.factor_name == "rsi_14"
    series = f.calculate(MOCK_RESULTS, bars_map=BARS_MAP)
    assert len(series) == len(MOCK_RESULTS)
    assert all(0 <= v <= 100 for v in series)
    print(f"PASS  RSIFactor(14)  n={len(series)}")


def test_bar_factor_skips_missing():
    partial = {k: v for k, v in list(BARS_MAP.items())[:3]}
    series = PriceMomentumFactor(60).calculate(MOCK_RESULTS, bars_map=partial)
    assert len(series) == 3
    print(f"PASS  BarFactor skips missing bars_map  n={len(series)}")


def test_bar_factor_insufficient_bars():
    short = {sym: make_bars(sym.split(".")[0], 30) for sym, *_ in SYMBOLS}
    series = PriceMomentumFactor(60).calculate(MOCK_RESULTS, bars_map=short)
    assert len(series) == 0
    print("PASS  BarFactor omits symbols with insufficient bars")


# ================================================================
# FactorEngine: registration & calculate
# ================================================================

def test_engine_register():
    eng = FactorEngine()
    assert len(eng) == 0
    eng.register(SharpeRatioFactor())
    eng.register(CalmarRatioFactor())
    assert len(eng) == 2
    assert "sharpe_ratio" in eng.factor_names
    assert "FactorEngine" in repr(eng)
    print(f"PASS  register  {repr(eng)}")


def test_engine_register_overwrites():
    eng = FactorEngine()
    eng.register(SharpeRatioFactor())
    eng.register(SharpeRatioFactor())
    assert len(eng) == 1
    print("PASS  register overwrites duplicate name")


def test_engine_register_empty_name_raises():
    eng = FactorEngine()
    class NoName(ResultFactor):
        factor_name = ""
        def _extract(self, r): return 0.0
    try:
        eng.register(NoName())
        assert False
    except ValueError:
        pass
    print("PASS  register raises for empty factor_name")


def test_engine_unregister():
    eng = FactorEngine()
    eng.register(SharpeRatioFactor())
    eng.register(CalmarRatioFactor())
    eng.unregister("sharpe_ratio")
    assert "sharpe_ratio" not in eng.factor_names
    assert len(eng) == 1
    print("PASS  unregister")


def test_engine_calculate_no_factors_raises():
    try:
        FactorEngine().calculate(MOCK_RESULTS)
        assert False
    except RuntimeError as e:
        assert "register" in str(e).lower()
    print("PASS  calculate() raises without factors")


def test_engine_calculate_basic():
    import pandas as pd
    eng = FactorEngine()
    eng.register(SharpeRatioFactor())
    eng.register(TotalReturnFactor())
    eng.register(CalmarRatioFactor())
    df = eng.calculate(MOCK_RESULTS)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == len(MOCK_RESULTS)
    for col in ("sharpe_ratio", "calmar_ratio", "status",
                "total_return", "max_ddpercent"):
        assert col in df.columns, f"missing: {col}"
    print(f"PASS  calculate() basic  shape={df.shape}")


def test_engine_calculate_with_bar_factors():
    eng = FactorEngine()
    eng.register(SharpeRatioFactor())
    eng.register(PriceMomentumFactor(60))
    eng.register(VolatilityFactor(60))
    eng.register(RSIFactor(14))
    df = eng.calculate(MOCK_RESULTS, bars_map=BARS_MAP)
    assert df["price_momentum_60b"].notna().sum() == len(MOCK_RESULTS)
    assert "rsi_14" in df.columns
    print(f"PASS  calculate() with BarFactors  shape={df.shape}")


def test_engine_failed_skipped_as_null():
    results = MOCK_RESULTS + [
        make_mock_result("fail.SSE", status=TaskStatus.FAILED),
        make_mock_result("skip.SSE", status=TaskStatus.SKIPPED),
    ]
    eng = FactorEngine()
    # Use CalmarRatioFactor — it is NOT a metadata column, so it appears
    # as a real factor column.  FAILED/SKIPPED have no statistics, so
    # their CalmarRatio slot must be NaN.
    eng.register(CalmarRatioFactor())
    df = eng.calculate(results)
    assert len(df) == len(results)
    assert "calmar_ratio" in df.columns
    assert math.isnan(df.loc["fail.SSE", "calmar_ratio"])
    assert math.isnan(df.loc["skip.SSE", "calmar_ratio"])
    # sharpe_ratio comes from metadata (BacktestResult.sharpe_ratio default=0.0)
    # so it is 0.0 for FAILED/SKIPPED, not NaN — that is expected behaviour.
    assert df.loc["fail.SSE", "sharpe_ratio"] == 0.0
    print("PASS  FAILED/SKIPPED rows: factor cols NaN, metadata cols default 0")


if __name__ == "__main__":
    print("=" * 65)
    print("Phase 9 Test Part 1: FactorTemplate + built-ins + Engine basics")
    print("=" * 65)

    print("\n--- FactorTemplate ---")
    test_factor_template_abstract()
    test_custom_result_factor()
    test_custom_bar_factor()
    test_failed_skipped_excluded_from_result_factor()

    print("\n--- Built-in ResultFactors ---")
    test_builtin_result_factors()
    test_calmar_excludes_zero_dd()

    print("\n--- Built-in BarFactors ---")
    test_price_momentum()
    test_volatility()
    test_rsi()
    test_bar_factor_skips_missing()
    test_bar_factor_insufficient_bars()

    print("\n--- FactorEngine ---")
    test_engine_register()
    test_engine_register_overwrites()
    test_engine_register_empty_name_raises()
    test_engine_unregister()
    test_engine_calculate_no_factors_raises()
    test_engine_calculate_basic()
    test_engine_calculate_with_bar_factors()
    test_engine_failed_skipped_as_null()

    print()
    print("=" * 65)
    print("Phase 9 Part 1 ALL TESTS PASSED")
    print("=" * 65)
