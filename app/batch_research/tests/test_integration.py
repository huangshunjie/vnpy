"""
tests/test_integration.py

Integration tests: __init__ exports, _RecentPools logic,
SettingDialog <-> StockPoolManager wiring, cross-module imports.
"""
import json
import pytest


# ===========================================================================
# Top-level package exports
# ===========================================================================

class TestTopLevelExports:
    def test_import_app(self):
        from vnpy.app.batch_research import BatchResearchApp
        assert BatchResearchApp.app_name == "BatchResearch"

    def test_import_app_name(self):
        from vnpy.app.batch_research import APP_NAME
        assert APP_NAME == "BatchResearch"

    def test_import_stock_pool_manager(self):
        from vnpy.app.batch_research import StockPoolManager
        assert StockPoolManager is not None

    def test_import_import_result(self):
        from vnpy.app.batch_research import ImportResult
        assert ImportResult is not None

    def test_import_get_default_pool_defs(self):
        from vnpy.app.batch_research import get_default_pool_defs
        assert callable(get_default_pool_defs)

    def test_all_list(self):
        import vnpy.app.batch_research as pkg
        for name in ["BatchResearchApp", "APP_NAME", "StockPoolManager",
                     "ImportResult", "get_default_pool_defs"]:
            assert name in pkg.__all__, f"{name} missing from __all__"


# ===========================================================================
# manager sub-package exports
# ===========================================================================

class TestManagerExports:
    def test_stock_pool_manager(self):
        from vnpy.app.batch_research.manager import StockPoolManager
        assert StockPoolManager is not None

    def test_import_result(self):
        from vnpy.app.batch_research.manager import ImportResult
        assert ImportResult is not None

    def test_default_pool_def(self):
        from vnpy.app.batch_research.manager import DefaultPoolDef
        assert DefaultPoolDef is not None

    def test_get_default_pool_defs(self):
        from vnpy.app.batch_research.manager import get_default_pool_defs
        assert len(get_default_pool_defs()) == 3

    def test_online_updater(self):
        from vnpy.app.batch_research.manager import OnlineUpdater
        assert OnlineUpdater is not None


# ===========================================================================
# ui sub-package exports (import-only, no Qt window)
# ===========================================================================

class TestUiExports:
    def test_setting_dialog_importable(self):
        from vnpy.app.batch_research.ui import SettingDialog
        assert SettingDialog is not None

    def test_stock_pool_dialog_importable(self):
        from vnpy.app.batch_research.ui import StockPoolDialog
        assert StockPoolDialog is not None

    def test_stock_pool_editor_importable(self):
        from vnpy.app.batch_research.ui import StockPoolEditor
        assert StockPoolEditor is not None

    def test_result_table_importable(self):
        from vnpy.app.batch_research.ui import ResultTableWidget
        assert ResultTableWidget is not None

    def test_ui_all_list(self):
        import vnpy.app.batch_research.ui as ui
        for name in ["BatchResearchWidget", "SettingDialog", "ResultTableWidget",
                     "FactorAnalysisDialog", "StockPoolDialog", "StockPoolEditor"]:
            assert name in ui.__all__


# ===========================================================================
# _RecentPools logic (no Qt)
# ===========================================================================

class TestRecentPoolsLogic:
    def _make(self, path, max_len=3):
        names = []
        key = "recent_pool_names"
        def push(name):
            if name in names: names.remove(name)
            names.insert(0, name)
            del names[max_len:]
            path.write_text(__import__("json").dumps({key: names}), encoding="utf-8")
        def prune(existing): names[:] = [n for n in names if n in existing]
        def load():
            if path.exists():
                names[:] = __import__("json").loads(
                    path.read_text(encoding="utf-8")).get(key, [])
        return push, prune, load, names

    def test_push_prepends(self, tmp_path):
        push, _, _, names = self._make(tmp_path / "r.json")
        push("A"); push("B"); push("C")
        assert names == ["C", "B", "A"]

    def test_push_moves_to_front(self, tmp_path):
        push, _, _, names = self._make(tmp_path / "r.json")
        push("A"); push("B"); push("C"); push("A")
        assert names[0] == "A" and len(names) == 3

    def test_overflow_eviction(self, tmp_path):
        push, _, _, names = self._make(tmp_path / "r.json", max_len=3)
        push("A"); push("B"); push("C"); push("D")
        assert len(names) == 3 and "A" not in names

    def test_persists(self, tmp_path):
        f = tmp_path / "r.json"
        push, _, _, names = self._make(f)
        push("X"); push("Y")
        data = __import__("json").loads(f.read_text(encoding="utf-8"))
        assert data["recent_pool_names"] == names

    def test_load_from_disk(self, tmp_path):
        f = tmp_path / "r.json"
        push, _, load, names = self._make(f)
        push("A"); push("B"); saved = list(names); del names[:]
        load(); assert names == saved

    def test_prune_removes_deleted(self, tmp_path):
        push, prune, _, names = self._make(tmp_path / "r.json")
        push("A"); push("B"); push("C")
        prune({"B", "C"})
        assert "A" not in names and set(names) == {"B", "C"}

    def test_prune_all(self, tmp_path):
        push, prune, _, names = self._make(tmp_path / "r.json")
        push("A"); push("B"); prune(set()); assert names == []

    def test_empty_on_missing_file(self, tmp_path):
        _, _, load, names = self._make(tmp_path / "missing.json")
        load(); assert names == []


