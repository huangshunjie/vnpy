"""
backtest_bridge/model/signal_model.py

SignalRecord    — 单条外部信号（来自任意模块）
BacktestConfig  — 单次回测参数配置
BacktestResult  — 单次回测结果汇总
BatchResult     — 批量回测汇总
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import SignalSource, SignalDirection, BridgeMode, PositionSizing, RunStatus


@dataclass
class SignalRecord:
    """单条外部信号。"""
    signal_id:   str             = ""
    source:      SignalSource    = SignalSource.CUSTOM
    symbol:      str             = ""
    direction:   SignalDirection = SignalDirection.FLAT
    strength:    float           = 0.0     # [-1.0, 1.0]  强度
    confidence:  float           = 1.0     # [0.0, 1.0]  置信度
    timestamp:   datetime        = field(default_factory=datetime.now)
    metadata:    dict            = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "signal_id":  self.signal_id,
            "source":     self.source.value,
            "symbol":     self.symbol,
            "direction":  self.direction.value,
            "strength":   round(self.strength,   4),
            "confidence": round(self.confidence, 4),
            "timestamp":  str(self.timestamp)[:19],
        }


@dataclass
class BacktestConfig:
    """单次回测参数配置。"""
    config_id:   str          = ""
    name:        str          = ""
    vt_symbol:   str          = "BTCUSDT.BINANCE"
    interval:    str          = "1d"
    start:       datetime     = field(default_factory=lambda: datetime(2022, 1, 1))
    end:         datetime     = field(default_factory=lambda: datetime(2023, 12, 31))
    capital:     float        = 1_000_000.0
    rate:        float        = 0.0002      # 手续费率
    slippage:    float        = 0.5         # 滑点（价格单位）
    size:        float        = 1.0         # 合约乘数
    pricetick:   float        = 0.1         # 最小价格变动
    mode:        BridgeMode   = BridgeMode.SIGNAL_DRIVEN
    signal_source: SignalSource = SignalSource.ALPHA_FACTORY
    sizing:      PositionSizing = PositionSizing.SIGNAL_SCALED
    # signal scaling parameters
    max_pos:     float        = 1.0         # 最大仓位（手数）
    signal_threshold: float   = 0.1         # 信号强度阈值（低于此不交易）
    # risk filter
    use_risk_filter: bool     = True        # 是否使用风险门控

    def to_dict(self) -> dict:
        return {
            "config_id":        self.config_id,
            "name":             self.name,
            "vt_symbol":        self.vt_symbol,
            "interval":         self.interval,
            "start":            str(self.start)[:10],
            "end":              str(self.end)[:10],
            "capital":          self.capital,
            "rate":             self.rate,
            "slippage":         self.slippage,
            "mode":             self.mode.value,
            "signal_source":    self.signal_source.value,
            "sizing":           self.sizing.value,
            "max_pos":          self.max_pos,
            "signal_threshold": self.signal_threshold,
            "use_risk_filter":  self.use_risk_filter,
        }


@dataclass
class BacktestResult:
    """单次回测结果。"""
    run_id:      str       = ""
    config_id:   str       = ""
    name:        str       = ""
    status:      RunStatus = RunStatus.PENDING

    # core metrics
    total_return:    float = 0.0
    annual_return:   float = 0.0
    max_drawdown:    float = 0.0
    sharpe_ratio:    float = 0.0
    calmar_ratio:    float = 0.0
    sortino_ratio:   float = 0.0

    # trade stats
    total_trades:    int   = 0
    win_rate:        float = 0.0
    profit_factor:   float = 0.0
    avg_trade_pnl:   float = 0.0

    # capital
    end_balance:     float = 0.0
    total_commission:float = 0.0
    total_slippage:  float = 0.0

    # signal stats
    signals_used:    int   = 0
    signals_total:   int   = 0

    started_at:  datetime       = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    error_msg:   str             = ""

    # raw stats dict from BacktestingEngine.calculate_statistics()
    raw_stats:   dict            = field(default_factory=dict)

    @property
    def duration_s(self) -> float:
        if self.finished_at is None:
            return 0.0
        return round((self.finished_at - self.started_at).total_seconds(), 2)

    def to_dict(self) -> dict:
        return {
            "run_id":          self.run_id,
            "config_id":       self.config_id,
            "name":            self.name,
            "status":          self.status.value,
            "total_return":    round(self.total_return,  4),
            "annual_return":   round(self.annual_return, 4),
            "max_drawdown":    round(self.max_drawdown,  4),
            "sharpe_ratio":    round(self.sharpe_ratio,  4),
            "calmar_ratio":    round(self.calmar_ratio,  4),
            "sortino_ratio":   round(self.sortino_ratio, 4),
            "total_trades":    self.total_trades,
            "win_rate":        round(self.win_rate,      4),
            "profit_factor":   round(self.profit_factor, 4),
            "end_balance":     round(self.end_balance,   2),
            "signals_used":    self.signals_used,
            "signals_total":   self.signals_total,
            "duration_s":      self.duration_s,
            "error_msg":       self.error_msg,
        }


@dataclass
class BatchResult:
    """批量回测（多配置对比）结果。"""
    batch_id:    str       = ""
    name:        str       = ""
    run_ids:     list[str] = field(default_factory=list)
    results:     list[BacktestResult] = field(default_factory=list)
    started_at:  datetime  = field(default_factory=datetime.now)
    finished_at: datetime | None = None

    @property
    def best_sharpe(self) -> BacktestResult | None:
        done = [r for r in self.results if r.status == RunStatus.COMPLETED]
        return max(done, key=lambda r: r.sharpe_ratio) if done else None

    @property
    def best_return(self) -> BacktestResult | None:
        done = [r for r in self.results if r.status == RunStatus.COMPLETED]
        return max(done, key=lambda r: r.total_return) if done else None

    def to_dict(self) -> dict:
        done = [r for r in self.results if r.status == RunStatus.COMPLETED]
        bs   = self.best_sharpe
        br   = self.best_return
        return {
            "batch_id":    self.batch_id,
            "name":        self.name,
            "total_runs":  len(self.results),
            "completed":   len(done),
            "failed":      sum(1 for r in self.results if r.status == RunStatus.FAILED),
            "best_sharpe_run": bs.run_id if bs else "",
            "best_sharpe":     round(bs.sharpe_ratio, 4) if bs else 0.0,
            "best_return_run": br.run_id if br else "",
            "best_return":     round(br.total_return, 4) if br else 0.0,
            "started_at":  str(self.started_at)[:19],
            "finished_at": str(self.finished_at)[:19] if self.finished_at else "",
        }
