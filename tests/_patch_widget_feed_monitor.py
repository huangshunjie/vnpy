# -*- coding: utf-8 -*-
"""
Apply monitor dual-period patch to widget.py
重写 _feed_monitor、添加 _load_minute_bars_for_monitor、_minute_key_to_interval、
_on_monitor_minute_interval_changed 三个辅助方法。
"""
import io
from pathlib import Path

target = Path("vnpy/strategy_condition/ui/widget.py")
content = target.read_text(encoding="utf-8")

# ─── Patch 1: 替换 _feed_monitor 方法体（保留方法签名）───
old_method = '''    def _feed_monitor(self, symbol: str,
                      buy_dates: list = None,
                      sell_dates: list = None) -> None:
        """
        为指定股票生成条件监控快照并加载到 Monitor Tab。
        内置两层缓存：
          1. 如果 (symbol, strategy_hash, buy_dates, sell_dates) 命中缓存，
             直接从缓存加载渲染，0 延迟。
          2. 否则执行完整计算，结果存入缓存。
        """
        if self._monitor_tab is None:
            return
        if not self._strategy:
            return

        # ── 缓存 key ──
        buy_dates = buy_dates or []
        sell_dates = sell_dates or []
        cache_key = (
            symbol,
            self._strategy_hash(),
            tuple(buy_dates),
            tuple(sell_dates),
        )

        # ── 缓存命中：直接渲染 ──
        cached = self._snapshot_cache.get(cache_key)
        if cached is not None:
            snapshots, bars = cached
            print(
                f"[SCE] Monitor 缓存命中 {symbol} "
                f"({len(snapshots)} snapshots, {len(bars)} bars)",
                flush=True,
            )
            self._monitor_tab.load_snapshots(
                symbol, snapshots,
                bars=bars,
                buy_dates=buy_dates,
                sell_dates=sell_dates,
            )
            self._monitor_dirty = False
            return

        # ── 缓存未命中：计算快照 ──
        print(f"[SCE] _feed_monitor: computing for {symbol}", flush=True)
        try:
            n_bars = self._nbars_sp.value()

            # 优先复用 Chart Tab 已加载的原始 bars
            chart_raw_bars = getattr(self._kline_tab, '_last_raw_bars', None)
            if chart_raw_bars and len(chart_raw_bars) > 0:
                bars = [_BarAdapter(b) for b in chart_raw_bars]
            else:
                bars_dict = self._load_bars([symbol], n_bars)
                bars = bars_dict.get(symbol, [])

            if not bars:
                print(f"[SCE] _feed_monitor: no bars for {symbol}")
                return

            from ..monitor.condition_monitor_engine import ConditionMonitorEngine
            from ..engine.condition_engine import ConditionEngine
            ce = ConditionEngine()
            monitor_eng = ConditionMonitorEngine(ce)

            if len(bars) >= 200:
                monitor_warmup = 60
            elif len(bars) >= 100:
                monitor_warmup = 30
            else:
                monitor_warmup = min(10, max(1, len(bars) // 4))

            snapshots = monitor_eng.generate_snapshots(
                symbol=symbol,
                bars=bars,
                strategy=self._strategy,
                warmup=monitor_warmup,
                buy_dates=buy_dates,
                sell_dates=sell_dates,
            )
            print(
                f"[SCE] _feed_monitor: {len(snapshots)} snapshots "
                f"(warmup={monitor_warmup})",
                flush=True,
            )

            # 回测结果的卖出日期是权威来源
            effective_sell_dates = sell_dates

            # ── 存入缓存 ──
            self._snapshot_cache[cache_key] = (snapshots, bars)
            self._snapshot_cache_key = cache_key

            self._monitor_tab.load_snapshots(
                symbol, snapshots,
                bars=bars,
                buy_dates=buy_dates,
                sell_dates=effective_sell_dates,
            )
            self._monitor_dirty = False
            print(f"[SCE] _feed_monitor: done, cached", flush=True)
        except Exception as e:
            import traceback
            print(f"[SCE] Monitor 快照生成失败: {e}")
            traceback.print_exc()'''

