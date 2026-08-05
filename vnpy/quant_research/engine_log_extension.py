"""
quant_research/engine_log_extension.py

引擎日志扩展方法 - 需要添加到 ResearchEngine 类中

使用说明：
将此文件中的方法复制到 engine.py 的 ResearchEngine 类末尾，
并在 __init__ 方法中添加：
    from .registry import LogRegistry
    self.log_registry = LogRegistry()
    self.log(LogLevel.INFO, LogSource.SYSTEM, "量化研究平台引擎已启动")
"""
from typing import List, Optional
from ..constant import LogLevel, LogSource
from ..event import EVENT_LOG_MESSAGE


def log(
    self,
    level: LogLevel,
    source: LogSource,
    message: str,
    context_id: Optional[str] = None,
    context_name: Optional[str] = None,
    details: str = "",
    user: str = "",
) -> None:
    """记录日志"""
    if not hasattr(self, 'log_registry'):
        from .registry import LogRegistry
        self.log_registry = LogRegistry()
    
    record = self.log_registry.add(
        level=level,
        source=source,
        message=message,
        context_id=context_id,
        context_name=context_name,
        details=details,
        user=user,
    )
    self._put(EVENT_LOG_MESSAGE, record)


def get_recent_logs(self, n: int = 100) -> List:
    """获取最近的日志"""
    if not hasattr(self, 'log_registry'):
        from .registry import LogRegistry
        self.log_registry = LogRegistry()
    return self.log_registry.get_recent(n)


def filter_logs(
    self,
    level: Optional[LogLevel] = None,
    source: Optional[LogSource] = None,
    context_id: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 1000,
) -> List:
    """筛选日志"""
    if not hasattr(self, 'log_registry'):
        from .registry import LogRegistry
        self.log_registry = LogRegistry()
    return self.log_registry.filter(level, source, context_id, keyword, limit)


def get_error_logs(self, limit: int = 50) -> List:
    """获取错误日志"""
    if not hasattr(self, 'log_registry'):
        from .registry import LogRegistry
        self.log_registry = LogRegistry()
    return self.log_registry.get_errors(limit)


def get_log_statistics(self) -> dict:
    """获取日志统计信息"""
    if not hasattr(self, 'log_registry'):
        from .registry import LogRegistry
        self.log_registry = LogRegistry()
    return {
        'total': self.log_registry.total_count(),
        'by_level': self.log_registry.count_by_level(),
        'by_source': self.log_registry.count_by_source(),
    }


def clear_logs(self) -> None:
    """清空日志"""
    if not hasattr(self, 'log_registry'):
        from .registry import LogRegistry
        self.log_registry = LogRegistry()
    self.log_registry.clear()
    self.log(LogLevel.INFO, LogSource.SYSTEM, "日志已清空")
