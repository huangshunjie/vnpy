"""
预热股票池缓存 - 解决首次选择股票池时卡死的问题

使用方法：
1. 关闭所有 VeighNa 程序
2. 运行此脚本：python _preload_stock_pool.py
3. 等待完成后（约10-60秒），再启动程序

说明：
- 此脚本会从数据库加载所有股票信息并缓存到本地
- 缓存文件位置：C:\Users\11229\.vnpy\stock_pool\symbols_cache.json
- 缓存有效期：1小时
- 之后所有股票池选择操作都会秒开
"""

import time
from pathlib import Path

print("=" * 60)
print("股票池缓存预热工具")
print("=" * 60)

# 检查数据库是否存在
db_path = Path(r"C:\Users\11229\.vnpy\database.db")
if not db_path.exists():
    print(f"❌ 数据库不存在：{db_path}")
    print("请确认数据库路径是否正确")
    input("\n按回车键退出...")
    exit(1)

print(f"\n✓ 找到数据库：{db_path}")
print(f"  数据库大小：{db_path.stat().st_size / (1024**3):.2f} GB")

print("\n开始预热缓存...")
print("（这可能需要10-60秒，请耐心等待）\n")

start_time = time.time()

try:
    # 导入并执行预热
    from vnpy.trader.stock_pool import preload_cache
    
    # 显示进度
    print("正在查询数据库...")
    result = preload_cache()
    
    elapsed = time.time() - start_time
    
    print(f"\n✅ 缓存预热完成！")
    print(f"   耗时：{elapsed:.1f} 秒")
    
    # 显示缓存信息
    cache_file = Path.home() / ".vnpy" / "stock_pool" / "symbols_cache.json"
    if cache_file.exists():
        print(f"   缓存文件：{cache_file}")
        print(f"   缓存大小：{cache_file.stat().st_size / 1024:.1f} KB")
        
        # 读取缓存统计
        import json
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            symbols = cache_data.get('symbols', [])
            print(f"   股票数量：{len(symbols)} 只")
            
            # 按交易所统计
            from collections import Counter
            exchanges = Counter(s.split('.')[1] for s in symbols if '.' in s)
            print(f"   交易所分布：")
            for ex, count in exchanges.most_common():
                print(f"     {ex}: {count} 只")
    
    print("\n" + "=" * 60)
    print("现在可以启动 VeighNa 程序了！")
    print("选择股票池时将秒开，不会再卡顿。")
    print("=" * 60)
    
except Exception as e:
    elapsed = time.time() - start_time
    print(f"\n❌ 预热失败（耗时 {elapsed:.1f} 秒）")
    print(f"错误信息：{e}")
    print("\n可能的原因：")
    print("1. 数据库正在被其他程序占用（请关闭所有 VeighNa 程序）")
    print("2. 数据库文件损坏")
    print("3. 磁盘空间不足")
    
    import traceback
    print("\n详细错误：")
    traceback.print_exc()

input("\n按回车键退出...")
