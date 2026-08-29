# -*- coding: utf-8 -*-
"""
V24 修复脚本：直接修改源码，不依赖 GUI 文本编辑器。

修复内容：
1. condition_monitor_widget.py：重写 _focus_minute_fullscreen_window（三段独立保险 A/B/C）
2. condition_monitor_widget.py：升级 banner 版本号
3. kline_view.py：_KlineFullscreenWindow.__init__ 加 bars 间隔 fallback（V24-FS 推断）
4. kline_view.py：_on_outer_daily_bar_clicked 加 debug print
"""
import re
import os
import sys
import io

# 强制 stdout utf-8（Windows 中文 banner 打印可能乱码）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.abspath(__file__))
CMW = os.path.join(BASE, 'vnpy', 'strategy_condition', 'ui', 'condition_monitor_widget.py')
KV  = os.path.join(BASE, 'vnpy', 'strategy_condition', 'ui', 'kline_view.py')

print("=" * 80)
print("V24 patch script")
print("=" * 80)
print(f"CMW: {CMW}")
print(f"KV:  {KV}")


# ============================================================================
# 改动 1+2：condition_monitor_widget.py
# ============================================================================
with open(CMW, 'r', encoding='utf-8') as f:
    cmw_content = f.read()

# 改动 1：升级 banner 版本号
old_banner = '_BANNER_VERSION = "Monitor日线↔分钟联动 V23 (2026-08-25_00-05) — 识别分钟线全屏窗口改用负向判断（!= DAILY/WEEKLY/MONTHLY）"'
new_banner = '_BANNER_VERSION = "Monitor日线↔分钟联动 V24 (2026-08-25_14-30) — 三段独立保险（A 负向 + B bars 间隔 + C 兜底）"'

if old_banner in cmw_content:
    cmw_content = cmw_content.replace(old_banner, new_banner)
    print("[1] banner 版本号已升级 V23 -> V24")
else:
    print("[1] WARN: banner 版本号未找到，请手动确认")


# 改动 2：重写 _focus_minute_fullscreen_window
# 找到旧方法定义（V15 + V23 改版）并整段替换
old_method_marker_start = '    def _focus_minute_fullscreen_window(self, clicked_dt):'
old_method_marker_end_str = '    def _dim_fullscreen_windows(self, opacity: float = 0.25, ms: int = 400):'

