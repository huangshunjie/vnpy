# 量化研究平台使用教程 📚

## 🚀 快速开始

### 1. 启动平台

**方法一：通过 VeighNa Trader 启动**

```python
# 在你的启动脚本中
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy.quant_research import QuantResearchApp

# 创建应用
app = create_qapp()
event_engine = EventEngine()
main_engine = MainEngine(event_engine)

# 添加量化研究平台应用
main_engine.add_app(QuantResearchApp)

# 创建主窗口
main_window = MainWindow(main_engine, event_engine)
main_window.showMaximized()

app.exec()
```

**方法二：直接启动研究平台**

```python
# research_platform_demo.py
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.quant_research.ui.widget import ResearchPlatformWidget
from PySide6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
event_engine = EventEngine()
main_engine = MainEngine(event_engine)

# 创建研究平台窗口
research_widget = ResearchPlatformWidget(main_engine, event_engine)
research_widget.show()

sys.exit(app.exec())
```

---

## 📖 完整使用示例

### 场景：从零开始做一个量化策略研究

假设我们要研究一个**双均线策略**，下面是完整的工作流程：

---

## 第一步：创建实验 🔬

1. **打开"实验 (Experiments)"标签页**
2. **点击"新建实验"按钮**
3. **填写实验信息：**
   ```
   名称: 双均线策略研究
   描述: 研究快慢均线交叉的盈利能力
   标签: 均线, 趋势跟踪, A股
   参数:
     - fast_period: 5
     - slow_period: 20
   ```
4. **点击"确定"创建**

**效果：**
- 系统自动生成实验ID（如 `EXP-20260805-001`）
- 实验状态为 `DRAFT（草稿）`
- 在左侧资源管理器中可以看到新建的实验

---

## 第二步：准备数据集 🗄

1. **切换到"数据集 (Datasets)"标签页**
2. **点击"注册数据集"按钮**
3. **填写数据集信息：**
   ```
   名称: 沪深300日线数据
   版本: v1.0
   来源: Wind
   标的: 沪深300成分股
   时间范围: 2020-01-01 到 2024-12-31
   字段: open, high, low, close, volume
   行数: 365000
   大小: 45.6 MB
   ```
4. **点击"确定"注册**

**后续操作：**
- **创建快照**：点击"快照"按钮保存数据版本
- **数据质量评估**：设置质量分数（如 0.95）
- **查看血缘关系**：在"血缘"标签查看数据依赖

---

## 第三步：创建技术指标（特征） 🧩

### 特征1：快速移动平均线

1. **切换到"特征 (Features)"标签页**
2. **点击"新建特征"按钮**
3. **填写：**
   ```
   名称: MA5
   版本: v1.0
   类别: momentum
   公式: talib.MA(close, timeperiod=5)
   描述: 5日移动平均线
   依赖数据集: DS-20260805-001
   ```

### 特征2：慢速移动平均线

```
名称: MA20
版本: v1.0
类别: momentum
公式: talib.MA(close, timeperiod=20)
描述: 20日移动平均线
```

### 特征3：交叉信号

```
名称: MA_CROSS_SIGNAL
版本: v1.0
类别: technical
公式: np.where(MA5 > MA20, 1, -1)
描述: 均线交叉信号，1=金叉，-1=死叉
依赖特征: FT-20260805-001, FT-20260805-002
```

**评估特征有效性：**
- 选择特征 → 点击"IC分析"
- 输入IC值、RankIC、IR等指标
- 查看IC历史趋势

---

## 第四步：构建交易策略 📈

1. **切换到"策略 (Strategies)"标签页**
2. **点击"新建策略"按钮**
3. **填写策略信息：**
   ```
   名称: 双均线趋势策略
   版本: v1.0
   类型: trend_following
   代码路径: strategies/ma_cross_strategy.py
   股票池: 沪深300
   参数:
     - fast_period: 5
     - slow_period: 20
     - stop_loss: 0.05
   关联特征: FT-20260805-001, FT-20260805-002, FT-20260805-003
   关联数据集: DS-20260805-001
   描述: 当MA5上穿MA20时买入，下穿时卖出
   ```

**策略代码示例：**

