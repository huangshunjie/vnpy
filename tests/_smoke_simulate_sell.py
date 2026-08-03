"""验证 _simulate_sell_dates 内部模拟卖出逻辑"""
from datetime import datetime, timedelta
from vnpy.strategy_condition.monitor.condition_monitor_engine import ConditionMonitorEngine
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
from vnpy.strategy_condition.templates.builtin import get_all_templates


class FakeBar:
    def __init__(self, dt, o, h, l, c, v):
        self.dt = dt
        self.open = o
        self.high = h
        self.low = l
        self.close = c
        self.volume = v


# 100根K线：
#   bar 0-19: close=10 (平盘)
#   bar 20-39: 从10涨到12 (每根+0.1)
#   bar 40-59: 从12跌到8 (每根-0.2)
#   bar 60-99: close=8 (平盘)
bars = []
base = datetime(2024, 1, 1)
for i in range(100):
    d = base + timedelta(days=i)
    if i < 20:
        c = 10.0
    elif i < 40:
        c = 10.0 + (i - 20) * 0.1  # 涨到12
    elif i < 60:
        c = 12.0 - (i - 40) * 0.2  # 跌到8
    else:
        c = 8.0
    bars.append(FakeBar(d, c, c + 0.1, c - 0.1, c, 1000))

# 使用第一个内置模板策略
strategy = get_all_templates()[0]
print(f"Strategy: {strategy.name}")
print(f"Sell tree: {strategy.sell_tree}")
print(f"Params: stop_loss={strategy.params.stop_loss_pct}%, "
      f"take_profit={strategy.params.take_profit_pct}%, "
      f"trail_drawdown={strategy.params.trail_drawdown}%")

ce = ConditionEngine()
me = ConditionMonitorEngine(ce)

buy_dates = ['2024-01-21']  # bar index 20, close=10
result = me._simulate_sell_dates('TEST.SSE', bars, strategy, buy_dates, 10)
print(f"\n=== _simulate_sell_dates ===")
print(f"Buy date: 2024-01-21 (bar 20, close=10.0)")
print(f"Simulated sell dates: {result}")

# 验证 generate_snapshots 传播
snapshots = me.generate_snapshots(
    'TEST.SSE', bars, strategy,
    warmup=10, buy_dates=buy_dates, sell_dates=[])
print(f"\n=== generate_snapshots ===")
print(f"Snapshots count: {len(snapshots)}")
print(f"last_simulated_sell_dates: {me.last_simulated_sell_dates}")

if result:
    print("\n✅ 内部模拟卖出成功！")
else:
    print("\n⚠️  未产生卖出点 - 可能策略条件在此价格序列下未触发")
    # 打印一些关键价格节点来帮助诊断
    print(f"  bar 39 close: {bars[39].close:.2f} (peak)")
    print(f"  bar 50 close: {bars[50].close:.2f}")
    print(f"  bar 59 close: {bars[59].close:.2f}")
    # 手动检查 trailing stop: peak=12, 回撤10% → 触发价=12*(1-0.1)=10.8
    # bar 46: 12-6*0.2=10.8 → 应该触发
    print(f"  bar 46 close: {bars[46].close:.2f} (预期触发trailing stop)")