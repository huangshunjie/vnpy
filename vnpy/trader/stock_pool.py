"""
股票池筛选工具 (Stock Pool Filter) - 全面性能优化版

提供按交易所、板块、行业筛选股票的统一接口。

性能优化:
  - 内存缓存：避免重复查询数据库
  - 5分钟自动过期：平衡性能和数据新鲜度
  - 所有筛选函数共享同一缓存

数据来源:
  - 交易所/板块: 直接从本地数据库 bar_overview 按代码前缀过滤
  - 行业分类: TuShare stock_basic 的 industry 字段，缓存为 JSON

用法:
    from vnpy.trader.stock_pool import (
        get_symbols_by_exchange,
        get_symbols_by_board,
        get_symbols_by_industry,
        get_all_industries,
        update_industry_cache,
    )

    # 按交易所
    symbols = get_symbols_by_exchange("SSE")  # 沪市所有
    symbols = get_symbols_by_exchange("ALL")  # 全市场

    # 按板块
    symbols = get_symbols_by_board("科创板")

    # 按行业
    symbols = get_symbols_by_industry("银行")
    industries = get_all_industries()  # 获取所有行业列表
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger("StockPool")

# ─── 缓存路径 ───
_CACHE_DIR = Path.home() / ".vnpy" / "stock_pool"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_INDUSTRY_CACHE_FILE = _CACHE_DIR / "stock_industry.json"

# ─── 内存缓存：避免重复查询数据库（性能优化）───
_LOCAL_SYMBOLS_CACHE: Optional[Set[str]] = None
_CACHE_TIMESTAMP: float = 0
_CACHE_EXPIRE_SECONDS = 300  # 缓存5分钟

# ─── 板块定义（代码前缀规则） ───
BOARD_DEFINITIONS = {
    "沪主板": {"exchange": "SSE", "prefixes": ["60"]},
    "科创板": {"exchange": "SSE", "prefixes": ["68"]},
    "深主板": {"exchange": "SZSE", "prefixes": ["00"]},
    "创业板": {"exchange": "SZSE", "prefixes": ["30"]},
    "北交所": {"exchange": "BSE", "prefixes": ["8", "4"]},
}

# 交易所定义
EXCHANGE_DEFINITIONS = {
    "ALL": {"label": "全市场", "exchanges": ["SSE", "SZSE", "BSE"]},
    "SSE": {"label": "沪市", "exchanges": ["SSE"]},
    "SZSE": {"label": "深市", "exchanges": ["SZSE"]},
    "BSE": {"label": "北交所", "exchanges": ["BSE"]},
}


# ═══════════════════════════════════════════════
#  内部缓存管理
# ═══════════════════════════════════════════════

# 磁盘缓存路径（快速加载，避免首次查库慢）
_SYMBOLS_DISK_CACHE = _CACHE_DIR / "symbols_cache.json"


def _load_symbols_disk_cache():
    """Load symbols from disk JSON cache (milliseconds)."""
    if not _SYMBOLS_DISK_CACHE.exists():
        return None
    try:
        import os
        mtime = os.path.getmtime(_SYMBOLS_DISK_CACHE)
        if (time.time() - mtime) > 3600:
            return None
        with open(_SYMBOLS_DISK_CACHE, "r", encoding="utf-8") as f:
            data = json.load(f)
        symbols = set(data.get("symbols", []))
        if symbols:
            logger.info(f"\u4ece\u78c1\u76d8\u7f13\u5b58\u52a0\u8f7d: {len(symbols)} symbols")
            return symbols
    except Exception:
        pass
    return None


def _save_symbols_disk_cache(symbols):
    """Save symbols to disk JSON cache."""
    try:
        data = {
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "count": len(symbols),
            "symbols": sorted(symbols),
        }
        with open(_SYMBOLS_DISK_CACHE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Save disk cache failed: {e}")


def _ensure_symbols_cache() -> Set[str]:
    """
    Ensure symbols cache is available.
    Strategy: memory cache -> disk cache -> database query -> save disk cache
    """
    global _LOCAL_SYMBOLS_CACHE, _CACHE_TIMESTAMP

    current_time = time.time()

    if _LOCAL_SYMBOLS_CACHE is not None and (current_time - _CACHE_TIMESTAMP) <= _CACHE_EXPIRE_SECONDS:
        return _LOCAL_SYMBOLS_CACHE

    # Try disk cache first (fast path)
    if _LOCAL_SYMBOLS_CACHE is None:
        disk_cache = _load_symbols_disk_cache()
        if disk_cache is not None:
            _LOCAL_SYMBOLS_CACHE = disk_cache
            _CACHE_TIMESTAMP = current_time
            return _LOCAL_SYMBOLS_CACHE

    # Query database
    local_symbols = set()
    try:
        from vnpy.trader.database import get_database
        from vnpy.trader.constant import Interval

        db = get_database()
        overview = db.get_bar_overview()
        for o in overview:
            if o.interval == Interval.DAILY:
                local_symbols.add(f"{o.symbol}.{o.exchange.value}")
    except Exception as e:
        logger.error(f"Build symbols cache failed: {e}")

    _LOCAL_SYMBOLS_CACHE = local_symbols
    _CACHE_TIMESTAMP = current_time
    _save_symbols_disk_cache(local_symbols)
    logger.info(f"Symbols cache updated: {len(local_symbols)} stocks")

    return _LOCAL_SYMBOLS_CACHE


def preload_cache():
    """Preload symbols cache (call from background thread for async loading)."""
    _ensure_symbols_cache()


# ═══════════════════════════════════════════════
#  按交易所筛选
# ═══════════════════════════════════════════════

def get_symbols_by_exchange(exchange_key: str = "ALL") -> List[str]:
    """
    从数据库获取指定交易所的所有日线标的（优化版：使用缓存）。

    Args:
        exchange_key: "ALL", "SSE", "SZSE", "BSE"

    Returns:
        vt_symbol 列表，如 ["000001.SZSE", "600519.SSE", ...]
    """
    try:
        # 使用统一的缓存管理
        local_symbols = _ensure_symbols_cache()
        
        # 从缓存中按交易所筛选
        target_exchanges = EXCHANGE_DEFINITIONS.get(
            exchange_key, {"exchanges": [exchange_key]}
        )["exchanges"]

        symbols = []
        for vt_symbol in local_symbols:
            # vt_symbol 格式: "000001.SZSE"
            if "." in vt_symbol:
                exchange = vt_symbol.split(".")[-1]
                if exchange in target_exchanges:
                    symbols.append(vt_symbol)

        return sorted(symbols)
    except Exception as e:
        logger.error(f"get_symbols_by_exchange 失败: {e}")
        return []


# ═══════════════════════════════════════════════
#  按板块筛选
# ═══════════════════════════════════════════════

def get_symbols_by_board(board_name: str) -> List[str]:
    """
    按上市板块筛选股票（优化版：使用缓存）。

    Args:
        board_name: 板块名称，如 "科创板", "创业板"

    Returns:
        vt_symbol 列表
    """
    board_def = BOARD_DEFINITIONS.get(board_name)
    if not board_def:
        logger.warning(f"未找到板块定义: {board_name}")
        return []

    target_exchange = board_def["exchange"]
    prefixes = tuple(board_def["prefixes"])

    try:
        # 使用统一的缓存管理
        local_symbols = _ensure_symbols_cache()

        # 从缓存中按板块筛选
        symbols = []
        for vt_symbol in local_symbols:
            # vt_symbol 格式: "000001.SZSE"
            if "." in vt_symbol:
                symbol, exchange = vt_symbol.rsplit(".", 1)
                if exchange == target_exchange and symbol.startswith(prefixes):
                    symbols.append(vt_symbol)

        return sorted(symbols)
    except Exception as e:
        logger.error(f"get_symbols_by_board 失败: {e}")
        return []


# ═══════════════════════════════════════════════
#  按行业筛选
# ═══════════════════════════════════════════════

def get_all_industries() -> List[str]:
    """
    获取所有行业列表（从缓存中读取）。

    Returns:
        行业名称列表，如 ["银行", "医药生物", "电子", ...]
        如果没有缓存返回默认行业列表。
    """
    cache = _load_industry_cache()
    if not cache:
        # 返回默认行业列表（申万一级行业分类）
        return [
            "银行", "非银金融", "房地产", "建筑装饰", "建筑材料",
            "钢铁", "有色金属", "煤炭", "石油石化", "化工",
            "基础化工", "电力设备", "机械设备", "国防军工", "汽车",
            "家用电器", "纺织服饰", "轻工制造", "商贸零售", "消费者服务",
            "食品饮料", "农林牧渔", "医药生物", "电子", "通信",
            "计算机", "传媒", "电力及公用事业", "交通运输", "环保",
            "美容护理", "社会服务"
        ]

    industries: Set[str] = set()
    for info in cache.get("data", {}).values():
        ind = info.get("industry", "")
        if ind:
            industries.add(ind)

    return sorted(industries)


def get_symbols_by_industry(industry: str) -> List[str]:
    """
    按行业筛选股票（优化版：带内存缓存）。

    Args:
        industry: 行业名称，如 "银行", "电子"

    Returns:
        vt_symbol 列表
    """
    cache = _load_industry_cache()
    if not cache:
        return []

    # 使用统一的缓存管理
    local_symbols = _ensure_symbols_cache()

    # 从行业缓存中筛选
    symbols = []
    for symbol, info in cache.get("data", {}).items():
        if info.get("industry") != industry:
            continue
        exchange = info.get("exchange", "")
        vt_sym = f"{symbol}.{exchange}"
        # 如果有本地数据库，只返回已入库的
        if local_symbols:
            if vt_sym in local_symbols:
                symbols.append(vt_sym)
        else:
            symbols.append(vt_sym)

    return sorted(symbols)


def update_industry_cache(token: Optional[str] = None) -> tuple:
    """
    从 TuShare 拉取全市场股票行业分类并缓存。

    Args:
        token: TuShare API token。如果为 None，自动从配置读取。

    Returns:
        (success: bool, message: str)
    """
    global _LOCAL_SYMBOLS_CACHE, _CACHE_TIMESTAMP
    
    if token is None:
        token = _get_tushare_token()
    if not token:
        return False, "未配置 TuShare token"

    try:
        import tushare as ts
    except ImportError:
        return False, "未安装 tushare 库"

    try:
        pro = ts.pro_api(token)

        # 获取全市场上市股票基本信息
        df = pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name,industry,market,exchange",
        )

        if df is None or df.empty:
            return False, "TuShare 未返回数据"

        # 构建缓存数据结构
        cache_data = {}
        for _, row in df.iterrows():
            symbol = row["symbol"]
            exchange = row["exchange"]
            cache_data[symbol] = {
                "name": row["name"],
                "industry": row["industry"] if row["industry"] else "",
                "exchange": exchange,
                "market": row["market"],
            }

        # 保存到 JSON
        cache_obj = {
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "count": len(cache_data),
            "data": cache_data,
        }

        with open(_INDUSTRY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_obj, f, ensure_ascii=False, indent=2)

        # 清空内存缓存，强制下次重新加载
        _LOCAL_SYMBOLS_CACHE = None
        _CACHE_TIMESTAMP = 0

        msg = f"成功更新 {len(cache_data)} 只股票的行业数据"
        logger.info(msg)
        return True, msg

    except Exception as e:
        error_msg = f"更新失败: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


# ═══════════════════════════════════════════════
#  内部辅助函数
# ═══════════════════════════════════════════════

def _load_industry_cache() -> Dict:
    """加载行业分类缓存"""
    if not _INDUSTRY_CACHE_FILE.exists():
        return {}
    try:
        with open(_INDUSTRY_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载行业缓存失败: {e}")
        return {}


def _get_tushare_token() -> Optional[str]:
    """从 VeighNa 配置中读取 TuShare token"""
    try:
        from vnpy.trader.setting import SETTINGS
        return SETTINGS.get("tushare.token", "")
    except Exception:
        return None
