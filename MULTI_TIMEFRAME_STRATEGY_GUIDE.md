# vnpy 多周期策略使用指南

## 概述

vnpy 现已支持多周期策略开发，允许你在一个策略中同时使用不同周期的数据进行决策。例如：
- 日线判断趋势，5分钟寻找入场点
- 周线确认大趋势，日线执行交易
- 小时线识别形态，15分钟精准入场

本指南将帮助你快速上手多周期策略的编写和回测。

---

## 快速开始

### 1. 基本概念

**多周期策略的核心思想**：
```
策略执行周期（Execution Interval）
    ↓
条件 A: data_interval = 日线
条件 B: data_interval = 5分钟
条件 C: data_interval = None (使用执行周期)
    ↓
引擎自动加载各周期数据并评估
```

**关键组件**：
- `Condition.data_interval`: 指定条件使用的数据周期
- `MultiTimeframeContext`: 管理多周期数据的上下文
- `analyze_data_requirements()`: 分析策略需要哪些周期的数据
- `ScanEngine`: 自动检测并执行多周期评估

---

## 编写多周期策略

### 示例 1：日线趋势 + 5分钟放量

```python
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.core.condition_tree import ConditionNode
from vnpy.strategy_condition.core.strategy import Strategy, StrategyMeta, StrategyParams
from vnpy.strategy_condition.constant import ConditionCategory, ConditionIndicator
from vnpy.trader.constant import Interval

# 条件 1: 日线 MA20 向上
daily_ma = Condition(
    category=ConditionCategory.TREND,
    indicator=ConditionIndicator.MA_SLOPE,
    params={"ma_period": 20, "slope_window": 5, "min_slope": 0.0},
    data_interval=Interval.DAILY,  # ← 关键：指定使用日线
    label="日线MA20向上",
    enabled=True
)

# 条件 2: 5分钟放量
minute_volume = Condition(
    category=ConditionCategory.VOLUME,
    indicator=ConditionIndicator.VOLUME_RATIO,
    params={"period": 20, "min_ratio": 1.5},
    data_interval=Interval.MINUTE_5,  # ← 关键：指定使用5分钟
    label="5分钟放量",
    enabled=True
)

# 构造策略（AND 逻辑：两个条件都要满足）
buy_tree = ConditionNode.and_node(
    ConditionNode.leaf(daily_ma),
    ConditionNode.leaf(minute_volume),
    label="多周期买入条件"
)

# 卖出条件（止损止盈）
sell_tree = ConditionNode.or_node(
    ConditionNode.leaf(Condition(
        ConditionCategory.EXIT,
        ConditionIndicator.STOP_LOSS,
        {"pct": 8.0}
    )),
    ConditionNode.leaf(Condition(
        ConditionCategory.EXIT,
        ConditionIndicator.TAKE_PROFIT,
        {"pct": 15.0}
    ))
)

# 完整策略
strategy = Strategy(
    meta=StrategyMeta(
        name="多周期示例策略",
        description="日线趋势过滤 + 5分钟放量触发"
    ),
    buy_tree=buy_tree,
    sell_tree=sell_tree,
    params=StrategyParams(
        max_hold_days=30,
        stop_loss_pct=8.0,
        take_profit_pct=15.0
    )
)
```

### 示例 2：周线 + 日线 + 小时线

```python
# 周线：确认大趋势
weekly_trend = Condition(
    ConditionCategory.TREND,
    ConditionIndicator.MA_ALIGNMENT,
    {"periods": [5, 10, 20], "max_gap_pct": 5.0},
    data_interval=Interval.WEEKLY,
    label="周线多头排列"
)

# 日线：确认中期趋势
daily_pullback = Condition(
    ConditionCategory.MOMENTUM,
    ConditionIndicator.RSI_RANGE,
    {"period": 14, "min": 30, "max": 50},
    data_interval=Interval.DAILY,
    label="日线回调到位"
)

# 小时线：寻找入场点
hourly_macd = Condition(
    ConditionCategory.MOMENTUM,
    ConditionIndicator.MACD_GOLDEN,
    {"fast": 12, "slow": 26, "signal": 9},
    data_interval=Interval.HOUR,
    label="小时线MACD金叉"
)

# 三周期联动
buy_tree = ConditionNode.and_node(
    ConditionNode.leaf(weekly_trend),
    ConditionNode.leaf(daily_pullback),
    ConditionNode.leaf(hourly_macd),
    label="三周期联动买入"
)
```

