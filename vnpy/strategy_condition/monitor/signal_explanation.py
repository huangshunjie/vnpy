"""
strategy_condition/monitor/signal_explanation.py
信号解释引擎：为买入/卖出信号生成人类可读的解释文本

设计目标：
  - 从 ConditionSnapshot 中提取关键信息
  - 生成结构化的信号解释（摘要 + 详情 + 建议）
  - 支持中文输出
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .condition_snapshot import ConditionDetail, ConditionSnapshot


@dataclass
class SignalExplanation:
    """
    信号解释数据结构。

    Attributes:
        symbol: 股票代码
        dt: 信号时间
        signal_type: "BUY" / "SELL"
        summary: 一句话摘要
        key_factors: 关键驱动因素列表
        detail_text: 详细解释文本（多行）
        confidence: 置信度 [0, 1]
        risk_notes: 风险提示列表
    """
    symbol: str
    dt: datetime
    signal_type: str
    summary: str = ""
    key_factors: List[str] = field(default_factory=list)
    detail_text: str = ""
    confidence: float = 0.0
    risk_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "dt": str(self.dt)[:19],
            "signal_type": self.signal_type,
            "summary": self.summary,
            "key_factors": self.key_factors,
            "detail_text": self.detail_text,
            "confidence": round(self.confidence, 4),
            "risk_notes": self.risk_notes,
        }


class SignalExplanationEngine:
    """
    信号解释引擎。

    从 ConditionSnapshot 中提取信号相关信息，
    生成结构化的人类可读解释。
    """

    def explain_signal(self, snapshot: ConditionSnapshot) -> Optional[SignalExplanation]:
        """
        为单个快照生成信号解释。

        如果快照没有产生信号（signal_type is None），返回 None。
        """
        if not snapshot.has_signal:
            return None

        if snapshot.signal_type == "BUY":
            return self._explain_buy(snapshot)
        else:
            return self._explain_sell(snapshot)

    def explain_batch(self, snapshots: List[ConditionSnapshot]) -> List[SignalExplanation]:
        """批量生成信号解释（只处理有信号的快照）"""
        explanations = []
        for snap in snapshots:
            exp = self.explain_signal(snap)
            if exp:
                explanations.append(exp)
        return explanations

    def generate_condition_summary(self, snapshot: ConditionSnapshot) -> str:
        """
        为任意快照生成条件状态摘要（不要求有信号）。
        用于 Monitor UI 的状态显示。
        """
        lines = []
        lines.append(f"📊 {snapshot.symbol} @ {str(snapshot.dt)[:10]}")
        lines.append(f"   价格: {snapshot.price:.2f}")
        lines.append("")

        # 买入条件
        lines.append(f"📈 买入条件 ({snapshot.buy_summary}):")
        for d in snapshot.buy_details:
            icon = "✅" if d.passed else "❌"
            value_str = f" = {d.current_value}" if d.current_value is not None else ""
            lines.append(f"   {icon} {d.condition_name}{value_str}")
            if d.threshold_desc:
                lines.append(f"      阈值: {d.threshold_desc}")

        lines.append("")

        # 卖出条件
        lines.append(f"🚪 卖出条件 ({snapshot.sell_summary}):")
        for d in snapshot.sell_details:
            icon = "✅" if d.passed else "❌"
            value_str = f" = {d.current_value}" if d.current_value is not None else ""
            lines.append(f"   {icon} {d.condition_name}{value_str}")
            if d.threshold_desc:
                lines.append(f"      阈值: {d.threshold_desc}")

        # 最终判断
        lines.append("")
        if snapshot.signal_type == "BUY":
            lines.append("🟢 信号: 买入")
        elif snapshot.signal_type == "SELL":
            lines.append("🔴 信号: 卖出")
        else:
            lines.append("⚪ 信号: 无（继续观望）")

        return "\n".join(lines)

    # ── 内部实现 ──────────────────────────────────────────────────────

    def _explain_buy(self, snapshot: ConditionSnapshot) -> SignalExplanation:
        """生成买入信号解释"""
        passed_details = [d for d in snapshot.buy_details if d.passed]
        failed_details = [d for d in snapshot.buy_details if not d.passed]

        # 关键驱动因素
        key_factors = []
        for d in passed_details:
            factor = self._format_factor(d)
            key_factors.append(factor)

        # 置信度：基于通过率和平均得分
        confidence = self._calc_confidence(snapshot.buy_details, snapshot.buy_score)

        # 一句话摘要
        summary = self._generate_buy_summary(passed_details, snapshot)

        # 详细文本
        detail_lines = [f"买入信号触发 ({snapshot.buy_summary} 条件满足)"]
        detail_lines.append("")
        detail_lines.append("✅ 满足的条件:")
        for d in passed_details:
            val = f" ({d.current_value})" if d.current_value is not None else ""
            detail_lines.append(f"  • {d.condition_name}{val}")
        if failed_details:
            detail_lines.append("")
            detail_lines.append("❌ 未满足的条件:")
            for d in failed_details:
                val = f" ({d.current_value})" if d.current_value is not None else ""
                detail_lines.append(f"  • {d.condition_name}{val}")

        # 风险提示
        risk_notes = self._generate_risk_notes(snapshot, "BUY")

        return SignalExplanation(
            symbol=snapshot.symbol,
            dt=snapshot.dt,
            signal_type="BUY",
            summary=summary,
            key_factors=key_factors,
            detail_text="\n".join(detail_lines),
            confidence=confidence,
            risk_notes=risk_notes,
        )

    def _explain_sell(self, snapshot: ConditionSnapshot) -> SignalExplanation:
        """生成卖出信号解释"""
        passed_details = [d for d in snapshot.sell_details if d.passed]

        # 关键驱动因素
        key_factors = []
        for d in passed_details:
            factor = self._format_factor(d)
            key_factors.append(factor)

        # 置信度
        confidence = self._calc_confidence(snapshot.sell_details, snapshot.sell_score)

        # 摘要
        summary = self._generate_sell_summary(passed_details, snapshot)

        # 详细文本
        detail_lines = [f"卖出信号触发 ({snapshot.sell_summary} 条件满足)"]
        detail_lines.append("")
        detail_lines.append("🚪 触发的卖出条件:")
        for d in passed_details:
            val = f" ({d.current_value})" if d.current_value is not None else ""
            detail_lines.append(f"  • {d.condition_name}{val}")

        # 风险提示
        risk_notes = self._generate_risk_notes(snapshot, "SELL")

        return SignalExplanation(
            symbol=snapshot.symbol,
            dt=snapshot.dt,
            signal_type="SELL",
            summary=summary,
            key_factors=key_factors,
            detail_text="\n".join(detail_lines),
            confidence=confidence,
            risk_notes=risk_notes,
        )

    @staticmethod
    def _format_factor(detail: ConditionDetail) -> str:
        """格式化单个驱动因素的描述"""
        val_str = ""
        if detail.current_value is not None:
            val_str = f" ({detail.current_value})"
        return f"{detail.condition_name}{val_str}"

    @staticmethod
    def _calc_confidence(details: List[ConditionDetail], tree_score: float) -> float:
        """计算置信度"""
        if not details:
            return 0.0
        pass_rate = sum(1 for d in details if d.passed) / len(details)
        avg_score = sum(d.score for d in details) / len(details)
        # 综合：通过率 40% + 平均得分 30% + 树评分 30%
        confidence = pass_rate * 0.4 + avg_score * 0.3 + tree_score * 0.3
        return min(max(confidence, 0.0), 1.0)

    @staticmethod
    def _generate_buy_summary(passed: List[ConditionDetail],
                              snapshot: ConditionSnapshot) -> str:
        """生成买入信号的一句话摘要"""
        if not passed:
            return f"{snapshot.symbol} 买入信号触发"

        # 尝试识别主要类型
        indicators = {d.indicator for d in passed}

        parts = []
        if any(i in indicators for i in ("MA_SLOPE", "MA_ALIGNMENT", "PRICE_ABOVE_MA")):
            parts.append("趋势向好")
        if any(i in indicators for i in ("VOLUME_RATIO", "VOLUME_PRICE_UP")):
            parts.append("量能配合")
        if any(i in indicators for i in ("PULLBACK_PCT", "PULLBACK_TO_MA", "PULLBACK_FROM_HIGH")):
            parts.append("回调到位")
        if any(i in indicators for i in ("RSI_RANGE",)):
            parts.append("指标健康")
        if any(i in indicators for i in ("MACD_GOLDEN",)):
            parts.append("MACD金叉")
        if any(i in indicators for i in ("CONTINUOUS_RISE", "NEW_HIGH_N")):
            parts.append("动能充沛")

        if not parts:
            parts.append(f"{len(passed)}项条件满足")

        return f"{snapshot.symbol} 买入: {'，'.join(parts)}"

    @staticmethod
    def _generate_sell_summary(passed: List[ConditionDetail],
                               snapshot: ConditionSnapshot) -> str:
        """生成卖出信号的一句话摘要"""
        if not passed:
            return f"{snapshot.symbol} 卖出信号触发"

        indicators = {d.indicator for d in passed}

        if "STOP_LOSS" in indicators:
            return f"{snapshot.symbol} 卖出: 触发止损"
        if "TAKE_PROFIT" in indicators:
            return f"{snapshot.symbol} 卖出: 触发止盈"
        if "TRAILING_STOP" in indicators:
            return f"{snapshot.symbol} 卖出: 追踪止损触发"
        if "MAX_HOLD_DAYS" in indicators:
            return f"{snapshot.symbol} 卖出: 达到最大持仓天数"
        if "MA_BREAK_DOWN" in indicators:
            return f"{snapshot.symbol} 卖出: 跌破均线支撑"
        if "MACD_DEATH" in indicators:
            return f"{snapshot.symbol} 卖出: MACD死叉"

        return f"{snapshot.symbol} 卖出: {len(passed)}项卖出条件触发"

    @staticmethod
    def _generate_risk_notes(snapshot: ConditionSnapshot, side: str) -> List[str]:
        """生成风险提示"""
        notes = []

        if side == "BUY":
            # 检查有多少条件未满足
            failed = [d for d in snapshot.buy_details if not d.passed]
            if failed:
                names = "、".join(d.condition_name for d in failed[:3])
                notes.append(f"注意: {names} 条件未满足")

            # 检查量能
            vol_details = [d for d in snapshot.buy_details
                          if d.indicator in ("VOLUME_RATIO", "VOLUME_PRICE_UP")]
            if vol_details and not any(d.passed for d in vol_details):
                notes.append("⚠️ 量能不足，谨慎追涨")

            # 买入评分偏低
            if snapshot.buy_score < 0.5:
                notes.append("⚠️ 综合评分偏低，信号强度一般")

        elif side == "SELL":
            # 卖出通常更紧急
            stop_loss = [d for d in snapshot.sell_details
                        if d.indicator == "STOP_LOSS" and d.passed]
            if stop_loss:
                notes.append("⚠️ 止损条件触发，建议尽快执行")

        return notes