new_method = '''    def _feed_monitor(self, symbol: str,
                      buy_dates: list = None,
                      sell_dates: list = None) -> None:
        """
        为指定股票生成条件监控快照并加载到 Monitor Tab（双周期）。

        内置缓存：
          1. 缓存键 = (symbol, strategy_hash, buy_dates, sell_dates, minute_key)
          2. 命中 → 直接 load_layered_data，0 延迟
          3. 未命中 → 加载日线 + 分钟线 + 各自生成 snapshots，存入缓存

        加载层级：
          - 日线 bars  + daily snapshots  → _daily_panel
          - 分钟线 bars + minute snapshots → _minute_panel
          - 调用 _monitor_tab.load_layered_data(...) 一推双面板
        """
        if self._monitor_tab is None:
            return
        if not self._strategy:
            return

        # ── 缓存 key（考虑分钟周期，保证切换 5m/15m 后不命中旧 cache）──
        buy_dates = buy_dates or []
        sell_dates = sell_dates or []
        minute_key = self._monitor_tab.minute_interval_key()
        cache_key = (
            symbol,
            self._strategy_hash(),
            tuple(buy_dates),
            tuple(sell_dates),
            minute_key,
        )

        # ── 缓存命中：直接渲染 ──
        cached = self._snapshot_cache.get(cache_key)
        if cached is not None:
            (daily_snapshots, daily_bars,
             minute_snapshots, minute_bars) = cached
            print(
                f"[SCE] Monitor 缓存命中 {symbol} ({minute_key}) "
                f"daily={len(daily_bars)}/{len(daily_snapshots)}, "
                f"minute={len(minute_bars)}/{len(minute_snapshots)}",
                flush=True,
            )
            self._monitor_tab.load_layered_data(
                symbol,
                daily_snapshots, daily_bars,
                minute_snapshots, minute_bars,
                buy_dates=buy_dates,
                sell_dates=sell_dates,
            )
            self._monitor_dirty = False
            return

        # ── 缓存未命中：计算快照 ──
        print(f"[SCE] _feed_monitor: computing for {symbol} ({minute_key})",
              flush=True)
        daily_snapshots = []
        daily_bars = []
        try:
            n_bars = self._nbars_sp.value()

            # 1. 优先复用 Chart Tab 已加载的原始 bars 作为日线
            chart_raw_bars = getattr(self._kline_tab, '_last_raw_bars', None)
            if chart_raw_bars and len(chart_raw_bars) > 0:
                daily_bars = [_BarAdapter(b) for b in chart_raw_bars]
            else:
                bars_dict = self._load_bars([symbol], n_bars)
                daily_bars = bars_dict.get(symbol, [])

            if not daily_bars:
                print(f"[SCE] _feed_monitor: no daily bars for {symbol}")
                return

            # 2. 加载分钟线 bars（从数据库拉取，不依赖 chart tab）
            minute_interval = self._minute_key_to_interval(minute_key)
            minute_bars = self._load_minute_bars_for_monitor(
                symbol, daily_bars, minute_interval)

            # 3. 生成 daily snapshots
            from ..monitor.condition_monitor_engine import ConditionMonitorEngine
            from ..engine.condition_engine import ConditionEngine
            ce = ConditionEngine()
            monitor_eng = ConditionMonitorEngine(ce)

            if len(daily_bars) >= 200:
                monitor_warmup = 60
            elif len(daily_bars) >= 100:
                monitor_warmup = 30
            else:
                monitor_warmup = min(10, max(1, len(daily_bars) // 4))

            daily_snapshots = monitor_eng.generate_snapshots(
                symbol=symbol,
                bars=daily_bars,
                strategy=self._strategy,
                warmup=monitor_warmup,
                buy_dates=buy_dates,
                sell_dates=sell_dates,
            )
            print(
                f"[SCE] _feed_monitor: {len(daily_snapshots)} daily snapshots "
                f"(warmup={monitor_warmup})",
                flush=True,
            )

            # 4. 生成 minute snapshots（在分钟线上重新计算）
            minute_snapshots = []
            if minute_bars:
                if len(minute_bars) >= 500:
                    minute_warmup = 100
                elif len(minute_bars) >= 200:
                    minute_warmup = 60
                else:
                    minute_warmup = min(20, max(1, len(minute_bars) // 4))
                try:
                    minute_snapshots = monitor_eng.generate_snapshots(
                        symbol=symbol,
                        bars=minute_bars,
                        strategy=self._strategy,
                        warmup=minute_warmup,
                        buy_dates=buy_dates,
                        sell_dates=sell_dates,
                    )
                    print(
                        f"[SCE] _feed_monitor: {len(minute_snapshots)} "
                        f"minute snapshots ({minute_key}, warmup={minute_warmup})",
                        flush=True,
                    )
                except Exception as e:
                    print(f"[SCE] minute snapshots 生成失败: {e}")
                    minute_snapshots = []

            # 回测结果的卖出日期是权威来源
            effective_sell_dates = sell_dates

            # ── 存入缓存 ──
            self._snapshot_cache[cache_key] = (
                daily_snapshots, daily_bars,
                minute_snapshots, minute_bars,
            )
            self._snapshot_cache_key = cache_key

            # ── 推双周期面板 ──
            self._monitor_tab.load_layered_data(
                symbol,
                daily_snapshots, daily_bars,
                minute_snapshots, minute_bars,
                buy_dates=buy_dates,
                sell_dates=effective_sell_dates,
            )
            self._monitor_dirty = False
            print(f"[SCE] _feed_monitor: done, cached", flush=True)
        except Exception as e:
            import traceback
            print(f"[SCE] Monitor 快照生成失败: {e}")
            traceback.print_exc()
            # 降级：只推日线，避免 Monitor Tab 完全空白
            try:
                if daily_bars and daily_snapshots:
                    self._monitor_tab.load_snapshots(
                        symbol, daily_snapshots,
                        bars=daily_bars,
                        buy_dates=buy_dates,
                        sell_dates=sell_dates or [],
                    )
            except Exception:
                pass'''

