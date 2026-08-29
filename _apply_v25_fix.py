# -*- coding: utf-8 -*-
"""
V25 patch 脚本：修复 V24 的两个致命问题 + 大量诊断 print。

V24 失败原因（终端日志已证）：
1. AttributeError: type object 'Interval' has no attribute 'MONTHLY'
   → 路径A 第1行就崩，整个 try 被 except 吞掉
   → 路径B/C 根本不被执行
2. 分钟线全屏窗口的 _interval 仍是 DAILY（V20 推断 V24-FS fallback 都失败）
3. 主 Monitor 内嵌分钟面板跳转成功（V16），但全屏分钟窗口不动

V25 修复方案：
1. 路径A 防御性：try 包裹，加 hasattr 防御 MONTHLY
2. 路径A 拆出来：路径A 失败不影响路径B/C
3. 路径B 永远执行（不再依赖路径A 失败）
4. 路径C 永远执行（兜底）
5. 每个候选窗口都打 print（含 type, _interval, bars 数量, bars 间隔）
6. 每个 if 关键分支都打 print
7. focus_datetime 前后都打 print
8. 路径命中/失败/异常 都打 print
"""
import os
import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.abspath(__file__))
CMW = os.path.join(BASE, 'vnpy', 'strategy_condition', 'ui', 'condition_monitor_widget.py')

print("=" * 80)
print("V25 patch 脚本 - 加防御性 + 大量诊断 print")
print("=" * 80)
print(f"目标文件: {CMW}")


# ============================================================================
# 改动 1：升级 banner
# ============================================================================
with open(CMW, 'r', encoding='utf-8') as f:
    cmw_content = f.read()

old_banner = '_BANNER_VERSION = "Monitor日线↔分钟联动 V24 (2026-08-25_14-30) — 三段独立保险（A 负向 + B bars 间隔 + C 兜底）"'
new_banner = '_BANNER_VERSION = "Monitor日线↔分钟联动 V25 (2026-08-25_15-00) — 路径A 防御性 + 路径B/C 必执行 + 大量诊断 print"'

if old_banner in cmw_content:
    cmw_content = cmw_content.replace(old_banner, new_banner)
    print("[1] banner V24 -> V25 OK")
else:
    print("[1] WARN: banner V24 未找到")


# ============================================================================
# 改动 2：用防御性 + 拆 try 的 V25 版本替换 V24 的 _focus_minute_fullscreen_window
# ============================================================================
# 找到方法结束位置（下一个 def 或 class 之前）
method_start_marker = '    def _focus_minute_fullscreen_window(self, clicked_dt):'

# 找到方法起点
start_idx = cmw_content.find(method_start_marker)
if start_idx < 0:
    print("[2] ERROR: 找不到 _focus_minute_fullscreen_window 方法起点")
    sys.exit(1)

# 找到方法结束位置：从 start_idx 之后找下一个 "    def " 或 "    # " 顶头
# 我们直接用后面那个 marker：下一个 def _dim_fullscreen_windows
end_marker = '    def _dim_fullscreen_windows(self, opacity: float = 0.25, ms: int = 400):'
end_idx = cmw_content.find(end_marker, start_idx)
if end_idx < 0:
    print("[2] ERROR: 找不到 _dim_fullscreen_windows（方法结束 marker）")
    sys.exit(1)

print(f"[2] 找到方法: start={start_idx} end={end_idx}, 共 {end_idx - start_idx} 字符")


