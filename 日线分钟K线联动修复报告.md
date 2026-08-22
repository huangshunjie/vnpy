# 日线 K 线 → 5 分钟 K 线联动 修复报告

## 现象
- 截图：Monitor 标签页，日线 K 线 4022 根正常显示
- 5 分钟区域显示：`缺少5分钟数据` + `暂无快照数据`
- 状态栏：`日线 4022 根 / 5分钟 0 根`

## 根因
`vnpy/strategy_condition/ui/widget.py` 的 [`_feed_monitor()`](vnpy/strategy_condition/ui/widget.py:1033) 有一个**两层 try/except** 结构：

1. **内层 try**（line 1093-1109）调用 `monitor_eng.generate_snapshots(bars=minute_bars, ...)`
2. **外层 try**（line 1033-1142）包住整个流程
3. **外层 except**（line 1143+）是降级路径，**硬编码 `minute_bars=[]` 传给 UI**

只要内层 `generate_snapshots` 抛任何异常（业务逻辑差异、未捕获的属性访问、指标计算报错等）：
- 内层 except 把 `minute_snapshots` 设为 `[]`，**但此时 `minute_bars` 仍是有效的几百根数据**
- 外层 except 立刻抓住这个已经被"处理过"的异常，走降级
- 降级路径 `load_layered_data(..., [], [], ...)` 把 `minute_bars` 当成空列表推给 UI
- [`ConditionMonitorWidget.load_layered_data()`](vnpy/strategy_condition/ui/condition_monitor_widget.py:948) 看到 `minute_bars=[]` → 调用 [`show_empty("缺少5分钟数据")`](vnpy/strategy_condition/ui/condition_monitor_widget.py:679)
- 用户看到 "5分钟 0 根"

也就是说：**数据库里其实有数据（294,098 根 5min bar），但被代码自己清空了**。

## 修复
[`vnpy/strategy_condition/ui/widget.py`](vnpy/strategy_condition/ui/widget.py) 两个补丁：

### 修复点 1（line 1107-1117）
内层 except 增加 traceback 打印，**明确不让外层 try 吞掉整个流程**：
```python
except Exception as e:
    # 关键：只 print+记日志,不要 raise,
    # 否则外层 try/except 会把整个 _feed_monitor 当作失败,
    # 走降级路径（且该路径会清空 minute_bars,导致 UI 显示
    # "5分钟 0 根"+"缺少5分钟数据"）。
    print(f"[SCE] minute snapshots 生成失败: {e}")
    import traceback as _tb_snap
    _tb_snap.print_exc()
    minute_snapshots = []
```

### 修复点 2（line 1149-1172）
外层 except 的降级路径**不再硬编码 `[]`**，而是用真实变量：
```python
self._monitor_tab.load_layered_data(
    symbol,
    daily_snapshots or [], daily_bars,
    minute_snapshots if minute_snapshots else [],
    minute_bars if minute_bars else [],  # ← 修复前是 []
    buy_dates=buy_dates or [],
    sell_dates=sell_dates or [],
)
```

这样即使 `generate_snapshots` 失败，UI 仍能拿到有效的 `minute_bars`，`load_layered_data` 内部的 [`_build_minute_snapshots_fallback()`](vnpy/strategy_condition/ui/condition_monitor_widget.py:1009) 会用 bars + buy_dates/sell_dates 重建 snapshots，5 分钟 K 线 + 成交量 + 条件波形都能正常显示。

## 验证
1. ✅ 语法检查 `python -m py_compile` 通过
2. ✅ 端到端模拟测试 `tests/_verify_minute_link_fix.py`：
   - 构造 200 根 minute bars + 50 根 daily bars
   - 模拟 `generate_snapshots` 抛 `RuntimeError`
   - 断言降级路径的 `minute_bars` 仍然 = 200 根（不是 0）
   - 测试通过

## 改动文件
| 文件 | 改动 |
|------|------|
| [`vnpy/strategy_condition/ui/widget.py`](vnpy/strategy_condition/ui/widget.py:1107) | 内层 except 加 traceback |
| [`vnpy/strategy_condition/ui/widget.py`](vnpy/strategy_condition/ui/widget.py:1158) | 降级路径保留 minute_bars |
| [`tests/_patch_minute_link_fix.py`](tests/_patch_minute_link_fix.py) | 补丁脚本（已执行） |
| [`tests/_verify_minute_link_fix.py`](tests/_verify_minute_link_fix.py) | 端到端验证脚本（已通过） |

## 用户测试步骤
1. 启动 vnpy
2. 打开 条件监控 → Monitor 标签
3. 选股 + 运行回测
4. 单击日线 K 线
5. **预期**：5 分钟 K 线区域不再显示"缺少5分钟数据"，而是显示对应的 5 分钟 K 线 + 成交量 + 条件波形
6. 如果 `generate_snapshots` 仍然失败，控制台会打印 traceback（便于后续定位根因），但 UI 至少能画出 K 线
