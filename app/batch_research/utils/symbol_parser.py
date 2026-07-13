"""
utils/symbol_parser.py

SymbolParser — 股票代码解析与标准化工具。

职责：
  - 接受任意格式的输入文本（手动输入、Excel 粘贴、CSV、同花顺、Tushare 等）
  - 清洗、拆分、标准化为统一的 vt_symbol 列表（例如 "000001.SZSE"）
  - 自动推断交易所后缀
  - 去重（保持首次出现顺序）

不负责：
  - 网络查询
  - 文件 I/O
  - UI

交易所推断规则（A 股）：
  60xxxx / 68xxxx / 689xxx  → SSE   （沪市主板 / 科创板）
  00xxxx / 002xxx / 003xxx  → SZSE  （深市主板 / 中小板）
  300xxx / 301xxx           → SZSE  （创业板）
  43xxxx / 83xxxx / 87xxxx  → BSE   （北交所）
  其余 6 位数字             → SSE   （保守兜底）
"""

from __future__ import annotations

import re
from typing import Sequence


# ── 交易所推断表（前缀 → 交易所），顺序从长到短保证优先匹配 ──
_PREFIX_EXCHANGE: list[tuple[str, str]] = [
    ("689", "SSE"),   # 科创板 CDR
    ("688", "SSE"),   # 科创板
    ("687", "SSE"),   # 科创板
    ("60",  "SSE"),   # 沪市主板
    ("301", "SZSE"),  # 创业板注册制
    ("300", "SZSE"),  # 创业板
    ("003", "SZSE"),  # 深市中小板
    ("002", "SZSE"),  # 深市中小板
    ("001", "SZSE"),  # 深市主板
    ("000", "SZSE"),  # 深市主板
    ("83",  "BSE"),   # 北交所
    ("87",  "BSE"),   # 北交所
    ("43",  "BSE"),   # 北交所
]

# 合法 vt_symbol 后缀白名单
_VALID_EXCHANGES = {"SSE", "SZSE", "BSE", "CFFEX", "SHFE", "DCE", "CZCE", "GFEX"}

# 纯数字股票代码（A 股 6 位）
_RE_PURE_CODE = re.compile(r"^\d{6}$")

# 已带后缀的 vt_symbol，例如 000001.SZSE 或 600519.SSE
_RE_VT_SYMBOL = re.compile(r"^(\d{6})\.([\w]+)$", re.IGNORECASE)

# Tushare 格式：000001.SZ / 600519.SH
_RE_TUSHARE = re.compile(r"^(\d{6})\.(SH|SZ|BJ)$", re.IGNORECASE)

_TUSHARE_MAP = {"SH": "SSE", "SZ": "SZSE", "BJ": "BSE"}

# 分隔符：逗号（全/半角）、分号、Tab、一个或多个空格
_RE_SEP = re.compile(r"[,，;\t\s]+")


