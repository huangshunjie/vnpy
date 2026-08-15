"""测试交易所股票池筛选功能"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("=" * 60)
print("测试交易所股票池筛选")
print("=" * 60)

# 1. 测试stock_pool模块的get_symbols_by_exchange
print("\n1. 测试 get_symbols_by_exchange 函数:")
try:
    from vnpy.trader.stock_pool import get_symbols_by_exchange, _CACHE_LOADING, _ensure_symbols_cache
    
    print(f"   _CACHE_LOADING = {_CACHE_LOADING}")
    
    # 先确保缓存加载
    print("\n   调用 _ensure_symbols_cache()...")
    cache = _ensure_symbols_cache()
    print(f"   缓存大小: {len(cache)} 个股票")
    
    if cache:
        print(f"   前5个股票: {list(cache)[:5]}")
    
    # 测试SSE（沪市）
    print("\n   测试 SSE (沪市)...")
    sse_symbols = get_symbols_by_exchange("SSE")
    print(f"   返回数量: {len(sse_symbols)}")
    if sse_symbols:
        print(f"   前10个: {sse_symbols[:10]}")
    else:
        print("   WARNING: 返回空列表!")
        
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

# 2. 检查数据库
print("\n\n2. 直接查询数据库:")
try:
    from vnpy.trader.database import get_database
    from vnpy.trader.constant import Interval
    
    db = get_database()
    overview = db.get_bar_overview()
    
    sse_daily = [o for o in overview if o.exchange.value == "SSE" and o.interval == Interval.DAILY]
    print(f"   SSE日线数据数量: {len(sse_daily)}")
    
    if sse_daily:
        print(f"   前10个: {[f'{o.symbol}.{o.exchange.value}' for o in sse_daily[:10]]}")
    
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
