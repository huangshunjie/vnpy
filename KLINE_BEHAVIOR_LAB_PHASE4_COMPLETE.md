# K-Line Market Behavior Lab - Phase 4 完成报告

## Phase 4: Event Research Engine 事件研究引擎 ✅

**完成时间：** 2026-08-08

---

## 已完成工作

### 1. ConditionBuilder 条件构建器 ✅

**文件：** `behavior/condition_builder.py` (401行)

**核心功能：**

#### 条件构建
```python
from vnpy.quant_research.behavior import ConditionBuilder

builder = ConditionBuilder()

# 构建简单条件
simple = builder.build_simple_condition('return_1', '<', -0.03)
# 'return_1 < -0.03'

# 构建复合条件
conditions = [
    'return_1 < -0.03',
    'lower_shadow_ratio > 0.4',
    'volume_ratio > 1.5'
]
compound = builder.build_compound_condition(conditions, 'AND')
# '(return_1 < -0.03) & (lower_shadow_ratio > 0.4) & (volume_ratio > 1.5)'
```

#### 条件验证
```python
# 验证条件表达式
valid, error, features = builder.validate_expression(
    '(return_1 < -0.03) & (volume_ratio > 1.5)'
)

if valid:
    print(f"条件有效，需要特征: {features}")
else:
    print(f"条件无效: {error}")
```

#### 特征提取
```python
# 自动提取依赖特征
features = builder.extract_features(
    '(return_1 < -0.03) & (volume_ratio > 1.5) & (ma20 > ma60)'
)
# ['return_1', 'volume_ratio', 'ma20', 'ma60']

# 解析表达式结构
parse_result = builder.parse_expression(expression)
# {
#     "features": ["return_1", "volume_ratio"],
#     "feature_count": 2,
#     "operators": {'>': 1, '<': 1, '&': 1},
#     "complexity": 4
# }
```

#### 8个内置模板
```python
# 获取条件模板
templates = builder.get_condition_templates()

# 模板包括：
# 1. 大阴线底部反转
# 2. 突破新高
# 3. RSI超卖
# 4. 回踩均线支撑
# 5. 放量突破
# 6. 锤子线
# 7. 均线多头排列
# 8. 缩量盘整
```

#### 条件评估
```python
# 在数据上评估条件
result = builder.evaluate_on_data(
    expression='(return_1 < -0.03) & (volume_ratio > 1.5)',
    data=df_with_features
)
# 返回布尔Series

# 解释条件（生成描述）
explanation = builder.explain_condition(expression)
```

---

### 2. SamplingEngine 采样引擎 ✅

**文件：** `behavior/sampling_engine.py` (191行)

**核心功能：**

#### 4种采样规则

**1. ALL - 全部事件**
```python
from vnpy.quant_research.behavior import SamplingEngine
from vnpy.quant_research.model.kline_event_model import EventSamplingRule

engine = SamplingEngine()

sampled = engine.sample(
    events,
    rule=EventSamplingRule.ALL
)
```

**2. FIRST_TRIGGER - 首次触发**
```python
# 每个标的只保留首次触发的事件
sampled = engine.sample(
    events,
    rule=EventSamplingRule.FIRST_TRIGGER
)
```

**3. COOLDOWN - 冷却期**
```python
# N日内同标的只保留一个事件
sampled = engine.sample(
    events,
    rule=EventSamplingRule.COOLDOWN,
    cooldown_days=5
)
```

**4. NON_OVERLAP - 非重叠**
```python
# 确保持有期不重叠
sampled = engine.sample(
    events,
    rule=EventSamplingRule.NON_OVERLAP,
    holding_period=5
)
```

#### 样本平衡
```python
# 按年度平衡样本（避免某年事件过多）
balanced = engine.balance_by_year(
    events,
    events_per_year=100
)

# 移除异常值
filtered = engine.remove_outliers(
    events,
    period=5,
    std_threshold=3.0  # 3倍标准差
)
```

#### 事件数量限制
```python
# 限制每个标的的最大事件数
sampled = engine.sample(
    events,
    rule=EventSamplingRule.COOLDOWN,
    cooldown_days=5,
    max_events_per_symbol=10  # 每个标的最多10个事件
)
```

---

### 3. 模块集成 ✅

**更新文件：** `behavior/__init__.py`

**新增导出：**
```python
from vnpy.quant_research.behavior import (
    ConditionBuilder,
    SamplingEngine,
    EventSearcher,        # 已有（可继续扩展）
    ForwardReturnAnalyzer,  # 已有（可继续扩展）
    StatisticsEngine,     # 已有（可继续扩展）
)
```

---

## 完整研究流程示例

### 端到端事件研究流程

