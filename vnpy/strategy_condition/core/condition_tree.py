"""
strategy_condition/core/condition_tree.py

条件树节点：AND / OR / NOT + 叶节点（Condition）的递归组合。

树结构：
  ConditionNode(AND)
  ├── Condition(MACD_GOLDEN)          ← 叶节点
  ├── Condition(WEEKLY_MA_SLOPE)      ← 叶节点
  └── ConditionNode(OR)               ← 子树
      ├── Condition(PULLBACK_PCT)
      └── Condition(PULLBACK_TO_MA)

评估结果：(passed: bool, score: float)
  - AND：所有子节点 passed=True 才通过，score = 加权平均
  - OR ：任一子节点 passed=True 即通过，score = 最高子节点 score
  - NOT：对唯一子节点取反，score = 1 - child.score
  - LEAF：直接返回 Condition 的评估结果（由 condition_engine 填入）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from ..constant import NodeOp
from .condition import Condition, condition_from_dict

# 评估函数签名：(Condition, symbol, bars) -> (bool, float)
EvalFn = Callable[[Condition, str, list], Tuple[bool, float]]


@dataclass
class ConditionNode:
    """
    条件树节点。
    op=LEAF 时 condition 不为 None，children 为空。
    op=AND/OR/NOT 时 children 不为空，condition 为 None。
    """
    op:        NodeOp
    condition: Optional[Condition]       = None   # 叶节点
    children:  List["ConditionNode"]     = field(default_factory=list)
    label:     str                       = ""     # 可选显示标签

    # ── 构建辅助 ──────────────────────────────────────────────────────

    @classmethod
    def leaf(cls, cond: Condition) -> "ConditionNode":
        """创建叶节点"""
        return cls(op=NodeOp.LEAF, condition=cond, label=cond.display_name())

    @classmethod
    def and_node(cls, *children: "ConditionNode",
                 label: str = "AND") -> "ConditionNode":
        return cls(op=NodeOp.AND, children=list(children), label=label)

    @classmethod
    def or_node(cls, *children: "ConditionNode",
                label: str = "OR") -> "ConditionNode":
        return cls(op=NodeOp.OR, children=list(children), label=label)

    @classmethod
    def not_node(cls, child: "ConditionNode",
                 label: str = "NOT") -> "ConditionNode":
        return cls(op=NodeOp.NOT, children=[child], label=label)

    def add_child(self, child: "ConditionNode") -> None:
        if self.op == NodeOp.LEAF:
            raise ValueError("叶节点不能添加子节点")
        self.children.append(child)

    # ── 评估 ──────────────────────────────────────────────────────────

    def evaluate(self, symbol: str, bars: list,
                 eval_fn: EvalFn) -> Tuple[bool, float]:
        """
        递归评估条件树。
        eval_fn：外部注入的叶节点评估函数（由 condition_engine 提供）。
        返回 (passed, score)，score 在 [0, 1] 之间。
        """
        if self.op == NodeOp.LEAF:
            if self.condition is None or not self.condition.enabled:
                return True, 1.0
            return eval_fn(self.condition, symbol, bars)

        if not self.children:
            return True, 1.0

        results = [c.evaluate(symbol, bars, eval_fn) for c in self.children]

        if self.op == NodeOp.AND:
            return self._eval_and(results)
        elif self.op == NodeOp.OR:
            return self._eval_or(results)
        elif self.op == NodeOp.NOT:
            passed, score = results[0]
            return not passed, 1.0 - score
        return True, 1.0

    @staticmethod
    def _eval_and(results: List[Tuple[bool, float]]) -> Tuple[bool, float]:
        """AND：全部通过 + 加权平均 score"""
        if not all(p for p, _ in results):
            return False, 0.0
        scores = [s for _, s in results]
        return True, sum(scores) / len(scores)

    @staticmethod
    def _eval_or(results: List[Tuple[bool, float]]) -> Tuple[bool, float]:
        """OR：任一通过 + 取最高 score"""
        passed_scores = [s for p, s in results if p]
        if not passed_scores:
            return False, 0.0
        return True, max(passed_scores)

    # ── 树遍历 ────────────────────────────────────────────────────────

    def all_conditions(self) -> List[Condition]:
        """返回树中所有叶节点 Condition 的列表（深度优先）"""
        if self.op == NodeOp.LEAF:
            return [self.condition] if self.condition else []
        result = []
        for child in self.children:
            result.extend(child.all_conditions())
        return result

    def depth(self) -> int:
        """树深度"""
        if self.op == NodeOp.LEAF or not self.children:
            return 1
        return 1 + max(c.depth() for c in self.children)

    def count_leaves(self) -> int:
        """叶节点数量"""
        if self.op == NodeOp.LEAF:
            return 1
        return sum(c.count_leaves() for c in self.children)

    # ── JSON 序列化 ───────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"op": self.op.value, "label": self.label}
        if self.op == NodeOp.LEAF:
            d["condition"] = self.condition.to_dict() if self.condition else None
        else:
            d["children"] = [c.to_dict() for c in self.children]
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConditionNode":
        op    = NodeOp(d["op"])
        label = d.get("label", "")
        if op == NodeOp.LEAF:
            cond = condition_from_dict(d["condition"]) if d.get("condition") else None
            return cls(op=op, condition=cond, label=label)
        children = [cls.from_dict(c) for c in d.get("children", [])]
        return cls(op=op, children=children, label=label)

    # ── 显示 ──────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        if self.op == NodeOp.LEAF:
            return f"LEAF({self.condition})"
        return f"{self.op.value}({len(self.children)} children)"

    def pretty(self, indent: int = 0) -> str:
        """生成人类可读的树形字符串"""
        prefix = "  " * indent
        if self.op == NodeOp.LEAF:
            name = self.label or (str(self.condition) if self.condition else "?")
            return f"{prefix}─ {name}"
        lines = [f"{prefix}[{self.op.value}]  {self.label}"]
        for i, child in enumerate(self.children):
            connector = "└─" if i == len(self.children) - 1 else "├─"
            child_str = child.pretty(indent + 1)
            # 替换首行缩进符
            first_line = child_str.split("\n")[0]
            rest_lines = child_str.split("\n")[1:]
            lines.append(f"{'  ' * indent}{connector}{first_line.lstrip()}")
            lines.extend(rest_lines)
        return "\n".join(lines)
