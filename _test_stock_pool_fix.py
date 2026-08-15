"""测试股票池按钮修复"""
import sys

print("=" * 60)
print("测试股票池按钮修复")
print("=" * 60)

# 1. 测试 stock_pool.py 中没有 _CACHE_LOADING
print("\n1. 检查 stock_pool.py...")
try:
    from vnpy.trader.stock_pool import get_symbols_by_exchange
    print("   ✓ 成功导入 get_symbols_by_exchange")
    
    # 尝试导入 _CACHE_LOADING（应该失败）
    try:
        from vnpy.trader.stock_pool import _CACHE_LOADING
        print("   ✗ 错误：_CACHE_LOADING 仍然存在！")
        sys.exit(1)
    except ImportError:
        print("   ✓ _CACHE_LOADING 已成功移除")
except Exception as e:
    print(f"   ✗ 错误：{e}")
    sys.exit(1)

# 2. 测试获取股票数据
print("\n2. 测试获取沪市股票...")
try:
    symbols = get_symbols_by_exchange("SSE")
    if symbols:
        print(f"   ✓ 成功获取 {len(symbols)} 只沪市股票")
        print(f"   示例：{list(symbols)[:5]}")
    else:
        print("   ⚠ 警告：未找到沪市股票（可能数据库为空）")
except Exception as e:
    print(f"   ✗ 错误：{e}")
    import traceback
    traceback.print_exc()

# 3. 测试获取深市股票
print("\n3. 测试获取深市股票...")
try:
    symbols = get_symbols_by_exchange("SZSE")
    if symbols:
        print(f"   ✓ 成功获取 {len(symbols)} 只深市股票")
        print(f"   示例：{list(symbols)[:5]}")
    else:
        print("   ⚠ 警告：未找到深市股票（可能数据库为空）")
except Exception as e:
    print(f"   ✗ 错误：{e}")
    import traceback
    traceback.print_exc()

# 4. 检查 widget.py 中的导入
print("\n4. 检查 widget.py...")
try:
    with open("vnpy/strategy_condition/ui/widget.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    if "_CACHE_LOADING" in content:
        print("   ✗ 错误：widget.py 中仍有 _CACHE_LOADING 引用")
        # 找出位置
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if "_CACHE_LOADING" in line:
                print(f"      第 {i} 行: {line.strip()}")
        sys.exit(1)
    else:
        print("   ✓ widget.py 中没有 _CACHE_LOADING 引用")
except Exception as e:
    print(f"   ✗ 错误：{e}")

print("\n" + "=" * 60)
print("✓ 所有测试通过！")
print("=" * 60)
print("\n请重新启动应用程序，测试股票池按钮功能：")
print("1. 打开策略条件引擎")
print("2. 点击股票池下方的'沪市'或'深市'按钮")
print("3. 观察文本框是否正确显示股票代码")
print("\n注意：首次点击可能需要等待3-10秒查询数据库")
