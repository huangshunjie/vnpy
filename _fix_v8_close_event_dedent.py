# -*- coding: utf-8 -*-
"""
V8 终极 BUG 修复：
- L1460-L1492 的 closeEvent 和 keyPressEvent 被错误地嵌入到 _on_outer_daily_bar_clicked 方法体内部
- 它们缩进 8 空格（应该是 4 空格的类方法）
- 修复：把 L1459 之后的整段（L1460-L1492）重新 dedent -4
"""
import sys
from pathlib import Path

target = Path(r"vnpy\strategy_condition\ui\kline_view.py")
src = target.read_text(encoding="utf-8")
lines = src.split("\n")

# 找到 L1422 (_on_outer_daily_bar_clicked) 和 L1495 (class _FullscreenChart)
# L1458 是上一个方法的 print 结束，L1459 是空行，L1460 是 closeEvent 错位开始
# L1492 是 keyPressEvent 结束，L1493 是空行，L1494 是空行，L1495 是下一个类

# 验证 L1422 存在
assert lines[1421].strip().startswith("def _on_outer_daily_bar_clicked"), f"L1422 not match: {lines[1421]!r}"
# 验证 L1460 是 closeEvent 错位
assert lines[1459].startswith("        def closeEvent"), f"L1460 indent wrong: {lines[1459]!r}"
# 验证 L1495 是下一个类
assert lines[1494].startswith("class _FullscreenChart"), f"L1495 not match: {lines[1494]!r}"

# 修复范围：L1459 (空行) 到 L1492 (keyPressEvent 结束)
# 整段移除前导 4 空格
fixed_count = 0
for i in range(1459, 1493):  # 含 1459, 不含 1493
    if lines[i].startswith("    "):
        lines[i] = lines[i][4:]
        fixed_count += 1
    elif lines[i] == "" or lines[i].strip() == "":
        # 空行保持原样
        pass
    else:
        print(f"WARN: L{i+1} not indented: {lines[i]!r}")

print(f"Dedented {fixed_count} lines (L1459-L1492)")

# 同时检查 L1493, L1494 (两个空行) - 把它们改成单个空行
# 验证
new_1459 = lines[1459]
new_1460 = lines[1460]
new_1492 = lines[1492]
print(f"L1459 (前空行): {new_1459!r}")
print(f"L1460 (closeEvent): {new_1460!r}")
print(f"L1492 (keyPressEvent 末): {new_1492!r}")

# 写回
target.write_text("\n".join(lines), encoding="utf-8")
print("OK")