#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V8 关键修复：全屏窗口监听 owner_monitor.daily_bar_clicked 信号，
实现【在主 Monitor 日线点击时，全屏窗口的 vline 同步移动】。

V8 目标：
  - 去掉 V5 半透明设计
  - 去掉主 Monitor 中转（_lower_fullscreen_windows）
  - 全屏窗口自己监听 owner_monitor.daily_bar_clicked，独立移动 vline
"""

import re
import sys
from pathlib import Path

FILE = Path("vnpy/strategy_condition/ui/kline_view.py")
src = FILE.read_text(encoding="utf-8")

# ============================================================
# 修改 1: 在 _KlineFullscreenWindow 类中，新增一个槽函数
#         _on_outer_daily_bar_clicked(self, focus_dt, buy_signals, sell_signals)
#         + closeEvent 中断开 daily_bar_clicked 监听
# ============================================================
# 真实锚点（已通过 read_file 确认）：
#     def closeEvent(self, event) -> None:
#         ...
#         try:
#             owner = getattr(self, '_owner_monitor', None)
#             if owner is not None:
#                 lst = getattr(owner, '_fullscreen_windows', None)
#                 if lst is not None and self in lst:
#                     lst.remove(self)
#         except Exception:
#             pass
#         super().closeEvent(event)

old_close_event = '''    def closeEvent(self, event) -> None:
        """V5 新增：窗口关闭时从 owner_monitor._fullscreen_windows 中反注册，
        避免主 Monitor 持有已销毁的窗口引用导致后续 _lower_fullscreen_windows 崩溃。
        """
        try:
            owner = getattr(self, '_owner_monitor', None)
            if owner is not None:
                lst = getattr(owner, '_fullscreen_windows', None)
                if lst is not None and self in lst:
                    lst.remove(self)
        except Exception:
            pass
        super().closeEvent(event)'''

new_methods_and_close = '''    # ----------------------------------------------------------------
    # V8 新增：监听 owner_monitor.daily_bar_clicked 信号
    # 当主 Monitor 的日线面板被点击时，外部 owner 会发射
    #   daily_bar_clicked.emit(focus_dt, buy_signals, sell_signals)
    # 本窗口只关心 focus_dt —— 用它移动 vline。
    # ----------------------------------------------------------------
    def _on_outer_daily_bar_clicked(self, focus_dt, buy_signals, sell_signals) -> None:
        """V8 全屏窗口监听主 Monitor 的日线点击，独立移动 vline（无半透明、无中转）。"""
        try:
            chart = getattr(self, '_chart', None)
            if chart is None:
                return
            if focus_dt is None:
                return
            # 复用 _FullscreenChart 已有的 focus_datetime 接口（如果存在）
            if hasattr(chart, 'focus_datetime'):
                chart.focus_datetime(focus_dt, completed_daily=False)
                print(f"[KlineView][V8] 全屏窗口收到外部 daily_bar_clicked, focus_dt={focus_dt}, vline 已移动")
            else:
                # 兜底：直接定位 vline
                dts = getattr(chart, '_datetimes', None)
                if dts:
                    target = focus_dt
                    best_idx = 0
                    best_diff = None
                    for i, dt in enumerate(dts):
                        if dt is None:
                            continue
                        try:
                            diff = abs((dt - target).total_seconds())
                        except Exception:
                            continue
                        if best_diff is None or diff < best_diff:
                            best_diff = diff
                            best_idx = i
                    vline = getattr(chart, '_vline', None)
                    if vline is not None:
                        vline.setPos(best_idx)
                        print(f"[KlineView][V8] 全屏窗口 vline 兜底移动 idx={best_idx}, focus_dt={focus_dt}")
        except Exception as _exc:
            import traceback
            traceback.print_exc()
            print(f"[KlineView][V8] 全屏窗口 _on_outer_daily_bar_clicked 失败: {_exc}")

    def closeEvent(self, event) -> None:
        """V5 新增：窗口关闭时从 owner_monitor._fullscreen_windows 中反注册，
        避免主 Monitor 持有已销毁的窗口引用导致后续 _lower_fullscreen_windows 崩溃。
        V8 新增：同时断开 owner_monitor.daily_bar_clicked 监听。
        """
        try:
            owner = getattr(self, '_owner_monitor', None)
            if owner is not None:
                # V8：断开 daily_bar_clicked 监听
                try:
                    if hasattr(owner, 'daily_bar_clicked'):
                        try:
                            owner.daily_bar_clicked.disconnect(self._on_outer_daily_bar_clicked)
                        except (TypeError, RuntimeError):
                            pass  # 未连接
                except Exception:
                    pass
                # V5：反注册全屏窗口
                try:
                    lst = getattr(owner, '_fullscreen_windows', None)
                    if lst is not None and self in lst:
                        lst.remove(self)
                except Exception:
                    pass
        except Exception:
            pass
        super().closeEvent(event)'''

if old_close_event in src:
    src = src.replace(old_close_event, new_methods_and_close)
    print("[OK] 修改 1: _KlineFullscreenWindow 新增 _on_outer_daily_bar_clicked 槽函数 + closeEvent 断开")
else:
    print("[FAIL] 修改 1: 未找到 closeEvent 锚点")
    sys.exit(1)

# ============================================================
# 修改 2: 在 _on_fullscreen 函数中（创建 win 之后），
#         添加 owner_monitor.daily_bar_clicked → win._on_outer_daily_bar_clicked 连接
# ============================================================
# 真实锚点（已通过 read_file 确认）最后一段：
#                 try:
#                     if not hasattr(owner_monitor, '_fullscreen_windows'):
#                         owner_monitor._fullscreen_windows = []
#                     if win not in owner_monitor._fullscreen_windows:
#                         owner_monitor._fullscreen_windows.append(win)
#                 except Exception as _reg_exc:
#                     print(f"[KlineView][DEBUG] 全屏窗口注册到 monitor 失败: {_reg_exc}")
#                 print(f"[KlineView][DEBUG] 全屏窗口 owner_monitor 注入成功: {owner_monitor}")

old_fullscreen_inject = '''                try:
                    if not hasattr(owner_monitor, \'_fullscreen_windows\'):
                        owner_monitor._fullscreen_windows = []
                    if win not in owner_monitor._fullscreen_windows:
                        owner_monitor._fullscreen_windows.append(win)
                except Exception as _reg_exc:
                    print(f"[KlineView][DEBUG] 全屏窗口注册到 monitor 失败: {_reg_exc}")
                print(f"[KlineView][DEBUG] 全屏窗口 owner_monitor 注入成功: {owner_monitor}")'''

new_fullscreen_inject = '''                try:
                    if not hasattr(owner_monitor, \'_fullscreen_windows\'):
                        owner_monitor._fullscreen_windows = []
                    if win not in owner_monitor._fullscreen_windows:
                        owner_monitor._fullscreen_windows.append(win)
                except Exception as _reg_exc:
                    print(f"[KlineView][DEBUG] 全屏窗口注册到 monitor 失败: {_reg_exc}")

                # V8 新增：监听 owner_monitor.daily_bar_clicked，
                # 当主 Monitor 的日线面板被点击时，全屏窗口独立移动 vline
                try:
                    if hasattr(owner_monitor, \'daily_bar_clicked\'):
                        owner_monitor.daily_bar_clicked.connect(win._on_outer_daily_bar_clicked)
                        print(f"[KlineView][V8] 全屏窗口已监听 owner_monitor.daily_bar_clicked")
                except Exception as _link_exc:
                    print(f"[KlineView][V8] 全屏窗口监听 daily_bar_clicked 失败: {_link_exc}")

                print(f"[KlineView][DEBUG] 全屏窗口 owner_monitor 注入成功: {owner_monitor}")'''

if old_fullscreen_inject in src:
    src = src.replace(old_fullscreen_inject, new_fullscreen_inject)
    print("[OK] 修改 2: _on_fullscreen 新增 owner_monitor.daily_bar_clicked 连接")
else:
    print("[FAIL] 修改 2: 未找到 _fullscreen_windows 注册锚点")
    sys.exit(1)

FILE.write_text(src, encoding="utf-8")
print("\n[SUCCESS] V8 关键修复已写入", FILE)
print("\n下一步：用户重启 vnpy，验证全屏窗口能跟随主 Monitor 日线点击移动 vline")