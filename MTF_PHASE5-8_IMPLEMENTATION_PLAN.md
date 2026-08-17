# vnpy 多周期架构改造 Phase 5-8 实施计划

**生成时间：** 2026年8月16日  
**目的：** 完成 Phase 4-9 中未完成的关键工作

---

## 📋 优先级排序

根据 `MTF_PHASE4-9_STATUS_REPORT.md` 分析，未完成工作按优先级排序：

### 🔴 P0 - 高优先级（核心功能）

1. **Phase 5 数据对齐 + As-of Time 机制**
   - 影响：分钟级多周期策略准确性
   - 工作量：6-8小时
   - 阻塞：Phase 6, Phase 8

2. **Phase 8 端到端测试**
   - 影响：生产可靠性
   - 工作量：4-6小时
   - 阻塞：生产部署

### 🟡 P1 - 中优先级（增强功能）

3. **Phase 6 Monitor Engine 改造**
   - 影响：实时监控功能
   - 工作量：3-4小时
   - 替代方案：使用定时扫描

4. **Phase 8 性能测试**
   - 影响：大规模使用性能
   - 工作量：2-3小时

---

## Phase 5: 数据对齐和 As-of Time 机制

### 当前问题

```python
# vnpy/strategy_condition/engine/scan_engine.py:362-364
# 简化实现：所有周期都使用同一份数据（实际应该根据周期不同加载不同数据）
# TODO: 实际生产环境需要为不同周期加载相应的数据
ctx.set_bars(interval, bars_so_far)
```

### 解决方案

#### Step 1: 扩展 MTFCandleBuffer 支持多数据源

```python
# vnpy/strategy_condition/data/mtf_candle_buffer.py

class MultiTimeframeCandleBuffer:
    """
    多周期K线缓存（已完成）
    
    新增：支持为不同周期设置不同的基础数据源
    """
    
    def set_base_bars_multi(self, symbol: str, bars_dict: Dict[Interval, List[BarData]]):
        """
        为一个股票设置多个周期的基础数据
        
        Args:
            symbol: 股票代码
            bars_dict: {Interval.MINUTE_5: [...], Interval.DAILY: [...]}
        """
        # 存储每个周期的独立数据源
        for interval, bars in bars_dict.items():
            key = (symbol, interval)
            self._base_cache[key] = bars
```

#### Step 2: 实现 As-of Time 对齐

```python
# vnpy/strategy_condition/data/mtf_candle_buffer.py

def get_bars_as_of(
    self,
    symbol: str,
    n: int,
    interval: Interval,
    as_of_time: datetime
) -> List[BarData]:
    """
    获取截至指定时间点的K线数据
    
    关键：防止未来函数
    - 只返回 bar.datetime <= as_of_time 的K线
    - 确保回测和实盘时间语义一致
    
    Args:
        symbol: 股票代码
        n: K线数量
        interval: 周期
        as_of_time: 评估时间点（As-of Time）
    
    Returns:
        符合时间约束的K线列表
    """
    all_bars = self.get(symbol, n * 2, interval)  # 多取一些以便过滤
    if not all_bars:
        return []
    
    # 过滤：只保留 <= as_of_time 的K线
    valid_bars = [b for b in all_bars if b.datetime <= as_of_time]
    
    # 返回最后 n 根
    return valid_bars[-n:] if len(valid_bars) >= n else valid_bars
```

#### Step 3: 修改 ScanEngine._backtest_symbol

```python
# vnpy/strategy_condition/engine/scan_engine.py:358-365

# 当前代码（简化实现）：
for interval in req.intervals:
    ctx.set_bars(interval, bars_so_far)  # 所有周期用同一数据

# 改为：
for interval in req.intervals:
    # 从 MTFCandleBuffer 获取该周期的正确数据
    interval_bars = self._get_bars_as_of(
        symbol=symbol,
        n=len(bars_so_far),
        interval=interval,
        as_of_time=bars_so_far[-1].datetime
    )
    ctx.set_bars(interval, interval_bars)
```

#### Step 4: 新增 _get_bars_as_of 方法

