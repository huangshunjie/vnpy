"""
tests/test_stock_pool_manager.py

Unit tests for StockPoolManager — full CRUD + persistence.
"""
import json
import pytest
from pathlib import Path

from vnpy.app.batch_research.manager.stock_pool_manager import (
    StockPoolManager, ImportResult,
)
from vnpy.app.batch_research.model.stock_pool_model import StockPoolModel


@pytest.fixture
def mgr(tmp_path):
    m = StockPoolManager(pool_dir=tmp_path / "pools")
    for name in list(m.list_pools()):
        m.delete_pool(name)
    return m


@pytest.fixture
def mgr_with_pools(mgr):
    mgr.create_pool("Alpha", ["000001.SZSE", "600519.SSE"])
    mgr.create_pool("Beta",  ["300750.SZSE", "300015.SZSE"])
    mgr.create_pool("Gamma", ["688599.SSE", "688041.SSE", "688036.SSE"])
    return mgr


# ===========================================================================
# create_pool
# ===========================================================================

class TestCreatePool:
    def test_creates_and_returns_model(self, mgr):
        p = mgr.create_pool("X", ["000001.SZSE"])
        assert isinstance(p, StockPoolModel)
        assert p.name == "X"
        assert "000001.SZSE" in p.symbols

    def test_symbols_deduplicated(self, mgr):
        p = mgr.create_pool("Y", ["000001.SZSE", "600519.SSE", "000001.SZSE"])
        assert p.symbols.count("000001.SZSE") == 1

    def test_symbols_sorted(self, mgr):
        p = mgr.create_pool("Z", ["600519.SSE", "000001.SZSE", "300750.SZSE"])
        assert p.symbols == sorted(p.symbols)

    def test_empty_symbols_allowed(self, mgr):
        p = mgr.create_pool("Empty")
        assert p.count == 0

    def test_duplicate_name_raises(self, mgr):
        mgr.create_pool("Dup", ["000001.SZSE"])
        with pytest.raises(ValueError, match="已存在"):
            mgr.create_pool("Dup", ["600519.SSE"])

    def test_persisted_to_disk(self, mgr):
        mgr.create_pool("Persist", ["000001.SZSE"])
        json_file = mgr._pool_dir / "Persist.json"
        assert json_file.exists()
        data = json.loads(json_file.read_text(encoding="utf-8"))
        assert data["name"] == "Persist"

    def test_with_description(self, mgr):
        p = mgr.create_pool("Desc", ["000001.SZSE"], description="test desc")
        assert p.description == "test desc"

import json
import pytest
from vnpy.app.batch_research.manager.stock_pool_manager import StockPoolManager, ImportResult
from vnpy.app.batch_research.model.stock_pool_model import StockPoolModel

@pytest.fixture
def mgr(tmp_path):
    m = StockPoolManager(pool_dir=tmp_path / 'pools')
    for name in list(m.list_pools()):
        m.delete_pool(name)
    return m

@pytest.fixture
def mgr3(mgr):
    mgr.create_pool('Alpha', ['000001.SZSE', '600519.SSE'])
    mgr.create_pool('Beta',  ['300750.SZSE', '300015.SZSE'])
    mgr.create_pool('Gamma', ['688599.SSE', '688041.SSE', '688036.SSE'])
    return mgr

class TestCreatePool:
    def test_returns_model(self, mgr):
        p = mgr.create_pool('X', ['000001.SZSE'])
        assert isinstance(p, StockPoolModel) and 'X' == p.name
    def test_deduplicates(self, mgr):
        p = mgr.create_pool('Y', ['000001.SZSE', '600519.SSE', '000001.SZSE'])
        assert p.symbols.count('000001.SZSE') == 1
    def test_symbols_sorted(self, mgr):
        p = mgr.create_pool('Z', ['600519.SSE', '000001.SZSE'])
        assert p.symbols == sorted(p.symbols)
    def test_empty_allowed(self, mgr):
        assert mgr.create_pool('E').count == 0
    def test_duplicate_raises(self, mgr):
        mgr.create_pool('D', ['000001.SZSE'])
        with pytest.raises(ValueError): mgr.create_pool('D', [])
    def test_persisted(self, mgr):
        mgr.create_pool('P', ['000001.SZSE'])
        data = json.loads((mgr._pool_dir / 'P.json').read_text(encoding='utf-8'))
        assert data['name'] == 'P'
    def test_description(self, mgr):
        assert mgr.create_pool('D2', [], description='d').description == 'd'

