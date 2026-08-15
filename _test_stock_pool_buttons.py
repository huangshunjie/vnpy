"""测试股票池按钮功能"""

# 测试市场/板块按钮
from vnpy.trader.stock_pool import get_symbols_by_exchange, get_symbols_by_board

print("=" * 60)
print("测试市场筛选")
print("=" * 60)

for key, name in [("ALL", "全市场"), ("SSE", "沪市"), ("SZSE", "深市"), ("BSE", "北交所")]:
    symbols = get_symbols_by_exchange(key)
    print(f"{name} ({key}): {len(symbols)} 只股票")
    if symbols:
        print(f"  示例: {symbols[:3]}")
    else:
        print("  ⚠️ 返回空列表！")

print()
print("=" * 60)
print("测试板块筛选")
print("=" * 60)

for board in ["沪主板", "科创板", "深主板", "创业板"]:
    symbols = get_symbols_by_board(board)
    print(f"{board}: {len(symbols)} 只股票")
    if symbols:
        print(f"  示例: {symbols[:3]}")
    else:
        print("  ⚠️ 返回空列表！")

print()
print("=" * 60)
print("测试完成")
print("=" * 60)
