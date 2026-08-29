#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V21: Final indent fix
- Read raw bytes
- Find the misindented line
- Replace leading 16 spaces with 8 spaces
- Write back
"""
import sys

PATH = r'vnpy\strategy_condition\ui\kline_view.py'

with open(PATH, 'rb') as f:
    raw = f.read()

needle = b'self._owner_monitor = None  # V4:'
idx = raw.find(needle)
print(f'[V21] needle offset: {idx}')

# Find start of line
line_start = raw.rfind(b'\n', 0, idx) + 1
print(f'[V21] line_start: {line_start}')
print(f'[V21] line bytes: {raw[line_start:line_start+80]!r}')

# Check leading whitespace before 'self._owner_monitor'
prefix = raw[line_start:idx]
print(f'[V21] prefix bytes: {prefix!r}')
print(f'[V21] prefix len: {len(prefix)}')

# If 16 spaces, replace with 8 spaces
if prefix == b'                ':  # 16 spaces
    new_raw = raw[:line_start] + b'        ' + raw[idx:]  # 8 spaces
    print(f'[V21] FIXING: 16 spaces -> 8 spaces')
    with open(PATH, 'wb') as f:
        f.write(new_raw)
    print(f'[V21] DONE. new file size: {len(new_raw)}')
elif prefix == b'        ':  # 8 spaces
    print(f'[V21] ALREADY 8 spaces. no change needed.')
else:
    print(f'[V21] UNEXPECTED leading ws: {prefix!r}')
    sys.exit(1)

# Validate syntax
src = new_raw.decode('utf-8')
import ast
try:
    ast.parse(src)
    print(f'[V21] syntax OK')
except SyntaxError as e:
    print(f'[V21] SYNTAX ERROR: {e}')
    sys.exit(2)

# Show context
arr = src.splitlines()
print('--- after fix, lines 1220-1230 ---')
for i, l in enumerate(arr[1219:1231], start=1220):
    print(f'{i:4d}|{l!r}')