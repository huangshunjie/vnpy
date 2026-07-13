"""
temporal_intelligence_ai/datasource/alpha_loader.py

Alpha 数据加载器。

从 VeighNa 内部状态（Portfolio State / Execution Logs）读取
Alpha 信号记录，供 DecayEngine 使用。

设计原则：
  - 只读历史已记录的 Alpha 信号，无前瞻偏差
  - Alpha 记录以 dict 形式存储（兼容无外部 Alpha 模块时的降级处理）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class AlphaRecord:
    """
    单个 Alpha 信号记录。

    由策略 / Portfolio 层写入，DecayEngine 只读消费。
    """
    alpha_id:        str      = ""
    created_bar:     int      = 0       # 信号创建时的全局 bar 计数
    created_at:      datetime = field(default_factory=datetime.now)
    initial_strength: float   = 1.0    # 信号创建时的初始强度
    base_decay_rate: float    = 0.05   # 基础衰减率 λ（由信号来源指定）
    signal_type:     str      = ""     # 信号类型标签（可选）
    metadata:        dict     = field(default_factory=dict)


class AlphaLoader:
    """
    Alpha 信号数据加载器。

    当前阶段使用内存注册表（register / load 模式），
    后续可对接外部 Alpha Factory 或数据库。
    """

    def __init__(self) -> None:
        self._registry: dict[str, AlphaRecord] = {}

    # ── write ────────────────────────────────────────────────────────

    def register(self, record: AlphaRecord) -> None:
        """
        注册一条 Alpha 信号记录。

        同一 alpha_id 重复注册时覆盖（视为信号更新）。
        """
        self._registry[record.alpha_id] = record

    def register_many(self, records: List[AlphaRecord]) -> None:
        """批量注册 Alpha 记录。"""
        for r in records:
            self.register(r)

    # ── read ─────────────────────────────────────────────────────────

    def load(self, alpha_id: str) -> Optional[AlphaRecord]:
        """按 alpha_id 查询单条记录，不存在时返回 None。"""
        return self._registry.get(alpha_id)

    def load_all(self) -> List[AlphaRecord]:
        """返回所有已注册的 Alpha 记录列表。"""
        return list(self._registry.values())

    def load_active(self, current_bar: int,
                    max_age: int = 500) -> List[AlphaRecord]:
        """
        返回仍在有效存续期内的 Alpha 记录。

        Args:
            current_bar: 当前全局 bar 计数
            max_age:     最大允许存续 bar 数（超出视为强制到期）
        """
        result = []
        for rec in self._registry.values():
            age = current_bar - rec.created_bar
            if 0 <= age <= max_age:
                result.append(rec)
        return result

    def remove(self, alpha_id: str) -> None:
        """移除一条 Alpha 记录。"""
        self._registry.pop(alpha_id, None)

    def clear(self) -> None:
        """清空所有记录（引擎重置时使用）。"""
        self._registry.clear()

    @property
    def count(self) -> int:
        return len(self._registry)