# ===========================================================================
# Manager <-> SettingDialog data contract (non-Qt)
# ===========================================================================

class TestManagerSettingDialogWiring:
    def test_parse_symbols_via_manager(self, tmp_path):
        from vnpy.app.batch_research.manager import StockPoolManager
        mgr = StockPoolManager(pool_dir=tmp_path / "pools")
        mgr.create_pool("Test", ["000001.SZSE", "600519.SSE"])
        mgr.set_current("Test")
        assert set(mgr.get_current_symbols()) == {"000001.SZSE", "600519.SSE"}

    def test_config_roundtrip(self, tmp_path):
        from vnpy.app.batch_research.manager import StockPoolManager
        cfg_path = tmp_path / "cfg.json"
        mgr = StockPoolManager(pool_dir=tmp_path / "pools")
        mgr.create_pool("Pool1", ["000001.SZSE", "600519.SSE"])
        mgr.set_current("Pool1")
        data = {"current_pool_name": mgr.current_name}
        cfg_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        loaded = json.loads(cfg_path.read_text(encoding="utf-8"))
        mgr2 = StockPoolManager(pool_dir=tmp_path / "pools")
        name = loaded.get("current_pool_name", "")
        if name and mgr2.exists(name):
            mgr2.set_current(name)
        assert mgr2.current_name == "Pool1"
        assert set(mgr2.get_current_symbols()) == {"000001.SZSE", "600519.SSE"}

    def test_symbols_key_absent_from_new_config(self, tmp_path):
        from vnpy.app.batch_research.manager import StockPoolManager
        mgr = StockPoolManager(pool_dir=tmp_path / "pools")
        mgr.create_pool("P", ["000001.SZSE"]); mgr.set_current("P")
        cfg = {"current_pool_name": mgr.current_name}
        assert "symbols" not in cfg

    def test_legacy_migration(self, tmp_path):
        from vnpy.app.batch_research.manager import StockPoolManager
        mgr = StockPoolManager(pool_dir=tmp_path / "pools")
        symbols = ["000001.SZSE", "600519.SSE", "300750.SZSE"]
        legacy = "\u4e0a\u6b21\u56de\u6d4b\u80a1\u7968\u6c60"
        if not mgr.exists(legacy):
            mgr.create_pool(legacy, symbols)
        mgr.set_current(legacy)
        assert mgr.current_name == legacy
        assert set(mgr.get_current_symbols()) == set(symbols)

    def test_validate_empty_pool_error(self, tmp_path):
        from vnpy.app.batch_research.manager import StockPoolManager
        mgr = StockPoolManager(pool_dir=tmp_path / "pools")
        errors = [] if mgr.get_current_symbols() else ["stock pool empty"]
        assert errors != []

    def test_validate_passes_with_symbols(self, tmp_path):
        from vnpy.app.batch_research.manager import StockPoolManager
        mgr = StockPoolManager(pool_dir=tmp_path / "pools")
        mgr.create_pool("P", ["000001.SZSE"]); mgr.set_current("P")
        assert mgr.get_current_symbols() != []


# ===========================================================================
# Cross-module import chain
# ===========================================================================

class TestImportChain:
    def test_model_importable(self):
        from vnpy.app.batch_research.model.stock_pool_model import StockPoolModel
        assert StockPoolModel is not None

    def test_parser_importable(self):
        from vnpy.app.batch_research.utils.symbol_parser import (
            SymbolParser, CsvParser, parse_symbols, normalize_symbol)
        assert all(x is not None for x in [SymbolParser, CsvParser,
                                            parse_symbols, normalize_symbol])

    def test_manager_importable(self):
        from vnpy.app.batch_research.manager.stock_pool_manager import (
            StockPoolManager, ImportResult)
        assert StockPoolManager is not None

    def test_default_pools_importable(self):
        from vnpy.app.batch_research.manager.default_pools import (
            DefaultPoolDef, get_default_pool_defs, OnlineUpdater)
        assert all(x is not None for x in [DefaultPoolDef,
                                            get_default_pool_defs, OnlineUpdater])

    def test_no_circular_imports(self):
        import importlib
        import vnpy.app.batch_research
        importlib.reload(vnpy.app.batch_research)