---

## 执行回测

### 方法 1：使用 ScanEngine（推荐）

```python
from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
from vnpy.strategy_condition.engine.scan_engine import ScanEngine

# 初始化引擎
ce = ConditionEngine()
se = ScanEngine(condition_engine=ce)

# 准备数据（每个股票的K线列表）
all_bars_dict = {
    "600000.SH": daily_bars_list,
    "000001.SZ": daily_bars_list,
    # ... 更多股票
}

# 执行回测
batch = se.backtest(
    symbols=["600000.SH", "000001.SZ"],
    strategy=strategy,
    all_bars_dict=all_bars_dict,
    warmup=60,  # 预热期
    is_intraday=False,  # 是否分钟线回测
    execution_interval=Interval.DAILY  # 策略执行周期
)

# 查看结果
print(f"总信号数: {batch.count}")
for sig in batch.signals:
    print(f"{sig.symbol}: 买入 {sig.price:.2f}, "
          f"卖出 {sig.exit_price:.2f}, "
          f"收益 {sig.pnl_pct*100:.2f}%")
```

### 方法 2：运行完整示例

```bash
# 运行多周期策略演示
cd vnpy
python examples/multi_timeframe_strategy_demo.py
```

**输出示例**：
```
======================================================================
                              多周期策略回测演示
======================================================================

[步骤 1] 创建多周期策略
策略名称: 多周期示例策略
...

[步骤 6] 回测结果分析
  总信号数: 8
  盈利笔数: 4
  亏损笔数: 4
  平均收益: 0.66%

  交易明细（前5笔）:
  代码         买入日        卖出日        持仓天   收益%      原因
  600000.SH    2024-03-13   2024-04-08   26       +15.35%    take_profit
  600000.SH    2024-04-18   2024-05-20   32       +4.97%     max_hold
  ...
```

---

## 常用周期组合

### 1. 趋势跟踪型

**周线确认 + 日线执行**
```python
# 适合中长线持仓
weekly_ma = Condition(..., data_interval=Interval.WEEKLY)
daily_entry = Condition(..., data_interval=Interval.DAILY)
```

**日线过滤 + 小时线触发**
```python
# 适合短线波段
daily_trend = Condition(..., data_interval=Interval.DAILY)
hourly_signal = Condition(..., data_interval=Interval.HOUR)
```

### 2. 突破型

**日线突破 + 15分钟确认**
```python
daily_breakout = Condition(
    ConditionIndicator.NEW_HIGH_N,
    {"n": 20},
    data_interval=Interval.DAILY
)
minute_volume = Condition(
    ConditionIndicator.VOLUME_RATIO,
    {"min_ratio": 2.0},
    data_interval=Interval.MINUTE_15
)
```

### 3. 回调买入型

**周线上升 + 日线回调 + 小时反弹**
```python
weekly_up = Condition(..., data_interval=Interval.WEEKLY)
daily_pullback = Condition(..., data_interval=Interval.DAILY)
hourly_bounce = Condition(..., data_interval=Interval.HOUR)
```

---

## 数据周期说明

### 支持的周期

```python
from vnpy.trader.constant import Interval

Interval.TICK          # Tick数据
Interval.MINUTE_1      # 1分钟
Interval.MINUTE_5      # 5分钟
Interval.MINUTE_15     # 15分钟
Interval.MINUTE_30     # 30分钟
Interval.HOUR          # 1小时
Interval.DAILY         # 日线
Interval.WEEKLY        # 周线
Interval.MONTHLY       # 月线
```

### 周期选择建议

| 交易风格 | 主周期 | 辅助周期 | 说明 |
|---------|--------|---------|------|
| 超短线 | 5分钟 | 1分钟 | 日内交易 |
| 短线 | 日线 | 30分钟/1小时 | 持仓1-5天 |
| 波段 | 日线 | 日线/周线 | 持仓1-4周 |
| 中线 | 周线 | 日线 | 持仓1-3个月 |
| 长线 | 月线 | 周线 | 持仓3个月以上 |

---

## 策略诊断

### 检查策略是否为多周期

