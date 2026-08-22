"""
诊断 Monitor 面板分钟数据加载问题

测试场景：
1. 模拟回测后切换到 Monitor Tab
2. 检查 _feed_monitor 调用链
3. 验证 _load_minute_bars_for_monitor 数据加载
4. 检查 load_layered_data 数据传递
"""
from datetime import datetime, date
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.database import get_database


def test_minute_data_availability():
    """测试600028.SSE的分钟数据可用性"""
    print("=" * 60)
    print("测试1: 数据库分钟数据可用性检查")
    print("=" * 60)
    
    symbol = "600028"
    exchange = Exchange.SSE
    db = get_database()
    
    # 测试不同周期
    intervals = [
        ("1分钟", Interval.MINUTE),
        ("5分钟", Interval.MINUTE_5),
        ("15分钟", Interval.MINUTE_15),
        ("30分钟", Interval.MINUTE_30),
    ]
    
    start_dt = datetime(2020, 1, 1)
    end_dt = datetime(2026, 7, 20, 23, 59, 59)
    
    for name, interval in intervals:
        try:
            bars = db.load_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start=start_dt,
                end=end_dt,
            )
            if bars:
                print(f"\n{name}:")
                print(f"  总计: {len(bars)} 根")
                print(f"  起始: {bars[0].datetime}")
                print(f"  结束: {bars[-1].datetime}")
            else:
                print(f"\n{name}: 无数据")
        except Exception as e:
            print(f"\n{name}: 加载失败 - {e}")


def test_load_minute_bars_simulation():
    """模拟 _load_minute_bars_for_monitor 的逻辑"""
    print("\n" + "=" * 60)
    print("测试2: 模拟 _load_minute_bars_for_monitor 逻辑")
    print("=" * 60)
    
    symbol = "600028.SSE"
    
    # 模拟日线时间范围（从回测结果推断）
    # 假设回测范围 2020-01-01 ~ 2026-07-19
    start_date = date(2020, 1, 1)
    end_date = date(2026, 7, 19)
    
    print(f"\n股票: {symbol}")
    print(f"日线范围: {start_date} ~ {end_date}")
    
    # 测试加载5分钟数据
    from vnpy.trader.database import get_database
    from vnpy.trader.constant import Exchange, Interval
    
    db = get_database()
    parts = symbol.split(".")
    code = parts[0]
    exchange = Exchange.SSE
    
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    print(f"\n尝试加载 5分钟 数据...")
    print(f"  查询范围: {start_dt} ~ {end_dt}")
    
    try:
        bars = db.load_bar_data(
            symbol=code,
            exchange=exchange,
            interval=Interval.MINUTE_5,
            start=start_dt,
            end=end_dt,
        )
        
        if bars:
            print(f"[OK] 成功: {len(bars)} 根")
            print(f"  首根: {bars[0].datetime}")
            print(f"  末根: {bars[-1].datetime}")
            
            # 检查是否需要截断
            MAX_MINUTE_BARS = 20000
            if len(bars) > MAX_MINUTE_BARS:
                print(f"\n需要截断: {len(bars)} -> {MAX_MINUTE_BARS}")
                bars = bars[-MAX_MINUTE_BARS:]
                print(f"  截断后首根: {bars[0].datetime}")
        else:
            print("✗ 无数据")
            
            # 尝试扩大查询范围（模拟两次查询逻辑）
            print("\n尝试扩大查询范围到 2099-12-31...")
            far_end = datetime(2099, 12, 31, 23, 59, 59)
            bars2 = db.load_bar_data(
                symbol=code,
                exchange=exchange,
                interval=Interval.MINUTE_5,
                start=start_dt,
                end=far_end,
            )
            if bars2:
                # 按 end_dt 截断
                bars2 = [b for b in bars2 if b.datetime <= end_dt]
                print(f"✓ 扩大范围后: {len(bars2)} 根")
                if bars2:
                    print(f"  首根: {bars2[0].datetime}")
                    print(f"  末根: {bars2[-1].datetime}")
            else:
                print("✗ 扩大范围后仍无数据")
                
    except Exception as e:
        print(f"✗ 加载失败: {e}")
        import traceback
        traceback.print_exc()


def test_cache_key_generation():
    """测试缓存key生成逻辑"""
    print("\n" + "=" * 60)
    print("测试3: Monitor 缓存 key 生成")
    print("=" * 60)
    
    symbol = "600028.SSE"
    buy_dates = ["2026-03-09", "2026-04-07"]
    sell_dates = ["2026-05-08", "2026-06-05"]
    minute_key = "5m"
    
    # 模拟 strategy_hash（简化版）
    strategy_hash = "abc123def456"
    
    cache_key = (
        symbol,
        strategy_hash,
        tuple(buy_dates),
        tuple(sell_dates),
        minute_key,
    )
    
    print(f"\n缓存 key 组成:")
    print(f"  symbol: {cache_key[0]}")
    print(f"  strategy_hash: {cache_key[1]}")
    print(f"  buy_dates: {cache_key[2]}")
    print(f"  sell_dates: {cache_key[3]}")
    print(f"  minute_key: {cache_key[4]}")
    print(f"\n完整key: {cache_key}")


if __name__ == "__main__":
    try:
        test_minute_data_availability()
        test_load_minute_bars_simulation()
        test_cache_key_generation()
        
        print("\n" + "=" * 60)
        print("诊断完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n诊断过程出错: {e}")
        import traceback
        traceback.print_exc()