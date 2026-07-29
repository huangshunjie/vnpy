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

from ..core.condition import Condition
from ..core.condition_tree import ConditionNode
from ..core.strategy import Strategy
from ..engine.condition_engine import ConditionEngine
from .condition_snapshot import ConditionDetail, ConditionSnapshot, StateChangeEvent


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

    # ── 公开接口 ──────────────────────────────────────────────────────

    def generate_snapshots(
        self,
        symbol: str,
        bars: list,
        strategy: Strategy,
        warmup: int = 60,
    ) -> List[ConditionSnapshot]:
        """
        为指定股票的K线序列生成全部 ConditionSnapshot。

        Args:
            symbol: 股票代码
            bars: 完整K线序列（已排序）
            strategy: 当前策略（含 buy_tree / sell_tree）
            warmup: 预热K线数（前 warmup 根不生成快照）

        Returns:
            生成的 ConditionSnapshot 列表
        """
        snapshots: List[ConditionSnapshot] = []
        n = len(bars)
        start = max(warmup, 1)

        for i in range(start, n):
            bars_slice = bars[:i + 1]
            snapshot = self._evaluate_bar(symbol, bars_slice, i, strategy)
            snapshots.append(snapshot)

        # 更新缓存
        self._cache[symbol] = snapshots[-self.MAX_CACHE_SIZE:]

        # 生成状态变化事件
        self._changes_cache[symbol] = self._detect_state_changes(snapshots)

        self._log(
            f"[MonitorEngine] {symbol}: 生成 {len(snapshots)} 个快照, "
            f"{len(self._changes_cache[symbol])} 个状态变化事件"
        )
        return snapshots

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

    # ── 内部实现 ──────────────────────────────────────────────────────

    def _evaluate_bar(
        self,
        symbol: str,
        bars_slice: list,
        bar_index: int,
        strategy: Strategy,
    ) -> ConditionSnapshot:
        """对单根K线（截至 bar_index）生成完整的 ConditionSnapshot"""
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
        sell_eval_fn = self._make_recording_eval_fn(sell_recorder, bars_slice)
        sell_passed, sell_score = strategy.sell_tree.evaluate(
            symbol, bars_slice, sell_eval_fn
        )
        sell_details = list(sell_recorder.values())

        sell_passed_count = sum(1 for d in sell_details if d.passed)

        # 判断信号类型
        signal_type: Optional[str] = None
        if buy_passed:
            signal_type = "BUY"
        elif sell_passed:
            signal_type = "SELL"

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