# 构造 V25 新方法
new_method = '''    def _focus_minute_fullscreen_window(self, clicked_dt):
        """V25 防御性 + 三段独立保险 + 大量诊断 print。

        V24 失败根因（终端日志已证）：
        AttributeError: type object 'Interval' has no attribute 'MONTHLY'
        → 路径A 第1行就崩，整个 try 块被 except 吞掉
        → 路径B/C 永远不被执行
        → 结果：A/B/C 三条都没机会

        V25 修复：
        1. 路径A 用 hasattr 防御 MONTHLY 不存在的问题
        2. 路径A/B/C 每个都独立 try，单个失败不影响其他
        3. 路径B 永远执行（即使 A 命中，B 也作为验证日志）
        4. 路径C 永远执行（兜底）
        5. 每个关键点都打 print（候选窗口、路径A/B/C 命中/失败、focus_datetime 前后）
        """
        # ── 入口 print ──
        print(f"[联动V25][_focus_minute_fullscreen_window] 入口 clicked_dt={clicked_dt}")

        # ── 1) 收集全屏窗口列表（防御性） ──
        try:
            fullscreen_windows = list(getattr(self, '_fullscreen_windows', []) or [])
        except Exception as e:
            print(f"[联动V25] 收集 _fullscreen_windows 失败: {e}")
            fullscreen_windows = []

        if not fullscreen_windows:
            print(f"[联动V25] 没有任何已注册全屏窗口（_fullscreen_windows 为空）")
            print(f"[联动V25] 提示：请检查 _KlineFullscreenWindow 创建后是否调用了 self._register_fullscreen_window()")
            return

        # ── 2) 打印所有候选窗口信息（深度诊断） ──
        print(f"[联动V25] ============================================================")
        print(f"[联动V25] 候选全屏窗口 {len(fullscreen_windows)} 个：")
        for i, w in enumerate(fullscreen_windows):
            w_type = type(w).__name__
            w_id = id(w)
            w_iv = getattr(w, '_interval', '<NO _interval>')
            w_chart = getattr(w, '_chart', None)
            w_chart_type = type(w_chart).__name__ if w_chart else '<NO _chart>'
            w_bars = getattr(w_chart, '_bars', None) if w_chart else None
            w_bars_n = len(w_bars) if w_bars else 0
            w_gap = '<N/A>'
            if w_bars and len(w_bars) >= 2:
                try:
                    b0_dt = getattr(w_bars[0], 'datetime', None)
                    b1_dt = getattr(w_bars[1], 'datetime', None)
                    if b0_dt and b1_dt:
                        w_gap = f"{(b1_dt - b0_dt).total_seconds():.0f}s"
                except Exception:
                    pass
            print(f"[联动V25]   [{i}] type={w_type} id=0x{w_id:X} _interval={w_iv} "
                  f"chart_type={w_chart_type} bars={w_bars_n} bars_gap={w_gap}")
        print(f"[联动V25] ============================================================")

        # ── 3) 防御性准备：Interval 黑名单 ──
        try:
            from vnpy.trader.constant import Interval
            # V25 防御：MONTHLY 可能不存在
            _DAILY = getattr(Interval, 'DAILY', None)
            _WEEKLY = getattr(Interval, 'WEEKLY', None)
            _MONTHLY = getattr(Interval, 'MONTHLY', None)
            blacklist = tuple(iv for iv in (_DAILY, _WEEKLY, _MONTHLY) if iv is not None)
            print(f"[联动V25] Interval 黑名单 = {[str(x) for x in blacklist]}")
        except Exception as e:
            print(f"[联动V25] 导入 Interval 失败: {e}，使用字符串黑名单")
            Interval = None
            blacklist = ('d', 'w', 'm', 'D', 'W', 'M', 'DAILY', 'WEEKLY', 'MONTHLY')

        # ── 4) 路径A：负向判断（独立 try，不影响 B/C） ──
        minute_fs_A = None
        try:
            for i, w in enumerate(fullscreen_windows):
                iv = getattr(w, '_interval', None)
                if iv is None:
                    print(f"[联动V25] 路径A: 候选[{i}] {type(w).__name__}._interval=None → 跳过")
                    continue
                if iv in blacklist:
                    print(f"[联动V25] 路径A: 候选[{i}] {type(w).__name__}._interval={iv} 命中黑名单 → 视为日线，跳过")
                    continue
                minute_fs_A = w
                print(f"[联动V25] 路径A命中: 候选[{i}] {type(w).__name__}._interval={iv} → 视为分钟线 ✓")
                break
            if minute_fs_A is None:
                print(f"[联动V25] 路径A: 所有候选的 _interval 都在黑名单（都是 DAILY/WEEKLY/MONTHLY）→ 路径A 未命中")
        except Exception as e_A:
            print(f"[联动V25] 路径A 异常: {e_A}")
            import traceback
            traceback.print_exc()

        # ── 5) 路径B：bars 间隔反推（独立 try，强制执行） ──
        minute_fs_B = None
        try:
            for i, w in enumerate(fullscreen_windows):
                w_chart = getattr(w, '_chart', None)
                bars = getattr(w_chart, '_bars', None) if w_chart else None
                if not bars or len(bars) < 2:
                    print(f"[联动V25] 路径B: 候选[{i}] {type(w).__name__} bars=<{len(bars) if bars else 0}> → 跳过")
                    continue
                b0_dt = getattr(bars[0], 'datetime', None)
                b1_dt = getattr(bars[1], 'datetime', None)
                if b0_dt is None or b1_dt is None:
                    print(f"[联动V25] 路径B: 候选[{i}] {type(w).__name__} bars[0/1].datetime=None → 跳过")
                    continue
                try:
                    gap = (b1_dt - b0_dt).total_seconds()
                except Exception:
                    print(f"[联动V25] 路径B: 候选[{i}] {type(w).__name__} bars datetime 不可减 → 跳过")
                    continue
                # 间隔 < 半天 → 一定是分钟线
                if gap < 86400 * 0.5:
                    minute_fs_B = w
                    print(f"[联动V25] 路径B命中: 候选[{i}] {type(w).__name__} bars={len(bars)} "
                          f"gap={gap:.0f}s → 强制判定为分钟线 ✓")
                    break
                else:
                    print(f"[联动V25] 路径B: 候选[{i}] {type(w).__name__} bars={len(bars)} "
                          f"gap={gap:.0f}s ≥ 半天 → 视为日线")
            if minute_fs_B is None and not minute_fs_A:
                print(f"[联动V25] 路径B: 所有候选的 bars 间隔 ≥ 半天 → 路径B 未命中")
        except Exception as e_B:
            print(f"[联动V25] 路径B 异常: {e_B}")
            import traceback
            traceback.print_exc()

        # ── 6) 路径C：bars 数量兜底（独立 try，强制执行） ──
        minute_fs_C = None
        try:
            # 日线 1584 根 vs 分钟线 20000 根，分钟线 bar 数远大于日线
            max_bars = -1
            for i, w in enumerate(fullscreen_windows):
                w_chart = getattr(w, '_chart', None)
                bars = getattr(w_chart, '_bars', None) if w_chart else None
                if not bars:
                    print(f"[联动V25] 路径C: 候选[{i}] {type(w).__name__} bars=None → 跳过")
                    continue
                n = len(bars)
                print(f"[联动V25] 路径C: 候选[{i}] {type(w).__name__} bars={n}")
                if n > max_bars:
                    max_bars = n
                    minute_fs_C = w
            if minute_fs_C is not None and max_bars > 1000:
                print(f"[联动V25] 路径C兜底命中: {type(minute_fs_C).__name__} bars={max_bars}（最多，>1000）"
                      f"→ 视为分钟线 ✓")
            elif minute_fs_C is not None:
                print(f"[联动V25] 路径C: 最多 bars={max_bars}，但 < 1000，不当兜底用")
                minute_fs_C = None
        except Exception as e_C:
            print(f"[联动V25] 路径C 异常: {e_C}")
            import traceback
            traceback.print_exc()

        # ── 7) 选择最终目标：A > B > C ──
        minute_fs = minute_fs_A or minute_fs_B or minute_fs_C
        if minute_fs is None:
            print(f"[联动V25] ★★★ 失败 ★★★ A/B/C 三条路径都没找到分钟线全屏窗口，放弃跳转")
            return

        chosen_via = 'A' if minute_fs_A is minute_fs else ('B' if minute_fs_B is minute_fs else 'C')
        print(f"[联动V25] ✓ 最终选中: {type(minute_fs).__name__} (走路径{chosen_via})")

        # ── 8) 置顶分钟线全屏窗口 ──
        try:
            if minute_fs.isMinimized():
                minute_fs.showNormal()
            minute_fs.showMaximized()
            minute_fs.raise_()
            minute_fs.activateWindow()
            print(f"[联动V25] 置顶 {type(minute_fs).__name__} 完成")
        except Exception as _raise_exc:
            print(f"[联动V25] 置顶失败: {_raise_exc}")

        # ── 9) focus_datetime 跳转 ──
        try:
            chart = getattr(minute_fs, '_chart', None)
            print(f"[联动V25] 准备 focus_datetime, chart={type(chart).__name__ if chart else None}, "
                  f"hasattr(chart, 'focus_datetime')={hasattr(chart, 'focus_datetime') if chart else False}")
            if chart is not None and hasattr(chart, 'focus_datetime'):
                print(f"[联动V25] 调用 chart.focus_datetime(clicked_dt={clicked_dt}, completed_daily=False) 前")
                chart.focus_datetime(clicked_dt, completed_daily=False)
                print(f"[联动V25] ✓✓✓ 跳转到 {type(minute_fs).__name__} ({clicked_dt.date()}) 中心完成 ✓✓✓")
            else:
                print(f"[联动V25] ✗ {type(minute_fs).__name__} 没有 chart.focus_datetime 接口")
                # V25 兜底：尝试直接调 _on_daily_bar_clicked_from_outer
                if hasattr(minute_fs, '_on_daily_bar_clicked_from_outer'):
                    print(f"[联动V25] 兜底: 直接调用 minute_fs._on_daily_bar_clicked_from_outer")
                    minute_fs._on_daily_bar_clicked_from_outer(clicked_dt, [])
        except Exception as _focus_exc:
            print(f"[联动V25] focus_datetime 异常: {_focus_exc}")
            import traceback
            traceback.print_exc()

'''

