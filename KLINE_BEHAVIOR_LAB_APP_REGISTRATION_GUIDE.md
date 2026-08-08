# K-Line Behavior Lab - 应用注册指南

## 🎯 目标

将K-Line Behavior Lab作为独立应用显示在VeighNa应用中心。

---

## ✅ 方法1：自动注册（推荐）

VeighNa通常会自动扫描 `vnpy/` 目录下的应用。

### 步骤：

1. **确保文件结构正确**
   ```
   vnpy/
   └── kline_behavior_lab/
       ├── __init__.py      (包含 from .app import KLineBehaviorLabApp)
       ├── app.py          (包含 KLineBehaviorLabApp 类)
       ├── engine.py
       ├── widget.py
       └── constant.py
   ```

2. **重启VeighNa Studio**
   - 完全关闭VeighNa Studio
   - 重新启动

3. **在应用中心查找**
   - 打开VeighNa Apps界面
   - 查找 **"K-Line Behavior Lab"** 或 **"K线行为研究实验室"**
   - 点击打开

---

## 🔧 方法2：检查应用加载

如果没有自动加载，检查VeighNa的应用加载逻辑。

### 查找应用注册文件

VeighNa的应用注册通常在以下位置之一：

```
veighna_studio/
├── config/
│   └── app_config.json
├── trader/
│   └── app.py
└── __init__.py
```

### 手动添加应用

在VeighNa的应用配置中添加：

```python
# 在 vnpy/trader/app.py 或类似文件中
APPS = {
    # ... 其他应用
    "KLineBehaviorLab": "vnpy.kline_behavior_lab.KLineBehaviorLabApp",
}
```

---

## 📋 方法3：通过脚本注册

创建一个注册脚本：

```python
# register_kline_behavior_lab.py
from vnpy.kline_behavior_lab import KLineBehaviorLabApp

# VeighNa会自动发现并加载这个应用
print(f"Registered: {KLineBehaviorLabApp.display_name}")
```

---

## 🎨 应用信息

在应用中心中，K-Line Behavior Lab将显示为：

**卡片信息：**
- **应用名称**: K-Line Behavior Lab
- **显示名称**: K-Line Behavior Lab K线行为研究实验室
- **功能描述**: 
  - 67个K线特征
  - 8个研究模板
  - 智能条件验证
  - 灵活采样策略

---

## ✅ 验证应用已注册

### 方法1：通过VeighNa Studio
1. 启动VeighNa Studio
2. 打开应用中心
3. 查找 "K-Line Behavior Lab"

### 方法2：通过Python测试
```bash
D:\veighna_studio\python.exe test_kline_behavior_lab_app.py
```

### 方法3：检查控制台输出
启动VeighNa Studio时，控制台应该显示：
```
Loading app: K-Line Behavior Lab
```

---

## 🔍 故障排查

### 问题1：应用中心看不到应用

**解决方案：**
1. 确认文件结构正确
2. 检查 `__init__.py` 是否正确导出
3. 重启VeighNa Studio
4. 查看控制台错误信息

### 问题2：点击应用没反应

**解决方案：**
1. 检查 `widget.py` 中的导入是否正确
2. 确认 `quant_research` 模块可用
3. 查看日志文件

### 问题3：应用打开报错

**解决方案：**
1. 运行测试脚本检查依赖
2. 确认所有核心引擎可用
3. 检查ResearchEngine初始化

---

## 📝 应用特性

### 核心功能
- ✅ 67个K线特征（9大类别）
- ✅ 8个研究模板
- ✅ 实时条件验证
- ✅ 4种采样规则
- ✅ 智能依赖解析

### 技术特点
- ✅ 独立应用窗口
- ✅ 专业的标题栏
- ✅ 完整的UI集成
- ✅ 桥接quant_research核心引擎

---

## 🚀 使用流程

1. **在应用中心点击 "K-Line Behavior Lab"**
2. **看到专业的应用窗口**
   - 顶部：标题栏显示 "🔬 K-Line Market Behavior Lab"
   - 副标题：显示特征数和模板数
   - 主体：完整的研究界面
3. **开始研究**
   - 选择模板或自定义条件
   - 配置采样规则
   - 执行研究

---

## 🎊 完成标志

当你看到以下内容时，说明注册成功：

### VeighNa应用中心
```
┌─────────────────────────────┐
│  K-Line Behavior Lab        │
│  K线行为研究实验室           │
│  67特征 | 8模板              │
└─────────────────────────────┘
```

### 点击后打开的窗口
```
┌─────────────────────────────────────┐
│ 🔬 K-Line Market Behavior Lab       │
│ K线行为研究实验室 | 67个特征 | 8个模板 │
├─────────────────────────────────────┤
│                                     │
│  [研究界面 - BehaviorResearchTab]   │
│                                     │
└─────────────────────────────────────┘
```

---

## 📞 需要帮助？

如果遇到问题：
1. 运行测试脚本：`test_kline_behavior_lab_app.py`
2. 查看控制台日志
3. 检查文件权限
4. 确认VeighNa版本兼容

---

**K-Line Behavior Lab v1.0.0**  
**独立应用，专业研究！**
