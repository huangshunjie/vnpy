# K-Line Market Behavior Lab - 快速入门指南

## 🚀 5分钟快速开始

### 第一步：验证安装

运行测试确保所有组件正常：

```bash
# 测试核心引擎
D:\veighna_studio\python.exe test_core_engines_simple.py

# 测试UI集成
D:\veighna_studio\python.exe test_ui_integration.py
```

**预期结果：**
```
[PASS] Phase 2 - Data Models
[PASS] Phase 3 - Feature Engine
[PASS] Phase 4 - Event Research
[PASS] Integration Test
[PASS] UI Integration Test
```

---

## 📚 使用示例

### 示例1：使用特征引擎

```python
from vnpy.quant_research.behavior import FeatureEngine
import pandas as pd
import numpy as np

# 创建引擎
engine = FeatureEngine()

# 准备K线数据
df = pd.DataFrame({
    'open': [10.0, 10.2, 10.1, 10.3],
    'high': [10.5, 10.6, 10.4, 10.7],
    'low': [9.8, 9.9, 9.7, 10.0],
    'close': [10.2, 10.1, 10.3, 10.5],
    'volume': [1000000, 1200000, 900000, 1500000],
})

# 计算特征
features = ['return_1', 'body_ratio', 'volume_ratio']
result = engine.calculate(df, features)

print(result.head())
print(f"\n计算了 {len(result.columns)} 列")
```

---

### 示例2：使用条件构建器

```python
from vnpy.quant_research.behavior import ConditionBuilder

# 创建构建器
builder = ConditionBuilder()

# 1. 构建简单条件
condition1 = builder.build_simple_condition('return_1', '<', -0.03)
print(f"简单条件: {condition1}")

# 2. 构建复合条件
conditions = [
    'return_1 < -0.03',
    'lower_shadow_ratio > 0.4',
    'volume_ratio > 1.5'
]
condition2 = builder.build_compound_condition(conditions, 'AND')
print(f"\n复合条件: {condition2}")

# 3. 验证条件
valid, error, features = builder.validate_expression(condition2)
print(f"\n验证结果: {'有效' if valid else '无效'}")
print(f"依赖特征: {features}")

# 4. 使用模板
templates = builder.get_condition_templates()
print(f"\n可用模板: {len(templates)}个")
for t in templates[:3]:
    print(f"  - {t['name']}: {t['description']}")
```

---

### 示例3：完整研究流程

```python
from vnpy.quant_research.behavior import (
    FeatureEngine,
    ConditionBuilder,
    SamplingEngine,
    get_global_registry
)
from vnpy.quant_research.model.kline_event_model import EventSamplingRule
import pandas as pd
import numpy as np

# === 步骤1: 准备数据 ===
print("步骤1: 准备数据")
np.random.seed(42)
df = pd.DataFrame({
    'open': np.random.rand(200) * 10 + 10,
    'high': np.random.rand(200) * 10 + 15,
    'low': np.random.rand(200) * 10 + 5,
    'close': np.random.rand(200) * 10 + 10,
    'volume': np.random.rand(200) * 1000000,
})
print(f"✓ 数据: {len(df)}行")

# === 步骤2: 构建研究条件 ===
print("\n步骤2: 构建条件")
builder = ConditionBuilder()

# 使用模板
templates = builder.get_condition_templates()
template = templates[0]  # 大阴线底部反转
condition = template['expression']

# 或手动构建
# condition = "(return_1 < -0.03) & (lower_shadow_ratio > 0.4) & (volume_ratio > 1.5)"

valid, error, features = builder.validate_expression(condition)
print(f"✓ 条件: {condition[:50]}...")
print(f"✓ 依赖特征: {features}")

# === 步骤3: 计算特征 ===
print("\n步骤3: 计算特征")
engine = FeatureEngine()
df_with_features = engine.calculate(df, features)
print(f"✓ 计算完成: {len(df_with_features.columns)}列")

# === 步骤4: 评估条件（找触发点）===
print("\n步骤4: 评估条件")
result = builder.evaluate_on_data(condition, df_with_features)
trigger_count = result.sum()
print(f"✓ 找到 {trigger_count} 个触发点")

# === 步骤5: 性能统计 ===
print("\n步骤5: 性能统计")
stats = engine.get_statistics()
print(f"✓ 总计算: {stats['total_calculations']}次")
print(f"✓ 缓存命中率: {stats['cache_hit_rate']:.2%}")
print(f"✓ 平均耗时: {stats['avg_time']:.4f}秒")

print("\n✅ 研究流程完成！")
```

