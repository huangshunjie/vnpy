"""
strategy_lifecycle_ai/dispatcher.py  (Phase 5 - Final)

LifecycleEngine — 策略生命周期系统顶层引擎（Phase 5 完整版）。

Phase 5 新增：
  - evaluate_retirement()     单策略退役评估
  - auto_screen_retirement()  批量退役筛查
  - execute_retirement()      执行退役（含绩效/衰减数据回填）
  - archive_strategy()        归档
  - restore_strategy()        恢复
  - auto_cycle()              全周期自动调度（track→decay→evolve→retire）
  - 广播所有生命周期事件

❌ 禁止任何交易执行逻辑
"""

from __future__ import annotations
from datetime import datetime

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import (APP_NAME, StrategyPhase, PerformanceRating,
                       DecayLevel, EvolutionType, RetirementReason)
from .event import (
    EVENT_STRATEGY_REGISTERED, EVENT_STRATEGY_UPDATED,
    EVENT_STRATEGY_DECAY_DETECTED, EVENT_STRATEGY_EVOLVED,
    EVENT_STRATEGY_RETIRED, EVENT_PERFORMANCE_UPDATE,
    EVENT_DECAY_LEVEL_CHANGED, EVENT_EVOLUTION_TRIGGERED,
    EVENT_LIFECYCLE_HEARTBEAT,
)
from .engine.lifecycle_engine   import LifecycleEngine   as _LifecycleCore
from .engine.registry_engine    import RegistryEngine
from .engine.performance_engine import PerformanceEngine
from .engine.decay_engine       import DecayEngine
from .engine.evolution_engine   import EvolutionEngine
from .engine.retirement_engine  import RetirementEngine
from .datasource.strategy_loader    import StrategyLoader
from .datasource.performance_loader import PerformanceLoader
from .datasource.portfolio_loader   import PortfolioLoader
from .model.strategy_model    import StrategyState
from .model.performance_model import PerformanceState
from .model.decay_model       import DecayState
from .model.evolution_model   import EvolutionRecord
from .engine.retirement_engine import RetirementEvaluation, RetirementRecord


