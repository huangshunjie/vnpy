"""
诊断多周期回测卡死问题
"""
import sys
import time
from datetime import datetime
from vnpy.trader.constant import Interval, Exchange
from vnpy.strategy_condition.core.strategy import Strategy, StrategyParams
from vnpy.strategy_condition.core.condition_tree import ConditionNode, LogicOp
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.constant import CondIndicator
from vnpy.strategy_condition.engine.scan_engine import ScanEngine
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer
from vnpy.trader.database import get_database

def main():
    """测试多周期回测性能"""
    
    # 准备数据
    db = get_database()
    symbol = "510300.SSE"  # 测试一支股票
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始加载数据...")
    
    # 加载5分钟数据
    start_time = time.time()
    minute_bars = db.load_bar_data(
        symbol=symbol,
        exchange=Exchange.SSE,
        interval=Interval.MINUTE_5,
        start=datetime(2020, 1, 1),
        end=datetime(2025, 12, 31)
    )
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 5分钟数据: {len(minute_bars)} 根 (耗时 {time.time()-start_time:.2f}s)")
    
    # 加载日线数据
    start_time = time.time()
    daily_bars = db.load_bar_data(
        symbol=symbol,
        exchange=Exchange.SSE,
        interval=Interval.DAILY,
        start=datetime(2020, 1, 1),
        end=datetime(2025, 12, 31)
    )
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 日线数据: {len(daily_bars)} 根 (耗时 {time.time()-start_time:.2f}s)")
    
    if not minute_bars or not daily_bars:
        print("❌ 数据不足，无法测试")
        return
    
    # 计算理论遍历次数
    print(f"\n理论上需要遍历 {len(minute_bars)} 根5分钟K线")
    print(f"每根K线需要：")
    print(f"  1. 构造虚拟日线（O(1)）")
    print(f"  2. 评估日线条件（均线计算 O(n)）")
    print(f"  3. 评估5分钟条件（O(1)）")
    print(f"总计算复杂度约为 O({len(minute_bars)} * {len(daily_bars)}) = {len(minute_bars) * len(daily_bars):,}")
    
    # 构造简单策略
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 构造策略...")
    
    # 买入条件：均线多头排列（日线）
    cond1 = Condition(
        indicator=CondIndicator.MA_ALIGNMENT,
        params={"periods": [5, 10, 20, 60], "_data_interval": "d"}
    )
    
    # 买入条件：回踩MA20（日线）
    cond2 = Condition(
        indicator=CondIndicator.PULLBACK_MA20,
        params={"max_gap_pct": 0.0, "_data_interval": "d"}
    )
    
    # 买入条件：缩量阴线（5分钟）
    cond3 = Condition(
        indicator=CondIndicator.SHRINKING_VOLUME_BEARISH,
        params={"vol_ratio": 0.8, "_data_interval": "5m"}
    )
    
    buy_tree = ConditionNode(
        logic=LogicOp.AND,
        conditions=[cond1, cond2],
        children=[ConditionNode(logic=LogicOp.LEAF, conditions=[cond3])]
    )
    
    sell_tree = ConditionNode(logic=LogicOp.OR, conditions=[
        Condition(indicator=CondIndicator.STOP_LOSS, params={"pct": -0.05})
    ])
    
    strategy = Strategy(
        name="测试策略",
        buy_tree=buy_tree,
        sell_tree=sell_tree,
        params=StrategyParams(
            min_bars=60,
            max_hold_days=30,
            stop_loss_pct=-0.05,
            take_profit_pct=0.15,
            trailing_stop_pct=-0.03
        )
    )
    
    # 准备引擎
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 准备引擎...")
    ce = ConditionEngine()
    se = ScanEngine(ce, log_fn=print)
    
    # 设置MTF Buffer
    mtf_buffer = MultiTimeframeCandleBuffer()
    mtf_buffer.inject(symbol, daily_bars, Interval.DAILY)
    mtf_buffer.inject(symbol, minute_bars, Interval.MINUTE_5)
    se.set_mtf_buffer(mtf_buffer)
    
    # 模拟回测（只测试前100根5分钟K线）
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开始测试回测（前100根）...")
    
    test_bars = minute_bars[:min(100, len(minute_bars))]
    all_bars_dict = {symbol: test_bars}
    
    start_time = time.time()
    try:
        batch = se.backtest(
            symbols=[symbol],
            strategy=strategy,
            all_bars_dict=all_bars_dict,
            warmup=60,
            is_intraday=True,
            execution_interval=Interval.MINUTE_5
        )
        elapsed = time.time() - start_time
        
        print(f"\n✅ 回测完成！")
        print(f"   耗时: {elapsed:.2f}s")
        print(f"   信号数: {batch.count}")
        print(f"   平均每根K线: {elapsed/len(test_bars)*1000:.1f}ms")
        
        if elapsed / len(test_bars) > 0.1:  # 每根K线超过100ms
            print(f"\n⚠️ 性能警告：每根K线处理时间过长")
            print(f"   全量回测 {len(minute_bars)} 根预计需要: {elapsed/len(test_bars)*len(minute_bars)/60:.1f} 分钟")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()