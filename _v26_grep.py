"""直接 grep 源文件，验证 V26 print 是否真的在 kline_view.py 中。"""
import os, re

path = 'vnpy/strategy_condition/ui/kline_view.py'
print(f'File: {path}')
print(f'Exists: {os.path.exists(path)}')
print(f'Size: {os.path.getsize(path) if os.path.exists(path) else "N/A"} bytes')
print('='*80)

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1) 找 [KlineView]
print('【1】含 [KlineView] 的行：')
hits = []
for i, line in enumerate(lines, start=1):
    if '[KlineView]' in line:
        hits.append((i, line.rstrip()))
        print(f'  L{i:4d}: {line.rstrip()}')
if not hits:
    print('  ❌ 没找到！')
print()

# 2) 找 [联动V26]
print('【2】含 [联动V26] 的行：')
hits2 = []
for i, line in enumerate(lines, start=1):
    if '[联动V26]' in line:
        hits2.append((i, line.rstrip()))
        print(f'  L{i:4d}: {line.rstrip()}')
if not hits2:
    print('  ❌ 没找到！')
print()

# 3) 找 [联动V25]
print('【3】含 [联动V25] 的行：')
hits3 = []
for i, line in enumerate(lines, start=1):
    if '[联动V25]' in line:
        hits3.append((i, line.rstrip()))
        print(f'  L{i:4d}: {line.rstrip()}')
if not hits3:
    print('  ❌ 没找到！')
print()

# 4) 找 [Monitor]
print('【4】含 [Monitor] 的行：')
hits4 = []
for i, line in enumerate(lines, start=1):
    if '[Monitor]' in line:
        hits4.append((i, line.rstrip()))
        print(f'  L{i:4d}: {line.rstrip()}')
if not hits4:
    print('  ❌ 没找到！')
print()

print('='*80)
print(f'小结: [KlineView]={len(hits)}个 | [联动V26]={len(hits2)}个 | [联动V25]={len(hits3)}个 | [Monitor]={len(hits4)}个')