```python
from vnpy.strategy_condition.core.mtf_context import analyze_data_requirements

# 分析策略数据需求
req = analyze_data_requirements(strategy.buy_tree, Interval.DAILY)

print(f"执行周期: {req.strategy_execution_interval.value}")
print(f"需要的数据周期: {[i.value for i in req.intervals]}")
print(f"是否多周期: {len(req.intervals) > 1}")

# 查看每个条件的周期
for cond in strategy.buy_tree.all_conditions():
    interval = cond.data_interval.value if cond.data_interval else "执行周期"
    print(f"  - {cond.label}: {interval}")
```

**输出示例**：
```
执行周期: d
需要的数据周期: ['d', '5m']
是否多周期: True
  - 日线MA20向上: d
  - 5分钟放量: 5m
```

---

## 注意事项

### 1. 数据对齐（Phase 5 待完善）

当前版本（Phase 4）的多周期数据加载是简化实现：
- 所有周期暂时使用相同的数据源
- 真正的多周期数据对齐将在 Phase 5 实现

**建议**：
- 优先使用日线级别的多周期策略（周线+日线）
- 分钟级别的多周期需等待 Phase 5 完善

### 2. 数据需求

不同周期组合对数据量的要求：
```python
# 示例：MA20 需要至少 20 根K线
params = StrategyParams(
    min_bars=60,  # 建议预留 2-3 倍的最大周期参数
)
```

### 3. 执行周期的选择

**原则**：执行周期 ≤ 最小数据周期

```python
# ✓ 正确：执行周期 = 5分钟，数据周期 = 日线+5分钟
execution_interval=Interval.MINUTE_5

# ✗ 错误：执行周期 = 日线，但有5分钟条件
# （日线执行时无法获得日内的5分钟数据）
execution_interval=Interval.DAILY  # 不推荐
```

### 4. 性能考虑

多周期策略需要加载更多数据：
- 使用 `warmup` 参数控制预热期长度
- 考虑使用缓存减少重复加载
- 并行回测自动启用（股票数 ≥ 4）

---

## 常见问题

### Q1: 为什么回测没有产生信号？

**可能原因**：
1. 预热期过滤了符合条件的K线
2. 条件太严格，数据不满足
3. 冷却期限制了重复交易

**调试方法**：
```python
# 降低预热期
batch = se.backtest(..., warmup=30)  # 从60改为30

# 放宽条件
params={"ma_period": 10, "min_slope": -0.001}  # 降低阈值

# 缩短冷却期
params=StrategyParams(cooldown_days=1)  # 从5改为1
```

### Q2: 如何保存和加载多周期策略？

```python
# 保存
strategy_dict = strategy.to_dict()
import json
with open("my_strategy.json", "w", encoding="utf-8") as f:
    json.dump(strategy_dict, f, ensure_ascii=False, indent=2)

# 加载
with open("my_strategy.json", "r", encoding="utf-8") as f:
    strategy_dict = json.load(f)
strategy = Strategy.from_dict(strategy_dict)
```

`data_interval` 会自动保存和恢复。

### Q3: 可以混合使用多周期和单周期条件吗？

可以！未指定 `data_interval` 的条件会使用执行周期：

```python
# 混合策略
buy_tree = ConditionNode.and_node(
    # 多周期条件
    ConditionNode.leaf(Condition(..., data_interval=Interval.DAILY)),
    # 单周期条件（使用执行周期）
    ConditionNode.leaf(Condition(..., data_interval=None)),
)
```

---

## 下一步

1. **运行示例**：`python examples/multi_timeframe_strategy_demo.py`
2. **修改策略**：尝试不同的周期组合和指标
3. **实盘准备**：等待 Phase 5 完成后进行实盘测试

**Phase 5 路线图**：
- 完善多周期数据加载和对齐
- UI 界面支持周期选择
- 性能优化和缓存机制

---

## 技术支持

- **文档**: `MTF_PHASE4_COMPLETE.md` - Phase 4 完成报告
- **测试**: `tests/test_mtf_phase4.py` - 单元测试
- **示例**: `examples/multi_timeframe_strategy_demo.py` - 完整演示

**相关文件**：
- `vnpy/strategy_condition/core/condition.py` - Condition 数据模型
- `vnpy/strategy_condition/core/mtf_context.py` - 多周期上下文
- `vnpy/strategy_condition/engine/condition_engine.py` - 条件评估引擎
- `vnpy/strategy_condition/engine/scan_engine.py` - 扫描和回测引擎

祝你开发出强大的多周期策略！🚀