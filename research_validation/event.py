"""
research_validation/event.py

Research Validation System 事件常量（Phase 1）。

命名空间前缀 "eValidation." 与其他模块完全隔离。
"""

# 验证任务启动
# data: ValidationTask
EVENT_VALIDATION_START    = "eValidation.start"

# 验证进度更新
# data: dict {"task_id": str, "progress": float, "message": str}
EVENT_VALIDATION_PROGRESS = "eValidation.progress"

# 验证结果就绪
# data: ValidationResult
EVENT_VALIDATION_RESULT   = "eValidation.result"

# 验证出错
# data: dict {"task_id": str, "error": str, "traceback": str}
EVENT_VALIDATION_ERROR    = "eValidation.error"

# 验证日志
# data: str
EVENT_VALIDATION_LOG      = "eValidation.log"

# 验证任务取消
# data: str  (task_id)
EVENT_VALIDATION_CANCEL   = "eValidation.cancel"