new_method = '''    def _focus_minute_fullscreen_window(self, clicked_dt):
        """V24 三段独立保险：日线全屏 → 分钟线全屏跳转。

        V1-V23 反复修复的根因：_KlineFullscreenWindow._interval 在某些路径下
        会被错误推断成 DAILY，导致 V15 的"严格匹配"和 V23 的"负向判断"都失败。

        V24 方案（每段独立可验证）：

        - 路径A（V23 负向判断）：_interval 不是 DAILY/WEEKLY/MONTHLY → 当分钟线
        - 路径B（V24 新增 - bars 间隔反推）：如果 _interval 看起来是 DAILY，
          但 bars 实际间隔 < 半天 → 强制判定为分钟线
        - 路径C（V24 新增 - bars 数量兜底）：上面两条都失败时，
          bars 数量最多的全屏窗口（分钟线 20000 根 >> 日线 1584 根）→ 视为分钟线

        每段都有独立 print 输出，调试时贴 banner 就能立刻定位走的是哪条。
        """
        try:
            from vnpy.trader.constant import Interval

            # 1) 收集"全屏窗口列表"
            fullscreen_windows = list(getattr(self, '_fullscreen_windows', []) or [])
            if not fullscreen_windows:
                print(f"[联动V24] 没有任何已注册全屏窗口，无法跳转")
                return

            # 2) 打印所有候选窗口信息（用于诊断）
            win_info = []
            for w in fullscreen_windows:
                w_iv = getattr(w, '_interval', None)
                w_chart = getattr(w, '_chart', None)
                w_bars = getattr(w_chart, '_bars', None) if w_chart else None
                w_bars_n = len(w_bars) if w_bars else 0
                win_info.append(
                    f"(type={type(w).__name__}, _interval={w_iv}, bars={w_bars_n})"
                )
            print(f"[联动V24] 候选全屏窗口 {len(fullscreen_windows)} 个: {win_info}")

            # ── 路径A：V23 负向判断 ──
            minute_fs_A = None
            for w in fullscreen_windows:
                iv = getattr(w, '_interval', None)
                if iv is None:
                    continue
                if iv in (Interval.DAILY, Interval.WEEKLY, Interval.MONTHLY):
                    print(f"[联动V24] 路径A: 跳过 {type(w).__name__}._interval={iv} (视为日线)")
                    continue
                minute_fs_A = w
                print(f"[联动V24] 路径A命中: {type(w).__name__}._interval={iv} → 视为分钟线全屏 ✓")
                break

            # ── 路径B：V24 新增 - 用 bars 实际间隔反推 ──
            minute_fs_B = None
            if minute_fs_A is None:
                for w in fullscreen_windows:
                    w_chart = getattr(w, '_chart', None)
                    bars = getattr(w_chart, '_bars', None) if w_chart else None
                    if not bars or len(bars) < 2:
                        continue
                    b0_dt = getattr(bars[0], 'datetime', None)
                    b1_dt = getattr(bars[1], 'datetime', None)
                    if b0_dt is None or b1_dt is None:
                        continue
                    try:
                        gap = (b1_dt - b0_dt).total_seconds()
                    except Exception:
                        continue
                    # 间隔 < 半天 → 一定是分钟线
                    if gap < 86400 * 0.5:
                        minute_fs_B = w
                        print(f"[联动V24] 路径B命中: {type(w).__name__} bars={len(bars)} "
                              f"gap={gap:.0f}s → 强制判定为分钟线全屏 ✓")
                        break

            # ── 路径C：V24 新增 - bars 数量兜底 ──
            # 日线 1584 根 vs 分钟线 20000 根，分钟线 bar 数远大于日线
            minute_fs_C = None
            if minute_fs_A is None and minute_fs_B is None:
                max_bars = -1
                for w in fullscreen_windows:
                    w_chart = getattr(w, '_chart', None)
                    bars = getattr(w_chart, '_bars', None) if w_chart else None
                    if not bars:
                        continue
                    n = len(bars)
                    if n > max_bars:
                        max_bars = n
                        minute_fs_C = w
                if minute_fs_C is not None and max_bars > 1000:
                    print(f"[联动V24] 路径C兜底命中: {type(minute_fs_C).__name__} "
                          f"bars={max_bars}（最多）→ 视为分钟线全屏 ✓")

            # ── 选择最终目标：A > B > C ──
            minute_fs = minute_fs_A or minute_fs_B or minute_fs_C
            if minute_fs is None:
                print(f"[联动V24] A/B/C 三条路径都没找到分钟线全屏窗口，放弃跳转")
                return

            # 3) 把分钟线全屏窗口置顶（不被日线全屏挡住）
            try:
                if minute_fs.isMinimized():
                    minute_fs.showNormal()
                minute_fs.showMaximized()
                minute_fs.raise_()
                minute_fs.activateWindow()
            except Exception as _raise_exc:
                print(f"[联动V24] raise_/activateWindow 失败: {_raise_exc}")

            # 4) 跳到 clicked_dt 的中心
            try:
                chart = getattr(minute_fs, '_chart', None)
                if chart is not None and hasattr(chart, 'focus_datetime'):
                    # focus_datetime(clicked_dt) 由 KlineChartWidget/_FullscreenChart 提供：
                    # 会把 x 范围设置为以 clicked_dt 为中心的窗口
                    chart.focus_datetime(clicked_dt, completed_daily=False)
                    print(f"[联动V24] ✓ 跳转到 {type(minute_fs).__name__} "
                          f"({clicked_dt.date()}) 中心完成")
                else:
                    print(f"[联动V24] ✗ {type(minute_fs).__name__} 没有 chart.focus_datetime 接口")
            except Exception as _focus_exc:
                print(f"[联动V24] focus_datetime 失败: {_focus_exc}")
                import traceback
                traceback.print_exc()

        except Exception as e:
            print(f"[联动V24] _focus_minute_fullscreen_window 顶层失败: {e}")
            import traceback
            traceback.print_exc()

'''

