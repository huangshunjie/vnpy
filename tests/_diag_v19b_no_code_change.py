"""V19b 诊断：UTF-8 输出，固定 stdout"""
import os, sys, re

# 强制 UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

base = r'c:\Users\11229\Documents\GitHub\vnpy'
ui = os.path.join(base, r'vnpy\strategy_condition\ui')
p = os.path.join(ui, 'kline_view.py')
src = open(p, encoding='utf-8').read()
lines = src.split('\n')

print("="*80)
print("V19b 诊断：kline_view.py 关键信息")
print("="*80)

# [1] _KlineFullscreenWindow.__init__ 是否有 self._interval
print("\n[1] _KlineFullscreenWindow.__init__ 中 self._interval 赋值：")
in_init = False
for i, ln in enumerate(lines, 1):
    if re.search(r'class _KlineFullscreenWindow', ln):
        in_init = True
        init_start = i
        continue
    if in_init:
        if 'self._interval' in ln or 'self.interval' in ln:
            print(f"  L{i}: {ln.rstrip()}")
        if re.search(r'^    def \w+', ln) and 'def __init__' not in ln and i > init_start:
            in_init = False
            break

# [2] 全文 daily_bar_clicked
print("\n[2] daily_bar_clicked 信号引用：")
for i, ln in enumerate(lines, 1):
    if 'daily_bar_clicked' in ln:
        print(f"  L{i}: {ln.rstrip()}")

# [3] _on_outer_daily_bar_clicked 实现全文
print("\n[3] _on_outer_daily_bar_clicked 全文：")
for i, ln in enumerate(lines, 1):
    if 'def _on_outer_daily_bar_clicked' in ln:
        for j in range(i, min(i+80, len(lines))):
            print(f"  L{j}: {lines[j-1].rstrip()}")
            if j > i and re.search(r'^    def \w+', lines[j-1]) and '_on_outer_daily_bar_clicked' not in lines[j-1]:
                break
        break

# [4] _FullscreenChart 类内 def 列表
print("\n[4] _FullscreenChart 类内方法列表：")
start = None
end = None
for i, ln in enumerate(lines, 1):
    if re.search(r'class _FullscreenChart', ln):
        start = i
    elif start and (re.search(r'^class ', ln) or (re.search(r'^def ', ln) and 'class _FullscreenChart' not in ln)):
        end = i
        break
if start:
    chunk = '\n'.join(lines[start-1:end or len(lines)])
    methods = re.findall(r'def (\w+)\(', chunk)
    for m in methods:
        print(f"  - {m}")
    if 'focus_datetime' not in methods:
        print("  >>> _FullscreenChart 没有 focus_datetime 方法 (确认)")

# [5] _KlineFullscreenWindow 类内方法列表
print("\n[5] _KlineFullscreenWindow 类内方法列表：")
start = None
end = None
for i, ln in enumerate(lines, 1):
    if re.search(r'class _KlineFullscreenWindow', ln):
        start = i
    elif start and re.search(r'^class ', ln):
        end = i
        break
if start:
    chunk = '\n'.join(lines[start-1:end or len(lines)])
    methods = re.findall(r'def (\w+)\(', chunk)
    for m in methods:
        print(f"  - {m}")

# [6] L1133 上下文
print("\n[6] L1130-1150 上下文（owner_monitor.daily_bar_clicked.connect）：")
for i in range(1125, min(1155, len(lines))+1):
    print(f"  L{i}: {lines[i-1].rstrip()}")

# [7] L1440-1530 _on_outer_daily_bar_clicked 上下文
print("\n[7] L1500-1535（_on_outer_daily_bar_clicked 收尾）：")
for i in range(1495, min(1535, len(lines))+1):
    print(f"  L{i}: {lines[i-1].rstrip()}")

print("\n" + "="*80)