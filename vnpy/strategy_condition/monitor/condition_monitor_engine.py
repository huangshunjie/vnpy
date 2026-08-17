"""
strategy_condition/monitor/condition_monitor_engine.py
条件监控引擎：Snapshot 生成 + 状态变化检测 + 缓存管理

核心机制：
  通过代理 eval_fn 拦截 ConditionTree 的叶节点评估过程，
  在不修改已有 ConditionEngine 逻辑的前提下，记录每个条件的详细评估结果。

性能设计：
  - 一次生成，多处使用（Snapshot Cache）
  - 按 symbol 索引缓存
  - 支持增量追加（新K线只追加新 Snapshot）
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..constant import ConditionIndicator
from ..core.condition import Condition
from ..core.condition_tree import ConditionNode
from ..core.strategy import Strategy
from ..engine.condition_engine import ConditionEngine
from .condition_snapshot import ConditionDetail, ConditionSnapshot, StateChangeEvent
from .sell_signal_lifecycle import (
    ConditionLayerResult,
    DecisionCheck,
    DecisionLayerResult,
    ExecutionLayerResult,
    SellSignalLifecycle,
    SignalLayerResult,
)
from ..constant import DecisionResult, RejectReason


# 纯技术面卖出指标：无需持仓上下文也能给出有意义信号的指标。
# 这些条件在监控波形中独立展示，无论是否处于持仓区间。
#
# 注意：STOP_LOSS / TRAILING_STOP / TAKE_PROFIT / MAX_HOLD_DAYS 已移除，
#       因为它们必须依赖持仓状态（买入价、持仓天数），无持仓时不应显示信号。
#       只有在有持仓时，这些条件才会基于真实买入价进行评估。
_PURE_TECHNICAL_EXIT_INDICATORS = {
    ConditionIndicator.MA_BREAK_DOWN,
    ConditionIndicator.MACD_DEATH_SELL,
    ConditionIndicator.TIME_OF_DAY,      # 时间过滤：纯K线时间戳判断，不依赖持仓
}


class ConditionMonitorEngine:
    """
    条件监控引擎。

    职责：
      1. 为每根K线生成 ConditionSnapshot（包含买入/卖出所有条件的详情）
      2. 维护 Snapshot 缓存
      3. 检测条件状态变化事件
      4. 提供热力图和统计数据源
    """

    MAX_CACHE_SIZE: int = 2000

    def __init__(self, condition_engine: ConditionEngine,
                 log_fn: Optional[Callable] = None):
        self._ce = condition_engine
        self._log = log_fn or print
        # 缓存: {symbol: [ConditionSnapshot, ...]}
        self._cache: Dict[str, List[ConditionSnapshot]] = {}
        # 状态变化事件缓存: {symbol: [StateChangeEvent, ...]}
        self._changes_cache: Dict[str, List[StateChangeEvent]] = {}
        # 最近一次内部模拟产生的卖出日期（供调用方同步 K线标记）
        self.last_simulated_sell_dates: List[str] = []

    # ── 公开接口 ──────────────────────────────────────────────────────

    def generate_snapshots(
        self,
        symbol: str,
        bars: list,
        strategy: Strategy,
        warmup: int = 60,
        buy_dates: Optional[List[str]] = None,
        sell_dates: Optional[List[str]] = None,
        inject_buy_signals: bool = True,
    ) -> List[ConditionSnapshot]:
        """
        为指定股票的K线序列生成全部 ConditionSnapshot。

        Args:
            symbol: 股票代码
            bars: 完整K线序列（已排序）
            strategy: 当前策略（含 buy_tree / sell_tree）
            warmup: 预热K线数（前 warmup 根不生成快照）
            buy_dates: 回测产生的买入信号时间字符串列表（用于维护虚拟持仓）
            sell_dates: 回测产生的卖出信号时间字符串列表

        Returns:
            生成的 ConditionSnapshot 列表
        """
        snapshots: List[ConditionSnapshot] = []
        n = len(bars)
        start = max(warmup, 1)

        # 检查是否有"未配对"的买入（没有对应的后续卖出）
        # 对未配对的买入进行内部模拟卖出，保证"一买对应一卖"
        effective_sell_dates = list(sell_dates or [])
        self.last_simulated_sell_dates = []
        if buy_dates:
            unmatched_buys = self._find_unmatched_buys(
                bars, buy_dates, effective_sell_dates)
            if unmatched_buys:
                simulated = self._simulate_sell_dates(
                    symbol, bars, strategy, unmatched_buys, warmup)
                if simulated:
                    effective_sell_dates.extend(simulated)
                    self.last_simulated_sell_dates = simulated
                    self._log(
                        f"[MonitorEngine] {symbol}: "
                        f"{len(unmatched_buys)} 个未配对买入, "
                        f"内部模拟产生 {len(simulated)} 个卖出点"
                    )

        # 构建持仓状态跟踪器
        position_tracker = self._build_position_tracker(
            bars, buy_dates or [], effective_sell_dates)

        for i in range(start, n):
            bars_slice = bars[:i + 1]
            # 获取当前 bar 的持仓上下文
            pos_ctx = position_tracker.get(i)
            snapshot = self._evaluate_bar(
                symbol, bars_slice, i, strategy, pos_ctx)
            snapshots.append(snapshot)

        # 更新缓存
        self._cache[symbol] = snapshots[-self.MAX_CACHE_SIZE:]

        # 生成状态变化事件
        self._changes_cache[symbol] = self._detect_state_changes(snapshots)

        self._log(
            f"[MonitorEngine] {symbol}: 生成 {len(snapshots)} 个快照, "
            f"{len(self._changes_cache[symbol])} 个状态变化事件"
        )

        # ── 实际信号注入 ────────────────────────────────────────────────
        # 将回测产生的 buy_dates 标记到对应 snapshot 上，
        # 使得 Monitor tab 的 buy 波形在信号触发当日呈高电平(1.0)。
        # 注意：卖出条件不做全量注入，因为 sell_tree 用 OR 逻辑，
        # 全量注入会导致所有卖出条件在 sell_bar 上都显示为 True（不正确）。
        # 卖出条件的 passed 值完全由 eval_exit() 精确评估决定。
        injected_buy = 0
        injected_sell = 0
        try:
            for dt_str in ((buy_dates or []) if inject_buy_signals else []):
                bar_idx = self._find_bar_index_by_dt_str(bars, dt_str)
                if bar_idx is None:
                    print(
                        f"[MonitorEngine.inject] {symbol} buy_date {dt_str!r} "
                        f"未匹配到 bar (可能在 warmup 区间或区间外)"
                    )
                    continue
                hit = 0
                for snap in snapshots:
                    if snap.bar_index == bar_idx:
                        for d in snap.buy_details:
                            d.passed = True
                        hit += 1
                if hit == 0:
                    print(
                        f"[MonitorEngine.inject] {symbol} buy bar_index={bar_idx} "
                        f"({dt_str}) 未命中任何 snapshot (snapshot 范围 "
                        f"[{snapshots[0].bar_index}, {snapshots[-1].bar_index}])"
                    )
                else:
                    injected_buy += 1
                    print(
                        f"[MonitorEngine.inject] {symbol} BUY {dt_str} -> "
                        f"bar_index={bar_idx}, 标记 {hit} 个 snapshot.buy_details[*].passed=True"
                    )
        except Exception as e:
            # 注入阶段不应阻塞主流程
            print(f"[MonitorEngine.inject] {symbol} 信号注入异常: {e!r}")

        if injected_buy or injected_sell:
            print(
                f"[MonitorEngine.inject] {symbol} 注入完成: "
                f"buy={injected_buy}, sell={injected_sell}"
            )
        # ── 注入结束 ────────────────────────────────────────────────────

        return snapshots

    def _build_position_tracker(
        self,
        bars: list,
        buy_dates: List[str],
        sell_dates: List[str],
    ) -> Dict[int, Dict[str, Any]]:
        """
        根据回测的买卖信号时间列表，为每根 K 线构建持仓上下文。

        Returns:
            {bar_index: {"entry_price": float, "peak_price": float, "hold_bars": int}}
            空字典表示该 bar 无持仓。
        """
        if not buy_dates:
            return {}

        # 将 buy_dates / sell_dates 匹配到 bar 索引
        # 支持格式："YYYY-MM-DD" 或 "YYYY-MM-DD HH:MM"
        buy_indices: List[int] = []
        sell_indices: List[int] = []

        for dt_str in buy_dates:
            idx = self._find_bar_index_by_dt_str(bars, dt_str)
            if idx is not None:
                buy_indices.append(idx)

        for dt_str in sell_dates:
            idx = self._find_bar_index_by_dt_str(bars, dt_str)
            if idx is not None:
                sell_indices.append(idx)

        # 配对买卖信号，构建持仓区间
        # 按索引排序
        buy_indices.sort()
        sell_indices.sort()

        # 建立持仓上下文映射
        tracker: Dict[int, Dict[str, Any]] = {}

        for buy_idx in buy_indices:
            # 找对应的卖出索引（第一个 > buy_idx 的 sell_idx）
            sell_idx = None
            for si in sell_indices:
                if si > buy_idx:
                    sell_idx = si
                    break

            entry_price = bars[buy_idx].close
            peak_price = entry_price

            # 获取买入 bar 的交易日期（用于 T+1 判断）
            buy_bar_dt = getattr(bars[buy_idx], "dt", None)
            buy_trade_date = buy_bar_dt.date() if buy_bar_dt else None

            # 持仓区间：从 buy_idx 到 sell_idx（含）
            end_idx = sell_idx if sell_idx is not None else len(bars) - 1
            for j in range(buy_idx, end_idx + 1):
                cur_price = bars[j].close
                if cur_price > peak_price:
                    peak_price = cur_price

                # T+1 判断：当前 bar 是否与买入在同一交易日
                cur_bar_dt = getattr(bars[j], "dt", None)
                cur_trade_date = cur_bar_dt.date() if cur_bar_dt else None
                t1_protected = (
                    buy_trade_date is not None
                    and cur_trade_date is not None
                    and cur_trade_date == buy_trade_date
                )

                tracker[j] = {
                    "entry_price": entry_price,
                    "peak_price": peak_price,
                    "hold_bars": j - buy_idx,
                    "t1_protected": t1_protected,
                }

        return tracker

    @staticmethod
    def _find_bar_index_by_dt_str(bars: list, dt_str: str) -> Optional[int]:
        """将日期字符串匹配到 bars 中最近的 bar 索引"""
        if not dt_str or not bars:
            return None
        # 尝试解析时间字符串
        dt_str = dt_str.strip()
        target_dt = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                target_dt = datetime.strptime(dt_str, fmt)
                break
            except ValueError:
                continue
        if target_dt is None:
            return None

        # 统一为 naive datetime，避免 offset-naive vs offset-aware 报 TypeError
        # bar 可能是 _BarAdapter 包装后有 tz 的 BarData
        if target_dt.tzinfo is not None:
            target_dt = target_dt.replace(tzinfo=None)
        # 精确匹配或最近匹配
        best_idx = None
        best_diff = float("inf")
        for i, bar in enumerate(bars):
            bar_dt = getattr(bar, "dt", None)
            if bar_dt is None:
                continue
            # 统一到 naive 再做差
            if bar_dt.tzinfo is not None:
                bar_dt = bar_dt.replace(tzinfo=None)
            diff = abs((bar_dt - target_dt).total_seconds())
            if diff < best_diff:
                best_diff = diff
                best_idx = i
            # 精确匹配直接返回
            if diff == 0:
                return i
        # 容忍1分钟内的误差
        if best_diff <= 60:
            return best_idx
        return best_idx  # 仍返回最近的

    def get_snapshot_at(self, symbol: str, bar_index: int) -> Optional[ConditionSnapshot]:
        """
        获取指定 symbol 在 bar_index 位置的快照。
        用于K线光标联动：移动光标时直接读缓存，不重新计算。
        """
        snapshots = self._cache.get(symbol, [])
        for snap in snapshots:
            if snap.bar_index == bar_index:
                return snap
        return None

    def get_snapshot_by_dt(self, symbol: str, dt: datetime) -> Optional[ConditionSnapshot]:
        """按时间查找最接近的快照"""
        snapshots = self._cache.get(symbol, [])
        if not snapshots:
            return None
        # 精确匹配
        for snap in snapshots:
            if snap.dt == dt:
                return snap
        # 找最近的
        best = min(snapshots, key=lambda s: abs((s.dt - dt).total_seconds()))
        return best

    def get_all_snapshots(self, symbol: str) -> List[ConditionSnapshot]:
        """获取某股票全部缓存快照"""
        return self._cache.get(symbol, [])

    def get_state_changes(self, symbol: str) -> List[StateChangeEvent]:
        """获取某股票全部条件状态变化事件"""
        return self._changes_cache.get(symbol, [])

    def get_heatmap_data(self, symbol: str) -> Dict[str, Any]:
        """
        获取条件热力图数据。

        Returns:
            {
                "dates": [datetime, ...],
                "conditions": ["MA突破", "量比确认", ...],
                "matrix": [[True/False, ...], ...]  # dates x conditions
            }
        """
        snapshots = self._cache.get(symbol, [])
        if not snapshots:
            return {"dates": [], "conditions": [], "matrix": []}

        # 收集所有条件名
        cond_names: List[str] = []
        if snapshots[0].buy_details:
            cond_names = [d.condition_name for d in snapshots[0].buy_details]

        dates = [s.dt for s in snapshots]
        matrix: List[List[bool]] = []
        for snap in snapshots:
            row = [d.passed for d in snap.buy_details]
            matrix.append(row)

        return {
            "dates": dates,
            "conditions": cond_names,
            "matrix": matrix,
        }

    def get_condition_stats(self, symbol: str) -> Dict[str, Dict[str, Any]]:
        """
        获取各条件的统计信息。

        Returns:
            {
                "MA突破": {
                    "pass_rate": 0.65,
                    "total_bars": 200,
                    "passed_bars": 130,
                    "avg_score": 0.72,
                },
                ...
            }
        """
        snapshots = self._cache.get(symbol, [])
        if not snapshots:
            return {}

        stats: Dict[str, Dict[str, Any]] = {}
        for snap in snapshots:
            for detail in snap.buy_details + snap.sell_details:
                name = detail.condition_name
                if name not in stats:
                    stats[name] = {
                        "pass_rate": 0.0,
                        "total_bars": 0,
                        "passed_bars": 0,
                        "total_score": 0.0,
                    }
                stats[name]["total_bars"] += 1
                if detail.passed:
                    stats[name]["passed_bars"] += 1
                stats[name]["total_score"] += detail.score

        for name, s in stats.items():
            total = s["total_bars"]
            s["pass_rate"] = round(s["passed_bars"] / total, 4) if total > 0 else 0.0
            s["avg_score"] = round(s["total_score"] / total, 4) if total > 0 else 0.0
            del s["total_score"]

        return stats

    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """清除缓存"""
        if symbol:
            self._cache.pop(symbol, None)
            self._changes_cache.pop(symbol, None)
        else:
            self._cache.clear()
            self._changes_cache.clear()

    # ── 内部模拟卖出 ─────────────────────────────────────────────────

    def _find_unmatched_buys(
        self,
        bars: list,
        buy_dates: List[str],
        sell_dates: List[str],
    ) -> List[str]:
        """
        找出没有对应后续卖出的买入日期。

        逻辑：按时间排序后，每个 buy 尝试匹配第一个在它之后的 sell。
        未被匹配到的 buy 即为"未配对买入"。
        """
        buy_indices: List[Tuple[int, str]] = []
        sell_indices: List[int] = []

        for dt_str in buy_dates:
            idx = self._find_bar_index_by_dt_str(bars, dt_str)
            if idx is not None:
                buy_indices.append((idx, dt_str))

        for dt_str in sell_dates:
            idx = self._find_bar_index_by_dt_str(bars, dt_str)
            if idx is not None:
                sell_indices.append(idx)

        buy_indices.sort(key=lambda x: x[0])
        sell_indices.sort()

        # 贪心配对：每个 buy 找第一个 > buy_idx 的 sell
        used_sells = set()
        unmatched: List[str] = []

        for buy_idx, buy_dt_str in buy_indices:
            matched = False
            for si in sell_indices:
                if si > buy_idx and si not in used_sells:
                    used_sells.add(si)
                    matched = True
                    break
            if not matched:
                unmatched.append(buy_dt_str)

        return unmatched

    def _simulate_sell_dates(
        self,
        symbol: str,
        bars: list,
        strategy: Strategy,
        buy_dates: List[str],
        warmup: int,
    ) -> List[str]:
        """
        当外部未提供 sell_dates 时，内部逐 bar 模拟卖出。
        每个买入点后，顺序评估 sell_tree，第一次 sell=True 即为卖出点。
        保证"一买一卖"配对。
        """
        n = len(bars)
        simulated_sells: List[str] = []

        # 找到所有 buy bar indices
        buy_indices: List[int] = []
        for dt_str in buy_dates:
            idx = self._find_bar_index_by_dt_str(bars, dt_str)
            if idx is not None:
                buy_indices.append(idx)
        buy_indices.sort()

        for buy_idx in buy_indices:
            entry_price = bars[buy_idx].close
            peak_price = entry_price
            buy_bar_dt = getattr(bars[buy_idx], "dt", None)
            buy_trade_date = buy_bar_dt.date() if buy_bar_dt else None

            sold = False
            # 从 buy_idx+1 开始评估（当天不可卖，T+1）
            for j in range(buy_idx + 1, n):
                cur_bar = bars[j]
                cur_price = cur_bar.close
                if cur_price > peak_price:
                    peak_price = cur_price

                # T+1 检查
                cur_bar_dt = getattr(cur_bar, "dt", None)
                cur_trade_date = cur_bar_dt.date() if cur_bar_dt else None
                if (buy_trade_date and cur_trade_date
                        and cur_trade_date == buy_trade_date):
                    continue  # 买入当天不可卖

                hold_bars = j - buy_idx
                bars_slice = bars[:j + 1]

                # 使用 eval_exit 评估卖出条件
                sell_eval_fn = self._make_simple_exit_eval_fn(
                    bars_slice, entry_price, cur_price, peak_price,
                    hold_bars, strategy.params)

                sell_passed, _ = strategy.sell_tree.evaluate(
                    symbol, bars_slice, sell_eval_fn)

                if sell_passed:
                    # 记录卖出时间
                    dt = getattr(cur_bar, "dt", None)
                    if dt:
                        if dt.hour == 0 and dt.minute == 0:
                            sell_str = dt.strftime("%Y-%m-%d")
                        else:
                            sell_str = dt.strftime("%Y-%m-%d %H:%M")
                        simulated_sells.append(sell_str)
                    sold = True
                    break

            # 如果卖了，后续 buy 不能在 sell 之前（按时间序已排序，直接跳过）

        return simulated_sells

    def _make_simple_exit_eval_fn(
        self,
        bars_slice: list,
        entry_price: float,
        cur_price: float,
        peak_price: float,
        hold_bars: int,
        sp=None,
    ) -> Callable[[Condition, str, list], Tuple[bool, float]]:
        """
        简化的卖出评估函数（不记录详情，仅判断 pass/fail）。
        
        注意：与 Monitor 波形显示不同，模拟卖出拥有精确的持仓上下文
        （entry_price, peak_price, hold_bars），所以所有卖出条件
        统一走 eval_exit，使用真实持仓数据判断，不走近似。
        """
        def eval_fn(cond: Condition, symbol: str, bars: list) -> Tuple[bool, float]:
            # 模拟卖出时所有退出条件统一用 eval_exit（有精确持仓上下文）
            return self._ce.eval_exit(
                cond, entry_price, cur_price, peak_price, hold_bars, bars, sp)
        return eval_fn

    # ── 内部实现 ──────────────────────────────────────────────────────

    def _evaluate_bar(
        self,
        symbol: str,
        bars_slice: list,
        bar_index: int,
        strategy: Strategy,
        pos_ctx: Optional[Dict[str, Any]] = None,
    ) -> ConditionSnapshot:
        """
        对单根K线（截至 bar_index）生成完整的 ConditionSnapshot。

        Args:
            pos_ctx: 持仓上下文，如果当前处于持仓状态则包含：
                     {"entry_price", "peak_price", "hold_bars"}
                     为 None 时表示当前无持仓。
        """
        last_bar = bars_slice[-1]
        dt = getattr(last_bar, "dt", datetime.now())
        price = last_bar.close

        # 买入条件评估（带记录）
        buy_recorder: Dict[str, ConditionDetail] = {}
        buy_eval_fn = self._make_recording_eval_fn(buy_recorder, bars_slice)
        buy_passed, buy_score = strategy.buy_tree.evaluate(
            symbol, bars_slice, buy_eval_fn
        )
        buy_details = list(buy_recorder.values())
        buy_passed_count = sum(1 for d in buy_details if d.passed)

        # 卖出条件评估（带记录）
        sell_recorder: Dict[str, ConditionDetail] = {}
        if pos_ctx is not None and not pos_ctx.get("t1_protected", False):
            # 有持仓且已过T+1保护期：使用 eval_exit 正确评估卖出条件
            sell_eval_fn = self._make_recording_exit_eval_fn(
                sell_recorder, bars_slice,
                entry_price=pos_ctx["entry_price"],
                cur_price=price,
                peak_price=pos_ctx["peak_price"],
                hold_bars=pos_ctx["hold_bars"],
                sp=strategy.params,
            )
        else:
            # 无持仓 或 T+1保护期内（买入当天不可卖出）：
            # 卖出条件全部标记为 False
            sell_eval_fn = self._make_recording_no_position_fn(
                sell_recorder, bars_slice)

        sell_passed, sell_score = strategy.sell_tree.evaluate(
            symbol, bars_slice, sell_eval_fn
        )
        sell_details = list(sell_recorder.values())
        sell_passed_count = sum(1 for d in sell_details if d.passed)

        # 判断信号类型
        signal_type: Optional[str] = None
        if buy_passed:
            signal_type = "BUY"
        elif sell_passed and pos_ctx is not None and not pos_ctx.get("t1_protected", False):
            # 卖出信号仅在同时满足三个条件时才成立：
            #   1. sell_tree 评估通过 (sell_passed=True)
            #   2. 当前在持仓段内 (pos_ctx is not None)
            #   3. 已过 A 股 T+1 保护期 (not t1_protected)
            signal_type = "SELL"

        # ── 构建 Sell Signal Lifecycle 诊断 ──────────────────────
        sell_lifecycles = self._build_sell_lifecycles(
            symbol=symbol,
            bar_index=bar_index,
            dt=dt,
            price=price,
            sell_details=sell_details,
            pos_ctx=pos_ctx,
            buy_passed=buy_passed,
        )
        # 聚合摘要
        sell_signal_created = any(lc.signal.signal_created for lc in sell_lifecycles)
        sell_decision_result: Optional[str] = None
        sell_reject_reason: Optional[str] = None
        if sell_signal_created:
            # 取第一个有信号的 lifecycle 的 decision
            for lc in sell_lifecycles:
                if lc.signal.signal_created:
                    sell_decision_result = lc.decision.result.value
                    if lc.decision.result == DecisionResult.REJECTED:
                        sell_reject_reason = lc.decision.reject_description
                    break

        return ConditionSnapshot(
            dt=dt,
            symbol=symbol,
            price=price,
            bar_index=bar_index,
            buy_details=buy_details,
            sell_details=sell_details,
            buy_passed_count=buy_passed_count,
            buy_total_count=len(buy_details),
            buy_result=buy_passed,
            buy_score=buy_score,
            sell_passed_count=sell_passed_count,
            sell_total_count=len(sell_details),
            sell_result=sell_passed,
            sell_score=sell_score,
            signal_type=signal_type,
            sell_lifecycles=sell_lifecycles,
            sell_signal_created=sell_signal_created,
            sell_decision_result=sell_decision_result,
            sell_reject_reason=sell_reject_reason,
        )

    def _make_recording_eval_fn(
        self,
        recorder: Dict[str, ConditionDetail],
        bars_slice: list,
    ) -> Callable[[Condition, str, list], Tuple[bool, float]]:
        """
        创建代理 eval_fn：在调用原始 ConditionEngine 评估的同时，
        记录每个叶节点条件的详细结果到 recorder。
        """
        original_eval = self._ce.eval_condition

        def recording_eval(cond: Condition, symbol: str, bars: list) -> Tuple[bool, float]:
            passed, score = original_eval(cond, symbol, bars)
            # 提取当前值和阈值描述
            current_value = self._extract_current_value(cond, bars_slice)
            threshold_desc = self._format_threshold(cond)
            detail = ConditionDetail(
                condition_name=cond.display_name(),
                indicator=cond.indicator.value,
                passed=passed,
                score=score,
                current_value=current_value,
                threshold_desc=threshold_desc,
                params=dict(cond.params),
            )
            recorder[cond.display_name()] = detail
            return passed, score

        return recording_eval

    def _extract_current_value(self, cond: Condition, bars: list) -> Optional[float]:
        """
        从K线数据中提取条件相关的当前指标值。
        尽可能提供有意义的数值（如 MA值、RSI值、量比等）。
        """
        if not bars:
            return None

        closes = [b.close for b in bars]
        volumes = [float(b.volume) for b in bars]
        p = cond.params
        ind = cond.indicator.value

        try:
            # 均线相关
            if ind in ("MA_SLOPE", "WEEKLY_MA_SLOPE", "MA_ALIGNMENT",
                       "PRICE_ABOVE_MA", "MA_BREAK_DOWN"):
                period = int(p.get("ma_period", 20))
                if len(closes) >= period:
                    ma = sum(closes[-period:]) / period
                    return round(ma, 4)

            # RSI
            if ind == "RSI_RANGE":
                period = int(p.get("period", 14))
                if len(closes) > period:
                    return round(self._calc_rsi(closes, period), 2)

            # 量比
            if ind in ("VOLUME_RATIO", "VOLUME_PRICE_UP", "VOLUME_SHRINK"):
                period = int(p.get("period", 20))
                if len(volumes) >= period and period > 0:
                    avg_vol = sum(volumes[-period:]) / period
                    if avg_vol > 0:
                        return round(volumes[-1] / avg_vol, 2)

            # 收益率
            if ind == "RETURN_N_DAYS":
                n = int(p.get("n", 10))
                if len(closes) > n and closes[-n - 1] > 0:
                    ret = (closes[-1] - closes[-n - 1]) / closes[-n - 1] * 100
                    return round(ret, 2)

            # 止损止盈（返回当前收益率）
            if ind in ("STOP_LOSS", "TAKE_PROFIT", "TRAILING_STOP"):
                return round(closes[-1], 4)

            # 通用：返回最新收盘价
            return round(closes[-1], 4)

        except Exception:
            return None

    @staticmethod
    def _calc_rsi(closes: list, period: int = 14) -> float:
        """计算 RSI 值"""
        if len(closes) <= period:
            return 50.0
        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _format_threshold(cond: Condition) -> str:
        """格式化条件阈值为人类可读的描述文字"""
        p = cond.params
        ind = cond.indicator.value

        if ind == "MA_SLOPE":
            return f"斜率 > {p.get('min_slope', 0.0)}"
        if ind == "MA_ALIGNMENT":
            periods = p.get("periods", [5, 10, 20, 60])
            return f"MA{'<'.join(str(x) for x in periods)} 多头排列"
        if ind == "RSI_RANGE":
            return f"RSI ∈ [{p.get('min', 30)}, {p.get('max', 70)}]"
        if ind == "VOLUME_RATIO":
            return f"量比 >= {p.get('min_ratio', 1.5)}x"
        if ind == "VOLUME_SHRINK":
            return f"量比 <= {p.get('max_ratio', 0.7)}x"
        if ind == "RETURN_N_DAYS":
            return f"{p.get('n', 10)}日收益 >= {p.get('min_return', 5)}%"
        if ind == "STOP_LOSS":
            return f"跌幅 >= {p.get('pct', 8)}%"
        if ind == "TAKE_PROFIT":
            return f"涨幅 >= {p.get('pct', 15)}%"
        if ind == "TRAILING_STOP":
            return f"盈利>{p.get('take_profit', 15)}%后回撤{p.get('trail_drawdown', 10)}%"
        if ind == "MAX_HOLD_DAYS":
            return f"持仓 >= {p.get('days', 60)}天"
        if ind == "MA_BREAK_DOWN":
            return f"收盘价 < MA{p.get('ma_period', 20)}"
        if ind == "NEW_HIGH_N":
            return f"{p.get('n', 20)}日新高"
        if ind in ("PULLBACK_PCT", "PULLBACK_FROM_HIGH"):
            return f"回调 {p.get('min_drop', -8)}% ~ {p.get('max_drop', -2)}%"
        if ind == "PULLBACK_TO_MA":
            return f"回踩 MA{p.get('ma_period', 20)}"
        if ind == "MACD_GOLDEN":
            return "MACD DIF 上穿 DEA"
        if ind == "MACD_DEATH":
            return "MACD DIF 下穿 DEA"
        if ind == "CONTINUOUS_RISE":
            return f"连涨 >= {p.get('min_days', 3)}天"
        if ind == "VOLUME_PRICE_UP":
            return f"放量上涨 > {p.get('min_chg', 1)}%"

        # 通用回退
        return str(p) if p else ""

    def _detect_state_changes(
        self, snapshots: List[ConditionSnapshot]
    ) -> List[StateChangeEvent]:
        """
        遍历快照序列，检测每个条件的状态翻转事件。
        """
        if len(snapshots) < 2:
            return []

        changes: List[StateChangeEvent] = []

        for i in range(1, len(snapshots)):
            prev = snapshots[i - 1]
            curr = snapshots[i]

            # 检测买入条件变化
            prev_buy_map = {d.condition_name: d.passed for d in prev.buy_details}
            for detail in curr.buy_details:
                old = prev_buy_map.get(detail.condition_name)
                if old is not None and old != detail.passed:
                    changes.append(StateChangeEvent(
                        dt=curr.dt,
                        bar_index=curr.bar_index,
                        condition_name=detail.condition_name,
                        indicator=detail.indicator,
                        old_state=old,
                        new_state=detail.passed,
                        side="buy",
                    ))

            # 检测卖出条件变化
            prev_sell_map = {d.condition_name: d.passed for d in prev.sell_details}
            for detail in curr.sell_details:
                old = prev_sell_map.get(detail.condition_name)
                if old is not None and old != detail.passed:
                    changes.append(StateChangeEvent(
                        dt=curr.dt,
                        bar_index=curr.bar_index,
                        condition_name=detail.condition_name,
                        indicator=detail.indicator,
                        old_state=old,
                        new_state=detail.passed,
                        side="sell",
                    ))

        return changes

    def _make_recording_exit_eval_fn(
        self,
        recorder: Dict[str, ConditionDetail],
        bars_slice: list,
        entry_price: float,
        cur_price: float,
        peak_price: float,
        hold_bars: int,
        sp=None,
    ) -> Callable[[Condition, str, list], Tuple[bool, float]]:
        """
        创建带持仓上下文的卖出条件评估代理。

        关键原则（参数统一）：
          持仓段内，ALL 卖出条件统一走 eval_exit，使用真实的
          entry_price / peak_price / hold_bars，与回测引擎逻辑完全一致。
          这确保 Monitor 波形和回测结果的触发时机严格对齐。

          "纯技术面近似"（eval_condition）仅在无持仓时使用
          （见 _make_recording_no_position_fn），用于展示波形趋势。
        """
        def recording_exit_eval(cond: Condition, symbol: str, bars: list) -> Tuple[bool, float]:
            # 持仓段内：所有卖出条件统一走 eval_exit（与回测一致）
            passed, score = self._ce.eval_exit(
                cond, entry_price, cur_price, peak_price, hold_bars, bars, sp)
            # 展示当前收益率（比裸价格更有诊断意义）
            current_value = round(
                (cur_price - entry_price) / entry_price * 100, 2
            ) if entry_price > 0 else 0.0

            threshold_desc = self._format_threshold(cond)
            detail = ConditionDetail(
                condition_name=cond.display_name(),
                indicator=cond.indicator.value,
                passed=passed,
                score=score,
                current_value=current_value,
                threshold_desc=threshold_desc,
                params=dict(cond.params),
            )
            recorder[cond.display_name()] = detail
            return passed, score

        return recording_exit_eval

    def _make_recording_no_position_fn(
        self,
        recorder: Dict[str, ConditionDetail],
        bars_slice: list,
    ) -> Callable[[Condition, str, list], Tuple[bool, float]]:
        """
        无持仓（或 T+1 保护期）时的卖出条件评估代理。

        分派规则：
          - 纯技术面卖出条件：依然独立评估（走 eval_condition），
              这样"跌破 MA20 / MACD 死叉"波形在无持仓区间也能正常展示。
          - 持仓依赖卖出条件：无持仓上下文，一律返回 False。
        """
        def no_position_eval(cond: Condition, symbol: str, bars: list) -> Tuple[bool, float]:
            threshold_desc = self._format_threshold(cond)
            if cond.indicator in _PURE_TECHNICAL_EXIT_INDICATORS:
                passed, score = self._ce.eval_condition(cond, symbol, bars)
                current_value = self._extract_current_value(cond, bars_slice)
            else:
                passed, score = False, 0.0
                current_value = None
            detail = ConditionDetail(
                condition_name=cond.display_name(),
                indicator=cond.indicator.value,
                passed=passed,
                score=score,
                current_value=current_value,
                threshold_desc=threshold_desc,
                params=dict(cond.params),
            )
            recorder[cond.display_name()] = detail
            return passed, score

        return no_position_eval

    # ── Sell Signal Lifecycle 构建 ────────────────────────────────────

    def _build_sell_lifecycles(
        self,
        symbol: str,
        bar_index: int,
        dt: datetime,
        price: float,
        sell_details: List[ConditionDetail],
        pos_ctx: Optional[Dict[str, Any]],
        buy_passed: bool,
    ) -> List[SellSignalLifecycle]:
        """
        根据卖出条件评估结果和持仓上下文，构建每个卖出条件的完整生命周期。

        生命周期流转：
          1. Condition: 条件是否满足（从 sell_details 获取）
          2. Signal: 条件满足 + 有持仓 → 产生信号
          3. Decision: T+1 / 冷却期 / 冲突 检查
          4. Execution: 由外部回填（此处不处理）
        """
        lifecycles: List[SellSignalLifecycle] = []

        has_position = pos_ctx is not None
        entry_price = pos_ctx["entry_price"] if pos_ctx else 0.0
        peak_price = pos_ctx["peak_price"] if pos_ctx else 0.0
        hold_bars = pos_ctx["hold_bars"] if pos_ctx else 0
        t1_protected = pos_ctx.get("t1_protected", False) if pos_ctx else False

        for detail in sell_details:
            # ── Layer 1: Condition ──
            cond_layer = ConditionLayerResult(
                condition_name=detail.condition_name,
                indicator=detail.indicator,
                triggered=detail.passed,
                score=detail.score,
                trigger_time=dt if detail.passed else None,
                context={
                    "current_value": detail.current_value,
                    "threshold": detail.threshold_desc,
                    "params": detail.params,
                    "entry_price": round(entry_price, 4) if has_position else None,
                    "peak_price": round(peak_price, 4) if has_position else None,
                    "current_price": round(price, 4),
                    "hold_bars": hold_bars if has_position else None,
                },
            )

            # ── Layer 2: Signal ──
            signal_layer = SignalLayerResult()
            if detail.passed and has_position:
                signal_layer.signal_created = True
                signal_layer.signal_source = detail.condition_name
                signal_layer.signal_time = dt

            # ── Layer 3: Decision ──
            decision_layer = DecisionLayerResult()
            if signal_layer.signal_created:
                checks: List[DecisionCheck] = []

                # Check 1: T+1 保护
                t1_check = DecisionCheck(
                    check_name="T+1保护",
                    passed=not t1_protected,
                    description="买入当日不可卖出" if t1_protected else "已过T+1保护期",
                )
                checks.append(t1_check)

                # Check 2: 买卖冲突
                conflict_check = DecisionCheck(
                    check_name="买卖冲突",
                    passed=not buy_passed,
                    description="买卖信号同时触发，跳过卖出" if buy_passed else "无冲突",
                )
                checks.append(conflict_check)

                # Check 3: 持仓确认（冗余确认，正常流程下 has_position 已保证）
                position_check = DecisionCheck(
                    check_name="持仓确认",
                    passed=True,
                    description=f"持仓中，入场价{entry_price:.2f}",
                )
                checks.append(position_check)

                decision_layer.checks = checks

                # 判定最终结果
                if not t1_check.passed:
                    decision_layer.result = DecisionResult.REJECTED
                    decision_layer.reject_reason = RejectReason.T1_LOCK
                    decision_layer.reject_description = "T+1当日锁定，无法卖出"
                elif not conflict_check.passed:
                    decision_layer.result = DecisionResult.REJECTED
                    decision_layer.reject_reason = RejectReason.CONFLICT
                    decision_layer.reject_description = "买卖信号冲突，优先跳过卖出"
                else:
                    decision_layer.result = DecisionResult.APPROVED
                    decision_layer.reject_reason = RejectReason.NONE
                    decision_layer.reject_description = ""

            # ── Layer 4: Execution（由外部回填） ──
            execution_layer = ExecutionLayerResult()

            # ── 组装 Lifecycle ──
            lc = SellSignalLifecycle(
                symbol=symbol,
                bar_index=bar_index,
                dt=dt,
                has_position=has_position,
                entry_price=entry_price,
                entry_time=None,  # 可从 pos_ctx 扩展
                peak_price=peak_price,
                hold_bars=hold_bars,
                condition=cond_layer,
                signal=signal_layer,
                decision=decision_layer,
                execution=execution_layer,
            )
            lifecycles.append(lc)

        return lifecycles
