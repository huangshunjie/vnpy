"""
screening/utils/expression.py

字段取值与比较运算工具（Phase 3）。
"""

from __future__ import annotations
from typing import Any, Optional

from ..constant import CompareOperator


def compare(lhs: Any, op: CompareOperator, rhs: Any) -> bool:
    """
    执行数值比较。
    任意一侧为 None 时返回 True（数据缺失不过滤）。
    """
    if lhs is None or rhs is None:
        return True
    try:
        l = float(lhs)
        r = float(rhs)
    except (TypeError, ValueError):
        return True

    if op == CompareOperator.GT:  return l > r
    if op == CompareOperator.GTE: return l >= r
    if op == CompareOperator.LT:  return l < r
    if op == CompareOperator.LTE: return l <= r
    if op == CompareOperator.EQ:  return abs(l - r) < 1e-9
    if op == CompareOperator.NEQ: return abs(l - r) >= 1e-9
    return True


def parse_value(raw: Any) -> Optional[float]:
    """将原始值转换为 float；支持百分比字符串如 '15%' → 0.15。"""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    if s.endswith("%"):
        try:
            return float(s[:-1]) / 100.0
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def tree_to_expression(tree) -> str:
    """将 ConditionTree 序列化为可读字符串（用于显示/调试）。"""
    if tree is None or tree.root is None:
        return ""
    return _node_to_str(tree.root)


def _node_to_str(node) -> str:
    from ..model.condition import ConditionLeaf, ConditionGroup
    if isinstance(node, ConditionLeaf):
        rhs = f"field({node.value})" if node.value_is_field else str(node.value)
        op = node.operator
        op_str = op.value if hasattr(op, "value") else str(op)
        return f"{node.field_name} {op_str} {rhs}"
    if isinstance(node, ConditionGroup):
        if not node.children:
            return "(empty)"
        parts = [_node_to_str(c) for c in node.children if c]
        op = node.operator
        op_str = op.value if hasattr(op, "value") else str(op)
        if op_str == "NOT":
            return f"NOT ({parts[0] if parts else ''})"
        sep = f" {op_str} "
        inner = sep.join(parts)
        return f"({inner})" if len(parts) > 1 else inner
    return ""


def validate_expression(expr: str) -> tuple:
    """验证表达式语法（简单检查）。返回 (is_valid, error_msg)。"""
    if not expr or not expr.strip():
        return False, "表达式为空"
    return True, ""