```python
# strategies/ma_cross_strategy.py
from vnpy.trader.constant import Direction, Offset
from vnpy.trader.object import TickData, BarData
import talib

class MACrossStrategy:
    def __init__(self):
        self.fast_period = 5
        self.slow_period = 20
        self.ma_fast = []
        self.ma_slow = []
    
    def on_bar(self, bar: BarData):
        # 计算均线
        self.ma_fast = talib.MA(self.close_array, self.fast_period)
        self.ma_slow = talib.MA(self.close_array, self.slow_period)
        
        # 交易信号
        if self.ma_fast[-1] > self.ma_slow[-1] and self.ma_fast[-2] <= self.ma_slow[-2]:
            # 金叉：买入
            self.buy(bar.close_price, 1)
        elif self.ma_fast[-1] < self.ma_slow[-1] and self.ma_fast[-2] >= self.ma_slow[-2]:
            # 死叉：卖出
            self.sell(bar.close_price, 1)
```

---

## 第五步：回测验证 ⏮

1. **切换到"回测 (Backtests)"标签页**
2. **点击"提交回测"按钮**
3. **配置回测参数：**
   ```
   名称: 双均线策略_首次回测
   关联策略: ST-20260805-001
   回测区间: 2020-01-01 至 2023-12-31
   初始资金: 1,000,000
   手续费率: 0.0003
   滑点: 0
   股票池: 沪深300
   ```
4. **点击"提交"开始回测**

**查看回测结果：**
- 回测完成后，状态变为 `COMPLETED`
- 双击回测记录查看详细结果
- 查看指标：
  ```
  年化收益率: 15.8%
  最大回撤: -12.3%
  夏普比率: 1.45
  盈亏比: 2.1
  胜率: 58%
  ```

**查看权益曲线：**
- 在详情面板查看逐日权益曲线
- 分析回撤区间和盈利区间

**对比回测：**
- 选择多个回测记录
- 点击"对比"按钮
- 查看并排对比的绩效指标

---

## 第六步：参数优化（可选）⚙

### 使用Pipeline自动化优化

1. **切换到"流水线 (Pipelines)"标签页**
2. **点击"新建流水线"**
3. **配置流水线：**
   ```
   名称: 双均线参数优化
   描述: 优化快慢均线周期参数
   调度: 手动执行
   关联策略: ST-20260805-001
   ```

4. **添加执行步骤：**

   **步骤1：参数网格生成**
   ```
   名称: 生成参数组合
   类型: parameter_grid
   参数:
     fast_period: [3, 5, 7, 10]
     slow_period: [15, 20, 30, 40]
   ```

   **步骤2：批量回测**
   ```
   名称: 批量回测
   类型: batch_backtest
   依赖: 步骤1
   ```

   **步骤3：结果汇总**
   ```
   名称: 汇总最优参数
   类型: summarize
   依赖: 步骤2
   ```

5. **运行流水线**
   - 点击"运行"按钮
   - 监控执行进度
   - 查看执行日志

---

## 第七步：生成研究报告 📄

1. **切换到"报告 (Reports)"标签页**
2. **点击"新建报告"**
3. **填写报告信息：**
   ```
   标题: 双均线策略研究报告
   类型: research
   作者: 张三
   关联实验: EXP-20260805-001
   关联策略: ST-20260805-001
   关联回测: BT-20260805-001, BT-20260805-002
   ```

4. **添加报告章节：**

   **第1节：研究背景**
   ```markdown
   ## 研究背景
   本研究旨在验证双均线交叉策略在A股市场的有效性。
   选择沪深300成分股作为研究标的，回测周期为2020-2024年。
   ```

   **第2节：数据说明**
   ```markdown
   ## 数据说明
   - 数据来源: Wind
   - 时间范围: 2020-01-01 至 2024-12-31
   - 数据频率: 日线
   - 股票数量: 300只
   ```

   **第3节：策略逻辑**
   ```markdown
   ## 策略逻辑
   当5日均线上穿20日均线时买入，下穿时卖出。
   止损设置为5%。
   ```

   **第4节：回测结果**
   ```markdown
   ## 回测结果
   | 指标 | 数值 |
   |------|------|
   | 年化收益 | 15.8% |
   | 最大回撤 | -12.3% |
   | 夏普比率 | 1.45 |
   | 胜率 | 58% |
   ```

5. **发布报告**
   - 勾选所有章节
   - 点击"发布"按钮
   - 设置输出路径（可导出PDF）

---

## 第八步：模型训练（可选）🤖

如果要用机器学习增强策略：

