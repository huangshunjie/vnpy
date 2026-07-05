"""
adaptive_learning_ai/engine/update_engine.py  (Phase 5)

UpdateEngine — 系统更新引擎。

职责：
  - 接收 AdaptationRecord 列表，生成 ModelVersion 记录
  - 维护参数版本历史（支持回滚）
  - 策略重权（strategy reweighting）
  - 发出系统级更新摘要
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable
import uuid

from ..constant import AdaptationTarget, UpdateStrategy, SystemStatus
from ..model.adaptation_model import AdaptationRecord
from ..model.system_model     import ModelVersion, SystemUpdateRecord


class UpdateEngine:
    """系统更新引擎（Phase 5 完整实现）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log     = log_fn or (lambda m: None)
        self._status  = SystemStatus.IDLE
        self._cycle   = 0

        # 版本历史：{target.value: {entity_id: [ModelVersion, ...]}}
        self._versions: dict[str, dict[str, list[ModelVersion]]] = {
            t.value: {} for t in AdaptationTarget}

        self._update_records: list[SystemUpdateRecord] = []

    def init(self)  -> None: self._log("[UpdateEngine] init()")
    def start(self) -> None:
        self._status = SystemStatus.COLLECTING
        self._log("[UpdateEngine] start()")

    def stop(self)  -> None:
        self._status = SystemStatus.STOPPED
        self._log("[UpdateEngine] stop()")

    # ── core: apply adaptation records → model versions ──────────────
    def apply_records(
        self,
        records: list[AdaptationRecord],
        cycle:   int = 0,
        trigger: str = "adaptation",
    ) -> SystemUpdateRecord:
        """
        将已应用的 AdaptationRecord 列表转化为 ModelVersion，
        生成 SystemUpdateRecord 并存档。
        """
        self._status = SystemStatus.UPDATING
        versions: list[ModelVersion] = []
        targets_seen: set[str]  = set()
        entities_seen: set[str] = set()
        total_improvement = 0.0

        for rec in records:
            if not rec.success:
                continue
            target_key = rec.target.value
            eid        = rec.entity_id

            hist = self._versions[target_key].setdefault(eid, [])
            ver_num = len(hist) + 1

            mv = ModelVersion(
                version_id     = f"VER_{uuid.uuid4().hex[:8].upper()}",
                version        = ver_num,
                target         = target_key,
                entity_id      = eid,
                value          = rec.value_after,
                previous_value = rec.value_before,
                delta          = rec.actual_delta,
                source         = rec.proposal_id,
                is_active      = True,
            )
            # mark previous version inactive
            for old in hist:
                old.is_active = False
            hist.append(mv)
            versions.append(mv)
            targets_seen.add(target_key)
            entities_seen.add(eid)
            # proxy improvement: delta toward target (negative is usually good)
            total_improvement += abs(rec.actual_delta)

        avg_imp = round(total_improvement / max(len(versions), 1), 6)

        ur = SystemUpdateRecord(
            update_id        = f"UPD_{uuid.uuid4().hex[:8].upper()}",
            cycle            = cycle,
            trigger          = trigger,
            n_params_updated = len(versions),
            n_rollbacks      = 0,
            targets_affected = sorted(targets_seen),
            entities_updated = sorted(entities_seen),
            avg_improvement  = avg_imp,
            confidence       = (sum(r.actual_delta for r in records if r.success)
                                 / max(len(records), 1)),
            success          = True,
            versions         = versions,
        )
        self._update_records.append(ur)
        self._status = SystemStatus.COLLECTING
        self._log(
            f"[UpdateEngine] update: cycle={cycle} "
            f"params={len(versions)} targets={sorted(targets_seen)}")
        return ur

    # ── rollback ─────────────────────────────────────────────────────
    def rollback(
        self,
        target:    AdaptationTarget,
        entity_id: str,
        n_steps:   int = 1,
    ) -> ModelVersion | None:
        """
        回滚到指定参数的第 n_steps 前版本。
        Returns the version that was restored.
        """
        hist = self._versions[target.value].get(entity_id, [])
        if len(hist) <= n_steps:
            self._log(
                f"[UpdateEngine] rollback: not enough history for "
                f"{target.value}/{entity_id}")
            return None

        # 激活 n_steps 之前的版本
        for v in hist:
            v.is_active = False
        restore_ver = hist[-(n_steps + 1)]
        restore_ver.is_active = True

        # 记录回滚
        rollback_mv = ModelVersion(
            version_id     = f"VER_{uuid.uuid4().hex[:8].upper()}",
            version        = len(hist) + 1,
            target         = target.value,
            entity_id      = entity_id,
            value          = restore_ver.value,
            previous_value = hist[-1].value,
            delta          = restore_ver.value - hist[-1].value,
            source         = "rollback",
            is_active      = True,
        )
        hist.append(rollback_mv)

        # 更新 update_records 中的 rollback count
        if self._update_records:
            self._update_records[-1].n_rollbacks += 1

        self._log(
            f"[UpdateEngine] rollback {target.value}/{entity_id}: "
            f"{hist[-2].value:.6f} → {restore_ver.value:.6f}")
        return rollback_mv

    # ── strategy reweighting ──────────────────────────────────────────
    def reweight_strategies(
        self,
        performance_scores: dict[str, float],  # {entity_id: score [0,100]}
        target: AdaptationTarget = AdaptationTarget.STRATEGY_ALLOCATION,
        blend_factor: float = 0.2,
    ) -> list[ModelVersion]:
        """
        根据绩效评分对策略权重重新赋权。
        使用 softmax 归一化 → blend 更新。
        """
        import math
        scores    = list(performance_scores.values())
        ids       = list(performance_scores.keys())
        max_score = max(scores) if scores else 1.0

        # softmax
        exps  = [math.exp((s - max_score) / 20.0) for s in scores]
        total = sum(exps) or 1.0
        new_weights = [e / total for e in exps]

        versions = []
        for eid, new_w in zip(ids, new_weights):
            hist = self._versions[target.value].setdefault(eid, [])
            cur  = hist[-1].value if hist else (1.0 / len(ids))
            blended = cur + blend_factor * (new_w - cur)

            for v in hist:
                v.is_active = False
            mv = ModelVersion(
                version_id     = f"VER_{uuid.uuid4().hex[:8].upper()}",
                version        = len(hist) + 1,
                target         = target.value,
                entity_id      = eid,
                value          = round(blended, 8),
                previous_value = cur,
                delta          = round(blended - cur, 8),
                source         = "reweight",
                is_active      = True,
            )
            hist.append(mv)
            versions.append(mv)

        self._log(
            f"[UpdateEngine] reweight: {len(versions)} strategies updated")
        return versions

    # ── query ─────────────────────────────────────────────────────────
    def get_current_version(
        self,
        target:    AdaptationTarget,
        entity_id: str,
    ) -> ModelVersion | None:
        hist = self._versions[target.value].get(entity_id, [])
        active = [v for v in hist if v.is_active]
        return active[-1] if active else (hist[-1] if hist else None)

    def get_version_history(
        self,
        target:    AdaptationTarget,
        entity_id: str,
        n:         int = 10,
    ) -> list[ModelVersion]:
        return self._versions[target.value].get(entity_id, [])[-n:]

    def get_update_records(self, n: int = 20) -> list[SystemUpdateRecord]:
        return self._update_records[-n:]

    def summary(self) -> dict:
        total_versions = sum(
            len(hist)
            for tgt_dict in self._versions.values()
            for hist in tgt_dict.values()
        )
        return {
            "phase":          5,
            "status":         self._status.value,
            "total_updates":  len(self._update_records),
            "total_versions": total_versions,
            "n_rollbacks":    sum(r.n_rollbacks for r in self._update_records),
        }
