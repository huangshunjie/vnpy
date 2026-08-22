"""
诊断 Monitor Tab 的日线分钟联动功能
"""
import sys
import os

def check_file_content(filepath, search_patterns):
    """检查文件中是否包含指定模式"""
    print(f"\n检查文件: {filepath}")
    if not os.path.exists(filepath):
        print(f"  ❌ 文件不存在")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    results = {}
    for name, pattern in search_patterns.items():
        found = pattern in content
        status = "✅" if found else "❌"
        print(f"  {status} {name}")
        results[name] = found
    
    return all(results.values())

# 检查 condition_monitor_widget.py
print("=" * 60)
print("检查 condition_monitor_widget.py")
print("=" * 60)

patterns1 = {
    "_connect_daily_click_handler 方法": "def _connect_daily_click_handler(self)",
    "_on_daily_bar_clicked 方法": "def _on_daily_bar_clicked(self, clicked_dt)",
    "_get_signals_for_date 方法": "def _get_signals_for_date(self, target_date)",
    "_update_minute_view_for_date 方法": "def _update_minute_view_for_date(self, target_date, signals)",
    "daily_bar_clicked 信号": "daily_bar_clicked = QtCore.Signal(object, dict)",
    "优先读取 signal_type": "signal_type = getattr(snap, 'signal_type', None)",
    "连接日线点击处理器调用": "self._connect_daily_click_handler()",
}

check_file_content(
    "vnpy/strategy_condition/ui/condition_monitor_widget.py",
    patterns1
)

# 检查 kline_view.py  
print("\n" + "=" * 60)
print("检查 kline_view.py")
print("=" * 60)

patterns2 = {
    "KlineViewTab.focus_on_date 方法": "def focus_on_date(self, target_date, signals=None)",
    "_update_signals_display 方法": "def _update_signals_display(self, signals)",
    "全屏窗口 closeEvent": "def closeEvent(self, event) -> None:",
    "日线全屏转发逻辑": "_forward_daily_click",
    "分钟全屏响应逻辑": "_on_daily_clicked_from_main",
}

check_file_content(
    "vnpy/strategy_condition/ui/kline_view.py",
    patterns2
)

print("\n" + "=" * 60)
print("总结")
print("=" * 60)
print("""
如果以上检查有 ❌ 标记，说明相关功能未正确实现。

常见问题：
1. 非全屏模式不联动 → 检查 _connect_daily_click_handler 是否被调用
2. 分钟线不显示 → 检查数据是否正确加载到 minute_panel
3. 分钟全屏打不开 → 检查 _on_fullscreen 方法和全屏窗口构造
""")