1. **切换到"模型 (Models)"标签页**
2. **点击"新建模型"**
3. **配置模型：**
   ```
   名称: MA_XGBoost_Predictor
   类型: gradient_boosting
   框架: XGBoost
   版本: v1.0
   关联特征: FT-20260805-001, FT-20260805-002, ...
   关联数据集: DS-20260805-001
   超参数:
     - n_estimators: 100
     - max_depth: 6
     - learning_rate: 0.1
   ```

4. **添加训练记录**
   - 点击"训练"按钮
   - 输入训练时长、数据集
   - 记录训练指标（AUC、准确率等）

5. **评估模型**
   - 输入测试集指标
   - 对比不同训练轮次的效果

6. **部署模型**
   - 选择最优模型
   - 点击"部署"
   - 设置部署环境和端点

---

## 第九步：管理工件 📦

保存研究过程中的重要文件：

1. **切换到"工件 (Artifacts)"标签页**
2. **点击"注册工件"**
3. **上传文件：**
   ```
   名称: 回测权益曲线图
   类型: IMAGE
   版本: v1.0
   文件路径: /output/equity_curve.png
   文件大小: 245 KB
   关联回测: BT-20260805-001
   ```

**可管理的工件类型：**
- 📊 **模型文件**（.pkl, .h5）
- 📄 **报告文件**（.pdf, .html）
- 📈 **图表**（.png, .jpg）
- 📋 **日志文件**（.log）
- ⚙️ **配置文件**（.json, .yaml）
- 📊 **数据文件**（.csv, .xlsx）

---

## 第十步：查看系统日志 📋

1. **切换到"日志 (Logs)"标签页**
2. **查看所有操作日志**

**筛选功能：**
- **按级别筛选**: INFO / WARNING / ERROR
- **按来源筛选**: EXPERIMENT / BACKTEST / STRATEGY
- **关键词搜索**: 搜索"失败"、"成功"等

**查看详情：**
- 点击任意日志行
- 下方详情面板显示完整信息

**导出日志：**
- 点击"导出"按钮
- 选择保存路径
- 生成 .txt 文件

---

## 🎯 常用操作技巧

### 1. 快速导航
- **双击左侧资源管理器**的项目，快速跳转到对应标签页
- 使用**顶部标签页**切换不同功能模块

### 2. 批量操作
- **Ctrl + 点击**选择多个项目
- 批量删除、批量标记

### 3. 搜索查找
- 每个标签页都有**搜索框**
- 支持模糊搜索名称、ID、标签

### 4. 状态管理
- **实验状态**: DRAFT → RUNNING → COMPLETED/FAILED
- **策略状态**: DRAFT → TESTING → LIVE → RETIRED
- **回测状态**: PENDING → RUNNING → COMPLETED/FAILED

### 5. 关联追踪
- 点击任意记录的"关联"按钮
- 查看上下游依赖关系
- 构建完整的研究链路

---

## 💡 最佳实践

### 1. 命名规范
```
实验名称: [策略类型]_[研究重点]_[日期]
  例如: TrendFollowing_MA_Cross_20260805

数据集名称: [市场]_[品种]_[频率]_[版本]
  例如: A股_沪深300_日线_v1.0

特征名称: [指标类型]_[参数]
  例如: MA_5, RSI_14, MACD_12_26_9
```

### 2. 版本管理
- 重要修改必须更新版本号（v1.0 → v1.1）
- 为每个版本添加详细的变更说明
- 保留历史版本供对比分析

### 3. 标签使用
```
按策略类型: 趋势跟踪, 均值回归, 套利
按市场: A股, 港股, 期货, 加密货币
按状态: 验证中, 已上线, 已下线
```

### 4. 定期维护
- **每周**检查错误日志
- **每月**清理过期数据集快照
- **每季度**归档停用的策略和实验

---

## 🔍 故障排查

### 问题1：回测失败
**解决方案：**
1. 检查日志标签页的 ERROR 级别日志
2. 验证数据集是否完整
3. 检查策略代码是否有语法错误

### 问题2：特征IC值异常
**解决方案：**
1. 检查数据质量分数
2. 验证特征计算公式
3. 查看数据集的时间范围是否匹配

### 问题3：流水线卡住
**解决方案：**
1. 检查流水线状态
2. 查看执行日志
3. 点击"暂停"后"重置"

---

## 📞 获取帮助

- 查看 `OPTIMIZATION_REPORT.md` 了解技术细节
- 查看 `engine_log_extension.py` 了解引擎API
- 在日志标签页搜索相关错误信息

---

**祝你使用愉快！ 🎉**
