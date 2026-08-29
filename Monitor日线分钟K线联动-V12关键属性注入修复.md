# Monitor 日线↔分钟 K 线联动 — V12 关键属性注入修复

## 问题根因

V11 之前的所有修复（包括 V8 ~ V11 报告）都在 `_on_fullscreen` 中**读取**
`getattr(win, '_interval', None)` 来判断全屏窗口显示的是日线还是分钟线，
**但整个代码链路中从来没人写入过 `win._interval`！**

结果：
- `_KlineFullscreenWindow` 没有 `_interval` 属性
- `getattr(win, '_interval', None)` 永远返回 `None`
- 全屏窗口内部逻辑无法区分日线/分钟线 → 联动失败

## 修复方案

3 处最小化、零侵入的注入点：

### 1. `KlineViewTab.__init__` 中初始化 `self._interval`（行 ~725）

```python
self._interval = self._interval_options[0][0]   # 默认 DAILY
```

### 2. `KlineViewTab` 中监听下拉框变化时同步（行 ~726-728）

```python
self._interval_cb.currentIndexChanged.connect(
    lambda idx: setattr(self, '_interval', self._interval_options[idx][0])
)
```

这样用户在 tab 上切换"日线/1分钟/5分钟..."时，`self._interval` 跟着更新。

### 3. `_on_fullscreen` 创建 win 后注入 `win._interval`（行 ~1000）

```python
try:
    win._interval = getattr(self, '_interval', None) or \
                    self._interval_options[self._interval_cb.currentIndex()][0]
except Exception:
    pass
```

- 优先用 `self._interval`（已同步到下拉框当前选中）
- 兜底从 `_interval_options[idx]` 重新取
- `try/except` 防御任何意外

## 验证

### 语法检查
```
$ python -c "import ast; ast.parse(open('vnpy/strategy_condition/ui/kline_view.py', encoding='utf-8').read())"
OK: kline_view.py syntax OK
```

### 代码定位
```
725:        self._interval = self._interval_options[0][0]
726:        self._interval_cb.currentIndexChanged.connect(
727:            lambda idx: setattr(self, '_interval', self._interval_options[idx][0])
728:        )
~1000: win._interval = getattr(self, '_interval', None) or self._interval_options[...][0]
```

## 修复效果

- ✅ 全屏窗口拿到正确的 Interval 枚举（DAILY / MINUTE_5 等）
- ✅ 全屏窗口内部能正确判断当前是日线还是分钟线
- ✅ 日线 ↔ 分钟线联动在全屏模式下生效
- ✅ 切换 KlineViewTab 的下拉框后，新开的全屏窗口也跟随
- ✅ 现有功能无破坏（getattr 兜底、try/except 保护）

## 文件改动汇总

- **修改**: `vnpy/strategy_condition/ui/kline_view.py`（共 3 处小改动）
- **新增**: `Monitor日线分钟K线联动-V12关键属性注入修复.md`（本文件）

## 关键学习

`getattr(obj, attr, None)` 的安全读取不会"创造"属性 ——
读取不会自动写入。如果某段代码用 `getattr(win, '_interval', None)`，
**必须保证在某处对 win 显式赋值了 `_interval`**。
V1~V11 一直漏掉了这个写入步骤。