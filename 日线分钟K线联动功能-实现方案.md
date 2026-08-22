# 日线分钟K线联动功能 - 完整实现方案

## 需求概述

点击日线K线时，分钟K线自动聚焦到该日期，并显示该日期的买入/卖出信号。要求在非全屏模式和全屏模式下都能工作。

## 核心设计

### 1. 信号传递链路

```
日线K线点击 → ConditionMonitorWidget → 分钟面板更新
                    ↓
            全屏窗口（如已打开）
```

### 2. 已完成的修改

#### 2.1 `condition_monitor_widget.py`
- ✅ 添加 `daily_bar_clicked` 信号
- ✅ 实现 `_on_daily_bar_clicked()` 处理日线点击
- ✅ 实现 `_get_signals_for_date()` 查找指定日期的信号
- ✅ 实现 `_update_minute_view_for_date()` 更新分钟视图
- ✅ 在 `_connect_daily_click_handler()` 中连接日线图表点击事件

#### 2.2 `kline_view.py`（已部分修改）
- ✅ `KlineViewTab` 添加 `focus_on_date()` 方法
- ✅ `KlineViewTab` 添加 `_update_signals_display()` 方法
- ✅ `_on_fullscreen()` 传递联动上下文参数
- ✅ `_KlineFullscreenWindow` 支持 `parent_monitor` 和 `window_type` 参数
- ✅ 添加全屏窗口联动方法

### 3. 关键前提验证

需要确认日线K线图表是否已经支持点击事件：

```python
# 在 KlineChartWidget 中需要有：
class KlineChartWidget:
    bar_clicked = QtCore.Signal(object)  # 发射 datetime 对象
    
    def mouseReleaseEvent(self, event):
        # 计算点击位置对应的 bar_index
        # 发射 bar_clicked 信号
        self.bar_clicked.emit(datetime_obj)
```

## 实现步骤（剩余工作）

### Step 1: 验证日线图表点击事件

检查 `KlineChartWidget` 是否已实现 `bar_clicked` 信号。如果没有，需要添加：

```python
# 在 KlineChartWidget 类中
bar_clicked = QtCore.Signal(object)

def mouseReleaseEvent(self, event):
    if self._main_plot:
        pos = event.pos()
        mp = self._main_plot.vb.mapSceneToView(QtCore.QPointF(pos))
        x = int(round(mp.x()))
        
        if 0 <= x < len(self._datetimes):
            dt = self._datetimes[x]
            self.bar_clicked.emit(dt)
```

### Step 2: 测试非全屏模式联动

1. 启动应用，加载双周期数据
2. 点击日线K线的某一根
3. 验证：
   - 控制台输出 `[联动] 日线K线被点击`
   - 分钟K线自动滚动到该日期
   - 如果该日有信号，分钟K线显示信号标记

### Step 3: 测试全屏模式联动

1. 打开分钟K线全屏窗口
2. 在主界面点击日线K线
3. 验证：
   - 控制台输出 `[联动] 分钟全屏窗口收到日线点击`
   - 全屏窗口自动滚动到该日期
   - 信号标记正确显示

### Step 4: 边界情况处理

- 点击的日期在分钟数据范围外
- 点击的日期无分钟数据
- 点击的日期有信号，但分钟级别无对应数据
- 全屏窗口关闭时不响应点击

## 数据流示意

```
用户点击日线K线 (2026-07-15)
  ↓
日线图表 bar_clicked 信号 → datetime(2026-07-15 00:00)
  ↓
ConditionMonitorWidget._on_daily_bar_clicked()
  ↓
查找该日期的信号:
  - buy_dates 中有该日期 → 提取第一根分钟K线时间
  - sell_dates 中有该日期 → 提取最后一根分钟K线时间
  ↓
调用 KlineViewTab.focus_on_date(date(2026-07-15), signals)
  ↓
分钟K线:
  1. 找到 2026-07-15 的所有分钟K线索引 [150, 151, ..., 389]
  2. 设置 X 轴范围 [145, 394]（前后留5根）
  3. 更新信号标记：buy_indices={150}, sell_indices={389}
  ↓
全屏窗口（如已打开）:
  通过 daily_bar_clicked 信号接收相同参数
  执行相同的聚焦和信号更新逻辑
```

