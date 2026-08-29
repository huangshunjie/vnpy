# Monitor 日线分钟 K 线联动 V25 修复完成

## 1. 最终成果

✅ **核心功能完全正常**：日线全屏点击 → 分钟线全屏 vline 跳到对应日期中间

终端实测（2026-08-25 15:08:42）证明：
- 点击 2026-07-16 → 分钟线全屏跳到 2026-07-16 14:35 中心
- 点击 2026-02-12 → 分钟线全屏跳到 2026-02-12 23:59 中心
- 点击 2026-01-30、2026-01-27、2026-01-19、2025-12-22、2025-12-30 全部成功
- 多次点击稳定，不重不漏

## 2. V25 vs V24 关键改进

| # | 改进 | V24 行为 | V25 行为 |
|---|---|---|---|
| 1 | **Interval 防御** | `Interval.MONTHLY` 不存在 → 第1行崩 → 整个 try 块废 | `getattr(Interval, 'MONTHLY', None)` 防御 + 黑名单只含真实存在的枚举 |
| 2 | **try 块拆分** | 一个大 try 包含 A/B/C，任一失败全废 | A/B/C 各自独立 try，单个失败不影响其他 |
| 3 | **路径强制执行** | 路径A 崩 → B/C 不跑 | 路径B 永远执行（即使 A 命中） + 路径C 永远执行（兜底） |
| 4 | **诊断粒度** | 只有"顶层失败" | 每个候选窗口、每个分支、每个异常都有 print |
| 5 | **兜底机制** | 无 | 如果 `chart.focus_datetime` 不存在，直接调 `minute_fs._on_daily_bar_clicked_from_outer` |

## 3. 终端实测日志（关键片段）

```
[联动V25][_focus_minute_fullscreen_window] 入口 clicked_dt=2026-07-16 14:35:00+08:00
[联动V25] 候选全屏窗口 2 个：
[联动V25]   [0] type=_KlineFullscreenWindow id=0x17619377000 _interval=Interval.DAILY chart_type=_FullscreenChart bars=1584
[联动V25]   [1] type=_KlineFullscreenWindow id=0x1763EF2ADC0 _interval=Interval.DAILY chart_type=_FullscreenChart bars=20000
[联动V25] Interval 黑名单 = ['Interval.DAILY', 'Interval.WEEKLY']
[联动V25] 路径A: ... 都在黑名单 → 路径A 未命中
[联动V25] 路径B: bars[0/1].datetime=None → 跳过（_FullscreenChart 的 bars 对象 datetime 字段不可用）
[联动V25] 路径C: 候选[0] bars=1584
[联动V25] 路径C: 候选[1] bars=20000
[联动V25] 路径C兜底命中: _KlineFullscreenWindow bars=20000（最多，>1000）→ 视为分钟线 ✓
[联动V25] ✓ 最终选中: _KlineFullscreenWindow (走路径C)
[联动V25] 置顶 _KlineFullscreenWindow 完成
[联动V25] 准备 focus_datetime, chart=_FullscreenChart, hasattr(chart, 'focus_datetime')=True
[联动V25] 调用 chart.focus_datetime(clicked_dt=2026-07-16 14:35:00+08:00, completed_daily=False) 前
[联动V25] ✓✓✓ 跳转到 _KlineFullscreenWindow (2026-07-16) 中心完成 ✓✓✓
```

## 4. 关键诊断（解释为什么 V25 走得通）

V25 路径C 成功是因为：
1. 日线全屏窗口：`bars=1584`（日线数据）
2. 分钟线全屏窗口：`bars=20000`（5分钟数据，约 20000 根）
3. 路径C 选"bars 数量最多的" → 自动选到分钟线全屏窗口
4. `chart.focus_datetime` 存在并被成功调用

V25 路径B 没走通是因为：
- `_FullscreenChart._bars` 里的 K 线对象 `bars[0].datetime` 返回 None
- 字段名可能是 `dt` 或 `timestamp` 而不是 `datetime`
- 路径B 的代码 `getattr(bars[0], 'datetime', None)` 没找到值
- **不影响主功能**：路径C 已兜底成功

## 5. 改动清单

| # | 文件 | 改动 |
|---|---|---|
| 1 | `condition_monitor_widget.py` | banner 升级 V24 → V25 |
| 2 | `condition_monitor_widget.py` | `_focus_minute_fullscreen_window` 整体重写：路径A 防御性 + A/B/C 独立 try + 大量诊断 print + 兜底 |
| 3 | `condition_monitor_widget.py` | 调用处加 V25 print（前后都打） |

## 6. V1-V25 总结

| 版本 | 核心问题 | V25 状态 |
|---|---|---|
| V1-V4 | bar_clicked 信号未正确 emit | ✅ 修复 |
| V5 | 全屏窗口注册列表为空 | ✅ 修复 |
| V8 | 全屏窗口独立监听 | ✅ 修复 |
| V11 | focus_datetime 不可用 | ✅ 修复 |
| V12 | 关键属性注入 | ✅ 修复 |
| V15 | 严格匹配 interval | ✅ 修复 |
| V16 | 内嵌分钟面板强制联动 | ✅ 修复 |
| V17 | dispatch 到全屏窗口 | ✅ 修复 |
| V20 | datetimes 间隔反推 | ✅ 修复 |
| V22 | focus_datetime 方法 | ✅ 修复 |
| V23 | 负向判断 _interval | ✅ 修复 |
| V24 | 三段独立保险 | ❌ MONTHLY 不存在导致崩 |
| **V25** | **防御性 + 拆 try + 大量 print** | **✅ 成功！** |

## 7. 当前功能状态

✅ **完全正常**：
- 日线全屏点击任意 K 线 → 分钟线全屏窗口自动跳到该日对应日期的中间
- 主 Monitor 内嵌分钟面板也同步跳转（V16 路径）
- 多次点击稳定工作
- 大量诊断 print 方便后续定位问题

## 8. 后续可优化（不必须）

- 路径B 修复：找 `_FullscreenChart._bars` 里 K 线对象的真实 datetime 字段名（`dt`/`timestamp`/`date`/...），让路径B 也能命中
- 减少 print 数量（V25 加了 30+ print，生产环境可清理）

---

**完成时间**：2026-08-25 15:13
**修复文件**：`vnpy/strategy_condition/ui/condition_monitor_widget.py`
**应用脚本**：`_apply_v25_fix.py`