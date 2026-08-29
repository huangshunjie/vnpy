"""
V20 终极修复：在 _KlineFullscreenWindow.__init__ 中根据 datetimes 实际间隔反推 self._interval。
原因：KlineViewTab 默认 _interval=DAILY，_PeriodMonitorPanel 也默认日线，
     导致全屏窗口拿到错误的 _interval。
     修复：用 datetimes[i+1]-datetimes[i] 的实际间隔反推 Interval 并覆盖 self._interval。
"""
import re
src_path = r'vnpy\strategy_condition\ui\kline_view.py'
src = open(src_path, encoding='utf-8').read()
orig_len = len(src)

# Step 1: 确保 Interval 已导入
if not re.search(r'^\s*from\s+vnpy\.trader\.constant\s+import.*Interval', src, re.MULTILINE):
    # 找现有的 from vnpy.trader.constant import ... 那一行
    m = re.search(r'^(from\s+vnpy\.trader\.constant\s+import\s+[^\n]+)$', src, re.MULTILINE)
    if m:
        line = m.group(1)
        # 已有 import，添加 Interval
        if not line.rstrip().endswith(','):
            new_line = line + ', Interval'
        else:
            new_line = line + ' Interval'
        src = src.replace(line, new_line, 1)
        print('[OK] Added Interval to existing import:', new_line)
    else:
        # 单独加一行
        src = 'from vnpy.trader.constant import Interval\n' + src
        print('[OK] Added standalone Interval import')
else:
    print('[OK] Interval already imported')

# Step 2: 在 marker 之后插入推断代码
marker = 'self._owner_monitor = None  # V4: 转发日线点击用'
idx = src.find(marker)
if idx < 0:
    marker = 'self._owner_monitor = None'
    idx = src.find(marker)
assert idx >= 0, 'marker not found'
print(f'marker idx = {idx}')

insert = '''        self._owner_monitor = None  # V4: 转发日线点击用

        # V20: 根据 datetimes 实际间隔反推 self._interval
        # 解决 KlineViewTab 默认 _interval=DAILY 的问题
        try:
            if datetimes is not None and len(datetimes) >= 2:
                _gap = datetimes[1] - datetimes[0]
                if hasattr(_gap, 'total_seconds'):
                    _secs = _gap.total_seconds()
                else:
                    _secs = float(_gap)
                if _secs <= 360:
                    _new_iv = Interval.MINUTE_5
                elif _secs <= 1200:
                    _new_iv = Interval.MINUTE_15
                elif _secs <= 4500:
                    _new_iv = Interval.HOUR_1
                else:
                    _new_iv = Interval.DAILY
                if getattr(self, '_interval', None) != _new_iv:
                    print(f'[V20-FS] 全屏窗口 _interval 推断: gap={_secs:.0f}s -> {_new_iv}')
                    self._interval = _new_iv
        except Exception as _e:
            print(f'[V20-FS] 推断 _interval 失败: {_e}')
'''
new_src = src.replace(marker, insert, 1)
assert new_src != src, 'replace failed'
open(src_path, 'w', encoding='utf-8').write(new_src)
print(f'[OK] V20 fix applied. {orig_len} -> {len(new_src)} bytes')

# Step 3: 语法验证
import ast
try:
    ast.parse(new_src)
    print('[OK] syntax check passed')
except SyntaxError as e:
    print(f'[FAIL] syntax error: {e}')
    raise