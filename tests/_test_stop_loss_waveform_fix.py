"""
测试止损波形图修复：
- 买入前：无止损信号
- 持仓期间且未达到止损：无止损信号
- 持仓期间且达到止损：显示止损信号
- 卖出后：止损信号消失
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from vnpy.trader.object import BarData, Interval, Exchange
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.core.strategy import Strategy
from vnpy.strategy_condition.constant import ConditionIndicator
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
from vnpy.strategy_condition.monitor.condition_monitor_engine import ConditionMonitorEngine


def create_bars(symbol: str, start_date: datetime, prices: list) -> list:
    """创建K线数据"""
    bars = []
    for i, price in enumerate(prices):
        dt = start_date + timedelta(days=i)
        bar = BarData(
            symbol=symbol,
            exchange=Exchange.SSE,
            datetime=dt,
            interval=Interval.DAILY,
            open_price=price,
            high_price=price * 1.02,
            low_price=price * 0.98,
            close_price=price,
            volume=1000000,
            turnover=price * 1000000,
            open_interest=0,
            gateway_name="test"
        )
        bars.append(bar)
    return bars


def test_stop_loss_waveform():
    """测试止损波形图显示逻辑"""
    print("=" * 80)
    print("测试止损波形图修复")
    print("=" * 80)
    
    # 创建条件引擎和监控引擎
    cond_engine = ConditionEngine()
    monitor_engine = ConditionMonitorEngine(cond_engine)
    
    # 创建策略条件
    buy_cond = Condition(
        indicator=ConditionIndicator.MA_SLOPE,
        params={"ma_period": 5, "min_slope": 0.5}
    )
    
    sell_cond = Condition(
        indicator=ConditionIndicator.STOP_LOSS,
        params={"pct": 8.0}  # 止损-8%
    )
    
    # 创建策略
    strategy = Strategy(
        name="测试策略",
        buy_conditions=[buy_cond],
        sell_conditions=[sell_cond]
    )
    
    # 模拟价格走势：买入价10元，先涨到11元，然后跌到9元（触发止损）
    symbol = "000001.SZ"
    start_date = datetime(2024, 1, 1)
    prices = [
        # 买入前5天
        9.5, 9.6, 9.7, 9.8, 9.9,
        # 买入日（第6天，价格10.0）
        10.0,
        # 持仓期间，先涨
        10.1, 10.2, 10.5, 11.0,
        # 开始回落
        10.8, 10.5, 10.2, 10.0,
        # 继续下跌，触发止损（第15天，价格9.2，相对买入价10.0跌8%）
        9.8, 9.5, 9.2,
        # 卖出后继续跌
        9.0, 8.8
    ]
    
    bars = create_bars(symbol, start_date, prices)
    
    # 指定买入和卖出日期（字符串格式）
    buy_dates = [bars[5].datetime.strftime("%Y-%m-%d")]  # 第6天买入
    sell_dates = [bars[16].datetime.strftime("%Y-%m-%d")]  # 第17天卖出
    
    # 生成监控快照
    print("\n生成监控快照...")
    snapshots = monitor_engine.generate_snapshots(
        symbol=symbol,
        bars=bars,
        strategy=strategy,
        warmup=1,
        buy_dates=buy_dates,
        sell_dates=sell_dates
    )
    
    print(f"生成了 {len(snapshots)} 个快照\n")
    
    # 关键时间点检查
    test_points = [
        (4, "买入前1天", False),  # 应该无止损信号
        (5, "买入当天", False),   # 买入当天无止损信号
        (8, "持仓中，价格10.5（涨5%）", False),  # 未达到止损
        (14, "持仓中，价格9.8（跌2%）", False),  # 未达到止损
        (16, "持仓中，价格9.2（跌8%）", True),   # 应该显示止损信号
        (17, "卖出当天", False),  # 卖出后应该无信号
        (18, "卖出后1天", False), # 卖出后应该无信号
    ]
    
    print("检查关键时间点的止损信号：")
    print("-" * 80)
    
    all_passed = True
    for idx, desc, expected_signal in test_points:
        if idx >= len(snapshots):
            continue
            
        snap = snapshots[idx]
        has_stop_loss_signal = False
        
        # 检查卖出条件详情中是否有止损信号
        for detail in snap.sell_details:
            if detail.indicator == "STOP_LOSS" and detail.passed:
                has_stop_loss_signal = True
                break
        
        status = "✓" if has_stop_loss_signal == expected_signal else "✗"
        result = "通过" if has_stop_loss_signal == expected_signal else "失败"
        
        print(f"{status} 第{idx+1}天 ({snap.dt.strftime('%Y-%m-%d')}): {desc}")
        print(f"   价格: {snap.price:.2f}, 期望止损信号: {expected_signal}, 实际: {has_stop_loss_signal} - {result}")
        
        if has_stop_loss_signal != expected_signal:
            all_passed = False
            print(f"   详细信息: sell_passed_count={snap.sell_passed_count}, sell_result={snap.sell_result}")
            for detail in snap.sell_details:
                if detail.indicator == "STOP_LOSS":
                    print(f"   止损条件: passed={detail.passed}, score={detail.score}")
        print()
    
    print("=" * 80)
    if all_passed:
        print("✓ 所有测试通过！止损波形图现在正确显示：")
        print("  - 只在持仓期间评估")
        print("  - 基于真实买入价计算")
        print("  - 卖出后信号消失")
    else:
        print("✗ 部分测试失败")
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    success = test_stop_loss_waveform()
    sys.exit(0 if success else 1)