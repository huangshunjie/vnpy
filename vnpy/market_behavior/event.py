"""
market_behavior/event.py
事件常量定义
"""

# ── K线解析 ───────────────────────────────────────────────────────────
EVENT_MB_CANDLE_PARSED      = "eMB_CandleParsed"       # 单根K线解析完成

# ── 价格事件 ──────────────────────────────────────────────────────────
EVENT_MB_EVENT_DETECTED     = "eMB_EventDetected"      # 行为事件触发
EVENT_MB_LIMIT_UP           = "eMB_LimitUp"            # 涨停
EVENT_MB_LIMIT_DOWN         = "eMB_LimitDown"          # 跌停
EVENT_MB_RISE_PCT           = "eMB_RisePct"            # 大涨
EVENT_MB_FALL_PCT           = "eMB_FallPct"            # 大跌
EVENT_MB_CONTINUOUS         = "eMB_Continuous"         # 连续行为触发

# ── 形态识别 ──────────────────────────────────────────────────────────
EVENT_MB_PATTERN_FOUND      = "eMB_PatternFound"       # 单K形态识别
EVENT_MB_SEQUENCE_FOUND     = "eMB_SequenceFound"      # K线组合识别
EVENT_MB_BREAKOUT_FOUND     = "eMB_BreakoutFound"      # 突破信号

# ── 因子与标签 ────────────────────────────────────────────────────────
EVENT_MB_FACTOR_UPDATED     = "eMB_FactorUpdated"      # 行为因子更新
EVENT_MB_LABEL_UPDATED      = "eMB_LabelUpdated"       # 行为标签更新

# ── 选股适配 ──────────────────────────────────────────────────────────
EVENT_MB_CONDITION_READY    = "eMB_ConditionReady"     # 选股条件生成完成

# ── 回测 ──────────────────────────────────────────────────────────────
EVENT_MB_BACKTEST_STARTED   = "eMB_BacktestStarted"    # 回测开始
EVENT_MB_BACKTEST_PROGRESS  = "eMB_BacktestProgress"   # 回测进度
EVENT_MB_BACKTEST_DONE      = "eMB_BacktestDone"       # 回测完成
EVENT_MB_BACKTEST_FAILED    = "eMB_BacktestFailed"     # 回测失败

# ── 系统 ──────────────────────────────────────────────────────────────
EVENT_MB_LOG                = "eMB_Log"                # 系统日志
EVENT_MB_STARTED            = "eMB_Started"            # 引擎启动
EVENT_MB_STOPPED            = "eMB_Stopped"            # 引擎停止
EVENT_MB_ERROR              = "eMB_Error"              # 系统错误
