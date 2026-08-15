"""测试股票池更新时间显示功能"""

import sys
sys.path.insert(0, '.')

from vnpy.trader.stock_pool import get_pool_update_time

# 测试获取更新时间
update_time = get_pool_update_time()

if update_time:
    print(f"[SUCCESS] 成功获取股票池更新时间: {update_time}")
else:
    print("[FAIL] 未能获取更新时间（可能缓存文件不存在或没有update_time字段）")
    
# 检查缓存文件
from pathlib import Path
import json

cache_path = Path.home() / ".vnpy" / "stock_pool" / "symbols_cache.json"
print(f"\n缓存文件路径: {cache_path}")
print(f"文件存在: {cache_path.exists()}")

if cache_path.exists():
    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f"缓存文件中的 update_time: {data.get('update_time', '未找到')}")
        print(f"缓存的股票数量: SSE={len(data.get('SSE', []))}, SZSE={len(data.get('SZSE', []))}")