```python
# vnpy/strategy_condition/engine/scan_engine.py

def _get_bars_as_of(
    self,
    symbol: str,
    n: int,
    interval: Interval,
    as_of_time: datetime
) -> list:
    """
    获取截至指定时间点的K线（防止未来函数）
    
    Phase 5: As-of Time 机制的核心实现
    
    优先级：
    1. MTFCandleBuffer.get_bars_as_of()（支持时间过滤）
    2. 传统 CandleBuffer（向后兼容，但无时间过滤）
    
    Args:
        symbol: 股票代码
        n: K线数量
        interval: 周期
        as_of_time: 评估时间点
    
    Returns:
        符合时间约束的K线列表
    """
    if self._mtf_buffer is not None:
        # Phase 5: 使用支持 As-of Time 的方法
        return self._mtf_buffer.get_bars_as_of(
            symbol, n, interval, as_of_time
        )
    
    # 回退：传统方法（无时间过滤）
    return self._get_bars(symbol, n, interval)
```

### 测试验证

```python
# tests/test_mtf_phase5_asof_time.py

def test_asof_time_no_future_leak():
    """测试 As-of Time 机制防止未来函数"""
    
    # 构造测试数据：100根日线
    bars = create_test_bars(100, Interval.DAILY)
    
    # 在第50根K线时评估
    as_of_time = bars[49].datetime
    
    # 获取截至第50根的数据
    result = buffer.get_bars_as_of(
        symbol="TEST",
        n=20,
        interval=Interval.DAILY,
        as_of_time=as_of_time
    )
    
    # 验证：不包含未来数据
    assert len(result) == 20
    assert all(b.datetime <= as_of_time for b in result)
    assert result[-1].datetime == bars[49].datetime
```

---

## Phase 6: Monitor Engine 多周期集成

### 当前问题

MonitorEngine 未集成 MultiTimeframeContext，无法监控多周期条件。

### 解决方案

#### Step 1: 修改 generate_snapshots

```python
# vnpy/strategy_condition/monitor/condition_monitor_engine.py:80-152

def generate_snapshots(
    self,
    symbol: str,
    bars: list,
    strategy: Strategy,
    warmup: int = 60,
    buy_dates: Optional[List[str]] = None,
    sell_dates: Optional[List[str]] = None,
    inject_buy_signals: bool = True,
    execution_interval: Interval = Interval.DAILY,  # 新增参数
) -> List[ConditionSnapshot]:
    """
    Phase 6: 支持多周期策略监控
    
    新增：
    - execution_interval: 策略执行周期
    - 分析数据需求
    - 构造 MultiTimeframeContext
    """
    # 分析策略数据需求
    from ..core.mtf_context import analyze_data_requirements
    req = analyze_data_requirements(strategy.buy_tree, execution_interval)
    is_multi_timeframe = len(req.intervals) > 1
    
    if is_multi_timeframe:
        self._log(f"[MonitorEngine] {symbol} 多周期策略监控")
    
    # ... 后续逻辑
```

#### Step 2: 修改 _evaluate_bar

```python
# vnpy/strategy_condition/monitor/condition_monitor_engine.py:580-688

def _evaluate_bar(
    self,
    symbol: str,
    bars_slice: list,
    bar_index: int,
    strategy: Strategy,
    pos_ctx: Optional[Dict[str, Any]] = None,
    mtf_context: Optional[MultiTimeframeContext] = None,  # 新增
) -> ConditionSnapshot:
    """
    Phase 6: 使用 MultiTimeframeContext 评估
    """
    # 买入条件评估
    buy_recorder: Dict[str, ConditionDetail] = {}
    
    if mtf_context:
        # 多周期评估
        buy_eval_fn = self._make_recording_mtf_eval_fn(
            buy_recorder, bars_slice, mtf_context
        )
    else:
        # 单周期评估（向后兼容）
        buy_eval_fn = self._make_recording_eval_fn(
            buy_recorder, bars_slice
        )
    
    buy_passed, buy_score = strategy.buy_tree.evaluate(
        symbol, bars_slice, buy_eval_fn
    )
    # ... 其余逻辑不变
```

#### Step 3: 新增 _make_recording_mtf_eval_fn

