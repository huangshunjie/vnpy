"""
market_behavior/engine/backtest_engine.py
Phase 8: 回测引擎

功能：
  run()                 在历史K线上逐根回放，记录每次条件触发
  calc_forward_return() 计算触发后 N 日持有收益率
  calc_hit_rate()       胜率
  calc_sharpe()         夏普比率
  calc_max_drawdown()   最大回撤
  report()              汇总输出字典
"""
from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..constant import BacktestStatus
from ..model.candle import CandleBar
from ..engine.adapter_engine import AdapterEngine, ScreenSpec, ScreenCondition


class TriggerRecord:
    """单次条件触发记录。"""

    def __init__(
        self,
        record_id:    str,
        symbol:       str,
        trigger_dt:   datetime,
        trigger_bar:  int,          # 触发时的 bar 索引（在全量序列中）
        trigger_price: float,
        score:        float,
        details:      Dict[str, Any],
    ) -> None:
        self.record_id     = record_id
        self.symbol        = symbol
        self.trigger_dt    = trigger_dt
        self.trigger_bar   = trigger_bar
        self.trigger_price = trigger_price
        self.score         = score
        self.details       = details
        # 持有期收益率（由 calc_forward_return 填充）
        self.forward_returns: Dict[int, float] = {}
        self.gross_returns:   Dict[int, float] = {}  # 扣成本前的毛收益

    def to_dict(self) -> dict:
        return {
            "record_id":      self.record_id,
            "symbol":         self.symbol,
            "trigger_dt":     str(self.trigger_dt)[:19],
            "trigger_bar":    self.trigger_bar,
            "trigger_price":  self.trigger_price,
            "score":          round(self.score, 6),
            "forward_returns": {str(k): round(v, 6)
                                for k, v in self.forward_returns.items()},
        }


class BacktestResult:
    """回测结果汇总。"""

    def __init__(
        self,
        bt_id:          str,
        symbol:         str,
        spec_name:      str,
        status:         BacktestStatus,
        triggers:       List[TriggerRecord],
        hold_days:      int,
        total_bars:     int,
        metrics:        Dict[str, Any],
    ) -> None:
        self.bt_id      = bt_id
        self.symbol     = symbol
        self.spec_name  = spec_name
        self.status     = status
        self.triggers   = triggers
        self.hold_days  = hold_days
        self.total_bars = total_bars
        self.metrics    = metrics

    def to_dict(self) -> dict:
        return {
            "bt_id":       self.bt_id,
            "symbol":      self.symbol,
            "spec_name":   self.spec_name,
            "status":      self.status.value,
            "total_bars":  self.total_bars,
            "hold_days":   self.hold_days,
            "trigger_count": len(self.triggers),
            "metrics":     self.metrics,
            "triggers":    [t.to_dict() for t in self.triggers],
        }


class _ReplayBuffer:
    """
    回放用只读滑动窗口 buffer。
    向 AdapterEngine 注入，每步只暴露截止当前根的历史。
    """

    def __init__(self, symbol: str, all_bars: List[CandleBar]) -> None:
        self._symbol   = symbol
        self._all_bars = all_bars
        self._cursor   = 0          # 当前可见的最后一根（含）

    def advance(self, idx: int) -> None:
        self._cursor = idx

    def get(self, symbol: str, n: int = 30) -> List[CandleBar]:
        if symbol != self._symbol:
            return []
        end = self._cursor + 1
        start = max(0, end - n)
        return self._all_bars[start:end]


