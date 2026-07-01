"""
factor_research/ui/score_tab.py

ScoreTab -- Factor Comprehensive Score Tab.

Layout (left radar + right score panel):
┌──────────────────────────────┬────────────────────┐
│  PyQtGraph radar chart        │  Score panel        │
│  6-dim spider web             │  Total score        │
│  score polygon (filled)       │  Grade S/A/B/C/D    │
│                               │  6 dimension rows   │
│                               │  raw value + score  │
└──────────────────────────────┴────────────────────┘

Radar chart implementation:
  PyQtGraph has no polar/radar widget.
  We draw the spider manually in a PlotItem:
  - 5-ring hexagon grid (at 20/40/60/80/100 score levels)
  - 6 radial axis lines with labels at outer ring
  - Score polygon filled with semi-transparent color
  - Reference circle at score=50 (dashed)

Data sources:
  widget._on_plot_ready routes:
    "ic"       -> score_tab.feed_ic(IcStats)
    "quantile" -> score_tab.feed_quantile(QuantileResult)
  ScoreTab accumulates both, recomputes when both arrive.

Score dimensions:
  1. |IC|        raw=|ic_mean|            full score at 0.10
  2. |ICIR|      raw=|icir|               full score at 2.0
  3. IC Win%     raw=max(pr, 1-pr)*100    full score at 75%
  4. Monotonicity raw=|mono_score|        full score at 1.0
  5. |L-S Sharpe| raw from QuantileResult full score at 2.0
  6. MDD quality  raw=max(0, 1-|mdd|/0.5) full score at mdd=0
"""

from __future__ import annotations

import math

import numpy as np
import pyqtgraph as pg

from vnpy.trader.ui import QtCore, QtWidgets

from ..model import (
    FactorScore,
    IcStats,
    LongShortStats,
    PerfStats,
    QuantileResult,
    ScoreDimension,
)

# ── palette ──────────────────────────────────────────────────────────────
_BG          = "#1E1E1E"
_FG          = "#CCCCCC"
_GRID_COLOR  = "#444444"
_AXIS_COLOR  = "#666666"
_POLY_FILL   = "#5B9BD588"   # semi-transparent blue
_POLY_LINE   = "#5B9BD5"
_REF50_COLOR = "#888888"
_GRADE_COLORS = {
    "S": "#FFD700",
    "A": "#4CAF50",
    "B": "#2196F3",
    "C": "#FF9800",
    "D": "#F44336",
}
_N_DIM  = 6          # number of radar dimensions
_N_RING = 5          # concentric rings at 20/40/60/80/100


def _radar_xy(angle_deg: float, r: float) -> tuple[float, float]:
    """Convert (angle, radius) to (x, y), angle 0 = up, clockwise."""
    rad = math.radians(angle_deg - 90)
    return r * math.cos(rad), r * math.sin(rad)