```python
# vnpy/strategy_condition/monitor/condition_monitor_engine.py

def _make_recording_mtf_eval_fn(
    self,
    recorder: Dict[str, ConditionDetail],
    bars_slice: list,
    mtf_context: MultiTimeframeContext,
) -> Callable[[Condition, str, list], Tuple[bool, float]]:
    """
    Phase 6: 创建多周期监控评估函数
    """
    original_eval = self._ce.eval_condition
    
    def recording_mtf_eval(cond: Condition, symbol: str, bars: list) -> Tuple[bool, float]:
        # 使用 MultiTimeframeContext 评估
        passed, score = original_eval(
            cond, symbol, bars, _mtf_context=mtf_context
        )
        
        # 记录详情（包含周期信息）
        current_value = self._extract_current_value(cond, bars_slice)
        threshold_desc = self._format_threshold(cond)
        
        detail = ConditionDetail(
            condition_name=cond.display_name(),
            indicator=cond.indicator.value,
            passed=passed,
            score=score,
            current_value=current_value,
            threshold_desc=threshold_desc,
            params=dict(cond.params),
            data_interval=cond.data_interval.value if cond.data_interval else None,  # 新增
        )
        recorder[cond.display_name()] = detail
        return passed, score
    
    return recording_mtf_eval
```

### 测试验证

```python
# tests/test_mtf_phase6_monitor.py

def test_monitor_multi_timeframe():
    """测试监控引擎多周期支持"""
    
    # 创建多周期策略
    strategy = create_multi_timeframe_strategy()
    
    # 生成快照
    snapshots = monitor_engine.generate_snapshots(
        symbol="TEST",
        bars=test_bars,
        strategy=strategy,
        execution_interval=Interval.MINUTE_5
    )
    
    # 验证：条件详情包含周期信息
    assert len(snapshots) > 0
    for snap in snapshots:
        for detail in snap.buy_details:
            if detail.data_interval:
                assert detail.data_interval in ["5m", "d"]
```

---

## Phase 8: 端到端测试和性能测试

### 端到端测试

```python
# tests/test_mtf_e2e_complete.py

def test_complete_multi_timeframe_workflow():
    """完整多周期工作流测试"""
    
    # 1. 创建多周期策略（日线趋势 + 5分钟入场）
    daily_ma = Condition(
        ConditionCategory.TREND,
        ConditionIndicator.MA_SLOPE,
        {"ma_period": 20, "min_slope": 0.0},
        data_interval=Interval.DAILY,
    )
    
    minute_volume = Condition(
        ConditionCategory.VOLUME,
        ConditionIndicator.VOLUME_RATIO,
        {"period": 20, "min_ratio": 1.5},
        data_interval=Interval.MINUTE_5,
    )
    
    strategy = create_strategy(daily_ma, minute_volume)
    
    # 2. 准备多周期数据
    daily_bars = load_daily_bars("TEST", 200)
    minute_bars = load_minute_bars("TEST", 10000)
    
    # 3. 使用 MTFCandleBuffer
    mtf_buffer = MultiTimeframeCandleBuffer()
    mtf_buffer.set_base_bars("TEST", minute_bars, Interval.MINUTE_5)
    mtf_buffer.set_base_bars("TEST", daily_bars, Interval.DAILY)
    
    # 4. ScanEngine 扫描
    scan_engine.set_mtf_buffer(mtf_buffer)
    batch = scan_engine.scan(
        symbols=["TEST"],
        strategy=strategy,
        execution_interval=Interval.MINUTE_5
    )
    
    # 5. 验证结果
    assert batch.count > 0
    for signal in batch.signals:
        assert signal.score > 0
    
    # 6. 回测验证
    all_bars_dict = {"TEST": minute_bars}
    backtest_batch = scan_engine.backtest(
        symbols=["TEST"],
        strategy=strategy,
        all_bars_dict=all_bars_dict,
        execution_interval=Interval.MINUTE_5
    )
    
    assert backtest_batch.count > 0
```

### 性能测试

