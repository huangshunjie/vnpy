"""
验证日线分钟K线联动功能
测试非全屏模式和全屏模式下的信号联动
"""
import sys
import io
from pathlib import Path
from datetime import datetime, date

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from vnpy.strategy_condition.monitor.condition_snapshot import ConditionSnapshot
from vnpy.strategy_condition.constant import SignalType


def create_test_bars(symbol: str, interval: Interval, num_bars: int, base_date):
    """创建测试K线数据"""
    bars = []
    for i in range(num_bars):
        if interval == Interval.DAILY:
            dt = datetime(base_date.year, base_date.month, base_date.day + i, 15, 0)
        else:  # Interval.MINUTE
            dt = datetime(base_date.year, base_date.month, base_date.day, 9, 30 + i)
        
        bar = BarData(
            symbol=symbol,
            exchange=Exchange.SSE,
            datetime=dt,
            interval=interval,
            open_price=10.0 + i * 0.1,
            high_price=10.5 + i * 0.1,
            low_price=9.5 + i * 0.1,
            close_price=10.0 + i * 0.1,
            volume=1000000,
            turnover=10000000,
            open_interest=0,
            gateway_name="test"
        )
        bars.append(bar)
    return bars


def create_test_snapshots(symbol: str, target_date: date, buy_minute_idx=30, sell_minute_idx=120):
    """创建测试快照数据，模拟在特定分钟有买卖信号"""
    snapshots = []
    
    # 创建一整天的分钟快照（9:30-15:00，共240分钟）
    for i in range(240):
        dt = datetime(target_date.year, target_date.month, target_date.day, 9, 30 + i)
        
        # 确定信号类型
        signal_type = SignalType.NONE
        if i == buy_minute_idx:
            signal_type = SignalType.BUY
        elif i == sell_minute_idx:
            signal_type = SignalType.SELL
        
        snapshot = ConditionSnapshot(
            datetime=dt,
            symbol=symbol,
            exchange=Exchange.SSE,
            interval=Interval.MINUTE,
            condition_name="测试条件",
            signal_type=signal_type,
            condition_result=True if signal_type != SignalType.NONE else False,
            buy_price=10.0 if signal_type == SignalType.BUY else None,
            sell_price=11.0 if signal_type == SignalType.SELL else None
        )
        snapshots.append(snapshot)
    
    return snapshots