class ScoreTab(QtWidgets.QWidget):
    """Factor comprehensive score Tab."""

    score_ready: QtCore.Signal = QtCore.Signal(object)  # emits FactorScore after each successful computation

    _DIM_NAMES = [
        "|IC| 均值",
        "|ICIR|",
        "IC 胜率",
        "单调性",
        "|L-S Sharpe|",
        "L-S 抗回撤",
    ]
    _DIM_DESCS = [
        "满分基准 |IC|=0.10",
        "满分基准 |ICIR|=2.0",
        "胜率偏离50%的程度",
        "满分基准 |单调性|=1.0",
        "满分基准 |Sharpe|=2.0",
        "满分基准 MDD=0%",
    ]

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._ic_stats: IcStats | None = None
        self._q_result: QuantileResult | None = None
        self._factor_score: FactorScore | None = None
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(8)

        root.addWidget(self._build_chart(), stretch=3)
        root.addWidget(self._build_score_panel(), stretch=2)

    def _build_chart(self) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget(self)
        v = QtWidgets.QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)

        self._placeholder = QtWidgets.QLabel(
            "暂无数据\n运行完成后自动显示综合评分"
        )
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        pg.setConfigOptions(antialias=True, background=_BG, foreground=_FG)
        self._glw = pg.GraphicsLayoutWidget()

        self._plot = self._glw.addPlot(row=0, col=0)
        self._plot.setAspectLocked(True)
        self._plot.hideAxis("left")
        self._plot.hideAxis("bottom")
        self._plot.setRange(xRange=(-130, 130), yRange=(-130, 130))

        self._radar_items: list[pg.PlotDataItem | pg.FillBetweenItem] = []

        v.addWidget(self._placeholder)
        v.addWidget(self._glw)
        self._glw.hide()
        return container

    def _build_score_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget(self)
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(10)

        # ── total score ──
        score_box = QtWidgets.QGroupBox("综合评分")
        score_layout = QtWidgets.QHBoxLayout(score_box)

        self.lbl_score = QtWidgets.QLabel("—")
        self.lbl_score.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_score.setStyleSheet("font-size: 42px; font-weight: bold;")

        self.lbl_grade = QtWidgets.QLabel("—")
        self.lbl_grade.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_grade.setStyleSheet("font-size: 56px; font-weight: bold;")

        score_layout.addWidget(self.lbl_score, stretch=2)
        score_layout.addWidget(self.lbl_grade, stretch=1)
        v.addWidget(score_box)

        # ── dimension table ──
        dim_box = QtWidgets.QGroupBox("评分明细")
        dim_layout = QtWidgets.QVBoxLayout(dim_box)

        self._dim_rows: list[dict] = []
        for i in range(_N_DIM):
            row_w = QtWidgets.QWidget()
            row = QtWidgets.QHBoxLayout(row_w)
            row.setContentsMargins(0, 2, 0, 2)
            row.setSpacing(6)

            lbl_name  = QtWidgets.QLabel(self._DIM_NAMES[i])
            lbl_name.setFixedWidth(110)
            lbl_raw   = QtWidgets.QLabel("—")
            lbl_raw.setFixedWidth(80)
            lbl_raw.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

            bar = QtWidgets.QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setFixedHeight(14)
            bar.setTextVisible(False)

            lbl_s = QtWidgets.QLabel("—")
            lbl_s.setFixedWidth(36)
            lbl_s.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

            row.addWidget(lbl_name)
            row.addWidget(lbl_raw)
            row.addWidget(bar, stretch=1)
            row.addWidget(lbl_s)
            dim_layout.addWidget(row_w)

            self._dim_rows.append({
                "name":  lbl_name,
                "raw":   lbl_raw,
                "bar":   bar,
                "score": lbl_s,
            })

        v.addWidget(dim_box)

        # ── info label ──
        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_info.setWordWrap(True)
        v.addWidget(self.lbl_info)
        v.addStretch()

        return panel

    # ------------------------------------------------------------------ #
    #  Public interface
    # ------------------------------------------------------------------ #

    def feed_ic(self, stats: IcStats) -> None:
        """Receive IcStats from widget; recompute if both sources ready."""
        self._ic_stats = stats
        self._try_refresh()

    def feed_quantile(self, result: QuantileResult) -> None:
        """Receive QuantileResult from widget; recompute if both sources ready."""
        self._q_result = result
        self._try_refresh()

    def clear(self) -> None:
        """Reset to empty state."""
        self._ic_stats   = None
        self._q_result   = None
        self._factor_score = None
        self.lbl_score.setText("—")
        self.lbl_score.setStyleSheet("font-size: 42px; font-weight: bold;")
        self.lbl_grade.setText("—")
        self.lbl_grade.setStyleSheet("font-size: 56px; font-weight: bold;")
        self.lbl_info.setText("")
        for row in self._dim_rows:
            row["raw"].setText("—")
            row["bar"].setValue(0)
            row["score"].setText("—")
        self._clear_radar()
        self._glw.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  Internal: refresh trigger
    # ------------------------------------------------------------------ #

    def _try_refresh(self) -> None:
        if self._ic_stats is None or self._q_result is None:
            return
        fs = self._compute_score(self._ic_stats, self._q_result)
        self._factor_score = fs
        self._render(fs)
        self.score_ready.emit(fs)

    # ------------------------------------------------------------------ #
    #  Score computation
    # ------------------------------------------------------------------ #

    @staticmethod
    def _compute_score(
        ic: IcStats,
        qr: QuantileResult,
    ) -> FactorScore:
        """Compute 6-dimension score from IcStats + QuantileResult."""

        def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
            return max(lo, min(hi, v))

        def _nan(v: float) -> bool:
            return math.isnan(v)

        dims: list[ScoreDimension] = []

        # 1. |IC| mean  (full at 0.10)
        ic_abs = abs(ic.ic_mean) if not _nan(ic.ic_mean) else float("nan")
        ic_score = _clamp(ic_abs / 0.10 * 100) if not _nan(ic_abs) else 0.0
        dims.append(ScoreDimension(
            name="|IC| 均值", raw_value=ic_abs,
            score=ic_score, weight=1.0,
            description="满分基准 |IC|=0.10",
        ))

        # 2. |ICIR|  (full at 2.0)
        icir_abs = abs(ic.icir) if not _nan(ic.icir) else float("nan")
        icir_score = _clamp(icir_abs / 2.0 * 100) if not _nan(icir_abs) else 0.0
        dims.append(ScoreDimension(
            name="|ICIR|", raw_value=icir_abs,
            score=icir_score, weight=1.0,
            description="满分基准 |ICIR|=2.0",
        ))

        # 3. IC Win Rate  (deviation from 50%; full at 75%)
        pr = ic.ic_positive_rate if not _nan(ic.ic_positive_rate) else float("nan")
        if not _nan(pr):
            deviation = abs(pr - 0.5) * 100   # 0~50
            wr_score  = _clamp(deviation / 25.0 * 100)
        else:
            wr_score = 0.0
        dims.append(ScoreDimension(
            name="IC 胜率", raw_value=pr * 100 if not _nan(pr) else float("nan"),
            score=wr_score, weight=1.0,
            description="胜率偏离50%越大越好",
        ))

        # 4. Monotonicity  (full at |mono|=1.0)
        mono = qr.monotonicity_score if not _nan(qr.monotonicity_score) else float("nan")
        mono_score = _clamp(abs(mono) * 100) if not _nan(mono) else 0.0
        dims.append(ScoreDimension(
            name="单调性", raw_value=mono,
            score=mono_score, weight=1.0,
            description="满分基准 |单调性|=1.0",
        ))

        # 5. |L-S Sharpe|  (compute from QuantileResult.long_short_series)
        ls_sharpe = ScoreTab._ls_sharpe(qr)
        ls_abs    = abs(ls_sharpe) if not _nan(ls_sharpe) else float("nan")
        ls_score  = _clamp(ls_abs / 2.0 * 100) if not _nan(ls_abs) else 0.0
        dims.append(ScoreDimension(
            name="|L-S Sharpe|", raw_value=ls_sharpe,
            score=ls_score, weight=1.0,
            description="满分基准 |Sharpe|=2.0",
        ))

        # 6. MDD quality  (lower |MDD| = better; full at mdd=0, zero at mdd>=50%)
        ls_mdd = ScoreTab._ls_mdd(qr)
        if not _nan(ls_mdd):
            mdd_score = _clamp(max(0.0, 1.0 - abs(ls_mdd) / 0.5) * 100)
        else:
            mdd_score = 0.0
        dims.append(ScoreDimension(
            name="L-S 抗回撤", raw_value=ls_mdd,
            score=mdd_score, weight=1.0,
            description="满分基准 MDD=0%",
        ))

        # Weighted total
        total_w   = sum(d.weight for d in dims)
        total_s   = sum(d.score * d.weight for d in dims) / total_w if total_w > 0 else 0.0
        grade     = FactorScore.grade_from_score(total_s)

        return FactorScore(
            vt_symbol=ic.vt_symbol,
            factor_name=ic.factor_name,
            dimensions=dims,
            total_score=total_s,
            grade=grade,
        )

    @staticmethod
    def _ls_sharpe(qr: QuantileResult) -> float:
        """Compute L-S Sharpe from long_short_series (period returns)."""
        ls = qr.long_short_series
        if ls is None or ls.empty:
            return float("nan")
        # long_short_series is cumulative; recover period returns
        nav = (1 + ls.dropna()).values
        if len(nav) < 3:
            return float("nan")
        r   = np.diff(nav) / np.maximum(nav[:-1], 1e-12)
        std = float(np.std(r, ddof=1))
        if std < 1e-12:
            return float("nan")
        ann_factor = math.sqrt(QuantileEngine_TRADING_DAYS / qr.lag)
        return float(np.mean(r)) / std * ann_factor

    @staticmethod
    def _ls_mdd(qr: QuantileResult) -> float:
        """Compute L-S max drawdown from long_short_series."""
        ls = qr.long_short_series
        if ls is None or ls.empty:
            return float("nan")
        nav  = (1 + ls.dropna()).values
        if len(nav) < 2:
            return float("nan")
        peak = np.maximum.accumulate(nav)
        return float(np.min((nav - peak) / np.maximum(peak, 1e-12)))

    # ------------------------------------------------------------------ #
    #  Render
    # ------------------------------------------------------------------ #

    def _render(self, fs: FactorScore) -> None:
        """Update score panel and radar chart."""
        # total score label
        s = fs.total_score
        self.lbl_score.setText(f"{s:.1f}")
        grade_color = _GRADE_COLORS.get(fs.grade, _FG)
        self.lbl_grade.setText(fs.grade)
        self.lbl_grade.setStyleSheet(
            f"font-size: 56px; font-weight: bold; color: {grade_color};"
        )

        # dimension rows
        for i, dim in enumerate(fs.dimensions):
            row = self._dim_rows[i]
            rv  = dim.raw_value
            sc  = dim.score
            # raw value formatting
            if math.isnan(rv):
                row["raw"].setText("—")
            elif dim.name in ("|IC| 均值", "|ICIR|", "|L-S Sharpe|"):
                row["raw"].setText(f"{rv:.4f}")
            elif dim.name == "IC 胜率":
                row["raw"].setText(f"{rv:.1f}%")
            elif dim.name == "单调性":
                row["raw"].setText(f"{rv:.3f}")
            elif dim.name == "L-S 抗回撤":
                row["raw"].setText(f"{rv:.2%}" if not math.isnan(rv) else "—")
            else:
                row["raw"].setText(f"{rv:.4f}")

            row["bar"].setValue(int(sc))
            row["score"].setText(f"{sc:.0f}")

        # info label
        self.lbl_info.setText(
            f"{fs.vt_symbol}  {fs.factor_name}  综合得分 {fs.total_score:.1f} 分（{fs.grade} 级）"
        )

        # radar chart
        self._draw_radar([d.score for d in fs.dimensions])

        self._placeholder.hide()
        self._glw.show()

    # ------------------------------------------------------------------ #
    #  Radar chart drawing
    # ------------------------------------------------------------------ #

    def _clear_radar(self) -> None:
        for item in self._radar_items:
            self._plot.removeItem(item)
        self._radar_items.clear()

    def _draw_radar(self, scores: list[float]) -> None:
        """Draw spider web + score polygon for 6 dimensions."""
        self._clear_radar()
        n    = _N_DIM
        R    = 100.0      # outer ring radius (= score 100)
        angles = [360.0 / n * i for i in range(n)]

        # ── concentric rings ──
        for ring_idx in range(1, _N_RING + 1):
            r = R * ring_idx / _N_RING
            xs, ys = [], []
            for ang in angles:
                x, y = _radar_xy(ang, r)
                xs.append(x); ys.append(y)
            xs.append(xs[0]); ys.append(ys[0])
            ring_color = _GRID_COLOR if ring_idx < _N_RING else "#666666"
            ring_item  = self._plot.plot(
                xs, ys,
                pen=pg.mkPen(color=ring_color, width=1),
            )
            self._radar_items.append(ring_item)

        # ── radial axes + dimension labels ──
        label_r = R * 1.18
        for i, ang in enumerate(angles):
            x0, y0 = 0.0, 0.0
            x1, y1 = _radar_xy(ang, R)
            axis_item = self._plot.plot(
                [x0, x1], [y0, y1],
                pen=pg.mkPen(color=_AXIS_COLOR, width=1),
            )
            self._radar_items.append(axis_item)

            # label
            lx, ly = _radar_xy(ang, label_r)
            text = pg.TextItem(
                text=self._DIM_NAMES[i],
                color=_FG,
                anchor=(0.5, 0.5),
            )
            text.setPos(lx, ly)
            self._plot.addItem(text)
            self._radar_items.append(text)

        # ── reference circle at score=50 ──
        r50  = R * 0.5
        ref_xs, ref_ys = [], []
        for ang in angles:
            x, y = _radar_xy(ang, r50)
            ref_xs.append(x); ref_ys.append(y)
        ref_xs.append(ref_xs[0]); ref_ys.append(ref_ys[0])
        ref_item = self._plot.plot(
            ref_xs, ref_ys,
            pen=pg.mkPen(color=_REF50_COLOR,
                         style=QtCore.Qt.PenStyle.DashLine, width=1),
        )
        self._radar_items.append(ref_item)

        # ── score polygon ──
        poly_xs, poly_ys = [], []
        for i, ang in enumerate(angles):
            r = R * max(0.0, min(100.0, scores[i])) / 100.0
            x, y = _radar_xy(ang, r)
            poly_xs.append(x); poly_ys.append(y)
        poly_xs.append(poly_xs[0]); poly_ys.append(poly_ys[0])

        poly_line = self._plot.plot(
            poly_xs, poly_ys,
            pen=pg.mkPen(color=_POLY_LINE, width=2.5),
        )
        self._radar_items.append(poly_line)

        # filled polygon using FillBetweenItem (origin curve vs score curve)
        origin_curve = self._plot.plot(
            [0.0] * (n + 1), [0.0] * (n + 1),
            pen=pg.mkPen(None),
        )
        score_curve = self._plot.plot(
            poly_xs, poly_ys,
            pen=pg.mkPen(None),
        )
        fill = pg.FillBetweenItem(
            origin_curve, score_curve,
            brush=pg.mkBrush(_POLY_FILL),
        )
        self._plot.addItem(fill)
        self._radar_items.extend([origin_curve, score_curve, fill])

        # ── score value labels on polygon vertices ──
        for i, ang in enumerate(angles):
            r   = R * max(0.0, min(100.0, scores[i])) / 100.0
            lx2 = _radar_xy(ang, r + 8)[0]
            ly2 = _radar_xy(ang, r + 8)[1]
            sv_text = pg.TextItem(
                text=f"{scores[i]:.0f}",
                color=_POLY_LINE,
                anchor=(0.5, 0.5),
            )
            sv_text.setPos(lx2, ly2)
            self._plot.addItem(sv_text)
            self._radar_items.append(sv_text)


# Module-level constant accessed by static method
QuantileEngine_TRADING_DAYS = 252
