# -*- coding: utf-8 -*-
"""
从数据库提取真实股票，更新股票池缓存
运行此脚本后，股票池将显示准确的数量
"""
import json
from pathlib import Path
from datetime import datetime

print("正在从数据库提取真实股票...")

try:
    # 使用vnpy的数据库接口
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    
    from vnpy.trader.database import get_database
    from vnpy.trader.constant import Interval
    
    db = get_database()
    print("✓ 数据库连接成功")
    
    # 获取所有日线数据的symbol
    print("正在查询数据库...")
    overview = db.get_bar_overview()
    
    stock_pool = set()
    for o in overview:
        if o.interval == Interval.DAILY:
            stock_pool.add(f"{o.symbol}.{o.exchange.value}")
    
    print(f"✓ 查询完成，找到 {len(stock_pool)} 只股票")
    
    # 保存到缓存
    cache_dir = Path.home() / ".vnpy" / "stock_pool"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "symbols_cache.json"
    
    data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(stock_pool),
        "symbols": sorted(stock_pool),
        "note": "从数据库提取的真实股票列表"
    }
    
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 缓存已更新")
    print(f"  文件位置: {cache_file}")
    print(f"  股票总数: {len(stock_pool)}")
    
    # 统计各交易所数量
    sse_count = len([s for s in stock_pool if '.SSE' in s])
    szse_count = len([s for s in stock_pool if '.SZSE' in s])
    bse_count = len([s for s in stock_pool if '.BSE' in s])
    
    print(f"  沪市: {sse_count}")
    print(f"  深市: {szse_count}")
    print(f"  北交所: {bse_count}")
    print("\n现在重启vnpy，数量应该准确了！")
    
except Exception as e:
    print(f"\n✗ 出错: {e}")
    print("\n请确保：")
    print("  1. 已配置vnpy数据库")
    print("  2. 数据库中有日线数据")
    print("  3. vnpy程序已关闭")
    import traceback
    traceback.print_exc()
