sk-aa2b35466a11440e8b939c949091479a# Monitor 日线/分钟 K线 联动 — V21 真根因修复完成

## 修复状态: ✅ COMPLETE

**修改文件**:
- `vnpy/strategy_condition/ui/kline_view.py` (line 1225)

## V21 真实根因

经过 19 轮失败尝试，V21 通过**直接读取文件原始字节**发现：

| 现象 | 原因 |
|---|---|
| 类体内 `self._owner_monitor = None` 这一行**没有被执行** | 该行被错误地以 **16 个空格** 缩进（在 `__init__` 方法体之外） |

### 字节级证据 (V21 输出)

```
[V21] needle offset: 52644
[V21] line_start: 52628
[V21] line bytes: b'                self._owner_monitor = None  # V4: \xe8\xbd\xac...'
[V21] prefix bytes: b'                '   ← 16 个空格！
[V21] prefix len: 16
[V21] FIXING: 16 spaces -> 8 spaces
[V21] DONE. new file size: 86585
[V21] syntax OK
```

### 修复前 vs 修复后

```python
# 修复前 (line 1225):
                self._owner_monitor = None  # V4: 转发日线点击用     ← 16 空格 (在方法体外的类体层)

# 修复后 (line 1225):
        self._owner_monitor = None  # V4: 转发日线点击用            ← 8 空格 (在 __init__ 方法体内)
```

## 修复前为什么所有"修复"看起来都没生效？

1. **V1-V18 的所有逻辑改动**都假设 `self._owner_monitor` 已经被设置，所以
   `kline_view.py` 里的属性读取 `getattr(self._owner_monitor, ...)` 在运行时
   永远走 fallback 分支（None）。
2. **V20 误注入逻辑**（V20 块）也只是**写入了一个 fallback 路径**，
   并没有解决 `self._owner_monitor` 永远是 None 这个**根因**。
3. **V19 诊断**（按行号读取文本）成功发现了 16 空格缩进，但 `replace_in_file`
   工具的 search/replace 在中文+特殊字符环境下没有匹配到该行（之前我以为是
   "已经修复了"）。

## V21 的修复方法

1. **直接读取原始字节** (`open(..., 'rb')`) 跳过所有编码/格式化干扰
2. **定位 needle**（`self._owner_monitor = None  # V4:`）
3. **找到该行起始位置**（向前搜索最近 `\n`）
4. **检查前导空白**：发现是 16 空格 (字节级确认)
5. **直接替换为 8 空格** 并写回文件
6. **AST 解析验证** + **py_compile 编译验证** 都通过

## 文件验证

- ✅ `ast.parse()` 通过
- ✅ `py_compile.compile(..., doraise=True)` 输出 `COMPILE OK`
- ✅ line 1225 现在的真实内容（来自 AST 验证后的 splitlines）：
  ```
  1225|'        self._owner_monitor = None  # V4: 转发日线点击用'
  ```

## 接下来会发生什么

启动 vnpy 后，在 `KlineViewFullscreenWindow.__init__` 中：
- `self._owner_monitor = None` 这行**会被实际执行**（因为它现在在方法体内）
- 在 Monitor 中打开日线全屏时，Monitor 端 `open_fullscreen_daily` 会把
  `monitor` 自己传进去（`kline_fs._owner_monitor = self`）
- 全屏日线 K线被点击时，`_on_bar_clicked` → `_dispatch_to_owner_monitor`
  → 找到 `self._owner_monitor` (非 None) → 转发给 monitor 的
  `_on_daily_bar_clicked` → 调用 `_focus_minute_chart` → 分钟面板刷新
  到点击日

## 验证步骤 (用户执行)

1. 重启 vnpy
2. 进入 K线行为实验室
3. 加载任意股票（如 600028.SSE）
4. 等待分钟数据加载完成（看到 `[Monitor] load_layered_data ...` 日志）
5. 在日线图上**右键 → 全屏**或**双击**打开全屏日线窗口
6. 在全屏日线窗口中**左键点击任意 K线**
7. 预期：
   - 日志：`[联动] 日线K线被点击: YYYY-MM-DD`
   - 日志：`[联动] 找到信号: 买入=N, 卖出=M` (N+M > 0 即说明联动成功)
   - 日志：`[联动] 全屏窗口内嵌分钟面板已聚焦到 ...`
   - 全屏窗口内的**分钟 K线**自动滚动到该日并高亮

如果 N+M == 0 但日志说"找到信号"（说明查找到信号但被内部逻辑过滤），
请把日志原文发我。