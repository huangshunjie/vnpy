"""
指数成分股管理模块 (Index Constituents Manager)

提供统一的指数成分股读写接口，所有 App 共享使用。

存储位置: ~/.vnpy/index_constituents/
文件格式: JSON

支持的指数:
  - 000016  上证50
  - 000300  沪深300
  - 000905  中证500
  - 000852  中证1000
  - 399006  创业板指
  - 399005  中小板指
  - 000688  科创50

用法:
    from vnpy.trader.index_constituents import (
        get_index_symbols,
        get_index_info,
        update_index_from_tushare,
        get_all_supported_indices,
        INDEX_STORE_DIR,
    )

    # 读取成分股
    symbols = get_index_symbols("000300")  # → ["000001.SZSE", "600519.SSE", ...]

    # 更新成分股（从 TuShare 拉取）
    result = update_index_from_tushare("000300", token="your_token")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("IndexConstituents")

# ─── 存储路径 ───
INDEX_STORE_DIR = Path.home() / ".vnpy" / "index_constituents"
INDEX_STORE_DIR.mkdir(parents=True, exist_ok=True)

# ─── 支持的指数定义 ───
# category 用于 UI 分组展示
SUPPORTED_INDICES: Dict[str, Dict] = {
    # ━━━ 规模指数（核心宽基） ━━━
    "000016": {"name": "上证50", "ts_code": "000016.SH", "exchange": "SSE", "category": "规模指数"},
    "000010": {"name": "上证180", "ts_code": "000010.SH", "exchange": "SSE", "category": "规模指数"},
    "000300": {"name": "沪深300", "ts_code": "399300.SZ", "exchange": "", "category": "规模指数"},
    "000905": {"name": "中证500", "ts_code": "000905.SH", "exchange": "", "category": "规模指数"},
    "000852": {"name": "中证1000", "ts_code": "000852.SH", "exchange": "", "category": "规模指数"},
    "932000": {"name": "中证2000", "ts_code": "932000.CSI", "exchange": "", "category": "规模指数"},
    "000510": {"name": "中证A500", "ts_code": "000510.SH", "exchange": "", "category": "规模指数"},
    "399330": {"name": "深证100", "ts_code": "399330.SZ", "exchange": "SZSE", "category": "规模指数"},

    # ━━━ 板块指数 ━━━
    "399006": {"name": "创业板指", "ts_code": "399006.SZ", "exchange": "SZSE", "category": "板块指数"},
    "399673": {"name": "创业板50", "ts_code": "399673.SZ", "exchange": "SZSE", "category": "板块指数"},
    "000688": {"name": "科创50", "ts_code": "000688.SH", "exchange": "SSE", "category": "板块指数"},
    "000698": {"name": "科创100", "ts_code": "000698.SH", "exchange": "SSE", "category": "板块指数"},
    "399005": {"name": "中小板指", "ts_code": "399005.SZ", "exchange": "SZSE", "category": "板块指数"},
    "899050": {"name": "北证50", "ts_code": "899050.BJ", "exchange": "BSE", "category": "板块指数"},

    # ━━━ 风格/策略指数 ━━━
    "000015": {"name": "上证红利", "ts_code": "000015.SH", "exchange": "SSE", "category": "风格策略"},
    "000913": {"name": "中证300价值", "ts_code": "000913.SH", "exchange": "", "category": "风格策略"},
    "399702": {"name": "深证F120", "ts_code": "399702.SZ", "exchange": "SZSE", "category": "风格策略"},
    "000029": {"name": "上证180价值", "ts_code": "000029.SH", "exchange": "SSE", "category": "风格策略"},
    "000028": {"name": "上证180成长", "ts_code": "000028.SH", "exchange": "SSE", "category": "风格策略"},

    # ━━━ 行业主题指数 ━━━
    "000932": {"name": "中证消费", "ts_code": "000932.SH", "exchange": "", "category": "行业主题"},
    "000933": {"name": "中证医药", "ts_code": "000933.SH", "exchange": "", "category": "行业主题"},
    "399986": {"name": "中证银行", "ts_code": "399986.SZ", "exchange": "", "category": "行业主题"},
    "399975": {"name": "中证证券", "ts_code": "399975.SZ", "exchange": "", "category": "行业主题"},
    "399808": {"name": "中证新能源", "ts_code": "399808.SZ", "exchange": "", "category": "行业主题"},
    "399997": {"name": "中证白酒", "ts_code": "399997.SZ", "exchange": "", "category": "行业主题"},
    "399967": {"name": "中证军工", "ts_code": "399967.SZ", "exchange": "", "category": "行业主题"},
    "931071": {"name": "中证半导体", "ts_code": "931071.CSI", "exchange": "", "category": "行业主题"},
    "930997": {"name": "中证计算机", "ts_code": "930997.CSI", "exchange": "", "category": "行业主题"},
    "399812": {"name": "中证养老产业", "ts_code": "399812.SZ", "exchange": "", "category": "行业主题"},
}


@dataclass
class ConstituentInfo:
    """单只成分股信息"""
    symbol: str          # 纯代码，如 "000001"
    exchange: str        # 交易所，如 "SZSE"
    name: str = ""       # 股票名称
    weight: float = 0.0  # 权重（百分比）

    @property
    def vt_symbol(self) -> str:
        return f"{self.symbol}.{self.exchange}"


@dataclass
class IndexData:
    """指数成分股数据"""
    index_code: str          # 指数代码，如 "000300"
    index_name: str          # 指数名称，如 "沪深300"
    update_date: str         # 更新日期，如 "2026-08-09"
    count: int               # 成分股数量
    constituents: List[Dict] # 成分股列表


def _get_file_path(index_code: str) -> Path:
    """获取成分股 JSON 文件路径"""
    info = SUPPORTED_INDICES.get(index_code, {})
    name = info.get("name", index_code)
    return INDEX_STORE_DIR / f"{index_code}_{name}.json"


def _symbol_to_exchange(symbol: str) -> str:
    """根据股票代码推断交易所"""
    if symbol.startswith(("60", "68")):
        return "SSE"
    if symbol.startswith(("00", "30", "002", "003", "301")):
        return "SZSE"
    if symbol.startswith(("8", "4")):
        return "BSE"
    return "SSE"


# ═══════════════════════════════════════════════
#  公开读取接口
# ═══════════════════════════════════════════════

def get_all_supported_indices() -> Dict[str, str]:
    """
    返回所有支持的指数代码和名称映射。

    Returns:
        {"000016": "上证50", "000300": "沪深300", ...}
    """
    return {code: info["name"] for code, info in SUPPORTED_INDICES.items()}


def get_index_symbols(index_code: str) -> List[str]:
    """
    获取指数成分股的 vt_symbol 列表。

    Args:
        index_code: 指数代码，如 "000300"

    Returns:
        vt_symbol 列表，如 ["000001.SZSE", "600519.SSE", ...]
        如果本地没有缓存数据，返回空列表。
    """
    data = _load_index_data(index_code)
    if data is None:
        return []
    symbols = []
    for c in data["constituents"]:
        sym = c["symbol"]
        exch = c.get("exchange", "") or _symbol_to_exchange(sym)
        symbols.append(f"{sym}.{exch}")
    return sorted(symbols)


def get_index_info(index_code: str) -> Optional[Dict]:
    """
    获取指数的完整信息（含成分股详情）。

    Returns:
        IndexData 的字典形式，或 None（如果没有缓存）。
    """
    return _load_index_data(index_code)


def get_index_meta(index_code: str) -> Optional[Dict]:
    """
    获取指数的元信息（不含成分股明细，速度快）。

    Returns:
        {"index_code": ..., "index_name": ..., "update_date": ..., "count": ...}
        或 None。
    """
    fp = _get_file_path(index_code)
    if not fp.exists():
        return None
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "index_code": data.get("index_code", index_code),
            "index_name": data.get("index_name", ""),
            "update_date": data.get("update_date", ""),
            "count": data.get("count", 0),
        }
    except Exception:
        return None


def is_index_cached(index_code: str) -> bool:
    """检查指数成分股是否已缓存"""
    return _get_file_path(index_code).exists()


# ═══════════════════════════════════════════════
#  TuShare 更新接口
# ═══════════════════════════════════════════════

def update_index_from_tushare(
    index_code: str,
    token: Optional[str] = None,
    trade_date: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    从 TuShare 拉取指数成分股并保存到本地。

    Args:
        index_code: 指数代码，如 "000300"
        token: TuShare API token。如果为 None，自动从 vnpy 配置读取。
        trade_date: 交易日期（格式 YYYYMMDD）。如果为 None，使用最近交易日。

    Returns:
        (success: bool, message: str)
    """
    if index_code not in SUPPORTED_INDICES:
        return False, f"不支持的指数代码: {index_code}"

    # 获取 token
    if token is None:
        token = _get_tushare_token()
    if not token:
        return False, "未配置 TuShare token，请在全局配置中设置 datafeed.password"

    try:
        import tushare as ts
    except ImportError:
        return False, "未安装 tushare 库，请执行: pip install tushare"

    index_info = SUPPORTED_INDICES[index_code]
    ts_code = index_info["ts_code"]
    index_name = index_info["name"]

    try:
        pro = ts.pro_api(token)

        # 使用 index_weight 获取成分股权重
        if trade_date:
            df = pro.index_weight(
                index_code=ts_code,
                start_date=trade_date,
                end_date=trade_date,
            )
        else:
            # 不指定日期时，获取最近的成分股数据
            # TuShare index_weight 需要日期，先获取最近交易日
            today_str = datetime.now().strftime("%Y%m%d")
            df = pro.index_weight(
                index_code=ts_code,
                start_date=_date_offset(today_str, -30),
                end_date=today_str,
            )

        if df is None or df.empty:
            # 备选：尝试 index_member 接口
            return _update_via_index_member(pro, index_code, ts_code, index_name)

        # 取最新日期的数据
        latest_date = df["trade_date"].max()
        df_latest = df[df["trade_date"] == latest_date].copy()

        # 解析成分股
        constituents = []
        for _, row in df_latest.iterrows():
            con_code = str(row["con_code"])  # 如 "000001.SZ"
            parts = con_code.split(".")
            symbol = parts[0]
            ts_exch = parts[1] if len(parts) > 1 else ""
            exchange = "SSE" if ts_exch == "SH" else "SZSE"
            weight = float(row.get("weight", 0) or 0)

            constituents.append({
                "symbol": symbol,
                "exchange": exchange,
                "name": "",
                "weight": round(weight, 4),
            })

        # 补充股票名称（批量查询）
        constituents = _fill_stock_names(pro, constituents)

        # 保存
        update_date = f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:8]}"
        _save_index_data(index_code, index_name, update_date, constituents)

        return True, f"成功更新 {index_name}，共 {len(constituents)} 只成分股（数据日期: {update_date}）"

    except Exception as e:
        logger.error(f"更新 {index_name} 失败: {e}")
        return False, f"更新 {index_name} 失败: {str(e)}"


