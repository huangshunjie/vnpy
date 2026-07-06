"""
system_integration_bus/event.py

System Integration Bus — 事件常量。
"""

APP_NAME = "SystemIntegrationBus"

# ── 总线生命周期 ──────────────────────────────────────────────────────
EVENT_BUS_STARTED        = "eSIB_BusStarted"
EVENT_BUS_STOPPED        = "eSIB_BusStopped"
EVENT_BUS_DEGRADED       = "eSIB_BusDegraded"

# ── 管道阶段事件 ──────────────────────────────────────────────────────
EVENT_STAGE_INGEST       = "eSIB_StageIngest"      # DIL 数据就绪
EVENT_STAGE_SIGNAL       = "eSIB_StageSignal"      # Alpha/Regime 信号就绪
EVENT_STAGE_ALLOCATE     = "eSIB_StageAllocate"    # 组合/资本/风险决策就绪
EVENT_STAGE_EXECUTE      = "eSIB_StageExecute"     # 执行指令就绪
EVENT_STAGE_LEARN        = "eSIB_StageLearn"       # 学习反馈就绪

# ── 跨模块消息路由 ────────────────────────────────────────────────────
EVENT_BUS_MESSAGE        = "eSIB_BusMessage"       # 通用总线消息
EVENT_BUS_BROADCAST      = "eSIB_BusBroadcast"     # 广播至所有订阅者

# ── 子系统健康 ────────────────────────────────────────────────────────
EVENT_ENGINE_HEALTH      = "eSIB_EngineHealth"     # 子引擎心跳/状态
EVENT_ENGINE_OFFLINE     = "eSIB_EngineOffline"    # 子引擎下线
EVENT_ENGINE_RECOVERED   = "eSIB_EngineRecovered"  # 子引擎恢复

# ── 管道完成 ──────────────────────────────────────────────────────────
EVENT_PIPELINE_CYCLE     = "eSIB_PipelineCycle"    # 一个完整管道周期完成
EVENT_PIPELINE_ERROR     = "eSIB_PipelineError"    # 管道阶段出错

# ── 跨模块关键信号（总线转发） ─────────────────────────────────────────
EVENT_SIGNAL_FORWARDED   = "eSIB_SignalForwarded"  # 信号从一个模块转发到另一个
EVENT_RISK_GATE          = "eSIB_RiskGate"         # 风险门控（阻断执行）
EVENT_REGIME_BROADCAST   = "eSIB_RegimeBroadcast"  # Regime 变化广播至所有模块
