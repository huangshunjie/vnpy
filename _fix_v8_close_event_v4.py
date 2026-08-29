"""
V8-BUG 终极修复 V4：
直接定位 L1415-L1492（0-based 1414-1491），全段 +4 空格。
- L1415 注释 "# ----..."（0 缩进）→ 4 缩进
- L1422 def _on_outer_daily_bar_clicked（0 缩进）→ 4 缩进
- 函数体内 8/12 缩进行保持不变
- L1460 def closeEvent 已经是 4 缩进，但不属于类（因为 def 之前都是游离）→ 整体要变 8 缩进
- L1488 def keyPressEvent 同理

逻辑：
- 注释行（# 开头）缩进 +4
- 顶层 def（0 缩进的 def）缩进 +4
- 顶层 class 缩进 0（保持）
- 函数体内 8/12/16 缩进 +4
- 空行不变
"""
from pathlib import Path

p = Path("vnpy/strategy_condition/ui/kline_view.py")
src = p.read_text(encoding="utf-8")
lines = src.splitlines(keepends=True)

# 定位起点：包含 "# ----" 注释，且 0 缩进
floating_start = None
for i, ln in enumerate(lines):
    if ln.startswith("# ----") and ln.rstrip("\n").rstrip() == "# " + "-" * 64:
        # 是大分割注释
        floating_start = i
        break
assert floating_start is not None, "找不到 # ---- 注释"
print(f"floating_start (0-based) = {floating_start}, 1-based = {floating_start+1}")

# 定位终点：keyPressEvent 函数体结束后的空行+class _FullscreenChart
# 找 class _FullscreenChart 起始（0 缩进的 class）
fullscreen_class_idx = None
for i in range(floating_start, len(lines)):
    if lines[i].startswith("class _FullscreenChart"):
        fullscreen_class_idx = i
        break
assert fullscreen_class_idx is not None, "找不到 class _FullscreenChart"
print(f"class _FullscreenChart 1-based = {fullscreen_class_idx+1}")

# keyPressEvent 函数体结束位置：fullscreen_class_idx 之前最近的非空行
# 实际结构：keyPressEvent 函数体 → 空行 → 空行 → class _FullscreenChart
# key_end 应该是 class 之前紧邻的空行（多空行）
key_end = fullscreen_class_idx
while key_end > 0 and lines[key_end - 1].strip() == "":
    key_end -= 1
# key_end 是 keyPressEvent 函数体最后一行（不含尾随空行）
key_end += 1  # 切到 key_end 之后第一个空行
print(f"key_end (0-based) = {key_end}, 1-based = {key_end+1}, line = {lines[key_end]!r}")

# 切片：floating_start .. key_end（含 key_end 紧邻的第一个空行）
floating_block = lines[floating_start:key_end]
print(f"floating_block 行数 = {len(floating_block)}")
print(f"首 5 行：")
for i, ln in enumerate(floating_block[:5]):
    print(f"  [{i}] {ln!r}")
print(f"末 5 行：")
for i, ln in enumerate(floating_block[-5:]):
    print(f"  [{i}] {ln!r}")

# 给每行 +4 缩进（仅当有非空白内容时）
indented = []
for ln in floating_block:
    if ln.strip() == "":
        indented.append(ln)
    else:
        indented.append("    " + ln)

# 重组
new_lines = lines[0:floating_start]  # floating_start 之前的所有行
new_lines.extend(indented)            # 缩进后的段
new_lines.extend(lines[key_end:])     # 剩余部分（含空行 + class _FullscreenChart ...）

new_src = "".join(new_lines)
p.write_text(new_src, encoding="utf-8")
print(f"OK: rewrote. Old line count={len(lines)}, new line count={len(new_lines)}")