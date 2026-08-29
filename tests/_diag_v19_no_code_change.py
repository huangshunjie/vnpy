"""
V19 诊断：完全不改代码，纯打印现有状态
- 检查 _KlineFullscreenWindow._interval 是否被设置
- 检查 _FullscreenChart 是否真有 _datetimes
- 检查 daily_bar_clicked 信号如何连
"""
import os
import re
import sys

base = r'c:\Users\11229\Documents\GitHub\vnpy'
ui = os.path.join(base, r'vnpy\strategy_condition\ui')

print("="*80)
print("V19 诊断：扫描 kline_view.py 关键信息")
print("="*80)

p = os.path.join(ui, 'kline_view.py')
src = open(p, encoding='utf-8').read()
lines = src.split('\n')

# 1. 找 _KlineFullscreenWindow.__init__
print("\n[1] _KlineFullscreenWindow.__init__ 中是否有 self._interval = ...？")
in_init = False
for i, ln in enumerate(lines, 1):
    if 'class _KlineFullscreenWindow' in ln:
        in_init = True
        init_start = i
        continue
    if in_init:
        if 'self._interval' in ln or 'self.interval' in ln:
            print(f"  L{i}: {ln.rstrip()}")
        if 'def ' in ln and 'def __init__' not in ln and i > init_start:
            in_init = False
            break

# 2. 找 _KlineFullscreenWindow 是否有 _on_outer_daily_bar_clicked
print("\n[2] 是否有 _on_outer_daily_bar_clicked？")
for i, ln in enumerate(lines, 1):
    if '_on_outer_daily_bar_clicked' in ln or 'outer_daily_bar_clicked' in ln:
        print(f"  L{i}: {ln.rstrip()}")

# 3. 找 _FullscreenChart.__init__ 中 _datetimes 的赋值
print("\n[3] _FullscreenChart 中 _datetimes 赋值：")
for i, ln in enumerate(lines, 1):
    if 'class _FullscreenChart' in ln or 'self._datetimes' in ln or 'self.datetimes' in ln:
        print(f"  L{i}: {ln.rstrip()}")

# 4. 找 KlineViewTab._on_fullscreen 中 datetimes 怎么传
print("\n[4] KlineViewTab._on_fullscreen：")
in_fn = False
for i, ln in enumerate(lines, 1):
    if 'def _on_fullscreen' in ln or 'def open_fullscreen' in ln:
        in_fn = True
        print(f"  L{i}: {ln.rstrip()}")
        continue
    if in_fn:
        print(f"  L{i}: {ln.rstrip()}")
        if 'def ' in ln and 'def _on_fullscreen' not in ln and 'def open_fullscreen' not in ln:
            break

# 5. 找 daily_bar_clicked 信号 connect 在哪些地方
print("\n[5] daily_bar_clicked 信号连接：")
for i, ln in enumerate(lines, 1):
    if 'daily_bar_clicked' in ln:
        print(f"  L{i}: {ln.rstrip()}")

# 6. 找 _FullscreenChart 是否有 focus_datetime 方法
print("\n[6] _FullscreenChart 是否有 focus_datetime 方法？")
for i, ln in enumerate(lines, 1):
    if 'class _FullscreenChart' in ln:
        for j in range(i, min(i+200, len(lines))):
            if 'def focus_datetime' in lines[j] or 'def _on_outer' in lines[j]:
                print(f"  L{j+1}: {lines[j].rstrip()}")
        break
print("\n[6b] 全文搜 focus_datetime 定义（在 _FullscreenChart 类内）：")
# 找到 class _FullscreenChart 起点和下一个 class/def 起点
start = None
end = None
for i, ln in enumerate(lines, 1):
    if 'class _FullscreenChart' in ln:
        start = i
    elif start and ('class ' in ln or (ln.startswith('def ') or ln.startswith('async def '))):
        end = i
        break
if start:
    chunk = '\n'.join(lines[start-1:end or len(lines)])
    for m in re.finditer(r'def (\w+)\(', chunk):
        print(f"  - def {m.group(1)}")
    if 'focus_datetime' in chunk:
        # 找具体行
        sub_lines = chunk.split('\n')
        for k, sl in enumerate(sub_lines, 1):
            if 'focus_datetime' in sl:
                print(f"  hit L{start-1+k}: {sl.rstrip()}")
    else:
        print("  ⚠ _FullscreenChart 内没有 focus_datetime 方法定义")

print("\n[7] 全文搜 _on_outer_daily_bar_clicked 实现：")
for i, ln in enumerate(lines, 1):
    if 'def _on_outer_daily_bar_clicked' in ln:
        # 输出整个方法
        for j in range(i, min(i+80, len(lines))):
            print(f"  L{j}: {lines[j-1].rstrip()}")
            if j > i and lines[j-1].startswith('    def ') and 'def _on_outer_daily_bar_clicked' not in lines[j-1]:
                break
        break

print("\n" + "="*80)
print("诊断完成")