---

## 🎨 UI集成代码示例

### 在behavior_tab.py中使用核心引擎

```python
class BehaviorResearchTab(QWidget):
    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        
        # === 核心引擎初始化 ===
        self.feature_engine = FeatureEngine()
        self.condition_builder = ConditionBuilder()
        self.sampling_engine = SamplingEngine()
        self.feature_registry = get_global_registry()
        
        print(f"[BehaviorTab] 已加载 {len(self.feature_registry.get_feature_names())} 个特征")
        
        self._init_ui()
    
    def _on_apply_template(self):
        """应用条件模板"""
        template = self._template_combo.currentData()
        if template:
            # 填充条件表达式
            self._condition_edit.setText(template['expression'])
            # 填充研究名称
            self._research_name_edit.setText(template['name'])
            # 更新状态
            self._status_label.setText(f"✓ 已应用模板: {template['name']}")
    
    def _on_condition_changed(self):
        """实时验证条件"""
        condition = self._condition_edit.toPlainText().strip()
        if not condition:
            self._validation_label.setText("请输入条件表达式")
            return
        
        # 使用条件构建器验证
        valid, error, features = self.condition_builder.validate_expression(condition)
        
        if valid:
            # 显示绿色提示
            feature_text = ', '.join(features[:3])
            if len(features) > 3:
                feature_text += f" (+{len(features)-3}个)"
            self._validation_label.setText(f"✓ 有效 | 依赖: {feature_text}")
            self._validation_label.setStyleSheet("color: green;")
        else:
            # 显示红色错误
            self._validation_label.setText(f"✗ {error}")
            self._validation_label.setStyleSheet("color: red;")
    
    def _on_validate_condition(self):
        """详细验证对话框"""
        condition = self._condition_edit.toPlainText().strip()
        if not condition:
            QMessageBox.warning(self, "验证", "请输入条件表达式")
            return
        
        valid, error, features = self.condition_builder.validate_expression(condition)
        
        if valid:
            # 显示详细信息
            msg = f"✓ 条件有效\n\n"
            msg += f"依赖特征 ({len(features)}个):\n"
            msg += '\n'.join(f"  - {f}" for f in features)
            QMessageBox.information(self, "验证结果", msg)
        else:
            QMessageBox.warning(self, "验证失败", f"条件表达式无效:\n\n{error}")
    
    def _on_view_features(self):
        """增强的特征浏览器"""
        from PySide6.QtWidgets import QDialog, QTextEdit, QVBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"K线特征库 ({len(self.feature_registry.get_feature_names())}个)")
        dialog.resize(700, 600)
        
        layout = QVBoxLayout(dialog)
        
        # 创建特征列表
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        
        # 获取统计信息
        stats = self.feature_registry.get_statistics()
        
        # 构建Markdown文本
        text = f"# K线特征库\n\n"
        text += f"**总计:** {stats['total_features']}个特征\n"
        text += f"**适合条件:** {stats['suitable_for_condition']}个\n"
        text += f"**适合因子:** {stats['suitable_for_alpha']}个\n\n"
        text += "---\n\n"
        
        # 按类型分组显示
        from vnpy.quant_research.model.kline_feature_model import KLineFeatureType
        
        for feature_type in KLineFeatureType:
            features = self.feature_registry.list_features(feature_type=feature_type)
            if features:
                text += f"\n## {feature_type.value.upper()}\n\n"
                for f in sorted(features, key=lambda x: x.name):
                    text += f"**{f.name}** - {f.display_name}\n"
                    text += f"> {f.description}\n"
                    text += f"> 回看周期: {f.lookback_period}日\n\n"
        
        text_edit.setMarkdown(text)
        layout.addWidget(text_edit)
        
        # 关闭按钮
        btn = QPushButton("关闭")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)
        
        dialog.exec()
```

---

## 🔧 UI增强完整代码片段

### 1. 添加模板选择UI

在 `_create_condition_group` 方法中添加：

