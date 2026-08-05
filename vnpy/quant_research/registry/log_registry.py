"""
quant_research/registry/log_registry.py

日志注册表 — 内存存储所有系统日志。
"""
from __future__ import annotations
from collections import deque
from datetime import datetime
from typing import List, Optional

from ..constant import LogLevel, LogSource
from ..model.log_model import LogRecord


class LogRegistry:
    """日志注册表 — 使用环形缓冲区存储最近的日志"""

    def __init__(self, max_logs: int = 10000):
        self._logs: deque[LogRecord] = deque(maxlen=max_logs)
        self._counter = 0

    def add(
        self,
        level:        LogLevel,
        source:       LogSource,
        message:      str,
        context_id:   Optional[str] = None,
        context_name: Optional[str] = None,
        details:      str = "",
        user:         str = "",
    ) -> LogRecord:
        """添加日志记录"""
        self._counter += 1
        record = LogRecord(
            log_id       = f"LOG-{self._counter:06d}",
            timestamp    = datetime.now(),
            level        = level,
            source       = source,
            message      = message,
            context_id   = context_id,
            context_name = context_name,
            details      = details,
            user         = user,
        )
        self._logs.append(record)
        return record

    def get_recent(self, n: int = 100) -> List[LogRecord]:
        """获取最近 n 条日志"""
        logs = list(self._logs)
        return logs[-n:] if len(logs) > n else logs

    def filter(
        self,
        level:      Optional[LogLevel]  = None,
        source:     Optional[LogSource] = None,
        context_id: Optional[str]       = None,
        keyword:    Optional[str]       = None,
        limit:      int                 = 1000,
    ) -> List[LogRecord]:
        """筛选日志"""
        results = []
        for log in reversed(self._logs):
            if level and log.level != level:
                continue
            if source and log.source != source:
                continue
            if context_id and log.context_id != context_id:
                continue
            if keyword and keyword.lower() not in log.message.lower():
                continue
            results.append(log)
            if len(results) >= limit:
                break
        return results

    def get_by_level(self, level: LogLevel, limit: int = 100) -> List[LogRecord]:
        """按级别获取日志"""
        return self.filter(level=level, limit=limit)

    def get_by_source(self, source: LogSource, limit: int = 100) -> List[LogRecord]:
        """按来源获取日志"""
        return self.filter(source=source, limit=limit)

    def search(self, keyword: str, limit: int = 100) -> List[LogRecord]:
        """搜索日志"""
        return self.filter(keyword=keyword, limit=limit)

    def count_by_level(self) -> dict:
        """统计各级别日志数量"""
        counts = {level: 0 for level in LogLevel}
        for log in self._logs:
            counts[log.level] += 1
        return counts

    def count_by_source(self) -> dict:
        """统计各来源日志数量"""
        counts = {source: 0 for source in LogSource}
        for log in self._logs:
            counts[log.source] += 1
        return counts

    def clear(self) -> None:
        """清空所有日志"""
        self._logs.clear()
        self._counter = 0

    def get_errors(self, limit: int = 50) -> List[LogRecord]:
        """获取错误日志"""
        results = []
        for log in reversed(self._logs):
            if log.level in (LogLevel.ERROR, LogLevel.CRITICAL):
                results.append(log)
                if len(results) >= limit:
                    break
        return results

    def get_warnings(self, limit: int = 50) -> List[LogRecord]:
        """获取警告日志"""
        return self.get_by_level(LogLevel.WARNING, limit)

    def total_count(self) -> int:
        """总日志数"""
        return len(self._logs)
