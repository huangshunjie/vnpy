#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""诊断股票池SSE按钮问题"""

import sys
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vnpy.trader.stock_pool import get_symbols_by_exchange, _ensure_symbols_cache

print("="*60)
print("诊断：股票池沪市按钮问题")
print("="*60)

# 1. 检查缓存状态
print("\n[1] 检查缓存状态...")
cache = _ensure_symbols_cache()
print(f"    缓存中的股票数量: {len(cache)}")
if cache:
    print(f"    示例股票: {list(cache)[:5]}")
else:
    print("    ⚠️  缓存为空！这是问题的根源。")

# 2. 测试get_symbols_by_exchange("SSE")
print("\n[2] 测试 get_symbols_by_exchange('SSE')...")
sse_symbols = get_symbols_by_exchange("SSE")
print(f"    返回的沪市股票数量: {len(sse_symbols)}")
if sse_symbols:
    print(f"    示例: {sse_symbols[:5]}")
else:
    print("    ⚠️  返回空列表！")

# 3. 等待后重试
if not sse_symbols:
    print("\n[3] 等待1.5秒后重试（模拟UI的重试机制）...")
    time.sleep(1.5)
    sse_symbols_retry = get_symbols_by_exchange("SSE")
    print(f"    重试后的沪市股票数量: {len(sse_symbols_retry)}")
    if sse_symbols_retry:
        print(f"    ✓ 重试成功！示例: {sse_symbols_retry[:5]}")
    else:
        print("    ✗ 重试失败，仍然为空")

# 4. 结论
print("\n" + "="*60)
print("结论:")
if len(cache) == 0:
    print("❌ 问题：缓存未初始化")
    print("   解决方案：")
    print("   1. 确保已运行 _preload_stock_pool.py")
    print("   2. 或者重启应用程序以触发后台加载")
elif len(sse_symbols) == 0:
    print("❌ 问题：SSE交易所筛选逻辑有问题")
else:
    print("✓ 一切正常，应该能看到沪市股票")
    print(f"  共 {len(sse_symbols)} 只沪市股票")
print("="*60)
