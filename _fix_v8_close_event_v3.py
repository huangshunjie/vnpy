"""
V8-BUG 终极修复 V3：
不靠行号硬编码（多次因前面修复产生偏差），直接按文本/缩进定位。
策略：
1. 找到 "    def _on_fs_measure_toggle"（类内方法）
2. 找该方法结束的下一个空行（属于该类的内部空行）
3. 之后如果下一行不是 4 空格缩进（即 0 缩进），说明是游离段
4. 找到游离段中 "def closeEvent" 和 "def keyPressEvent" 的真正位置
5. 删除从游离段开始到 keyPressEvent 函数体末尾的整段
6. 把这段加上 4 空格缩进，插入到 _on_fs_measure_toggle 结束的内部空行之后
"""
import re
from pathlib import Path

p = Path("vnpy/strategy_condition/ui/kline_view.py")
src = p.read_text(encoding="utf-8")
lines = src.splitlines(keepends=True)

# 步骤 1：定位 _on_fs_measure_toggle（4 空格缩进，类内方法）
fs_toggle_idx = None
for i, ln in enumerate(lines):
    if ln == "    def _on_fs_measure_toggle(self, checked: bool) -> None:\n":
        fs_toggle_idx = i
        break
assert fs_toggle_idx is not None, "找不到 _on_fs_measure_toggle"

# 步骤 2：从 fs_toggle_idx 往下找函数体结束
# 函数体结束的标志：连续遇到第一个非缩进行（即 0 空格缩进）时为函数结束
j = fs_toggle_idx + 1
while j < len(lines) and (lines[j].startswith("    ") or lines[j].strip() == ""):
    j += 1
# j 是函数结束后的第一个非缩进行索引（可能是空行、注释、或者下一个 def）
# 通常函数体内最后一个语句后有一空行，下一个 def 也是 4 缩进
# 实际：函数结束后应该遇到 0 缩进的行：注释 "# ----..." 或 "def xxx" 游离
print(f"_on_fs_measure_toggle 在第 {fs_toggle_idx+1} 行 (1-based)")
print(f"函数体结束（j={j}，1-based={j+1}）下一行：{lines[j]!r}")

# j 应该是 0 缩进的 "# ----..." 注释（游离段起点）
# 验证
assert lines[j].startswith("# ----"), f"游离段起点应该以 # ---- 开头: {lines[j]!r}"
floating_start = j

# 步骤 3：找游离段中 "def closeEvent" 和 "def keyPressEvent"
close_idx = None
key_idx = None
for i in range(floating_start, len(lines)):
    if lines[i] == "def closeEvent(self, event):\n" and close_idx is None:
        close_idx = i
    if lines[i] == "def keyPressEvent(self, event):\n" and key_idx is None:
        key_idx = i

assert close_idx is not None, f"找不到 def closeEvent"
assert key_idx is not None, f"找不到 def keyPressEvent"
print(f"closeEvent 在第 {close_idx+1} 行 (1-based)")
print(f"keyPressEvent 在第 {key_idx+1} 行 (1-based)")

# 步骤 4：找 keyPressEvent 函数体结束
# keyPressEvent 体内应该是 12 空格缩进（def 4 + 类 4 = 8？不对，是 8+4=12）
# 找下一个 0 缩进的行
k = key_idx + 1
while k < len(lines) and (lines[k].startswith(" ") or lines[k].strip() == ""):
    k += 1
# k 是 keyPressEvent 函数体结束后的第一个 0 缩进行（空行+空行+class _FullscreenChart）
# 实际 k 会是连续空行中的第一个

# 步骤 5：找 _FullscreenChart 类起始（应该是 0 缩进的 class 行）
fullscreen_idx = None
for i in range(k, min(k + 5, len(lines))):
    if lines[i].startswith("class _FullscreenChart"):
        fullscreen_idx = i
        break
assert fullscreen_idx is not None, f"找不到 _FullscreenChart 类"

# keyPressEnd = 第一个 0 缩进行（应该是空行）
key_end = k
print(f"keyPressEvent 函数体结束在 {key_end+1} 行（该行 0 缩进）: {lines[key_end]!r}")
print(f"_FullscreenChart 在第 {fullscreen_idx+1} 行")

# 步骤 6：取游离段 floating_start ~ key_end
floating_block = lines[floating_start:key_end]

# 步骤 7：每行 +4 缩进
indented = []
for ln in floating_block:
    if ln.strip() == "":
        indented.append(ln)
    else:
        indented.append("    " + ln)

# 步骤 8：重组
# new_lines[0:fs_toggle_end] 包含 _on_fs_measure_toggle 函数 + 1 个空行
# 之后是 indented 块
# 之后是 key_end 起的所有行（含空行+class _FullscreenChart...）
new_lines = lines[0:floating_start]  # 包含 _on_fs_measure_toggle 函数 + 内部空行（最后是空行）
new_lines.extend(indented)            # 缩进后的游离段
new_lines.extend(lines[key_end:])     # 剩余部分（含类 _FullscreenChart 起始）

# 写入
new_src = "".join(new_lines)
p.write_text(new_src, encoding="utf-8")
print(f"OK: rewrote. Old line count={len(lines)}, new line count={len(new_lines)}")