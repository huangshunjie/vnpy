"""
V8 终极修复：将 1414-1492 段（游离在类外）正确缩进到 _KlineFullscreenWindow 类内
- _on_outer_daily_bar_clicked → 变成方法（self 有效）
- closeEvent → 真正覆盖 QWidget.closeEvent，清理 owner_monitor 引用
- keyPressEvent → 真正覆盖 QWidget.keyPressEvent，ESC 关闭

实现：找到 1414-1492 整段，删除；然后把它在 _on_fs_measure_toggle 后追加（缩进 4 空格）
"""
import re
from pathlib import Path

p = Path("vnpy/strategy_condition/ui/kline_view.py")
src = p.read_text(encoding="utf-8")
lines = src.splitlines(keepends=True)

# 找出游离段（1422 起的 _on_outer_daily_bar_clicked 和后续的 closeEvent/keyPressEvent）
# 1415 行的注释也是类外
# 边界：从包含 "# ----" 注释起 (1415)，到 "keyPressEvent" 函数结束 (1492) 之后一个空行前
# 思路：找 1414 行的索引（0-based: 1413），找 1493 行的索引（0-based: 1492）

# 验证 1414 行（0-based 1413）的字符
print(f"L1414 (0-based 1413): {lines[1413]!r}")
print(f"L1492 (0-based 1491): {lines[1491]!r}")
print(f"L1493 (0-based 1492): {lines[1492]!r}")
print(f"L1494 (0-based 1493): {lines[1493]!r}")
print(f"L1495 (0-based 1494): {lines[1494]!r}")
print(f"L1413 (0-based 1412): {lines[1412]!r}")
print(f"L1411 (0-based 1410): {lines[1410]!r}")