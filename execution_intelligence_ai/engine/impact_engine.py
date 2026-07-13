"""
execution_intelligence_ai/engine/impact_engine.py  (Phase 3)

ImpactEngine — 市场冲击模型引擎。

功能：
  - estimate_impact()   : 估算订单的市场冲击（三种模型可选）
  - record_realized()   : 记录实现冲击，触发 EWA 修正
  - get_impact_curve()  : 生成冲击曲线数据（UI 绘图用）
  - calibrate()         : 基于历史记录校准 coeff / eta / gamma
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable

from ..constant import ImpactLevel
from ..model.impact_model import (
    ImpactParams, ImpactState, ImpactRecord, ImpactHistory)
from ..utils.impact_utils import (
    linear_impact, sqrt_impact, almgren_chriss_impact,
    calc_liquidity_score, classify_impact_level,
    adjust_impact_estimate, impact_curve,
)


class ImpactEngine:
    """
    市场冲击模型引擎（Phase 3 完整实现）。

    设计原则：
      - 不依赖外部数据源，所有输入来自调用方（Market/Portfolio 传入）
      - 支持三种模型：linear / sqrt / almgren_chriss
      - 每次执行后可回填实现冲击，触发 EWA 系数修正
      - 历史记录用于模型校准（RMSE 追踪）
    """

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log     = log_fn or (lambda m: None)
        self._params  = ImpactParams()
        self._states: dict[str, ImpactState] = {}
        self._history = ImpactHistory()

    def init(self) -> None:
        self._log("[ImpactEngine] init()")

    def start(self) -> None:
        self._log("[ImpactEngine] start()")

    def stop(self) -> None:
        self._log("[ImpactEngine] stop()")

    # ------------------------------------------------------------------ #
    #  参数配置
    # ------------------------------------------------------------------ #

    def set_params(self, params: ImpactParams) -> None:
        self._params = params
        self._log(f"[ImpactEngine] params updated: model={params.model} "
                  f"eta={params.eta} gamma={params.gamma}")

    def get_params(self) -> ImpactParams:
        return self._params

    # ------------------------------------------------------------------ #
    #  核心：估算冲击
    # ------------------------------------------------------------------ #

    def estimate_impact(
        self,
        execution_id: str,
        symbol:       str,
        order_size:   float,
        volatility:   float,
        adv:          float     | None = None,
        spread_bps:   float     | None = None,
        model:        str       | None = None,
    ) -> ImpactState:
        """
        估算订单的市场冲击。

        参数说明：
          order_size : 订单数量（股/手）
          volatility : 日收益率标准差（如 0.02 = 2%）
          adv        : 日均成交量（不传则用 ImpactParams.adv）
          spread_bps : 买卖价差基点（不传则用 ImpactParams.spread_bps）
          model      : 覆盖 ImpactParams.model

        Returns ImpactState，同时缓存到 self._states。
        """
        adv_val      = adv        if adv        is not None else self._params.adv
        spread_val   = spread_bps if spread_bps is not None else self._params.spread_bps
        model_choice = model      if model      is not None else self._params.model

        if adv_val <= 0:
            adv_val = max(order_size * 10, 1.0)   # 保底：订单量的10倍

        ratio = round(order_size / adv_val, 6)

        # ── 选择冲击模型 ──────────────────────────────────────────────
        if model_choice == "linear":
            total_bp = linear_impact(
                order_size, adv_val, volatility, self._params.coeff)
            temp_bp  = total_bp
            perm_bp  = 0.0
            t_ratio  = 1.0

        elif model_choice == "almgren_chriss":
            ac = almgren_chriss_impact(
                order_size, adv_val, volatility,
                self._params.eta, self._params.gamma)
            total_bp = ac["total_bp"]
            temp_bp  = ac["temporary_bp"]
            perm_bp  = ac["permanent_bp"]
            t_ratio  = ac["ratio"]

        else:  # sqrt（默认，行业标准）
            total_bp = sqrt_impact(
                order_size, adv_val, volatility, self._params.coeff)
            temp_bp  = total_bp
            perm_bp  = 0.0
            t_ratio  = 1.0

        # ── 流动性评分 ─────────────────────────────────────────────────
        liq = calc_liquidity_score(
            adv_val, spread_val, order_size)

        # ── 流动性折扣（低流动性时冲击放大）─────────────────────────────
        if liq < 0.3:
            amplifier = 1.0 + (0.3 - liq) * 3.0   # 最多放大 1.9×
            total_bp  = round(total_bp * amplifier, 4)
            temp_bp   = round(temp_bp  * amplifier, 4)
            perm_bp   = round(perm_bp  * amplifier, 4)

        # ── 冲击等级 ───────────────────────────────────────────────────
        level_str = classify_impact_level(total_bp)
        level     = ImpactLevel(level_str)

        state = ImpactState(
            execution_id     = execution_id,
            symbol           = symbol,
            order_size       = order_size,
            adv              = adv_val,
            volatility       = volatility,
            order_size_ratio = ratio,
            estimated_bp     = total_bp,
            temporary_bp     = temp_bp,
            permanent_bp     = perm_bp,
            temp_ratio       = t_ratio,
            adjusted_bp      = total_bp,    # 初始等于估算值
            liquidity_score  = liq,
            spread_bps       = spread_val,
            impact_level     = level,
            model            = model_choice,
            estimated_at     = datetime.now(),
        )
        self._states[execution_id] = state

        self._log(
            f"[ImpactEngine] estimate: {execution_id} {symbol} "
            f"model={model_choice} size={order_size:.0f} "
            f"impact={total_bp:.2f}bp level={level_str} liq={liq:.3f}"
        )
        return state

    # ------------------------------------------------------------------ #
    #  实时修正：回填实现冲击
    # ------------------------------------------------------------------ #

    def record_realized(
        self,
        execution_id: str,
        realized_bp:  float,
    ) -> ImpactState | None:
        """
        执行完成后回填实现冲击，触发 EWA 系数修正。

        EWA：adjusted = (1-alpha)*estimated + alpha*realized
        同时将记录写入历史，供 calibrate() 使用。
        """
        state = self._states.get(execution_id)
        if state is None:
            self._log(f"[ImpactEngine] WARN: record_realized: "
                      f"{execution_id} not found")
            return None

        state.realized_bp   = realized_bp
        state.adjusted_bp   = adjust_impact_estimate(
            state.estimated_bp, realized_bp, self._params.alpha)
        state.realized_at   = datetime.now()

        # 更新冲击等级为实现值
        state.impact_level  = ImpactLevel(
            classify_impact_level(realized_bp))

        # 写入历史
        rec = ImpactRecord(
            execution_id = execution_id,
            symbol       = state.symbol,
            order_size   = state.order_size,
            adv          = state.adv,
            volatility   = state.volatility,
            estimated_bp = state.estimated_bp,
            realized_bp  = realized_bp,
            error_bp     = round(realized_bp - state.estimated_bp, 4),
        )
        self._history.add(rec)

        self._log(
            f"[ImpactEngine] realized: {execution_id} "
            f"est={state.estimated_bp:.2f}bp "
            f"real={realized_bp:.2f}bp "
            f"adjusted={state.adjusted_bp:.2f}bp "
            f"error={rec.error_bp:+.2f}bp"
        )
        return state

    # ------------------------------------------------------------------ #
    #  冲击曲线（UI 绘图数据）
    # ------------------------------------------------------------------ #

    def get_impact_curve(
        self,
        adv:        float,
        volatility: float,
        model:      str   | None = None,
        n_points:   int   = 20,
        max_ratio:  float = 0.5,
    ) -> list[dict]:
        """
        生成冲击曲线 — 不同订单量对应的冲击基点。

        Returns [{"ratio": ..., "impact_bp": ...}, ...]
        用于 UI 折线图（x轴=订单量/ADV，y轴=冲击bp）。
        """
        m = model if model is not None else self._params.model
        return impact_curve(
            adv        = adv,
            volatility = volatility,
            model      = m,
            n_points   = n_points,
            max_ratio  = max_ratio,
            eta        = self._params.eta,
            gamma      = self._params.gamma,
        )

    def get_multi_model_curves(
        self,
        adv:       float,
        volatility: float,
        n_points:  int   = 20,
        max_ratio: float = 0.5,
    ) -> dict[str, list[dict]]:
        """
        同时返回三种模型的曲线（UI 对比图用）。
        """
        return {
            "linear":          self.get_impact_curve(adv, volatility, "linear",          n_points, max_ratio),
            "sqrt":            self.get_impact_curve(adv, volatility, "sqrt",             n_points, max_ratio),
            "almgren_chriss":  self.get_impact_curve(adv, volatility, "almgren_chriss",  n_points, max_ratio),
        }

    # ------------------------------------------------------------------ #
    #  模型校准
    # ------------------------------------------------------------------ #

    def calibrate(self, min_records: int = 10) -> dict:
        """
        基于历史记录估算系数偏差，返回校准建议。

        简单校准：若平均估算误差 > 5bp，建议调整 coeff。
        Phase 5 可替换为最小二乘回归。
        """
        n = len(self._history.records)
        if n < min_records:
            return {"status": "insufficient_data",
                    "records": n, "required": min_records}

        mean_err  = self._history.mean_error_bp()
        rmse      = self._history.rmse_bp()
        # 简单线性建议：如果平均低估，增大 coeff
        suggestion = round(
            self._params.coeff * (1 + mean_err / 10), 4) if mean_err > 0 else self._params.coeff

        result = {
            "status":             "ok",
            "records":            n,
            "mean_error_bp":      mean_err,
            "rmse_bp":            rmse,
            "current_coeff":      self._params.coeff,
            "suggested_coeff":    suggestion,
        }
        self._log(f"[ImpactEngine] calibrate: {result}")
        return result

    # ------------------------------------------------------------------ #
    #  查询
    # ------------------------------------------------------------------ #

    def get_state(self, execution_id: str) -> ImpactState | None:
        return self._states.get(execution_id)

    def get_all_states(self) -> list[ImpactState]:
        return list(self._states.values())

    def get_history(self) -> ImpactHistory:
        return self._history

    def summary(self) -> dict:
        n = len(self._states)
        severe = sum(1 for s in self._states.values()
                     if s.impact_level == ImpactLevel.SEVERE)
        return {
            "phase":          3,
            "status":         "active",
            "model":          self._params.model,
            "total_estimated": n,
            "severe_count":   severe,
            "history_count":  len(self._history.records),
            "mean_error_bp":  self._history.mean_error_bp(),
            "rmse_bp":        self._history.rmse_bp(),
        }
