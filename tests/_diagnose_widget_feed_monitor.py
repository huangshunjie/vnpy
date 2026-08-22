"""
诊断 widget._feed_monitor 是否正确加载分钟数据

目标：找出为什么 Monitor 面板显示 "5分钟 0 根"
"""
import sys
from datetime import date
from vnpy.strategy_condition.ui.widget import StrategyConditionWidget
from vnpy.trader.constant import Exchange


def test_feed_monitor_minute_load():
    """模拟回测完成后切换到 Monitor Tab 的数据加载流程"""
    print("=" * 60)
    print("测试: widget._feed_monitor 分钟数据加载")
    print("=" * 60)
    
    # 创建 widget（不显示UI）
    widget = StrategyConditionWidget()
    
    # 模拟回测结果数据
    symbol = "600028.SSE"
    buy_dates = [date(2026, 3, 9), date(2026, 4, 7)]
    sell_dates = [date(2026, 5, 8), date(2026, 6, 5)]
    
    # 模拟 daily_snapshots（简化版）
    from vnpy.strategy_condition.monitor.condition_snapshot import ConditionSnapshot
    from datetime import datetime
    
    daily_snapshots = [
        ConditionSnapshot(
            symbol=symbol,
            dt=datetime(2026, 3, 9, 15, 0),
            signal_type='buy',
        ),
        ConditionSnapshot(
            symbol=symbol,
            dt=datetime(2026, 4, 7, 15, 0),
            signal_type='buy',
        ),
        ConditionSnapshot(
            symbol=symbol,
            dt=datetime(2026, 5, 8, 15, 0),
            signal_type='sell',
        ),
        ConditionSnapshot(
            symbol=symbol,
            dt=datetime(2026, 6, 5, 15, 0),
            signal_type='sell',
        ),
    ]
    
    # 模拟获取日线数据
    from vnpy.trader.database import get_database
    db = get_database()
    
    start_dt = datetime(2020, 1, 1)
    end_dt = datetime(2026, 7, 19, 23, 59, 59)
    
    from vnpy.trader.constant import Interval
    daily_bars = db.load_bar_data(
        symbol="600028",
        exchange=Exchange.SSE,
        interval=Interval.DAILY,
        start=start_dt,
        end=end_dt,
    )
    
    print(f"\n日线数据: {len(daily_bars)} 根")
    if daily_bars:
        print(f"  起始: {daily_bars[0].datetime}")
        print(f"  结束: {daily_bars[-1].datetime}")
    
    # 调用 _feed_monitor
    print(f"\n调用 _feed_monitor...")
    print(f"  symbol: {symbol}")
    print(f"  buy_dates: {buy_dates}")
    print(f"  sell_dates: {sell_dates}")
    print(f"  daily_snapshots: {len(daily_snapshots)} 个")
    print(f"  daily_bars: {len(daily_bars)} 根")
    
    try:
        widget._feed_monitor(
            symbol=symbol,
            buy_dates=buy_dates,
            sell_dates=sell_dates,
            daily_snapshots=daily_snapshots,
            daily_bars=daily_bars,
        )
        print(f"\n[OK] _feed_monitor 调用成功")
        
        # 检查 Monitor Tab 的状态
        monitor_tab = widget._monitor_tab
        status_text = monitor_tab._status_lbl.text()
        print(f"\nMonitor 状态栏: {status_text}")
        
        # 检查分钟面板
        minute_panel = monitor_tab._minute_panel
        if hasattr(minute_panel, '_current_bars'):
            minute_bars = minute_panel._current_bars
            print(f"分钟面板 _current_bars: {len(minute_bars)} 根")
        else:
            print(f"分钟面板没有 _current_bars 属性")
            
    except Exception as e:
        print(f"\n[ERROR] _feed_monitor 调用失败:")
        print(f"  {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_feed_monitor_minute_load()