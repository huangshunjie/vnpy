"""
factor_research/engine/score_engine.py

ScoreEngine — 因子综合评分层（预留接口）。

职责：
  - 汇总 IC、分层收益、Decay 等指标
  - 按加权规则计算因子综合得分
  - 输出因子排名与评级
  - 严禁直接操作 UI，严禁直接访问数据库

第一阶段：仅定义接口骨架，不实现任何算法。
"""

from __future__ import annotations

from typing import Any


class ScoreEngine:
    """
    因子综合评分引擎（预留接口）。

    后续阶段将支持：
      - 多维度指标加权评分
      - 自定义评分权重配置
      - 因子等级划分（S/A/B/C/D）
    """

    def __init__(self) -> None:
        self._weights: dict[str, float] = {}

    def set_weights(self, weights: dict[str, float]) -> None:
        """设置各维度评分权重（预留接口）。"""
        raise NotImplementedError("ScoreEngine.set_weights() 待后续阶段实现")

    def compute_score(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """计算综合评分（预留接口）。"""
        raise NotImplementedError("ScoreEngine.compute_score() 待后续阶段实现")
