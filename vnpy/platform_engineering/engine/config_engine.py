"""
platform_engineering/engine/config_engine.py
ConfigEngine 完整版 — Phase 6
CRUD + 版本化快照 + 回滚 + 锁定 + 环境标签 + 变更回调 + ConfigDiffEngine
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..model.config import ConfigRecord, ConfigVersion
from ..repository.config_repository import ConfigRepository
from ..constant import ConfigType


# ── ConfigDiffEngine ──────────────────────────────────────────────

class DiffEntry:
    """单个字段的变更记录。"""
    __slots__ = ("key", "op", "old_val", "new_val")

    def __init__(self, key: str, op: str,
                 old_val: Any = None, new_val: Any = None) -> None:
        self.key     = key
        self.op      = op        # "add" | "remove" | "change"
        self.old_val = old_val
        self.new_val = new_val

    def __repr__(self) -> str:
        if self.op == "add":
            return f"[+] {self.key}: {self.new_val!r}"
        if self.op == "remove":
            return f"[-] {self.key}: {self.old_val!r}"
        return f"[~] {self.key}: {self.old_val!r} → {self.new_val!r}"


class ConfigDiffEngine:
    """两版本配置 JSON diff（递归扁平化键路径）。"""

    @staticmethod
    def diff(old: dict, new: dict) -> List[DiffEntry]:
        entries: List[DiffEntry] = []
        ConfigDiffEngine._diff_recursive(old, new, "", entries)
        return entries

    @staticmethod
    def _diff_recursive(
        old: Any, new: Any, prefix: str, out: List[DiffEntry]
    ) -> None:
        if isinstance(old, dict) and isinstance(new, dict):
            all_keys = set(old) | set(new)
            for k in sorted(all_keys):
                path = f"{prefix}.{k}" if prefix else k
                if k not in old:
                    out.append(DiffEntry(path, "add", new_val=new[k]))
                elif k not in new:
                    out.append(DiffEntry(path, "remove", old_val=old[k]))
                else:
                    ConfigDiffEngine._diff_recursive(old[k], new[k], path, out)
        else:
            if old != new:
                out.append(DiffEntry(prefix, "change", old_val=old, new_val=new))

    @staticmethod
    def summary(entries: List[DiffEntry]) -> str:
        adds    = sum(1 for e in entries if e.op == "add")
        removes = sum(1 for e in entries if e.op == "remove")
        changes = sum(1 for e in entries if e.op == "change")
        return f"+{adds} -{removes} ~{changes}"


# ── ConfigEngine ──────────────────────────────────────────────────

class ConfigEngine:
    """
    配置管理引擎。
    - create_config   创建配置项（自动生成初始版本快照）
    - update_config   更新数据（生成新版本快照）
    - rollback_config 回滚到历史版本
    - delete_config   软删除（锁定后禁止删除）
    - lock / unlock   锁定配置（锁定后禁止修改）
    - get_config / list_configs  查询
    - diff_versions   两版本 diff
    - on_config_changed  变更回调
    - export_config / import_config  JSON 序列化
    """

    def __init__(self) -> None:
        self._repo:      ConfigRepository                       = ConfigRepository()
        self._callbacks: List[Callable[[ConfigRecord, str], None]] = []
        self._diff      = ConfigDiffEngine()

    def start(self) -> None: pass
    def stop(self)  -> None: pass

    # ── callback ──────────────────────────────────────────────────

    def on_config_changed(
        self, cb: Callable[[ConfigRecord, str], None]
    ) -> None:
        """cb(record, action)  action: 'create'|'update'|'rollback'|'delete'"""
        self._callbacks.append(cb)

    def _fire(self, rec: ConfigRecord, action: str) -> None:
        for cb in self._callbacks:
            try:
                cb(rec, action)
            except Exception:
                pass

    # ── create ────────────────────────────────────────────────────

    def create_config(
        self,
        name:        str,
        config_type: ConfigType = ConfigType.STRATEGY,
        data:        dict       = None,
        description: str        = "",
        owner:       str        = "",
        tags:        List[str]  = None,
        created_by:  str        = "",
        note:        str        = "",
    ) -> ConfigRecord:
        rec = ConfigRecord(
            config_id   = "CFG-" + uuid.uuid4().hex[:8].upper(),
            name        = name,
            config_type = config_type,
            current_data= data or {},
            description = description,
            owner       = owner,
            tags        = tags or [],
            is_locked   = False,
            created_by  = created_by,
            created_at  = datetime.now(),
            updated_at  = datetime.now(),
        )
        # initial version snapshot
        ver = self._snap(rec, note=note or "初始版本", created_by=created_by)
        self._repo.save(rec)
        self._fire(rec, "create")
        return rec

    # ── update ────────────────────────────────────────────────────

    def update_config(
        self,
        config_id: str,
        data:      dict,
        note:      str = "",
        updated_by:str = "",
    ) -> Optional[ConfigVersion]:
        rec = self._get_or_raise(config_id)
        if rec.is_locked:
            raise ValueError(f"配置 {config_id} 已锁定，无法修改")
        rec.current_data = data
        rec.updated_at   = datetime.now()
        ver = self._snap(rec, note=note or "更新配置", created_by=updated_by)
        self._repo.save(rec)
        self._fire(rec, "update")
        return ver

    def patch_config(
        self,
        config_id: str,
        patch:     dict,
        note:      str = "",
        updated_by:str = "",
    ) -> Optional[ConfigVersion]:
        """合并更新（深度 merge），而非全量替换。"""
        rec = self._get_or_raise(config_id)
        if rec.is_locked:
            raise ValueError(f"配置 {config_id} 已锁定，无法修改")
        merged = {**rec.current_data, **patch}
        return self.update_config(config_id, merged,
                                  note=note or "合并更新", updated_by=updated_by)

    # ── rollback ──────────────────────────────────────────────────

    def rollback_config(
        self,
        config_id:  str,
        version_id: str,
        note:       str = "",
        operator:   str = "",
    ) -> bool:
        rec = self._get_or_raise(config_id)
        if rec.is_locked:
            raise ValueError(f"配置 {config_id} 已锁定，无法回滚")
        ver = next((v for v in rec.versions if v.version_id == version_id), None)
        if not ver:
            return False
        rec.current_data = ver.data.copy()
        rec.updated_at   = datetime.now()
        self._snap(rec,
                   note=note or f"回滚到 {ver.version_tag}",
                   created_by=operator)
        self._repo.save(rec)
        self._fire(rec, "rollback")
        return True

    # ── lock / unlock ─────────────────────────────────────────────

    def lock(self, config_id: str, operator: str = "") -> ConfigRecord:
        rec = self._get_or_raise(config_id)
        rec.is_locked  = True
        rec.updated_at = datetime.now()
        self._snap(rec, note=f"锁定配置", created_by=operator)
        self._repo.save(rec)
        self._fire(rec, "lock")
        return rec

    def unlock(self, config_id: str, operator: str = "") -> ConfigRecord:
        rec = self._get_or_raise(config_id)
        rec.is_locked  = False
        rec.updated_at = datetime.now()
        self._snap(rec, note="解锁配置", created_by=operator)
        self._repo.save(rec)
        self._fire(rec, "unlock")
        return rec

    # ── delete ────────────────────────────────────────────────────

    def delete_config(self, config_id: str) -> bool:
        rec = self._get_or_raise(config_id)
        if rec.is_locked:
            raise ValueError(f"配置 {config_id} 已锁定，无法删除")
        self._repo.delete(config_id)
        self._fire(rec, "delete")
        return True

    # ── query ─────────────────────────────────────────────────────

    def get_config(self, config_id: str) -> Optional[ConfigRecord]:
        return self._repo.get(config_id)

    def list_configs(
        self,
        config_type: Optional[ConfigType] = None,
        owner:       Optional[str]        = None,
    ) -> List[ConfigRecord]:
        items = self._repo.list()
        if config_type:
            items = [c for c in items if c.config_type == config_type]
        if owner:
            items = [c for c in items if c.owner == owner]
        return sorted(items, key=lambda c: c.updated_at, reverse=True)

    def search_configs(self, keyword: str) -> List[ConfigRecord]:
        kw = keyword.lower()
        return [c for c in self._repo.list()
                if kw in c.name.lower() or kw in c.description.lower()]

    # ── diff ──────────────────────────────────────────────────────

    def diff_versions(
        self,
        config_id:   str,
        version_id_a: str,
        version_id_b: str,
    ) -> Tuple[List[DiffEntry], str]:
        """返回 (entries, summary_string)。"""
        rec = self._get_or_raise(config_id)
        va  = next((v for v in rec.versions if v.version_id == version_id_a), None)
        vb  = next((v for v in rec.versions if v.version_id == version_id_b), None)
        if not va or not vb:
            return [], "无法找到版本"
        entries = self._diff.diff(va.data, vb.data)
        return entries, self._diff.summary(entries)

    def diff_with_current(
        self, config_id: str, version_id: str
    ) -> Tuple[List[DiffEntry], str]:
        """历史版本与当前数据 diff。"""
        rec = self._get_or_raise(config_id)
        ver = next((v for v in rec.versions if v.version_id == version_id), None)
        if not ver:
            return [], "版本不存在"
        entries = self._diff.diff(ver.data, rec.current_data)
        return entries, self._diff.summary(entries)

    # ── import / export ───────────────────────────────────────────

    def export_config(self, config_id: str) -> str:
        """导出当前配置为 JSON 字符串。"""
        rec = self._get_or_raise(config_id)
        return json.dumps({
            "config_id":   rec.config_id,
            "name":        rec.name,
            "config_type": rec.config_type.value,
            "data":        rec.current_data,
            "description": rec.description,
            "owner":       rec.owner,
            "tags":        rec.tags,
            "exported_at": datetime.now().isoformat(),
        }, ensure_ascii=False, indent=2)

    def import_config(
        self,
        json_str:   str,
        created_by: str = "",
        note:       str = "从 JSON 导入",
    ) -> ConfigRecord:
        """从 JSON 字符串导入（创建新配置项）。"""
        obj  = json.loads(json_str)
        ctype = next(
            (t for t in ConfigType if t.value == obj.get("config_type", "")),
            ConfigType.SYSTEM,
        )
        return self.create_config(
            name        = obj.get("name", "imported"),
            config_type = ctype,
            data        = obj.get("data", {}),
            description = obj.get("description", ""),
            owner       = obj.get("owner", ""),
            tags        = obj.get("tags", []),
            created_by  = created_by,
            note        = note,
        )

    # ── helpers ───────────────────────────────────────────────────

    def _get_or_raise(self, config_id: str) -> ConfigRecord:
        rec = self._repo.get(config_id)
        if not rec:
            raise KeyError(f"配置 {config_id} 不存在")
        return rec

    def _snap(
        self,
        rec:        ConfigRecord,
        note:       str = "",
        created_by: str = "",
    ) -> ConfigVersion:
        ver = ConfigVersion(
            version_id  = "VER-" + uuid.uuid4().hex[:8].upper(),
            version_tag = f"v{len(rec.versions)+1}",
            data        = rec.current_data.copy(),
            note        = note,
            created_by  = created_by,
            created_at  = datetime.now(),
        )
        rec.versions.append(ver)
        return ver

    # ── stats ─────────────────────────────────────────────────────

    def stats(self) -> dict:
        items = self._repo.list()
        return {
            "total":  len(items),
            "locked": sum(1 for c in items if c.is_locked),
            "by_type": {
                t.value: sum(1 for c in items if c.config_type == t)
                for t in ConfigType
            },
            "total_versions": sum(len(c.versions) for c in items),
        }
