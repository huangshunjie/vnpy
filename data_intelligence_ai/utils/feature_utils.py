"""
data_intelligence_ai/utils/feature_utils.py  (Phase 2)

特征计算工具函数。

- 6种特征类型的标准计算函数
- 特征 ID 生成
- 谱系构建
- 版本冲突检测
"""
from __future__ import annotations
import math
import uuid
from datetime import datetime
from ..constant import FeatureType, DataType
from ..model.feature_model import FeatureRecord, FeatureLineage, FeatureVersion


# ── ID 生成 ───────────────────────────────────────────────────────────
def make_feature_id(feature_name: str, symbol: str, version: int) -> str:
    return f"FT_{feature_name[:8].upper()}_{symbol[:6].upper()}_V{version}"


# ── 谱系构建 ──────────────────────────────────────────────────────────
def make_lineage(
    feature_name: str,
    source_type:  DataType,
    source_id:    str   = "",
    compute_fn:   str   = "",
    dependencies: list[str] | None = None,
) -> FeatureLineage:
    return FeatureLineage(
        feature_name = feature_name,
        source_type  = source_type,
        source_id    = source_id,
        compute_fn   = compute_fn,
        dependencies = dependencies or [],
    )


# ── 特征构建快捷函数 ──────────────────────────────────────────────────

def make_feature(
    feature_name:  str,
    feature_type:  FeatureType,
    symbol:        str,
    value:         float,
    source:        str        = "",
    source_record: str        = "",
    version:       int        = 1,
    source_dtype:  DataType   = DataType.MARKET,
    compute_fn:    str        = "",
    dependencies:  list[str] | None = None,
    metadata:      dict | None = None,
) -> FeatureRecord:
    """通用特征记录构建函数。"""
    lineage = make_lineage(feature_name, source_dtype,
                            source_record, compute_fn, dependencies)
    return FeatureRecord(
        feature_id    = make_feature_id(feature_name, symbol, version),
        feature_name  = feature_name,
        feature_type  = feature_type,
        symbol        = symbol,
        timestamp     = datetime.now(),
        value         = round(value, 8),
        version       = version,
        source        = source,
        source_record = source_record,
        lineage       = lineage,
        metadata      = metadata or {},
    )


# ── 6种特征类型计算函数 ───────────────────────────────────────────────

def compute_price_feature(
    prices:       list[float],
    feature_name: str,
    symbol:       str,
    source_record:str = "",
    version:      int = 1,
) -> FeatureRecord:
    """
    价格特征：支持 close_ret / log_ret / price_zscore。
    """
    if not prices or len(prices) < 2:
        value = 0.0
    elif feature_name == "log_ret":
        p0, p1 = prices[-2], prices[-1]
        value  = math.log(p1 / p0) if p0 > 0 and p1 > 0 else 0.0
    elif feature_name == "price_zscore":
        mu    = sum(prices) / len(prices)
        sigma = math.sqrt(sum((p - mu) ** 2 for p in prices) / len(prices)) or 1.0
        value = (prices[-1] - mu) / sigma
    else:  # close_ret (default)
        p0, p1 = prices[-2], prices[-1]
        value  = (p1 - p0) / abs(p0) if p0 != 0 else 0.0

    return make_feature(feature_name, FeatureType.PRICE, symbol, value,
                         source="market", source_record=source_record,
                         version=version, compute_fn=f"compute_price/{feature_name}")


def compute_volume_feature(
    volumes:      list[float],
    feature_name: str,
    symbol:       str,
    source_record:str = "",
    version:      int = 1,
) -> FeatureRecord:
    """
    成交量特征：支持 vol_ratio / vol_zscore / turnover_norm。
    """
    if not volumes or len(volumes) < 2:
        value = 0.0
    elif feature_name == "vol_ratio":
        avg   = sum(volumes[:-1]) / max(len(volumes) - 1, 1) or 1.0
        value = volumes[-1] / avg
    elif feature_name == "vol_zscore":
        mu    = sum(volumes) / len(volumes)
        sigma = math.sqrt(sum((v - mu) ** 2 for v in volumes) / len(volumes)) or 1.0
        value = (volumes[-1] - mu) / sigma
    else:  # turnover_norm
        total = sum(volumes) or 1.0
        value = volumes[-1] / total

    return make_feature(feature_name, FeatureType.VOLUME, symbol, value,
                         source="market", source_record=source_record,
                         version=version, compute_fn=f"compute_volume/{feature_name}")


