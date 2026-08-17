# K线形态回测 Bug 修复报告

**日期**: 2026-08-16  
**状态**: ✅ 已完成  
**影响**: 关键 - 阻止所有使用K线形态条件的策略回测

---

## 问题描述

用户使用「阳线」（KLINE_YANG）条件创建策略并进行回测时，回测无结果（0 信号），即使测试数据中有 50 根阳线K线。

### 症状

```
[5] 执行回测...
[ConditionEngine] KLINE_YANG: The truth value of an array with more than one element is ambiguous...
[ScanEngine] backtest test_yang: 1 股 → 0 信号 (0.00s)
  信号数量: 0
  ❌ 回测无结果！
```

---

## 根因分析

通过系统诊断发现**五个连锁 bug**：

### Bug 1: ConditionEngine 缺少 K线形态指标路由

**文件**: `vnpy/strategy_condition/engine/condition_engine.py`

K线形态指标（KLINE_YANG, KLINE_YIN 等）在 `eval_condition()` 中没有对应的路由分支，导致这些条件永远返回 `(False, 0.0)`。

**修复**: 在 `eval_condition()` 中添加 K线形态的处理分支

```python
# ── K线形态（单根） ──
if ind == CI.KLINE_YANG:
    opens = [b.open for b in bars]
    return check_kline_yang(closes, opens)
if ind == CI.KLINE_YIN:
    opens = [b.open for b in bars]
    return check_kline_yin(closes, opens)
# ... 其他K线形态
```

### Bug 2: kline_patterns 函数不兼容 numpy 数组

**文件**: `vnpy/strategy_condition/indicators/kline_patterns.py`

函数使用 `if not closes or not opens:` 检查空值，但当传入 numpy 数组时，`not array` 会抛出异常：

```
ValueError: The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()
```

**修复**: 改用 `len()` 检查，并显式转换比较结果为 bool

```python
def check_kline_yang(closes, opens) -> Tuple[bool, float]:
    """当日阳线: close > open"""
    if len(closes) == 0 or len(opens) == 0:
        return False, 0.0
    passed = bool(closes[-1] > opens[-1])  # 显式转换
    return passed, 1.0 if passed else 0.0
```

### Bug 3: 空 OR 节点错误返回 True

**文件**: `vnpy/strategy_condition/core/condition_tree.py`

空的卖出树（OR 节点）在评估时返回 `(True, 1.0)`，触发"同日冲突检查"，导致所有买入信号被拦截。

**逻辑错误**:
- 空的 OR 节点应该返回 False（没有满足的条件）
- 空的 AND 节点应该返回 True（没有约束）

**修复**: 根据节点类型返回正确的默认值

```python
if not self.children:
    # 空节点的返回值取决于操作类型：
    # - AND: 没有约束 → True（空集的 AND 为真）
    # - OR: 没有满足的条件 → False（空集的 OR 为假）
    if self.op == NodeOp.AND:
        return True, 1.0
    else:
        return False, 0.0
```

### Bug 4: condition_engine 未从 precomputed 提取 opens

**文件**: `vnpy/strategy_condition/engine/condition_engine.py`

`eval_condition()` 第 93-102 行在提取预计算数据时，只提取了 `closes/highs/lows/volumes`，遗漏了 `opens`，导致 K线形态函数调用时 opens 仍然从 bars 提取（list），与 closes（numpy array）类型不匹配。

**修复**: 在 `_precomputed` 分支中也提取 opens

```python
if _precomputed:
    closes = _precomputed["closes"]
    opens = _precomputed.get("opens")  # 新增
    highs = _precomputed["highs"]
    lows = _precomputed["lows"]
    volumes = _precomputed["volumes"]
```

### Bug 5: scan_engine 预计算缺少 opens 字段

**文件**: `vnpy/strategy_condition/engine/scan_engine.py`

`_make_precomputed()` 函数构造的预计算字典缺少 `opens` 字段，导致 K线形态条件无法从预计算中获取开盘价数据。

**修复**: 添加 `_all_opens` 数组和对应字段

```python
_all_opens = np.array([b.open for b in all_bars], dtype=np.float64)

def _make_precomputed(end: int) -> dict:
    return {
        "closes": _all_closes[:end],
        "opens": _all_opens[:end],      # 新增
        "highs": _all_highs[:end],
        "lows": _all_lows[:end],
        "volumes": _all_volumes[:end],
    }
```

---

## 验证结果

### 修复前
```
[ScanEngine] backtest test_yang: 1 股 → 0 信号
```

### 修复后
```
[ScanEngine] backtest test_yang: 1 股 → 1 信号 (0.00s)
  信号数量: 1
  ✓ 回测成功！
    - TEST001 @ 2024-02-20 00:00:00 price=105.00 score=1.00
```

---

## 修改文件清单

1. ✅ `vnpy/strategy_condition/engine/condition_engine.py` - 添加 K线形态路由 + 从 precomputed 提取 opens
2. ✅ `vnpy/strategy_condition/indicators/kline_patterns.py` - numpy 兼容性修复
3. ✅ `vnpy/strategy_condition/core/condition_tree.py` - 修复空节点逻辑
4. ✅ `vnpy/strategy_condition/engine/scan_engine.py` - 添加 opens 预计算

---

## 影响范围

**受益的功能**:
- 所有使用 K线形态条件的策略回测
- 实时监控中的 K线形态条件
- UI 条件编辑器中的 K线形态选项

**不影响**:
- 其他类型的技术指标（趋势、强度、偏离等）
- 多周期架构（Phase 4-8）

---

## 后续建议

1. **单元测试覆盖**: 为 K线形态指标添加完整的单元测试
2. **集成测试**: 增加端到端回测测试用例
3. **代码审查**: 检查其他指标函数是否也存在 numpy 兼容性问题
4. **文档更新**: 在开发文档中说明预计算字典的标准结构

---

## 测试脚本

诊断脚本已保存为 `_diagnose_backtest_e2e.py`，可用于回归测试：

```bash
python -X utf8 _diagnose_backtest_e2e.py
```

预期输出应包含 `✓ 回测成功！` 和至少 1 个信号。

### 真实场景测试

测试脚本 `_diagnose_real_scenario.py` 模拟用户实际策略（阳线 + 止损-8% + data_interval='d'）：

```bash
python -X utf8 _diagnose_real_scenario.py
```

成功输出：
```
[8] 执行回测:
[ScanEngine] backtest test_yang_real: 1 股 → 3 信号 (0.00s)
    信号数量: 3
    ✓ 回测成功！
      TEST001 @ 2020-03-05 price=10.74 exit=13.37 pnl=24.34% reason=max_hold
      TEST001 @ 2020-05-08 price=13.86 exit=18.86 pnl=35.93% reason=max_hold
      TEST001 @ 2020-07-11 price=19.11 exit=20.29 pnl=6.02% reason=max_hold
```
