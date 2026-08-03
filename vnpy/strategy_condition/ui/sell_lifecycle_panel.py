"""
strategy_condition/ui/sell_lifecycle_panel.py

Sell Signal Lifecycle 诊断面板。
在 K 线光标联动时展示当前 bar 的卖出信号四层诊断：
  Condition → Signal → Decision → Execution

设计：
  - 紧凑卡片式布局，嵌入到 Monitor Tab 右侧或底部
  - 每个卖出条件一行，四个阶段用 icon/color 表示流转状态
  - 点击某行可展开详情
"""
from __future__ import annotations

from typing import List, Optional

from vnpy.trader.ui import QtWidgets, QtCore, QtGui

from ..monitor.condition_snapshot import ConditionSnapshot
from ..monitor.sell_signal_lifecycle import SellSignalLifecycle
from ..constant import DecisionResult, SellLifecycleStage


# ── 颜色常量（与 condition_monitor_widget 保持一致） ──
_BG = "#1e1e2e"
_FG = "#cdd6f4"
_MUT = "#6c7086"
_BORD = "#45475a"
_GRN = "#a6e3a1"
_RED = "#f38ba8"
_YEL = "#f9e2af"
_BLU = "#89b4fa"
_CARD_BG = "#181825"
_HOVER_BG = "#313244"

# 阶段颜色映射
_STAGE_COLORS = {
    SellLifecycleStage.CONDITION: _MUT,
    SellLifecycleStage.SIGNAL: _YEL,
    SellLifecycleStage.DECISION: _BLU,
    SellLifecycleStage.EXECUTION: _RED,
}

# 阶段图标
_STAGE_ICONS = {
    SellLifecycleStage.CONDITION: "📊",
    SellLifecycleStage.SIGNAL: "⚡",
    SellLifecycleStage.DECISION: "🔍",
    SellLifecycleStage.EXECUTION: "✅",
}


