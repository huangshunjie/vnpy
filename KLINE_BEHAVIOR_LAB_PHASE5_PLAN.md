# K-Line Market Behavior Lab - Phase 5 开发计划

## Phase 5: UI Implementation 用户界面实现

**状态：** 开发中  
**预计时间：** 4-5天

---

## 开发策略

由于UI代码量较大，采用**分模块渐进式开发**策略：

### 阶段划分

**5.1 重构BehaviorResearchTab主框架** (1天)
- 集成FeatureEngine、ConditionBuilder、SamplingEngine
- 实现流程导航
- 配置区域和结果区域分离

**5.2 实现核心面板** (2天)
- 研究范围配置面板
- 条件构建面板
- 事件搜索与采样面板

**5.3 实现分析面板** (1天)
- 统计报告展示面板
- 稳定性分析面板
- 特征重要性面板

**5.4 实现辅助对话框** (1天)
- 特征浏览器对话框
- 条件模板选择对话框
- 结果导出对话框

---

## UI架构设计

### 主界面布局

```
┌─────────────────────────────────────────────────────┐
│  K-Line Market Behavior Lab                         │
├─────────────────────────────────────────────────────┤
│  流程导航: [1.配置] → [2.条件] → [3.执行] → [4.结果] │
├──────────────────┬──────────────────────────────────┤
│                  │                                  │
│  左侧配置区      │      右侧结果展示区              │
│  (300px固定)     │      (自适应)                    │
│                  │                                  │
│  ┌──────────┐   │  ┌─────────────────────────┐    │
│  │研究配置  │   │  │ 事件列表 (Table)         │    │
│  │数据范围  │   │  │ - 标的/时间/收益         │    │
│  │条件构建  │   │  │ - 可排序/筛选            │    │
│  │采样规则  │   │  └─────────────────────────┘    │
│  │          │   │                                  │
│  │[开始研究]│   │  ┌─────────────────────────┐    │
│  └──────────┘   │  │ 统计图表 (Charts)        │    │
│                  │  │ - 收益分布直方图         │    │
│                  │  │ - MFE/MAE散点图          │    │
│                  │  │ - 年度收益对比           │    │
│                  │  └─────────────────────────┘    │
│                  │                                  │
└──────────────────┴──────────────────────────────────┘
│  状态栏: 就绪 | 事件数: 0 | 平均收益: --            │
└─────────────────────────────────────────────────────┘
```

---

## 核心组件清单

### 1. BehaviorResearchTab (主Tab)
**文件：** `ui/behavior_tab_enhanced.py`

**职责：**
- 总体布局管理
- 流程控制
- 子组件协调

**关键方法：**
```python
class BehaviorResearchTab(QWidget):
    def __init__(self, engine):
        # 初始化所有引擎
        self.feature_engine = FeatureEngine()
        self.condition_builder = ConditionBuilder()
        self.sampling_engine = SamplingEngine()
        self.event_searcher = EventSearcher()
        self.forward_analyzer = ForwardReturnAnalyzer()
        
    def _on_run_research(self):
        """执行完整研究流程"""
        # 1. 验证配置
        # 2. 计算特征
        # 3. 搜索事件
        # 4. 采样
        # 5. 分析
        # 6. 展示结果
```

---

### 2. ScopeConfigPanel (研究范围配置面板)
**组件：** QGroupBox

**包含内容：**
- 数据集选择 (QComboBox)
- 股票池选择 (QComboBox + 自定义按钮)
- 时间范围 (QDateEdit start/end)
- K线周期 (QComboBox: 日/周/月)
- 复权方式 (QComboBox: 前复权/后复权/不复权)

**布局：**
```python
┌─ 研究范围配置 ────────────┐
│ 数据集:    [沪深300 ▼]    │
│ 股票池:    [全部 ▼] [...]  │
│ 开始日期:  [2020-01-01]   │
│ 结束日期:  [2024-12-31]   │
│ K线周期:   [日线 ▼]       │
│ 复权方式:  [前复权 ▼]     │
└───────────────────────────┘
```

---

### 3. ConditionBuilderPanel (条件构建面板)
**组件：** QGroupBox

