"""
risk_engine_2/model/risk_model.py

归因分析数据模型（Phase 4）。

RiskContribution  : 单个来源（策略 / 因子 / 行业）的风险贡献
AttributionResult : 单轮归因计算结果（含各维度贡献列表）
AttributionReport : 完整归因报告（历史快照 + 汇总）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RiskContribution:
    """
    单个来源的风险贡献。

    一条记录代表某策略 / 因子 / 行业对组合整体风险的贡献比例。
    """
    source_type: str   = ""   # "strategy" | "factor" | "industry" | "market"
    source_name: str   = ""   # 具体名称

    # PnL 贡献
    pnl_contrib:       float = 0.0   # 该来源贡献的绝对 PnL
    pnl_contrib_pct:   float = 0.0   # 占总 PnL 的比例

    # 风险贡献（波动率 / 回撤）
    risk_contrib:      float = 0.0   # 贡献的绝对风险
    risk_contrib_pct:  float = 0.0   # 占总风险的比例

    # 权重
    weight:            float = 0.0   # 该来源在组合中的权重

    # Beta 贡献（仅因子层级使用）
    beta_contrib:      float = 0.0

    @property
    def is_positive(self) -> bool:
        """该来源是否贡献正收益。"""
        return self.pnl_contrib >= 0

    @property
    def label(self) -> str:
        return f"{self.source_type}:{self.source_name}"

    @property
    def summary(self) -> str:
        sign = "+" if self.pnl_contrib >= 0 else ""
        return (
            f"{self.source_name:12s}  PnL={sign}{self.pnl_contrib:>10.2f}"
            f"  ({self.pnl_contrib_pct:>+6.1%})"
            f"  Risk={self.risk_contrib_pct:>5.1%}"
            f"  w={self.weight:>5.1%}"
        )


@dataclass
class AttributionResult:
    """
    单轮归因计算结果。

    由 AttributionEngine.compute() 生成，包含三个维度的贡献列表。
    """
    # 归因时间窗口
    period_start: datetime = field(default_factory=datetime.now)
    period_end:   datetime = field(default_factory=datetime.now)

    # 组合级汇总
    total_pnl:         float = 0.0
    total_risk:        float = 0.0   # 组合整体波动率（年化）
    portfolio_beta:    float = 0.0
    max_drawdown:      float = 0.0
    max_drawdown_pct:  float = 0.0

    # 三维度归因
    strategy_contribs: list[RiskContribution] = field(default_factory=list)
    factor_contribs:   list[RiskContribution] = field(default_factory=list)
    industry_contribs: list[RiskContribution] = field(default_factory=list)

    # 市场残差（不能被策略/因子/行业解释的部分）
    market_contrib:    RiskContribution | None = None

    # 计算时间
    computed_at: datetime = field(default_factory=datetime.now)

    # ------------------------------------------------------------------ #
    #  汇总属性
    # ------------------------------------------------------------------ #

    @property
    def top_strategy(self) -> RiskContribution | None:
        """PnL 贡献最大的策略。"""
        if not self.strategy_contribs:
            return None
        return max(self.strategy_contribs, key=lambda c: c.pnl_contrib)

    @property
    def worst_strategy(self) -> RiskContribution | None:
        """PnL 贡献最小（亏损最多）的策略。"""
        if not self.strategy_contribs:
            return None
        return min(self.strategy_contribs, key=lambda c: c.pnl_contrib)

    @property
    def top_risk_contributor(self) -> RiskContribution | None:
        """风险贡献最大的来源（跨所有维度）。"""
        all_c = self.strategy_contribs + self.factor_contribs + self.industry_contribs
        if not all_c:
            return None
        return max(all_c, key=lambda c: c.risk_contrib_pct)

    @property
    def strategy_explained_pct(self) -> float:
        """策略层可解释的 PnL 比例。"""
        if abs(self.total_pnl) < 1e-9:
            return 0.0
        explained = sum(c.pnl_contrib for c in self.strategy_contribs)
        return explained / self.total_pnl

    def to_text(self) -> str:
        """生成纯文本归因摘要，供日志和 UI 文本区展示。"""
        lines = [
            f"{'─' * 60}",
            f"  归因报告  {self.period_start.strftime('%Y-%m-%d')} ~"
            f" {self.period_end.strftime('%Y-%m-%d')}",
            f"  总 PnL={self.total_pnl:+.2f}  "
            f"Beta={self.portfolio_beta:.3f}  "
            f"MaxDD={self.max_drawdown_pct:.2%}",
            f"{'─' * 60}",
        ]
        if self.strategy_contribs:
            lines.append("  [策略贡献]")
            for c in sorted(self.strategy_contribs,
                             key=lambda x: x.pnl_contrib, reverse=True):
                lines.append(f"    {c.summary}")
        if self.factor_contribs:
            lines.append("  [因子贡献]")
            for c in sorted(self.factor_contribs,
                             key=lambda x: x.risk_contrib_pct, reverse=True):
                lines.append(f"    {c.summary}")
        if self.industry_contribs:
            lines.append("  [行业贡献]")
            for c in sorted(self.industry_contribs,
                             key=lambda x: x.pnl_contrib, reverse=True):
                lines.append(f"    {c.summary}")
        if self.market_contrib:
            lines.append(f"  [市场残差]  {self.market_contrib.summary}")
        lines.append(f"{'─' * 60}")
        return "\n".join(lines)


@dataclass
class AttributionReport:
    """
    完整归因报告（含历史快照序列）。

    由 AttributionEngine 持有，每次触发归因计算后 append 新结果。
    供 UI 展示最新结果，或导出历史序列。
    """
    results:     list[AttributionResult] = field(default_factory=list)
    max_history: int                     = 100

    @property
    def latest(self) -> AttributionResult | None:
        return self.results[-1] if self.results else None

    def append(self, result: AttributionResult) -> None:
        self.results.append(result)
        if len(self.results) > self.max_history:
            self.results = self.results[-self.max_history:]

    def clear(self) -> None:
        self.results.clear()