## 信号匹配策略

### 日期到分钟时间的映射

```python
# 在 _get_signals_for_date() 中
date_str = '2026-07-15'
is_buy_day = date_str in [d[:10] for d in buy_dates]
is_sell_day = date_str in [d[:10] for d in sell_dates]

if is_buy_day:
    # 买入信号标记在当日第一根分钟K线
    day_bars = [b for b in minute_bars if b.datetime.date() == target_date]
    signals['buy'] = [day_bars[0].datetime]

if is_sell_day:
    # 卖出信号标记在当日最后一根分钟K线
    signals['sell'] = [day_bars[-1].datetime]
```

## 调试建议

### 关键日志输出点

1. 日线点击：`[联动] 日线K线被点击: 2026-07-15`
2. 信号查找：`[联动] 找到信号: 买入=1, 卖出=1`
3. 分钟聚焦：`[联动] 聚焦到日期 2026-07-15, 索引范围: 150-389`
4. 信号更新：`[联动] 更新信号标记: 买入=1, 卖出=1`
5. 全屏联动：`[联动] 分钟全屏窗口已连接日线点击信号`

### 常见问题排查

**问题1**: 点击日线K线无反应
- 检查 `KlineChartWidget.bar_clicked` 信号是否存在
- 检查 `_connect_daily_click_handler()` 是否成功连接

**问题2**: 分钟K线不跳转
- 检查 `focus_on_date()` 是否被调用
- 检查目标日期是否在分钟数据范围内
- 检查 `_chart._datetimes` 是否正确

**问题3**: 信号标记未显示
- 检查 `_get_signals_for_date()` 返回值
- 检查 `_update_signals_display()` 是否正确映射索引
- 检查图表的 `_buy_triggers` 和 `_sell_triggers` 是否更新

**问题4**: 全屏窗口不联动
- 检查全屏窗口创建时是否传递 `parent_monitor` 和 `window_type`
- 检查 `daily_bar_clicked` 信号连接
- 检查全屏窗口的 `_on_daily_clicked_from_main()` 是否被调用

## 测试用例

### 用例1: 正常日期点击
- 输入：点击有分钟数据的日线K线
- 预期：分钟K线滚动到该日期，前后各显示5根

### 用例2: 买入信号日期
- 输入：点击有买入信号的日线K线
- 预期：分钟K线显示买入标记（绿色三角）在当日第一根

### 用例3: 卖出信号日期
- 输入：点击有卖出信号的日线K线
- 预期：分钟K线显示卖出标记（红色倒三角）在当日最后一根

### 用例4: 买卖信号同日
- 输入：点击既有买入又有卖出的日线K线
- 预期：分钟K线显示两个标记，买入在首，卖出在尾

### 用例5: 全屏模式联动
- 输入：打开分钟全屏窗口，点击日线K线
- 预期：主界面和全屏窗口同步更新

### 用例6: 无分钟数据日期
- 输入：点击非交易日或数据缺失的日期
- 预期：控制台输出提示，分钟K线不变

## 性能优化建议

1. **信号查找缓存**：首次查找后缓存日期到信号的映射
2. **索引预计算**：加载分钟数据时预先建立 datetime → index 映射
3. **批量更新**：合并信号更新和视图刷新操作
4. **防抖处理**：快速点击时只响应最后一次

## 扩展功能建议

1. **双向联动**：点击分钟K线时高亮对应日线K线
2. **日期导航**：提供上一交易日/下一交易日按钮
3. **信号详情弹窗**：点击信号标记时显示触发条件详情
4. **多日期联动**：支持框选多根日线K线，分钟视图显示整个区间

## 完成标准

✅ 非全屏模式：点击日线→分钟滚动+信号显示  
✅ 全屏模式：点击日线→全屏窗口滚动+信号显示  
✅ 边界情况正确处理  
✅ 调试日志完整清晰  
✅ 用户体验流畅无卡顿  

---

**实现状态**: 核心代码已就位，需验证 KlineChartWidget 点击事件并进行集成测试

**预计测试时间**: 30分钟

**风险评估**: 低（功能独立，不影响现有逻辑）