"""
针对性诊断脚本：601211.SSE 1分钟 K 线，测试2 策略，追查 2026-07-17 附近为什么"卖出条件亮但回测不卖"

模拟 UI 端 _on_backtest 的完整流程，在 _backtest_symbol 的关键决策点打印每根 K 线的状态，
输出可读的时间戳、bar 索引、当前 buy/sell tree 评估结果、状态机决策（空仓/持仓/冷却期/T+1）。

用法:
    python tests/_diag_601211_20260717.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import get_database
from vnpy.strategy_condition.core.strategy import Strategy
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
from vnpy.strategy_condition.engine.scan_engine import ScanEngine


# ---------- BarAdapter：与 widget.py 保持一致 ----------
class _BarAdapter:
    __slots__ = ("_b",)

    def __init__(self, bar) -> None:
        self._b = bar

    @property
    def open(self):  return self._b.open_price
    @property
    def high(self):  return self._b.high_price
    @property
    def low(self):   return self._b.low_price
    @property
    def close(self): return self._b.close_price
    @property
    def volume(self): return self._b.volume
    @property
    def dt(self):    return self._b.datetime


# ---------- 加载策略 ----------
def load_strategy(name: str = "测试2") -> Strategy:
    fp = Path.home() / ".vnpy" / "strategy_condition" / f"{name}.json"
    if not fp.exists():
        raise FileNotFoundError(f"策略文件不存在：{fp}")
    txt = fp.read_text(encoding="utf-8")
    return Strategy.from_json(txt)


# ---------- 加载 K 线 ----------
def load_bars(symbol: str, start: datetime, end: datetime,
              interval: Interval = Interval.MINUTE) -> list:
    db = get_database()
    code, exch_str = symbol.split(".")
    raw = db.load_bar_data(
        symbol=code, exchange=Exchange(exch_str),
        interval=interval, start=start, end=end,
    )
    return [_BarAdapter(b) for b in raw]


# ---------- 诊断回测：从 scan_engine._backtest_symbol 移植并加日志 ----------
def diag_backtest(symbol: str, all_bars: list, strategy: Strategy,
                  warmup: int, focus_start: datetime, focus_end: datetime):
    ce = ConditionEngine()
    se = ScanEngine(ce)
    eval_fn = ce.eval_condition
    sp = strategy.params
    cost = sp.commission_rate + sp.stamp_duty_rate + sp.slippage_rate

    print(f"\n===== 回测参数 =====")
    print(f"  股票    : {symbol}")
    print(f"  K线数量 : {len(all_bars)}")
    print(f"  warmup  : {warmup}")
    print(f"  min_bars: {sp.min_bars}")
    print(f"  max_hold: {sp.max_hold_days}")
    print(f"  cooldown: {sp.cooldown_days}")
    print(f"  stop_loss_pct   : {sp.stop_loss_pct}")
    print(f"  take_profit_pct : {sp.take_profit_pct}")
    print(f"  trail_drawdown  : {sp.trail_drawdown}")
    print(f"  is_intraday: True (分钟线)")
    print()

    print(f"===== buy_tree =====")
    print(f"  {strategy.buy_tree}")
    print(f"===== sell_tree =====")
    print(f"  {strategy.sell_tree}")
    print()

    signals = []
    last_exit_idx = -9999
    i = warmup

    # 逐笔交易记录
    trades = []
    # 逐 bar 决策日志（仅记录 focus 区间内的）
    bar_log = []

    # 处理时区：如果 K 线 dt 带时区，将 focus 边界也转成 UTC+8
    sample_dt = all_bars[warmup].dt if warmup < len(all_bars) else all_bars[0].dt
    if sample_dt.tzinfo is not None:
        focus_start = focus_start.replace(tzinfo=sample_dt.tzinfo)
        focus_end = focus_end.replace(tzinfo=sample_dt.tzinfo)

    def in_focus(bar) -> bool:
        return focus_start <= bar.dt <= focus_end

    while i < len(all_bars) - 1:
        bar_i = all_bars[i]
        in_range = in_focus(bar_i)

        # 冷却期
        if sp.cooldown_days > 0:
            if i - last_exit_idx <= sp.cooldown_days:
                if in_range:
                    bar_log.append(
                        f"[{bar_i.dt}] i={i:>6} 状态=空仓 决策=冷却期 "
                        f"(距上次卖出={i - last_exit_idx}<={sp.cooldown_days})"
                    )
                i += 1
                continue

        # 评 buy_tree
        bars_so_far = all_bars[:i + 1]
        try:
            passed, score = strategy.buy_tree.evaluate(symbol, bars_so_far, eval_fn)
        except Exception as e:
            passed, score = False, 0.0
            if in_range:
                bar_log.append(f"[{bar_i.dt}] i={i:>6} buy_tree 评估异常: {e}")

        if not passed:
            if in_range:
                bar_log.append(
                    f"[{bar_i.dt}] i={i:>6} 状态=空仓 决策=buy_tree未通过 score={score:.3f}"
                )
            i += 1
            continue

        # 同日冲突
        try:
            sell_conflict, _ = se._eval_sell_tree(
                strategy.sell_tree, symbol,
                entry_price=bar_i.close, cur_price=bar_i.close,
                peak_price=bar_i.close, hold_days=0,
                bars=bars_so_far, sp=sp,
            )
        except Exception:
            sell_conflict = False

        if sell_conflict:
            if in_range:
                bar_log.append(
                    f"[{bar_i.dt}] i={i:>6} 状态=空仓 决策=同日冲突 "
                    f"(buy+sell同时True)"
                )
            i += 1
            continue

        # 建仓
        entry_price = bar_i.close
        peak_price = entry_price
        max_j = min(i + sp.max_hold_days, len(all_bars) - 1)
        entry_date = bar_i.dt.date()

        # T+1: 找下一个交易日首根
        start_j = i + 1
        for j in range(i + 1, max_j + 1):
            if all_bars[j].dt.date() > entry_date:
                start_j = j
                break
        else:
            start_j = max_j

        if in_range or in_focus(all_bars[min(max_j, len(all_bars)-1)]):
            bar_log.append(
                f"[{bar_i.dt}] i={i:>6} 状态=空仓→建仓 entry_price={entry_price:.3f} "
                f"start_j={start_j} max_j={max_j} T+1保护={start_j-i-1}根"
            )

        # 持仓段
        exit_bar = max_j
        exit_price = all_bars[max_j].close
        exit_reason = "max_hold"

        for j in range(start_j, max_j + 1):
            bar_j = all_bars[j]
            cur_price = bar_j.close
            if cur_price > peak_price:
                peak_price = cur_price
            hold_bars_count = j - i

            try:
                triggered, _ = se._eval_sell_tree(
                    strategy.sell_tree, symbol, entry_price,
                    cur_price, peak_price, hold_bars_count,
                    all_bars[:j + 1], sp,
                )
            except Exception:
                triggered = False

            if in_focus(bar_j):
                bar_log.append(
                    f"[{bar_j.dt}] j={j:>6} 状态=持仓 hold_bars={hold_bars_count} "
                    f"cur={cur_price:.3f} peak={peak_price:.3f} "
                    f"drawdown={100*(peak_price-cur_price)/peak_price:.2f}% "
                    f"pnl={100*(cur_price-entry_price)/entry_price:.2f}% "
                    f"sell_tree={'[HIT]' if triggered else '[--] '}"
                )

            if triggered:
                exit_bar = j
                exit_price = cur_price
                try:
                    exit_reason = se._exit_reason(
                        strategy.sell_tree, entry_price,
                        cur_price, peak_price, hold_bars_count,
                        all_bars[:j + 1], sp,
                    )
                except Exception:
                    exit_reason = "?"
                break

        # 记录交易
        raw_ret = (exit_price - entry_price) / entry_price if entry_price > 0 else 0.0
        exit_dt = all_bars[exit_bar].dt
        trades.append({
            "entry_i": i, "exit_i": exit_bar,
            "entry_dt": bar_i.dt, "exit_dt": exit_dt,
            "entry_price": entry_price, "exit_price": exit_price,
            "reason": exit_reason,
            "pnl_pct": (raw_ret - cost) * 100,
            "hold_bars": exit_bar - i,
        })

        last_exit_idx = exit_bar
        i = exit_bar + 1

    return trades, bar_log


def main():
    strategy = load_strategy("测试2")
    print(f"加载策略: {strategy.name}")

    # 与 UI 保持一致：起止日期 2020-01-01 → 今日
    # 但为了聚焦 07-17，只需要该日前后各几天的数据
    focus_dt = datetime(2026, 7, 17)
    focus_start = focus_dt - timedelta(days=2)
    focus_end = focus_dt + timedelta(days=1)

    load_start = datetime(2020, 1, 1)
    load_end = datetime.now().replace(hour=23, minute=59, second=59)

    print(f"加载 K 线: 601211.SSE 1分钟 {load_start.date()} → {load_end.date()}")
    bars = load_bars("601211.SSE", load_start, load_end, Interval.MINUTE)
    print(f"共 {len(bars)} 根 K 线\n")

    if not bars:
        print("未加载到任何 K 线，请检查数据库")
        return

    warmup = max(60, strategy.params.min_bars)

    trades, bar_log = diag_backtest(
        "601211.SSE", bars, strategy, warmup,
        focus_start, focus_end,
    )

    print(f"===== 全部回测交易 (共 {len(trades)} 笔) =====")
    for t in trades:
        marker = " <== 涉及 07-17" if (
            t["entry_dt"].date() <= focus_dt.date() <= t["exit_dt"].date()
        ) else ""
        print(
            f"  {t['entry_dt']} → {t['exit_dt']} "
            f"hold={t['hold_bars']:>4}根 "
            f"pnl={t['pnl_pct']:+.2f}% reason={t['reason']}{marker}"
        )

    print(f"\n===== 07-15 ~ 07-18 期间逐 K 线决策日志 (共 {len(bar_log)} 行) =====")
    for line in bar_log:
        print(line)


if __name__ == "__main__":
    main()