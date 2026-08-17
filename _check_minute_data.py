"""
检查数据库中是否有分钟线数据
"""

from vnpy.trader.database import get_database
from vnpy.trader.constant import Exchange, Interval
from datetime import datetime, timedelta

db = get_database()

# 测试股票池中的几只股票
test_symbols = [
    ("600028", Exchange.SSE),
    ("600036", Exchange.SSE),
    ("600426", Exchange.SSE),
    ("601838", Exchange.SSE),
    ("601668", Exchange.SSE),
]

end_dt = datetime.now()
start_dt = end_dt - timedelta(days=30)  # 最近30天

print("=" * 70)
print("检查数据库中的K线数据")
print("=" * 70)
print(f"时间范围: {start_dt.date()} ~ {end_dt.date()}")
print()

# 检查每只股票的各周期数据
intervals_to_check = [
    (Interval.DAILY, "日线"),
    (Interval.MINUTE_5, "5分钟"),
    (Interval.MINUTE_15, "15分钟"),
    (Interval.MINUTE_30, "30分钟"),
    (Interval.HOUR, "60分钟"),
]

for symbol, exchange in test_symbols:
    print(f"\n{symbol}.{exchange.value}:")
    print("-" * 50)
    
    for interval, name in intervals_to_check:
        try:
            bars = db.load_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start=start_dt,
                end=end_dt
            )
            
            if bars:
                print(f"  {name:8s}: {len(bars):4d} 根 (最新: {bars[-1].datetime.date()})")
            else:
                print(f"  {name:8s}: ❌ 无数据")
                
        except Exception as e:
            print(f"  {name:8s}: ❌ 错误 - {e}")

print("\n" + "=" * 70)
print("总结")
print("=" * 70)

# 统计有分钟线数据的股票数量
symbols_with_minute_data = []
for symbol, exchange in test_symbols:
    try:
        bars = db.load_bar_data(
            symbol=symbol,
            exchange=exchange,
            interval=Interval.MINUTE_5,
            start=start_dt,
            end=end_dt
        )
        if bars:
            symbols_with_minute_data.append(f"{symbol}.{exchange.value}")
    except:
        pass

if symbols_with_minute_data:
    print(f"✓ 有 {len(symbols_with_minute_data)}/{len(test_symbols)} 只股票有5分钟数据")
    print(f"  股票: {', '.join(symbols_with_minute_data)}")
else:
    print("❌ 没有任何股票有5分钟数据！")
    print("\n可能原因：")
    print("1. 未下载分钟线数据")
    print("2. 需要通过'数据管理'应用下载分钟K线")
    print("3. 或者数据源不提供历史分钟线数据")