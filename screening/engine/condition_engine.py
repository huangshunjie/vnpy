"""
screening/engine/condition_engine.py

Condition Builder Engine — 条件树执行引擎（Phase 3）。
"""

from __future__ import annotations
from typing import Any, Callable, List, Optional

from ..constant import ConditionOperator, CompareOperator
from ..model.condition import ConditionTree, ConditionNode, ConditionLeaf, ConditionGroup
from ..utils.data_fetcher import DataFetcher
from ..utils.expression import compare, parse_value, tree_to_expression


class ConditionEngine:
    """
    条件树执行引擎（Phase 3 完整实现）。

    对股票池中每只股票执行 ConditionTree 求值，
    返回通过条件的股票列表。
    """

    def __init__(
        self,
        log_fn: Optional[Callable[[str], None]] = None,
        main_engine: Any = None,
    ) -> None:
        self._log = log_fn or print
        self._tree: Optional[ConditionTree] = None
        self._fetcher = DataFetcher(main_engine=main_engine)

    # ── 配置 ─────────────────────────────────────────────────────────

    def set_tree(self, tree: ConditionTree) -> None:
        self._tree = tree
        self._fetcher.clear_cache()

    def get_tree(self) -> Optional[ConditionTree]:
        return self._tree

    def clear_tree(self) -> None:
        self._tree = ConditionTree.empty()
        self._fetcher.clear_cache()

    def set_main_engine(self, main_engine: Any) -> None:
        self._fetcher.set_main_engine(main_engine)

    # ── 主接口 ────────────────────────────────────────────────────────

    def filter_symbols(self, symbols: List[str]) -> List[str]:
        """
        对股票池执行条件树过滤，返回通过的股票列表。
        若条件树为空或未设置，返回全部股票。
        """
        if self._tree is None or self._tree.is_empty():
            self._log("[ConditionEngine] 条件树为空，跳过过滤")
            return list(symbols)

        self._fetcher.clear_cache()
        passed = []
        failed = 0
        for symbol in symbols:
            try:
                result = self._evaluate_node(self._tree.root, symbol)
            except Exception as e:
                self._log(f"[ConditionEngine] {symbol} 求值异常：{e}，默认通过")
                result = True
            if result:
                passed.append(symbol)
            else:
                failed += 1

        self._log(
            f"[ConditionEngine] 条件过滤完成："
            f"通过 {len(passed)}，过滤 {failed}"
        )
        return passed

    def evaluate_symbol(self, symbol: str) -> bool:
        """对单只股票执行条件树求值。"""
        if self._tree is None or self._tree.is_empty():
            return True
        return self._evaluate_node(self._tree.root, symbol)

    # ── 条件树递归求值 ────────────────────────────────────────────────

    def _evaluate_node(self, node: Optional[ConditionNode], symbol: str) -> bool:
        if node is None:
            return True

        if isinstance(node, ConditionLeaf):
            return self._evaluate_leaf(node, symbol)

        if isinstance(node, ConditionGroup):
            return self._evaluate_group(node, symbol)

        return True

    def _evaluate_leaf(self, leaf: ConditionLeaf, symbol: str) -> bool:
        """求值叶节点：取字段值 → 比较。"""
        if not leaf.enabled:
            return True

        lhs = self._fetcher.get_field(symbol, leaf.field_name)

        if leaf.value_is_field:
            rhs = self._fetcher.get_field(symbol, str(leaf.value))
        else:
            rhs = parse_value(leaf.value)

        return compare(lhs, leaf.operator, rhs)

    def _evaluate_group(self, group: ConditionGroup, symbol: str) -> bool:
        """求值逻辑组节点：AND / OR / NOT。"""
        if not group.enabled:
            return True

        active = [c for c in group.children if c is not None]
        if not active:
            return True

        if group.operator == ConditionOperator.AND:
            return all(self._evaluate_node(c, symbol) for c in active)

        if group.operator == ConditionOperator.OR:
            return any(self._evaluate_node(c, symbol) for c in active)

        if group.operator == ConditionOperator.NOT:
            return not self._evaluate_node(active[0], symbol)

        return True

    # ── 验证 ──────────────────────────────────────────────────────────

    def validate_tree(self) -> tuple:
        """验证条件树结构。返回 (is_valid, error_message)。"""
        if self._tree is None:
            return False, "条件树未设置"
        if self._tree.is_empty():
            return False, "条件树为空"
        ok, msg = self._validate_node(self._tree.root)
        return ok, msg

    def _validate_node(self, node: Optional[ConditionNode]) -> tuple:
        if node is None:
            return False, "存在空节点"
        if isinstance(node, ConditionLeaf):
            if not node.field_name:
                return False, "叶节点字段名为空"
            if node.value is None and not node.value_is_field:
                return False, f"叶节点 {node.field_name} 的值为空"
            return True, ""
        if isinstance(node, ConditionGroup):
            if node.operator == ConditionOperator.NOT and len(node.children) != 1:
                return False, "NOT 节点必须恰好有一个子节点"
            for c in node.children:
                ok, msg = self._validate_node(c)
                if not ok:
                    return False, msg
            return True, ""
        return True, ""

    # ── 摘要 ──────────────────────────────────────────────────────────

    def get_expression(self) -> str:
        return tree_to_expression(self._tree)

    def summary(self) -> dict:
        return {
            "has_tree": self._tree is not None,
            "tree_name": self._tree.name if self._tree else "",
            "is_empty": self._tree.is_empty() if self._tree else True,
            "expression": self.get_expression(),
        }
