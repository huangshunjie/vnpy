"""Phase 10 test Part 1b: UI widgets (headless Qt)"""
import os, sys
from datetime import datetime
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from vnpy.event import EventEngine
from vnpy.trader.ui import QtWidgets
_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)


class _FakeMainEngine:
    def __init__(self, ee):
        self._engines = {}
    def get_engine(self, name): return None
    def write_log(self, msg, source=""): pass


def _make_table():
    from vnpy.app.batch_research.ui.result_table import ResultTableWidget
    ee = EventEngine()
    me = _FakeMainEngine(ee)
    return ResultTableWidget(me, ee), ee


# ================================================================
# SettingDialog tests
# ================================================================

def test_setting_dialog_instantiates():
    from vnpy.app.batch_research.ui import SettingDialog
    dlg = SettingDialog()
    assert dlg.windowTitle() == "批量回测配置"
    assert dlg.minimumWidth() >= 400
    print("PASS  SettingDialog instantiates")


def test_setting_dialog_config_keys():
    from vnpy.app.batch_research.ui import SettingDialog
    dlg = SettingDialog()
    dlg._pool_edit.setPlainText("000001.SZSE\n600519.SSE")
    dlg._end_edit.setDate(dlg._start_edit.date().addDays(365))
    cfg = dlg.get_config()
    assert cfg["symbols"] == ["000001.SZSE", "600519.SSE"]
    for key in ("start", "end", "capital", "rate", "slippage", "size", "pricetick"):
        assert key in cfg["parameters"]
    assert "use_multiprocess" in cfg and "max_workers" in cfg
    print(f"PASS  SettingDialog.get_config()  symbols={cfg['symbols']}")


def test_setting_dialog_roundtrip():
    from vnpy.app.batch_research.ui import SettingDialog
    dlg = SettingDialog()
    cfg_in = {
        "parameters": {
            "start": datetime(2021, 1, 1), "end": datetime(2022, 12, 31),
            "capital": 500_000, "rate": 2e-4, "slippage": 0.05,
            "size": 100.0, "pricetick": 0.01,
            "strategy_setting": {"atr_length": 22},
        },
        "symbols": ["000001.SZSE", "600519.SSE", "300750.SZSE"],
        "use_multiprocess": True,
        "max_workers": 8,
    }
    dlg.set_config(cfg_in)
    cfg_out = dlg.get_config()
    assert cfg_out["symbols"] == cfg_in["symbols"]
    assert cfg_out["use_multiprocess"] is True
    assert cfg_out["max_workers"] == 8
    assert cfg_out["parameters"]["capital"] == 500_000
    print("PASS  SettingDialog roundtrip")


def test_setting_dialog_validation():
    from vnpy.app.batch_research.ui import SettingDialog
    dlg = SettingDialog()
    # Empty pool
    dlg._pool_edit.setPlainText("")
    errors = dlg._validate()
    assert any("股票池" in e for e in errors)
    # Date order
    dlg._pool_edit.setPlainText("000001.SZSE")
    dlg._end_edit.setDate(dlg._start_edit.date().addDays(-1))
    errors = dlg._validate()
    assert any("日期" in e for e in errors)
    print("PASS  SettingDialog validation")


def test_setting_dialog_strategy_setting_parse():
    from vnpy.app.batch_research.ui import SettingDialog
    dlg = SettingDialog()
    dlg._pool_edit.setPlainText("000001.SZSE")
    dlg._end_edit.setDate(dlg._start_edit.date().addDays(365))
    dlg._setting_edit.setPlainText("atr_length=22\natr_ma_length=10\nlabel=foo")
    cfg = dlg.get_config()
    s = cfg["parameters"]["strategy_setting"]
    assert s["atr_length"] == 22
    assert s["atr_ma_length"] == 10
    assert s["label"] == "foo"
    print("PASS  SettingDialog strategy_setting parse")


# ================================================================
# FactorAnalysisDialog
# ================================================================

def _make_results(n=5):
    from vnpy.app.batch_research.task import BacktestResult, TaskStatus
    results = []
    for i in range(n):
        r = BacktestResult(vt_symbol=f"SYM{i:02d}.SZSE", task_id=f"t{i}",
                           strategy_name="T", status=TaskStatus.SUCCESS)
        ret = (i - 2) * 5.0
        r.statistics = {
            "total_return": ret, "annual_return": ret/2,
            "sharpe_ratio": ret/10, "max_ddpercent": -8.0,
            "return_drawdown_ratio": abs(ret/8) if ret else 0,
            "ewm_sharpe": ret/11, "total_trade_count": 50,
            "daily_trade_count": 50/240, "total_days": 365,
            "profit_days": 200, "loss_days": 165, "capital": 1_000_000,
            "end_balance": 1_000_000*(1+ret/100), "daily_return": 0.02,
            "return_std": 1.5, "max_drawdown": ret*10000,
            "max_drawdown_duration": 30, "rgr_ratio": 1.5,
            "total_net_pnl": ret*10000, "daily_net_pnl": ret*10000/365,
            "total_commission": 5000, "daily_commission": 5000/365,
            "total_slippage": 2000, "daily_slippage": 2000/365,
            "total_turnover": 5_000_000, "daily_turnover": 5_000_000/365,
        }
        results.append(r)
    return results


