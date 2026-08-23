"""
_smoke_daily_click_fix_v2.py
完整验证 condition_monitor_widget.py 日线→分钟联动修复。

修复要点（2026-08-23）：
  1. ConditionMonitorWidget 之前引用了不存在的 self._kline_tab，
     现在改用 self._daily_panel._kline_tab._chart。
  2. _update_minute_view_for_date 之前调用 KlineViewTab 上并不存在的
     focus_on_date(date, signals) 方法，hasattr 失败后只打了一行日志。
     现在改用真正存在的 focus_datetime(dt, completed_daily) 方法，
     传入当天 12:00 + completed_daily=True 把 vline 定位到目标日期
     最后已完成的 minute bar。
  3. signals 仍被缓存到 self._pending_signals 供后续诊断/高亮。
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "vnpy" / "strategy_condition" / "ui" / "condition_monitor_widget.py"

src = TARGET.read_text(encoding="utf-8")
tree = ast.parse(src)


def get_class(name: str) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"class {name} not found")


def get_method(klass: ast.ClassDef, name: str) -> ast.FunctionDef:
    for node in klass.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"method {name} not found in {klass.name}")


def get_text(node: ast.AST) -> str:
    return ast.get_source_segment(src, node) or ""


def collect_calls(method: ast.FunctionDef) -> list:
    """收集方法体内所有函数调用（Call 节点），返回 ast.unparse(func) 列表。"""
    calls = []
    for sub in ast.walk(method):
        if isinstance(sub, ast.Call):
            try:
                calls.append(ast.unparse(sub.func))
            except Exception:
                pass
    return calls


def has_attr_access(node: ast.AST, attr_chain: str) -> bool:
    """
    检查 node 中是否存在形如 a.b.c 的属性访问。
    attr_chain 用点分字符串，如 "self._kline_tab._chart.bar_clicked"。
    """
    parts = attr_chain.split(".")
    target = parts[-1]

    for sub in ast.walk(node):
        if not isinstance(sub, ast.Attribute):
            continue
        if sub.attr != target:
            continue
        # 反向追 Object 链，验证完整路径
        cur = sub.value
        ok = True
        for p in reversed(parts[:-1]):
            if not isinstance(cur, ast.Attribute) or cur.attr != p:
                ok = False
                break
            cur = cur.value
        # 起点：要求整个链起始是 self（除非只有一个 part）
        if len(parts) == 1:
            return True
        if ok and isinstance(cur, ast.Name) and cur.id == parts[0]:
            return True
    return False


# ════════════════ 断言 ════════════════

monitor_cls = get_class("ConditionMonitorWidget")
panel_cls = get_class("_PeriodMonitorPanel")

# ── 1. 验证连接器引用的属性链 ──
connector = get_method(monitor_cls, "_connect_daily_click_handler")
connector_src = get_text(connector)
assert "self._daily_panel._kline_tab._chart" in connector_src, (
    "FAILED: _connect_daily_click_handler 必须通过 "
    "self._daily_panel._kline_tab._chart 取 KlineChartWidget"
)
# 还要确保不使用错误的 self._kline_tab（裸属性，绕过 _daily_panel）
assert not re.search(
    r"self\._kline_tab(?!.*_daily_panel)",
    connector_src,
), "FAILED: 不应再直接使用 self._kline_tab（应在 _daily_panel 下）"
print("[OK] 1) _connect_daily_click_handler 已使用 self._daily_panel._kline_tab._chart")

# ── 2. 验证 _update_minute_view_for_date 不再调用不存在的 focus_on_date ──
updater = get_method(monitor_cls, "_update_minute_view_for_date")
updater_calls = collect_calls(updater)
focus_on_date_calls = [
    c for c in updater_calls
    if c.endswith(".focus_on_date")
]
assert not focus_on_date_calls, (
    f"FAILED: _update_minute_view_for_date 不应再调用 focus_on_date，实际：{focus_on_date_calls}"
)
print("[OK] 2) _update_minute_view_for_date 不再调用不存在的 focus_on_date")

# ── 3. 验证 _update_minute_view_for_date 现在调用真正的 focus_datetime ──
assert "focus_datetime" in get_text(updater), (
    "FAILED: _update_minute_view_for_date 必须调用 focus_datetime"
)
print("[OK] 3) _update_minute_view_for_date 已切换到 focus_datetime")

# ── 4. 验证 completed_daily=True 真的传下去了 ──
assert "completed_daily=True" in get_text(updater), (
    "FAILED: 应当用 completed_daily=True 让 vline 落在目标日期最后已完成的 bar"
)
print("[OK] 4) focus_datetime 调用传递了 completed_daily=True")

# ── 5. 验证 signals 被缓存到 _pending_signals ──
assert "_pending_signals" in get_text(updater), (
    "FAILED: signals 应当被缓存到 self._pending_signals"
)
print("[OK] 5) signals 已缓存到 self._pending_signals")

# ── 6. 验证 _PeriodMonitorPanel 仍然有 focus_datetime 方法（vline 落点的真正实现）──
panel_focus = get_method(panel_cls, "focus_datetime")
panel_focus_src = get_text(panel_focus)
assert "setPos" in panel_focus_src, (
    "FAILED: _PeriodMonitorPanel.focus_datetime 必须通过 chart._vline.setPos 移动 vline"
)
assert "set_vline_pos" in panel_focus_src, (
    "FAILED: _PeriodMonitorPanel.focus_datetime 还应同步波形区 vline"
)
print("[OK] 6) _PeriodMonitorPanel.focus_datetime 仍然正确：移动 vline + 波形竖线")

# ── 7. 验证 _on_daily_bar_clicked 真的把 click 转发给 _update_minute_view_for_date ──
on_click = get_method(monitor_cls, "_on_daily_bar_clicked")
on_click_calls = collect_calls(on_click)
assert "self._update_minute_view_for_date" in on_click_calls, (
    "FAILED: _on_daily_bar_clicked 必须调用 self._update_minute_view_for_date"
)
print("[OK] 7) _on_daily_bar_clicked → _update_minute_view_for_date 链路完整")

# ── 8. 验证 daily_bar_clicked 信号依然发射（供全屏窗口监听）──
on_click_src = get_text(on_click)
assert "self.daily_bar_clicked.emit" in on_click_src, (
    "FAILED: _on_daily_bar_clicked 必须发射 daily_bar_clicked 信号"
)
print("[OK] 8) daily_bar_clicked 信号依然发射给全屏窗口")

# ── 9. 验证 _get_signals_for_date 仍然能产出 buy/sell 列表 ──
get_sigs = get_method(monitor_cls, "_get_signals_for_date")
gs_src = get_text(get_sigs)
assert "'buy'" in gs_src and "'sell'" in gs_src, (
    "FAILED: _get_signals_for_date 必须产出 buy/sell 列表"
)
print("[OK] 9) _get_signals_for_date 正确产出 buy/sell 列表")

# ── 10. 跨文件验证 KlineChartWidget 类存在并包含 bar_clicked 信号 ──
kline_view_path = ROOT / "vnpy" / "strategy_condition" / "ui" / "kline_view.py"
kv_src = kline_view_path.read_text(encoding="utf-8")
kv_tree = ast.parse(kv_src)

kline_chart_widget_cls = None
for node in kv_tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "KlineChartWidget":
        kline_chart_widget_cls = node
        break
assert kline_chart_widget_cls is not None, "KlineChartWidget class not found"

# 在 class body 中查找 bar_clicked = Signal(...) 形式
def _has_signal(cls_node: ast.ClassDef, signal_name: str) -> bool:
    for n in cls_node.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == signal_name:
                    return True
    return False

assert _has_signal(kline_chart_widget_cls, "bar_clicked"), (
    "FAILED: KlineChartWidget 没有 bar_clicked 信号定义（_on_mouse_clicked 中不可 emit）"
)
print("[OK] 10) KlineChartWidget.bar_clicked 是真实信号（kline_view.py 静态确认）")

# ── 11. 验证 _on_mouse_clicked 真的在 emit bar_clicked ──
on_mouse_clicked = get_method(kline_chart_widget_cls, "_on_mouse_clicked")
omc_calls = collect_calls(on_mouse_clicked)
assert any(c.endswith("bar_clicked.emit") for c in omc_calls), (
    f"FAILED: KlineChartWidget._on_mouse_clicked 必须 emit bar_clicked，实际：{omc_calls}"
)
print("[OK] 11) KlineChartWidget._on_mouse_clicked → bar_clicked.emit 已接通")

# ── 12. 验证 condition_monitor_widget.py 内的 _PeriodMonitorPanel.focus_datetime
#       才是 vline 定位的真正入口（不是 KlineViewTab）──
panel_focus_dt = get_method(panel_cls, "focus_datetime")
panel_focus_src2 = get_text(panel_focus_dt)
assert "set_vline_pos" in panel_focus_src2 or "vline.setPos" in panel_focus_src2, (
    "FAILED: _PeriodMonitorPanel.focus_datetime 必须移动 vline"
)
assert "_kline_tab" in panel_focus_src2, (
    "FAILED: _PeriodMonitorPanel.focus_datetime 必须通过 _kline_tab 触达 KlineChartWidget"
)
print("[OK] 12) _PeriodMonitorPanel.focus_datetime 是 vline 定位的真实入口")

print()
print("=" * 60)
print("全部 12 项检查通过 [OK]")
print("日线K线点击 → 分钟面板 vline 联动链路已完整修复")
print("=" * 60)