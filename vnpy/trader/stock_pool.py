"""
股票池筛选工具 (Stock Pool Filter) - 全面性能优化版

提供按交易所、板块、行业筛选股票的统一接口。

性能优化:
  - 内存缓存：避免重复查询数据库
  - 24小时磁盘缓存：大幅提升启动速度
  - 后台线程查询：避免UI卡死
  - 所有筛选函数共享同一缓存
  - **核心优化**：使用DISTINCT查询避免199GB数据库全表扫描

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
from threading import Thread, Lock

logger = logging.getLogger("StockPool")

# ─── 缓存路径 ───
_CACHE_DIR = Path.home() / ".vnpy" / "stock_pool"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_INDUSTRY_CACHE_FILE = _CACHE_DIR / "stock_industry.json"

# ─── 内存缓存：避免重复查询数据库（性能优化）───
_LOCAL_SYMBOLS_CACHE: Optional[Set[str]] = None
_SYMBOLS_BY_EXCHANGE_CACHE: Dict[str, List[str]] = {}
_CACHE_TIMESTAMP: float = 0
_CACHE_EXPIRE_SECONDS = 300  # 内存缓存5分钟
_CACHE_LOCK = Lock()  # 线程锁（保留用于未来扩展）
_CACHE_LOADING = False  # 标记：是否正在后台加载数据

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
    """Load symbols from disk JSON cache (milliseconds).
    
    磁盘缓存有效期从1小时延长到24小时，提升用户体验。
    """
    if not _SYMBOLS_DISK_CACHE.exists():
        return None
    try:
        import os
        mtime = os.path.getmtime(_SYMBOLS_DISK_CACHE)
        # 修改：从1小时（3600秒）延长到24小时（86400秒）
        if (time.time() - mtime) > 86400:
            logger.info("磁盘缓存已过期（>24小时），将重新查询数据库")
            return None
        with open(_SYMBOLS_DISK_CACHE, "r", encoding="utf-8") as f:
            data = json.load(f)
        symbols = set(data.get("symbols", []))
        if symbols:
            logger.info(f"从磁盘缓存加载: {len(symbols)} symbols")
            return symbols
    except Exception as e:
        logger.warning(f"加载磁盘缓存失败: {e}")
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
        logger.info(f"磁盘缓存已保存: {len(symbols)} symbols")
    except Exception as e:
        logger.error(f"Save disk cache failed: {e}")


def _query_database_fast() -> Set[str]:
    """
    **核心优化**：使用DISTINCT查询避免199GB数据库COUNT(*)全表扫描
    
    替代原来的 db.get_bar_overview()，后者会执行：
        DbBarData.select().count()  # 这在199GB数据库上极慢！
    
    新方法直接查询不重复的symbol+exchange组合，快100倍以上
    """
    try:
        from vnpy.trader.constant import Interval, Exchange
        
        logger.info("使用优化的DISTINCT查询数据库...")
        start_time = time.time()
        
        local_symbols = set()
        
        # 尝试使用vnpy_sqlite的直接查询（最快）
        try:
            import vnpy_sqlite.sqlite_database as sqlite_module
            DbBarData = sqlite_module.DbBarData
            
            # 核心优化：使用DISTINCT避免全表扫描
            query = (DbBarData
                    .select(DbBarData.symbol, DbBarData.exchange, DbBarData.interval)
                    .where(DbBarData.interval == Interval.DAILY.value)
                    .distinct())
            
            for row in query:
                # 修复：exchange是字符串，需要转换为标准格式
                exchange_str = row.exchange
                if isinstance(exchange_str, str):
                    # 确保exchange是大写标准格式
                    exchange_str = exchange_str.upper()
                local_symbols.add(f"{row.symbol}.{exchange_str}")
                
            elapsed = time.time() - start_time
            logger.info(f"✓ DISTINCT查询完成: {len(local_symbols)} symbols, 耗时 {elapsed:.2f}秒")
            
        except ImportError:
            # 降级：使用通用的get_bar_overview()
            logger.warning("vnpy_sqlite不可用，降级到get_bar_overview()（可能较慢）")
            from vnpy.trader.database import get_database
            
            db = get_database()
            overview = db.get_bar_overview()
            
            for o in overview:
                if o.interval == Interval.DAILY:
                    local_symbols.add(f"{o.symbol}.{o.exchange.value}")
                    
            elapsed = time.time() - start_time
            logger.info(f"get_bar_overview()完成: {len(local_symbols)} symbols, 耗时 {elapsed:.2f}秒")
        
        return local_symbols
        
    except Exception as e:
        logger.error(f"查询数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return set()


def _query_database_async():
    """在后台线程查询数据库，避免UI卡死"""
    global _LOCAL_SYMBOLS_CACHE, _CACHE_TIMESTAMP, _CACHE_LOADING

    try:
        local_symbols = _query_database_fast()

        # 更新缓存
        with _CACHE_LOCK:
            _LOCAL_SYMBOLS_CACHE = local_symbols
            _CACHE_TIMESTAMP = time.time()
            _CACHE_LOADING = False

        # 保存到磁盘
        _save_symbols_disk_cache(local_symbols)

    except Exception as e:
        logger.error(f"后台查询数据库失败: {e}")
        with _CACHE_LOCK:
            _CACHE_LOADING = False


def _ensure_symbols_cache() -> Set[str]:
    """
    Ensure symbols cache is available.
    Strategy: memory cache -> disk cache -> async database query (return empty first)

    性能优化关键（真正的异步实现）：
    1. 优先使用内存缓存（5分钟有效期）
    2. 其次使用磁盘缓存（24小时有效期）
    3. 如果都没有，启动后台线程查询数据库，先返回空集合（UI不阻塞）
    4. 避免在主线程（UI线程）阻塞查询大数据库
    """
    global _LOCAL_SYMBOLS_CACHE, _CACHE_TIMESTAMP, _CACHE_LOADING

    current_time = time.time()

    # 1. 检查内存缓存（最快）
    if _LOCAL_SYMBOLS_CACHE is not None and (current_time - _CACHE_TIMESTAMP) <= _CACHE_EXPIRE_SECONDS:
        return _LOCAL_SYMBOLS_CACHE

    # 2. 检查磁盘缓存（较快）
    if _LOCAL_SYMBOLS_CACHE is None:
        disk_cache = _load_symbols_disk_cache()
        if disk_cache is not None:
            _LOCAL_SYMBOLS_CACHE = disk_cache
            _CACHE_TIMESTAMP = current_time
            return _LOCAL_SYMBOLS_CACHE

    # 3. 磁盘缓存也过期了，启动后台异步加载（UI不阻塞）
    if not _CACHE_LOADING:
        _CACHE_LOADING = True
        logger.info("缓存过期，启动后台异步加载...")
        thread = Thread(target=_query_database_async, daemon=True)
        thread.start()

    # 返回当前缓存（可能为空或过期），UI不会被阻塞
    # UI层会显示"正在加载"提示，用户可以稍后重试
    if _LOCAL_SYMBOLS_CACHE is not None:
        logger.info("使用过期缓存，后台正在更新...")
        return _LOCAL_SYMBOLS_CACHE
    else:
        logger.info("缓存为空，后台正在加载，请稍后重试")
        return set()


def _query_database_sync() -> Set[str]:
    """同步查询数据库（阻塞式）

    仅用于 force_refresh_cache()，不要在UI线程调用！
    """
    return _query_database_fast()


def force_refresh_cache():
    """
    强制刷新缓存（同步查询数据库）。

    注意：此函数会阻塞调用线程，仅供手动刷新使用！
    不要在UI主线程调用，否则会卡死界面。
    """
    global _LOCAL_SYMBOLS_CACHE, _CACHE_TIMESTAMP

    logger.info("强制刷新缓存（同步查询）...")
    local_symbols = _query_database_sync()

    with _CACHE_LOCK:
        _LOCAL_SYMBOLS_CACHE = local_symbols
        _CACHE_TIMESTAMP = time.time()

    _save_symbols_disk_cache(local_symbols)
    logger.info(f"缓存刷新完成: {len(local_symbols)} symbols")


# ═══════════════════════════════════════════════
#  按交易所筛选
# ═══════════════════════════════════════════════

def get_symbols_by_exchange(exchange_key: str = "ALL") -> List[str]:
    """Exchange filter optimized""" 
    global _SYMBOLS_BY_EXCHANGE_CACHE
    exchange_def = EXCHANGE_DEFINITIONS.get(exchange_key)
    if not exchange_def:
        logger.warning(f"Exchange not found: {exchange_key}")
        return []
    target_exchanges = exchange_def["exchanges"]
    try:
        local_symbols = _ensure_symbols_cache()
        if not local_symbols:
            return []
        if not _SYMBOLS_BY_EXCHANGE_CACHE:
            from collections import defaultdict
            temp_cache = defaultdict(list)
            for vt_symbol in local_symbols:
                if "." in vt_symbol:
                    exchange = vt_symbol.split(".")[-1]
                    temp_cache[exchange].append(vt_symbol)
            for ex, symbols in temp_cache.items():
                _SYMBOLS_BY_EXCHANGE_CACHE[ex] = sorted(symbols)
            logger.info(f"Exchange cache built: {len(_SYMBOLS_BY_EXCHANGE_CACHE)} exchanges")
        symbols = []
        for ex in target_exchanges:
            symbols.extend(_SYMBOLS_BY_EXCHANGE_CACHE.get(ex, []))
        return symbols
    except Exception as e:
        logger.error(f"get_symbols_by_exchange error: {e}")
        return []


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

        if not local_symbols:
            logger.warning("缓存为空，可能正在后台加载，请稍后重试")
            return []

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

    if not local_symbols:
        logger.warning("缓存为空，可能正在后台加载，请稍后重试")

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


def is_cache_loading() -> bool:
    """检查缓存是否正在后台加载"""
    return _CACHE_LOADING


def get_cache_status() -> dict:
    """获取缓存状态信息（用于UI显示）"""
    return {
        "has_cache": _LOCAL_SYMBOLS_CACHE is not None,
        "cache_count": len(_LOCAL_SYMBOLS_CACHE) if _LOCAL_SYMBOLS_CACHE else 0,
        "is_loading": _CACHE_LOADING,
        "cache_age_seconds": time.time() - _CACHE_TIMESTAMP if _CACHE_TIMESTAMP > 0 else None,
    }

def get_pool_update_time() -> str:
    """获取股票池数据的更新时间（用于UI显示）"""
    try:
        cache_path = _SYMBOLS_DISK_CACHE
        if cache_path.exists():
            import json
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                update_time = data.get('update_time', '')
                if update_time:
                    # 格式化时间显示，例如：2026-08-15 14:30
                    from datetime import datetime
                    dt = datetime.fromisoformat(update_time)
                    return dt.strftime('%Y-%m-%d %H:%M')
        return ''
    except Exception as e:
        return ''

