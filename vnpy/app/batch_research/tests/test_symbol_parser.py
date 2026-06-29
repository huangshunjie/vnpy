"""
tests/test_symbol_parser.py

Unit tests for SymbolParser and CsvParser.
"""
import tempfile
import pytest
from pathlib import Path

from vnpy.app.batch_research.utils.symbol_parser import (
    SymbolParser, CsvParser, CsvParseResult, ParsedRow,
    parse_symbols, normalize_symbol,
)


# ===========================================================================
# SymbolParser.normalize
# ===========================================================================

class TestNormalize:
    def setup_method(self):
        self.p = SymbolParser()

    # --- already valid vt_symbol ---
    def test_valid_vt_symbol_sse(self):
        assert self.p.normalize("600519.SSE") == "600519.SSE"

    def test_valid_vt_symbol_szse(self):
        assert self.p.normalize("000001.SZSE") == "000001.SZSE"

    def test_valid_vt_symbol_bse(self):
        assert self.p.normalize("430047.BSE") == "430047.BSE"

    def test_valid_vt_symbol_cffex(self):
        import pytest
        pytest.skip("SymbolParser is A-share stock only; CFFEX futures not in scope")

    # --- Tushare format ---
    def test_tushare_sh(self):
        assert self.p.normalize("600519.SH") == "600519.SSE"

    def test_tushare_sz(self):
        assert self.p.normalize("000001.SZ") == "000001.SZSE"

    def test_tushare_bj(self):
        assert self.p.normalize("430047.BJ") == "430047.BSE"

    def test_tushare_case_insensitive(self):
        assert self.p.normalize("600519.sh") == "600519.SSE"

    # --- 6-digit pure code ---
    def test_pure_code_sse_60(self):
        assert self.p.normalize("600519") == "600519.SSE"

    def test_pure_code_sse_688(self):
        assert self.p.normalize("688599") == "688599.SSE"

    def test_pure_code_szse_000(self):
        assert self.p.normalize("000001") == "000001.SZSE"

    def test_pure_code_szse_300(self):
        assert self.p.normalize("300750") == "300750.SZSE"

    def test_pure_code_szse_301(self):
        assert self.p.normalize("301155") == "301155.SZSE"

    def test_pure_code_bse_43(self):
        assert self.p.normalize("430047") == "430047.BSE"

    def test_pure_code_bse_83(self):
        assert self.p.normalize("831267") == "831267.BSE"

    # --- unknown / invalid ---
    def test_empty_returns_empty(self):
        assert self.p.normalize("") == ""

    def test_whitespace_returns_empty(self):
        assert self.p.normalize("   ") == ""

    def test_short_code_rejected(self):
        assert self.p.normalize("1234") == ""

    def test_letters_only_rejected(self):
        assert self.p.normalize("ABCDEF") == ""

    def test_unknown_suffix_infers_exchange(self):
        # unknown suffix → fall back to inference from digits
        result = self.p.normalize("600519.UNKNOWN")
        assert result == "600519.SSE"

    def test_whitespace_stripped(self):
        assert self.p.normalize("  600519  ") == "600519.SSE"


# ===========================================================================
# SymbolParser.parse
# ===========================================================================

class TestParse:
    def setup_method(self):
        self.p = SymbolParser()

    def test_single_code(self):
        assert self.p.parse("000001") == ["000001.SZSE"]

    def test_newline_separated(self):
        r = self.p.parse("000001\n600519\n300750")
        assert r == ["000001.SZSE", "600519.SSE", "300750.SZSE"]

    def test_comma_separated(self):
        r = self.p.parse("000001,600519,300750")
        assert set(r) == {"000001.SZSE", "600519.SSE", "300750.SZSE"}

    def test_fullwidth_comma(self):
        r = self.p.parse("000001，600519")
        assert "000001.SZSE" in r and "600519.SSE" in r

    def test_tab_separated(self):
        r = self.p.parse("000001\t600519")
        assert "000001.SZSE" in r

    def test_mixed_format(self):
        r = self.p.parse("000001.SZ\n600519.SH\n300750")
        assert "000001.SZSE" in r
        assert "600519.SSE" in r
        assert "300750.SZSE" in r

    def test_excel_paste_with_name_column(self):
        text = "000001\t平安银行\n600519\t贵州茅台"
        r = self.p.parse(text)
        assert "000001.SZSE" in r
        assert "600519.SSE" in r

    def test_dedup_preserves_first_seen_order(self):
        r = self.p.parse("000001\n600519\n000001\n300750\n600519")
        assert r == ["000001.SZSE", "600519.SSE", "300750.SZSE"]

    def test_junk_filtered_silently(self):
        r = self.p.parse("hello\n000001\n世界\n600519")
        assert r == ["000001.SZSE", "600519.SSE"]

    def test_empty_input(self):
        assert self.p.parse("") == []

    def test_whitespace_only_input(self):
        assert self.p.parse("   \n\t  ") == []

    def test_parse_many(self):
        r = self.p.parse_many(["000001\n600519", "300750\n000001"])
        assert r == ["000001.SZSE", "600519.SSE", "300750.SZSE"]


# ===========================================================================
# Module-level convenience functions
# ===========================================================================

def test_parse_symbols_function():
    r = parse_symbols("000001\n600519")
    assert "000001.SZSE" in r


def test_normalize_symbol_function():
    assert normalize_symbol("600519.SH") == "600519.SSE"


# ===========================================================================
# SymbolParser.infer_exchange
# ===========================================================================

