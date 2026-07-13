"""
global_portfolio_intelligence/engine/rebalance_engine.py  (Phase 5)

RebalanceEngine — 再平衡决策引擎。

触发条件：
  1. risk_drift          — 风险漂移超过阈值
  2. alpha_decay         — Alpha 质量快速衰减
  3. execution_inefficiency — 执行效率低下
  4. regime_shift        — 市场状态切换
  5. scheduled           — 定期再平衡
  6. manual              — 手动触发

流程：
  detect_imbalance() → compute_adjustments() → apply_rebalancing()
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable
import uuid

from ..constant import RebalanceTrigger
from ..model.rebalance_model import (
    RebalanceTriggerEvent, RebalanceAdjustment, RebalanceState)


# 默认触发阈值
DEFAULT_THRESHOLDS = {
    "risk_drift":           0.05,    # 风险漂移 > 5% 触发
    "alpha_decay":          0.15,    # Alpha 衰减 > 15% 触发
    "exec_inefficiency":    0.20,    # 执行效率低于 80% 触发
    "regime_shift_prob":    0.60,    # 市场转换概率 > 60% 触发
}


class RebalanceEngine:
    """再平衡决策引擎（Phase 5 完整实现）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log        = log_fn or (lambda m: None)
        self._thresholds = dict(DEFAULT_THRESHOLDS)
        self._state      = RebalanceState()
        self._history:   list[RebalanceState] = []

    def init(self)  -> None: self._log("[RebalanceEngine] init()")
    def start(self) -> None: self._log("[RebalanceEngine] start()")
    def stop(self)  -> None: self._log("[RebalanceEngine] stop()")

    def set_threshold(self, key: str, value: float) -> None:
        self._thresholds[key] = value

    # ── main pipeline ────────────────────────────────────────────────
    def detect_and_rebalance(self, metrics: dict) -> RebalanceState:
        """
        完整再平衡流程：检测失衡 → 计算调整 → 更新状态。

        metrics 字典：
          risk_drift          float  当前风险漂移量 [0,1]
          alpha_decay_rate    float  Alpha 衰减速率 [0,1]
          exec_inefficiency   float  执行低效程度  [0,1]
          regime_shift_prob   float  市场切换概率  [0,1]
          strategy_weights    dict   {id: current_weight}
          target_weights      dict   {id: target_weight}
          alpha_scores        dict   {id: score}
          exec_scores         dict   {id: efficiency [0,1]}
        """
        triggers    = self._detect_triggers(metrics)
        adjustments = self._compute_adjustments(metrics, triggers)

        hp = sum(1 for a in adjustments if a.priority == 1)
        mp = sum(1 for a in adjustments if a.priority == 2)
        lp = sum(1 for a in adjustments if a.priority == 3)

        # 系统健康度 = 100 - 失衡惩罚
        imbalance = self._imbalance_score(metrics)
        health    = max(0.0, 100.0 - imbalance)

        self._state = RebalanceState(
            active_triggers   = triggers,
            trigger_count     = len(triggers),
            adjustments       = adjustments,
            n_high_priority   = hp,
            n_mid_priority    = mp,
            n_low_priority    = lp,
            system_health     = round(health,   2),
            imbalance_score   = round(imbalance, 2),
            risk_drift        = float(metrics.get("risk_drift",        0.0)),
            alpha_decay_rate  = float(metrics.get("alpha_decay_rate",  0.0)),
            exec_inefficiency = float(metrics.get("exec_inefficiency", 0.0)),
            regime_shift_prob = float(metrics.get("regime_shift_prob", 0.0)),
            updated_at        = datetime.now(),
            rebalance_count   = self._state.rebalance_count + 1,
        )
        self._history.append(self._state)

        self._log(
            f"[RebalanceEngine] rebalance #{self._state.rebalance_count}: "
            f"triggers={len(triggers)} adj={len(adjustments)} "
            f"health={health:.1f} imbalance={imbalance:.1f}"
        )
        return self._state

    def manual_rebalance(self, reason: str = "manual") -> RebalanceState:
        """手动触发再平衡。"""
        trigger = RebalanceTriggerEvent(
            trigger_id   = f"TRIG_{uuid.uuid4().hex[:6].upper()}",
            trigger_type = RebalanceTrigger.MANUAL,
            severity     = 0.5,
            description  = reason,
            metric_name  = "manual",
            metric_value = 1.0,
            threshold    = 0.0,
        )
        self._state = RebalanceState(
            active_triggers  = [trigger],
            trigger_count    = 1,
            adjustments      = [],
            system_health    = self._state.system_health,
            imbalance_score  = self._state.imbalance_score,
            updated_at       = datetime.now(),
            rebalance_count  = self._state.rebalance_count + 1,
        )
        self._history.append(self._state)
        self._log(f"[RebalanceEngine] manual rebalance: {reason}")
        return self._state

    def scheduled_rebalance(self) -> RebalanceState:
        """定时再平衡（传入空 metrics 使用默认值）。"""
        return self.detect_and_rebalance({})

    # ── detection ────────────────────────────────────────────────────
    def _detect_triggers(self, metrics: dict) -> list[RebalanceTriggerEvent]:
        triggers = []
        checks = [
            ("risk_drift",        RebalanceTrigger.RISK_DRIFT,
             "Risk drift exceeds threshold"),
            ("alpha_decay_rate",  RebalanceTrigger.ALPHA_DECAY,
             "Alpha quality decaying rapidly"),
            ("exec_inefficiency", RebalanceTrigger.EXECUTION_INEFFICIENCY,
             "Execution efficiency below threshold"),
            ("regime_shift_prob", RebalanceTrigger.REGIME_SHIFT,
             "Market regime shift detected"),
        ]
        for key, trig_type, desc in checks:
            val       = float(metrics.get(key, 0.0))
            threshold = self._thresholds.get(
                key.replace("_rate", "").replace("_prob", ""), 0.3)
            # map key names
            thresh_map = {
                "risk_drift":        "risk_drift",
                "alpha_decay_rate":  "alpha_decay",
                "exec_inefficiency": "exec_inefficiency",
                "regime_shift_prob": "regime_shift_prob",
            }
            threshold = self._thresholds.get(thresh_map.get(key, key), 0.3)

            if val > threshold:
                severity = min((val - threshold) / max(threshold, 1e-9), 1.0)
                triggers.append(RebalanceTriggerEvent(
                    trigger_id   = f"TRIG_{uuid.uuid4().hex[:6].upper()}",
                    trigger_type = trig_type,
                    severity     = round(severity, 4),
                    description  = f"{desc} ({val:.3f} > {threshold:.3f})",
                    metric_name  = key,
                    metric_value = val,
                    threshold    = threshold,
                ))
        return triggers

    # ── adjustment computation ────────────────────────────────────────
    def _compute_adjustments(
        self,
        metrics:  dict,
        triggers: list[RebalanceTriggerEvent],
    ) -> list[RebalanceAdjustment]:
        adjustments = []
        trigger_types = {t.trigger_type for t in triggers}

        # 1. Risk drift → adjust strategy weights toward target
        if RebalanceTrigger.RISK_DRIFT in trigger_types:
            sw = metrics.get("strategy_weights", {})
            tw = metrics.get("target_weights",   {})
            for eid in set(list(sw.keys()) + list(tw.keys())):
                cur    = sw.get(eid, 0.0)
                target = tw.get(eid, cur)
                delta  = target - cur
                if abs(delta) > 0.01:
                    adjustments.append(RebalanceAdjustment(
                        entity_id     = eid,
                        entity_type   = "strategy",
                        dimension     = "weight",
                        current_value = cur,
                        target_value  = target,
                        delta         = round(delta, 6),
                        priority      = 1,
                        reason        = "risk drift correction",
                    ))

        # 2. Alpha decay → reduce weight of low-scoring alphas
        if RebalanceTrigger.ALPHA_DECAY in trigger_types:
            alpha_scores = metrics.get("alpha_scores", {})
            for aid, score in alpha_scores.items():
                if score < 50.0:
                    cur    = 1.0 / max(len(alpha_scores), 1)
                    target = cur * (score / 50.0)
                    adjustments.append(RebalanceAdjustment(
                        entity_id     = aid,
                        entity_type   = "alpha",
                        dimension     = "alpha",
                        current_value = cur,
                        target_value  = round(target, 6),
                        delta         = round(target - cur, 6),
                        priority      = 1,
                        reason        = f"alpha decay: score={score:.1f}",
                    ))

        # 3. Execution inefficiency → reduce execution intensity
        if RebalanceTrigger.EXECUTION_INEFFICIENCY in trigger_types:
            exec_scores = metrics.get("exec_scores", {})
            for sid, eff in exec_scores.items():
                if eff < 0.8:
                    adjustments.append(RebalanceAdjustment(
                        entity_id     = sid,
                        entity_type   = "strategy",
                        dimension     = "execution",
                        current_value = eff,
                        target_value  = min(eff * 1.2, 1.0),
                        delta         = round(min(eff * 0.2, 0.2), 6),
                        priority      = 2,
                        reason        = f"low exec efficiency: {eff:.2f}",
                    ))

        # 4. Regime shift → adjust capital distribution
        if RebalanceTrigger.REGIME_SHIFT in trigger_types:
            regime_prob = float(metrics.get("regime_shift_prob", 0.0))
            adjustments.append(RebalanceAdjustment(
                entity_id     = "SYSTEM",
                entity_type   = "global",
                dimension     = "capital",
                current_value = regime_prob,
                target_value  = 0.0,
                delta         = round(-regime_prob, 6),
                priority      = 1,
                reason        = f"regime shift: p={regime_prob:.2f}",
            ))

        # Sort by priority
        adjustments.sort(key=lambda a: a.priority)
        return adjustments

    # ── imbalance score ───────────────────────────────────────────────
    def _imbalance_score(self, metrics: dict) -> float:
        """
        综合失衡评分 [0, 100]。
        各维度失衡加权求和。
        """
        weights = {
            "risk_drift":        30.0,
            "alpha_decay_rate":  25.0,
            "exec_inefficiency": 25.0,
            "regime_shift_prob": 20.0,
        }
        thresholds = {
            "risk_drift":        self._thresholds["risk_drift"],
            "alpha_decay_rate":  self._thresholds["alpha_decay"],
            "exec_inefficiency": self._thresholds["exec_inefficiency"],
            "regime_shift_prob": self._thresholds["regime_shift_prob"],
        }
        score = 0.0
        for key, w in weights.items():
            val       = float(metrics.get(key, 0.0))
            threshold = thresholds[key]
            excess    = max(0.0, val - threshold)
            norm      = min(excess / max(threshold, 1e-9), 1.0)
            score    += w * norm
        return round(score, 2)

    # ── query ────────────────────────────────────────────────────────
    def get_state(self) -> RebalanceState:
        return self._state

    def get_history(self, n: int = 20) -> list[RebalanceState]:
        return self._history[-n:]

    def summary(self) -> dict:
        return {
            "phase":           5,
            "status":          "active",
            "rebalance_count": self._state.rebalance_count,
            "system_health":   round(self._state.system_health,   2),
            "imbalance_score": round(self._state.imbalance_score, 2),
            "active_triggers": self._state.trigger_count,
            "n_adjustments":   len(self._state.adjustments),
            "thresholds":      {k: round(v, 4)
                                for k, v in self._thresholds.items()},
        }
