"""
risk_engine_2/model/drawdown_model.py

实时 PnL 与回撤数据模型（Phase 3）。

PnLSnapshot   : 单个时间点的 PnL 快照
DrawdownState : 实时回撤状态（峰值 / 当前 / 最大回撤）
AlertRecord   : 单条预警记录（触发时间 / 类型 / 值 / 动作）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..constant import AlertType, RiskAction, RiskLevel


@dataclass
class PnLSnapshot:
    """
    单时间点 PnL 快照。

    由 DrawdownEngine 每次成交或价格更新后生成，
    追加到时间序列用于绘制 PnL 曲线和计算回撤。
    """
    timestamp:       datetime = field(default_factory=datetime.now)

    # 累计 PnL（含已实现 + 浮动）
    realized_pnl:    float = 0.0
    unrealized_pnl:  float = 0.0

    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl

    @property
    def ts_str(self) -> str:
        return self.timestamp.strftime("%H:%M:%S")


@dataclass
class DrawdownState:
    """
    实时回撤状态。

    DrawdownEngine 持有一个 DrawdownState 实例，
    每次 PnL 更新时调用 update() 维护峰值和回撤。
    """
    # 峰值（历史最高 total_pnl）
    peak_pnl:        float = 0.0

    # 当前值
    current_pnl:     float = 0.0

    # 当前回撤（绝对值）= peak - current，始终 >= 0
    current_drawdown: float = 0.0

    # 当前回撤率 = current_drawdown / (nav + peak_pnl)
    current_drawdown_pct: float = 0.0

    # 历史最大回撤（绝对值）
    max_drawdown:     float = 0.0
    max_drawdown_pct: float = 0.0

    # 最大回撤发生时间
    max_drawdown_at:  datetime | None = None

    # 当日亏损（每日重置）
    daily_pnl:       float = 0.0
    daily_loss_pct:  float = 0.0     # daily_pnl / nav（当 daily_pnl < 0 时为正值）

    # 参考净值（用于计算回撤率）
    nav:             float = 0.0

    # 快照时间序列（用于绘图，最多保留 N 条）
    pnl_series:      list[PnLSnapshot] = field(default_factory=list)
    max_series_len:  int = 500

    def update(
        self,
        total_pnl:     float,
        realized_pnl:  float = 0.0,
        unrealized_pnl: float = 0.0,
        nav:           float = 0.0,
    ) -> None:
        """
        用新的 total_pnl 更新回撤状态。

        Parameters
        ----------
        total_pnl      : 当前累计 PnL（已实现 + 浮动）
        realized_pnl   : 已实现 PnL
        unrealized_pnl : 浮动 PnL
        nav            : 组合净值（用于回撤率计算）
        """
        if nav > 0:
            self.nav = nav

        self.current_pnl = total_pnl
        ref = self.nav if self.nav > 0 else 1.0

        # 更新峰值
        if total_pnl > self.peak_pnl:
            self.peak_pnl = total_pnl

        # 当前回撤
        self.current_drawdown = max(self.peak_pnl - total_pnl, 0.0)
        self.current_drawdown_pct = self.current_drawdown / ref

        # 最大回撤
        if self.current_drawdown > self.max_drawdown:
            self.max_drawdown     = self.current_drawdown
            self.max_drawdown_pct = self.current_drawdown_pct
            self.max_drawdown_at  = datetime.now()

        # 日亏损（由 DrawdownEngine 每日重置 daily_pnl_base）
        if total_pnl < 0:
            self.daily_pnl      = total_pnl
            self.daily_loss_pct = abs(total_pnl) / ref

        # 追加快照
        snap = PnLSnapshot(
            realized_pnl   = realized_pnl,
            unrealized_pnl = unrealized_pnl,
        )
        self.pnl_series.append(snap)
        if len(self.pnl_series) > self.max_series_len:
            self.pnl_series = self.pnl_series[-self.max_series_len:]

    def reset_daily(self) -> None:
        """每日开盘重置当日亏损计数。"""
        self.daily_pnl      = 0.0
        self.daily_loss_pct = 0.0

    @property
    def is_in_drawdown(self) -> bool:
        return self.current_drawdown > 1e-9

    @property
    def recovery_needed(self) -> float:
        """从当前回撤恢复到峰值需要的盈利额。"""
        return self.current_drawdown


@dataclass
class AlertRecord:
    """
    单条预警记录。

    由 AlertEngine 触发时生成，追加到历史列表，
    同时发布 EVENT_RISK_ALERT 事件。
    """
    alert_id:   str       = ""
    alert_type: AlertType = AlertType.DRAWDOWN_BREACH
    risk_level: RiskLevel = RiskLevel.WARNING
    action:     RiskAction = RiskAction.ALERT

    # 触发值与阈值
    triggered_value:    float = 0.0
    threshold:          float = 0.0

    # 描述
    message:    str       = ""
    symbol:     str       = ""           # 相关合约（单票预警时填写）

    # 是否已处理（UI 标记）
    acknowledged: bool    = False

    # 时间
    triggered_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: datetime | None = None

    @property
    def ts_str(self) -> str:
        return self.triggered_at.strftime("%H:%M:%S")

    @property
    def level_str(self) -> str:
        return self.risk_level.value

    def acknowledge(self) -> None:
        self.acknowledged    = True
        self.acknowledged_at = datetime.now()
