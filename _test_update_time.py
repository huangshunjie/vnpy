"""测试股票池更新时间功能"""

from vnpy.trader import stock_pool

# 测试获取更新时间
print("测试 get_pool_update_time 函数:")
update_time = stock_pool.get_pool_update_time()
print(f"返回值: {repr(update_time)}")
print(f"类型: {type(update_time)}")
print(f"是否为空: {not update_time}")

# 查看缓存文件路径
import pathlib
cache_path = pathlib.Path.home() / ".vnpy" / "stock_pool_cache.json"
print(f"\n缓存文件路径: {cache_path}")
print(f"文件是否存在: {cache_path.exists()}")

if cache_path.exists():
    import json
    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f"\n缓存文件中的 update_time: {data.get('update_time', 'NOT FOUND')}")