class LifecycleEngine(BaseEngine):
    """Strategy Lifecycle Intelligence System (Phase 5 - Final)."""

    engine_name = APP_NAME

    def __init__(self, main_engine, event_engine):
        super().__init__(main_engine, event_engine, APP_NAME)
        self._started_at  = None
        self._log_records = []
        self._lifecycle_core = _LifecycleCore(log_fn=self._log)
        self._registry       = RegistryEngine(log_fn=self._log)
        self._performance    = PerformanceEngine(log_fn=self._log)
        self._decay          = DecayEngine(log_fn=self._log)
        self._evolution      = EvolutionEngine(log_fn=self._log)
        self._retirement     = RetirementEngine(log_fn=self._log)
        self._strategy_loader    = StrategyLoader(main_engine=main_engine)
        self._performance_loader = PerformanceLoader(main_engine=main_engine)
        self._portfolio_loader   = PortfolioLoader(main_engine=main_engine)
        self._regime_context     = {}
        self._log("[" + APP_NAME + "] Engine created (Phase 5)")

    # ── BaseEngine ───────────────────────────────────────────────────────

    def init(self):
        self._log("[" + APP_NAME + "] init()")
        self._lifecycle_core.init()

    def start(self):
        self._started_at = datetime.now()
        self._log("[" + APP_NAME + "] start()")
        self._lifecycle_core.start()
        self.dispatch_event(EVENT_LIFECYCLE_HEARTBEAT,
            {"status": "started", "phase": 5,
             "strategy_count": self._registry.count()})

    def stop(self):
        self._log("[" + APP_NAME + "] stop()")
        self._lifecycle_core.stop()

    def close(self):
        self.stop()

    # ── Phase 1 ──────────────────────────────────────────────────────────

    def register_strategy(self, strategy_id, strategy_name="", meta=None):
        state = self._registry.register(strategy_id, strategy_name, meta)
        self.dispatch_event(EVENT_STRATEGY_REGISTERED, state.to_dict())
        return state

    def update_strategy_state(self, strategy_id, **kwargs):
        state = self._registry.get(strategy_id)
        if state is None:
            return None
        for k, v in kwargs.items():
            if hasattr(state, k):
                setattr(state, k, v)
        state.updated_at = datetime.now()
        self.dispatch_event(EVENT_STRATEGY_UPDATED, state.to_dict())
        return state

    # ── Phase 2 ──────────────────────────────────────────────────────────

    def track_performance(self, strategy_id, pnl_series, trade_count=0):
        if self._registry.get(strategy_id) is None:
            self._registry.register(strategy_id)
        state = self._performance.analyze(strategy_id, pnl_series, trade_count)
        s = self._registry.get(strategy_id)
        if s:
            s.sharpe = state.sharpe; s.max_drawdown = state.max_drawdown
            s.win_rate = state.win_rate; s.rating = state.rating
            s.updated_at = datetime.now()
        self.dispatch_event(EVENT_PERFORMANCE_UPDATE, state.to_dict())
        return state

    def batch_track(self, data):
        return {sid: self.track_performance(sid, pnl, tc)
                for sid, (pnl, tc) in data.items()}

    # ── Phase 3 ──────────────────────────────────────────────────────────

    def set_regime_context(self, context):
        self._regime_context = dict(context)

    def detect_decay(self, strategy_id, pnl_series, returns=None, regime_context=None):
        if self._registry.get(strategy_id) is None:
            self._registry.register(strategy_id)
        if returns is None:
            from .utils.performance_utils import compute_returns
            returns = compute_returns(pnl_series)
        sharpe_series = self._performance.get_rolling_sharpe(strategy_id, window=60)
        dd_series     = self._performance.get_rolling_drawdown(strategy_id, window=60)
        if not sharpe_series:
            ps = self._performance.get_state(strategy_id); sharpe_series = [ps.sharpe]
        if not dd_series:
            ps = self._performance.get_state(strategy_id); dd_series = [ps.max_drawdown]
        ctx = regime_context if regime_context is not None else self._regime_context
        decay_state = self._decay.detect(
            strategy_id=strategy_id, sharpe_series=sharpe_series,
            dd_series=dd_series, returns=returns,
            pnl_series=pnl_series, regime_context=ctx)
        s_state = self._registry.get(strategy_id)
        if s_state is not None:
            if decay_state.decay_level in (DecayLevel.SEVERE, DecayLevel.CRITICAL):
                s_state.phase = StrategyPhase.DECAY; s_state.updated_at = datetime.now()
            elif decay_state.decay_level == DecayLevel.NONE and s_state.phase == StrategyPhase.DECAY:
                s_state.phase = StrategyPhase.RECOVERING; s_state.updated_at = datetime.now()
        self.dispatch_event(EVENT_STRATEGY_DECAY_DETECTED, decay_state.to_dict())
        if decay_state.level_changed:
            self.dispatch_event(EVENT_DECAY_LEVEL_CHANGED, {
                **decay_state.to_dict(),
                "prev_level": decay_state.prev_level.value,
                "new_level":  decay_state.decay_level.value,
            })
        return decay_state

    def auto_detect_all_decay(self, pnl_map, trade_map=None):
        results = {}
        for sid, pnl in pnl_map.items():
            tc = (trade_map or {}).get(sid, 0)
            self.track_performance(sid, pnl, tc)
            results[sid] = self.detect_decay(sid, pnl)
        return results

    # ── Phase 4 ──────────────────────────────────────────────────────────

    def evolve_strategy(self, strategy_id, params, trigger_reason="auto",
                        peer_id="", peer_params=None, seed=None):
        if self._registry.get(strategy_id) is None:
            self._registry.register(strategy_id)
        s_state   = self._registry.get(strategy_id)
        p_state   = self._performance.get_state(strategy_id)
        d_state   = self._decay.get_state(strategy_id)
        sharpe      = p_state.sharpe; decay_score = d_state.decay_score
        decay_level = d_state.decay_level; live_days = getattr(s_state, "live_days", 0)
        win_rate    = p_state.win_rate
        weights     = s_state.meta.get("factor_weights", {}) if s_state else {}
        peer_sharpe = 0.0
        if peer_id:
            peer_p = self._performance.get_state(peer_id); peer_sharpe = peer_p.sharpe
        record = self._evolution.evolve(
            strategy_id=strategy_id, params=params, sharpe=sharpe,
            decay_score=decay_score, live_days=live_days, win_rate=win_rate,
            decay_level=decay_level, weights=weights or None,
            peer_id=peer_id, peer_params=peer_params, peer_sharpe=peer_sharpe,
            trigger_reason=trigger_reason, seed=seed)
        self._evolution.register_candidate(
            strategy_id, sharpe, decay_score, live_days, win_rate, params)
        if s_state is not None:
            s_state.phase = StrategyPhase.RECOVERING; s_state.updated_at = datetime.now()
        payload = record.to_dict()
        self.dispatch_event(EVENT_EVOLUTION_TRIGGERED, payload)
        self.dispatch_event(EVENT_STRATEGY_EVOLVED,    payload)
        return record

    def batch_evolve(self, strategy_ids, params_map, trigger_reason="batch"):
        results = {}
        strong      = self._evolution.get_strong_strategies()
        peer_id     = strong[0]["strategy_id"] if strong else ""
        peer_params = strong[0]["params"]       if strong else None
        for sid in strategy_ids:
            results[sid] = self.evolve_strategy(
                sid, params_map.get(sid, {}), trigger_reason, peer_id, peer_params)
        return results

    def update_evolution_result(self, evolution_id, strategy_id, sharpe_after):
        record = self._evolution.update_result(evolution_id, strategy_id, sharpe_after)
        if record is not None:
            self.dispatch_event(EVENT_STRATEGY_EVOLVED, record.to_dict())
        return record

    def auto_evolve_decaying(self, pnl_map, params_map, trade_map=None):
        results = {}
        for sid, pnl in pnl_map.items():
            tc = (trade_map or {}).get(sid, 0)
            self.track_performance(sid, pnl, tc)
            d_state = self.detect_decay(sid, pnl)
            if d_state.decay_level.value in ("moderate", "severe", "critical"):
                results[sid] = self.evolve_strategy(
                    sid, params_map.get(sid, {}), trigger_reason="decay_triggered")
        return results

    # ── Phase 5 核心接口 ─────────────────────────────────────────────────

    def evaluate_retirement(self, strategy_id, force=False):
        """
        单策略退役条件评估。

        从已有的 Performance / Decay 状态取数，返回 RetirementEvaluation。
        """
        if self._registry.get(strategy_id) is None:
            self._registry.register(strategy_id)
        p = self._performance.get_state(strategy_id)
        d = self._decay.get_state(strategy_id)
        s = self._registry.get(strategy_id)
        return self._retirement.evaluate(
            strategy_id  = strategy_id,
            sharpe       = p.sharpe,
            max_drawdown = p.max_drawdown,
            decay_days   = d.decay_days,
            decay_level  = d.decay_level,
            trade_count  = p.trade_count,
            live_days    = getattr(s, "live_days", 0) if s else 0,
            sample_count = p.sample_count,
            force        = force,
        )

    def auto_screen_retirement(self):
        """
        批量筛查所有活跃策略的退役条件。

        Returns list[RetirementEvaluation]（should_retire=True）
        """
        data = []
        for s in self._registry.get_all():
            if self._retirement.is_retired(s.strategy_id):
                continue
            p = self._performance.get_state(s.strategy_id)
            d = self._decay.get_state(s.strategy_id)
            data.append({
                "strategy_id":  s.strategy_id,
                "sharpe":       p.sharpe,
                "max_drawdown": p.max_drawdown,
                "decay_days":   d.decay_days,
                "decay_level":  d.decay_level,
                "trade_count":  p.trade_count,
                "live_days":    getattr(s, "live_days", 0),
                "sample_count": p.sample_count,
            })
        return self._retirement.auto_screen(data)

    def execute_retirement(self, strategy_id, reason_str="manual", note=""):
        """
        执行退役（带绩效/衰减数据回填）。

        流程：
          1. 取当前 Performance / Decay 状态
          2. RetirementEngine.retire()
          3. 广播 EVENT_STRATEGY_RETIRED
        """
        state = self._registry.get(strategy_id)
        if state is None:
            return None
        try:
            reason = RetirementReason(reason_str)
        except ValueError:
            reason = RetirementReason.MANUAL
        p = self._performance.get_state(strategy_id)
        d = self._decay.get_state(strategy_id)
        record = self._retirement.retire(
            state            = state,
            reason           = reason,
            note             = note,
            sharpe_at_exit   = p.sharpe,
            drawdown_at_exit = p.max_drawdown,
            decay_days       = d.decay_days,
            trade_count      = p.trade_count,
        )
        self.dispatch_event(EVENT_STRATEGY_RETIRED, record.to_dict())
        return record

    def retire_strategy(self, strategy_id, reason_str="manual", note=""):
        """兼容旧接口 → execute_retirement。"""
        return self.execute_retirement(strategy_id, reason_str, note)

    def archive_strategy(self, strategy_id):
        """归档已退役策略（RETIRED → ARCHIVED）。"""
        state  = self._registry.get(strategy_id)
        record = self._retirement.archive(strategy_id, state)
        if record:
            self._log(f"[{APP_NAME}] archived: {strategy_id}")
        return record

    def restore_strategy(self, strategy_id):
        """从退役状态恢复策略（非归档策略）。"""
        state   = self._registry.get(strategy_id)
        success = self._retirement.restore(strategy_id, state)
        if success:
            self._log(f"[{APP_NAME}] restored: {strategy_id}")
        return success

    def auto_archive_old(self):
        """自动归档超期的已退役策略。"""
        states = {s.strategy_id: s for s in self._registry.get_all()}
        return self._retirement.auto_archive_old(states)

    # ── 全周期自动调度 ─────────────────────────────────────────────────

    def auto_cycle(self, pnl_map, params_map, trade_map=None,
                   auto_retire=True, auto_evolve=True):
        """
        全周期自动调度：track → decay → [evolve] → [retire]。

        流程（每 bar 调用一次）：
          1. track_performance()  更新绩效
          2. detect_decay()       检测衰减
          3. auto_evolve_decaying() 衰减中策略自动进化（可选）
          4. auto_screen_retirement() 筛查退役候选
          5. execute_retirement()  对满足条件策略执行退役（可选）
          6. auto_archive_old()   自动归档超期退役策略

        Parameters
        ----------
        pnl_map     : {strategy_id: pnl_series}
        params_map  : {strategy_id: params_dict}（进化用）
        trade_map   : {strategy_id: trade_count}
        auto_retire : 是否自动执行退役
        auto_evolve : 是否自动进化衰减策略

        Returns
        -------
        dict {
            "performance":   {sid: PerformanceState},
            "decay":         {sid: DecayState},
            "evolved":       {sid: EvolutionRecord},
            "retired":       [RetirementEvaluation],
            "archived":      [str],
        }
        """
        result = {
            "performance": {},
            "decay":       {},
            "evolved":     {},
            "retired":     [],
            "archived":    [],
        }

        # 1. 追踪绩效
        for sid, pnl in pnl_map.items():
            tc = (trade_map or {}).get(sid, 0)
            result["performance"][sid] = self.track_performance(sid, pnl, tc)

        # 2. 衰减检测
        for sid, pnl in pnl_map.items():
            result["decay"][sid] = self.detect_decay(sid, pnl)

        # 3. 自动进化（衰减策略）
        if auto_evolve:
            for sid, d_state in result["decay"].items():
                if d_state.decay_level.value in ("moderate", "severe", "critical"):
                    if not self._retirement.is_retired(sid):
                        rec = self.evolve_strategy(
                            sid, params_map.get(sid, {}),
                            trigger_reason="auto_cycle_decay")
                        result["evolved"][sid] = rec

        # 4. 筛查退役候选
        candidates = self.auto_screen_retirement()

        # 5. 执行退役
        for ev in candidates:
            if auto_retire:
                record = self.execute_retirement(
                    ev.strategy_id,
                    reason_str = ev.primary_reason.value,
                    note       = f"auto_cycle: {', '.join(ev.triggered_rules)}",
                )
                if record:
                    result["retired"].append(ev)
            else:
                result["retired"].append(ev)

        # 6. 自动归档
        result["archived"] = self.auto_archive_old()

        return result

    # ── 查询接口（Phase 1-5 完整）─────────────────────────────────────

    def get_strategy(self, sid):          return self._registry.get(sid)
    def get_all_strategies(self):         return self._registry.get_all()
    def get_strategies_by_phase(self, p): return self._registry.get_by_phase(p)

    def get_performance_state(self, sid):             return self._performance.get_state(sid)
    def get_performance_history(self, sid, limit=30): return self._performance.get_history(sid, limit)
    def get_performance_ranking(self, top_n=10):      return self._performance.get_ranking(top_n)
    def get_best_strategy(self):                      return self._performance.get_best()
    def get_worst_strategy(self):                     return self._performance.get_worst()
    def get_by_rating(self, rating):                  return self._performance.get_by_rating(rating)
    def get_rolling_sharpe(self, sid, w=60):          return self._performance.get_rolling_sharpe(sid, w)
    def get_rolling_drawdown(self, sid, w=60):        return self._performance.get_rolling_drawdown(sid, w)

    def get_decay_state(self, sid):             return self._decay.get_state(sid)
    def get_decay_history(self, sid, limit=30): return self._decay.get_history(sid, limit)
    def get_decay_score_series(self, sid):      return self._decay.get_score_series(sid)
    def get_decaying_strategies(self):          return self._decay.get_decaying()
    def get_critical_strategies(self):          return self._decay.get_critical()
    def get_severe_or_above(self):              return self._decay.get_severe_or_above()

    def get_evolution_history(self, sid, limit=20):  return self._evolution.get_history(sid, limit)
    def get_evolution_candidates(self, top_n=10):    return self._evolution.get_candidates(top_n)
    def get_strong_strategies(self, min_sharpe=2.0): return self._evolution.get_strong_strategies(min_sharpe)
    def get_evolution_success_rate(self, sid):       return self._evolution.get_success_rate(sid)
    def get_improvement_series(self, sid):           return self._evolution.get_improvement_series(sid)

    def get_retirement_history(self, limit=50):      return self._retirement.get_history(limit=limit)
    def get_retired_strategies(self):                return self._retirement.get_retired()
    def get_archived_strategies(self):               return self._retirement.get_archived()
    def get_retirement_evaluation(self, sid):        return self._retirement.get_evaluation(sid)
    def get_recent_evaluations(self, limit=20):      return self._retirement.get_recent_evaluations(limit)
    def is_retired(self, sid):                       return self._retirement.is_retired(sid)
    def is_archived(self, sid):                      return self._retirement.is_archived(sid)

    def get_logs(self, limit=200): return self._log_records[-limit:]

    # ── 事件 / 摘要 ──────────────────────────────────────────────────────

    def dispatch_event(self, event_type, data=None):
        self.event_engine.put(Event(event_type, data or {}))

    def get_summary(self):
        uptime = 0.0
        if self._started_at:
            uptime = round((datetime.now() - self._started_at).total_seconds(), 1)
        reg  = self._registry.summary()
        perf = self._performance.summary()
        dec  = self._decay.summary()
        evo  = self._evolution.summary()
        ret  = self._retirement.summary()
        return {
            "app":              APP_NAME,
            "phase":            5,
            "strategy_count":   reg["total"],
            "by_phase":         reg["by_phase"],
            "avg_sharpe":       perf["avg_sharpe"],
            "decaying_count":   dec["decaying"],
            "critical_count":   dec["critical"],
            "decay_by_level":   dec["by_level"],
            "total_evolutions": evo["total_evolutions"],
            "evo_success_rate": evo["success_rate"],
            "evo_candidates":   evo["candidates"],
            "retired_count":    ret["retired_count"],
            "archived_count":   ret["archived_count"],
            "retire_by_reason": ret["by_reason"],
            "quant_os":         self._strategy_loader.is_available(),
            "portfolio_engine": self._performance_loader.is_available(),
            "capital_ai":       self._portfolio_loader.is_available(),
            "uptime":           uptime,
        }

    def _log(self, msg):
        ts = str(datetime.now())[:19]
        self._log_records.append(ts + "  " + msg)
        try:
            self.write_log(msg)
        except Exception:
            pass