**包含内容：**
- 条件模板选择 (QComboBox + 预览)
- 条件表达式编辑器 (QTextEdit with syntax highlight)
- 特征浏览按钮 (打开特征浏览器对话框)
- 条件验证按钮 (实时验证)
- 依赖特征显示 (QLabel，自动解析)

**布局：**
```python
┌─ 研究条件 ────────────────────┐
│ 模板: [大阴线底部反转 ▼] [应用]│
│                                │
│ 条件表达式:                    │
│ ┌────────────────────────┐    │
│ │(return_1 < -0.03) &     │    │
│ │(lower_shadow_ratio>0.4)&│    │
│ │(volume_ratio > 1.5)     │    │
│ └────────────────────────┘    │
│                                │
│ [浏览特征] [验证条件]          │
│                                │
│ 依赖特征: return_1,            │
│          lower_shadow_ratio,   │
│          volume_ratio          │
└────────────────────────────────┘
```

---

### 4. SamplingConfigPanel (采样配置面板)
**组件：** QGroupBox

**包含内容：**
- 采样规则 (QComboBox: ALL/FIRST/COOLDOWN/NON_OVERLAP)
- 冷却期天数 (QSpinBox, 当选择COOLDOWN时启用)
- 持有期天数 (QSpinBox, 当选择NON_OVERLAP时启用)
- 每标的最大事件数 (QSpinBox, 0=不限制)
- 未来周期配置 (QLineEdit: "1,3,5,10,20")
- 异常值过滤 (QCheckBox + QDoubleSpinBox: 3σ)

**布局：**
```python
┌─ 采样规则 ────────────────┐
│ 采样规则: [冷却期 ▼]      │
│ 冷却期:   [5] 天          │
│ 持有期:   [5] 天          │
│ 每标的上限: [50] 个事件   │
│                           │
│ 未来周期: [1,3,5,10,20]   │
│                           │
│ ☑ 移除异常值 (±[3.0]σ)   │
└───────────────────────────┘
```

---

### 5. ExecutionPanel (执行控制面板)
**组件：** QWidget

**包含内容：**
- 开始研究按钮 (大号，醒目)
- 进度条 (QProgressBar)
- 状态显示 (QLabel)
- 停止按钮 (执行时显示)

**布局：**
```python
┌───────────────────────────┐
│  [🚀 开始研究]            │
│                           │
│  进度: ████████░░  80%    │
│                           │
│  状态: 正在搜索事件...    │
│  已处理: 2500/3000 标的   │
└───────────────────────────┘
```

---

### 6. EventResultsPanel (事件结果面板)
**组件：** QWidget with QTableWidget + Charts

**功能：**
- 事件列表表格 (可排序、筛选、导出)
- 快速统计卡片 (事件数、标的数、平均收益、胜率)
- 操作按钮 (导出CSV、生成报告、查看详情)

**表格列：**
```
事件ID | 标的 | 日期 | 入场价 | 1日收益 | 3日收益 | 5日收益 | 10日收益 | 20日收益 | MFE | MAE | 标记
```

---

### 7. StatisticsPanel (统计分析面板)
**组件：** QWidget with QTabWidget

**子Tab：**

**Tab 1: 收益分布**
- 各持有期收益统计表
- 收益分布直方图
- 累积收益曲线

**Tab 2: 风险指标**
- VaR/CVaR
- MFE/MAE散点图
- 最大回撤

**Tab 3: 分组分析**
- 年度收益对比柱状图
- 行业收益对比
- 市值分组收益

---

### 8. 辅助对话框

#### FeatureBrowserDialog (特征浏览器)
```python
┌─ 特征浏览器 ────────────────────────┐
│ 搜索: [_______________] [搜索]      │
│                                     │
│ 分类: [全部 ▼] [收益类 ▼] ...      │
│                                     │
│ ┌─────────────────────────────┐   │
│ │ return_1  - 1日收益率        │   │
│ │   描述: 当日收盘价相对前...   │   │
│ │   公式: (close-close.shift   │   │
│ │   回看: 1日                   │   │
│ │   [插入到条件]                │   │
│ ├─────────────────────────────┤   │
│ │ lower_shadow_ratio - 下影线   │   │
│ │   ...                         │   │
│ └─────────────────────────────┘   │
│                                     │
│ 共80个特征 | 已选择: 3个            │
│                                     │
│          [关闭]                     │
└─────────────────────────────────────┘
```