class SellLifecyclePanel(QtWidgets.QWidget):
    """
    卖出信号生命周期诊断面板。
    展示当前选中 bar 的所有卖出条件的四层流转状态。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lifecycles: List[SellSignalLifecycle] = []
        self._init_ui()

    def _init_ui(self):
        self.setMinimumWidth(320)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {_BG};
                color: {_FG};
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 12px;
            }}
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # 标题
        self._title_label = QtWidgets.QLabel("📋 卖出信号诊断")
        self._title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {_FG};
            padding: 4px 0;
        """)
        layout.addWidget(self._title_label)

        # 摘要行
        self._summary_label = QtWidgets.QLabel("")
        self._summary_label.setStyleSheet(f"color: {_MUT}; font-size: 11px; padding: 2px 0;")
        layout.addWidget(self._summary_label)

        # 分隔线
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setStyleSheet(f"color: {_BORD};")
        layout.addWidget(sep)

        # 滚动区域（条件列表）
        self._scroll = QtWidgets.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {_BG};
            }}
        """)

        self._list_widget = QtWidgets.QWidget()
        self._list_layout = QtWidgets.QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._list_widget)
        layout.addWidget(self._scroll, stretch=1)

    # ── 公开接口 ──────────────────────────────────────────────

    def update_from_snapshot(self, snapshot: Optional[ConditionSnapshot]) -> None:
        """从 ConditionSnapshot 更新面板内容"""
        if snapshot is None or not snapshot.sell_lifecycles:
            self._clear()
            self._summary_label.setText("无卖出条件数据")
            return

        self._lifecycles = snapshot.sell_lifecycles
        self._refresh_display()

    def update_lifecycles(self, lifecycles: List[SellSignalLifecycle]) -> None:
        """直接传入 lifecycle 列表更新"""
        self._lifecycles = lifecycles
        self._refresh_display()

    def clear(self) -> None:
        self._clear()

    # ── 内部方法 ──────────────────────────────────────────────

    def _clear(self):
        """清空列表"""
        while self._list_layout.count() > 1:  # 保留 stretch
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._summary_label.setText("")
        self._lifecycles = []

    def _refresh_display(self):
        """刷新整个面板"""
        # 保存 lifecycles（_clear 会清空）
        lifecycles = self._lifecycles
        self._clear()
        self._lifecycles = lifecycles

        if not self._lifecycles:
            self._summary_label.setText("无卖出条件")
            return

        # 摘要
        triggered_count = sum(1 for lc in self._lifecycles if lc.condition.triggered)
        signal_count = sum(1 for lc in self._lifecycles if lc.signal.signal_created)
        approved_count = sum(
            1 for lc in self._lifecycles
            if lc.decision.result == DecisionResult.APPROVED
        )
        rejected_count = sum(
            1 for lc in self._lifecycles
            if lc.decision.result == DecisionResult.REJECTED
        )

        pos_text = "持仓中" if self._lifecycles[0].has_position else "未持仓"
        summary_parts = [
            f"{pos_text}",
            f"条件触发: {triggered_count}/{len(self._lifecycles)}",
        ]
        if signal_count > 0:
            summary_parts.append(f"信号: {signal_count}")
        if approved_count > 0:
            summary_parts.append(f"批准: {approved_count}")
        if rejected_count > 0:
            summary_parts.append(f"拒绝: {rejected_count}")

        self._summary_label.setText("  |  ".join(summary_parts))

        # 创建每个条件的卡片
        for lc in self._lifecycles:
            card = self._create_lifecycle_card(lc)
            # 在 stretch 之前插入
            self._list_layout.insertWidget(
                self._list_layout.count() - 1, card)

    def _create_lifecycle_card(self, lc: SellSignalLifecycle) -> QtWidgets.QWidget:
        """为单个 lifecycle 创建卡片"""
        card = QtWidgets.QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {_CARD_BG};
                border: 1px solid {_BORD};
                border-radius: 4px;
                padding: 6px;
            }}
            QFrame:hover {{
                background-color: {_HOVER_BG};
            }}
        """)

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(8, 6, 8, 6)
        card_layout.setSpacing(4)

        # 第一行：条件名 + 阶段管道
        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(6)

        # 条件名（带触发状态颜色）
        name_color = _GRN if lc.condition.triggered else _MUT
        name_label = QtWidgets.QLabel(lc.condition.condition_name)
        name_label.setStyleSheet(f"color: {name_color}; font-weight: bold; font-size: 12px;")
        top_row.addWidget(name_label)

        top_row.addStretch()

        # 四阶段管道指示器
        pipeline_text = self._build_pipeline_text(lc)
        pipeline_label = QtWidgets.QLabel(pipeline_text)
        pipeline_label.setStyleSheet(f"font-size: 11px;")
        top_row.addWidget(pipeline_label)

        card_layout.addLayout(top_row)

        # 第二行：状态摘要
        status_label = QtWidgets.QLabel(lc.status_summary)
        status_color = self._get_status_color(lc)
        status_label.setStyleSheet(f"color: {status_color}; font-size: 11px;")
        card_layout.addWidget(status_label)

        # 第三行（仅在有信号时）：Decision 检查详情
        if lc.signal.signal_created and lc.decision.checks:
            checks_text = self._build_checks_text(lc)
            checks_label = QtWidgets.QLabel(checks_text)
            checks_label.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            checks_label.setWordWrap(True)
            card_layout.addWidget(checks_label)

        # Tooltip：完整 JSON
        card.setToolTip(self._build_tooltip(lc))

        return card

    def _build_pipeline_text(self, lc: SellSignalLifecycle) -> str:
        """构建四阶段管道文本，如 ✅→⚡→🔍→⬜"""
        stage = lc.stage
        stages = [
            SellLifecycleStage.CONDITION,
            SellLifecycleStage.SIGNAL,
            SellLifecycleStage.DECISION,
            SellLifecycleStage.EXECUTION,
        ]
        icons = []
        reached = False
        for s in stages:
            if s == stage:
                reached = True
            if s.value <= stage.value:
                # 已到达的阶段
                if s == SellLifecycleStage.DECISION and lc.is_rejected:
                    icons.append("🚫")
                else:
                    icons.append(_STAGE_ICONS[s])
            else:
                icons.append("⬜")
        return " → ".join(icons)

    def _get_status_color(self, lc: SellSignalLifecycle) -> str:
        """根据状态选择颜色"""
        if lc.is_executed:
            return _RED
        if lc.is_rejected:
            return _YEL
        if lc.decision.result == DecisionResult.APPROVED:
            return _GRN
        if lc.signal.signal_created:
            return _BLU
        if lc.condition.triggered:
            return _GRN
        return _MUT

    def _build_checks_text(self, lc: SellSignalLifecycle) -> str:
        """构建 Decision checks 文本"""
        parts = []
        for check in lc.decision.checks:
            icon = "✅" if check.passed else "❌"
            parts.append(f"{icon} {check.check_name}: {check.description}")
        return "  |  ".join(parts)

    def _build_tooltip(self, lc: SellSignalLifecycle) -> str:
        """构建详细 tooltip"""
        lines = [
            f"─── {lc.condition.condition_name} ───",
            f"阶段: {lc.stage.value}",
            f"",
            f"【条件层】",
            f"  触发: {'是' if lc.condition.triggered else '否'}",
            f"  评分: {lc.condition.score:.2f}",
        ]

        ctx = lc.condition.context
        if ctx.get("entry_price"):
            lines.append(f"  入场价: {ctx['entry_price']}")
        if ctx.get("peak_price"):
            lines.append(f"  最高价: {ctx['peak_price']}")
        if ctx.get("current_price"):
            lines.append(f"  当前价: {ctx['current_price']}")

        if lc.signal.signal_created:
            lines.extend([
                f"",
                f"【信号层】",
                f"  信号源: {lc.signal.signal_source}",
                f"  时间: {lc.signal.signal_time}",
            ])

        if lc.decision.result != DecisionResult.PENDING:
            lines.extend([
                f"",
                f"【决策层】",
                f"  结果: {lc.decision.result.value}",
            ])
            if lc.decision.reject_description:
                lines.append(f"  原因: {lc.decision.reject_description}")
            for check in lc.decision.checks:
                icon = "✓" if check.passed else "✗"
                lines.append(f"  [{icon}] {check.check_name}: {check.description}")

        if lc.execution.executed:
            lines.extend([
                f"",
                f"【执行层】",
                f"  成交价: {lc.execution.execution_price:.2f}",
                f"  数量: {lc.execution.volume}",
                f"  原因: {lc.execution.exit_reason}",
            ])

        return "\n".join(lines)


