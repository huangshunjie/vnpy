"""
risk_engine_2/model/limit_model.py

仓位限制数据模型（Phase 2）。

RiskLimit       : 单条风控限制规则（阈值 + 动作）
LimitCheckResult: 单次校验结果（通过 / 预警 / 阻断）
LimitReport     : 多条校验结果汇总
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..constant import LimitType, RiskLevel, RiskAction


@dataclass
class RiskLimit:
    """
    单条风控限制规则。

    一条规则对应一个 LimitType，定义：
      - 警告阈值（warning_threshold）：超过时发预警，不阻断
      - 硬限制（hard_limit）        ：超过时执行 action
      - 动作（action）              ：阻断 / 告警 / 减仓 / 暂停
    """
    limit_id:   str       = ""
    limit_type: LimitType = LimitType.POSITION
    symbol:     str       = ""          # 空串 = 全组合规则；非空 = 单票规则
    industry:   str       = ""          # 行业集中度规则使用

    # 阈值
    warning_threshold: float = 0.0      # 预警线（0 = 不启用）
    hard_limit:        float = 0.0      # 硬限制线（0 = 不启用）

    # 超限动作
    action: RiskAction = RiskAction.BLOCK

    # 是否启用
    enabled: bool = True

    # 描述
    description: str = ""

    @property
    def label(self) -> str:
        """简短描述，用于 UI 展示。"""
        scope = self.symbol or self.industry or "全组合"
        return f"{self.limit_type.value}[{scope}]"

    def is_warning(self, value: float) -> bool:
        """判断 value 是否触及预警线。"""
        if not self.enabled or self.warning_threshold <= 0:
            return False
        return value >= self.warning_threshold

    def is_breach(self, value: float) -> bool:
        """判断 value 是否突破硬限制。"""
        if not self.enabled or self.hard_limit <= 0:
            return False
        return value >= self.hard_limit


@dataclass
class LimitCheckResult:
    """
    单次限制校验结果。

    由 LimitEngine.check() 返回，描述某条规则的当前状态。
    """
    limit_id:   str       = ""
    limit_type: LimitType = LimitType.POSITION
    symbol:     str       = ""
    industry:   str       = ""

    # 当前实际值
    current_value: float  = 0.0

    # 阈值（从规则复制，方便 UI 直接展示）
    warning_threshold: float = 0.0
    hard_limit:        float = 0.0

    # 状态
    risk_level: RiskLevel = RiskLevel.NORMAL
    is_blocked: bool      = False       # True = 该笔订单被阻断

    # 触发的动作
    action:  RiskAction = RiskAction.ALERT
    message: str        = ""

    # 时间戳
    checked_at: datetime = field(default_factory=datetime.now)

    @property
    def passed(self) -> bool:
        """True = 未突破硬限制（可放行）。"""
        return not self.is_blocked

    @property
    def utilization_pct(self) -> float:
        """当前值相对硬限制的使用率（0~1+）。"""
        if self.hard_limit <= 0:
            return 0.0
        return self.current_value / self.hard_limit

    @property
    def status_str(self) -> str:
        color_map = {
            RiskLevel.NORMAL:   "正常",
            RiskLevel.WARNING:  "预警",
            RiskLevel.CRITICAL: "严重",
            RiskLevel.BREACH:   "突破",
        }
        return color_map.get(self.risk_level, "—")


@dataclass
class LimitReport:
    """多条校验结果的汇总报告。"""
    results:      list[LimitCheckResult] = field(default_factory=list)
    checked_at:   datetime               = field(default_factory=datetime.now)

    # 汇总状态（取最严重等级）
    overall_level: RiskLevel = RiskLevel.NORMAL
    any_blocked:   bool      = False
    blocked_count: int       = 0
    warning_count: int       = 0

    @classmethod
    def from_results(cls, results: list[LimitCheckResult]) -> "LimitReport":
        if not results:
            return cls()

        level_order = {
            RiskLevel.NORMAL:   0,
            RiskLevel.WARNING:  1,
            RiskLevel.CRITICAL: 2,
            RiskLevel.BREACH:   3,
        }
        worst = RiskLevel.NORMAL
        blocked = 0
        warnings = 0
        for r in results:
            if level_order.get(r.risk_level, 0) > level_order.get(worst, 0):
                worst = r.risk_level
            if r.is_blocked:
                blocked += 1
            if r.risk_level in (RiskLevel.WARNING, RiskLevel.CRITICAL):
                warnings += 1

        return cls(
            results       = results,
            overall_level = worst,
            any_blocked   = blocked > 0,
            blocked_count = blocked,
            warning_count = warnings,
        )