class TestQuery:
    def test_get_pool(self, mgr3):
        assert mgr3.get_pool('Alpha').name == 'Alpha'
    def test_get_pool_missing(self, mgr3):
        assert mgr3.get_pool('Nope') is None
    def test_get_symbols_sorted(self, mgr3):
        s = mgr3.get_symbols('Alpha')
        assert s == sorted(s) and '000001.SZSE' in s
    def test_get_symbols_missing(self, mgr3):
        assert mgr3.get_symbols('Nope') == []
    def test_exists(self, mgr3):
        assert mgr3.exists('Alpha') and not mgr3.exists('Nope')
    def test_list_sorted(self, mgr3):
        names = mgr3.list_pools()
        assert names == sorted(names)
    def test_len(self, mgr3):   assert len(mgr3) == 3
    def test_iter(self, mgr3):
        # __iter__ yields StockPoolModel objects; extract names for comparison
        names = {item if isinstance(item, str) else item.name for item in mgr3}
        assert names == {'Alpha', 'Beta', 'Gamma'}

class TestUpdateSymbols:
    def test_replaces(self, mgr3):
        mgr3.update_symbols('Alpha', ['688599.SSE'])
        assert mgr3.get_pool('Alpha').symbols == ['688599.SSE']
    def test_deduplicates(self, mgr3):
        mgr3.update_symbols('Alpha', ['000001.SZSE', '000001.SZSE'])
        assert mgr3.get_pool('Alpha').count == 1
    def test_persists(self, mgr3):
        mgr3.update_symbols('Alpha', ['688599.SSE'])
        m2 = StockPoolManager(pool_dir=mgr3._pool_dir)
        assert m2.get_pool('Alpha').symbols == ['688599.SSE']
    def test_missing_raises(self, mgr3):
        with pytest.raises(KeyError): mgr3.update_symbols('Nope', [])

class TestDeletePool:
    def test_removes(self, mgr3):
        mgr3.delete_pool('Alpha'); assert not mgr3.exists('Alpha')
    def test_removes_file(self, mgr3):
        f = mgr3._pool_dir / 'Alpha.json'
        mgr3.delete_pool('Alpha'); assert not f.exists()
    def test_missing_silent(self, mgr3):
        mgr3.delete_pool('Nope')  # no raise
    def test_resets_current(self, mgr3):
        mgr3.set_current('Alpha'); mgr3.delete_pool('Alpha')
        assert mgr3.current_name == ''

class TestRenamePool:
    def test_renames(self, mgr3):
        mgr3.rename_pool('Alpha', 'A2')
        assert mgr3.exists('A2') and not mgr3.exists('Alpha')
    def test_symbols_preserved(self, mgr3):
        old = mgr3.get_symbols('Alpha')
        mgr3.rename_pool('Alpha', 'A2')
        assert mgr3.get_symbols('A2') == old
    def test_files_updated(self, mgr3):
        mgr3.rename_pool('Alpha', 'A2')
        assert not (mgr3._pool_dir / 'Alpha.json').exists()
        assert (mgr3._pool_dir / 'A2.json').exists()
    def test_missing_raises(self, mgr3):
        with pytest.raises(KeyError): mgr3.rename_pool('Nope', 'X')
    def test_target_exists_raises(self, mgr3):
        with pytest.raises(ValueError): mgr3.rename_pool('Alpha', 'Beta')
    def test_current_updated(self, mgr3):
        mgr3.set_current('Alpha'); mgr3.rename_pool('Alpha', 'A2')
        assert mgr3.current_name == 'A2'

class TestCopyPool:
    def test_creates_copy(self, mgr3):
        p = mgr3.copy_pool('Alpha', 'Copy')
        assert mgr3.exists('Copy') and p.symbols == mgr3.get_symbols('Alpha')
    def test_original_unchanged(self, mgr3):
        orig = list(mgr3.get_symbols('Alpha'))
        mgr3.copy_pool('Alpha', 'Copy')
        mgr3.update_symbols('Copy', ['688599.SSE'])
        assert mgr3.get_symbols('Alpha') == orig
    def test_source_missing_raises(self, mgr3):
        with pytest.raises(KeyError): mgr3.copy_pool('Nope', 'X')
    def test_target_exists_raises(self, mgr3):
        with pytest.raises(ValueError): mgr3.copy_pool('Alpha', 'Beta')

class TestCurrentPool:
    def test_set_returns_true(self, mgr3):
        assert mgr3.set_current('Alpha') is True
    def test_updates_name(self, mgr3):
        mgr3.set_current('Alpha'); assert mgr3.current_name == 'Alpha'
    def test_nonexistent_false(self, mgr3):
        assert mgr3.set_current('Nope') is False
    def test_empty_clears(self, mgr3):
        mgr3.set_current('Alpha'); mgr3.set_current('')
        assert mgr3.current_name == ''
    def test_get_current_symbols(self, mgr3):
        mgr3.set_current('Alpha')
        assert set(mgr3.get_current_symbols()) == {'000001.SZSE', '600519.SSE'}
    def test_no_selection_empty(self, mgr3):
        assert mgr3.get_current_symbols() == []

