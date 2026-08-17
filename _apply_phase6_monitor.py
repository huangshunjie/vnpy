# -*- coding: utf-8 -*-
"""
Phase 6: Monitor Engine 多周期集成
为 Monitor Engine 添加多周期支持
"""

# Phase 6 核心设计理念：
#
# Monitor Engine 当前架构已经很好地通过代理模式工作：
# 1. 它通过 _make_recording_eval_fn() 包装 ConditionEngine.eval_condition()
# 2. ConditionEngine 已经在 Phase 4 完成了多周期支持
# 3. 因此，Monitor Engine 只需要确保正确传递 MultiTimeframeContext
#
# 由于 Monitor Engine 主要用于"回测后分析"（generate_snapshots在回测完成后调用），
# 而不是实时监控，它的数据来源通常是单一周期的K线（如日线或分钟线）。
#
# 对于多周期策略的监控，需要考虑两种场景：
#
# 场景 A：单数据源监控（当前实现）
# - 传入单一周期K线（如日线）
# - 策略包含不同周期条件（如周线MA）
# - 使用 BarResampler 重采样（Phase 4已支持）
# - 无需修改 Monitor Engine
#
# 场景 B：多数据源监控（Phase 6扩展）
# - 传入多周期数据（通过 MTFCandleBuffer）
# - 生成快照时使用 As-of Time 对齐
# - 需要传递 mtf_buffer 和 execution_interval
#
# 实施策略：
# 1. 为 generate_snapshots() 添加可选的 mtf_buffer 和 execution_interval 参数
# 2. 检测策略是否为多周期（通过 analyze_data_requirements）
# 3. 如果是多周期且提供了 mtf_buffer，使用 MultiTimeframeContext
# 4. 保持向后兼容：不提供这些参数时行为不变

import sys
import os

monitor_engine_file = "vnpy/strategy_condition/monitor/condition_monitor_engine.py"

