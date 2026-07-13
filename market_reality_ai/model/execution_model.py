"""
market_reality_ai/model/execution_model.py

Phase 2: 执行现实仿真完整模型。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import ExecutionDeviationType, SimulationStatus


@dataclass
class SlippageRecord:
    """单笔成交执行现实记录。"""
    record_id:       str   = ""
    symbol:          str   = ""
    direction:       int   = 1        # +1 buy / -1 sell
    order_size:      float = 0.0
    adv:             float = 10000.0  # average daily volume

    # prices
    order_price:     float = 0.0      # reference price at signal time
    realized_price:  float = 0.0      # Realized Price = Market + Slip + Impact + Noise

    # deviation components (all in basis points)
    slippage_bps:    float = 0.0      # execution slippage
    spread_bps:      float = 5.0      # bid-ask spread at execution
    delay_noise_bps: float = 0.0      # price drift during latency
    impact_bps:      float = 0.0      # Phase 3 market impact (stub here)
    total_cost_bps:  float = 0.0      # sum of all components

    # fill
    fill_rate:       float = 1.0      # 0.0–1.0
    filled_size:     float = 0.0      # actual filled quantity
    rejected:        bool  = False

    # execution quality
    latency_ms:      float = 0.0
    regime:          str   = "normal"
    volatility:      float = 0.02

    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "record_id":       self.record_id,
            "symbol":          self.symbol,
            "direction":       self.direction,
            "order_size":      self.order_size,
            "order_price":     self.order_price,
            "realized_price":  round(self.realized_price, 8),
            "slippage_bps":    round(self.slippage_bps,    4),
            "spread_bps":      round(self.spread_bps,      4),
            "delay_noise_bps": round(self.delay_noise_bps, 4),
            "impact_bps":      round(self.impact_bps,      4),
            "total_cost_bps":  round(self.total_cost_bps,  4),
            "fill_rate":       round(self.fill_rate,        4),
            "filled_size":     round(self.filled_size,      6),
            "rejected":        self.rejected,
            "latency_ms":      round(self.latency_ms,       2),
            "regime":          self.regime,
            "volatility":      round(self.volatility,       6),
            "timestamp":       str(self.timestamp)[:19],
        }


@dataclass
class CalibrationParams:
    """ExecutionSimulator 校准参数。"""
    base_bps:    float = 2.0    # base slippage floor
    eta:         float = 0.10   # temporary impact coefficient
    gamma:       float = 0.03   # permanent impact coefficient
    base_latency:float = 5.0    # median latency (ms)
    jitter_ms:   float = 3.0    # latency jitter
    queue_ms:    float = 0.0    # queue waiting time
    n_samples:   int   = 0
    calibrated:  bool  = False

    @classmethod
    def from_dict(cls, d: dict) -> "CalibrationParams":
        return cls(
            base_bps    = d.get("base_bps",    2.0),
            eta         = d.get("eta",         0.10),
            gamma       = d.get("gamma",       0.03),
            base_latency= d.get("avg_latency", 5.0),
            jitter_ms   = d.get("jitter_ms",   3.0),
            n_samples   = d.get("n_samples",   0),
            calibrated  = d.get("calibrated",  False),
        )

    def to_dict(self) -> dict:
        return {
            "base_bps":    self.base_bps,
            "eta":         self.eta,
            "gamma":       self.gamma,
            "avg_latency": self.base_latency,
            "jitter_ms":   self.jitter_ms,
            "queue_ms":    self.queue_ms,
            "n_samples":   self.n_samples,
            "calibrated":  self.calibrated,
        }


@dataclass
class ExecutionRealityState:
    """执行现实仿真整体状态。"""
    status:            SimulationStatus = SimulationStatus.IDLE
    total_simulations: int   = 0
    total_rejected:    int   = 0

    # aggregated metrics
    avg_slippage_bps:  float = 0.0
    p50_slippage_bps:  float = 0.0
    p95_slippage_bps:  float = 0.0
    avg_fill_rate:     float = 0.0
    rejection_rate:    float = 0.0
    avg_latency_ms:    float = 0.0
    reality_gap_bps:   float = 0.0   # composite execution cost

    calibration:       CalibrationParams = field(
        default_factory=CalibrationParams)
    records:           list[SlippageRecord] = field(default_factory=list)
    updated_at:        datetime = field(default_factory=datetime.now)

    def update_from_records(self) -> None:
        """Recompute aggregate metrics from the records list."""
        recs = self.records
        if not recs:
            return
        n = len(recs)
        slips  = sorted(r.slippage_bps for r in recs)
        fills  = [r.fill_rate   for r in recs]
        lats   = [r.latency_ms  for r in recs]
        rej_n  = sum(1 for r in recs if r.rejected)

        def _p(sl, p):
            return sl[min(int(len(sl) * p), len(sl) - 1)]

        self.total_simulations = n
        self.total_rejected    = rej_n
        self.avg_slippage_bps  = round(sum(slips) / n,   4)
        self.p50_slippage_bps  = round(_p(slips, 0.50),  4)
        self.p95_slippage_bps  = round(_p(slips, 0.95),  4)
        self.avg_fill_rate     = round(sum(fills) / n,   4)
        self.rejection_rate    = round(rej_n / n,         4)
        self.avg_latency_ms    = round(sum(lats)  / n,   2)
        avg_s = sum(slips) / n
        avg_f = sum(fills) / n
        self.reality_gap_bps   = round(avg_s * (2.0 - avg_f), 4)
        self.updated_at        = datetime.now()

    def to_dict(self) -> dict:
        return {
            "status":            self.status.value,
            "total_simulations": self.total_simulations,
            "total_rejected":    self.total_rejected,
            "avg_slippage_bps":  self.avg_slippage_bps,
            "p50_slippage_bps":  self.p50_slippage_bps,
            "p95_slippage_bps":  self.p95_slippage_bps,
            "avg_fill_rate":     self.avg_fill_rate,
            "rejection_rate":    self.rejection_rate,
            "avg_latency_ms":    self.avg_latency_ms,
            "reality_gap_bps":   self.reality_gap_bps,
            "phase":             2,
        }
