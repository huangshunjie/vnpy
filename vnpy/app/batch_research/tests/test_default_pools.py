"""
tests/test_default_pools.py

Unit tests for default_pools module and _seed_defaults behaviour.
"""
import pytest
from pathlib import Path

from vnpy.app.batch_research.manager.default_pools import (
    DefaultPoolDef, get_default_pool_defs,
    OnlineUpdater, DEFAULT_UPDATER,
)
from vnpy.app.batch_research.manager.stock_pool_manager import StockPoolManager


# ===========================================================================
# DefaultPoolDef
# ===========================================================================

class TestDefaultPoolDef:
    def test_count(self):
        defs = get_default_pool_defs()
        assert len(defs) == 3

    def test_all_are_dataclass(self):
        for d in get_default_pool_defs():
            assert isinstance(d, DefaultPoolDef)

    def test_names_unique(self):
        names = [d.name for d in get_default_pool_defs()]
        assert len(names) == len(set(names))

    def test_names_start_with_example_prefix(self):
        for d in get_default_pool_defs():
            assert d.name.startswith("示例："), f"bad name: {d.name!r}"

    def test_each_has_ten_symbols(self):
        for d in get_default_pool_defs():
            assert len(d.symbols) >= 10, f"{d.name} only has {len(d.symbols)}"

    def test_all_symbols_are_vt_symbol(self):
        for d in get_default_pool_defs():
            for sym in d.symbols:
                assert "." in sym, f"not vt_symbol: {sym!r} in {d.name}"

    def test_has_description(self):
        for d in get_default_pool_defs():
            assert isinstance(d.description, str) and len(d.description) > 0

    def test_frozen_immutable(self):
        d = get_default_pool_defs()[0]
        with pytest.raises((AttributeError, TypeError)):
            d.name = "changed"   # type: ignore

    def test_get_default_pool_defs_returns_copy(self):
        d1 = get_default_pool_defs()
        d2 = get_default_pool_defs()
        assert d1 is not d2   # new list each call


# ===========================================================================
# _seed_defaults (via StockPoolManager)
# ===========================================================================

class TestSeedDefaults:
    def test_seeds_on_first_init(self, tmp_path):
        mgr = StockPoolManager(pool_dir=tmp_path / "pools")
        names = mgr.list_pools()
        expected = {d.name for d in get_default_pool_defs()}
        assert expected.issubset(set(names))

    def test_seeds_correct_symbol_counts(self, tmp_path):
        mgr = StockPoolManager(pool_dir=tmp_path / "pools")
        for d in get_default_pool_defs():
            pool = mgr.get_pool(d.name)
            assert pool is not None
            assert pool.count == len(d.symbols), (
                f"{d.name}: expected {len(d.symbols)}, got {pool.count}"
            )

    def test_seeds_correct_descriptions(self, tmp_path):
        mgr = StockPoolManager(pool_dir=tmp_path / "pools")
        for d in get_default_pool_defs():
            pool = mgr.get_pool(d.name)
            assert pool.description == d.description

    def test_idempotent_does_not_overwrite_user_edit(self, tmp_path):
        pool_dir = tmp_path / "pools"
        mgr = StockPoolManager(pool_dir=pool_dir)
        first = get_default_pool_defs()[0].name
        mgr.update_symbols(first, ["000001.SZSE", "600519.SSE"])
        assert mgr.get_pool(first).count == 2

        # re-init (simulates restart)
        mgr2 = StockPoolManager(pool_dir=pool_dir)
        assert mgr2.get_pool(first).count == 2, \
            "_seed_defaults must not overwrite user edits"

    def test_deleted_pool_re_seeded_on_restart(self, tmp_path):
        pool_dir = tmp_path / "pools"
        mgr = StockPoolManager(pool_dir=pool_dir)
        first = get_default_pool_defs()[0].name
        mgr.delete_pool(first)
        assert not mgr.exists(first)

        mgr2 = StockPoolManager(pool_dir=pool_dir)
        assert mgr2.exists(first), \
            "deleted default pool must be re-seeded on next startup"

    def test_user_pools_coexist(self, tmp_path):
        mgr = StockPoolManager(pool_dir=tmp_path / "pools")
        mgr.create_pool("MyPool", ["000001.SZSE"])
        n_default = len(get_default_pool_defs())
        assert len(mgr) == n_default + 1
        assert mgr.exists("MyPool")


# ===========================================================================
# OnlineUpdater Protocol
# ===========================================================================

class TestOnlineUpdaterProtocol:
    def test_stub_satisfies_protocol(self):
        assert isinstance(DEFAULT_UPDATER, OnlineUpdater)

    def test_stub_fetch_returns_empty(self):
        result = DEFAULT_UPDATER.fetch("anything")
        assert result == []

    def test_stub_supported_pools_empty(self):
        assert DEFAULT_UPDATER.supported_pools() == []

    def test_custom_class_satisfies_protocol(self):
        class MyUpdater:
            def fetch(self, pool_name: str) -> list:
                return ["000001.SZSE"]
            def supported_pools(self) -> list:
                return ["A"]
        assert isinstance(MyUpdater(), OnlineUpdater)

    def test_incomplete_class_fails_check(self):
        class Incomplete:
            def fetch(self, name: str) -> list:
                return []
            # missing supported_pools
        assert not isinstance(Incomplete(), OnlineUpdater)


# ===========================================================================
# set_updater + refresh_pool_online
# ===========================================================================

class TestRefreshPoolOnline:
    def _make_mgr(self, tmp_path):
        mgr = StockPoolManager(pool_dir=tmp_path / "pools")
        return mgr

    def test_stub_updater_leaves_pool_unchanged(self, tmp_path):
        mgr = self._make_mgr(tmp_path)
        first = get_default_pool_defs()[0].name
        original_count = mgr.get_pool(first).count
        pool = mgr.refresh_pool_online(first)
        assert pool.count == original_count

    def test_mock_updater_refreshes_symbols(self, tmp_path):
        class MockUpdater:
            def fetch(self, name): return ["000001.SZSE", "600519.SSE", "300750.SZSE"]
            def supported_pools(self): return ["any"]

        mgr = self._make_mgr(tmp_path)
        mgr.set_updater(MockUpdater())
        first = get_default_pool_defs()[0].name
        pool = mgr.refresh_pool_online(first)
        assert pool.count == 3
        assert "600519.SSE" in pool.symbols

    def test_create_if_missing_true(self, tmp_path):
        class MockUpdater:
            def fetch(self, name): return ["000001.SZSE", "600519.SSE"]
            def supported_pools(self): return ["NewPool"]

        mgr = self._make_mgr(tmp_path)
        mgr.set_updater(MockUpdater())
        pool = mgr.refresh_pool_online("NewPool", create_if_missing=True)
        assert pool.count == 2
        assert mgr.exists("NewPool")

    def test_create_if_missing_false_raises(self, tmp_path):
        class MockUpdater:
            def fetch(self, name): return ["000001.SZSE"]
            def supported_pools(self): return ["any"]

        mgr = self._make_mgr(tmp_path)
        mgr.set_updater(MockUpdater())
        with pytest.raises((KeyError, RuntimeError)):
            mgr.refresh_pool_online("NonExistentPool", create_if_missing=False)