# 替换
cmw_content_new = cmw_content[:start_idx] + new_method + cmw_content[end_idx:]

# 写回
with open(CMW, 'w', encoding='utf-8') as f:
    f.write(cmw_content_new)
print(f"[2] _focus_minute_fullscreen_window V25 版已写入（防御性 + 大量 print）")
print(f"    旧: {end_idx - start_idx} 字符 -> 新: {len(new_method)} 字符")


# ============================================================================
# 改动 3：kline_view.py V24-FS fallback 的 hasattr 防御
# ============================================================================
KV = os.path.join(BASE, 'vnpy', 'strategy_condition', 'ui', 'kline_view.py')
with open(KV, 'r', encoding='utf-8') as f:
    kv_content = f.read()

# 把 V24-FS 里所有 Interval.MONTHLY 改成 getattr
old_v24fs = "cur_iv_ok = cur_iv is not None and cur_iv not in (_Iv.DAILY, _Iv.WEEKLY, _Iv.MONTHLY)"
new_v24fs = """cur_iv_ok = cur_iv is not None and cur_iv not in (
                getattr(_Iv, 'DAILY', None),
                getattr(_Iv, 'WEEKLY', None),
                getattr(_Iv, 'MONTHLY', None),
            )
            cur_iv_ok = bool(cur_iv_ok)"""