def update_all_indices(
    token: Optional[str] = None,
    callback=None,
) -> Dict[str, Tuple[bool, str]]:
    """
    更新所有支持的指数成分股。

    Args:
        token: TuShare token
        callback: 进度回调函数 callback(index_code, index_name, success, message)

    Returns:
        {index_code: (success, message), ...}
    """
    results = {}
    for code, info in SUPPORTED_INDICES.items():
        success, msg = update_index_from_tushare(code, token=token)
        results[code] = (success, msg)
        if callback:
            callback(code, info["name"], success, msg)
    return results


# ═══════════════════════════════════════════════
#  内部辅助函数
# ═══════════════════════════════════════════════

def _get_tushare_token() -> str:
    """从 vnpy 全局配置读取 TuShare token"""
    try:
        from vnpy.trader.setting import SETTINGS
        return SETTINGS.get("datafeed.password", "")
    except Exception:
        return ""


def _load_index_data(index_code: str) -> Optional[Dict]:
    """从本地 JSON 文件读取指数数据"""
    fp = _get_file_path(index_code)
    if not fp.exists():
        return None
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"读取 {fp} 失败: {e}")
        return None


def _save_index_data(
    index_code: str,
    index_name: str,
    update_date: str,
    constituents: List[Dict],
) -> None:
    """保存指数成分股数据到本地 JSON"""
    data = {
        "index_code": index_code,
        "index_name": index_name,
        "update_date": update_date,
        "count": len(constituents),
        "constituents": constituents,
    }
    fp = _get_file_path(index_code)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存 {index_name} 成分股到 {fp}（{len(constituents)} 只）")


