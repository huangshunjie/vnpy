"""
BacktestTask / BacktestResult

表示一次单股票回测任务及其执行结果的数据类。

设计约定：
- BacktestTask  是「输入」，描述回测任务本身
- BacktestResult 是「输出」，承载 calculate_statistics() 返回的全部指标
  以及任务元信息，便于后续汇总、排序、导出
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from vnpy_ctastrategy.template import CtaTemplate


class TaskStatus(Enum):
    """回测任务的生命周期状态。"""
    PENDING   = "pending"    # 等待执行
    RUNNING   = "running"    # 执行中
    SUCCESS   = "success"    # 成功完成
    FAILED    = "failed"     # 执行失败（异常或无数据）
    SKIPPED   = "skipped"    # 主动跳过（如停牌、数据不足）


@dataclass
class BacktestTask:
    """
    单股票回测任务描述。

    一个 BacktestTask 对应一次 BacktestingEngine 调用。
    Worker 从此对象中读取全部信息，外部不直接操作 BacktestingEngine。
    """

    # ---------- 标的 ----------
    vt_symbol: str                          # 例如 "000001.SZSE"

    # ---------- 策略 ----------
    strategy_class: type[CtaTemplate]       # 策略类（不是实例）
    strategy_setting: dict[str, Any] = field(default_factory=dict)

    # ---------- 回测时间范围（覆盖全局参数，留 None 则使用全局）----------
    start: datetime | None = None
    end: datetime | None = None

    # ---------- 任务元信息 ----------
    task_id: str = ""                       # 可选，用于日志追踪；空时由 Scheduler 自动生成
    status: TaskStatus = TaskStatus.PENDING

    def __post_init__(self) -> None:
        if not self.vt_symbol:
            raise ValueError("vt_symbol 不能为空")
        if "." not in self.vt_symbol:
            raise ValueError(
                f"vt_symbol 格式错误，必须为 'symbol.exchange'，当前值：{self.vt_symbol}"
            )

    @property
    def symbol(self) -> str:
        """股票代码部分，例如 '000001'。"""
        return self.vt_symbol.split(".")[0]

    @property
    def exchange(self) -> str:
        """交易所部分，例如 'SZSE'。"""
        return self.vt_symbol.split(".")[1]

    def __repr__(self) -> str:
        return (
            f"BacktestTask(vt_symbol={self.vt_symbol!r}, "
            f"strategy={self.strategy_class.__name__}, "
            f"status={self.status.value})"
        )


@dataclass
class BacktestResult:
    """
    单股票回测结果。

    statistics 字段直接承载 BacktestingEngine.calculate_statistics() 的返回值，
    键名与官方完全一致，不做任何重命名，保持零适配成本。

    官方统计字段（vnpy_ctastrategy 4.4.0）：
        start_date, end_date,
        total_days, profit_days, loss_days,
        capital, end_balance,
        max_drawdown, max_ddpercent, max_drawdown_duration,
        total_net_pnl, daily_net_pnl,
        total_commission, daily_commission,
        total_slippage, daily_slippage,
        total_turnover, daily_turnover,
        total_trade_count, daily_trade_count,
        total_return, annual_return, daily_return, return_std,
        sharpe_ratio, ewm_sharpe, return_drawdown_ratio, rgr_ratio
    """

    # ---------- 来源任务标识 ----------
    vt_symbol: str
    task_id: str
    strategy_name: str

    # ---------- 执行状态 ----------
    status: TaskStatus = TaskStatus.PENDING

    # ---------- 时间戳 ----------
    run_start_time: datetime | None = None
    run_end_time: datetime | None = None

    # ---------- 官方统计指标（原样存储）----------
    statistics: dict[str, Any] = field(default_factory=dict)

    # ---------- 错误信息（status=FAILED 时填充）----------
    error_msg: str = ""

    # L2 预留：逐日净値序列（待 Worker 扩展后填充）
    daily_results: list | None = None

    # L3 预留：逐笔交易记录（待 Worker 扩展后填充）
    trades: list | None = None

    # ---------- 常用指标快捷属性 ----------
    @property
    def total_return(self) -> float:
        return float(self.statistics.get("total_return", 0.0))

    @property
    def annual_return(self) -> float:
        return float(self.statistics.get("annual_return", 0.0))

    @property
    def sharpe_ratio(self) -> float:
        return float(self.statistics.get("sharpe_ratio", 0.0))

    @property
    def max_ddpercent(self) -> float:
        return float(self.statistics.get("max_ddpercent", 0.0))

    @property
    def return_drawdown_ratio(self) -> float:
        return float(self.statistics.get("return_drawdown_ratio", 0.0))

    @property
    def total_trade_count(self) -> int:
        return int(self.statistics.get("total_trade_count", 0))

    @property
    def elapsed_seconds(self) -> float | None:
        """回测耗时（秒），两端时间戳均存在时返回。"""
        if self.run_start_time and self.run_end_time:
            return (self.run_end_time - self.run_start_time).total_seconds()
        return None

    def to_flat_dict(self) -> dict[str, Any]:
        """
        将结果展开为单层字典，用于 CSV / Excel 导出。
        元信息字段前缀 '_' 与统计指标字段平铺在同一行。
        """
        row: dict[str, Any] = {
            "vt_symbol": self.vt_symbol,
            "task_id": self.task_id,
            "strategy_name": self.strategy_name,
            "status": self.status.value,
            "elapsed_seconds": self.elapsed_seconds,
            "error_msg": self.error_msg,
        }
        row.update(self.statistics)
        return row

    def __repr__(self) -> str:
        return (
            f"BacktestResult(vt_symbol={self.vt_symbol!r}, "
            f"status={self.status.value}, "
            f"total_return={self.total_return:.2f}%, "
            f"sharpe={self.sharpe_ratio:.2f})"
        )