if old_method not in content:
    print("[ERR] old_method not found, dump start:")
    idx = content.find("def _feed_monitor")
    print(repr(content[idx:idx+200]))
    raise SystemExit(1)

content = content.replace(old_method, new_method, 1)

# ─── Patch 2: 在 _on_tab_changed 后插入新方法（minute_key_to_interval 等）───
old_tab_changed_tail = '''    def _on_tab_changed(self, idx: int) -> None:
        """切换到 Monitor Tab 时，使用缓存快速展示"""
        if self._monitor_tab is None:
            return
        monitor_idx = self._tab.indexOf(self._monitor_tab)
        if idx != monitor_idx:
            return
        symbol = getattr(self._kline_tab, "_current_symbol", "")
        if not symbol:
            return
        buy_dates  = getattr(self._kline_tab, "_last_buy_dates",  [])
        sell_dates = getattr(self._kline_tab, "_last_sell_dates", [])
        # _feed_monitor 内部会先查缓存，命中则 0 延迟
        self._feed_monitor(symbol, buy_dates=buy_dates, sell_dates=sell_dates)'''

new_tab_changed_tail = '''    def _on_tab_changed(self, idx: int) -> None:
        """切换到 Monitor Tab 时，使用缓存快速展示"""
        if self._monitor_tab is None:
            return
        monitor_idx = self._tab.indexOf(self._monitor_tab)
        if idx != monitor_idx:
            return
        symbol = getattr(self._kline_tab, "_current_symbol", "")
        if not symbol:
            return
        buy_dates  = getattr(self._kline_tab, "_last_buy_dates",  [])
        sell_dates = getattr(self._kline_tab, "_last_sell_dates", [])
        # _feed_monitor 内部会先查缓存，命中则 0 延迟
        self._feed_monitor(symbol, buy_dates=buy_dates, sell_dates=sell_dates)

    def _on_monitor_minute_interval_changed(self) -> None:
        """
        Monitor Tab 分钟周期下拉变化时，主动重新拉取双周期数据。
        缓存 key 已包含 minute_key，所以旧 cache 自然会失效。
        """
        if self._monitor_tab is None:
            return
        symbol = getattr(self._kline_tab, "_current_symbol", "")
        if not symbol:
            return
        buy_dates  = getattr(self._kline_tab, "_last_buy_dates",  [])
        sell_dates = getattr(self._kline_tab, "_last_sell_dates", [])
        print(f"[SCE] Monitor 分钟周期变化，重建 cache", flush=True)
        self._feed_monitor(symbol, buy_dates=buy_dates, sell_dates=sell_dates)

    @staticmethod
    def _minute_key_to_interval(key: str):
        """
        将 monitor 面板的分钟 key（"1m"/"5m"/"15m"/"30m"/"1h"）
        转换为 vnpy.trader.constant.Interval 枚举。
        """
        from vnpy.trader.constant import (
            MINUTE, MINUTE_5, MINUTE_15, MINUTE_30, HOUR,
        )
        return {
            "1m":  MINUTE,
            "5m":  MINUTE_5,
            "15m": MINUTE_15,
            "30m": MINUTE_30,
            "1h":  HOUR,
        }.get(key, MINUTE_5)

    def _load_minute_bars_for_monitor(
        self, symbol: str, daily_bars: list, minute_interval,
    ) -> list:
        """
        加载分钟线 bars 用于 Monitor Tab 下方面板。

        策略：
          1. 从 daily_bars 推断日线范围 [start_date, end_date]
          2. 调用 _load_bars_by_date_range 拉取分钟数据
          3. 失败/为空 → 返回 []（由 load_layered_data 决定是否降级）

        性能限制：最多保留 3000 根（60 个交易日 × 48 根/天（5min））。
        """
        try:
            if not daily_bars:
                return []
            first_dt = getattr(daily_bars[0], "datetime", None)
            last_dt = getattr(daily_bars[-1], "datetime", None)
            if first_dt is None or last_dt is None:
                return []
            start_d = first_dt.date() if hasattr(first_dt, "date") else first_dt
            end_d = last_dt.date() if hasattr(last_dt, "date") else last_dt

            bars = self._load_bars_by_date_range(
                symbol, minute_interval, start_d, end_d)

            MAX_MINUTE_BARS = 3000
            if len(bars) > MAX_MINUTE_BARS:
                bars = bars[-MAX_MINUTE_BARS:]
            print(
                f"[SCE] _load_minute_bars_for_monitor {symbol}: "
                f"interval={minute_interval}, n={len(bars)}",
                flush=True,
            )
            return bars
        except Exception as e:
            print(f"[SCE] 加载分钟线失败 {symbol}: {e}")
            return []'''

if old_tab_changed_tail not in content:
    print("[ERR] old_tab_changed_tail not found")
    idx = content.find("def _on_tab_changed")
    print(repr(content[idx:idx+500]))
    raise SystemExit(1)

content = content.replace(old_tab_changed_tail, new_tab_changed_tail, 1)

target.write_text(content, encoding="utf-8")
print(f"[OK] widget.py patched, {len(content)} bytes")
