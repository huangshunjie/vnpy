# vnpy 多周期架构改造 Phase 5 规划

## 概述

Phase 5 是多周期架构的最后一个阶段，目标是实现**完整的多周期数据管理和 UI 集成**，使多周期策略能够在生产环境中正常运行。

**当前状态**（Phase 4 完成）：
- ✅ 多周期数据模型（MTFContext）
- ✅ 条件评估引擎支持多周期
- ✅ 策略执行引擎支持多周期
- ⚠️  数据加载是简化实现（所有周期使用同一数据源）

**Phase 5 目标**：
- 实现真正的多周期数据加载和对齐
- 实现周期转换（分钟→小时→日→周）
- UI 界面支持周期选择
- 性能优化和缓存机制

---

## 核心任务

### 任务 1: 周期转换器（BarResampler）

**目标**：实现 K 线数据的周期转换，支持从小周期聚合到大周期。

#### 1.1 基础转换器

```python
# vnpy/strategy_condition/data/bar_resampler.py

class BarResampler:
    """
    K线周期转换器
    
    支持的转换：
    - 分钟 → 小时 (5m → 1h)
    - 分钟 → 日线 (5m → 1d)
    - 日线 → 周线 (1d → 1w)
    - 日线 → 月线 (1d → 1M)
    """
    
    @staticmethod
    def resample(bars: list, from_interval: Interval, 
                 to_interval: Interval) -> list:
        """
        将 bars 从 from_interval 转换到 to_interval
        
        算法：
        1. 按目标周期分组（小时/日/周/月）
        2. 每组内聚合：
           - open = 第一根的 open
           - high = max(all high)
           - low = min(all low)
           - close = 最后一根的 close
           - volume = sum(all volume)
        3. datetime = 周期结束时间
        """
        pass
    
    @staticmethod
    def minute_to_hour(bars: list) -> list:
        """5分钟 → 1小时"""
        pass
    
    @staticmethod
    def minute_to_daily(bars: list) -> list:
        """分钟 → 日线"""
        pass
    
    @staticmethod
    def daily_to_weekly(bars: list) -> list:
        """日线 → 周线"""
        pass
```

#### 1.2 转换规则

| 源周期 | 目标周期 | 转换方法 | 说明 |
|--------|----------|---------|------|
| 1分钟 | 5分钟 | 按时间分组 | 每5分钟一组 |
| 5分钟 | 1小时 | 按小时分组 | 每小时12根5分钟 |
| 1小时 | 日线 | 按日期分组 | 交易时间内的所有小时线 |
| 日线 | 周线 | 按周分组 | 周一到周五 |
| 日线 | 月线 | 按月分组 | 每月所有交易日 |

**关键点**：
- 保持时间对齐（使用周期结束时间）
- 处理不完整周期（如当前未完成的小时/日/周）
- 考虑交易时间（9:30-15:00）

---

### 任务 2: 多周期 CandleBuffer

**目标**：扩展现有 CandleBuffer，支持多周期数据缓存和自动转换。

#### 2.1 MultiTimeframeCandleBuffer

```python
# vnpy/strategy_condition/data/mtf_candle_buffer.py

class MultiTimeframeCandleBuffer:
    """
    多周期K线缓存
    
    特性：
    1. 支持多个周期的数据缓存
    2. 自动从基础周期转换到目标周期
    3. 智能缓存策略（避免重复转换）
    4. 时间对齐保证
    """
    
    def __init__(self, base_buffer, base_interval: Interval = Interval.MINUTE_5):
        """
        Args:
            base_buffer: 基础数据源（通常是分钟线CandleBuffer）
            base_interval: 基础周期（最小周期，其他周期从它转换）
        """
        self._base = base_buffer
        self._base_interval = base_interval
        self._cache: Dict[str, Dict[Interval, list]] = {}  # symbol → interval → bars
        self._resampler = BarResampler()
    
    def get(self, symbol: str, n: int, interval: Interval) -> list:
        """
        获取指定周期的K线数据
        
        逻辑：
        1. 如果 interval == base_interval，直接从 base_buffer 获取
        2. 如果缓存中有且足够，返回缓存
        3. 否则，从 base_buffer 获取足够的基础数据，转换后缓存
        """
        if interval == self._base_interval:
            return self._base.get(symbol, n)
        
        # 检查缓存
        if self._has_cached(symbol, interval, n):
            return self._get_cached(symbol, interval, n)
        
        # 转换并缓存
        base_bars = self._fetch_base_bars(symbol, interval, n)
        converted = self._resampler.resample(base_bars, self._base_interval, interval)
        self._update_cache(symbol, interval, converted)
        return converted[-n:]
    
    def clear_cache(self, symbol: str = None, interval: Interval = None):
        """清空缓存"""
        pass
```

#### 2.2 缓存策略

**缓存时机**：
- 第一次请求某周期数据时转换并缓存
- 后续请求直接返回缓存

**缓存更新**：
- 增量更新：新数据到达时，只转换新增部分
- 定时清理：避免内存占用过大

**缓存失效**：
- 基础数据更新时，清空所有派生周期缓存
- 手动清空（测试/重置）

