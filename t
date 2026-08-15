# -*- coding: utf-8 -*-
"""
测试优化后的stock_pool性能
"""
import sys
import time

sys.path.insert(0, r'c:\Users\11229\Documents\GitHub\vnpy')

print("=" * 70)
print("测试优化后的stock_pool查询性能")
print("=" * 70)

from vnpy.trader.stock_pool import get_symbols_by_exchange

print("\n测试1: 查询沪市股票")
print("-" * 70)
start = time.time()
sse_symbols = get_symbols_by_exchange("SSE")
elapsed = time.time() - start

print(f"✓ 查询完成")
print(f"  耗时: {elapsed:.2f} 秒")
print(f"  结果: {len(sse_symbols)} 只股票")
if sse_symbols:
    print(f"  样本: {sse_symbols[:5]}")

print("\n测试2: 再次查询沪市（测试缓存）")
print("-" * 70)
start = time.time()
sse_symbols2 = get_symbols_by_exchange("SSE")
elapsed2 = time.time() - start

print(f"✓ 查询完成")
print(f"  耗时: {elapsed2:.2f} 秒（应该很快，使用缓存）")
print(f"  结果: {len(sse_symbols2)} 只股票")

print("\n" + "=" * 70)
print("优化效果总结:")
print(f"  首次查询: {elapsed:.2f}秒")
print(f"  缓存查询: {elapsed2:.2f}秒")
if elapsed < 5:
    print("  ✓ 性能优化成功！首次查询<5秒")
else:
    print("  ⚠ 首次查询仍需优化")
print("=" * 70)
