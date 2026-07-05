"""
data_intelligence_ai/engine/feature_engine.py  (Phase 2)

FeatureEngine — Feature Store 核心引擎。

职责：
  - 特征写入（含版本管理 + 覆写保护）
  - 特征读取（按名称/类型/标的查询）
  - 特征谱系追踪
  - 特征版本历史管理
  - Feature Store 状态维护
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable
import uuid

from ..constant import FeatureType, DataType, SystemStatus
from ..model.feature_model import (
    FeatureRecord, FeatureLineage, FeatureVersion, FeatureState)
from ..utils.feature_utils import (
    check_overwrite, make_version_record,
    features_from_market,
    compute_alpha_feature, compute_regime_feature,
    compute_execution_feature,
)


class FeatureEngine:
    """Feature Store 引擎（Phase 2 完整实现）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log    = log_fn or (lambda m: None)
        self._status = SystemStatus.IDLE

        # Store: {feature_name: {symbol: FeatureRecord}}
        self._store:    dict[str, dict[str, FeatureRecord]]  = {}
        # Version history: {feature_name: {symbol: [FeatureVersion, ...]}}
        self._versions: dict[str, dict[str, list[FeatureVersion]]] = {}
        # Lineage: {feature_name: FeatureLineage}
        self._lineage:  dict[str, FeatureLineage] = {}

        self._write_count:     int = 0
        self._overwrite_count: int = 0
        self._started_at: datetime | None = None

    def init(self)  -> None: self._log("[FeatureEngine] init()")
    def start(self) -> None:
        self._started_at = datetime.now()
        self._status     = SystemStatus.COMPUTING
        self._log("[FeatureEngine] start()")

    def stop(self)  -> None:
        self._status = SystemStatus.STOPPED
        self._log("[FeatureEngine] stop()")

    # ── write ─────────────────────────────────────────────────────────
    def write(self, record: FeatureRecord) -> tuple[bool, str]:
        """
        写入一条特征记录。

        Returns (success, reason)
        - 若相同 (feature_name, symbol) 已存在：执行覆写保护检查
        - 若通过检查：更新 Store + 追加版本记录
        """
        fname  = record.feature_name
        symbol = record.symbol

        existing = self._store.get(fname, {}).get(symbol)
        if existing is not None:
            should, reason = check_overwrite(existing, record)
            if not should:
                return False, reason
            # 生成版本记录
            ver_rec = make_version_record(existing, record)
            self._versions.setdefault(fname, {}).setdefault(symbol, []).append(ver_rec)
            self._overwrite_count += 1
        else:
            # 首次写入：生成初始版本
            init_ver = FeatureVersion(
                feature_name   = fname,
                symbol         = symbol,
                version        = record.version,
                value          = record.value,
                previous_value = 0.0,
                delta          = record.value,
                is_active      = True,
                source_record  = record.source_record,
            )
            self._versions.setdefault(fname, {}).setdefault(symbol, []).append(init_ver)

        self._store.setdefault(fname, {})[symbol] = record
        if record.lineage:
            self._lineage[fname] = record.lineage

        self._write_count += 1
        return True, "ok"

    def write_many(self, records: list[FeatureRecord]) -> dict[str, int]:
        """批量写入。Returns {"written": n, "skipped": m}"""
        written = skipped = 0
        for r in records:
            ok, _ = self.write(r)
            if ok:
                written += 1
            else:
                skipped += 1
        return {"written": written, "skipped": skipped}

    # ── ingest from raw data (auto-compute) ──────────────────────────
    def ingest_market(self, symbol: str,
                       prices: list[float],
                       volumes: list[float],
                       version: int = 1) -> dict[str, int]:
        """从行情数据自动计算并写入标准价格/成交量/波动率特征。"""
        feats = features_from_market(symbol, prices, volumes, version)
        return self.write_many(feats)

    def ingest_alpha(self, feature_name: str, symbol: str,
                      value: float, source_record: str = "",
                      version: int = 1) -> tuple[bool, str]:
        """写入 Alpha 特征。"""
        feat = compute_alpha_feature(value, feature_name, symbol,
                                      source_record, version)
        return self.write(feat)

    def ingest_regime(self, feature_name: str, prob: float,
                       symbol: str = "_market",
                       source_record: str = "",
                       version: int = 1) -> tuple[bool, str]:
        """写入市场状态特征。"""
        feat = compute_regime_feature(prob, feature_name, symbol,
                                       source_record, version)
        return self.write(feat)

    def ingest_execution(self, feature_name: str, value: float,
                          symbol: str = "",
                          source_record: str = "",
                          version: int = 1) -> tuple[bool, str]:
        """写入执行特征。"""
        feat = compute_execution_feature(value, feature_name, symbol,
                                          source_record, version)
        return self.write(feat)

    # ── read ──────────────────────────────────────────────────────────
    def get(self, feature_name: str,
             symbol: str) -> FeatureRecord | None:
        return self._store.get(feature_name, {}).get(symbol)

    def get_by_type(self, feature_type: FeatureType) -> list[FeatureRecord]:
        return [r for sym_dict in self._store.values()
                for r in sym_dict.values()
                if r.feature_type == feature_type]

    def get_by_symbol(self, symbol: str) -> list[FeatureRecord]:
        return [r for sym_dict in self._store.values()
                for r in sym_dict.values()
                if r.symbol == symbol]

    def get_all(self) -> list[FeatureRecord]:
        return [r for sym_dict in self._store.values()
                for r in sym_dict.values()]

    def list_feature_names(self) -> list[str]:
        return sorted(self._store.keys())

    def list_symbols(self) -> list[str]:
        symbols: set[str] = set()
        for sym_dict in self._store.values():
            symbols.update(sym_dict.keys())
        return sorted(symbols)

    # ── lineage ───────────────────────────────────────────────────────
    def get_lineage(self, feature_name: str) -> FeatureLineage | None:
        return self._lineage.get(feature_name)

    def get_all_lineage(self) -> dict[str, FeatureLineage]:
        return dict(self._lineage)

    # ── version history ───────────────────────────────────────────────
    def get_version_history(self, feature_name: str,
                              symbol: str,
                              n: int = 10) -> list[FeatureVersion]:
        return self._versions.get(feature_name, {}).get(symbol, [])[-n:]

    def get_latest_version(self, feature_name: str,
                            symbol: str) -> int:
        hist = self._versions.get(feature_name, {}).get(symbol, [])
        return hist[-1].version if hist else 0

    # ── state ─────────────────────────────────────────────────────────
    def get_state(self) -> FeatureState:
        all_records = self.get_all()
        n = len(all_records)

        type_counts: dict[str, int] = {}
        for r in all_records:
            type_counts[r.feature_type.value] = \
                type_counts.get(r.feature_type.value, 0) + 1

        sym_counts: dict[str, int] = {}
        for r in all_records:
            sym_counts[r.symbol] = sym_counts.get(r.symbol, 0) + 1

        max_ver = max((r.version for r in all_records), default=1)
        total_vers = sum(
            len(hist)
            for sym_dict in self._versions.values()
            for hist in sym_dict.values()
        )

        # write rate (per minute)
        if self._started_at and self._write_count > 0:
            elapsed = (datetime.now() - self._started_at).total_seconds() / 60.0
            rate    = round(self._write_count / max(elapsed, 1/60), 2)
        else:
            rate = 0.0

        return FeatureState(
            total_features   = n,
            active_features  = n,
            type_counts      = type_counts,
            symbol_counts    = sym_counts,
            latest_version   = max_ver,
            total_versions   = total_vers,
            overwrite_count  = self._overwrite_count,
            write_rate       = rate,
            updated_at       = datetime.now(),
        )

    def summary(self) -> dict:
        s = self.get_state()
        return {
            "phase":           2,
            "status":          self._status.value,
            "total_features":  s.total_features,
            "total_versions":  s.total_versions,
            "overwrite_count": s.overwrite_count,
            "write_rate":      s.write_rate,
            "type_counts":     s.type_counts,
        }