---

### 任务 3: ScanEngine 数据加载改造

**目标**：将 `_get_bars()` 改造为真正从不同数据源加载不同周期。

#### 3.1 改造方案

```python
# vnpy/strategy_condition/engine/scan_engine.py

class ScanEngine:
    def __init__(self, condition_engine, mtf_buffer=None, log_fn=None):
        """
        Args:
            mtf_buffer: MultiTimeframeCandleBuffer（新增）
        """
        self._ce = condition_engine
        self._mtf_buf = mtf_buffer  # 多周期缓存
        self._log = log_fn or print
    
    def _get_bars(self, symbol: str, n: int, interval: Interval) -> list:
        """
        Phase 5: 根据 interval 从正确的数据源加载
        """
        if self._mtf_buf is None:
            return []
        
        try:
            return self._mtf_buf.get(symbol, n, interval)
        except Exception as e:
            self._log(f"加载 {symbol} {interval.value} 数据失败: {e}")
            return []
```

#### 3.2 回测数据准备

```python
def backtest(self, symbols, strategy, execution_interval, ...):
    """
    Phase 5: 多周期回测数据准备
    """
    # 分析数据需求
    req = analyze_data_requirements(strategy.buy_tree, execution_interval)
    
    # 为每个符号准备所有需要的周期数据
    all_bars_dict = {}  # symbol → interval → bars
    for symbol in symbols:
        all_bars_dict[symbol] = {}
        for interval in req.intervals:
            bars = self._get_bars(symbol, n_bars, interval)
            all_bars_dict[symbol][interval] = bars
    
    # 执行回测（逐日滚动时，动态构造 MTFContext）
    ...
```

---

### 任务 4: UI 集成 - 条件编辑器

**目标**：在条件编辑器中添加"数据周期"选择下拉框。

#### 4.1 UI 改造

```python
# vnpy/strategy_condition/ui/condition_editor.py

class ConditionEditor(QDialog):
    def _init_ui(self):
        """
        添加"数据周期"行：
        
        [指标类型] ▼
        [具体指标] ▼
        [数据周期] ▼  ← 新增
        [参数1]
        [参数2]
        ...
        """
        # 周期选择
        self.interval_combo = QComboBox()
        self.interval_combo.addItem("执行周期（默认）", None)
        self.interval_combo.addItem("1分钟", Interval.MINUTE_1)
        self.interval_combo.addItem("5分钟", Interval.MINUTE_5)
        self.interval_combo.addItem("15分钟", Interval.MINUTE_15)
        self.interval_combo.addItem("30分钟", Interval.MINUTE_30)
        self.interval_combo.addItem("1小时", Interval.HOUR)
        self.interval_combo.addItem("日线", Interval.DAILY)
        self.interval_combo.addItem("周线", Interval.WEEKLY)
        self.interval_combo.addItem("月线", Interval.MONTHLY)
        
        layout.addRow("数据周期:", self.interval_combo)
    
    def _to_condition(self) -> Condition:
        """创建条件时保存 data_interval"""
        interval = self.interval_combo.currentData()
        
        return Condition(
            category=...,
            indicator=...,
            params=...,
            data_interval=interval,  # ← 保存用户选择
            label=...,
        )
```

#### 4.2 显示优化

**标签增强**：条件标签自动显示周期信息
```python
def _generate_label(self) -> str:
    """
    MA20向上  →  MA20向上 (日线)
    放量      →  放量 (5分钟)
    """
    base_label = self._get_indicator_label()
    if self.data_interval:
        interval_name = self._get_interval_name(self.data_interval)
        return f"{base_label} ({interval_name})"
    return base_label
```

**条件树可视化**：
```
[AND] 买入条件
  ├── MA20向上 (日线)    ← 显示周期
  └── 放量 (5分钟)       ← 显示周期
```

---

### 任务 5: 性能优化

#### 5.1 数据预加载

```python
class MultiTimeframeCandleBuffer:
    def preload(self, symbols: List[str], intervals: List[Interval],
                n_bars: int):
        """
        批量预加载数据，减少单次请求开销
        
        适用场景：
        - 回测开始前预加载所有股票的所有周期数据
        - 实时扫描前预加载股票池数据
        """
        for symbol in symbols:
            for interval in intervals:
                self.get(symbol, n_bars, interval)
```

#### 5.2 并行转换

```python
def _batch_resample(self, symbol_bars_pairs, from_interval, to_interval):
    """
    使用多进程并行转换周期
    
    适用场景：回测时批量转换数百只股票的数据
    """
    from concurrent.futures import ProcessPoolExecutor
    
    with ProcessPoolExecutor() as executor:
        results = executor.map(
            self._resampler.resample,
            symbol_bars_pairs,
            ...
        )
    return list(results)
```

#### 5.3 增量更新

```python
def update_incremental(self, symbol: str, new_base_bars: list):
    """
    增量更新：只转换新增的基础数据
    
    算法：
    1. 检测缓存中各周期的最后一根K线时间
    2. 过滤出新增的基础K线
    3. 只转换新增部分
    4. 合并到缓存末尾
    """
    pass
```

---

