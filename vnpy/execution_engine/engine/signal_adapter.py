"""
execution_engine/engine/signal_adapter.py

SignalAdapter — 上游信号 -> OrderRequest 转换层（Phase 4）。
"""

from __future__ import annotations
import math
from typing import Any
from ..constant import SignalSource
from ..model.order_model import OrderRequest
from ..model.signal_model import ExecutionSignal, BatchOrderRequest


class SignalAdapter:
    """上游信号 -> OrderRequest 转换层（无状态）。"""

    def __init__(self, min_volume=0.01, lot_size=1.0, price_fallback=0.0):
        self.min_volume     = min_volume
        self.lot_size       = lot_size
        self.price_fallback = price_fallback

    # Portfolio
    def from_portfolio(self, data):
        requests, skipped = [], []
        for item in data.get("rebalance", []):
            try:
                symbol   = str(item["symbol"])
                price    = float(item.get("signal_price", self.price_fallback))
                nav      = float(item.get("nav", 0.0))
                target_w = float(item.get("target_weight",  0.0))
                current_w= float(item.get("current_weight", 0.0))
                delta_w  = target_w - current_w
                if price <= 0:
                    skipped.append(f"portfolio: zero price {symbol}"); continue
                if abs(delta_w) < 1e-9:
                    skipped.append(f"portfolio: zero delta {symbol}"); continue
                raw_vol = abs(delta_w) * nav / price if nav > 0 else abs(delta_w)
                volume  = self._round_lot(raw_vol)
                if volume < self.min_volume:
                    skipped.append(f"portfolio: vol too small {symbol}"); continue
                direction = "LONG" if delta_w > 0 else "SHORT"
                requests.append(OrderRequest(
                    symbol=symbol, direction=direction, volume=volume,
                    signal_price=price, source=SignalSource.PORTFOLIO.value,
                ))
            except (KeyError, ValueError, TypeError) as e:
                skipped.append(f"portfolio: {e}")
        return requests, skipped

    # CTA
    def from_cta(self, data):
        requests, skipped = [], []
        try:
            symbol    = str(data["symbol"])
            direction = str(data.get("direction", "LONG")).upper()
            if direction not in ("LONG", "SHORT"):
                return requests, [f"cta: bad direction {direction}"]
            price  = float(data.get("price", self.price_fallback))
            if price <= 0:
                return requests, [f"cta: zero price {symbol}"]
            volume = self._round_lot(float(data.get("volume", 0.0)))
            if volume < self.min_volume:
                return requests, [f"cta: vol too small {symbol}"]
            requests.append(OrderRequest(
                symbol=symbol, direction=direction, volume=volume,
                signal_price=price, source=SignalSource.CTA.value,
            ))
        except (KeyError, ValueError, TypeError) as e:
            skipped.append(f"cta: {e}")
        return requests, skipped

    # Factor
    def from_factor(self, data):
        requests, skipped = [], []
        nav = float(data.get("nav", 0.0))
        for item in data.get("signals", []):
            try:
                symbol    = str(item["symbol"])
                direction = str(item.get("direction", "LONG")).upper()
                if direction not in ("LONG", "SHORT"):
                    skipped.append(f"factor: bad direction {symbol}"); continue
                price  = float(item.get("price", self.price_fallback))
                if price <= 0:
                    skipped.append(f"factor: zero price {symbol}"); continue
                weight = float(item.get("weight", 0.0))
                raw_vol = weight * nav / price if nav > 0 and price > 0 else weight
                volume  = self._round_lot(raw_vol)
                if volume < self.min_volume:
                    skipped.append(f"factor: vol too small {symbol}"); continue
                requests.append(OrderRequest(
                    symbol=symbol, direction=direction, volume=volume,
                    signal_price=price, source=SignalSource.FACTOR.value,
                ))
            except (KeyError, ValueError, TypeError) as e:
                skipped.append(f"factor: {e}")
        return requests, skipped

    # BatchOrderRequest
    def from_batch(self, batch: BatchOrderRequest):
        requests, skipped = [], []
        for sig in batch.valid_signals:
            req = self._signal_to_request(sig)
            if req is not None:
                requests.append(req)
            else:
                skipped.append(f"batch: skipped {sig.symbol}")
        return requests, skipped

    # 自动路由
    def from_dict(self, data):
        t = str(data.get("type", "")).lower()
        if t == "portfolio":
            return self.from_portfolio(data)
        if t == "cta":
            return self.from_cta(data)
        if t == "factor":
            return self.from_factor(data)
        return self._parse_generic(data)

    # 内部工具
    def _round_lot(self, volume):
        if self.lot_size <= 0:
            return volume
        return math.floor(volume / self.lot_size) * self.lot_size

    def _signal_to_request(self, sig: ExecutionSignal):
        if not sig.is_valid:
            return None
        if sig.volume > 0:
            volume = self._round_lot(sig.volume)
        elif sig.target_weight > 0 and sig.signal_price > 0 and sig.portfolio_nav > 0:
            volume = self._round_lot(
                sig.target_weight * sig.portfolio_nav / sig.signal_price
            )
        else:
            return None
        if volume < self.min_volume:
            return None
        return OrderRequest(
            symbol=sig.symbol, direction=sig.direction, volume=volume,
            signal_price=sig.signal_price, source=sig.source.value,
        )

    def _parse_generic(self, data):
        requests, skipped = [], []
        required = ("symbol", "direction", "volume", "signal_price")
        missing  = [k for k in required if k not in data]
        if missing:
            return requests, [f"generic: missing {missing}"]
        try:
            volume = self._round_lot(float(data["volume"]))
            if volume < self.min_volume:
                return requests, ["generic: vol too small"]
            requests.append(OrderRequest(
                symbol=str(data["symbol"]),
                direction=str(data["direction"]).upper(),
                volume=volume,
                signal_price=float(data["signal_price"]),
                order_type=str(data.get("order_type", "MARKET")),
                source=str(data.get("source", SignalSource.MANUAL.value)),
            ))
        except (KeyError, ValueError, TypeError) as e:
            skipped.append(f"generic: {e}")
        return requests, skipped
