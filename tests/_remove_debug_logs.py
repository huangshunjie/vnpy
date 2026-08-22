"""
移除之前添加的调试日志
"""

def remove_debug_logs():
    widget_path = "vnpy/strategy_condition/ui/widget.py"
    
    with open(widget_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除 _load_minute_bars_for_monitor 入口日志
    old_1 = """    def _load_minute_bars_for_monitor(
        self, symbol: str, daily_bars: list, minute_interval,
    ) -> list:
        print(f"\\n[TRACE] _load_minute_bars_for_monitor 被调用:")
        print(f"  symbol={symbol}")
        print(f"  daily_bars数量={len(daily_bars) if daily_bars else 0}")
        print(f"  minute_interval={minute_interval}")
        \"\"\"
"""
    
    new_1 = """    def _load_minute_bars_for_monitor(
        self, symbol: str, daily_bars: list, minute_interval,
    ) -> list:
        \"\"\"
"""
    
    if old_1 in content:
        content = content.replace(old_1, new_1)
        print("[OK] 移除了 _load_minute_bars_for_monitor 入口日志")
    
    # 移除返回日志
    old_2 = """            print(
                f"[SCE] _load_minute_bars_for_monitor {symbol}: "
                f"interval={minute_interval}, n={len(bars)}",
                flush=True,
            )
            print(f"[TRACE] _load_minute_bars_for_monitor 返回: {len(bars)}根")
            return bars"""
    
    new_2 = """            print(
                f"[SCE] _load_minute_bars_for_monitor {symbol}: "
                f"interval={minute_interval}, n={len(bars)}",
                flush=True,
            )
            return bars"""
    
    if old_2 in content:
        content = content.replace(old_2, new_2)
        print("[OK] 移除了返回日志")
    
    # 移除 minute_bars 赋值日志
    old_3 = """            # 2. 加载分钟线 bars（从数据库拉取，不依赖 chart tab）
            minute_interval = self._minute_key_to_interval(minute_key)
            print(f"[TRACE] 调用 _load_minute_bars_for_monitor, minute_key={minute_key}, interval={minute_interval}")
            minute_bars = self._load_minute_bars_for_monitor(
                symbol, daily_bars, minute_interval)
            print(f"[TRACE] _load_minute_bars_for_monitor 返回后, minute_bars={'None' if minute_bars is None else len(minute_bars)}")"""
    
    new_3 = """            # 2. 加载分钟线 bars（从数据库拉取，不依赖 chart tab）
            minute_interval = self._minute_key_to_interval(minute_key)
            minute_bars = self._load_minute_bars_for_monitor(
                symbol, daily_bars, minute_interval)"""
    
    if old_3 in content:
        content = content.replace(old_3, new_3)
        print("[OK] 移除了 minute_bars 赋值日志")
    
    # 移除 load_layered_data 调用日志
    old_4 = """            # ── 推双周期面板 ──
            print(f"[TRACE] 调用 load_layered_data:")
            print(f"  daily_snapshots={len(daily_snapshots) if daily_snapshots else 0}")
            print(f"  daily_bars={len(daily_bars) if daily_bars else 0}")
            print(f"  minute_snapshots={len(minute_snapshots) if minute_snapshots else 0}")
            print(f"  minute_bars={len(minute_bars) if minute_bars else 0}")
            self._monitor_tab.load_layered_data("""
    
    new_4 = """            # ── 推双周期面板 ──
            self._monitor_tab.load_layered_data("""
    
    if old_4 in content:
        content = content.replace(old_4, new_4)
        print("[OK] 移除了 load_layered_data 调用日志")
    
    # 移除降级路径日志
    old_5 = """                    print(f"[TRACE] 降级路径 - 调用 load_layered_data:")
                    print(f"  daily_bars={len(daily_bars) if daily_bars else 0}")
                    print(f"  minute_bars={len(minute_bars) if minute_bars else 0}")
                    self._monitor_tab.load_layered_data("""
    
    new_5 = """                    self._monitor_tab.load_layered_data("""
    
    if old_5 in content:
        content = content.replace(old_5, new_5)
        print("[OK] 移除了降级路径日志")
    
    with open(widget_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n[OK] 已保存到 {widget_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("移除调试日志")
    print("=" * 60)
    remove_debug_logs()
    print("\n清理完成！")