class TestImportFromText:
    def test_basic(self, mgr):
        p = mgr.import_from_text('T', '000001\n600519\n300750')
        assert p.count == 3 and '600519.SSE' in p.symbols
    def test_tushare(self, mgr):
        p = mgr.import_from_text('T', '000001.SZ\n600519.SH')
        assert '000001.SZSE' in p.symbols
    def test_overwrite(self, mgr):
        mgr.import_from_text('T', '000001\n600519')
        assert mgr.import_from_text('T', '300750', overwrite=True).count == 1
    def test_no_overwrite_raises(self, mgr):
        mgr.import_from_text('T', '000001')
        with pytest.raises(ValueError): mgr.import_from_text('T', '600519')

class TestImportFromFile:
    def test_plain_csv(self, mgr, tmp_path):
        f = tmp_path / 'a.csv'; f.write_text('000001\n600519\n300750\n', encoding='utf-8')
        assert mgr.import_from_file('F', f).count == 3
    def test_with_header(self, mgr, tmp_path):
        f = tmp_path / 'b.csv'; f.write_text('code,name\n000001,AB\n600519,CD\n', encoding='utf-8')
        assert mgr.import_from_file('G', f).count == 2
    def test_gbk(self, mgr, tmp_path):
        f = tmp_path / 'c.csv'; f.write_bytes('000001\n300750\n'.encode('gbk'))
        assert '000001.SZSE' in mgr.import_from_file('H', f).symbols
    def test_not_found_raises(self, mgr, tmp_path):
        with pytest.raises(FileNotFoundError): mgr.import_from_file('X', tmp_path / 'nope.csv')
    def test_preview_type(self, mgr, tmp_path):
        f = tmp_path / 'd.csv'; f.write_text('000001\ngarbage\n600519\n', encoding='utf-8')
        ir = mgr.import_from_file_with_preview('P', f)
        assert isinstance(ir, ImportResult) and ir.imported_count == 2 and ir.skipped_rows == 1
    def test_preview_overwrite_flag(self, mgr, tmp_path):
        f = tmp_path / 'e.csv'; f.write_text('000001\n600519\n', encoding='utf-8')
        mgr.import_from_file_with_preview('Q', f)
        assert mgr.import_from_file_with_preview('Q', f, overwrite=True).overwritten is True
    def test_preview_summary(self, mgr, tmp_path):
        f = tmp_path / 'f.csv'; f.write_text('000001\n600519\n', encoding='utf-8')
        assert isinstance(mgr.import_from_file_with_preview('R', f).summary(), str)

class TestExportToFile:
    def test_exports_count(self, mgr3, tmp_path):
        out = tmp_path / 'out.csv'
        n = mgr3.export_to_file('Alpha', out)
        assert n == mgr3.get_pool('Alpha').count
        assert len(out.read_text(encoding='utf-8-sig').strip().splitlines()) == n
    def test_vt_symbol_format(self, mgr3, tmp_path):
        out = tmp_path / 'out2.csv'; mgr3.export_to_file('Alpha', out)
        for line in out.read_text(encoding='utf-8-sig').strip().splitlines():
            assert '.' in line
    def test_missing_raises(self, mgr, tmp_path):
        with pytest.raises(KeyError): mgr.export_to_file('Nope', tmp_path / 'out.csv')

class TestPersistence:
    def test_reload(self, tmp_path):
        d = tmp_path / 'pools'
        m1 = StockPoolManager(pool_dir=d)
        for n in list(m1.list_pools()): m1.delete_pool(n)
        m1.create_pool('A', ['000001.SZSE', '600519.SSE'])
        m2 = StockPoolManager(pool_dir=d)
        assert m2.exists('A') and set(m2.get_symbols('A')) == {'000001.SZSE','600519.SSE'}
    def test_reload_after_delete(self, tmp_path):
        d = tmp_path / 'pools'
        m1 = StockPoolManager(pool_dir=d)
        for n in list(m1.list_pools()): m1.delete_pool(n)
        m1.create_pool('X', ['000001.SZSE']); m1.delete_pool('X')
        assert not StockPoolManager(pool_dir=d).exists('X')
    def test_corrupt_json_skipped(self, tmp_path):
        d = tmp_path / 'pools'; d.mkdir(parents=True)
        (d / 'bad.json').write_text('{{not json', encoding='utf-8')
        assert not StockPoolManager(pool_dir=d).exists('bad')

def test_repr(mgr3):
    r = repr(mgr3)
    assert 'StockPoolManager' in r and '3' in r
