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
    # SEQUENCE 专用：相邻步骤之间允许的最大间隔（K线根数）。
    # step_gap[i] 表示第 i+1 步必须在第 i 步之后的 step_gap[i] 根K线内发生。
    # 长度不足或为空时，对应间隔使用 default_gap。
    step_gap:  List[int]                 = field(default_factory=list)
    # SEQUENCE 专用：默认最大间隔（K线根数），0 表示不限制
    default_gap: int                     = 0
    # SEQUENCE 专用：最后一步必须落在最近 recent_window 根K线内才算"当前触发"
    # 0 表示不限制（只要序列在历史上完整出现过即可）
    recent_window: int                   = 5

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
    def sequence_node(cls, *children: "ConditionNode",
                      default_gap: int = 0, recent_window: int = 5,
                      step_gap: Optional[List[int]] = None,
                      label: str = "SEQUENCE") -> "ConditionNode":
        return cls(op=NodeOp.SEQUENCE, children=list(children),
                   label=label, step_gap=step_gap or [],
                   default_gap=default_gap, recent_window=recent_window)

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

        if self.op == NodeOp.SEQUENCE:
            return self._eval_sequence(symbol, bars, eval_fn)
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

    def _eval_sequence(self, symbol: str, bars: list,
                       eval_fn: EvalFn) -> Tuple[bool, float]:
        """
        SEQUENCE：子条件按时间先后依次发生（时序序列匹配）。

        算法（正向贪婪匹配）：
          利用"叶条件只判断序列最后一根K线是否满足"的特性，通过对
          bars[:k+1] 前缀切片，即可探测"某条件在第 k 根K线成立"。
          - 从头到尾扫描K线，依次为每个子步骤寻找最早的成立位置；
          - 第 i+1 步的成立位置必须严格晚于第 i 步；
          - 相邻两步间隔不得超过 gap（step_gap[i] 或 default_gap，
            0 表示不限制）；
          - 全部步骤匹配成功后，最后一步的位置必须落在最近
            recent_window 根K线内（recent_window=0 表示不限制），
            以保证"当前时刻"确实处于序列末端，而非久远的历史形态。

        返回 (passed, score)。score 为各步成立时评分的平均值。
        """
        steps = [c for c in self.children]
        if not steps:
            return True, 1.0

        n = len(bars)
        # 每个子步骤在某个前缀位置的评估结果做缓存，避免重复计算
        # cache[step_idx][k] = (passed, score)
        cache: List[dict] = [dict() for _ in steps]

        def step_at(step_idx: int, k: int) -> Tuple[bool, float]:
            """判断第 step_idx 步是否在"截至第 k 根K线"时成立。"""
            c = cache[step_idx]
            if k in c:
                return c[k]
            res = steps[step_idx].evaluate(symbol, bars[:k + 1], eval_fn)
            c[k] = res
            return res

        matched_pos: List[int] = []
        matched_score: List[float] = []
        search_start = 0
        for si in range(len(steps)):
            # 该步允许的最大间隔（相对上一步位置）
            if si == 0:
                gap = 0            # 首步不受间隔约束
            elif si - 1 < len(self.step_gap) and self.step_gap[si - 1] > 0:
                gap = self.step_gap[si - 1]
            else:
                gap = self.default_gap

            found = -1
            found_score = 0.0
            upper = n - 1
            if si > 0 and gap > 0:
                upper = min(n - 1, matched_pos[-1] + gap)
            for k in range(search_start, upper + 1):
                ok, sc = step_at(si, k)
                if ok:
                    found = k
                    found_score = sc
                    break
            if found < 0:
                return False, 0.0
            matched_pos.append(found)
            matched_score.append(found_score)
            search_start = found + 1     # 下一步必须严格晚于本步

        # 最后一步必须落在最近 recent_window 根K线内
        if self.recent_window and self.recent_window > 0:
            if matched_pos[-1] < n - self.recent_window:
                return False, 0.0

        avg = sum(matched_score) / len(matched_score)
        return True, avg

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
            if self.op == NodeOp.SEQUENCE:
                d["step_gap"]      = list(self.step_gap)
                d["default_gap"]   = self.default_gap
                d["recent_window"] = self.recent_window
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConditionNode":
        op    = NodeOp(d["op"])
        label = d.get("label", "")
        if op == NodeOp.LEAF:
            cond = condition_from_dict(d["condition"]) if d.get("condition") else None
            return cls(op=op, condition=cond, label=label)
        children = [cls.from_dict(c) for c in d.get("children", [])]
        if op == NodeOp.SEQUENCE:
            return cls(op=op, children=children, label=label,
                       step_gap=list(d.get("step_gap", [])),
                       default_gap=int(d.get("default_gap", 0)),
                       recent_window=int(d.get("recent_window", 5)))
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
