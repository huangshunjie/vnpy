"""
capital_allocation_ai/engine/routing_engine.py  (Phase 3)

StrategyCapitalRouter — 策略资金路由引擎（完整实现）。

职责：
  - 维护 Alpha → Strategy 映射
  - 将 CapitalAllocation 路由到对应策略
  - 合并同一策略下多个 Alpha 的资金
  - 检测路由冲突
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..model.allocation_model import CapitalAllocation


class StrategyCapitalRouter:
    """策略资金路由引擎（Phase 3）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log    = log_fn or (lambda msg: None)
        self._routes: dict[str, str]  = {}   # {alpha_id: strategy_id}
        self._routed_history: list    = []

    # ------------------------------------------------------------------ #
    #  路由注册
    # ------------------------------------------------------------------ #

    def register_route(self, alpha_id: str, strategy_id: str) -> None:
        """注册 Alpha → Strategy 路由映射。"""
        self._routes[alpha_id] = strategy_id
        self._log(
            f"[RouterEngine] register_route  {alpha_id} -> {strategy_id}"
        )

    def register_routes(self, mapping: dict[str, str]) -> None:
        """批量注册路由映射。"""
        for alpha_id, strategy_id in mapping.items():
            self.register_route(alpha_id, strategy_id)

    def unregister_route(self, alpha_id: str) -> None:
        self._routes.pop(alpha_id, None)
        self._log(f"[RouterEngine] unregister_route  {alpha_id}")

    def clear_routes(self) -> None:
        self._routes.clear()
        self._log("[RouterEngine] clear_routes")

    # ------------------------------------------------------------------ #
    #  路由计算
    # ------------------------------------------------------------------ #

    def route(
        self,
        allocations: dict[str, CapitalAllocation],
    ) -> dict[str, float]:
        """
        将 Alpha 资金分配路由到对应策略（合并同策略多 Alpha）。

        未注册路由的 Alpha 归入 "_unrouted" 桶。

        Returns
        -------
        dict  {strategy_id: total_allocated_capital}
        """
        result: dict[str, float] = {}

        for alpha_id, alloc in allocations.items():
            strategy_id = self._routes.get(alpha_id, "_unrouted")
            result[strategy_id] = result.get(strategy_id, 0.0) + alloc.allocated

        for k in result:
            result[k] = round(result[k], 2)

        self._routed_history.append({
            "ts":          str(datetime.now())[:19],
            "n_alphas":    len(allocations),
            "n_strategies": len(result),
            "routing":     dict(result),
        })

        self._log(
            f"[RouterEngine] route  n_alphas={len(allocations)}"
            f"  n_strategies={len(result)}"
            f"  unrouted={'_unrouted' in result}"
        )
        return result

    def route_ratios(
        self,
        allocations: dict[str, CapitalAllocation],
    ) -> dict[str, float]:
        """
        路由到策略级资金比例（而非金额）。

        Returns
        -------
        dict  {strategy_id: ratio}
        """
        raw = self.route(allocations)
        total = sum(raw.values())
        if total < 1e-12:
            return {}
        return {k: round(v / total, 8) for k, v in raw.items()}

    # ------------------------------------------------------------------ #
    #  冲突检测
    # ------------------------------------------------------------------ #

    def check_conflicts(self) -> list[str]:
        """
        检测路由冲突（同一 Alpha 映射到多个策略的情况不存在，
        但检查孤立 Alpha：策略 ID 为空字符串）。

        Returns
        -------
        list[str]  有冲突的 alpha_id 列表
        """
        conflicts = [
            alpha_id for alpha_id, sid in self._routes.items()
            if not sid or not sid.strip()
        ]
        if conflicts:
            self._log(f"[RouterEngine] conflicts detected: {conflicts}")
        return conflicts

    def get_unrouted_alphas(
        self,
        alpha_ids: list[str],
    ) -> list[str]:
        """返回未注册路由的 Alpha ID 列表。"""
        return [aid for aid in alpha_ids if aid not in self._routes]

    # ------------------------------------------------------------------ #
    #  查询
    # ------------------------------------------------------------------ #

    def get_routes(self) -> dict[str, str]:
        return dict(self._routes)

    def get_strategy_alphas(self) -> dict[str, list[str]]:
        """返回 strategy → [alpha_id] 的反向映射。"""
        inv: dict[str, list[str]] = {}
        for alpha_id, sid in self._routes.items():
            inv.setdefault(sid, []).append(alpha_id)
        return inv

    def get_routed_history(self, limit: int = 20) -> list:
        return self._routed_history[-limit:]

    def summary(self) -> dict:
        return {
            "routes":        len(self._routes),
            "strategies":    len(set(self._routes.values())),
            "routed_count":  len(self._routed_history),
            "phase":         3,
        }