with open(monitor_engine_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到 generate_snapshots 方法的签名行
signature_idx = None
for i, line in enumerate(lines):
    if 'def generate_snapshots(' in line:
        signature_idx = i
        break

if not signature_idx:
    print(f"未找到 generate_snapshots 方法")
    sys.exit(1)

# 修改签名：添加 mtf_buffer 和 execution_interval 参数
# 找到参数结束的位置（包含 inject_buy_signals 的那一行后面的 ) -> 行）
params_end_idx = None
for i in range(signature_idx, min(signature_idx + 15, len(lines))):
    if 'inject_buy_signals: bool = True,' in lines[i]:
        params_end_idx = i
        break

if params_end_idx:
    # 在 inject_buy_signals 后添加新参数
    old_line = lines[params_end_idx]
    new_line = old_line.rstrip('\n') + '\n' + \
               '        mtf_buffer=None,  # Phase 6: 多周期数据源\n' + \
               '        execution_interval=None,  # Phase 6: 策略执行周期\n'
    lines[params_end_idx] = new_line
    print(f"✓ 已更新 generate_snapshots 签名")
else:
    print(f"✗ 未找到参数结束位置")

# 在方法开头添加多周期检测逻辑
# 找到 """...""" docstring 结束后的第一个实际代码行
docstring_end_idx = None
in_docstring = False
for i in range(signature_idx, min(signature_idx + 30, len(lines))):
    if '"""' in lines[i] and not in_docstring:
        in_docstring = True
    elif '"""' in lines[i] and in_docstring:
        docstring_end_idx = i + 1
        break

if docstring_end_idx:
    # 在 docstring 后插入多周期检测代码
    mtf_check_code = '''        # Phase 6: 多周期策略检测
        is_multi_timeframe = False
        req = None
        if execution_interval is not None:
            from ..core.mtf_context import analyze_data_requirements
            req = analyze_data_requirements(strategy.buy_tree, execution_interval)
            is_multi_timeframe = len(req.intervals) > 1
            if is_multi_timeframe:
                self._log(
                    f"[MonitorEngine] {symbol}: 多周期策略监控 "
                    f"(执行周期={execution_interval.value}, "
                    f"数据周期={[i.value for i in req.intervals]})"
                )
        
'''
    lines.insert(docstring_end_idx, mtf_check_code)
    print(f"✓ 已添加多周期检测逻辑")
else:
    print(f"✗ 未找到 docstring 结束位置")

# 找到 for i in range(start, n): 循环开始的地方
# 在循环内调用 _evaluate_bar 时传递 mtf_context
loop_idx = None
for i in range(signature_idx, min(signature_idx + 150, len(lines))):
    if 'for i in range(start, n):' in lines[i]:
        loop_idx = i
        break

if loop_idx:
    # 在 bars_slice = bars[:i + 1] 后插入 mtf_context 构造代码
    for j in range(loop_idx, min(loop_idx + 20, len(lines))):
        if 'bars_slice = bars[:i + 1]' in lines[j]:
            mtf_context_code = '''            
            # Phase 6: 构造 MultiTimeframeContext（如果需要）
            mtf_context = None
            if is_multi_timeframe and mtf_buffer is not None and req is not None:
                from ..core.mtf_context import MultiTimeframeContext
                eval_time = getattr(bars_slice[-1], 'dt', None)
                mtf_context = MultiTimeframeContext(
                    symbol=symbol,
                    evaluation_time=eval_time
                )
                # 为每个周期设置数据
                for interval in req.intervals:
                    if mtf_buffer:
                        interval_bars = mtf_buffer.get_bars_as_of(
                            symbol, len(bars_slice), interval, eval_time
                        ) if eval_time else mtf_buffer.get(symbol, len(bars_slice), interval)
                        if interval_bars:
                            mtf_context.set_bars(interval, interval_bars)
            
'''
            lines.insert(j + 1, mtf_context_code)
            print(f"✓ 已添加 mtf_context 构造代码")
            break

# 修改 _evaluate_bar 调用，传递 mtf_context
eval_bar_idx = None
for i in range(loop_idx, min(loop_idx + 40, len(lines))):
    if 'snapshot = self._evaluate_bar(' in lines[i]:
        eval_bar_idx = i
        break

if eval_bar_idx:
    # 找到这个调用的结束（pos_ctx）行
    for j in range(eval_bar_idx, min(eval_bar_idx + 5, len(lines))):
        if 'pos_ctx)' in lines[j] or 'pos_ctx,' in lines[j]:
            old_line = lines[j]
            # 替换为传递 mtf_context
            new_line = old_line.replace('pos_ctx)', 'pos_ctx, mtf_context)').replace(
                'pos_ctx,', 'pos_ctx, mtf_context,')
            lines[j] = new_line
            print(f"✓ 已修改 _evaluate_bar 调用")
            break

# 修改 _evaluate_bar 方法签名，添加 mtf_context 参数
eval_bar_def_idx = None
for i, line in enumerate(lines):
    if 'def _evaluate_bar(' in line:
        eval_bar_def_idx = i
        break

if eval_bar_def_idx:
    # 找到 pos_ctx 参数行
    for j in range(eval_bar_def_idx, min(eval_bar_def_idx + 10, len(lines))):
        if 'pos_ctx: Optional[Dict[str, Any]] = None,' in lines[j]:
            old_line = lines[j]
            new_line = old_line.rstrip('\n') + '\n' + \
                       '        mtf_context=None,  # Phase 6: 多周期上下文\n'
            lines[j] = new_line
            print(f"✓ 已修改 _evaluate_bar 签名")
            break

# 在 _evaluate_bar 内部，传递 mtf_context 给 eval_fn
# 找到 buy_eval_fn = self._make_recording_eval_fn(buy_recorder, bars_slice)
buy_eval_fn_idx = None
for i in range(eval_bar_def_idx, min(eval_bar_def_idx + 50, len(lines))):
    if 'buy_eval_fn = self._make_recording_eval_fn(buy_recorder, bars_slice)' in lines[i]:
        buy_eval_fn_idx = i
        break

if buy_eval_fn_idx:
    # 替换为条件判断
    mtf_eval_code = '''        buy_eval_fn = (
            self._make_recording_mtf_eval_fn(buy_recorder, bars_slice, mtf_context)
            if mtf_context
            else self._make_recording_eval_fn(buy_recorder, bars_slice)
        )
'''
    lines[buy_eval_fn_idx] = mtf_eval_code
    print(f"✓ 已修改 buy_eval_fn 构造")

# 在文件末尾添加 _make_recording_mtf_eval_fn 方法
new_method = '''
    def _make_recording_mtf_eval_fn(
        self,
        recorder: Dict[str, ConditionDetail],
        bars_slice: list,
        mtf_context,
    ) -> Callable[[Condition, str, list], Tuple[bool, float]]:
        """
        Phase 6: 创建多周期监控评估函数
        
        与 _make_recording_eval_fn 类似，但使用 MultiTimeframeContext
        """
        original_eval = self._ce.eval_condition
        
        def recording_mtf_eval(cond: Condition, symbol: str, bars: list) -> Tuple[bool, float]:
            # 使用 MultiTimeframeContext 评估
            passed, score = original_eval(
                cond, symbol, bars, _mtf_context=mtf_context
            )
            
            # 记录详情
            current_value = self._extract_current_value(cond, bars_slice)
            threshold_desc = self._format_threshold(cond)
            
            detail = ConditionDetail(
                condition_name=cond.display_name(),
                indicator=cond.indicator.value,
                passed=passed,
                score=score,
                current_value=current_value,
                threshold_desc=threshold_desc,
                params=dict(cond.params),
            )
            recorder[cond.display_name()] = detail
            return passed, score
        
        return recording_mtf_eval
'''

# 在最后一行（return lifecycles）之后添加新方法
lines.append(new_method)
print(f"✓ 已添加 _make_recording_mtf_eval_fn 方法")

# 写回文件
with open(monitor_engine_file, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"\nPhase 6 Monitor Engine 多周期集成完成！")
print(f"主要变更：")
print(f"  1. generate_snapshots() 新增 mtf_buffer, execution_interval 参数")
print(f"  2. 自动检测多周期策略")
print(f"  3. 构造 MultiTimeframeContext 并传递")
print(f"  4. 新增 _make_recording_mtf_eval_fn() 方法")
print(f"\n向后兼容：不提供新参数时行为完全不变")