## 实施计划

### Step 1: 周期转换器（1-2天）
- [x] BarResampler 基础框架
- [ ] 分钟→小时转换
- [ ] 小时→日线转换
- [ ] 日线→周线转换
- [ ] 单元测试

### Step 2: 多周期 CandleBuffer（2-3天）
- [ ] MultiTimeframeCandleBuffer 框架
- [ ] 缓存机制实现
- [ ] 自动转换逻辑
- [ ] 集成测试

### Step 3: ScanEngine 改造（1天）
- [ ] _get_bars() 改造
- [ ] 回测数据准备改造
- [ ] 端到端测试

### Step 4: UI 集成（1-2天）
- [ ] 条件编辑器添加周期选择
- [ ] 标签显示优化
- [ ] 策略摘要显示周期信息
- [ ] 用户体验测试

### Step 5: 性能优化（1-2天）
- [ ] 预加载机制
- [ ] 并行转换
- [ ] 增量更新
- [ ] 性能基准测试

**总计**：约 6-10 个工作日

---

## 测试验证

### 单元测试

```python
# tests/test_bar_resampler.py
def test_minute_to_hour():
    """测试5分钟转1小时"""
    pass

def test_daily_to_weekly():
    """测试日线转周线"""
    pass

# tests/test_mtf_candle_buffer.py
def test_cache_hit():
    """测试缓存命中"""
    pass

def test_auto_conversion():
    """测试自动转换"""
    pass
```

### 集成测试

```python
# tests/test_mtf_phase5_integration.py
def test_real_multiperiod_backtest():
    """
    使用真实多周期数据进行回测
    
    1. 准备分钟线数据
    2. 创建多周期策略（日线+5分钟）
    3. 回测应该自动转换日线数据
    4. 验证结果正确性
    """
    pass
```

### 性能测试

```python
# tests/test_mtf_performance.py
def test_conversion_speed():
    """测试转换速度（1000只股票 × 200根K线）"""
    pass

def test_cache_efficiency():
    """测试缓存效率（命中率 > 90%）"""
    pass
```

---

## 技术难点

### 难点 1: 时间对齐

**问题**：不同周期的K线时间戳如何对齐？

**方案**：
- 统一使用周期结束时间
- 分钟线：9:35, 9:40, 9:45...
- 日线：15:00
- 周线：周五 15:00

### 难点 2: 不完整周期

**问题**：当前正在进行的小时/日/周如何处理？

**方案**：
- 回测模式：只保留完整周期
- 实时模式：保留未完成周期，但标记状态

### 难点 3: 数据稀疏性

**问题**：某些股票缺失部分周期数据怎么办？

**方案**：
- 前向填充（forward fill）
- 明确标记缺失数据
- 评估时返回 False（数据不足）

---

## 向后兼容

Phase 5 必须保持与 Phase 1-4 的完全兼容：

1. **现有单周期策略**：无需修改，继续正常工作
2. **现有API**：不破坏现有接口
3. **渐进式迁移**：用户可以逐步将策略迁移到多周期

**兼容性测试**：
```python
# 确保现有测试全部通过
python tests/test_mtf_phase4.py  # 应该继续通过
python tests/test_strategy_condition_advanced.py  # 应该继续通过
```

---

## 文档更新

Phase 5 完成后需要更新的文档：

1. **MTF_PHASE5_COMPLETE.md**：Phase 5 完成报告
2. **MULTI_TIMEFRAME_STRATEGY_GUIDE.md**：更新数据对齐说明
3. **API_REFERENCE.md**：多周期 API 参考（新建）
4. **MIGRATION_GUIDE.md**：从单周期迁移到多周期的指南（新建）

---

## 成功标准

Phase 5 成功的标志：

1. ✅ BarResampler 能正确转换各种周期
2. ✅ MultiTimeframeCandleBuffer 缓存命中率 > 90%
3. ✅ 多周期回测结果与手动计算一致
4. ✅ UI 界面支持周期选择，用户体验流畅
5. ✅ 性能测试达标（100只股票回测 < 10秒）
6. ✅ 所有现有测试继续通过（向后兼容）
7. ✅ 完整的文档和示例

---

## 风险与挑战

### 风险 1: 数据对齐复杂性

**风险**：周期转换时的时间对齐可能出现微妙的错误

**缓解**：
- 详尽的单元测试覆盖边界情况
- 与成熟库（如 pandas resample）的结果对比验证

### 风险 2: 性能瓶颈

**风险**：大量周期转换可能导致性能下降

**缓解**：
- 智能缓存策略
- 并行处理
- 性能基准测试和持续优化

### 风险 3: UI 复杂度

**风险**：UI 改造可能影响现有用户体验

**缓解**：
- 渐进式UI改进
- 保持默认行为不变（周期=None）
- 充分的用户测试

---

## 下一步行动

**立即开始**：
1. 创建 `vnpy/strategy_condition/data/` 目录
2. 实现 `BarResampler` 基础框架
3. 编写第一个转换函数（分钟→小时）
4. 编写对应的单元测试

**本周目标**：完成 Step 1（周期转换器）

准备好开始 Phase 5 了吗？