if old_v24fs in kv_content:
    kv_content = kv_content.replace(old_v24fs, new_v24fs)
    with open(KV, 'w', encoding='utf-8') as f:
        f.write(kv_content)
    print("[3] kline_view.py V24-FS fallback 加 hasattr 防御 OK")
else:
    print("[3] WARN: V24-FS fallback 段未找到，可能已被改过")


# ============================================================================
# 改动 4：在 _focus_minute_fullscreen_window 的"调用者"位置加 V25 print
# ============================================================================
# 找 _dispatch_to_fullscreen_windows 或 _handle_daily_bar_clicked 之类的入口
# 看看是谁调了 _focus_minute_fullscreen_window
# 简单点：在调用前后都打 print
old_call = "self._focus_minute_fullscreen_window(clicked_dt)"
new_call = '''print(f"[联动V25][调用者] 即将调用 _focus_minute_fullscreen_window(clicked_dt={clicked_dt})")
                _focus_result = self._focus_minute_fullscreen_window(clicked_dt)
                print(f"[联动V25][调用者] _focus_minute_fullscreen_window 已返回={_focus_result}")'''

# 注意 _focus_minute_fullscreen_window 没有 return，但为了 print 仍用变量接
if old_call in cmw_content_new:
    # 重新读 cmw
    with open(CMW, 'r', encoding='utf-8') as f:
        cmw_content_now = f.read()
    if old_call in cmw_content_now:
        cmw_content_now = cmw_content_now.replace(old_call, new_call)
        with open(CMW, 'w', encoding='utf-8') as f:
            f.write(cmw_content_now)
        print("[4] _focus_minute_fullscreen_window 调用处已加 print")
    else:
        print("[4] WARN: 改完再读，调用点不见了（可能 V25 新方法里就有）")
