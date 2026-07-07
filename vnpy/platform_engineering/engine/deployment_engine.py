"""
platform_engineering/engine/deployment_engine.py
DeploymentEngine 完整版 — Phase 4
状态机 + 审批工作流 + 版本快照 + 冻结/回滚
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional

from ..model.deployment import DeploymentRecord, DeployVersion
from ..constant import DeployStage, DeployAction


# ── valid transitions ─────────────────────────────────────────────
# 每个阶段允许推进到哪些阶段
_TRANSITIONS: Dict[DeployStage, List[DeployStage]] = {
    DeployStage.RESEARCH:      [DeployStage.VALIDATION],
    DeployStage.VALIDATION:    [DeployStage.APPROVAL, DeployStage.RESEARCH],
    DeployStage.APPROVAL:      [DeployStage.PAPER_TRADING, DeployStage.VALIDATION],
    DeployStage.PAPER_TRADING: [DeployStage.PRODUCTION, DeployStage.VALIDATION],
    DeployStage.PRODUCTION:    [DeployStage.PAUSED, DeployStage.ROLLED_BACK,
                                DeployStage.RETIRED],
    DeployStage.PAUSED:        [DeployStage.PRODUCTION, DeployStage.ROLLED_BACK,
                                DeployStage.RETIRED],
    DeployStage.ROLLED_BACK:   [DeployStage.RESEARCH],
    DeployStage.RETIRED:       [],
}

# 需要 approver 才能推进的阶段
_REQUIRE_APPROVAL = {DeployStage.PAPER_TRADING, DeployStage.PRODUCTION}


class DeploymentEngine:
    """
    策略部署管理引擎。
    - 创建/查询/列出部署记录
    - 状态机推进（含合法性校验）
    - 审批工作流（submit_for_approval / approve / reject）
    - 版本快照（add_version / rollback_to_version）
    - 冻结/解冻（freeze / unfreeze）
    - 完成回调（on_stage_changed）
    """

    def __init__(self) -> None:
        self._records:   Dict[str, DeploymentRecord] = {}
        self._callbacks: List[Callable[[DeploymentRecord, DeployStage], None]] = []

    def start(self) -> None: pass
    def stop(self)  -> None: pass

    # ── callback ──────────────────────────────────────────────────

    def on_stage_changed(
        self, cb: Callable[[DeploymentRecord, DeployStage], None]
    ) -> None:
        self._callbacks.append(cb)

    def _fire(self, rec: DeploymentRecord, prev: DeployStage) -> None:
        for cb in self._callbacks:
            try:
                cb(rec, prev)
            except Exception:
                pass

    # ── create ────────────────────────────────────────────────────

    def create_deployment(
        self,
        strategy_id:   str,
        strategy_name: str,
        created_by:    str = "",
        tags:          List[str] = None,
        note:          str = "",
    ) -> DeploymentRecord:
        rec = DeploymentRecord(
            deploy_id     = "DEP-" + uuid.uuid4().hex[:8].upper(),
            strategy_id   = strategy_id,
            strategy_name = strategy_name,
            current_stage = DeployStage.RESEARCH,
            tags          = tags or [],
            created_by    = created_by,
            created_at    = datetime.now(),
            updated_at    = datetime.now(),
        )
        # create initial version snapshot
        self._snap(rec, note=note or "初始版本", created_by=created_by)
        self._records[rec.deploy_id] = rec
        return rec

    # ── query ─────────────────────────────────────────────────────

    def get_deployment(self, deploy_id: str) -> Optional[DeploymentRecord]:
        return self._records.get(deploy_id)

    def list_deployments(
        self, stage: Optional[DeployStage] = None
    ) -> List[DeploymentRecord]:
        items = list(self._records.values())
        if stage:
            items = [d for d in items if d.current_stage == stage]
        return sorted(items, key=lambda d: d.updated_at, reverse=True)

    # ── state machine ─────────────────────────────────────────────

    def advance_stage(
        self,
        deploy_id: str,
        stage:     DeployStage,
        operator:  str = "",
        note:      str = "",
    ) -> DeploymentRecord:
        rec = self._get_or_raise(deploy_id)
        if rec.is_frozen:
            raise ValueError(f"部署 {deploy_id} 已冻结，无法推进阶段")
        allowed = _TRANSITIONS.get(rec.current_stage, [])
        if stage not in allowed:
            raise ValueError(
                f"不允许从 {rec.current_stage.value} 推进到 {stage.value}")
        if stage in _REQUIRE_APPROVAL and not rec.approver:
            raise ValueError(
                f"推进到 {stage.value} 需要先完成审批")
        prev = rec.current_stage
        rec.current_stage = stage
        rec.updated_at    = datetime.now()
        if stage == DeployStage.PRODUCTION:
            rec.live_at    = datetime.now()
        elif stage == DeployStage.PAUSED:
            rec.paused_at  = datetime.now()
        elif stage == DeployStage.RETIRED:
            rec.retired_at = datetime.now()
        self._snap(rec, note=note or f"推进到 {stage.value}", created_by=operator)
        self._fire(rec, prev)
        return rec

    # ── approval workflow ─────────────────────────────────────────

    def submit_for_approval(
        self,
        deploy_id: str,
        note:      str = "",
    ) -> DeploymentRecord:
        """将处于 VALIDATION 阶段的部署提交审批。"""
        rec = self._get_or_raise(deploy_id)
        if rec.current_stage != DeployStage.VALIDATION:
            raise ValueError("只有处于 VALIDATION 阶段才能提交审批")
        prev = rec.current_stage
        rec.current_stage = DeployStage.APPROVAL
        rec.updated_at    = datetime.now()
        self._snap(rec, note=note or "提交审批", created_by="system")
        self._fire(rec, prev)
        return rec

    def approve(
        self,
        deploy_id: str,
        approver:  str,
        note:      str = "",
    ) -> DeploymentRecord:
        """审批通过 → 可推进到 PAPER_TRADING。"""
        rec = self._get_or_raise(deploy_id)
        if rec.current_stage != DeployStage.APPROVAL:
            raise ValueError("只有处于 APPROVAL 阶段才能审批")
        rec.approver      = approver
        rec.approve_note  = note
        rec.approved_at   = datetime.now()
        rec.updated_at    = datetime.now()
        self._snap(rec, note=f"审批通过: {note}", created_by=approver)
        return rec

    def reject(
        self,
        deploy_id: str,
        approver:  str,
        note:      str = "",
    ) -> DeploymentRecord:
        """审批拒绝 → 回到 VALIDATION。"""
        rec = self._get_or_raise(deploy_id)
        if rec.current_stage != DeployStage.APPROVAL:
            raise ValueError("只有处于 APPROVAL 阶段才能拒绝")
        prev = rec.current_stage
        rec.current_stage = DeployStage.VALIDATION
        rec.approver      = ""
        rec.approve_note  = f"[拒绝] {note}"
        rec.updated_at    = datetime.now()
        self._snap(rec, note=f"审批拒绝: {note}", created_by=approver)
        self._fire(rec, prev)
        return rec

    # ── version management ────────────────────────────────────────

    def add_version(
        self,
        deploy_id:       str,
        version_tag:     str = "",
        config_snapshot: dict = None,
        commit_hash:     str = "",
        note:            str = "",
        created_by:      str = "",
    ) -> Optional[DeployVersion]:
        rec = self._records.get(deploy_id)
        if not rec:
            return None
        ver = DeployVersion(
            version_id       = "VER-" + uuid.uuid4().hex[:8].upper(),
            version_tag      = version_tag or f"v{len(rec.versions)+1}",
            stage            = rec.current_stage,
            config_snapshot  = config_snapshot or {},
            commit_hash      = commit_hash,
            note             = note,
            created_by       = created_by,
            created_at       = datetime.now(),
        )
        rec.versions.append(ver)
        rec.current_version = ver.version_id
        rec.updated_at      = datetime.now()
        return ver

    def rollback_to_version(
        self,
        deploy_id:  str,
        version_id: str,
        operator:   str = "",
    ) -> DeploymentRecord:
        rec = self._get_or_raise(deploy_id)
        ver = next((v for v in rec.versions if v.version_id == version_id), None)
        if not ver:
            raise ValueError(f"版本 {version_id} 不存在")
        prev = rec.current_stage
        rec.current_stage   = DeployStage.ROLLED_BACK
        rec.current_version = version_id
        rec.updated_at      = datetime.now()
        self._snap(rec, note=f"回滚到 {ver.version_tag}", created_by=operator)
        self._fire(rec, prev)
        return rec

    # ── freeze / unfreeze ─────────────────────────────────────────

    def freeze(self, deploy_id: str, operator: str = "") -> DeploymentRecord:
        rec = self._get_or_raise(deploy_id)
        rec.is_frozen  = True
        rec.updated_at = datetime.now()
        self._snap(rec, note="冻结部署", created_by=operator)
        return rec

    def unfreeze(self, deploy_id: str, operator: str = "") -> DeploymentRecord:
        rec = self._get_or_raise(deploy_id)
        rec.is_frozen  = False
        rec.updated_at = datetime.now()
        self._snap(rec, note="解冻部署", created_by=operator)
        return rec

    # ── helpers ───────────────────────────────────────────────────

    def _get_or_raise(self, deploy_id: str) -> DeploymentRecord:
        rec = self._records.get(deploy_id)
        if not rec:
            raise KeyError(f"部署 {deploy_id} 不存在")
        return rec

    def _snap(
        self,
        rec:        DeploymentRecord,
        note:       str = "",
        created_by: str = "",
    ) -> DeployVersion:
        ver = DeployVersion(
            version_id      = "VER-" + uuid.uuid4().hex[:8].upper(),
            version_tag     = f"v{len(rec.versions)+1}",
            stage           = rec.current_stage,
            config_snapshot = {},
            note            = note,
            created_by      = created_by,
            created_at      = datetime.now(),
        )
        rec.versions.append(ver)
        rec.current_version = ver.version_id
        return ver

    # ── stats ─────────────────────────────────────────────────────

    def stats(self) -> dict:
        items = list(self._records.values())
        return {
            "total":  len(items),
            "frozen": sum(1 for d in items if d.is_frozen),
            "by_stage": {
                s.value: sum(1 for d in items if d.current_stage == s)
                for s in DeployStage
            },
        }