class SymbolParser:
    """
    股票代码解析器。

    用法::

        parser = SymbolParser()

        # 单行或多行输入
        symbols = parser.parse("000001\\n600519\\n300750.SZSE")

        # Excel / CSV 粘贴
        symbols = parser.parse("000001\\t平安银行\\n600519\\t贵州茅台")

        # Tushare 格式
        symbols = parser.parse("000001.SZ, 600519.SH")

    返回值均为去重后的 vt_symbol 列表，保持首次出现顺序。
    """

    def parse(self, text: str) -> list[str]:
        """
        解析任意格式输入文本，返回去重 vt_symbol 列表。

        :param text: 原始输入，支持多行、逗号/Tab/空格分隔。
        :return:     去重后的 vt_symbol 列表（保持首次出现顺序）。
        """
        if not text or not text.strip():
            return []

        candidates: list[str] = []
        for line in text.splitlines():
            # 按分隔符拆分每行，取每个 token
            for token in _RE_SEP.split(line):
                token = token.strip()
                if token:
                    candidates.append(token)

        result: list[str] = []
        seen: set[str] = set()
        for token in candidates:
            vt = self.normalize(token)
            if vt and vt not in seen:
                seen.add(vt)
                result.append(vt)

        return result

    def parse_many(self, texts: Sequence[str]) -> list[str]:
        """
        解析多段文本，合并去重后返回。

        :param texts: 文本列表。
        :return:      去重 vt_symbol 列表。
        """
        combined = "\n".join(texts)
        return self.parse(combined)

    def normalize(self, token: str) -> str:
        """
        将单个 token 转换为标准 vt_symbol。

        识别顺序：
          1. 标准 vt_symbol（000001.SZSE）→ 校验后缀合法性后直接返回
          2. Tushare 格式（000001.SZ）→ 转换后缀
          3. 6 位纯数字 → 推断交易所
          4. 其他 → 返回空字符串（调用方过滤）

        :param token: 单个待处理字符串。
        :return:      标准 vt_symbol，无法识别时返回空字符串。
        """
        token = token.strip()
        if not token:
            return ""

        # 1. 标准 vt_symbol
        m = _RE_VT_SYMBOL.match(token)
        if m:
            symbol   = m.group(1)
            exchange = m.group(2).upper()
            if exchange in _VALID_EXCHANGES:
                return f"{symbol}.{exchange}"
            # 后缀非法时，忽略后缀重新推断
            return f"{symbol}.{self.infer_exchange(symbol)}"

        # 2. Tushare 格式（000001.SZ）
        m = _RE_TUSHARE.match(token)
        if m:
            symbol   = m.group(1)
            exchange = _TUSHARE_MAP[m.group(2).upper()]
            return f"{symbol}.{exchange}"

        # 3. 6 位纯数字
        if _RE_PURE_CODE.match(token):
            return f"{token}.{self.infer_exchange(token)}"

        # 4. 无法识别
        return ""

    @staticmethod
    def infer_exchange(symbol: str) -> str:
        """
        根据股票代码前缀推断 A 股交易所。

        :param symbol: 6 位纯数字代码。
        :return:       "SSE" / "SZSE" / "BSE"，无法匹配时默认 "SSE"。
        """
        for prefix, exchange in _PREFIX_EXCHANGE:
            if symbol.startswith(prefix):
                return exchange
        return "SSE"


# 模块级单例，方便直接调用
_default_parser = SymbolParser()


def parse_symbols(text: str) -> list[str]:
    """
    模块级便捷函数：解析文本，返回 vt_symbol 列表。

    等价于 SymbolParser().parse(text)。
    """
    return _default_parser.parse(text)


def normalize_symbol(token: str) -> str:
    """
    模块级便捷函数：标准化单个 token。

    等价于 SymbolParser().normalize(token)。
    """
    return _default_parser.normalize(token)


# ---------------------------------------------------------------------------
# CsvParser -- multi-column CSV / TXT file importer
# ---------------------------------------------------------------------------

_SYMBOL_HEADER_KEYWORDS = (
    "代码", "股票代码", "证券代码", "股票码",
    "symbol", "code", "ticker", "ts_code", "seccode", "stockcode",
)
_ENCODINGS = ("utf-8-sig", "utf-8", "gbk", "gb2312", "gb18030")


def _detect_encoding(raw: bytes) -> str:
    for enc in _ENCODINGS:
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            pass
    return "utf-8"


class ParsedRow:
    """Single-row parse result."""

    __slots__ = ("raw", "symbol", "reason")

    def __init__(self, raw: str, symbol: str, reason: str = "") -> None:
        self.raw    = raw
        self.symbol = symbol
        self.reason = reason

    @property
    def ok(self) -> bool:
        return bool(self.symbol)