class BacktestEngine:
    """
    回测引擎 (Phase 8)。

    用法：
        be = BacktestEngine()
        be.set_adapter_engine(ae)
        result = be.run(symbol, all_bars, spec, hold_days=5)
        print(result.metrics)
    """

    DEFAULT_CFG: Dict[str, Any] = {
        "warmup_bars":       20,    # 预热期（不触发信号的前 N 根）
        "hold_days":         5,     # 默认持有天数
        "risk_free_rate":    0.0,   # 无风险利率（年化%，夏普用）
        "annual_factor":     252,   # 年化因子（交易日）
        "min_triggers":      3,     # 回测有效触发次数下限
        "allow_overlap":     False, # 是否允许持仓期内再次触发
        # 交易成本（均为小数，如万3=0.0003）
        "commission_rate":   0.0003,  # 买入手续费率（万3）
        "stamp_duty_rate":   0.0010,  # 卖出印花税率（千1）
        "slippage_rate":     0.0002,  # 滑点（买卖各承担一半，共万2）
    }

    def __init__(
        self,
        log_fn:      Optional[Callable[[str], None]] = None,
        dispatch_fn: Optional[Callable[[str, dict], None]] = None,
    ) -> None:
        self._log        = log_fn or print
        self._dispatch   = dispatch_fn
        self._running    = False
        self._cfg        = dict(self.DEFAULT_CFG)
        self._adapter    = None
        self._bt_count   = 0

    def set_adapter_engine(self, ae: AdapterEngine) -> None:
        self._adapter = ae

    def configure(self, **kw) -> None:
        self._cfg.update(kw)

    def init(self):  self._log("[BacktestEngine] init()")
    def start(self): self._running = True;  self._log("[BacktestEngine] start()")
    def stop(self):  self._running = False; self._log("[BacktestEngine] stop()")

    def summary(self) -> dict:
        return {
            "engine":   "BacktestEngine",
            "status":   "running" if self._running else "stopped",
            "bt_count": self._bt_count,
        }

    # ══════════════════════════════════════════════════════════════════
    # 主回测入口
    # ══════════════════════════════════════════════════════════════════

    def run(
        self,
        symbol:    str,
        all_bars:  List[CandleBar],
        spec:      ScreenSpec,
        hold_days:       int   = 0,
        commission_rate: float = None,
        stamp_duty_rate: float = None,
        slippage_rate:   float = None,
        take_profit:     float = 0.0,    # 止盈触发收益率（%），0=不启用
        trail_drawdown:  float = 0.0,    # 追踪止盈回撤（%），0=不启用
        stop_loss:       float = 0.0,    # 止损触发亏损（%），0=不启用
    ) -> BacktestResult:
        """
        逐根回放 all_bars，在每根K线末尾用 AdapterEngine 评估条件。
        记录触发点，计算持有收益，返回 BacktestResult。
        """
        hold  = hold_days or self._cfg["hold_days"]
        comm  = commission_rate if commission_rate is not None else self._cfg["commission_rate"]
        stamp = stamp_duty_rate if stamp_duty_rate is not None else self._cfg["stamp_duty_rate"]
        slip  = slippage_rate   if slippage_rate   is not None else self._cfg["slippage_rate"]
        # 止盈止损参数注入 cfg，供 _fill_forward_returns 读取
        cfg   = dict(self._cfg)
        cfg["take_profit"]    = take_profit
        cfg["trail_drawdown"] = trail_drawdown
        cfg["stop_loss"]      = stop_loss
        warmup = self._cfg["warmup_bars"]
        bt_id  = uuid.uuid4().hex[:10]

        if not all_bars or len(all_bars) < warmup + 2:
            return BacktestResult(bt_id, symbol, spec.name,
                                  BacktestStatus.FAILED, [], hold,
                                  len(all_bars),
                                  {"error": "insufficient_bars"})

        # 注入回放 buffer
        replay_buf = _ReplayBuffer(symbol, all_bars)
        if self._adapter:
            self._adapter.set_candle_buffer(replay_buf)
            if self._adapter._factor_engine:
                self._adapter._factor_engine.set_candle_buffer(replay_buf)
            if self._adapter._label_engine:
                self._adapter._label_engine.set_candle_buffer(replay_buf)

        triggers: List[TriggerRecord] = []
        in_hold_until = -1   # 当前持仓到期的 bar 索引

        for i in range(warmup, len(all_bars)):
            replay_buf.advance(i)

            # 持仓期内不重复触发（若 allow_overlap=False）
            if not self._cfg["allow_overlap"] and i <= in_hold_until:
                continue

            if not self._adapter:
                continue

            result = self._adapter.evaluate(symbol, spec)
            if result.passed:
                bar = all_bars[i]
                rec = TriggerRecord(
                    record_id=f"{bt_id}_{len(triggers)}",
                    symbol=symbol,
                    trigger_dt=bar.dt,
                    trigger_bar=i,
                    trigger_price=bar.close,
                    score=result.score,
                    details=result.details,
                )
                triggers.append(rec)
                in_hold_until = i + hold

        # 计算持有收益
        tp       = cfg.get("take_profit",    0.0)
        trail    = cfg.get("trail_drawdown", 0.0)
        sl       = cfg.get("stop_loss",      0.0)
        self._fill_forward_returns(triggers, all_bars, [hold],
                                   comm, stamp, slip, tp, trail, sl)

        # 统计指标
        metrics = self._calc_metrics(triggers, hold, len(all_bars))

        self._bt_count += 1
        bt_result = BacktestResult(
            bt_id, symbol, spec.name, BacktestStatus.DONE,
            triggers, hold, len(all_bars), metrics,
        )
        self._emit_done(bt_result)
        return bt_result

    # ══════════════════════════════════════════════════════════════════
    # 持有收益填充
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _fill_forward_returns(
        triggers:        List[TriggerRecord],
        all_bars:        List[CandleBar],
        hold_days:       List[int],
        commission_rate: float = 0.0,
        stamp_duty_rate: float = 0.0,
        slippage_rate:   float = 0.0,
        take_profit:     float = 0.0,
        trail_drawdown:  float = 0.0,
        stop_loss:       float = 0.0,
    ) -> None:
        """
        为每条触发记录填充持有收益率，支持动态止盈止损。

        take_profit > 0：盈利达到 take_profit% 后启动追踪止盈
        trail_drawdown > 0：触发止盈后，从最高点回撤 trail_drawdown% 卖出
        stop_loss > 0：亏损达到 stop_loss% 时止损卖出
        hold_days[-1]：最大持仓天数兜底
        """
        cost_total = commission_rate + stamp_duty_rate + slippage_rate
        use_dynamic = (take_profit > 0 or stop_loss > 0)
        max_hold = max(hold_days) if hold_days else 20

        for rec in triggers:
            i  = rec.trigger_bar
            p0 = rec.trigger_price
            if p0 <= 0:
                continue

            if use_dynamic:
                # ── 逐天模拟持仓 ──────────────────────────────────
                peak_price    = p0          # 持仓期间最高价（用于追踪止盈）
                tp_activated  = False       # 是否已触发止盈激活
                exit_bar      = min(i + max_hold, len(all_bars) - 1)
                exit_price    = all_bars[exit_bar].close
                exit_reason   = "max_hold"

                for k in range(i + 1, min(i + max_hold + 1, len(all_bars))):
                    bar   = all_bars[k]
                    price = bar.close
                    ret   = (price - p0) / p0 * 100   # 当前收益率 %

                    # 更新最高价
                    if price > peak_price:
                        peak_price = price

                    # 止损检查
                    if stop_loss > 0 and ret <= -stop_loss:
                        exit_price  = price
                        exit_bar    = k
                        exit_reason = "stop_loss"
                        break

                    # 止盈激活检查
                    if take_profit > 0 and ret >= take_profit:
                        tp_activated = True

                    # 追踪止盈检查（已激活且从最高点回撤超阈值）
                    if tp_activated and trail_drawdown > 0:
                        drawdown = (peak_price - price) / peak_price * 100
                        if drawdown >= trail_drawdown:
                            exit_price  = price
                            exit_bar    = k
                            exit_reason = "take_profit"
                            break

                raw_return = (exit_price - p0) / p0
                rec.details["exit_reason"] = exit_reason
                rec.details["exit_bar"]    = exit_bar
                rec.details["hold_actual"] = exit_bar - i

                for h in hold_days:
                    rec.forward_returns[h] = raw_return - cost_total
                    rec.gross_returns[h]   = raw_return

            else:
                # ── 原有逻辑：固定持有天数 ────────────────────────
                for h in hold_days:
                    j = i + h
                    pn = all_bars[j].close if j < len(all_bars) else all_bars[-1].close
                    raw_return = (pn - p0) / p0
                    rec.forward_returns[h] = raw_return - cost_total
                    rec.gross_returns[h]   = raw_return
    def _calc_metrics(
        self,
        triggers:   List[TriggerRecord],
        hold:       int,
        total_bars: int,
    ) -> Dict[str, Any]:
        """计算胜率 / 平均收益 / 夏普 / 最大回撤等指标。"""
        metrics: Dict[str, Any] = {
            "trigger_count":   len(triggers),
            "total_bars":      total_bars,
            "trigger_rate":    round(len(triggers) / max(total_bars, 1), 4),
        }

        if not triggers:
            metrics.update({
                "hit_rate":        None,
                "avg_return":      None,
                "median_return":   None,
                "max_return":      None,
                "min_return":      None,
                "sharpe":          None,
                "max_drawdown":    None,
                "avg_score":       None,
                "valid":           False,
            })
            return metrics

        rets = [rec.forward_returns.get(hold, 0.0) for rec in triggers]
        scores = [rec.score for rec in triggers]

        metrics["hit_rate"]      = round(self.calc_hit_rate(rets), 4)
        metrics["avg_return"]    = round(self.calc_avg_return(rets), 6)
        metrics["median_return"] = round(self._median(rets), 6)
        metrics["max_return"]    = round(max(rets), 6)
        metrics["min_return"]    = round(min(rets), 6)
        metrics["sharpe"]        = self.calc_sharpe(rets, hold)
        metrics["max_drawdown"]  = round(self.calc_max_drawdown(rets), 6)
        metrics["avg_score"]     = round(sum(scores) / len(scores), 4)
        metrics["valid"]         = (
            len(triggers) >= self._cfg["min_triggers"]
        )
        return metrics

    # ══════════════════════════════════════════════════════════════════
    # 公开统计方法（可独立调用）
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def calc_hit_rate(returns: List[float]) -> float:
        """胜率：收益 > 0 的比例。"""
        if not returns:
            return 0.0
        return sum(1 for r in returns if r > 0) / len(returns)

    @staticmethod
    def calc_avg_return(returns: List[float]) -> float:
        """平均收益率。"""
        if not returns:
            return 0.0
        return sum(returns) / len(returns)

    def calc_sharpe(self, returns: List[float], hold: int = 1) -> Optional[float]:
        """
        夏普比率（基于触发样本收益序列）。
        年化因子 = annual_factor / hold。
        """
        if len(returns) < 2:
            return None
        rf_daily = self._cfg["risk_free_rate"] / 100 / self._cfg["annual_factor"]
        rf_hold  = rf_daily * hold
        excess   = [r - rf_hold for r in returns]
        mean_e   = sum(excess) / len(excess)
        var_e    = sum((x - mean_e) ** 2 for x in excess) / (len(excess) - 1)
        std_e    = math.sqrt(var_e) if var_e > 0 else 0.0
        if std_e == 0:
            return None
        annual_f = math.sqrt(self._cfg["annual_factor"] / hold)
        return round(mean_e / std_e * annual_f, 4)

    @staticmethod
    def calc_max_drawdown(returns: List[float]) -> float:
        """
        最大回撤（基于触发信号的累计净值序列）。
        净值从 1.0 出发，每次触发乘以 (1 + return)。
        """
        if not returns:
            return 0.0
        nav     = 1.0
        peak    = 1.0
        max_dd  = 0.0
        for r in returns:
            nav  *= (1 + r)
            if nav > peak:
                peak = nav
            dd = (peak - nav) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd

    @staticmethod
    def _median(values: List[float]) -> float:
        if not values:
            return 0.0
        s = sorted(values)
        n = len(s)
        if n % 2 == 1:
            return s[n // 2]
        return (s[n // 2 - 1] + s[n // 2]) / 2

    # ══════════════════════════════════════════════════════════════════
    # 报告
    # ══════════════════════════════════════════════════════════════════

    def report(self, result: BacktestResult) -> Dict[str, Any]:
        """
        输出人类可读的回测报告字典。
        包含：触发次数 / 胜率 / 平均收益 / 夏普 / 最大回撤 / 有效性标记。
        """
        m = result.metrics
        valid_warn = "" if m.get("valid") else " ⚠ (触发次数不足)"

        rep = {
            "symbol":         result.symbol,
            "spec_name":      result.spec_name,
            "hold_days":      result.hold_days,
            "total_bars":     result.total_bars,
            "trigger_count":  m.get("trigger_count", 0),
            "trigger_rate":   f"{m.get('trigger_rate', 0):.1%}",
            "hit_rate":       (f"{m['hit_rate']:.1%}" if m.get("hit_rate") is not None
                               else "N/A"),
            "avg_return":     (f"{m['avg_return']*100:.2f}%"
                               if m.get("avg_return") is not None else "N/A"),
            "median_return":  (f"{m['median_return']*100:.2f}%"
                               if m.get("median_return") is not None else "N/A"),
            "max_return":     (f"{m['max_return']*100:.2f}%"
                               if m.get("max_return") is not None else "N/A"),
            "min_return":     (f"{m['min_return']*100:.2f}%"
                               if m.get("min_return") is not None else "N/A"),
            "sharpe":         (str(m["sharpe"]) if m.get("sharpe") is not None
                               else "N/A"),
            "max_drawdown":   (f"{m['max_drawdown']*100:.2f}%"
                               if m.get("max_drawdown") is not None else "N/A"),
            "avg_score":      (f"{m['avg_score']:.3f}"
                               if m.get("avg_score") is not None else "N/A"),
            "valid":          m.get("valid", False),
            "note":           valid_warn,
        }
        return rep

    # ══════════════════════════════════════════════════════════════════
    # 多规格批量回测
    # ══════════════════════════════════════════════════════════════════

    def run_multi(
        self,
        symbol:     str,
        all_bars:   List[CandleBar],
        specs:      List[ScreenSpec],
        hold_days:  int = 0,
    ) -> List[BacktestResult]:
        """对多个 ScreenSpec 做批量回测，返回结果列表。"""
        results = []
        for spec in specs:
            r = self.run(symbol, all_bars, spec, hold_days=hold_days)
            results.append(r)
        return results

    # ── 事件发布 ──────────────────────────────────────────────────────

    def _emit(self, et: str, data: dict) -> None:
        if self._dispatch:
            try:
                self._dispatch(et, data)
            except Exception:
                pass

    def _emit_done(self, result: BacktestResult) -> None:
        from ..event import EVENT_MB_BACKTEST_DONE
        self._emit(EVENT_MB_BACKTEST_DONE, result.to_dict())