```python
def _create_condition_group(self) -> QGroupBox:
    group = QGroupBox("🎯 研究条件")
    layout = QVBoxLayout(group)
    
    # === 新增：模板选择 ===
    template_layout = QHBoxLayout()
    template_layout.addWidget(QLabel("模板:"))
    
    self._template_combo = QComboBox()
    self._template_combo.addItem("自定义", "")
    
    # 加载模板
    templates = self.condition_builder.get_condition_templates()
    for template in templates:
        self._template_combo.addItem(template['name'], template)
    
    template_layout.addWidget(self._template_combo, 1)
    
    apply_btn = QPushButton("应用")
    apply_btn.clicked.connect(self._on_apply_template)
    template_layout.addWidget(apply_btn)
    
    layout.addLayout(template_layout)
    # === 模板选择结束 ===
    
    # 原有的条件表达式输入...
    layout.addWidget(QLabel("条件表达式:"))
    self._condition_edit = QTextEdit()
    # ...继续原有代码
```

### 2. 添加实时验证

```python
# 在条件输入框定义后添加
self._condition_edit = QTextEdit()
self._condition_edit.setPlaceholderText("(return_1 < -0.03) & (volume_ratio > 1.5)")
self._condition_edit.setMaximumHeight(100)
self._condition_edit.textChanged.connect(self._on_condition_changed)  # 连接信号
layout.addWidget(self._condition_edit)

# 添加验证状态标签
self._validation_label = QLabel("请输入条件表达式")
self._validation_label.setStyleSheet("color: #6c757d; font-size: 11px;")
layout.addWidget(self._validation_label)
```

### 3. 添加验证按钮

```python
# 在按钮布局中添加
btn_layout = QHBoxLayout()

self._btn_view_features = QPushButton("📚 浏览特征")
self._btn_view_features.clicked.connect(self._on_view_features)
btn_layout.addWidget(self._btn_view_features)

# === 新增：验证按钮 ===
validate_btn = QPushButton("✓ 验证条件")
validate_btn.clicked.connect(self._on_validate_condition)
btn_layout.addWidget(validate_btn)
# === 验证按钮结束 ===

btn_layout.addStretch()
layout.addLayout(btn_layout)
```

---

## ✅ 完成检查清单

### 核心引擎集成

- [x] 导入核心引擎模块
- [ ] 在__init__中创建引擎实例
- [ ] 添加模板选择UI
- [ ] 添加实时验证
- [ ] 添加验证按钮
- [ ] 实现事件处理方法
- [ ] 增强特征浏览器

### 功能验证

- [ ] 启动VeighNa Studio
- [ ] 打开行为研究Tab
- [ ] 确认引擎加载成功（控制台输出）
- [ ] 测试模板选择
- [ ] 测试条件验证
- [ ] 测试特征浏览

---

## 🎯 预期效果

### 用户体验流程

1. **打开Tab** → 看到"已加载67个特征"
2. **选择模板** → 自动填充条件和名称
3. **编辑条件** → 实时显示验证结果（绿色✓/红色✗）
4. **点击验证** → 弹窗显示详细依赖特征
5. **浏览特征** → 按类型分组显示所有特征
6. **开始研究** → 执行完整分析流程

---

## 📞 获取帮助

### 遇到问题？

1. **查看详细文档**
   - `BEHAVIOR_TAB_ENHANCEMENT_PLAN.md` - UI增强步骤
   - `KLINE_BEHAVIOR_LAB_PHASE1-4_COMPLETE_REPORT.md` - 完整报告

2. **运行测试**
   ```bash
   D:\veighna_studio\python.exe test_core_engines_simple.py
   D:\veighna_studio\python.exe test_ui_integration.py
   ```

3. **检查导入**
   ```python
   from vnpy.quant_research.behavior import (
       FeatureEngine,
       ConditionBuilder,
       SamplingEngine,
       get_global_registry,
   )
   ```

---

## 🚀 下一步

### 立即行动

1. **打开文件**
   ```
   vnpy/quant_research/ui/behavior_tab.py
   ```

2. **应用代码片段**
   - 复制上面的代码示例
   - 粘贴到对应位置
   - 保存文件

3. **测试功能**
   - 启动VeighNa Studio
   - 验证UI正常工作

### 预计时间

- **代码集成:** 20-30分钟
- **功能测试:** 10-15分钟
- **总计:** 约40分钟完成

---

## 🎉 完成后

恭喜！你将拥有：

✅ 67个可用K线特征  
✅ 8个预置研究模板  
✅ 实时条件验证  
✅ 智能依赖解析  
✅ 完整的研究流程  

**准备开始量化研究！**

---

需要我：
1. 提供更详细的某个部分说明
2. 创建额外的测试用例
3. 解释某个技术细节
