"""
base.py — 批量回测研究模块的公共常量与事件类型定义

Event 命名约定：
    EVENT_BATCH_*  本模块发出的所有事件前缀
"""

APP_NAME = "BatchResearch"

# ------------------------------------------------------------------ #
#  Event type strings
# ------------------------------------------------------------------ #

# 回测整体进度（data = ProgressData）
EVENT_BATCH_PROGRESS  = "eBatchProgress"

# 单个股票回测完成（data = BacktestResult）
EVENT_BATCH_RESULT    = "eBatchResult"

# 日志消息（data = str）
EVENT_BATCH_LOG       = "eBatchLog"

# 回测全部完成（data = RunSummary）
EVENT_BATCH_FINISHED  = "eBatchFinished"

# 回测被用户中止（data = None）
EVENT_BATCH_STOPPED   = "eBatchStopped"


# ------------------------------------------------------------------ #
#  Progress data container  (passed with EVENT_BATCH_PROGRESS)
# ------------------------------------------------------------------ #

class ProgressData:
    """Progress snapshot emitted after each task completes."""

    __slots__ = (
        "completed", "total", "success", "skipped", "failed",
        "current_symbol", "elapsed_seconds",
    )

    def __init__(
        self,
        completed: int,
        total: int,
        success: int,
        skipped: int,
        failed: int,
        current_symbol: str = "",
        elapsed_seconds: float = 0.0,
    ) -> None:
        self.completed       = completed
        self.total           = total
        self.success         = success
        self.skipped         = skipped
        self.failed          = failed
        self.current_symbol  = current_symbol
        self.elapsed_seconds = elapsed_seconds

    @property
    def percent(self) -> float:
        return self.completed / self.total * 100 if self.total else 0.0

    def __repr__(self) -> str:
        return (
            f"ProgressData({self.completed}/{self.total} "
            f"{self.percent:.1f}% "
            f"ok={self.success} skip={self.skipped} fail={self.failed})"
        )
