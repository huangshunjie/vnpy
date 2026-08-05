"""
quant_research/model/log_model.py

日志数据模型。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..constant import LogLevel, LogSource


@dataclass
class LogRecord:
    """日志记录"""
    log_id:       str
    timestamp:    datetime
    level:        LogLevel
    source:       LogSource
    message:      str
    context_id:   Optional[str] = None
    context_name: Optional[str] = None
    details:      str = ""
    user:         str = ""
    
    def to_display_string(self) -> str:
        """格式化为显示字符串"""
        time_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        level_str = self.level.value.upper()
        source_str = self.source.value.upper()
        
        parts = [f"[{time_str}]", f"[{level_str}]", f"[{source_str}]"]
        
        if self.context_id:
            parts.append(f"[{self.context_id}]")
        
        parts.append(self.message)
        
        return " ".join(parts)
