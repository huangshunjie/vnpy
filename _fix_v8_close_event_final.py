"""
V8-BUG 终极修复：
- 删除 L1415-L1492 段（游离段）
- 把它的内容用 4 空格缩进插入到 L1413 之后（_on_fs_measure_toggle 内部结束之后）
- closeEvent / keyPressEvent 成为真正的类方法
- 保持 _FullscreenChart 前的空行结构
"""
from pathlib import Path

p = Path("vnpy/strategy_condition/ui/kline_view.py")
src = p.read_text(encoding="utf-8")
lines = src.splitlines(keepends=True)

# 1) 找到关键锚点
# 0-based: 1410 = "    def _on_fs_measure_toggle"
# 0-based: 1412 = "        self._chart._on_measure_toggle(checked)"
# 0-based: 1413 = "" 空行
# 0-based: 1414 ~ 1491 = 游离段
# 0-based: 1492 = "" 空行
# 0-based: 1493 = "" 空行
# 0-based: 1494 = "class _FullscreenChart..."

# 验证
# 0-based 1410 = "    def _on_fs_measure_toggle"  (L1411)
# 0-based 1412 = "        self._chart._on_measure_toggle(checked)"  (L1413)
# 0-based 1413 = "" (L1414 空行)
# 0-based 1414 = "# ----..." (L1415 注释)
# 0-based 1421 = "def _on_outer_daily_bar_clicked"  (L1422)
# 0-based 1451 = "    def closeEvent" (L1452)
# 0-based 1479 = "    def keyPressEvent" (L1480)
# 0-based 1491 = "        super().keyPressEvent(event)" (L1492 最后一行)
# 0-based 1492 = "" (L1493 空行)
# 0-based 1493 = "" (L1494 空行)
# 0-based 1494 = "class _FullscreenChart..." (L1495)
assert "    def _on_fs_measure_toggle" in lines[1410], f"L1411 mismatch: {lines[1410]!r}"
assert "_on_measure_toggle(checked)" in lines[1412], f"L1413 mismatch: {lines[1412]!r}"
assert lines[1413] == "\n", f"L1414 should be empty: {lines[1413]!r}"
assert lines[1414].startswith("# ----"), f"L1415 should be comment: {lines[1414]!r}"
assert "_on_outer_daily_bar_clicked" in lines[1421], f"L1422 should be def: {lines[1421]!r}"
assert "    def closeEvent" in lines[1451], f"L1452 should be closeEvent: {lines[1451]!r}"
assert "    def keyPressEvent" in lines[1479], f"L1480 should be keyPressEvent: {lines[1479]!r}"
assert "class _FullscreenChart" in lines[1494], f"L1495 should be next class: {lines[1494]!r}"

# 2) 取出游离段 (0-based 1414 ~ 1491) - 从 "# ----" 注释开始，到 keyPressEvent 最后一行
floating_block = lines[1414:1492]  # 包含 1414-1491 共 78 行

# 3) 缩进每行 4 空格
print("Floating block first/last lines:")
for i, ln in enumerate([floating_block[0], floating_block[1], floating_block[2], floating_block[-3], floating_block[-2], floating_block[-1]]):
    print(f"  [{i}] {ln!r}")

# 现在的缩进是 0，需要 +4
indented = []
for ln in floating_block:
    if ln.strip() == "":
        # 纯空行保持空行
        indented.append(ln)
    else:
        indented.append("    " + ln)

# 4) 重组：lines[0:1414]（_on_fs_measure_toggle 函数 + 末尾空行） + 缩进块 + lines[1492:]（空行+空行+class）
new_lines = lines[0:1414]  # 0-1413 共 1414 行
new_lines.extend(indented)  # 加入缩进块
new_lines.extend(lines[1492:])  # 0-based 1492 起（含 1492 空行，1493 空行，1494 class ...）

# 5) 写入
new_src = "".join(new_lines)
p.write_text(new_src, encoding="utf-8")
print(f"OK: rewrote. Old line count={len(lines)}, new line count={len(new_lines)}")