"""
添加详细的调试日志到 _feed_monitor 和 _load_minute_bars_for_monitor
追踪实际的执行路径和数据流
"""

def add_debug_logs():
    widget_path = "vnpy/strategy_condition/ui/widget.py"
    
    with open(widget_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 在 _load_minute_bars_for_monitor 开始处添加日志
    old_load_minute = """    def _load_minute_bars_for_monitor(
        self, symbol: str, daily_bars: list, minute_interval,
    ) -> list:
        """
    
    new_load_minute = """    def _load_minute_bars_for_monitor(
        self, symbol: str, daily_bars: list, minute_interval,
    ) -> list:
        print(f"\\n[TRACE] _load_minute_bars_for_monitor 被调用:")
        print(f"  symbol={symbol}")
        print(f"  daily_bars数量={len(daily_bars) if daily_bars else 0}")
        print(f"  minute_interval={minute_interval}")
        """
    
    if old_load_minute in content:
        content = content.replace(old_load_minute, new_load_minute)
        print("[OK] 添加了 _load_minute_bars_for_monitor 入口日志")
    
    # 2. 在 _load_minute_bars_for_monitor 返回前添加日志
    old_return = """            print(
                f"[SCE] _load_minute_bars_for_monitor {symbol}: "
                f"interval={minute_interval}, n={len(bars)}",
                flush=True,
            )
            return bars"""
    
    new_return = """            print(
                f"[SCE] _load_minute_bars_for_monitor {symbol}: "
                f"interval={minute_interval}, n={len(bars)}",
                flush=True,
            )
            print(f"[TRACE] _load_minute_bars_for_monitor 返回: {len(bars)}根")
            return bars"""
    
    if old_return in content:
        content = content.replace(old_return, new_return)
        print("[OK] 添加了 _load_minute_bars_for_monitor 返回日志")
    
    # 3. 在 _feed_monitor 的 minute_bars 赋值后添加日志
    old_assign = """            # 2. 加载分钟线 bars（从数据库拉取，不依赖 chart tab）
            minute_interval = self._minute_key_to_interval(minute_key)
            minute_bars = self._load_minute_bars_for_monitor(
                symbol, daily_bars, minute_interval)"""
    
    new_assign = """            # 2. 加载分钟线 bars（从数据库拉取，不依赖 chart tab）
            minute_interval = self._minute_key_to_interval(minute_key)
            print(f"[TRACE] 调用 _load_minute_bars_for_monitor, minute_key={minute_key}, interval={minute_interval}")
            minute_bars = self._load_minute_bars_for_monitor(
                symbol, daily_bars, minute_interval)
            print(f"[TRACE] _load_minute_bars_for_monitor 返回后, minute_bars={'None' if minute_bars is None else len(minute_bars)}")"""
    
    if old_assign in content:
        content = content.replace(old_assign, new_assign)
        print("[OK] 添加了 minute_bars 赋值日志")
    
    # 4. 在 load_layered_data 调用前添加日志
    old_layered = """            # ── 推双周期面板 ──
            self._monitor_tab.load_layered_data(
                symbol,
                daily_snapshots, daily_bars,
                minute_snapshots, minute_bars,
                buy_dates=buy_dates,
                sell_dates=effective_sell_dates,
            )"""
    
    new_layered = """            # ── 推双周期面板 ──
            print(f"[TRACE] 调用 load_layered_data:")
            print(f"  daily_snapshots={len(daily_snapshots) if daily_snapshots else 0}")
            print(f"  daily_bars={len(daily_bars) if daily_bars else 0}")
            print(f"  minute_snapshots={len(minute_snapshots) if minute_snapshots else 0}")
            print(f"  minute_bars={len(minute_bars) if minute_bars else 0}")
            self._monitor_tab.load_layered_data(
                symbol,
                daily_snapshots, daily_bars,
                minute_snapshots, minute_bars,
                buy_dates=buy_dates,
                sell_dates=effective_sell_dates,
            )"""
    
    if old_layered in content:
        content = content.replace(old_layered, new_layered)
        print("[OK] 添加了 load_layered_data 调用日志")
    
    # 5. 在降级路径添加日志
    old_fallback = """                    self._monitor_tab.load_layered_data(
                        symbol,
                        daily_snapshots or [], daily_bars,
                        minute_snapshots if minute_snapshots else [],
                        minute_bars if minute_bars else [],
                        buy_dates=buy_dates or [],
                        sell_dates=sell_dates or [],
                    )"""
    
    new_fallback = """                    print(f"[TRACE] 降级路径 - 调用 load_layered_data:")
                    print(f"  daily_bars={len(daily_bars) if daily_bars else 0}")
                    print(f"  minute_bars={len(minute_bars) if minute_bars else 0}")
                    self._monitor_tab.load_layered_data(
                        symbol,
                        daily_snapshots or [], daily_bars,
                        minute_snapshots if minute_snapshots else [],
                        minute_bars if minute_bars else [],
                        buy_dates=buy_dates or [],
                        sell_dates=sell_dates or [],
                    )"""
    
    if old_fallback in content:
        content = content.replace(old_fallback, new_fallback)
        print("[OK] 添加了降级路径日志")
    
    with open(widget_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n[OK] 所有调试日志已添加到 {widget_path}")
    print("\n现在运行程序并执行回测，观察控制台输出：")
    print("  应该能看到完整的数据流路径和每一步的数据数量")


if __name__ == "__main__":
    print("=" * 60)
    print("添加 Monitor 数据加载路径追踪日志")
    print("=" * 60)
    add_debug_logs()