def _date_offset(date_str: str, days: int) -> str:
    """日期偏移"""
    from datetime import timedelta
    dt = datetime.strptime(date_str, "%Y%m%d")
    new_dt = dt + timedelta(days=days)
    return new_dt.strftime("%Y%m%d")


def _update_via_index_member(pro, index_code: str, ts_code: str, index_name: str) -> Tuple[bool, str]:
    """
    备选方案：使用 index_member 接口获取成分股（无权重信息）。
    适用于 index_weight 没有数据的情况。
    """
    try:
        df = pro.index_member(index_code=ts_code, is_new="Y")
        if df is None or df.empty:
            return False, f"{index_name}: TuShare 未返回数据，请检查接口权限"

        constituents = []
        for _, row in df.iterrows():
            con_code = str(row.get("con_code", "") or row.get("stock_code", ""))
            if not con_code:
                continue
            parts = con_code.split(".")
            symbol = parts[0]
            ts_exch = parts[1] if len(parts) > 1 else ""
            exchange = "SSE" if ts_exch == "SH" else "SZSE"
            constituents.append({
                "symbol": symbol,
                "exchange": exchange,
                "name": str(row.get("con_name", "")),
                "weight": 0.0,
            })

        if not constituents:
            return False, f"{index_name}: 解析成分股为空"

        # 补充名称
        constituents = _fill_stock_names(pro, constituents)

        update_date = date.today().isoformat()
        _save_index_data(index_code, index_name, update_date, constituents)
        return True, f"成功更新 {index_name}（通过 index_member），共 {len(constituents)} 只"

    except Exception as e:
        return False, f"{index_name} index_member 失败: {str(e)}"


def _fill_stock_names(pro, constituents: List[Dict]) -> List[Dict]:
    """
    批量补充股票名称。利用 TuShare stock_basic 接口。
    """
    # 只对没有名称的进行补充
    need_names = [c for c in constituents if not c.get("name")]
    if not need_names:
        return constituents

    try:
        df = pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name",
        )
        if df is not None and not df.empty:
            name_map = dict(zip(df["symbol"].astype(str), df["name"]))
            for c in constituents:
                if not c.get("name"):
                    c["name"] = name_map.get(c["symbol"], "")
    except Exception as e:
        logger.debug(f"补充股票名称失败（不影响主流程）: {e}")

    return constituents