def compute_volatility_feature(
    prices:       list[float],
    feature_name: str,
    symbol:       str,
    source_record:str = "",
    version:      int = 1,
) -> FeatureRecord:
    """
    波动率特征：支持 hist_vol / parkinson / garman_klass（使用收盘价近似）。
    """
    if not prices or len(prices) < 2:
        value = 0.0
    elif feature_name == "parkinson":
        # 近似：使用极差归一化
        hi, lo = max(prices), min(prices)
        value  = math.log(hi / lo) / (2 * math.sqrt(2 * math.log(2))) if lo > 0 else 0.0
    elif feature_name == "garman_klass":
        rets  = [math.log(prices[i] / prices[i-1])
                 for i in range(1, len(prices)) if prices[i-1] > 0]
        value = math.sqrt(sum(r**2 for r in rets) / max(len(rets), 1))
    else:  # hist_vol
        rets  = [(prices[i] - prices[i-1]) / abs(prices[i-1])
                 for i in range(1, len(prices)) if prices[i-1] != 0]
        if len(rets) < 2:
            value = 0.0
        else:
            mu    = sum(rets) / len(rets)
            value = math.sqrt(sum((r - mu) ** 2 for r in rets) / len(rets))

    return make_feature(feature_name, FeatureType.VOLATILITY, symbol, value,
                         source="market", source_record=source_record,
                         version=version, compute_fn=f"compute_vol/{feature_name}")


def compute_alpha_feature(
    alpha_value:  float,
    feature_name: str,
    symbol:       str,
    source_record:str = "",
    version:      int = 1,
) -> FeatureRecord:
    """Alpha 特征（直接透传，来自 Alpha Factory）。"""
    return make_feature(feature_name, FeatureType.ALPHA, symbol, alpha_value,
                         source="alpha_factory", source_record=source_record,
                         version=version, source_dtype=DataType.ALPHA,
                         compute_fn="passthrough_alpha")


def compute_regime_feature(
    regime_prob:  float,
    feature_name: str,
    symbol:       str   = "_market",
    source_record:str   = "",
    version:      int   = 1,
) -> FeatureRecord:
    """市场状态特征（来自 Market Regime）。"""
    return make_feature(feature_name, FeatureType.REGIME, symbol, regime_prob,
                         source="market_regime", source_record=source_record,
                         version=version, source_dtype=DataType.REGIME,
                         compute_fn="passthrough_regime")


def compute_execution_feature(
    exec_value:   float,
    feature_name: str,
    symbol:       str   = "",
    source_record:str   = "",
    version:      int   = 1,
) -> FeatureRecord:
    """执行特征（来自 Execution Intelligence）。"""
    return make_feature(feature_name, FeatureType.EXECUTION, symbol, exec_value,
                         source="execution_intelligence", source_record=source_record,
                         version=version, source_dtype=DataType.EXECUTION,
                         compute_fn="passthrough_execution")


# ── 版本冲突检测 ──────────────────────────────────────────────────────

def check_overwrite(
    existing: FeatureRecord,
    incoming: FeatureRecord,
) -> tuple[bool, str]:
    """
    检测特征是否会被覆写。

    Returns (should_overwrite, reason)
    """
    if existing.symbol != incoming.symbol:
        return False, "different symbol"
    if existing.feature_name != incoming.feature_name:
        return False, "different feature"
    if incoming.version < existing.version:
        return False, f"incoming version {incoming.version} < existing {existing.version}"
    if incoming.version == existing.version and abs(incoming.value - existing.value) < 1e-10:
        return False, "identical value, skip"
    return True, f"overwrite v{existing.version}→v{incoming.version}"


def make_version_record(
    existing: FeatureRecord,
    incoming: FeatureRecord,
) -> FeatureVersion:
    """从覆写事件生成 FeatureVersion 记录。"""
    return FeatureVersion(
        feature_name   = incoming.feature_name,
        symbol         = incoming.symbol,
        version        = incoming.version,
        value          = incoming.value,
        previous_value = existing.value,
        delta          = incoming.value - existing.value,
        is_active      = True,
        source_record  = incoming.source_record,
    )


# ── 批量特征从原始数据构建 ────────────────────────────────────────────

def features_from_market(
    symbol:  str,
    prices:  list[float],
    volumes: list[float],
    version: int = 1,
) -> list[FeatureRecord]:
    """
    从行情数据批量生成标准特征集。
    Returns list of FeatureRecord for price / volume / volatility.
    """
    feats: list[FeatureRecord] = []
    if len(prices) >= 2:
        feats.append(compute_price_feature(
            prices, "close_ret", symbol, version=version))
        feats.append(compute_price_feature(
            prices, "log_ret",   symbol, version=version))
        feats.append(compute_volatility_feature(
            prices, "hist_vol",  symbol, version=version))
    if len(volumes) >= 2:
        feats.append(compute_volume_feature(
            volumes, "vol_ratio", symbol, version=version))
    return feats