class SellLifecycleSummaryBar(QtWidgets.QWidget):
    """
    卖出信号生命周期摘要条。
    精简版，仅用一行展示当前 bar 的卖出诊断状态。
    适合嵌入到 K 线图底部信息栏。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {_CARD_BG};
                color: {_FG};
                font-size: 11px;
            }}
        """)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(12)

        self._icon_label = QtWidgets.QLabel("")
        self._text_label = QtWidgets.QLabel("")
        self._text_label.setStyleSheet(f"color: {_MUT};")

        layout.addWidget(self._icon_label)
        layout.addWidget(self._text_label, stretch=1)

    def update_from_snapshot(self, snapshot: Optional[ConditionSnapshot]) -> None:
        """从 snapshot 更新摘要条"""
        if snapshot is None or not snapshot.sell_lifecycles:
            self._icon_label.setText("")
            self._text_label.setText("")
            return

        lifecycles = snapshot.sell_lifecycles
        triggered = sum(1 for lc in lifecycles if lc.condition.triggered)

        if triggered == 0:
            self._icon_label.setText("⬜")
            self._text_label.setText("卖出条件均未触发")
            self._text_label.setStyleSheet(f"color: {_MUT};")
            return

        # 有触发
        if snapshot.sell_signal_created:
            if snapshot.sell_decision_result == "REJECTED":
                self._icon_label.setText("🚫")
                reason = snapshot.sell_reject_reason or "被拒绝"
                self._text_label.setText(f"卖出信号被拦截: {reason}")
                self._text_label.setStyleSheet(f"color: {_YEL};")
            elif snapshot.sell_decision_result == "APPROVED":
                self._icon_label.setText("⚡")
                self._text_label.setText(f"卖出信号已批准 ({triggered}个条件触发)")
                self._text_label.setStyleSheet(f"color: {_RED};")
            else:
                self._icon_label.setText("⚡")
                self._text_label.setText(f"卖出信号待决策 ({triggered}个条件触发)")
                self._text_label.setStyleSheet(f"color: {_BLU};")
        else:
            self._icon_label.setText("📊")
            self._text_label.setText(f"{triggered}个卖出条件触发，无持仓不产生信号")
            self._text_label.setStyleSheet(f"color: {_MUT};")