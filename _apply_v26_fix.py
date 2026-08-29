"""V26 修复 - 直接基于 def 定位 (不依赖 print 标记)"""
import re
from pathlib import Path

TARGET = Path(r"vnpy\strategy_condition\ui\kline_view.py")
text = TARGET.read_text(encoding="utf-8")

# 1) 找 _dispatch_to_other_fullscreen 方法
m = re.search(r'    def _dispatch_to_other_fullscreen\(self, focus_dt, signals\):', text)
if not m:
    print("[V26] ERROR: 找不到 _dispatch_to_other_fullscreen def")
    raise SystemExit(1)
method_start = m.start()
rest = text[method_start+1:]
# 下一个 def (4 空格缩进) 或 class
nxt = re.search(r'\n    def |\nclass ', rest)
if not nxt:
    raise SystemExit(1)
method_end = method_start + 1 + nxt.start()
print(f"[V26] _dispatch_to_other_fullscreen: line {text[:method_start].count(chr(10))+1}-{text[:method_end].count(chr(10))+1}")
print(f"[V26] 当前方法体: {len(text[method_start:method_end])} chars")
for i, line in enumerate(text[method_start:method_end].splitlines()[:30], 1):
    print(f"  {i:3d}: {line}")

# 2) 替换为 V26 新方法
new_method = '''    def _dispatch_to_other_fullscreen(self, focus_dt, signals):
        """V26: 在 dispatch 循环中用 bars 数量精确判断每个候选全屏窗口是日线还是分钟线,
        对分钟线窗口走专用 focus_datetime(15:00, completed_daily=False) 逻辑,
        对日线窗口走原 V18 _on_outer_daily_bar_clicked 逻辑.
        避免 V18 dispatch 把分钟线全屏窗口误判为日线 (因为 2 个全屏窗口 _interval 都是 DAILY).
        """
        owner = getattr(self, "_owner_monitor", None)
        if owner is None:
            print(f"[联动V26][{type(self).__name__}] 没有 _owner_monitor, dispatch 跳过")
            return
        full_windows = list(getattr(owner, "_fullscreen_windows", []) or [])
        print(f"[联动V26] dispatch: 已注册全屏窗口 {len(full_windows)} 个, clicked_dt={focus_dt}")
        for win in full_windows:
            try:
                chart = getattr(win, "_chart", None)
                bars = chart._bars if chart is not None and hasattr(chart, "_bars") else []
                if len(bars) > 1000:
                    win_type = "minute"
                elif len(bars) > 0:
                    win_type = "daily"
                else:
                    win_type = "unknown"
                print(f"[联动V26]   候选 {type(win).__name__} bars={len(bars)} -> 识别为 {win_type}")
            except Exception as _exc:
                print(f"[联动V26]   候选识别异常: {_exc}")
                win_type = "unknown"

            if win_type == "minute":
                # V26: 分钟线全屏窗口必须把 focus_dt 改到收盘 15:00:00
                # 然后用 focus_datetime(completed_daily=False) 跳到该日最后一根 5m bar
                try:
                    minute_focus_dt = focus_dt.replace(hour=15, minute=0, second=0, microsecond=0) if hasattr(focus_dt, "replace") else focus_dt
                except Exception:
                    minute_focus_dt = focus_dt
                print(f"[联动V26]   分钟线窗口: 改 focus_dt={minute_focus_dt}, completed_daily=False")
                chart = getattr(win, "_chart", None)
                if chart is not None and hasattr(chart, "focus_datetime"):
                    try:
                        chart.focus_datetime(minute_focus_dt, completed_daily=False)
                        print(f"[联动V26]   ✓ 分钟线窗口 focus_datetime 完成")
                    except Exception as _exc:
                        print(f"[联动V26]   ✗ 分钟线窗口 focus_datetime 异常: {_exc}")
                else:
                    print(f"[联动V26]   ! 分钟线窗口没有 focus_datetime, 回退 _on_outer_daily_bar_clicked")
                    try:
                        win._on_outer_daily_bar_clicked(minute_focus_dt, signals)
                    except Exception as _exc:
                        print(f"[联动V26]   ! 回退也失败: {_exc}")
            elif win_type == "daily":
                # 日线全屏窗口：走原 V18 逻辑
                try:
                    win._on_outer_daily_bar_clicked(focus_dt, signals)
                    print(f"[联动V26]   ✓ 日线窗口 V18 dispatch 完成")
                except Exception as _exc:
                    print(f"[联动V26]   ✗ 日线窗口 V18 dispatch 异常: {_exc}")
            else:
                print(f"[联动V26]   未知类型窗口, 跳过")
        print(f"[联动V26] dispatch 结束")
'''

new_text = text[:method_start] + new_method + text[method_end:]
print(f"[V26] ✓ 替换 _dispatch_to_other_fullscreen 方法: {len(text[method_start:method_end])} -> {len(new_method)} chars")

# 3) 给 _on_outer_daily_bar_clicked 加保险: 防止其他调用方也走错
# 找该方法 def
m2 = re.search(r'    def _on_outer_daily_bar_clicked\(self, focus_dt, signals\) -> None:', new_text)
if m2:
    s2 = m2.start()
    rest2 = new_text[s2+1:]
    nxt2 = re.search(r'\n    def |\nclass ', rest2)
    if nxt2:
        e2 = s2 + 1 + nxt2.start()
        old2 = new_text[s2:e2]
        # 在 docstring 之后插入保险
        new2 = old2.replace(
            '        """V        print(f"[联动V24]',
            '        """V26 保险: 如果是分钟线窗口且 focus_dt 是 00:00:00 改到 15:00:00。\n        try:\n            bars_self = self._chart._bars if hasattr(self, "_chart") and hasattr(self._chart, "_bars") else []\n            if len(bars_self) > 1000 and getattr(focus_dt, "hour", -1) == 0 and getattr(focus_dt, "minute", -1) == 0:\n                focus_dt = focus_dt.replace(hour=15, minute=0, second=0, microsecond=0)\n                print(f"[联动V26][保险] 分钟线窗口+00:00 focus_dt -> 改到 15:00:00={focus_dt}")\n        except Exception as _v26_exc:\n            print(f"[联动V26][保险] 异常: {_v26_exc}")\n        """V        print(f"[联动V24]"'
        )
        if new2 != old2:
            new_text = new_text[:s2] + new2 + new_text[e2:]
            print("[V26] ✓ _on_outer_daily_bar_clicked 已加 V26 保险")
        else:
            print("[V26] ! _on_outer_daily_bar_clicked 保险未匹配 (跳过)")

TARGET.write_text(new_text, encoding="utf-8")
print(f"[V26] ✓ 已写入 {TARGET}")

# 4) 语法检查
import ast
try:
    ast.parse(new_text, str(TARGET))
    print("[V26] ✓ 语法检查通过")
except SyntaxError as se:
    print(f"[V26] ✗ 语法错误: {se}")