"""
screening/event.py

Quant Screening Platform — 事件类型定义（Phase 1）。
"""

# ── Universe Manager ──────────────────────────────────────────────────
EVENT_UNIVERSE_UPDATED      = "eScreeningUniverseUpdated"      # 股票池已更新
EVENT_UNIVERSE_FILTER_DONE  = "eScreeningUniverseFilterDone"   # 基础过滤完成

# ── Condition Engine ──────────────────────────────────────────────────
EVENT_CONDITION_CHANGED     = "eScreeningConditionChanged"     # 条件树已修改
EVENT_CONDITION_SAVED       = "eScreeningConditionSaved"       # 条件规则已保存

# ── Screening Engine（主流程）────────────────────────────────────────
EVENT_SCREENING_STARTED     = "eScreeningStarted"              # 选股开始
EVENT_SCREENING_PROGRESS    = "eScreeningProgress"             # 选股进度更新
EVENT_SCREENING_DONE        = "eScreeningDone"                 # 选股完成
EVENT_SCREENING_ERROR       = "eScreeningError"                # 选股出错

# ── Factor Ranking ────────────────────────────────────────────────────
EVENT_FACTOR_RANK_UPDATED   = "eScreeningFactorRankUpdated"    # 因子排序完成

# ── Scoring Engine ────────────────────────────────────────────────────
EVENT_SCORE_UPDATED         = "eScreeningScoreUpdated"         # 综合评分更新

# ── Risk Filter ───────────────────────────────────────────────────────
EVENT_RISK_FILTER_DONE      = "eScreeningRiskFilterDone"       # 风险过滤完成

# ── Backtest ──────────────────────────────────────────────────────────
EVENT_BACKTEST_STARTED      = "eScreeningBacktestStarted"      # 回测开始
EVENT_BACKTEST_PROGRESS     = "eScreeningBacktestProgress"     # 回测进度
EVENT_BACKTEST_DONE         = "eScreeningBacktestDone"         # 回测完成

# ── Template ──────────────────────────────────────────────────────────
EVENT_TEMPLATE_SAVED        = "eScreeningTemplateSaved"        # 模板保存
EVENT_TEMPLATE_LOADED       = "eScreeningTemplateLoaded"       # 模板加载

# ── Portfolio ─────────────────────────────────────────────────────────
EVENT_PORTFOLIO_GENERATED   = "eScreeningPortfolioGenerated"   # 组合生成完成

# ── Log ───────────────────────────────────────────────────────────────
EVENT_SCREENING_LOG         = "eScreeningLog"                  # 日志消息