# 找到旧方法的位置（用 marker_start + 下一个 def 之间的内容）
start_idx = cmw_content.find(old_method_marker_start)
end_marker_idx = cmw_content.find(old_method_marker_end_str)

if start_idx < 0 or end_marker_idx < 0:
    print(f"[2] ERROR: 找不到旧方法位置 start={start_idx} end={end_marker_idx}")
    sys.exit(1)

# 替换
cmw_content_new = cmw_content[:start_idx] + new_method + cmw_content[end_marker_idx:]

# 写回
with open(CMW, 'w', encoding='utf-8') as f:
    f.write(cmw_content_new)
print(f"[2] _focus_minute_fullscreen_window 已重写为 V24 三段保险")
print(f"    旧位置: {start_idx} -> 新位置: {end_marker_idx - start_idx} 字符被替换")


# ============================================================================
# 改动 3：kline_view.py
# ============================================================================
with open(KV, 'r', encoding='utf-8') as f:
    kv_content = f.read()

# 改动 3a：在 _KlineFullscreenWindow.__init__ 中，V20 推断 _interval 的代码块
# 后追加 bars 间隔 fallback
v20_block_marker_start = '        # V20: 根据 datetimes 实际间隔反推 self._interval'
v20_block_marker_end = '''        try:
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
            print(f'[V20-FS] 推断 _interval 失败: {_e}')'''

if v20_block_marker_start in kv_content and v20_block_marker_end in kv_content:
    # 在 v20_block_end 之后追加 V24 fallback
    new_fallback = '''

        # V24 新增：datetimes 不可用时，fallback 到 bars 间隔反推
        # 解决 V20 推断路径下 _interval 仍被错误设置成 DAILY 的情况
        try:
            from vnpy.trader.constant import Interval as _Iv
            cur_iv = getattr(self, '_interval', None)
            cur_iv_ok = cur_iv is not None and cur_iv not in (_Iv.DAILY, _Iv.WEEKLY, _Iv.MONTHLY)
            if not cur_iv_ok:
                # 用 self._chart._bars 实际间隔反推
                _chart_bars = None
                if hasattr(self, '_chart') and self._chart is not None:
                    _chart_bars = getattr(self._chart, '_bars', None) or getattr(self._chart, '_kline_data', None)
                if _chart_bars and len(_chart_bars) >= 2:
                    _b0 = _chart_bars[0]
                    _b1 = _chart_bars[1]
                    _b0_dt = getattr(_b0, 'datetime', None) or getattr(_b0, 'dt', None)
                    _b1_dt = getattr(_b1, 'datetime', None) or getattr(_b1, 'dt', None)
                    if _b0_dt is not None and _b1_dt is not None:
                        try:
                            _bar_gap = (_b1_dt - _b0_dt).total_seconds()
                        except Exception:
                            _bar_gap = 0
                        if _bar_gap < 86400 * 0.5:
                            # 一定是分钟线
                            if _bar_gap <= 360:
                                self._interval = _Iv.MINUTE_5
                            elif _bar_gap <= 1200:
                                self._interval = _Iv.MINUTE_15
                            elif _bar_gap <= 4500:
                                self._interval = _Iv.HOUR_1
                            else:
                                self._interval = _Iv.MINUTE_5
                            print(f'[V24-FS] bars 间隔反推 _interval: '
                                  f'bars={len(_chart_bars)} gap={_bar_gap:.0f}s -> {self._interval}')
        except Exception as _e_v24:
            print(f'[V24-FS] bars 间隔反推失败: {_e_v24}')'''

    kv_content_new = kv_content.replace(v20_block_marker_end, v20_block_marker_end + new_fallback)
    with open(KV, 'w', encoding='utf-8') as f:
        f.write(kv_content_new)
    print("[3a] kline_view.py _KlineFullscreenWindow.__init__ V24 bars 间隔 fallback 已追加")