```python
# tests/test_mtf_performance.py

def test_large_scale_multi_timeframe_backtest():
    """大规模多周期回测性能测试"""
    
    import time
    
    # 100只股票 × 500根日线
    symbols = [f"60{i:04d}.SH" for i in range(100)]
    bars_dict = {sym: create_test_bars(500) for sym in symbols}
    
    strategy = create_multi_timeframe_strategy()
    
    # 测试回测性能
    start = time.perf_counter()
    batch = scan_engine.backtest(
        symbols=symbols,
        strategy=strategy,
        all_bars_dict=bars_dict,
        execution_interval=Interval.DAILY
    )
    elapsed = time.perf_counter() - start
    
    # 性能基准：100股 × 500根 应在 30秒内完成
    assert elapsed < 30, f"性能不达标：{elapsed:.2f}s"
    
    # 缓存命中率统计
    if mtf_buffer:
        stats = mtf_buffer.get_cache_stats()
        assert stats['hit_rate'] > 0.8, "缓存命中率过低"
```

### 12场景测试矩阵

```python
# tests/test_mtf_scenarios.py

SCENARIOS = [
    # (执行周期, 条件周期列表, 预期行为)
    ("DAILY", ["DAILY"], "单周期日线"),
    ("DAILY", ["DAILY", "WEEKLY"], "日线执行+周线过滤"),
    ("MINUTE_5", ["MINUTE_5"], "单周期5分钟"),
    ("MINUTE_5", ["MINUTE_5", "DAILY"], "分钟执行+日线过滤"),
    ("MINUTE_5", ["MINUTE_5", "HOUR", "DAILY"], "三周期组合"),
    # ... 继续添加到12个场景
]

@pytest.mark.parametrize("exec_interval,cond_intervals,desc", SCENARIOS)
def test_scenario(exec_interval, cond_intervals, desc):
    """场景测试"""
    strategy = create_scenario_strategy(exec_interval, cond_intervals)
    result = run_test(strategy, exec_interval)
    assert result.success, f"{desc} 失败"
```

---

## 实施步骤建议

### Week 1: Phase 5 核心

**Day 1-2: 数据对齐**
1. 扩展 MTFCandleBuffer.set_base_bars_multi()
2. 实现 get_bars_as_of()
3. 单元测试验证

**Day 3-4: As-of Time 机制**
1. 修改 ScanEngine._backtest_symbol()
2. 新增 _get_bars_as_of()
3. 防止未来函数测试

**Day 5: 集成测试**
1. 端到端测试
2. 修复发现的问题

### Week 2: Phase 6 + Phase 8

**Day 1-2: Monitor Engine**
1. 修改 generate_snapshots()
2. 新增 _make_recording_mtf_eval_fn()
3. 单元测试

**Day 3-4: 测试补全**
1. 12场景测试矩阵
2. 性能基准测试
3. 边界情况测试

**Day 5: 文档和验收**
1. 更新完成报告
2. 用户文档补充
3. 最终验收

---

## 成功标准

### Phase 5
- [ ] MTFCandleBuffer 支持多数据源
- [ ] get_bars_as_of() 正确过滤时间
- [ ] 回测无未来函数泄露
- [ ] 分钟级多周期策略准确

### Phase 6
- [ ] MonitorEngine 支持多周期
- [ ] 条件详情显示周期信息
- [ ] 监控波形正确

### Phase 8
- [ ] 端到端测试通过
- [ ] 12场景矩阵通过
- [ ] 性能达标（100股 × 500根 < 30秒）
- [ ] 缓存命中率 > 80%

---

## 风险和缓解

### 风险1: 破坏现有功能
- **缓解**: 保持向后兼容，所有修改通过参数控制
- **验证**: 运行现有测试套件确保通过

### 风险2: 性能下降
- **缓解**: 使用缓存，批量加载
- **验证**: 性能基准测试

### 风险3: 时间不足
- **缓解**: 优先实施 P0 项目，P1 项目可后续迭代
- **fallback**: Phase 5 完成即可满足核心需求

---

## 总结

本计划聚焦于完成 Phase 5-8 的关键未完成工作，优先级明确：
1. **Phase 5 数据对齐**（P0）- 保证准确性
2. **Phase 8 端到端测试**（P0）- 保证可靠性
3. **Phase 6 Monitor Engine**（P1）- 增强监控
4. **Phase 8 性能测试**（P1）- 优化性能

预计总工作量：**15-20小时**（2-3周兼职）

完成后，多周期架构改造将达到 **90%+ 完成度**，可全面用于生产环境。