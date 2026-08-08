# K-Line Behavior Lab - 快速访问指南

## 为什么在应用中心找不到？

VeighNa应用中心显示的应用是**预先配置好的应用列表**。新创建的应用需要额外的配置才能在应用中心显示。

但好消息是：**你已经可以使用K-Line Behavior Lab了！**

---

## 🚀 方案1：通过Quant Research Platform访问（推荐）

K-Line Behavior Lab的功能已经完全集成到Quant Research Platform中了！

### 步骤：

1. **打开 "Quant Research P"（量化研究平台）**
   - 在你的VeighNa Apps界面中点击 "Quant Research P"

2. **找到 "Behavior Research" Tab**
   - 在打开的窗口中，会看到多个Tab页
   - 点击 "Behavior Research" 或 "行为研究" Tab

3. **开始使用**
   - 你将看到完整的K-Line Behavior Lab界面
   - 67个特征、8个模板、所有功能都可用

这是**最简单、最直接的方式**，功能完全相同！

---

## 🔧 方案2：创建桌面快捷方式

如果你想要独立的快捷方式，可以创建一个：

### 步骤：

1. **创建启动脚本**
   
   创建文件：`C:\Users\11229\Desktop\K-Line Behavior Lab.bat`
   
   内容：
   ```batch
   @echo off
   D:\veighna_studio\python.exe -c "from vnpy.event import EventEngine; from vnpy.trader.engine import MainEngine; from vnpy.kline_behavior_lab.widget import KLineBehaviorLabWidget; from PySide6.QtWidgets import QApplication; import sys; app = QApplication(sys.argv); main_engine = MainEngine(EventEngine()); widget = KLineBehaviorLabWidget(main_engine, main_engine.event_engine); widget.show(); sys.exit(app.exec())"
   ```

2. **双击运行**
   - 将直接打开K-Line Behavior Lab独立窗口

---

## 🎯 方案3：添加到VeighNa应用列表（高级）

如果你确实想让它在应用中心显示，需要修改VeighNa的配置文件。

### 查找VeighNa配置文件

可能的位置：
```
D:\veighna_studio\Lib\site-packages\veighna\
C:\Users\11229\.veighna\
C:\Users\11229\AppData\Local\veighna\
```

### 需要修改的内容

在VeighNa的应用配置文件中添加：
```python
{
    "name": "KLineBehaviorLab",
    "display_name": "K-Line Behavior Lab",
    "category": "研究平台",
    "icon": "behavior.ico"
}
```

---

## ✅ 推荐做法

**我强烈推荐使用方案1**，因为：

1. **无需额外配置** - 立即可用
2. **功能完全相同** - 所有67个特征和8个模板都在
3. **集成更好** - 可以和其他研究工具协同使用
4. **官方支持** - Quant Research Platform是官方应用

### 现在就试试：

```
1. 在VeighNa Apps中点击 "Quant Research P"
2. 找到 "Behavior Research" Tab
3. 看到熟悉的界面：
   - 模板选择（8个）
   - 条件输入
   - 实时验证
   - 特征浏览（67个）
4. 开始使用！
```

---

## 🔍 验证功能是否可用

运行这个测试：

```bash
D:\veighna_studio\python.exe -c "from vnpy.quant_research.ui.behavior_tab import BehaviorResearchTab; print('BehaviorResearchTab available')"
```

如果显示 "BehaviorResearchTab available"，说明功能完全可用！

---

## 📝 为什么这样设计？

VeighNa的应用中心显示的是**独立应用**，而K-Line Behavior Lab的核心功能是作为**Quant Research Platform的一部分**集成的。

这种设计的优势：
- ✅ 更好的集成性（可以和其他研究工具协同）
- ✅ 共享数据集和资源
- ✅ 统一的研究流程
- ✅ 更容易维护和更新

---

## 🎉 总结

**你不需要在应用中心找到K-Line Behavior Lab！**

**直接使用方案1：**
1. 打开 "Quant Research P"
2. 点击 "Behavior Research" Tab
3. 所有功能都在那里！

这就是最佳的使用方式！

---

**如果还有问题，请告诉我具体看到了什么，我会帮你解决！**
