"""
risk_engine_2/engine/exposure_engine.py

ExposureEngine — 持仓快照维护 + 风险暴露计算（Phase 2）。

职责：
  - 接收 Execution Engine 的成交回报，实时维护 PortfolioSnapshot
  - 计算组合 Beta / 杠杆 / 单票集中度 / 行业集中度
  - 输出 ExposureReport，供 LimitEngine 校验
"""

from __future__ import annotations

from datetime import datetime

from ..model.exposure_model import (
    PortfolioSnapshot,
    PositionSnapshot,
    ExposureReport,
)
from ..utils.math_utils import (
    safe_div,
    calc_leverage,
    calc_portfolio_beta,
    calc_concentration,
    calc_industry_weights,
)


class ExposureEngine:
    """
    持仓暴露引擎（无状态计算 + 有状态快照维护）。

    使用方式：
        engine = ExposureEngine()
        engine.set_nav(1_000_000.0)
        engine.on_fill(fill_data)
        report = engine.compute_report()
    """

    def __init__(self) -> None:
        self._snapshot  = PortfolioSnapshot()
        self._nav:       float = 0.0

        # 行业映射（symbol → industry），由外部注入或 Phase 2 后从 DB 加载
        self._symbol_industry: dict[str, str] = {}

        # Beta 映射（symbol → beta），由外部注入
        self._symbol_betas: dict[str, float] = {}

    # ------------------------------------------------------------------ #
    #  外部注入
    # ------------------------------------------------------------------ #

    def set_nav(self, nav: float) -> None:
        """设置组合净值（来自 Portfolio Engine）。"""
        if nav >= 0:
            self._nav = nav
            self._snapshot.nav = nav

    def set_symbol_industry(self, mapping: dict[str, str]) -> None:
        """注入行业分类映射 {symbol: industry}。"""
        self._symbol_industry.update(mapping)

    def set_symbol_betas(self, mapping: dict[str, float]) -> None:
        """注入 Beta 映射 {symbol: beta}。"""
        self._symbol_betas.update(mapping)

    def set_symbol_beta(self, symbol: str, beta: float) -> None:
        """设置单标的 Beta。"""
        self._symbol_betas[symbol] = beta

    # ------------------------------------------------------------------ #
    #  成交回报处理（来自 Execution Engine EVENT_FILL_UPDATE）
    # ------------------------------------------------------------------ #

    def on_fill(self, fill: dict) -> None:
        """
        处理成交回报，更新持仓快照。

        fill 格式：
        {
          "symbol":     str,
          "direction":  "LONG" | "SHORT",
          "volume":     float,
          "price":      float,
          "multiplier": float  (optional, default=1.0)
        }
        """
        symbol     = str(fill.get("symbol", ""))
        direction  = str(fill.get("direction", "LONG"))
        volume     = float(fill.get("volume", 0.0))
        price      = float(fill.get("price", 0.0))
        multiplier = float(fill.get("multiplier", 1.0))

        if not symbol or volume <= 0 or price <= 0:
            return

        pos = self._snapshot.positions.get(symbol)
        if pos is None:
            pos = PositionSnapshot(
                symbol     = symbol,
                industry   = self._symbol_industry.get(symbol, "其他"),
                beta       = self._symbol_betas.get(symbol, 1.0),
                multiplier = multiplier,
            )

        # 更新数量和均价
        signed_vol = volume if direction == "LONG" else -volume
        old_vol    = pos.volume
        new_vol    = old_vol + signed_vol

        if abs(new_vol) < 1e-9:
            # 平仓
            self._snapshot.remove_position(symbol)
            return

        # 加权均价
        if (old_vol >= 0 and signed_vol > 0) or (old_vol <= 0 and signed_vol < 0):
            # 同向加仓
            total_cost = abs(old_vol) * pos.avg_price + volume * price
            pos.avg_price = safe_div(total_cost, abs(new_vol), price)
        else:
            # 反向减仓：均价不变
            pass

        pos.volume      = new_vol
        pos.last_price  = price
        pos.market_value = new_vol * price * multiplier
        pos.updated_at  = datetime.now()

        self._snapshot.upsert_position(pos)

    def on_price_update(self, symbol: str, last_price: float) -> None:
        """更新最新价格（来自行情事件）。"""
        pos = self._snapshot.positions.get(symbol)
        if pos is not None:
            pos.update_price(last_price)

    # ------------------------------------------------------------------ #
    #  暴露计算（核心）
    # ------------------------------------------------------------------ #

    def compute_report(self) -> ExposureReport:
        """
        计算当前组合的完整风险暴露报告。

        Returns
        -------
        ExposureReport  含杠杆 / Beta / 集中度 / 行业分布
        """
        positions = self._snapshot.positions
        nav       = self._nav

        if not positions:
            return ExposureReport(nav=nav, computed_at=datetime.now())

        # 各标的名义价值和权重
        long_notional  = 0.0
        short_notional = 0.0
        symbol_weights: dict[str, float] = {}

        for sym, pos in positions.items():
            notional = pos.notional
            if pos.volume > 0:
                long_notional  += notional
            else:
                short_notional += notional

            w = safe_div(pos.market_value, nav, 0.0)
            symbol_weights[sym] = w

        gross_notional = long_notional + short_notional
        net_notional   = long_notional - short_notional
        leverage       = calc_leverage(gross_notional, nav)

        # Beta
        portfolio_beta = calc_portfolio_beta(symbol_weights, self._symbol_betas)

        # 单票集中度
        max_w, max_sym = calc_concentration(symbol_weights)

        # 行业集中度
        ind_weights = calc_industry_weights(symbol_weights, self._symbol_industry)
        max_ind_w, max_ind = (0.0, "")
        if ind_weights:
            max_ind = max(ind_weights, key=lambda k: ind_weights[k])
            max_ind_w = ind_weights[max_ind]

        # Beta 贡献
        beta_contribs = {
            sym: symbol_weights.get(sym, 0.0) * self._symbol_betas.get(sym, 1.0)
            for sym in positions
        }

        return ExposureReport(
            nav                  = nav,
            position_count       = len(positions),
            total_gross_notional = gross_notional,
            total_net_notional   = net_notional,
            leverage             = leverage,
            portfolio_beta       = portfolio_beta,
            max_single_weight    = max_w,
            max_single_symbol    = max_sym,
            industry_weights     = ind_weights,
            max_industry_weight  = max_ind_w,
            max_industry_name    = max_ind,
            symbol_weights       = symbol_weights,
            beta_contributions   = beta_contribs,
            computed_at          = datetime.now(),
        )

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_snapshot(self) -> PortfolioSnapshot:
        """返回当前持仓快照（副本）。"""
        return self._snapshot

    def get_position(self, symbol: str) -> PositionSnapshot | None:
        return self._snapshot.positions.get(symbol)

    def clear(self) -> None:
        """清空所有持仓（新一轮回测前调用）。"""
        self._snapshot = PortfolioSnapshot()
        self._snapshot.nav = self._nav
