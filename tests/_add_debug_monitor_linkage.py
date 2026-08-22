# -*- coding: utf-8 -*-
"""为Monitor面板的数据加载添加详细调试输出"""
import io

path = "vnpy/strategy_condition/ui/widget.py"

with io.open(path, "r", encoding="utf-8") as f:
    src = f.read()

# 在 _feed_monitor 方法开始处添加调试输出
old_start = """    def _feed_monitor(
        self,
        symbol: str,
        exchange: Exchange,
        backtest_result: Optional[dict] = None,
    ) -> None:
        \"\"\"给Monitor面板喂数据（双面板：日线+5分钟，均展示快照波形）\"\"\"
        try:
            n_bars = self._nbars_sp.value()"""

new_start = """    def _feed_monitor(
        self,
        symbol: str,
        exchange: Exchange,
        backtest_result: Optional[dict] = None,
    ) -> None:
        \"\"\"给Monitor面板喂数据（双面板：日线+5分钟，均展示快照波形）\"\"\"
        print(f"\n{'='*70}")
        print(f"[DEBUG] _feed_monitor 被调用:")
        print(f"  symbol={symbol}, exchange={exchange}")
        print(f"  backtest_result={'有' if backtest_result else '无'}")
        print(f"{'='*70}")
        
        try:
            n_bars = self._nbars_sp.value()
            print(f"[DEBUG] n_bars = {n_bars}")"""

assert old_start in src, "未找到 _feed_monitor 方法开始"
src = src.replace(old_start, new_start, 1)
print("[OK] 1: 在 _feed_monitor 开始添加调试输出")

# 在加载minute_bars后添加调试
old_minute_load = """            minute_bars = self._datamanager.load_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.MINUTE_5,
                start=start_dt,
                end=end_dt,
            )"""

new_minute_load = """            minute_bars = self._datamanager.load_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.MINUTE_5,
                start=start_dt,
                end=end_dt,
            )
            print(f"[DEBUG] 从数据库加载5分钟数据:")
            print(f"  查询范围: {start_dt.date()} 至 {end_dt.date()}")
            print(f"  加载数量: {len(minute_bars)} 根")
            if minute_bars:
                print(f"  首根时间: {minute_bars[0].datetime}")
                print(f"  末根时间: {minute_bars[-1].datetime}")"""

assert old_minute_load in src, "未找到 minute_bars 加载代码"
src = src.replace(old_minute_load, new_minute_load, 1)
print("[OK] 2: 在加载 minute_bars 后添加调试输出")

# 在generate_snapshots调用前后添加调试
old_gen_snapshots = """            # 2. 分钟快照
            try:
                minute_snapshots = self._monitor.generate_snapshots(
                    symbol=symbol,
                    exchange=exchange,
                    bars=minute_bars,
                    interval=Interval.MINUTE_5,
                )"""

new_gen_snapshots = """            # 2. 分钟快照
            print(f"[DEBUG] 准备生成 minute_snapshots, minute_bars={len(minute_bars)}根")
            try:
                minute_snapshots = self._monitor.generate_snapshots(
                    symbol=symbol,
                    exchange=exchange,
                    bars=minute_bars,
                    interval=Interval.MINUTE_5,
                )
                print(f"[DEBUG] minute_snapshots 生成成功: {len(minute_snapshots)}个")"""

assert old_gen_snapshots in src, "未找到 generate_snapshots 调用"
src = src.replace(old_gen_snapshots, new_gen_snapshots, 1)
print("[OK] 3: 在 generate_snapshots 前后添加调试输出")

# 在load_layered_data调用前添加调试
old_load_layered = """            self._monitor_tab.load_layered_data(
                symbol,
                daily_snapshots, daily_bars,
                minute_snapshots, minute_bars,
                buy_dates=buy_dates or [],
                sell_dates=effective_sell_dates or [],
            )"""

new_load_layered = """            print(f"[DEBUG] 准备调用 load_layered_data:")
            print(f"  daily: {len(daily_snapshots)}个快照, {len(daily_bars)}根K线")
            print(f"  minute: {len(minute_snapshots)}个快照, {len(minute_bars)}根K线")
            print(f"  buy_dates: {len(buy_dates or [])}个")
            print(f"  sell_dates: {len(effective_sell_dates or [])}个")
            
            self._monitor_tab.load_layered_data(
                symbol,
                daily_snapshots, daily_bars,
                minute_snapshots, minute_bars,
                buy_dates=buy_dates or [],
                sell_dates=effective_sell_dates or [],
            )
            print(f"[DEBUG] load_layered_data 调用完成")"""

assert old_load_layered in src, "未找到 load_layered_data 调用"
src = src.replace(old_load_layered, new_load_layered, 1)
print("[OK] 4: 在 load_layered_data 调用前添加调试输出")

# 在降级路径添加调试
old_fallback = """            # 降级：哪怕 snapshots 生成失败，也要保证 K 线画出来
            # （条件波形可能没数据，但至少 K 线 + 成交量能看到）
            try:
                if daily_bars:"""

new_fallback = """            # 降级：哪怕 snapshots 生成失败，也要保证 K 线画出来
            # （条件波形可能没数据，但至少 K 线 + 成交量能看到）
            print(f"[DEBUG] 进入降级路径 (异常发生)")
            print(f"  minute_bars 是否存在: {'是' if minute_bars else '否'}")
            if minute_bars:
                print(f"  minute_bars 数量: {len(minute_bars)}")
            print(f"  minute_snapshots 是否存在: {'是' if minute_snapshots else '否'}")
            if minute_snapshots:
                print(f"  minute_snapshots 数量: {len(minute_snapshots)}")
            
            try:
                if daily_bars:"""

assert old_fallback in src, "未找到降级路径代码"
src = src.replace(old_fallback, new_fallback, 1)
print("[OK] 5: 在降级路径添加调试输出")

with io.open(path, "w", encoding="utf-8") as f:
    f.write(src)

print(f"\n[完成] 已为 {path} 添加详细调试输出")
print("\n使用方法:")
print("1. 运行此脚本应用调试补丁")
print("2. 启动vnpy程序")
print("3. 加载回测结果并切换到Monitor面板")
print("4. 点击日线K线，观察控制台输出")
print("5. 查找以 [DEBUG] 开头的行，了解数据加载的每一步")
print("\n关键观察点:")
print("- minute_bars 加载数量是否为0")
print("- minute_snapshots 生成是否成功")
print("- load_layered_data 接收的参数是否正确")
print("- 是否进入降级路径")