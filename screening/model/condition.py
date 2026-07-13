"""
screening/model/condition.py
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Any

from ..constant import ConditionOperator, CompareOperator, ConditionFieldType


def _op_val(op) -> str:
    return op.value if hasattr(op, "value") else str(op)


class ConditionNode(ABC):
    @abstractmethod
    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, d: dict) -> "ConditionNode":
        if d.get("node_type") == "leaf":
            return ConditionLeaf.from_dict(d)
        return ConditionGroup.from_dict(d)


@dataclass
class ConditionLeaf(ConditionNode):
    field_name: str
    field_type: ConditionFieldType
    operator: CompareOperator
    value: Any
    value_is_field: bool = False
    description: str = ""
    enabled: bool = True

    def __post_init__(self):
        if not isinstance(self.operator, CompareOperator):
            self.operator = CompareOperator(str(self.operator))
        if not isinstance(self.field_type, ConditionFieldType):
            self.field_type = ConditionFieldType(str(self.field_type))

    @property
    def node_type(self) -> str:
        return "leaf"

    def to_dict(self) -> dict:
        return {
            "node_type": "leaf",
            "field_name": self.field_name,
            "field_type": _op_val(self.field_type),
            "operator": _op_val(self.operator),
            "value": self.value,
            "value_is_field": self.value_is_field,
            "description": self.description,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ConditionLeaf":
        return cls(
            field_name=d["field_name"],
            field_type=ConditionFieldType(d["field_type"]),
            operator=CompareOperator(d["operator"]),
            value=d["value"],
            value_is_field=bool(d.get("value_is_field", False)),
            description=d.get("description", ""),
            enabled=bool(d.get("enabled", True)),
        )

    def __repr__(self) -> str:
        rhs = f"field({self.value})" if self.value_is_field else str(self.value)
        return f"{self.field_name} {_op_val(self.operator)} {rhs}"


@dataclass
class ConditionGroup(ConditionNode):
    operator: ConditionOperator
    children: List[ConditionNode] = field(default_factory=list)
    description: str = ""
    enabled: bool = True

    def __post_init__(self):
        if not isinstance(self.operator, ConditionOperator):
            self.operator = ConditionOperator(str(self.operator))

    @property
    def node_type(self) -> str:
        return "group"

    def add_child(self, node: ConditionNode) -> None:
        self.children.append(node)

    def to_dict(self) -> dict:
        return {
            "node_type": "group",
            "operator": _op_val(self.operator),
            "children": [c.to_dict() for c in self.children],
            "description": self.description,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ConditionGroup":
        grp = cls(
            operator=ConditionOperator(d["operator"]),
            description=d.get("description", ""),
            enabled=bool(d.get("enabled", True)),
        )
        for child_dict in d.get("children", []):
            grp.children.append(ConditionNode.from_dict(child_dict))
        return grp

    def __repr__(self) -> str:
        parts = [repr(c) for c in self.children]
        op_str = _op_val(self.operator)
        if op_str == "NOT":
            return f"NOT ({parts[0] if parts else ''})"
        return f"({f' {op_str} '.join(parts)})"


@dataclass
class ConditionTree:
    root: Optional[ConditionNode] = None
    name: str = "untitled"
    description: str = ""

    def is_empty(self) -> bool:
        return self.root is None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "root": self.root.to_dict() if self.root else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ConditionTree":
        root_dict = d.get("root")
        return cls(
            name=d.get("name", "untitled"),
            description=d.get("description", ""),
            root=ConditionNode.from_dict(root_dict) if root_dict else None,
        )

    @classmethod
    def empty(cls) -> "ConditionTree":
        return cls(root=ConditionGroup(operator=ConditionOperator.AND))

    def __repr__(self) -> str:
        return f"ConditionTree(name={self.name!r}, root={self.root!r})"