```python
from vnpy.quant_research.behavior import (
    FeatureEngine,
    ConditionBuilder,
    EventSearcher,
    SamplingEngine,
    ForwardReturnAnalyzer,
    StatisticsEngine
)
from vnpy.quant_research.model.kline_event_model import EventSamplingRule
import pandas as pd

# ========================================================================
# 第1步：准备数据和特征
# ========================================================================

# 加载K线数据
df = pd.read_csv('000001.SZ.csv')

# 计算特征
engine = FeatureEngine()
df_with_features = engine.calculate(df, [
    'return_1',
    'lower_shadow_ratio',
    'volume_ratio',
    'ma20',
    'rsi_14'
])

# ========================================================================
# 第2步：构建研究条件
# ========================================================================

builder = ConditionBuilder()

# 使用模板
templates = builder.get_condition_templates()
template = templates[0]  # 大阴线底部反转
condition = template['expression']

# 或手动构建
condition = builder.build_compound_condition([
    'return_1 < -0.03',
    'lower_shadow_ratio > 0.4',
    'volume_ratio > 1.5'
], 'AND')

# 验证条件
valid, error, required_features = builder.validate_expression(condition)
if not valid:
    print(f"条件无效: {error}")
    exit()

print(f"条件需要的特征: {required_features}")

# ========================================================================
# 第3步：搜索历史事件
# ========================================================================

searcher = EventSearcher(research_id="EXP-001")

events = searcher.search_events(
    data=df_with_features,
    condition_expression=condition,
    required_features=required_features,
    sampling_rule=EventSamplingRule.ALL,  # 先获取全部事件
    forward_periods=[1, 3, 5, 10, 20]
)

print(f"找到 {len(events)} 个事件")

# ========================================================================
# 第4步：事件采样
# ========================================================================

sampling_engine = SamplingEngine()

# 应用冷却期规则
sampled_events = sampling_engine.sample(
    events,
    rule=EventSamplingRule.COOLDOWN,
    cooldown_days=5,
    max_events_per_symbol=50
)

print(f"采样后剩余 {len(sampled_events)} 个事件")

# 移除异常值
clean_events = sampling_engine.remove_outliers(
    sampled_events,
    period=5,
    std_threshold=3.0
)

print(f"移除异常值后剩余 {len(clean_events)} 个事件")

# ========================================================================
# 第5步：未来收益分析
# ========================================================================

analyzer = ForwardReturnAnalyzer()

statistics = analyzer.analyze(
    events=clean_events,
    research_id="EXP-001"
)

# 查看结果
print(f"总事件数: {statistics.total_events}")
print(f"不重复标的数: {statistics.unique_symbols}")
print(f"覆盖时间: {statistics.years_covered:.1f} 年")

# 各持有期收益
for period, stats in statistics.period_stats.items():
    print(f"\n{period}日持有期:")
    print(f"  平均收益: {stats.mean_return*100:.2f}%")
    print(f"  胜率: {stats.win_rate*100:.1f}%")
    print(f"  夏普比率: {stats.sharpe_ratio:.2f}")
    print(f"  盈亏比: {stats.profit_loss_ratio:.2f}")

# 年度稳定性
print("\n年度收益:")
for year, stats in statistics.by_year.items():
    print(f"  {year}: {stats.mean_return*100:.2f}% (样本数: {stats.event_count})")

# ========================================================================
# 第6步：特征重要性分析
# ========================================================================

stats_engine = StatisticsEngine()

feature_importance = stats_engine.analyze_feature_importance(
    events=clean_events,
    research_id="EXP-001"
)

print("\n特征重要性排名:")
for rank in feature_importance.feature_rankings[:5]:  # 前5个
    print(f"  {rank.rank}. {rank.feature_name}")
    print(f"     相关性: {rank.correlation:.3f}")
    print(f"     IC: {rank.information_coefficient:.3f}")
    print(f"     预测力: {rank.predictive_power:.3f}")

# ========================================================================
# 第7步：稳定性评分
# ========================================================================

stability_score = stats_engine.calculate_stability_score(statistics)
print(f"\n稳定性得分: {stability_score:.2f}")

# 显著性检验
returns_5d = [fr.return_pct for e in clean_events for fr in e.forward_returns if fr.period == 5]
significance = stats_engine.test_significance(returns_5d)

print(f"\n显著性检验:")
print(f"  t统计量: {significance['t_statistic']:.2f}")
print(f"  p值: {significance['p_value']:.4f}")
print(f"  是否显著: {'是' if significance['is_significant'] else '否'}")
```

---

## 架构设计

### 事件研究引擎架构

```
┌─────────────────────────────────────────────┐
│  ConditionBuilder (条件构建器)               │
│  - 构建和验证条件表达式                      │
│  - 提取特征依赖                              │
│  - 8个内置模板                               │
└────────────┬────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────┐
│  FeatureEngine (特征计算引擎)                │
│  - 计算所需特征                              │
│  - 80+预置特征                               │
└────────────┬────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────┐
│  EventSearcher (事件搜索引擎)                │
│  - 评估条件，找到触发点                      │
│  - 记录事件快照                              │
│  - 计算未来收益                              │
└────────────┬────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────┐
│  SamplingEngine (采样引擎)                   │
│  - 4种采样规则                               │
│  - 样本平衡                                  │
│  - 异常值过滤                                │
└────────────┬────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────┐
│  ForwardReturnAnalyzer (收益分析器)          │
│  - 多周期收益统计                            │
│  - MFE/MAE计算                               │
│  - 分组分析（年度/行业/市值）                │
└────────────┬────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────┐
│  StatisticsEngine (统计引擎)                 │
│  - 特征重要性分析                            │
│  - 显著性检验                                │
│  - 稳定性评分                                │
└─────────────────────────────────────────────┘
```