class CsvParseResult:
    """Aggregate result from CsvParser.parse_file()."""

    def __init__(self) -> None:
        self.symbols:       list[str]       = []
        self.rows:          list[ParsedRow]  = []
        self.header_row:    str              = ""
        self.symbol_col:    int              = -1
        self.total_rows:    int              = 0
        self.skipped_rows:  int              = 0
        self.encoding_used: str              = ""

    @property
    def imported_count(self) -> int:
        return len(self.symbols)

    def summary(self) -> str:
        parts = [f"导入 {self.imported_count} 只股票"]
        if self.skipped_rows:
            parts.append(f"跳过 {self.skipped_rows} 行")
        if self.encoding_used:
            parts.append(f"编码 {self.encoding_used}")
        return "，".join(parts)


class CsvParser:
    """CSV / TXT stock pool file importer with auto-detection.

    Features:
      - Auto-detect encoding (utf-8-sig / gbk / gb18030 etc.)
      - Auto-detect header row and skip it
      - Auto-sniff which column contains stock codes
      - Handle comma / tab / pipe / semicolon delimiters
      - Per-row result for preview
      - Deduplicate output
    """

    def __init__(self) -> None:
        self._sym_parser = SymbolParser()

    def parse_file(self, filepath: "Path") -> CsvParseResult:
        """Parse a CSV/TXT file, return CsvParseResult.

        :raises FileNotFoundError: if file does not exist.
        """
        from pathlib import Path as _P
        path = _P(filepath)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在：{path}")
        raw_bytes = path.read_bytes()
        enc  = _detect_encoding(raw_bytes)
        text = raw_bytes.decode(enc, errors="replace")
        result = self._parse_text(text)
        result.encoding_used = enc
        return result

    def parse_text(self, text: str) -> CsvParseResult:
        """Parse already-decoded text, return CsvParseResult."""
        return self._parse_text(text)

    def _parse_text(self, text: str) -> CsvParseResult:
        result = CsvParseResult()
        lines  = [ln.rstrip("\r") for ln in text.splitlines()]
        if not lines:
            return result
        rows: list[list[str]] = [self._split_line(ln) for ln in lines]
        header_idx, sym_col = self._detect_header_and_col(rows)
        if header_idx >= 0:
            result.header_row = lines[header_idx]
            data_rows  = rows[header_idx + 1:]
            data_lines = lines[header_idx + 1:]
        else:
            data_rows  = rows
            data_lines = lines
        result.symbol_col = sym_col
        result.total_rows = len(data_rows)
        seen: set[str] = set()
        for raw_line, fields in zip(data_lines, data_rows):
            if not any(f.strip() for f in fields):
                result.rows.append(ParsedRow(raw_line, "", "空行"))
                result.skipped_rows += 1
                continue
            candidates = (
                [fields[sym_col]] if 0 <= sym_col < len(fields) else []
            ) + fields
            vt = ""
            for token in candidates:
                vt = self._sym_parser.normalize(token.strip())
                if vt:
                    break
            if not vt:
                result.rows.append(ParsedRow(raw_line, "", "未识别"))
                result.skipped_rows += 1
                continue
            result.rows.append(ParsedRow(raw_line, vt))
            if vt not in seen:
                seen.add(vt)
                result.symbols.append(vt)
        return result

    @staticmethod
    def _split_line(line: str) -> list[str]:
        for delim in (",", "\t", "|", ";"):
            if delim in line:
                return line.split(delim)
        parts = line.split()
        return parts if parts else [line]

    def _detect_header_and_col(
        self, rows: list[list[str]]
    ) -> tuple[int, int]:
        for i, fields in enumerate(rows[:5]):
            col = self._find_symbol_col(fields)
            if col >= 0:
                return i, col
        if rows:
            first_hits = [self._sym_parser.normalize(f.strip()) for f in rows[0]]
            if not any(first_hits):
                return 0, -1
        return -1, -1

    @staticmethod
    def _find_symbol_col(fields: list[str]) -> int:
        for idx, field in enumerate(fields):
            token = field.strip().lower()
            if not token:          # skip empty cells
                continue
            for kw in _SYMBOL_HEADER_KEYWORDS:
                if kw in token or token in kw:
                    return idx
        return -1
