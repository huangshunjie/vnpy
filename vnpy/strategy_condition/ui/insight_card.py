"""
strategy_condition/ui/insight_card.py
条件 Insight 卡片组件 — 显示条件的详细量化解读
"""
from __future__ import annotations
from typing import Optional

from vnpy.trader.ui import QtWidgets, QtCore, QtGui

from ..constant import ConditionIndicator
from ..insight.manager import ConditionInsightManager
from ..insight.schema import ConditionInsight, ParamInsight

# ── 颜色 ──
_BG = "#1e1e2e"
_PAN2 = "#11111b"
_BORD = "#45475a"
_FG = "#cdd6f4"
_MUT = "#6c7086"
_BLU = "#89b4fa"
_GRN = "#a6e3a1"
_YLW = "#f9e2af"
_RED = "#f38ba8"
_MAV = "#cba6f7"
_PNK = "#f5c2e7"
_TEAL = "#94e2d5"


def _section_label(text: str, color: str = _YLW, size: int = 17) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text)
    lbl.setStyleSheet(
        f"color:{color};font-size:{size}px;font-weight:bold;"
        f"background:transparent;border:none;padding:2px 0;")
    return lbl


def _body_label(text: str, color: str = _FG, size: int = 17) -> QtWidgets.QLabel:
    lbl = QtWidgets.QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        f"color:{color};font-size:{size}px;background:transparent;"
        f"border:none;padding:2px 4px;line-height:1.5;")
    return lbl


def _tag_widget(tags: list, color: str = _BLU) -> QtWidgets.QWidget:
    """创建水平排列的标签组"""
    w = QtWidgets.QWidget()
    w.setStyleSheet("background:transparent;border:none;")
    h = QtWidgets.QHBoxLayout(w)
    h.setContentsMargins(4, 0, 4, 0)
    h.setSpacing(4)
    for tag in tags:
        lbl = QtWidgets.QLabel(tag)
        lbl.setStyleSheet(
            f"color:{color};font-size:15px;background:#313244;"
            f"border:1px solid {_BORD};border-radius:3px;"
            f"padding:2px 8px;")
        h.addWidget(lbl)
    h.addStretch()
    return w


def _separator() -> QtWidgets.QFrame:
    sep = QtWidgets.QFrame()
    sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    sep.setStyleSheet(f"border:none;border-top:1px solid {_BORD};margin:4px 0;")
    return sep


class InsightCardWidget(QtWidgets.QWidget):
    """
    条件 Insight 卡片：展示条件的详细量化解读信息。
    包括：描述、公式、触发条件、参数解读、适用场景、搭配建议、风险提示、经验总结。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = ConditionInsightManager.instance()
        self._current_indicator: Optional[ConditionIndicator] = None
        self._init_ui()

    def _init_ui(self):
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)

        # 占位 — 未选择时显示
        self._placeholder = _body_label(
            "选择条件后显示详细解读", _MUT, 12)
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._placeholder)
        self._layout.addStretch()

    def has_content(self) -> bool:
        """判断是否成功加载了 Insight 内容"""
        if self._current_indicator is None:
            return False
        insight = self._manager.get(self._current_indicator)
        return insight is not None

    def show_insight(self, indicator: ConditionIndicator) -> None:
        """显示指定条件的 Insight 卡片"""
        if indicator == self._current_indicator:
            return
        self._current_indicator = indicator

        # 清除旧内容
        self._clear_layout()

        insight = self._manager.get(indicator)
        if not insight:
            self._show_fallback(indicator)
            return

        self._build_card(insight)

    def _clear_layout(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_fallback(self, indicator: ConditionIndicator):
        """没有 Insight 数据时的回退显示"""
        self._layout.addWidget(
            _body_label(f"暂无 {indicator.value} 的详细解读", _MUT))
        self._layout.addStretch()

    def _build_card(self, insight: ConditionInsight):
        """构建完整的 Insight 卡片"""
        layout = self._layout

        # ── 标题 + 角色标签 ──
        layout.addWidget(_section_label(f"📊 {insight.name}", _BLU, 19))
        if insight.roles:
            role_names = [r.value for r in insight.roles]
            layout.addWidget(_tag_widget(role_names, _MAV))

        # ── 描述 ──
        layout.addWidget(_body_label(insight.description, _FG, 17))
        layout.addWidget(_separator())

        # ── 公式 & 触发条件 ──
        if insight.formula:
            layout.addWidget(_section_label("📐 计算公式", _TEAL, 17))
            formula_lbl = _body_label(insight.formula, _GRN, 17)
            formula_lbl.setStyleSheet(
                formula_lbl.styleSheet() +
                "font-family:'Consolas','Courier New',monospace;")
            layout.addWidget(formula_lbl)

        if insight.trigger:
            layout.addWidget(_section_label("⚡ 触发条件", _TEAL, 17))
            layout.addWidget(_body_label(insight.trigger, _YLW, 17))

        layout.addWidget(_separator())

        # ── 参数解读 ──
        if insight.parameters:
            layout.addWidget(_section_label("⚙️ 参数说明", _YLW, 17))
            for p in insight.parameters:
                param_text = self._format_param(p)
                layout.addWidget(_body_label(param_text, _FG, 17))
            layout.addWidget(_separator())

        # ── 适用场景 ──
        if insight.scenarios_good or insight.scenarios_bad:
            layout.addWidget(_section_label("🎯 适用场景", _GRN, 17))
            if insight.scenarios_good:
                good_text = "✅ " + " / ".join(insight.scenarios_good)
                layout.addWidget(_body_label(good_text, _GRN, 17))
            if insight.scenarios_bad:
                bad_text = "⚠️ " + " / ".join(insight.scenarios_bad)
                layout.addWidget(_body_label(bad_text, _YLW, 17))
            layout.addWidget(_separator())

        # ── 搭配建议 ──
        if insight.combinations:
            layout.addWidget(_section_label("🔗 推荐搭配", _BLU, 17))
            layout.addWidget(_tag_widget(insight.combinations, _BLU))
            if insight.combo_model:
                layout.addWidget(
                    _body_label(f"→ {insight.combo_model}", _MUT, 17))
            layout.addWidget(_separator())

        # ── 风险提示 ──
        if insight.risks:
            layout.addWidget(_section_label("⚠️ 风险提示", _RED, 17))
            for risk in insight.risks:
                layout.addWidget(_body_label(f"• {risk}", _RED, 17))
            layout.addWidget(_separator())

        # ── 经验总结 ──
        if insight.experience:
            layout.addWidget(_section_label("💡 经验总结", _PNK, 17))
            layout.addWidget(_body_label(insight.experience, _PNK, 17))

        layout.addStretch()

    @staticmethod
    def _format_param(p: ParamInsight) -> str:
        """格式化单个参数的说明文本"""
        lines = [f"• {p.display_name}（{p.key}）"]
        if p.description:
            lines[0] += f"：{p.description}"
        parts = []
        if p.default is not None:
            parts.append(f"默认={p.default}")
        if p.min_val is not None and p.max_val is not None:
            parts.append(f"范围 {p.min_val}~{p.max_val}")
        if parts:
            lines.append(f"  {' | '.join(parts)}")
        # 场景推荐
        scenarios = []
        if p.typical_short:
            scenarios.append(f"短线:{p.typical_short}")
        if p.typical_mid:
            scenarios.append(f"中线:{p.typical_mid}")
        if p.typical_safe:
            scenarios.append(f"稳健:{p.typical_safe}")
        if scenarios:
            lines.append(f"  推荐 → {' / '.join(scenarios)}")
        return "\n".join(lines)