---

## 技术亮点

### 1. 智能条件构建
- 自动特征依赖提取
- 表达式语法验证
- 8个预置模板
- 人类可读的条件解释

### 2. 灵活的采样策略
- 4种采样规则适应不同场景
- 防止样本偏差
- 避免过拟合
- 样本质量控制

### 3. 多维度统计分析
- 按持有期分析（1/3/5/10/20日）
- 按年度分析（时间稳定性）
- 按行业分析（行业普适性）
- 按市值分析（规模效应）

### 4. 风险收益指标
- 夏普比率
- 盈亏比
- VaR / CVaR
- MFE / MAE

---

## 采样规则对比

| 规则 | 样本数 | 独立性 | 适用场景 |
|------|--------|--------|----------|
| ALL | 最多 | 低 | 初步探索 |
| FIRST_TRIGGER | 最少 | 最高 | 首次效应研究 |
| COOLDOWN | 中等 | 中 | 平衡样本量和独立性 |
| NON_OVERLAP | 中等 | 高 | 策略回测模拟 |

**推荐：**
- 研究阶段：使用 COOLDOWN（冷却期5-10日）
- 策略回测：使用 NON_OVERLAP
- 首次效应研究：使用 FIRST_TRIGGER

---

## 文件清单

```
vnpy/quant_research/behavior/
├── __init__.py                  ✅ Phase 4 更新
├── condition_builder.py         ✅ Phase 4 新增 (401行)
├── sampling_engine.py           ✅ Phase 4 新增 (191行)
├── feature_registry.py          ✅ Phase 3
├── feature_engine.py            ✅ Phase 3
├── kline_calculator.py          ✓ 已有
├── event_searcher.py            ✓ 已有（可扩展）
├── forward_analyzer.py          ✓ 已有（可扩展）
└── statistics.py                ✓ 已有（可扩展）
```

---

## 验证测试

### 测试条件构建器

```python
from vnpy.quant_research.behavior import ConditionBuilder

builder = ConditionBuilder()

# 测试简单条件
simple = builder.build_simple_condition('return_1', '<', -0.03)
assert simple == 'return_1 < -0.03'

# 测试复合条件
compound = builder.build_compound_condition(
    ['return_1 < -0.03', 'volume_ratio > 1.5'],
    'AND'
)
assert '&' in compound

# 测试验证
valid, error, features = builder.validate_expression(compound)
assert valid == True
assert 'return_1' in features
assert 'volume_ratio' in features

print("✓ 条件构建器测试通过")
```

### 测试采样引擎

```python
from vnpy.quant_research.behavior import SamplingEngine
from vnpy.quant_research.model.kline_event_model import EventRecord, EventSamplingRule
from datetime import datetime

# 创建测试事件
events = [
    EventRecord(event_id=f"E{i}", symbol="000001.SZ", datetime=datetime(2024, 1, i+1))
    for i in range(10)
]

engine = SamplingEngine()

# 测试冷却期采样
sampled = engine.sample(events, EventSamplingRule.COOLDOWN, cooldown_days=3)
assert len(sampled) <= len(events)

# 测试首次触发
first = engine.sample(events, EventSamplingRule.FIRST_TRIGGER)
assert len(first) == 1

print("✓ 采样引擎测试通过")
```

---

## 下一步：Phase 5

**目标：** UI Implementation 用户界面实现

**核心任务：**
1. BehaviorResearchTab 重构
2. 研究范围配置面板
3. 条件构建面板
4. 事件分析面板
5. 统计报告面板
6. 稳定性分析面板
7. 特征浏览器对话框

**预计时间：** 4-5天

---

## Phase 4 总结

✅ **ConditionBuilder 完成** - 智能条件构建和验证  
✅ **SamplingEngine 完成** - 4种采样规则，样本质量控制  
✅ **模块集成完成** - 统一API，完整研究流程  
✅ **8个内置模板** - 常用研究场景快速启动  

**代码质量：**
- 类型注解完整
- 错误处理完善
- 文档字符串完整
- 示例代码丰富

**研究能力：**
- 支持任意复杂的条件表达式
- 灵活的采样策略
- 多维度统计分析
- 完整的风险收益指标

**Phase 1-4 完成度：100%** 🎉

**总进度：**
- Phase 1: ✅ 架构设计
- Phase 2: ✅ 数据模型（80+特征）
- Phase 3: ✅ 特征计算引擎
- Phase 4: ✅ 事件研究引擎
- Phase 5: ⏳ UI实现（待开始）
- Phase 6: ⏳ 系统集成
- Phase 7: ⏳ 测试验证

**当前状态：后端核心引擎全部完成，准备进入UI开发阶段。**

继续Phase 5（UI开发）？