def test_factor_dialog_instantiates():
    from vnpy.app.batch_research.ui import FactorAnalysisDialog
    dlg = FactorAnalysisDialog(results=[], bars_map={})
    assert dlg.windowTitle() == "多因子截面分析"
    assert dlg.minimumWidth() >= 800
    print("PASS  FactorAnalysisDialog instantiates")


def test_factor_dialog_with_results():
    from vnpy.app.batch_research.ui import FactorAnalysisDialog
    results = _make_results(5)
    dlg = FactorAnalysisDialog(results=results, bars_map={})
    assert "5" in dlg._status_label.text()
    print("PASS  FactorAnalysisDialog with 5 results")


def test_factor_dialog_run_analysis():
    """Clicking 'run analysis' with valid results must not raise."""
    from vnpy.app.batch_research.ui import FactorAnalysisDialog
    results = _make_results(10)
    dlg = FactorAnalysisDialog(results=results, bars_map={})
    dlg._do_analysis()
    assert dlg._ic_table.rowCount() > 0
    print(f"PASS  FactorAnalysisDialog._do_analysis()  "
          f"IC rows={dlg._ic_table.rowCount()}")


# ================================================================
# ResultTableWidget
# ================================================================

def test_result_table_instantiates():
    w, _ = _make_table()
    assert w.columnCount() > 0
    assert w.rowCount() == 0
    print("PASS  ResultTableWidget instantiates")


def test_result_table_insert_and_clear():
    from vnpy.app.batch_research.task import BacktestResult, TaskStatus
    w, _ = _make_table()
    r = BacktestResult(vt_symbol="000001.SZSE", task_id="t",
                       strategy_name="T", status=TaskStatus.SUCCESS)
    r.statistics = {"total_return": 10.0, "annual_return": 5.0,
                    "sharpe_ratio": 1.2, "max_ddpercent": -8.0,
                    "total_trade_count": 50}
    w._insert_row(r)
    assert w.rowCount() == 1
    assert len(w.get_results()) == 1
    w.clear_results()
    assert w.rowCount() == 0
    print("PASS  ResultTableWidget insert + clear")


def test_result_table_row_colors():
    from vnpy.app.batch_research.task import BacktestResult, TaskStatus
    from vnpy.app.batch_research.ui.result_table import (
        COLOR_SUCCESS, COLOR_FAILED, COLOR_SKIPPED
    )
    w, _ = _make_table()

    for sym, status in [("A.SZSE", TaskStatus.SUCCESS),
                        ("B.SZSE", TaskStatus.FAILED),
                        ("C.SZSE", TaskStatus.SKIPPED)]:
        r = BacktestResult(vt_symbol=sym, task_id="t",
                           strategy_name="T", status=status)
        if status == TaskStatus.SUCCESS:
            r.statistics = {"total_return": 5.0, "annual_return": 2.5,
                            "sharpe_ratio": 1.0, "max_ddpercent": -5.0,
                            "total_trade_count": 30}
        elif status == TaskStatus.FAILED:
            r.error_msg = "e"
        w._insert_row(r)

    assert w.item(0, 0).background().color() == COLOR_SUCCESS
    assert w.item(1, 0).background().color() == COLOR_FAILED
    assert w.item(2, 0).background().color() == COLOR_SKIPPED
    print("PASS  ResultTableWidget row colors")


def test_result_table_sortable_item():
    """_SortableItem sorts numerically."""
    from vnpy.app.batch_research.ui.result_table import _SortableItem
    a = _SortableItem("1.5", 1.5)
    b = _SortableItem("2.3", 2.3)
    c = _SortableItem("-0.5", -0.5)
    assert a < b
    assert c < a
    assert not (b < a)
    print("PASS  _SortableItem numeric sort")


if __name__ == "__main__":
    print("=" * 55)
    print("Phase 10b: UI widgets (headless Qt)")
    print("=" * 55)

    print("\n--- SettingDialog ---")
    test_setting_dialog_instantiates()
    test_setting_dialog_config_keys()
    test_setting_dialog_roundtrip()
    test_setting_dialog_validation()
    test_setting_dialog_strategy_setting_parse()

    print("\n--- FactorAnalysisDialog ---")
    test_factor_dialog_instantiates()
    test_factor_dialog_with_results()
    test_factor_dialog_run_analysis()

    print("\n--- ResultTableWidget ---")
    test_result_table_instantiates()
    test_result_table_insert_and_clear()
    test_result_table_row_colors()
    test_result_table_sortable_item()

    print("\nPhase 10b ALL PASSED")
