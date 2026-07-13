"""
strategy_lifecycle_ai/engine/retirement_engine.py  (Phase 5)

RetirementEngine — 策略退役引擎（完整实现）。

退役触发规则（满足任意一条）：
  1. PERSISTENT_DECAY : decay_days >= critical_days AND level in (SEVERE, CRITICAL)
  2. NEGATIVE_SHARPE  : sharpe < threshold AND sample_count >= min_samples
  3. DRAWDOWN_BREACH  : max_drawdown >= drawdown_limit
  4. LOW_ACTIVITY     : live_days >= inactive_days AND trade_count == 0
  5. MANUAL           : 手动触发
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from ..constant import RetirementReason, StrategyPhase, DecayLevel
from ..model.strategy_model import StrategyState


@dataclass
class RetirementEvaluation:
    """退役条件评估结果。"""
    strategy_id:      str
    should_retire:    bool             = False
    triggered_rules:  list[str]        = field(default_factory=list)
    primary_reason:   RetirementReason = RetirementReason.MANUAL
    sharpe:           float            = 0.0
    max_drawdown:     float            = 0.0
    decay_days:       int              = 0
    decay_level:      str              = "none"
    trade_count:      int              = 0
    live_days:        int              = 0
    evaluated_at:     datetime         = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "strategy_id":     self.strategy_id,
            "should_retire":   self.should_retire,
            "triggered_rules": self.triggered_rules,
            "primary_reason":  self.primary_reason.value,
            "sharpe":          round(self.sharpe,       4),
            "max_drawdown":    round(self.max_drawdown, 4),
            "decay_days":      self.decay_days,
            "decay_level":     self.decay_level,
            "trade_count":     self.trade_count,
            "live_days":       self.live_days,
            "evaluated_at":    str(self.evaluated_at)[:19],
        }


@dataclass
class RetirementRecord:
    """单次退役记录。"""
    strategy_id:      str
    strategy_name:    str              = ""
    reason:           RetirementReason = RetirementReason.MANUAL
    note:             str              = ""
    sharpe_at_exit:   float            = 0.0
    drawdown_at_exit: float            = 0.0
    decay_days:       int              = 0
    live_days:        int              = 0
    trade_count:      int              = 0
    archived:         bool             = False
    retired_at:       datetime         = field(default_factory=datetime.now)
    archived_at:      datetime | None  = None
    meta:             dict             = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "strategy_id":      self.strategy_id,
            "strategy_name":    self.strategy_name,
            "reason":           self.reason.value,
            "note":             self.note,
            "sharpe_at_exit":   round(self.sharpe_at_exit,   4),
            "drawdown_at_exit": round(self.drawdown_at_exit, 4),
            "decay_days":       self.decay_days,
            "live_days":        self.live_days,
            "trade_count":      self.trade_count,
            "archived":         self.archived,
            "retired_at":       str(self.retired_at)[:19],
            "archived_at":      str(self.archived_at)[:19] if self.archived_at else "",
        }


class RetirementEngine:
    """策略退役引擎（Phase 5 完整实现）。"""

    def __init__(
        self,
        log_fn=None,
        critical_days=10,
        negative_sharpe_threshold=-0.3,
        drawdown_limit=0.35,
        inactive_days=30,
        min_samples=20,
        auto_archive_days=7,
    ):
        self._log = log_fn or (lambda m: None)
        self._critical_days = critical_days
        self._negative_sharpe_threshold = negative_sharpe_threshold
        self._drawdown_limit = drawdown_limit
        self._inactive_days = inactive_days
        self._min_samples = min_samples
        self._auto_archive_days = auto_archive_days
        self._records = []
        self._by_id   = {}
        self._evals   = {}

    def evaluate(self, strategy_id, sharpe, max_drawdown, decay_days,
                 decay_level, trade_count, live_days, sample_count, force=False):
        """退役条件自动评估，返回 RetirementEvaluation。"""
        rules = []
        primary = RetirementReason.MANUAL

        if force:
            rules.append("manual_force")
        else:
            # Rule 1: 持续严重衰减
            if (decay_days >= self._critical_days and
                    decay_level in (DecayLevel.SEVERE, DecayLevel.CRITICAL)):
                rules.append(
                    f"persistent_decay(days={decay_days},level={decay_level.value})")
                primary = RetirementReason.PERSISTENT_DECAY

            # Rule 2: 持续负 Sharpe
            if (sharpe < self._negative_sharpe_threshold and
                    sample_count >= self._min_samples):
                rules.append(
                    f"negative_sharpe(sharpe={sharpe:.3f})")
                if primary == RetirementReason.MANUAL:
                    primary = RetirementReason.NEGATIVE_SHARPE

            # Rule 3: 回撤超限
            if max_drawdown >= self._drawdown_limit:
                rules.append(
                    f"drawdown_breach(dd={max_drawdown:.3f})")
                if primary == RetirementReason.MANUAL:
                    primary = RetirementReason.DRAWDOWN_BREACH

            # Rule 4: 长期无交易
            if live_days >= self._inactive_days and trade_count == 0:
                rules.append(
                    f"low_activity(days={live_days})")
                if primary == RetirementReason.MANUAL:
                    primary = RetirementReason.LOW_ACTIVITY

        result = RetirementEvaluation(
            strategy_id    = strategy_id,
            should_retire  = len(rules) > 0,
            triggered_rules = rules,
            primary_reason = primary,
            sharpe         = sharpe,
            max_drawdown   = max_drawdown,
            decay_days     = decay_days,
            decay_level    = decay_level.value if hasattr(decay_level, "value") else str(decay_level),
            trade_count    = trade_count,
            live_days      = live_days,
            evaluated_at   = datetime.now(),
        )
        self._evals[strategy_id] = result
        return result

    def retire(self, state, reason=RetirementReason.MANUAL, note="",
               sharpe_at_exit=0.0, drawdown_at_exit=0.0,
               decay_days=0, trade_count=0):
        """执行退役，返回 RetirementRecord。"""
        if state.strategy_id in self._by_id:
            return self._by_id[state.strategy_id]
        record = RetirementRecord(
            strategy_id      = state.strategy_id,
            strategy_name    = state.strategy_name,
            reason           = reason,
            note             = note,
            sharpe_at_exit   = sharpe_at_exit,
            drawdown_at_exit = drawdown_at_exit,
            decay_days       = decay_days,
            live_days        = getattr(state, "live_days", 0),
            trade_count      = trade_count,
            retired_at       = datetime.now(),
        )
        state.phase      = StrategyPhase.RETIRED
        state.updated_at = datetime.now()
        self._records.append(record)
        self._by_id[state.strategy_id] = record
        self._log(
            f"[RetirementEngine] RETIRED {state.strategy_id}"
            f"  reason={reason.value}  sharpe={sharpe_at_exit:.3f}"
        )
        return record

    def archive(self, strategy_id, state=None):
        """归档已退役策略（RETIRED → ARCHIVED）。"""
        record = self._by_id.get(strategy_id)
        if record is None or record.archived:
            return record
        record.archived    = True
        record.archived_at = datetime.now()
        if state is not None:
            state.phase      = StrategyPhase.ARCHIVED
            state.updated_at = datetime.now()
        self._log(f"[RetirementEngine] ARCHIVED {strategy_id}")
        return record

    def auto_archive_old(self, states):
        """自动归档超过 auto_archive_days 天的已退役策略。"""
        archived_ids = []
        now = datetime.now()
        for record in self._records:
            if record.archived:
                continue
            if (now - record.retired_at).days >= self._auto_archive_days:
                state = states.get(record.strategy_id)
                self.archive(record.strategy_id, state)
                archived_ids.append(record.strategy_id)
        return archived_ids

    def auto_screen(self, strategy_data):
        """批量筛查退役候选，返回 should_retire=True 的评估列表。"""
        candidates = []
        for d in strategy_data:
            sid = d.get("strategy_id", "")
            if sid in self._by_id:
                continue
            dl = d.get("decay_level", DecayLevel.NONE)
            if isinstance(dl, str):
                try:   dl = DecayLevel(dl)
                except ValueError: dl = DecayLevel.NONE
            ev = self.evaluate(
                strategy_id  = sid,
                sharpe       = d.get("sharpe",       0.0),
                max_drawdown = d.get("max_drawdown",  0.0),
                decay_days   = d.get("decay_days",    0),
                decay_level  = dl,
                trade_count  = d.get("trade_count",   0),
                live_days    = d.get("live_days",     0),
                sample_count = d.get("sample_count",  0),
            )
            if ev.should_retire:
                candidates.append(ev)
        return candidates

    def restore(self, strategy_id, state=None):
        """从退役状态恢复（仅非归档策略）。"""
        record = self._by_id.get(strategy_id)
        if record is None or record.archived:
            return False
        del self._by_id[strategy_id]
        self._records = [r for r in self._records
                         if r.strategy_id != strategy_id]
        if state is not None:
            state.phase      = StrategyPhase.RECOVERING
            state.updated_at = datetime.now()
        self._log(f"[RetirementEngine] RESTORED {strategy_id}")
        return True

    def is_retired(self, sid):    return sid in self._by_id
    def is_archived(self, sid):   r = self._by_id.get(sid); return r is not None and r.archived
    def get_record(self, sid):    return self._by_id.get(sid)
    def get_retired(self):        return [r for r in self._records if not r.archived]
    def get_archived(self):       return [r for r in self._records if r.archived]
    def get_evaluation(self, sid): return self._evals.get(sid)

    def get_history(self, limit=50):
        return [r.to_dict() for r in self._records[-limit:]]

    def get_recent_evaluations(self, limit=20):
        evals = sorted(self._evals.values(), key=lambda e: e.evaluated_at, reverse=True)
        return [e.to_dict() for e in evals[:limit]]

    def count(self): return len(self._records)

    def count_by_reason(self):
        result = {}
        for r in self._records:
            result[r.reason.value] = result.get(r.reason.value, 0) + 1
        return result

    def update_params(self, **kwargs):
        for k, v in kwargs.items():
            attr = f"_{k}"
            if hasattr(self, attr):
                setattr(self, attr, v)

    def summary(self):
        return {
            "retired_count":  len(self.get_retired()),
            "archived_count": len(self.get_archived()),
            "total":          self.count(),
            "by_reason":      self.count_by_reason(),
            "phase":          5,
        }
