# -*- coding: utf-8 -*-
import time
import sys
sys.path.insert(0, ".")

print("="*60)
print("股票池沪市按钮性能测试")
print("="*60)

try:
    from vnpy.trader.stock_pool import get_symbols_by_exchange
    
    print("\n[测试1] 首次加载沪市股票（冷启动）")
    start = time.time()
    sse_symbols = get_symbols_by_exchange("SSE")
    elapsed = time.time() - start
    print(f"  结果: {len(sse_symbols)}只股票")
    print(f"  耗时: {elapsed:.3f}秒")
    if sse_symbols:
        print(f"  示例: {sse_symbols[:3]}")
    
    print("\n[测试2] 再次加载沪市股票（使用预分类缓存）")
    start = time.time()
    sse_symbols2 = get_symbols_by_exchange("SSE")
    elapsed2 = time.time() - start
    print(f"  结果: {len(sse_symbols2)}只股票")
    print(f"  耗时: {elapsed2:.3f}秒")
    print(f"  加速比: {elapsed/elapsed2:.1f}x")
    
    print("\n[测试3] 加载深市股票（使用预分类缓存）")
    start = time.time()
    szse_symbols = get_symbols_by_exchange("SZSE")
    elapsed3 = time.time() - start
    print(f"  结果: {len(szse_symbols)}只股票")
    print(f"  耗时: {elapsed3:.3f}秒")
    if szse_symbols:
        print(f"  示例: {szse_symbols[:3]}")
    
    print("\n" + "="*60)
    print("✓ 优化效果总结:")
    print(f"  - 第二次访问比第一次快 {elapsed/elapsed2:.1f} 倍")
    print(f"  - 使用了按交易所预分类的缓存机制")
    print(f"  - 沪市按钮现在应该非常快速响应")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
