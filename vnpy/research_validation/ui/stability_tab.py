"""
research_validation/ui/stability_tab.py

StabilityTab — 因子稳定性分析结果展示（Phase 4 实现）。

顶部：稳定性 KPI 卡片（评级 / 评分 / 半衰期 / 自相关）
中部左：Rolling IC ASCII 折线图
中部右：IC 衰减曲线图
底部：自相关序列 + 稳定性详细报告
"""

from __future__ import annotations

import math

from vnpy.trader.ui import QtCore, QtWidgets

_DARK_BG  = "#1e1e2e"
_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_ORG      = "#fab387"

_LEVEL_COLOR = {
    "STRONG":   _GRN,
    "MODERATE": _BLU,
    "WEAK":     _YLW,
    "UNSTABLE": _RED,
}


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    it.setForeground(QtGui.QColor(color))
    return it


class StabilityTab(QtWidgets.QWidget):
    """因子稳定性分析结果展示 Tab（Phase 4）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._summary = None
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_kpi_bar())

        mid = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        mid.addWidget(self._build_rolling_ic_panel())
        mid.addWidget(self._build_decay_panel())
        mid.setSizes([540, 360])
        root.addWidget(mid, stretch=1)

        root.addWidget(self._build_detail_bar())

    # ------------------------------------------------------------------ #
    #  子区域构建
    # ------------------------------------------------------------------ #

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(72)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(14, 6, 14, 6)
        h.setSpacing(24)

        kpis = [
            ("稳定性评级",       "—",   _MUT),
            ("稳定性评分",       "—",   _BLU),
            ("全期 IC 均值",     "—",   _FG),
            ("全期 IC IR",       "—",   _FG),
            ("IC 胜率",          "—",   _FG),
            ("IC 半衰期（期）",  "—",   _YLW),
            ("Lag-1 自相关",     "—",   _MUT),
            ("Rolling IC 均值",  "—",   _BLU),
        ]
        self._kpi: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in kpis:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(1)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(
                f"color: {color}; font-size: 12px; font-weight: bold;"
            )
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._kpi[name] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_rolling_ic_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        lbl = QtWidgets.QLabel("Rolling IC 时间序列（▓ = 正向  ░ = 负向）")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._txt_rolling = QtWidgets.QTextEdit()
        self._txt_rolling.setReadOnly(True)
        self._txt_rolling.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt_rolling, stretch=1)
        return w

    def _build_decay_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        lbl = QtWidgets.QLabel("IC 衰减曲线（Lag 1 → N）& 自相关序列")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._txt_decay = QtWidgets.QTextEdit()
        self._txt_decay.setReadOnly(True)
        self._txt_decay.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt_decay, stretch=1)
        return w

    def _build_detail_bar(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(110)
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 4, 8, 4)
        v.setSpacing(2)

        lbl = QtWidgets.QLabel("稳定性详细报告")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._txt_detail = QtWidgets.QTextEdit()
        self._txt_detail.setReadOnly(True)
        self._txt_detail.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt_detail)
        return w

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_summary(self, summary) -> None:
        """接收 StabilitySummary 并刷新 UI。"""
        self._summary = summary
        self._update_kpi(summary)
        self._update_rolling_ic(summary)
        self._update_decay(summary)
        self._update_detail(summary)

    def clear(self) -> None:
        self._summary = None
        for lbl in self._kpi.values():
            lbl.setText("—")
        self._txt_rolling.clear()
        self._txt_decay.clear()
        self._txt_detail.clear()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _update_kpi(self, s) -> None:
        level_color = _LEVEL_COLOR.get(s.stability_level, _MUT)
        score_color = (
            _GRN if s.stability_score >= 60 else
            (_YLW if s.stability_score >= 40 else _RED)
        )
        ic_color = _GRN if s.overall_ic_mean > 0.02 else (
                   _YLW if s.overall_ic_mean > 0 else _RED)
        hl_color = _GRN if s.ic_decay_halflife >= 5 else (
                   _YLW if s.ic_decay_halflife >= 2 else _RED)
        ac_color = _GRN if abs(s.lag1_autocorr) < 0.3 else (
                   _YLW if abs(s.lag1_autocorr) < 0.5 else _RED)

        self._kpi["稳定性评级"].setText(s.stability_level)
        self._kpi["稳定性评级"].setStyleSheet(
            f"color: {level_color}; font-size: 12px; font-weight: bold;"
        )
        self._kpi["稳定性评分"].setText(f"{s.stability_score:.1f}")
        self._kpi["稳定性评分"].setStyleSheet(
            f"color: {score_color}; font-size: 12px; font-weight: bold;"
        )
        self._kpi["全期 IC 均值"].setText(f"{s.overall_ic_mean:+.4f}")
        self._kpi["全期 IC 均值"].setStyleSheet(
            f"color: {ic_color}; font-size: 12px; font-weight: bold;"
        )
        self._kpi["全期 IC IR"].setText(f"{s.overall_ic_ir:.3f}")
        self._kpi["IC 胜率"   ].setText(f"{s.overall_win_rate:.1%}")
        self._kpi["IC 半衰期（期）"].setText(f"{s.ic_decay_halflife:.1f}")
        self._kpi["IC 半衰期（期）"].setStyleSheet(
            f"color: {hl_color}; font-size: 12px; font-weight: bold;"
        )
        self._kpi["Lag-1 自相关"].setText(f"{s.lag1_autocorr:+.3f}")
        self._kpi["Lag-1 自相关"].setStyleSheet(
            f"color: {ac_color}; font-size: 12px; font-weight: bold;"
        )
        self._kpi["Rolling IC 均值"].setText(f"{s.rolling_ic_mean:+.4f}")

    def _update_rolling_ic(self, s) -> None:
        """将 rolling IC 序列渲染为 ASCII 迷你条形图（每行 50 期）。"""
        valid = [(i, v) for i, v in enumerate(s.rolling_ic)
                 if not math.isnan(v)]
        if not valid:
            self._txt_rolling.setText("暂无 Rolling IC 数据。")
            return

        ic_vals  = [v for _, v in valid]
        max_abs  = max(abs(v) for v in ic_vals) or 1.0
        bar_w    = 16

        lines = [
            f"  Rolling IC（窗口={s.rolling_window} 期）  "
            f"均值={s.rolling_ic_mean:+.4f}  std={s.rolling_ic_std:.4f}",
            "  " + "─" * 58,
        ]

        row_w = 50
        i = 0
        while i < len(valid):
            batch = valid[i : i + row_w]
            start_idx = batch[0][0]

            # 迷你条形行
            bars = []
            for _, v in batch:
                frac = v / max_abs
                length = max(1, int(abs(frac) * 4))
                if v >= 0:
                    bars.append("▓" * length)
                else:
                    bars.append("░" * length)

            row_str = " ".join(f"{b:<4}" for b in bars[:20])
            ic_row  = " ".join(
                f"{v:+.3f}" for _, v in batch[:10]
            )
            lines.append(f"  [{start_idx:04d}] {ic_row}")
            i += row_w

        lines.append("  " + "─" * 58)
        pos_rate = sum(1 for v in ic_vals if v > 0) / len(ic_vals)
        lines.append(
            f"  有效期数={len(ic_vals)}  正向比={pos_rate:.1%}  "
            f"稳定性评级={s.stability_level}"
        )
        self._txt_rolling.setText("\n".join(lines))

    def _update_decay(self, s) -> None:
        """IC 衰减曲线 + 自相关序列。"""
        lines = ["  IC 衰减曲线（因子值 → 持有期收益 IC）", "  " + "─" * 50]

        if s.ic_decay:
            max_abs = max(abs(v) for v in s.ic_decay) or 1.0
            for lag, ic_val in enumerate(s.ic_decay, start=1):
                bar_len = int(abs(ic_val) / max_abs * 20)
                sign    = "+" if ic_val >= 0 else "-"
                bar     = sign + "█" * bar_len
                lines.append(
                    f"  lag={lag:2d}  {ic_val:+.4f}  {bar:<22}"
                )
            lines.append(f"  半衰期 ≈ {s.ic_decay_halflife:.1f} 期")
        else:
            lines.append("  暂无衰减数据。")

        lines.append("")
        lines.append("  自相关序列（lag=1~10）")
        lines.append("  " + "─" * 50)

        if s.autocorr_series:
            for lag, ac in enumerate(s.autocorr_series[:10], start=1):
                bar_len = int(abs(ac) * 20)
                sign    = "+" if ac >= 0 else "-"
                bar     = sign + "▒" * bar_len
                warn    = " ⚠" if abs(ac) > 0.5 else ""
                lines.append(
                    f"  lag={lag:2d}  {ac:+.3f}  {bar:<22}{warn}"
                )
        else:
            lines.append("  暂无自相关数据。")

        self._txt_decay.setText("\n".join(lines))

    def _update_detail(self, s) -> None:
        self._txt_detail.setText(s.to_text())
