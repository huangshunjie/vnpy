"""
诊断日线-分钟K线联动问题
"""
import sys
from vnpy.trader.ui import QtWidgets, QtCore

def diagnose_linkage():
    """诊断联动功能"""
    print("=" * 60)
    print("日线-分钟K线联动功能诊断")
    print("=" * 60)
    
    # 检查1: 导入相关模块
    print("\n[1] 检查模块导入...")
    try:
        from vnpy.strategy_condition.ui.condition_monitor_widget import (
            ConditionMonitorWidget, _PeriodMonitorPanel
        )
        from vnpy.strategy_condition.ui.kline_view import KlineChartWidget
        print("  ✓ 模块导入成功")
    except Exception as e:
        print(f"  ✗ 模块导入失败: {e}")
        return
    
    # 检查2: 验证信号定义
    print("\n[2] 检查信号定义...")
    try:
        widget = KlineChartWidget()
        has_signal = hasattr(widget, 'bar_clicked')
        print(f"  KlineChartWidget.bar_clicked 存在: {has_signal}")
        if has_signal:
            print(f"  信号类型: {type(widget.bar_clicked)}")
    except Exception as e:
        print(f"  ✗ 信号检查失败: {e}")
    
    # 检查3: 验证ConditionMonitorWidget初始化
    print("\n[3] 检查ConditionMonitorWidget初始化...")
    try:
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication(sys.argv)
        
        monitor = ConditionMonitorWidget()
        print(f"  ✓ ConditionMonitorWidget创建成功")
        
        # 检查daily_panel
        has_daily = hasattr(monitor, '_daily_panel')
        print(f"  _daily_panel 存在: {has_daily}")
        
        if has_daily:
            panel = monitor._daily_panel
            has_kline_tab = hasattr(panel, '_kline_tab')
            print(f"  _daily_panel._kline_tab 存在: {has_kline_tab}")
            
            if has_kline_tab:
                kline_tab = panel._kline_tab
                has_chart = hasattr(kline_tab, '_chart')
                print(f"  _daily_panel._kline_tab._chart 存在: {has_chart}")
                
                if has_chart:
                    chart = kline_tab._chart
                    has_signal = hasattr(chart, 'bar_clicked')
                    print(f"  _daily_panel._kline_tab._chart.bar_clicked 存在: {has_signal}")
                    
                    # 测试信号连接
                    if has_signal:
                        def test_slot(dt):
                            print(f"  [测试] 收到信号: {dt}")
                        
                        try:
                            chart.bar_clicked.connect(test_slot)
                            print("  ✓ 信号连接测试成功")
                            
                            # 模拟发射信号
                            from datetime import datetime
                            test_dt = datetime(2026, 4, 10, 14, 30)
                            chart.bar_clicked.emit(test_dt)
                            print("  ✓ 信号发射测试成功")
                        except Exception as e:
                            print(f"  ✗ 信号连接/发射失败: {e}")
        
        # 检查_on_daily_bar_clicked方法
        has_handler = hasattr(monitor, '_on_daily_bar_clicked')
        print(f"\n  _on_daily_bar_clicked 方法存在: {has_handler}")
        
        # 检查minute_panel的focus_date方法
        has_minute = hasattr(monitor, '_minute_panel')
        if has_minute:
            minute_panel = monitor._minute_panel
            has_focus = hasattr(minute_panel, 'focus_date')
            print(f"  _minute_panel.focus_date 方法存在: {has_focus}")
    
    except Exception as e:
        import traceback
        print(f"  ✗ 初始化检查失败: {e}")
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    diagnose_linkage()