def verify_signal_connection():
    """验证信号连接机制"""
    print("=" * 80)
    print("验证1：检查关键组件和信号定义")
    print("=" * 80)
    
    try:
        from vnpy.strategy_condition.ui.condition_monitor_widget import ConditionMonitorWidget
        from vnpy.strategy_condition.ui.kline_view import KlineViewTab, _KlineFullscreenWindow
        
        # 检查信号定义
        print("\n[OK] ConditionMonitorWidget 导入成功")
        print(f"  - 是否有 daily_bar_clicked 信号: {hasattr(ConditionMonitorWidget, 'daily_bar_clicked')}")
        
        print("\n[OK] KlineViewTab 导入成功")
        print(f"  - 是否有 focus_on_date 方法: {hasattr(KlineViewTab, 'focus_on_date')}")
        
        print("\n[OK] _KlineFullscreenWindow 导入成功")
        print(f"  - 是否有 _on_daily_clicked_from_main 方法: {hasattr(_KlineFullscreenWindow, '_on_daily_clicked_from_main')}")
        print(f"  - 是否有 _focus_chart_on_date 方法: {hasattr(_KlineFullscreenWindow, '_focus_chart_on_date')}")
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_signal_query_logic():
    """验证信号查询逻辑"""
    print("\n" + "=" * 80)
    print("验证2：检查信号查询逻辑(_get_signals_for_date)")
    print("=" * 80)
    
    try:
        from vnpy.strategy_condition.ui.condition_monitor_widget import ConditionMonitorWidget
        from PyQt5 import QtWidgets
        import inspect
        
        # 检查方法是否存在
        if not hasattr(ConditionMonitorWidget, '_get_signals_for_date'):
            print("\n[FAIL] _get_signals_for_date 方法不存在")
            return False
        
        print("\n[OK] _get_signals_for_date 方法存在")
        
        # 检查方法签名
        sig = inspect.signature(ConditionMonitorWidget._get_signals_for_date)
        print(f"  - 方法签名: {sig}")
        
        # 检查相关辅助方法
        print(f"\n  - _update_minute_view_for_date 存在: {hasattr(ConditionMonitorWidget, '_update_minute_view_for_date')}")
        print(f"  - _connect_daily_click_handler 存在: {hasattr(ConditionMonitorWidget, '_connect_daily_click_handler')}")
        print(f"  - _on_daily_bar_clicked 存在: {hasattr(ConditionMonitorWidget, '_on_daily_bar_clicked')}")
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_focus_on_date_logic():
    """验证聚焦逻辑"""
    print("\n" + "=" * 80)
    print("验证3：检查 focus_on_date 实现")
    print("=" * 80)
    
    try:
        from vnpy.strategy_condition.ui.kline_view import KlineViewTab
        import inspect
        
        # 获取方法源码的关键行
        source = inspect.getsource(KlineViewTab.focus_on_date)
        
        print("\n[OK] focus_on_date 方法源码检查:")
        
        # 检查关键实现点
        checks = {
            "设置显示范围": "setXRange" in source,
            "更新信号显示": "_update_signals_display" in source or "update_signals" in source,
            "处理 signals 参数": "signals" in source,
            "日期索引查找": "target_indices" in source or "enumerate" in source
        }
        
        for check_name, result in checks.items():
            status = "[OK]" if result else "[FAIL]"
            print(f"  {status} {check_name}: {result}")
        
        all_passed = all(checks.values())
        return all_passed
        
    except Exception as e:
        print(f"\n[FAIL] 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_fullscreen_linkage():
    """验证全屏窗口联动"""
    print("\n" + "=" * 80)
    print("验证4：检查全屏窗口联动机制")
    print("=" * 80)
    
    try:
        from vnpy.strategy_condition.ui.kline_view import _KlineFullscreenWindow
        import inspect
        
        print("\n[OK] 全屏窗口类存在")
        
        # 检查构造函数中的联动设置
        init_source = inspect.getsource(_KlineFullscreenWindow.__init__)
        
        checks = {
            "监听 daily_bar_clicked": "daily_bar_clicked.connect" in init_source,
            "window_type 参数": "window_type" in init_source,
            "parent_monitor 保存": "_parent_monitor" in init_source or "parent_monitor" in init_source
        }
        
        print("\n  构造函数检查:")
        for check_name, result in checks.items():
            status = "[OK]" if result else "[FAIL]"
            print(f"    {status} {check_name}: {result}")
        
        # 检查关键方法
        methods = {
            "_on_daily_clicked_from_main": "处理主界面日线点击",
            "_focus_chart_on_date": "聚焦图表到指定日期",
            "_update_fullscreen_signals": "更新全屏信号标记"
        }
        
        print("\n  关键方法检查:")
        for method_name, description in methods.items():
            exists = hasattr(_KlineFullscreenWindow, method_name)
            status = "[OK]" if exists else "[FAIL]"
            print(f"    {status} {method_name}: {description} - {'存在' if exists else '不存在'}")
        
        return all(checks.values()) and all(hasattr(_KlineFullscreenWindow, m) for m in methods)
        
    except Exception as e:
        print(f"\n[FAIL] 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_signal_disconnect():
    """验证信号断开逻辑"""
    print("\n" + "=" * 80)
    print("验证5：检查信号断开机制（closeEvent）")
    print("=" * 80)
    
    try:
        from vnpy.strategy_condition.ui.kline_view import _KlineFullscreenWindow
        import inspect
        
        if not hasattr(_KlineFullscreenWindow, 'closeEvent'):
            print("\n[FAIL] closeEvent 方法不存在")
            return False
        
        source = inspect.getsource(_KlineFullscreenWindow.closeEvent)
        
        checks = {
            "断开 daily_bar_clicked": "daily_bar_clicked.disconnect" in source,
            "断开 bar_clicked": "bar_clicked.disconnect" in source,
            "异常处理": "try" in source or "except" in source
        }
        
        print("\n[OK] closeEvent 方法检查:")
        for check_name, result in checks.items():
            status = "[OK]" if result else "[FAIL]"
            print(f"  {status} {check_name}: {result}")
        
        # 警告：检查是否使用了无参数的 disconnect()
        if "disconnect()" in source:
            print("\n  [WARN] 警告：发现无参数的 disconnect() 调用，可能会断开所有连接")
        
        return all(checks.values())
        
    except Exception as e:
        print(f"\n[FAIL] 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主验证流程"""
    print("\n")
    print("=" * 80)
    print("           日线分钟K线联动功能验证")
    print("=" * 80)
    
    results = []
    
    # 运行各项验证
    results.append(("信号连接机制", verify_signal_connection()))
    results.append(("信号查询逻辑", verify_signal_query_logic()))
    results.append(("聚焦逻辑", verify_focus_on_date_logic()))
    results.append(("全屏联动", verify_fullscreen_linkage()))
    results.append(("信号断开", verify_signal_disconnect()))
    
    # 总结
    print("\n" + "=" * 80)
    print("验证总结")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")
    
    print(f"\n总计: {passed}/{total} 项通过")
    
    if passed == total:
        print("\n[OK] 所有验证通过！联动功能骨架完整。")
        print("\n建议：")
        print("  1. 在实际UI环境中测试点击日线K线是否触发分钟视图更新")
        print("  2. 验证买卖信号标记是否正确显示在分钟K线上")
        print("  3. 测试全屏模式下的联动是否正常工作")
    else:
        print("\n[FAIL] 部分验证失败，需要修复相关问题。")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)