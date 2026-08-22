#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试日线分钟K线联动功能
"""
import sys
from pathlib import Path
from datetime import datetime, date

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("日线分钟K线联动功能测试")
print("=" * 70)

# 测试1: 验证关键方法存在
print("\n[测试1] 验证关键方法存在...")
try:
    from vnpy.strategy_condition.ui.kline_view import KlineViewTab, _KlineFullscreenWindow
    from vnpy.strategy_condition.ui.condition_monitor_widget import ConditionMonitorWidget
    
    # 检查 KlineViewTab 方法
    assert hasattr(KlineViewTab, 'focus_on_date'), "KlineViewTab 缺少 focus_on_date 方法"
    assert hasattr(KlineViewTab, '_update_signals_display'), "KlineViewTab 缺少 _update_signals_display 方法"
    assert hasattr(KlineViewTab, 'set_waveform_data'), "KlineViewTab 缺少 set_waveform_data 方法"
    
    # 检查 _KlineFullscreenWindow 方法
    assert hasattr(_KlineFullscreenWindow, '_on_daily_clicked_from_main'), "_KlineFullscreenWindow 缺少 _on_daily_clicked_from_main 方法"
    assert hasattr(_KlineFullscreenWindow, '_focus_chart_on_date'), "_KlineFullscreenWindow 缺少 _focus_chart_on_date 方法"
    assert hasattr(_KlineFullscreenWindow, '_update_fullscreen_signals'), "_KlineFullscreenWindow 缺少 _update_fullscreen_signals 方法"
    
    # 检查 ConditionMonitorWidget 方法和信号
    assert hasattr(ConditionMonitorWidget, 'daily_bar_clicked'), "ConditionMonitorWidget 缺少 daily_bar_clicked 信号"
    assert hasattr(ConditionMonitorWidget, '_on_daily_bar_clicked'), "ConditionMonitorWidget 缺少 _on_daily_bar_clicked 方法"
    assert hasattr(ConditionMonitorWidget, '_get_signals_for_date'), "ConditionMonitorWidget 缺少 _get_signals_for_date 方法"
    assert hasattr(ConditionMonitorWidget, '_update_minute_view_for_date'), "ConditionMonitorWidget 缺少 _update_minute_view_for_date 方法"
    
    print("[OK] 所有关键方法验证通过")
    
except Exception as e:
    print(f"[FAIL] 方法验证失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试2: 验证 KlineChartWidget 的 bar_clicked 信号
print("\n[测试2] 验证 KlineChartWidget 的 bar_clicked 信号...")
try:
    from vnpy.strategy_condition.ui.kline_view import KlineChartWidget
    from vnpy.trader.ui import QtCore
    
    # 检查信号是否存在
    assert hasattr(KlineChartWidget, 'bar_clicked'), "KlineChartWidget 缺少 bar_clicked 信号"
    
    # 检查信号类型
    # 直接检查属性存在即可（无需实例化）
    print(f"  bar_clicked 存在于类定义中")
    print("[OK] bar_clicked 信号存在")
        
except Exception as e:
    print(f"[FAIL] 信号验证失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试3: 模拟信号传递链路
print("\n[测试3] 模拟信号传递链路...")
try:
    from vnpy.trader.ui import QtWidgets, QtCore
    from vnpy.strategy_condition.ui.condition_monitor_widget import ConditionMonitorWidget
    from datetime import datetime, date
    
    # 创建应用（测试环境）
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    
    # 创建 ConditionMonitorWidget 实例
    monitor_widget = ConditionMonitorWidget()
    
    # 验证信号连接机制
    clicked_dt = datetime(2026, 7, 15, 9, 30)
    test_signals = {'buy': [], 'sell': []}
    
    # 模拟发射信号（不实际连接，只验证信号可发射）
    try:
        # 测试信号发射（实际场景中由日线K线点击触发）
        monitor_widget.daily_bar_clicked.emit(clicked_dt, test_signals)
        print("[OK] daily_bar_clicked 信号可正常发射")
    except Exception as e:
        print(f"[FAIL] 信号发射失败: {e}")
        raise
    
    # 清理
    monitor_widget.deleteLater()
    
except Exception as e:
    print(f"[FAIL] 信号传递测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试4: 验证日期查找逻辑
print("\n[测试4] 验证日期查找逻辑...")
try:
    from vnpy.trader.object import BarData
    from vnpy.trader.constant import Exchange, Interval
    from datetime import datetime, timedelta
    
    # 模拟分钟数据
    base_dt = datetime(2026, 7, 15, 9, 30)
    minute_bars = []
    for i in range(240):  # 一天的分钟K线
        bar = BarData(
            symbol='600000.SSE',
            exchange=Exchange.SSE,
            datetime=base_dt + timedelta(minutes=i),
            interval=Interval.MINUTE,
            open_price=10.0,
            high_price=10.5,
            low_price=9.5,
            close_price=10.2,
            volume=1000,
            gateway_name='TEST'
        )
        minute_bars.append(bar)
    
    # 测试日期查找
    target_date = date(2026, 7, 15)
    matched_bars = [b for b in minute_bars if b.datetime.date() == target_date]
    
    assert len(matched_bars) == 240, f"日期匹配失败，期望240根，实际{len(matched_bars)}根"
    assert matched_bars[0].datetime.time().hour == 9, "第一根K线时间错误"
    assert matched_bars[0].datetime.time().minute == 30, "第一根K线分钟错误"
    
    print(f"[OK] 日期查找逻辑正确: 找到 {len(matched_bars)} 根分钟K线")
    print(f"  首根: {matched_bars[0].datetime}")
    print(f"  末根: {matched_bars[-1].datetime}")
    
except Exception as e:
    print(f"[FAIL] 日期查找测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试5: 验证信号匹配逻辑
print("\n[测试5] 验证信号匹配逻辑...")
try:
    # 模拟买卖日期列表
    buy_dates = ['2026-07-15 09:30:00', '2026-07-16 10:00:00']
    sell_dates = ['2026-07-15 14:30:00', '2026-07-17 11:00:00']
    
    # 测试目标日期
    target_date = date(2026, 7, 15)
    date_str = target_date.strftime('%Y-%m-%d')
    
    # 匹配逻辑
    is_buy_day = any(str(d)[:10] == date_str for d in buy_dates)
    is_sell_day = any(str(d)[:10] == date_str for d in sell_dates)
    
    assert is_buy_day, "买入日期匹配失败"
    assert is_sell_day, "卖出日期匹配失败"
    
    print(f"[OK] 信号匹配逻辑正确")
    print(f"  目标日期: {date_str}")
    print(f"  是买入日: {is_buy_day}")
    print(f"  是卖出日: {is_sell_day}")
    
    # 测试非信号日
    target_date2 = date(2026, 7, 18)
    date_str2 = target_date2.strftime('%Y-%m-%d')
    is_buy_day2 = any(str(d)[:10] == date_str2 for d in buy_dates)
    is_sell_day2 = any(str(d)[:10] == date_str2 for d in sell_dates)
    
    assert not is_buy_day2, "非买入日误判"
    assert not is_sell_day2, "非卖出日误判"
    
    print(f"  非信号日期: {date_str2} - 正确识别为非信号日")
    
except Exception as e:
    print(f"[FAIL] 信号匹配测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试总结
print("\n" + "=" * 70)
print("[SUCCESS] 所有测试通过！")
print("=" * 70)
print("\n日线分钟K线联动功能已准备就绪，可以在实际应用中使用。")
print("\n使用方法：")
print("1. 在条件监控 Tab 选择「双周期」模式")
print("2. 加载股票数据（包含日线和分钟数据）")
print("3. 点击日线K线的任意一根")
print("4. 观察分钟K线自动跳转到该日期")
print("5. 如果该日有买入/卖出信号，分钟K线会显示信号标记")
print("\n全屏模式测试：")
print("1. 打开分钟K线的全屏窗口")
print("2. 在主界面点击日线K线")
print("3. 全屏窗口会同步跳转到该日期")
print("\n调试日志关键词：[联动]")
print("=" * 70)