#### TemplateSelectDialog (模板选择对话框)
```python
┌─ 条件模板 ──────────────────────────┐
│                                     │
│ ┌─ 大阴线底部反转 ─────────────┐   │
│ │ 分类: 反转                    │   │
│ │ 条件: (return_1 < -0.03) &   │   │
│ │       (lower_shadow_ratio...) │   │
│ │ 描述: 大跌+长下影线+放量      │   │
│ │                               │   │
│ │ [应用]                        │   │
│ └───────────────────────────────┘   │
│                                     │
│ ┌─ 突破新高 ───────────────────┐   │
│ │ ...                           │   │
│ └───────────────────────────────┘   │
│                                     │
│ [自定义]  [关闭]                    │
└─────────────────────────────────────┘
```

---

## 核心实现要点

### 1. 异步执行
```python
from PySide6.QtCore import QThread, Signal

class ResearchWorker(QThread):
    """后台研究线程"""
    progress = Signal(int, str)  # 进度，状态
    finished = Signal(object)    # 结果
    error = Signal(str)          # 错误
    
    def run(self):
        try:
            # 1. 加载数据
            self.progress.emit(10, "加载数据...")
            
            # 2. 计算特征
            self.progress.emit(30, "计算特征...")
            
            # 3. 搜索事件
            self.progress.emit(50, "搜索事件...")
            
            # 4. 采样和分析
            self.progress.emit(80, "分析收益...")
            
            # 5. 完成
            self.progress.emit(100, "完成")
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))
```

### 2. 图表集成
使用 `matplotlib` 嵌入PySide6：

```python
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

class ReturnsDistributionChart(FigureCanvasQTAgg):
    """收益分布直方图"""
    
    def __init__(self, parent=None):
        fig = Figure(figsize=(8, 4))
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        
    def plot(self, returns):
        self.axes.clear()
        self.axes.hist(returns, bins=50, alpha=0.7)
        self.axes.set_xlabel('收益率')
        self.axes.set_ylabel('频数')
        self.axes.set_title('未来5日收益分布')
        self.draw()
```

### 3. 实时验证
```python
def _on_condition_changed(self):
    """条件改变时实时验证"""
    condition = self._condition_edit.toPlainText()
    
    valid, error, features = self.condition_builder.validate_expression(condition)
    
    if valid:
        self._validation_label.setText(f"✓ 有效 | 依赖特征: {', '.join(features)}")
        self._validation_label.setStyleSheet("color: green")
    else:
        self._validation_label.setText(f"✗ {error}")
        self._validation_label.setStyleSheet("color: red")
```

---

## 开发优先级

### 第一优先级（核心功能）
1. ✅ 研究配置面板
2. ✅ 条件构建面板
3. ✅ 执行控制
4. ✅ 事件结果展示

### 第二优先级（增强功能）
5. ⏳ 统计图表
6. ⏳ 分组分析
7. ⏳ 特征浏览器

### 第三优先级（辅助功能）
8. ⏳ 模板管理
9. ⏳ 结果导出
10. ⏳ 研究历史

---

## 下一步行动

**建议：分步实现，每完成一个组件就测试验证。**

### Step 1: 重构BehaviorResearchTab主框架
- 创建 `behavior_tab_v2.py`
- 集成所有核心引擎
- 实现基本布局

### Step 2: 实现配置面板
- ScopeConfigPanel
- ConditionBuilderPanel
- SamplingConfigPanel

### Step 3: 实现执行流程
- ResearchWorker线程
- 进度反馈
- 错误处理

### Step 4: 实现结果展示
- EventResultsPanel
- StatisticsPanel
- 图表组件

---

**Phase 5预计完成时间：4-5天**

**当前建议：先实现Step 1（主框架重构），再逐步添加功能模块。**

是否开始实现Step 1？
