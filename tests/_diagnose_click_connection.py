"""诊断日线K线点击事件连接"""
import sys
sys.path.insert(0, r'c:\Users\11229\Documents\GitHub\vnpy')

from vnpy.strategy_condition.ui.condition_monitor_widget import ConditionMonitorWidget

# 创建实例
widget = ConditionMonitorWidget()

# 检查日线面板
print("=== 检查日线面板 ===")
print(f"有 _daily_panel 属性: {hasattr(widget, '_daily_panel')}")
if hasattr(widget, '_daily_panel'):
    daily_panel = widget._daily_panel
    print(f"_daily_panel 类型: {type(daily_panel)}")
    print(f"_daily_panel 有 _kline_tab: {hasattr(daily_panel, '_kline_tab')}")
    
    if hasattr(daily_panel, '_kline_tab'):
        kline_tab = daily_panel._kline_tab
        print(f"_kline_tab 类型: {type(kline_tab)}")
        print(f"_kline_tab 有 _chart: {hasattr(kline_tab, '_chart')}")
        
        if hasattr(kline_tab, '_chart'):
            chart = kline_tab._chart
            print(f"_chart 类型: {type(chart)}")
            print(f"_chart 有 bar_clicked 信号: {hasattr(chart, 'bar_clicked')}")
            
            if hasattr(chart, 'bar_clicked'):
                signal = chart.bar_clicked
                print(f"bar_clicked 类型: {type(signal)}")
                print(f"bar_clicked 连接数: {signal.receivers(signal)}")

# 检查Monitor widget的处理方法
print("\n=== 检查Monitor处理方法 ===")
print(f"有 _on_daily_bar_clicked: {hasattr(widget, '_on_daily_bar_clicked')}")
print(f"有 _connect_daily_click_handler: {hasattr(widget, '_connect_daily_click_handler')}")

# 尝试手动连接
print("\n=== 尝试手动连接 ===")
try:
    widget._connect_daily_click_handler()
    print("✓ _connect_daily_click_handler() 调用成功")
    
    # 再次检查连接
    if hasattr(widget._daily_panel, '_kline_tab'):
        chart = widget._daily_panel._kline_tab._chart
        if hasattr(chart, 'bar_clicked'):
            print(f"连接后 bar_clicked 连接数: {chart.bar_clicked.receivers(chart.bar_clicked)}")
except Exception as e:
    print(f"✗ 连接失败: {e}")
    import traceback
    traceback.print_exc()

print("\n诊断完成")