"""
factor_research/engine/factor_engine.py

FactorEngine — 因子计算层（预留接口）。

职责：
  - 接收原始行情数据，计算用户指定因子的截面值
  - 管理因子模板的注册与调用
  - 严禁直接操作 UI，严禁直接访问数据库

第一阶段：仅定义接口骨架，不实现任何算法。
"""

from __future__ import annotations

from typing import Any


class FactorEngine:
    """
    因子计算引擎（预留接口）。

    后续阶段将支持：
      - 内置因子（动量、反转、波动率等）
      - 自定义因子模板注册
      - 截面因子值计算与标准化
    """

    def __init__(self) -> None:
        self._factors: dict[str, Any] = {}

    def register(self, name: str, factor: Any) -> None:
        """注册因子模板（预留接口）。"""
        raise NotImplementedError("FactorEngine.register() 待后续阶段实现")

    def compute(self, data: Any, params: dict[str, Any] | None = None) -> Any:
        """计算因子截面值（预留接口）。"""
        raise NotImplementedError("FactorEngine.compute() 待后续阶段实现")

    def get_factor_names(self) -> list[str]:
        """返回已注册的因子名称列表（预留接口）。"""
        raise NotImplementedError("FactorEngine.get_factor_names() 待后续阶段实现")
