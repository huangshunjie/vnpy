"""
model/stock_pool_model.py

StockPoolModel — 单个股票池的数据容器。

职责：
  - 持有股票池的全部字段（名称、描述、股票列表、时间戳、扩展字段）
  - 提供 to_dict() / from_dict() 序列化
  - 提供纯数据操作（add / remove / deduplicate）

不负责：
  - UI 渲染
  - 文件 I/O
  - 网络请求
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


CURRENT_VERSION = 1


@dataclass
class StockPoolModel:
    """
    单个股票池的数据模型。

    Attributes:
        name:        股票池名称，同时用作持久化文件名（唯一键）。
        description: 可选描述文字。
        symbols:     vt_symbol 列表，例如 ["000001.SZSE", "600519.SSE"]。
        create_time: ISO 格式创建时间字符串。
        update_time: ISO 格式最近更新时间字符串。
        version:     JSON 格式版本号，用于未来兼容升级。
        extra:       预留扩展字段字典，对旧版本透明。
    """

    name: str
    symbols: list[str] = field(default_factory=list)
    description: str = ""
    create_time: str = ""
    update_time: str = ""
    version: int = CURRENT_VERSION
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        now = _now_iso()
        if not self.create_time:
            self.create_time = now
        if not self.update_time:
            self.update_time = now

    # ── 纯数据操作 ─────────────────────────────── #

    def add_symbol(self, vt_symbol: str) -> None:
        """追加一个 vt_symbol（不自动去重，由调用方决定是否先 deduplicate）。"""
        self.symbols.append(vt_symbol)
        self.touch()

    def remove_symbol(self, vt_symbol: str) -> bool:
        """
        移除一个 vt_symbol。

        :return: True 表示成功移除，False 表示原本不存在。
        """
        try:
            self.symbols.remove(vt_symbol)
            self.touch()
            return True
        except ValueError:
            return False

    def set_symbols(self, symbols: list[str]) -> None:
        """整体替换股票列表并更新时间戳。"""
        self.symbols = list(symbols)
        self.touch()

    def deduplicate(self, sort: bool = True) -> int:
        """
        原地去重。

        :param sort: 是否同时按 vt_symbol 字典序排序。
        :return: 删除的重复条目数量。
        """
        before = len(self.symbols)
        seen: set[str] = set()
        unique: list[str] = []
        for s in self.symbols:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        if sort:
            unique.sort()
        self.symbols = unique
        removed = before - len(self.symbols)
        if removed:
            self.touch()
        return removed

    def touch(self) -> None:
        """更新 update_time 为当前时间。"""
        self.update_time = _now_iso()

    # ── 序列化 ─────────────────────────────────── #

    def to_dict(self) -> dict[str, Any]:
        """序列化为可直接 json.dumps 的字典。"""
        return {
            "version":     self.version,
            "name":        self.name,
            "description": self.description,
            "create_time": self.create_time,
            "update_time": self.update_time,
            "symbols":     list(self.symbols),
            "extra":       dict(self.extra),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StockPoolModel":
        """
        从字典反序列化。

        兼容旧版本：缺失字段用默认值补齐，多余字段归入 extra。
        """
        known = {"version", "name", "description",
                 "create_time", "update_time", "symbols", "extra"}
        extra = {k: v for k, v in data.items() if k not in known}
        # 合并到 extra 字段里已有内容
        extra.update(data.get("extra", {}))

        return cls(
            name=        str(data.get("name", "")),
            description= str(data.get("description", "")),
            symbols=     list(data.get("symbols", [])),
            create_time= str(data.get("create_time", "")),
            update_time= str(data.get("update_time", "")),
            version=     int(data.get("version", CURRENT_VERSION)),
            extra=       extra,
        )

    # ── 只读属性 ───────────────────────────────── #

    @property
    def count(self) -> int:
        """股票数量。"""
        return len(self.symbols)

    # ── dunder ─────────────────────────────────── #

    def __repr__(self) -> str:
        return (
            f"StockPoolModel(name={self.name!r}, "
            f"count={self.count}, "
            f"update_time={self.update_time!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StockPoolModel):
            return NotImplemented
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)


# ── 工具函数 ────────────────────────────────────── #

def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
