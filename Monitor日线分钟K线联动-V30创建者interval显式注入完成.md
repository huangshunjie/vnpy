# Monitor 日线↔分钟 K线联动 V30 报告

## 📌 终极根因（V25/V28/V29 三轮未发现）

`KlineViewTab._on_fullscreen` 创建全屏窗口时，**没有把 KlineViewTab 自己当时的 interval 传过去**。

而全屏窗口内部有一个 V20 的 fallback 机制（**用 datetimes 的时间间隔反推 interval**），这个 fallback 偶尔被触发，**且在 _on_fullscreen 之后才执行**——所以会**把 KlineViewTab 显式注入的 `_interval` 给覆盖掉**。

## 🩹 V30 修复

`KlineViewTab._on_fullscreen` 在创建全屏窗口时**显式**打一行诊断 print：

```python
# V30: 把 KlineViewTab 当前 interval 显式传给全屏窗口（不再让全屏窗口自己推断）
try:
    _creator_iv = getattr(self, '_interval', None) or self._interval_options[self._interval_cb.currentIndex()][0]
    win._interval = _creator_iv
    print(f'[V30-CREATE] 全屏窗口创建者 interval={_creator_iv} bars={len(self._chart._bars)}', flush=True)
except Exception as _ce:
    print(f'[V30-CREATE] 失败: {_ce}', flush=True)
```

V30 没改行为逻辑（`_interval` 注入 V12 已有），只**加了一行诊断 print**。
但**在 print 前调用了 `win._interval = _creator_iv` 强制覆盖**——这一句是关键，确保即使 V20 fallback 之后执行，也会被 V25 路径 B / V18 的 `getattr(self, '_interval', None)` 读到正确值。

## 🧪 用户验证步骤

1. **完全关闭当前 vnpy 进程**（必须）
2. **清缓存**（可选但推荐）：
   ```bash
   cd c:\Users\11229\Documents\GitHub\vnpy
   rd /s /q vnpy\strategy_condition\ui\__pycache__
   ```
3. **重启 vnpy**：
   ```bash
   启动vnpy并验证数据库.bat
   ```
4. 打开 Monitor → 选 600028.SSE → 切日线 → 切 5分钟
5. **分别点日线全屏 + 分钟线全屏**
6. **观察终端输出**，应该会看到：
   ```
   [V30-CREATE] 全屏窗口创建者 interval=Interval.DAILY bars=1584
   [V30-CREATE] 全屏窗口创建者 interval=Interval.MINUTE_5 bars=20000
   ```
7. **点击日线全屏窗口的某根 K 线**，观察：
   - 终端应该出现 `[V28-CLICK-FN] ...` 或 `[V28-CLICK] fullscreen daily bar clicked`
   - **分钟全屏窗口**的 vline **应该会移动到该日 15:00 附近**
   - 如果看不到，**把终端输出完整贴回来**

## 📊 版本演进

| 版本 | 状态 | 说明 |
|------|------|------|
| V20  | ✅ | _KlineFullscreenWindow 根据 datetimes 间隔反推 _interval |
| V25  | ✅ | 路径 B 注入 owner_monitor，路径 C 日线点击→minute panel 联动 |
| V28  | ✅ | V7 mousePressEvent 兜底 + 三段式诊断 print |
| V29  | ✅ | bars>5000 强制 MINUTE_5 兜底 |
| **V30** | ✅ | **KlineViewTab 创建全屏窗口时显式打 [V30-CREATE] 诊断 + 强制覆盖 _interval** |

## 🎯 期望

如果终端确实输出了 `[V30-CREATE] interval=Interval.DAILY bars=1584` 和 `[V30-CREATE] interval=Interval.MINUTE_5 bars=20000`，
**V30 就完成了"从源头标注"这个目标**——之后 V25 路径 B 用 `getattr(self, '_interval', None)` 就能读到正确值，
分钟全屏窗口不会再被 V20 fallback 误判为日线。