else:
    print("[3a] ERROR: 找不到 V20 推断块，跳过 V24 fallback 追加")


# 改动 3b：_on_outer_daily_bar_clicked 加 debug print
# 找到方法定义位置
# 我们用更宽松的标记
old_outer_start = '    def _on_outer_daily_bar_clicked(self, focus_dt, signals) -> None:'
old_outer_first_line_marker = '        """V8 全屏窗口监听主 Monitor 的日线点击，独立移动 vline（无半透明、无中转）。'

if old_outer_start in kv_content and old_outer_first_line_marker in kv_content:
    # 在 docstring 后找一个合适的插入点
    # docstring 结束的 """ 后第一行
    docstring_end_marker = '        """\n'
    # 找 docstring 结束位置
    idx_doc = kv_content.find(old_outer_start)
    idx_doc_end = kv_content.find(old_outer_first_line_marker, idx_doc)
    if idx_doc_end > 0:
        # docstring 的 """ 紧跟着在 first_line 后面
        # 找 docstring 结束的 """
        idx_close = kv_content.find('        """', idx_doc_end)
        if idx_close > 0:
            insert_pos = idx_close + len('        """\n')
            debug_print = '''        print(f"[联动V24][{type(self).__name__}] 收到 daily_bar_clicked: "
              f"focus_dt={focus_dt}, self._interval={getattr(self, '_interval', None)}")
'''
            kv_content_with_debug = (
                kv_content[:insert_pos] + debug_print + kv_content[insert_pos:]
            )
            with open(KV, 'w', encoding='utf-8') as f:
                f.write(kv_content_with_debug)
            print("[3b] kline_view.py _on_outer_daily_bar_clicked debug print 已加入")
        else:
            print("[3b] WARN: 找不到 docstring 结束符，跳过 debug print")
    else:
        print("[3b] WARN: 找不到 docstring 起始符，跳过 debug print")
else:
    print("[3b] WARN: 找不到 _on_outer_daily_bar_clicked 方法定义，跳过 debug print")


# ============================================================================
# 语法检查
# ============================================================================
print("\n" + "=" * 80)
print("语法检查")
print("=" * 80)

import py_compile
try:
    py_compile.compile(CMW, doraise=True)
    print(f"[OK] {os.path.basename(CMW)} 语法正确")
except py_compile.PyCompileError as e:
    print(f"[ERROR] {os.path.basename(CMW)} 语法错误: {e}")
    sys.exit(1)

try:
    py_compile.compile(KV, doraise=True)
    print(f"[OK] {os.path.basename(KV)} 语法正确")
except py_compile.PyCompileError as e:
    print(f"[ERROR] {os.path.basename(KV)} 语法错误: {e}")
    sys.exit(1)


# ============================================================================
# 清理 pycache
# ============================================================================
print("\n" + "=" * 80)
print("清理 __pycache__")
print("=" * 80)
import shutil
for root, dirs, files in os.walk(os.path.join(BASE, 'vnpy', 'strategy_condition', 'ui')):
    for d in dirs:
        if d == '__pycache__':
            full = os.path.join(root, d)
            print(f"  删除 {full}")
            shutil.rmtree(full, ignore_errors=True)
print("[OK] __pycache__ 已清理")


# ============================================================================
# 总结
# ============================================================================
print("\n" + "=" * 80)
print("V24 修复应用完成 ✓")
print("=" * 80)
print("""
验证清单：
1. 启动 VNPY，确认 banner 显示 V24
2. 打开 Monitor → 加载双周期数据
3. 点"日线全屏"按钮
4. 点"分钟线全屏"按钮
5. 在日线全屏上点一根 K 线
6. 观察终端输出，定位走的是哪条路径：
   - [联动V24] 路径A命中：_interval 直接识别为非 DAILY
   - [联动V24] 路径B命中：bars 间隔反推识别
   - [联动V24] 路径C兜底命中：bars 数量兜底识别
7. 观察分钟线全屏窗口：vline 应该跳到你点的日线对应日期的中间
""")