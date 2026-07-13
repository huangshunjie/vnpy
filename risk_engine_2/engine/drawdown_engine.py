"""
risk_engine_2/engine/drawdown_engine.py

DrawdownEngine — 实时 PnL + 回撤追踪（Phase 3）。

职责：
  - 接收成交回报和价格更新，维护实时 PnL 和 DrawdownState
  - 检测回撤阈值触发
  - 输出 DrawdownState 供 AlertEngine 校验和 UI 展示

设计原则：无状态计算 + 有状态快照维护。
"""

from __future__ import annotations

from datetime import datetime, date

from ..model.drawdown_model import DrawdownState, PnLSnapshot
from ..utils.risk_metrics import compute_drawdown, check_drawdown_limit, check_daily_loss_limit


class DrawdownEngine:
    """实时 PnL 与回撤追踪引擎（Phase 3）。"""

    def __init__(self) -> None:
        self._state         = DrawdownState()
        self._realized_pnl: float = 0.0
        self._nav:          float = 0.0
        self._today:        date  = date.today()

        # 回撤阈值
        self.drawdown_warning: float = 0.05   # 5% 预警
        self.drawdown_limit:   float = 0.10   # 10% 硬限制
        self.daily_loss_warn:  float = 0.03   # 3% 日亏损预警
        self.daily_loss_limit: float = 0.05   # 5% 日亏损硬限制

    # ------------------------------------------------------------------ #
    #  外部注入
    # ------------------------------------------------------------------ #

    def set_nav(self, nav: float) -> None:
        if nav > 0:
            self._nav = nav
            self._state.nav = nav

    def set_thresholds(
        self,
        drawdown_warning:  float = 0.05,
        drawdown_limit:    float = 0.10,
        daily_loss_warn:   float = 0.03,
        daily_loss_limit:  float = 0.05,
    ) -> None:
        """更新回撤 / 日亏损阈值（UI 可调）。"""
        self.drawdown_warning  = drawdown_warning
        self.drawdown_limit    = drawdown_limit
        self.daily_loss_warn   = daily_loss_warn
        self.daily_loss_limit  = daily_loss_limit

    # ------------------------------------------------------------------ #
    #  成交 / 价格更新
    # ------------------------------------------------------------------ #

    def on_fill(self, fill: dict) -> None:
        """
        处理成交回报，更新已实现 PnL。

        fill 应包含 "realized_pnl" 字段（来自 FillRecord）。
        若无此字段，按简单成本法估算：Δ = (fill_price - avg_price) × volume × multiplier
        """
        self._check_daily_reset()
        realized = float(fill.get("realized_pnl", 0.0))
        self._realized_pnl += realized
        self._refresh_state()

    def on_price_update(
        self,
        unrealized_pnl: float,
        nav:            float = 0.0,
    ) -> None:
        """
        接收最新浮动 PnL（由 ExposureEngine 计算后传入）。

        Parameters
        ----------
        unrealized_pnl : 当前全组合浮动 PnL
        nav            : 最新净值（可选，0 = 使用已注入值）
        """
        self._check_daily_reset()
        if nav > 0:
            self._nav = nav
            self._state.nav = nav

        total = self._realized_pnl + unrealized_pnl
        self._state.update(
            total_pnl      = total,
            realized_pnl   = self._realized_pnl,
            unrealized_pnl = unrealized_pnl,
            nav            = self._nav,
        )

    # ------------------------------------------------------------------ #
    #  阈值校验
    # ------------------------------------------------------------------ #

    def check_drawdown(self) -> tuple[bool, str]:
        """
        校验当前回撤是否超阈值。

        Returns
        -------
        (passed, message)
          passed=False → 触发硬限制，需减仓 / 暂停
        """
        return check_drawdown_limit(
            drawdown_pct      = self._state.current_drawdown_pct,
            hard_limit        = self.drawdown_limit,
            warning_threshold = self.drawdown_warning,
        )

    def check_daily_loss(self) -> tuple[bool, str]:
        """校验当日亏损是否超阈值。"""
        return check_daily_loss_limit(
            daily_loss_pct    = self._state.daily_loss_pct,
            hard_limit        = self.daily_loss_limit,
            warning_threshold = self.daily_loss_warn,
        )

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_state(self) -> DrawdownState:
        """返回当前回撤状态。"""
        return self._state

    def get_pnl_series(self) -> list[PnLSnapshot]:
        return list(self._state.pnl_series)

    def clear(self) -> None:
        self._state        = DrawdownState(nav=self._nav)
        self._realized_pnl = 0.0

    # ------------------------------------------------------------------ #
    #  内部
    # ------------------------------------------------------------------ #

    def _refresh_state(self) -> None:
        self._state.update(
            total_pnl      = self._realized_pnl,
            realized_pnl   = self._realized_pnl,
            unrealized_pnl = 0.0,
            nav            = self._nav,
        )

    def _check_daily_reset(self) -> None:
        today = date.today()
        if today != self._today:
            self._today = today
            self._state.reset_daily()
