"""
quant_os/event.py

Quant OS 全局事件常量（Phase 1 定义）。

所有事件均以 "eQuantOS." 为前缀，避免与其他模块冲突。
"""

# ── OS 生命周期事件 ──────────────────────────────────────────────────────────
EVENT_OS_START   = "eQuantOS.start"    # OS 启动
EVENT_OS_STOP    = "eQuantOS.stop"     # OS 停止

# ── 模块注册事件 ─────────────────────────────────────────────────────────────
EVENT_MODULE_REGISTERED = "eQuantOS.module.registered"  # 模块注册成功

# ── 生命周期状态变更事件 ─────────────────────────────────────────────────────
EVENT_LIFECYCLE_CHANGE  = "eQuantOS.lifecycle.change"   # Alpha/Strategy 状态流转

# ── 策略调度触发事件 ─────────────────────────────────────────────────────────
EVENT_STRATEGY_TRIGGER  = "eQuantOS.strategy.trigger"   # 调度器触发策略重算

# ── 系统日志事件 ─────────────────────────────────────────────────────────────
EVENT_SYSTEM_LOG        = "eQuantOS.log"                # OS 级系统日志
