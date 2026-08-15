"""诊断为什么找不到股票数据"""

print("=" * 60)
print("诊断股票数据加载问题")
print("=" * 60)

# 1. 检查数据库管理器
print("\n[1] 检查数据库管理器...")
try:
    from vnpy.trader.database import get_database, database_manager
    db = get_database()
    print(f"✓ 数据库类型: {type(db).__name__}")
    print(f"✓ 数据库管理器: {database_manager}")
except Exception as e:
    print(f"✗ 数据库管理器错误: {e}")

# 2. 测试查询沪市股票
print("\n[2] 测试查询沪市股票 (SSE)...")
try:
    from vnpy.trader.database import get_database
    from vnpy.trader.constant import Exchange
    
    db = get_database()
    
    # 查询沪市股票
    bars = db.load_bar_data(
        symbol="",  # 空symbol会返回所有
        exchange=Exchange.SSE,
        interval=None,
        start=None,
        end=None
    )
    
    if bars:
        # 提取唯一的股票代码
        symbols = set()
        for bar in bars[:100]:  # 只看前100条
            symbols.add(f"{bar.symbol}.{bar.exchange.value}")
        
        print(f"✓ 找到 {len(bars)} 条K线数据")
        print(f"✓ 涉及股票数: {len(symbols)}")
        print(f"✓ 示例股票: {list(symbols)[:5]}")
    else:
        print("✗ 没有找到任何K线数据")
        print("  原因：数据库中没有沪市股票数据")
        print("  解决：请先通过【数据管理器】下载沪市股票的历史K线")
        
except Exception as e:
    print(f"✗ 查询失败: {e}")
    import traceback
    traceback.print_exc()

# 3. 测试深市股票
print("\n[3] 测试查询深市股票 (SZSE)...")
try:
    from vnpy.trader.database import get_database
    from vnpy.trader.constant import Exchange
    
    db = get_database()
    
    # 尝试不同的查询方式
    print("  尝试方式1: 使用 get_bar_overview()...")
    try:
        overview = db.get_bar_overview()
        szse_stocks = [k for k in overview.keys() if 'SZSE' in str(k)]
        print(f"  找到 {len(szse_stocks)} 只深市股票")
        if szse_stocks:
            print(f"  示例: {szse_stocks[:3]}")
    except AttributeError:
        print("  此数据库不支持 get_bar_overview()")
    
    print("\n  尝试方式2: 直接查询...")
    # 尝试查询一只已知的深市股票
    test_symbols = ["000001", "000002", "000003"]
    for symbol in test_symbols:
        try:
            bars = db.load_bar_data(
                symbol=symbol,
                exchange=Exchange.SZSE,
                interval=None,
                start=None,
                end=None
            )
            if bars:
                print(f"  ✓ 找到 {symbol}.SZSE，共 {len(bars)} 条K线")
                break
        except:
            pass
    else:
        print("  ✗ 未找到任何深市测试股票")
        
except Exception as e:
    print(f"✗ 查询失败: {e}")

# 4. 检查stock_pool.py的查询逻辑
print("\n[4] 检查 stock_pool.py 的查询逻辑...")
try:
    from vnpy.trader.stock_pool import _query_database_sync
    from vnpy.trader.constant import Exchange
    
    print("  执行 _query_database_sync(Exchange.SZSE)...")
    symbols = _query_database_sync(Exchange.SZSE)
    print(f"  返回结果: {len(symbols)} 只股票")
    if symbols:
        print(f"  示例: {list(symbols)[:10]}")
    else:
        print("  ✗ 返回空集合")
        
except Exception as e:
    print(f"✗ 调用失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 总结
print("\n" + "=" * 60)
print("诊断总结")
print("=" * 60)
print("""
可能的原因：
1. 数据库中没有下载股票K线数据
2. 数据库查询方法不兼容当前数据库类型
3. Exchange 枚举值不匹配

解决方案：
1. 先通过【数据管理器】下载历史K线数据
2. 检查数据库是否正确初始化
3. 验证 load_bar_data() 方法是否正常工作
""")
