# -*- coding: utf-8 -*-
"""
多周期策略示例与回测演示

策略逻辑：
- 日线级别：MA20 趋势向上（过滤层）
- 5分钟级别：放量突破（触发层）
- 卖出：止损 8% 或止盈 15%

这是一个典型的"日线过滤 + 分钟触发"多周期策略。
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime, timedelta
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.core.condition_tree import ConditionNode
from vnpy.strategy_condition.core.strategy import Strategy, StrategyMeta, StrategyParams
from vnpy.strategy_condition.constant import ConditionCategory, ConditionIndicator
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
from vnpy.strategy_condition.engine.scan_engine import ScanEngine
from vnpy.trader.constant import Interval


# ==================== 模拟数据生成 ====================

class MockBar:
    """模拟 K 线数据"""
    def __init__(self, dt, open_price, high, low, close, volume):
        self.dt = dt
        self.datetime = dt
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

    def __repr__(self):
        return f"Bar({self.dt.strftime('%Y-%m-%d %H:%M')}, C={self.close:.2f})"


def generate_realistic_bars(n: int, start_price: float = 100.0,
                            interval: Interval = Interval.DAILY) -> list:
    """
    生成更真实的模拟K线数据
    - 包含趋势、波动和成交量变化
    - 日线：每天一根
    - 5分钟线：每5分钟一根
    """
    import random
    import math
    
    bars = []
    base_date = datetime(2024, 1, 1, 9, 30)  # 从 2024-01-01 9:30 开始
    
    price = start_price
    base_volume = 1000000
    
    for i in range(n):
        # 计算时间
        if interval == Interval.DAILY:
            dt = base_date + timedelta(days=i)
            # 跳过周末
            while dt.weekday() >= 5:
                dt += timedelta(days=1)
        else:  # 分钟线
            dt = base_date + timedelta(minutes=i * 5)
            # 跳过非交易时间
            if dt.hour < 9 or dt.hour >= 15:
                continue
            if dt.hour == 9 and dt.minute < 30:
                continue
        
        # 生成价格波动（带趋势）
        # 前半段上涨，后半段震荡
        if i < n * 0.6:
            trend = 0.003  # 上涨趋势
        else:
            trend = -0.001  # 轻微下跌
        
        # 随机波动
        volatility = 0.015
        price_change = (trend + random.gauss(0, volatility)) * price
        price = max(price + price_change, start_price * 0.7)  # 不跌破起始价的70%
        
        # 生成 OHLC
        daily_range = price * 0.02  # 2% 的日内波动
        open_price = price + random.gauss(0, daily_range * 0.3)
        close = price + random.gauss(0, daily_range * 0.3)
        high = max(open_price, close) + abs(random.gauss(0, daily_range * 0.5))
        low = min(open_price, close) - abs(random.gauss(0, daily_range * 0.5))
        
        # 生成成交量（上涨时放量）
        if close > open_price:
            volume_mult = 1.0 + random.uniform(0.2, 0.8)
        else:
            volume_mult = 1.0 - random.uniform(0, 0.3)
        volume = int(base_volume * volume_mult * (1 + random.gauss(0, 0.2)))
        volume = max(volume, base_volume * 0.3)
        
        bars.append(MockBar(dt, open_price, high, low, close, volume))
    
    return bars


# ==================== 多周期策略定义 ====================

def create_mtf_strategy() -> Strategy:
    """
    创建多周期策略
    
    买入条件（AND）：
      1. 日线 MA20 向上（斜率 > 0）
      2. 5分钟放量（量比 > 1.5）
    
    卖出条件（OR）：
      1. 止损 8%
      2. 止盈 15%
    """
    # 日线条件：MA20 趋势向上
    daily_ma = Condition(
        category=ConditionCategory.TREND,
        indicator=ConditionIndicator.MA_SLOPE,
        params={"ma_period": 20, "slope_window": 5, "min_slope": 0.0},
        data_interval=Interval.DAILY,  # ← 指定使用日线数据
        label="日线MA20向上",
        enabled=True
    )
    
    # 5分钟条件：放量
    minute_volume = Condition(
        category=ConditionCategory.VOLUME,
        indicator=ConditionIndicator.VOLUME_RATIO,
        params={"period": 20, "min_ratio": 1.5},
        data_interval=Interval.MINUTE_5,  # ← 指定使用5分钟数据
        label="5分钟放量",
        enabled=True
    )
    
    # 买入条件树：日线 AND 分钟
    buy_tree = ConditionNode.and_node(
        ConditionNode.leaf(daily_ma),
        ConditionNode.leaf(minute_volume),
        label="多周期买入条件"
    )
    
    # 卖出条件
    stop_loss = Condition(
        category=ConditionCategory.EXIT,
        indicator=ConditionIndicator.STOP_LOSS,
        params={"pct": 8.0},
        label="止损8%",
        enabled=True
    )
    
    take_profit = Condition(
        category=ConditionCategory.EXIT,
        indicator=ConditionIndicator.TAKE_PROFIT,
        params={"pct": 15.0},
        label="止盈15%",
        enabled=True
    )
    
    sell_tree = ConditionNode.or_node(
        ConditionNode.leaf(stop_loss),
        ConditionNode.leaf(take_profit),
        label="卖出条件"
    )
    
    # 构造策略
    strategy = Strategy(
        meta=StrategyMeta(
            name="多周期示例策略",
            version="1.0.0",
            description="日线MA20过滤 + 5分钟放量触发",
            author="Kiro",
            tags=["多周期", "趋势", "放量"]
        ),
        buy_tree=buy_tree,
        sell_tree=sell_tree,
        params=StrategyParams(
            max_hold_days=30,
            stop_loss_pct=8.0,
            take_profit_pct=15.0,
            min_bars=60,
            cooldown_days=5,
        )
    )
    
    return strategy


# ==================== 回测执行 ====================

def run_backtest_demo():
    """运行多周期策略回测演示"""
    print("=" * 70)
    print("多周期策略回测演示".center(70))
    print("=" * 70)
    
    # 1. 创建策略
    print("\n[步骤 1] 创建多周期策略")
    strategy = create_mtf_strategy()
    print(f"策略名称: {strategy.name}")
    print(f"版本: {strategy.meta.version}")
    print(f"描述: {strategy.meta.description}")
    print(f"\n{strategy.summary()}")
    
    # 2. 生成模拟数据
    print("\n[步骤 2] 生成模拟数据")
    print("  生成日线数据...")
    daily_bars = generate_realistic_bars(200, 100.0, Interval.DAILY)
    print(f"  ✓ 日线: {len(daily_bars)} 根")
    
    print("  生成5分钟数据...")
    minute_bars = generate_realistic_bars(1000, 100.0, Interval.MINUTE_5)
    print(f"  ✓ 5分钟线: {len(minute_bars)} 根")
    
    # 显示数据样本
    print(f"\n  日线样本:")
    print(f"    起始: {daily_bars[0]}")
    print(f"    结束: {daily_bars[-1]}")
    print(f"  5分钟样本:")
    print(f"    起始: {minute_bars[0]}")
    print(f"    结束: {minute_bars[-1]}")
    
    # 3. 初始化引擎
    print("\n[步骤 3] 初始化回测引擎")
    ce = ConditionEngine(log_fn=lambda msg: print(f"    {msg}"))
    se = ScanEngine(condition_engine=ce, log_fn=lambda msg: print(f"    {msg}"))
    print("  ✓ ConditionEngine 初始化完成")
    print("  ✓ ScanEngine 初始化完成")
    
    # 4. 准备回测数据
    #注意：由于当前简化实现，我们使用日线数据作为回测基准
    # TODO: Phase 5 需要实现真正的多周期数据对齐
    print("\n[步骤 4] 准备回测数据")
    symbols = ["600000.SH", "000001.SZ"]
    all_bars_dict = {
        "600000.SH": daily_bars,
        "000001.SZ": daily_bars,  # 简化：使用相同数据
    }
    print(f"  股票数量: {len(symbols)}")
    print(f"  回测K线: {len(daily_bars)} 根（日线）")
    
    # 5. 执行回测
    print("\n[步骤 5] 执行多周期回测")
    print("  注意：由于数据加载简化，实际会使用日线数据评估所有条件")
    print("  完整多周期数据对齐将在 Phase 5 实现\n")
    
    batch = se.backtest(
        symbols=symbols,
        strategy=strategy,
        all_bars_dict=all_bars_dict,
        warmup=60,
        is_intraday=False,
        execution_interval=Interval.DAILY  # 策略执行周期
    )
    
    # 6. 分析结果
    print("\n[步骤 6] 回测结果分析")
    print("=" * 70)
    
    if batch.count == 0:
        print("  ⚠ 未产生交易信号")
        print("  可能原因：")
        print("    1. 数据不满足条件（MA趋势不向上 or 未放量）")
        print("    2. 预热期过滤了早期数据")
        print("    3. 冷却期限制了重复交易")
    else:
        print(f"  总信号数: {batch.count}")
        
        # 统计收益
        profitable = [s for s in batch.signals if s.pnl_pct and s.pnl_pct > 0]
        loss = [s for s in batch.signals if s.pnl_pct and s.pnl_pct <= 0]
        
        print(f"  盈利笔数: {len(profitable)}")
        print(f"  亏损笔数: {len(loss)}")
        
        if batch.signals:
            avg_pnl = sum(s.pnl_pct for s in batch.signals if s.pnl_pct) / len(batch.signals)
            print(f"  平均收益: {avg_pnl*100:.2f}%")
            
            # 显示前5笔交易
            print(f"\n  交易明细（前5笔）:")
            print("  " + "-" * 66)
            print(f"  {'代码':<12} {'买入日':<12} {'卖出日':<12} {'持仓天':<8} {'收益%':<10} {'原因':<12}")
            print("  " + "-" * 66)
            
            for i, sig in enumerate(batch.signals[:5]):
                buy_date = sig.dt.strftime('%Y-%m-%d') if sig.dt else "—"
                sell_date = sig.exit_dt.strftime('%Y-%m-%d') if sig.exit_dt else "—"
                pnl_str = f"{sig.pnl_pct*100:+.2f}%" if sig.pnl_pct else "—"
                reason = sig.exit_reason or "—"
                
                print(f"  {sig.symbol:<12} {buy_date:<12} {sell_date:<12} "
                      f"{sig.hold_days:<8} {pnl_str:<10} {reason:<12}")
    
    print("=" * 70)
    
    # 7. 策略诊断
    print("\n[步骤 7] 多周期策略诊断")
    from vnpy.strategy_condition.core.mtf_context import analyze_data_requirements
    
    req = analyze_data_requirements(strategy.buy_tree, Interval.DAILY)
    print(f"  策略执行周期: {req.strategy_execution_interval.value}")
    print(f"  需要的数据周期: {[i.value for i in req.intervals]}")
    print(f"  是否多周期: {'是' if len(req.intervals) > 1 else '否'}")
    
    # 显示每个条件的周期需求
    print(f"\n  条件分解:")
    for cond in strategy.buy_tree.all_conditions():
        interval_str = cond.data_interval.value if cond.data_interval else "default"
        print(f"    - {cond.label}: {interval_str}")
    
    print("\n" + "=" * 70)
    print("回测演示完成！")
    print("=" * 70)


if __name__ == "__main__":
    run_backtest_demo()