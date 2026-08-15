"""诊断股票池按钮问题

检查：
1. widget.py 中的修复是否已应用
2. 重试函数是否存在
3. 重试延迟是否合理
"""

import re

print("=" * 60)
print("股票池按钮诊断")
print("=" * 60)

# 读取 widget.py
with open("vnpy/strategy_condition/ui/widget.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 检查 _set_exchange_pool 函数
print("\n1. 检查 _set_exchange_pool 函数:")
if "def _set_exchange_pool" in content:
    print("   ✓ 函数存在")
    
    # 检查是否有重试逻辑
    if "QTimer.singleShot" in content and "_retry_exchange_pool" in content:
        print("   ✓ 有重试逻辑（QTimer + _retry_exchange_pool）")
        
        # 提取重试延迟时间
        match = re.search(r'QTimer\.singleShot\((\d+),', content)
        if match:
            delay = match.group(1)
            print(f"   - 重试延迟: {delay} 毫秒")
            if int(delay) < 2000:
                print(f"   ⚠ 警告：延迟可能不够！建议至少 3000 毫秒")
    else:
        print("   ✗ 缺少重试逻辑")
else:
    print("   ✗ 函数不存在")

# 2. 检查重试函数
print("\n2. 检查重试函数:")
retry_functions = ["_retry_exchange_pool", "_retry_board_pool", "_retry_index_pool"]
for func in retry_functions:
    if f"def {func}" in content:
        print(f"   ✓ {func} 存在")
    else:
        print(f"   ✗ {func} 不存在")

# 3. 检查是否更新了文本框
print("\n3. 检查是否更新合约代码文本框:")
if "_pool_edit.setPlainText" in content:
    print("   ✓ 有更新文本框的代码")
    # 统计出现次数
    count = content.count("_pool_edit.setPlainText")
    print(f"   - 出现次数: {count}")
else:
    print("   ✗ 没有更新文本框的代码")

# 4. 建议
print("\n" + "=" * 60)
print("诊断结果和建议:")
print("=" * 60)

if "QTimer.singleShot" in content:
    print("\n修复代码已应用，但可能存在以下问题：")
    print("1. 首次查询数据库可能需要5-10秒，1.5秒重试太快")
    print("2. 建议将重试延迟改为 3000 毫秒（3秒）")
    print("3. 或者增加多次重试机制（例如重试3次，间隔递增）")
else:
    print("\n修复代码未应用！需要运行修复脚本。")

print("\n下一步操作：")
print("1. 运行 _fix_stock_pool_buttons_v3.py (改进版修复)")
print("2. 或者等待后台加载完成后（约10秒）再点击按钮")