else:
    print("[4] WARN: 找不到调用点 self._focus_minute_fullscreen_window(clicked_dt)")


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
print("V25 修复应用完成 ✓")
print("=" * 80)
print("""
V25 vs V24 关键改进：
┌──────────────────────────────────────────────────────────┐
│ V24 失败：                                                │
│   路径A: if iv in (DAILY, WEEKLY, MONTHLY): ← MONTHLY 不存在 │
│   AttributeError → 整个 try 块崩 → 路径B/C 不执行            │
│                                                          │
│ V25 修复：                                                │
│   blacklist = tuple(iv for iv in (DAILY, WEEKLY, MONTHLY) │
│                   if iv is not None)  ← hasattr 防御      │
│   + 路径A/B/C 各自独立 try，单个失败不影响其他               │
│   + 每个候选窗口/分支/异常 都打 print                       │
└──────────────────────────────────────────────────────────┘

V25 关键诊断点（重启后会看到这些 print）：
  [联动V25] ============================================================
  [联动V25] 候选全屏窗口 N 个：
  [联动V25]   [0] type=_KlineFullscreenWindow id=0x... _interval=Interval.DAILY chart_type=... bars=1584 bars_gap=86400s
  [联动V25]   [1] type=_KlineFullscreenWindow id=0x... _interval=Interval.DAILY chart_type=... bars=20000 bars_gap=300s
  [联动V25] ============================================================
  [联动V25] 路径A: 候选[0] ..._interval=DAILY 命中黑名单 → 视为日线，跳过
  [联动V25] 路径A: 候选[1] ..._interval=DAILY 命中黑名单 → 视为日线，跳过
  [联动V25] 路径A: 所有候选的 _interval 都在黑名单 → 路径A 未命中
  [联动V25] 路径B: 候选[0] ... bars=1584 gap=86400s ≥ 半天 → 视为日线
  [联动V25] 路径B命中: 候选[1] ... bars=20000 gap=300s → 强制判定为分钟线 ✓
  [联动V25] ✓ 最终选中: _KlineFullscreenWindow (走路径B)
  [联动V25] 准备 focus_datetime, chart=..., hasattr(chart, 'focus_datetime')=True/False
  [联动V25] ✓✓✓ 跳转到 _KlineFullscreenWindow (...) 中心完成 ✓✓✓

验证步骤：
1. 关闭 VNPY，重新启动（清缓存生效）
2. 打开 Monitor → 加载双周期 → 开日线全屏 → 开分钟线全屏
3. 在日线全屏点 K 线
4. 看终端的 [联动V25] 完整 print 链
5. 看分钟线全屏窗口是否跳转
""")