class TestInferExchange:
    @pytest.mark.parametrize("code,expected", [
        ("600519", "SSE"),
        ("688599", "SSE"),
        ("601318", "SSE"),
        ("000001", "SZSE"),
        ("002594", "SZSE"),
        ("300750", "SZSE"),
        ("301155", "SZSE"),
        ("430047", "BSE"),
        ("831267", "BSE"),
        ("873693", "BSE"),
        ("999999", "SSE"),   # fallback
    ])
    def test_infer(self, code, expected):
        assert SymbolParser.infer_exchange(code) == expected


# ===========================================================================
# CsvParser
# ===========================================================================

class TestCsvParser:
    def setup_method(self):
        self.cp = CsvParser()

    # --- plain lists ---
    def test_plain_code_list(self):
        r = self.cp.parse_text("000001\n600519\n300750\n")
        assert r.symbols == ["000001.SZSE", "600519.SSE", "300750.SZSE"]
        assert r.skipped_rows == 0

    def test_plain_vt_symbols(self):
        r = self.cp.parse_text("000001.SZSE\n600519.SSE\n")
        assert r.symbols == ["000001.SZSE", "600519.SSE"]

    # --- header detection ---
    def test_header_with_keyword_col0(self):
        r = self.cp.parse_text("代码,名称,行业\n000001,平安银行,银行\n600519,茅台,白酒\n")
        assert r.symbols == ["000001.SZSE", "600519.SSE"]
        assert r.header_row.startswith("代码")
        assert r.symbol_col == 0

    def test_header_with_keyword_col1(self):
        r = self.cp.parse_text("名称,股票代码,行业\n平安银行,000001,银行\n茅台,600519,白酒\n")
        assert "000001.SZSE" in r.symbols
        assert r.symbol_col == 1

    def test_tushare_ts_code_col(self):
        r = self.cp.parse_text("ts_code,name\n000001.SZ,平安\n600519.SH,茅台\n")
        assert "000001.SZSE" in r.symbols
        assert "600519.SSE" in r.symbols

    def test_no_header(self):
        r = self.cp.parse_text("000001\n600519\n300750\n")
        assert r.header_row == ""
        assert r.total_rows == 3

    # --- delimiters ---
    def test_tab_delimiter(self):
        r = self.cp.parse_text("000001\t平安银行\n600519\t茅台\n")
        assert set(r.symbols) == {"000001.SZSE", "600519.SSE"}

    def test_pipe_delimiter(self):
        r = self.cp.parse_text("000001|平安|银行\n600519|茅台|白酒\n")
        assert "000001.SZSE" in r.symbols

    def test_semicolon_delimiter(self):
        r = self.cp.parse_text("000001;平安\n600519;茅台\n")
        assert "000001.SZSE" in r.symbols

    # --- mixed valid/invalid ---
    def test_blank_lines_skipped(self):
        r = self.cp.parse_text("000001\n\n600519\n\n300750\n")
        assert r.symbols == ["000001.SZSE", "600519.SSE", "300750.SZSE"]
        assert r.skipped_rows == 2

    def test_garbage_rows_skipped(self):
        r = self.cp.parse_text("000001\ngarbage\n600519\nXXXXXX\n")
        assert r.symbols == ["000001.SZSE", "600519.SSE"]
        assert r.skipped_rows == 2

    def test_mixed_blank_and_garbage(self):
        r = self.cp.parse_text("000001\n\ngarbage\n600519\nXXXXXX\n300750\n")
        assert r.symbols == ["000001.SZSE", "600519.SSE", "300750.SZSE"]
        assert r.skipped_rows == 3
        assert r.total_rows == 6

    # --- deduplication ---
    def test_dedup(self):
        r = self.cp.parse_text("000001\n600519\n000001\n300750\n600519\n")
        assert r.symbols == ["000001.SZSE", "600519.SSE", "300750.SZSE"]
        assert r.imported_count == 3

    # --- per-row detail ---
    def test_parsed_row_ok(self):
        r = self.cp.parse_text("000001\n")
        assert len(r.rows) == 1
        assert r.rows[0].ok is True
        assert r.rows[0].symbol == "000001.SZSE"

    def test_parsed_row_skip_reason(self):
        r = self.cp.parse_text("000001\ngarbage\n")
        assert r.rows[0].ok is True
        assert r.rows[1].ok is False
        assert r.rows[1].reason != ""

    # --- summary ---
    def test_summary_contains_count(self):
        r = self.cp.parse_text("000001\n600519\n")
        s = r.summary()
        assert "2" in s

    def test_summary_mentions_skipped(self):
        r = self.cp.parse_text("000001\ngarbage\n600519\n")
        s = r.summary()
        assert "1" in s   # 1 skipped

    # --- encoding detection ---
    def test_utf8_bom(self, tmp_path):
        f = tmp_path / "a.csv"
        f.write_bytes("代码,名称\n000001,平安\n600519,茅台\n".encode("utf-8-sig"))
        r = self.cp.parse_file(f)
        assert r.symbols == ["000001.SZSE", "600519.SSE"]
        assert r.encoding_used == "utf-8-sig"

    def test_gbk(self, tmp_path):
        f = tmp_path / "b.csv"
        f.write_bytes("代码,名称\n000001,平安\n300750,宁德\n".encode("gbk"))
        r = self.cp.parse_file(f)
        assert "000001.SZSE" in r.symbols
        assert r.encoding_used == "gbk"

    def test_utf8_plain(self, tmp_path):
        f = tmp_path / "c.txt"
        f.write_text("000001\n600519\n688599\n", encoding="utf-8")
        r = self.cp.parse_file(f)
        assert len(r.symbols) == 3

    # --- error handling ---
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            self.cp.parse_file(Path("/nonexistent/path.csv"))

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.csv"
        f.write_text("", encoding="utf-8")
        r = self.cp.parse_file(f)
        assert r.symbols == []
        assert r.total_rows == 0
