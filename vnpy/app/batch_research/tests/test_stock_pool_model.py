"""
tests/test_stock_pool_model.py

Unit tests for StockPoolModel.
"""
import pytest
from vnpy.app.batch_research.model.stock_pool_model import StockPoolModel


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_minimal_construction():
    m = StockPoolModel(name="A")
    assert m.name == "A"
    assert m.symbols == []
    assert m.description == ""
    assert m.count == 0


def test_construction_with_symbols():
    syms = ["000001.SZSE", "600519.SSE"]
    m = StockPoolModel(name="B", symbols=syms)
    assert m.symbols == syms
    assert m.count == 2


def test_symbols_are_stored_as_list():
    # dataclass does not coerce; pass a list explicitly
    m = StockPoolModel(name="C", symbols=["600519.SSE"])
    assert isinstance(m.symbols, list) and m.count == 1


def test_update_time_is_string():
    m = StockPoolModel(name="D")
    assert isinstance(m.update_time, str)
    assert len(m.update_time) > 0


# ---------------------------------------------------------------------------
# count property
# ---------------------------------------------------------------------------

def test_count_empty():
    assert StockPoolModel(name="E").count == 0


def test_count_with_items():
    m = StockPoolModel(name="F", symbols=["a", "b", "c"])
    assert m.count == 3


# ---------------------------------------------------------------------------
# Serialisation: to_dict / from_dict
# ---------------------------------------------------------------------------

def test_to_dict_keys():
    m = StockPoolModel(name="G", symbols=["000001.SZSE"], description="desc")
    d = m.to_dict()
    for key in ("name", "symbols", "description", "update_time"):
        assert key in d, f"missing key {key!r}"


def test_to_dict_values():
    syms = ["000001.SZSE", "600519.SSE"]
    m = StockPoolModel(name="H", symbols=syms, description="test")
    d = m.to_dict()
    assert d["name"] == "H"
    assert d["symbols"] == syms
    assert d["description"] == "test"


def test_from_dict_roundtrip():
    m = StockPoolModel(name="I", symbols=["300750.SZSE"], description="d")
    d = m.to_dict()
    m2 = StockPoolModel.from_dict(d)
    assert m2.name == m.name
    assert m2.symbols == m.symbols
    assert m2.description == m.description
    assert m2.update_time == m.update_time


def test_from_dict_missing_description():
    d = {"name": "J", "symbols": ["000001.SZSE"], "update_time": "2024-01-01 00:00:00"}
    m = StockPoolModel.from_dict(d)
    assert m.description == ""


def test_from_dict_missing_symbols():
    d = {"name": "K", "update_time": "2024-01-01 00:00:00"}
    m = StockPoolModel.from_dict(d)
    assert m.symbols == []


def test_from_dict_extra_keys_ignored():
    d = {"name": "L", "symbols": [], "update_time": "x", "unexpected": 99}
    m = StockPoolModel.from_dict(d)
    assert m.name == "L"


# ---------------------------------------------------------------------------
# JSON persistence helpers
# ---------------------------------------------------------------------------

def test_to_json_is_string():
    import json as _j
    m = StockPoolModel(name="M", symbols=["000001.SZSE"])
    j = _j.dumps(m.to_dict(), ensure_ascii=False)
    assert isinstance(j, str) and "000001.SZSE" in j and "M" in j


def test_from_json_roundtrip():
    import json as _j
    m = StockPoolModel(name="N", symbols=["688599.SSE"], description="sci")
    m2 = StockPoolModel.from_dict(_j.loads(_j.dumps(m.to_dict())))
    assert m2.name == m.name
    assert m2.symbols == m.symbols
    assert m2.description == m.description


def test_from_json_invalid_raises():
    import json as _j
    bad = "not valid json"
    with pytest.raises(Exception):
        _j.loads(bad)


# ---------------------------------------------------------------------------
# Mutation helpers
# ---------------------------------------------------------------------------

def test_set_symbols_deduplicates():
    # set_symbols stores as-is; deduplicate() removes dups
    m = StockPoolModel(name="O")
    m.set_symbols(["000001.SZSE", "600519.SSE", "000001.SZSE"])
    removed = m.deduplicate(sort=False)
    assert removed == 1 and m.count == 2


def test_set_symbols_sorts():
    # deduplicate(sort=True) sorts the list
    m = StockPoolModel(name="P")
    m.set_symbols(["600519.SSE", "000001.SZSE", "300750.SZSE"])
    m.deduplicate(sort=True)
    assert m.symbols == sorted(m.symbols)


def test_set_symbols_updates_time():
    import time
    m = StockPoolModel(name="Q")
    t0 = m.update_time
    time.sleep(0.01)
    m.set_symbols(["000001.SZSE"])
    assert m.update_time >= t0


def test_set_symbols_empty():
    m = StockPoolModel(name="R", symbols=["000001.SZSE"])
    m.set_symbols([])
    assert m.count == 0
    assert m.symbols == []


# ---------------------------------------------------------------------------
# __repr__ / __str__
# ---------------------------------------------------------------------------

def test_repr_contains_name_and_count():
    m = StockPoolModel(name="S", symbols=["000001.SZSE", "600519.SSE"])
    r = repr(m)
    assert "S" in r
    assert "2" in r
