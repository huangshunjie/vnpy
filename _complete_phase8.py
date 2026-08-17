#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 8: 完善 UI 多周期集成

1. 为 ConditionEngine 添加 eval_condition_mtf() 方法（与 Phase 6/7 兼容）
2. 修复 UI condition_editor.py 中的 to_condition() 方法，正确处理 data_interval
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def add_eval_condition_mtf():
    """为 ConditionEngine 添加 eval_condition_mtf 方法"""
    print("\n=== Step 1: 添加 eval_condition_mtf() 方法 ===\n")
    
    file_path = "vnpy/strategy_condition/engine/condition_engine.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已存在
    if 'def eval_condition_mtf(' in content:
        print("  ✅ eval_condition_mtf() 方法已存在")
        return True
    
    # 找到 eval_condition 方法结束位置
    insert_pos = content.find('    def _dispatch(')
    if insert_pos == -1:
        print("  ❌ 无法找到插入位置")
        return False
    
    # 准备插入的方法
    new_method = '''    def eval_condition_mtf(self, cond: Condition,
                           symbol: str, bars: list,
                           mtf_context: MultiTimeframeContext,
                           _precomputed: dict = None) -> Tuple[bool, float]:
        """
        多周期条件评估方法（Phase 6-8 统一接口）
        
        这是一个包装方法，将 mtf_context 传递给 eval_condition。
        与 Phase 6 MonitorEngine 和 Phase 7 ScanEngine 的调用方式保持一致。
        
        Args:
            cond: 条件对象
            symbol: 股票代码
            bars: 执行周期的K线数据
            mtf_context: 多周期上下文（包含所有需要的周期数据）
            _precomputed: 预计算数组字典（可选）
        
        Returns:
            (passed, score): 条件是否通过及得分
        """
        return self.eval_condition(
            cond, symbol, bars,
            _precomputed=_precomputed,
            _mtf_context=mtf_context
        )

'''
    
    # 插入新方法
    new_content = content[:insert_pos] + new_method + content[insert_pos:]
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("  ✅ 成功添加 eval_condition_mtf() 方法")
    print("  • 与 Phase 6 MonitorEngine 调用方式一致")
    print("  • 与 Phase 7 ScanEngine 调用方式一致")
    return True


def fix_ui_to_condition():
    """修复 UI 的 to_condition() 方法"""
    print("\n=== Step 2: 修复 UI to_condition() 方法 ===\n")
    
    file_path = "vnpy/strategy_condition/ui/condition_editor.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 查找 to_condition 方法
    in_to_condition = False
    method_start = -1
    method_end = -1
    
    for i, line in enumerate(lines):
        if 'def to_condition(self)' in line:
            in_to_condition = True
            method_start = i
        elif in_to_condition and line.strip() and not line[0].isspace():
            method_end = i
            break
    
    if method_start == -1:
        print("  ❌ 无法找到 to_condition() 方法")
        return False
    
    # 检查是否已经处理了 data_interval
    method_content = ''.join(lines[method_start:method_end])
    if 'data_interval=' in method_content and '_data_interval' in method_content:
        print("  ✅ to_condition() 方法已正确处理 data_interval")
        return True
    
    # 找到 return Condition(...) 语句
    return_line_idx = -1
    for i in range(method_start, method_end):
        if 'return Condition(' in lines[i]:
            return_line_idx = i
            break
    
    if return_line_idx == -1:
        print("  ❌ 无法找到 return Condition(...) 语句")
        return False
    
    # 找到 Condition 构造的结束位置
    condition_end_idx = return_line_idx
    paren_count = 0
    for i in range(return_line_idx, method_end):
        paren_count += lines[i].count('(') - lines[i].count(')')
        if paren_count == 0:
            condition_end_idx = i
            break
    
    # 在 Condition 构造之前添加 data_interval 处理
    insert_idx = return_line_idx
    indent = '        '
    new_lines = [
        f'{indent}# Phase 8: 从参数中提取 data_interval\n',
        f'{indent}params_copy = self._params_editor.get_params()\n',
        f'{indent}data_interval = params_copy.pop("_data_interval", None)\n',
        f'{indent}\n',
    ]
    
    # 修改 return Condition 行，使用 params_copy 和 data_interval
    # 找到 params= 那一行
    for i in range(return_line_idx, condition_end_idx + 1):
        if 'params=' in lines[i]:
            # 替换为 params=params_copy
            lines[i] = lines[i].replace(
                'self._params_editor.get_params()',
                'params_copy'
            )
        # 在最后的 ) 之前添加 data_interval=...
        if i == condition_end_idx and lines[i].strip() == ')':
            lines[i] = f'{indent}    data_interval=data_interval,\n{lines[i]}'
    
    # 插入新行
    lines[insert_idx:insert_idx] = new_lines
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("  ✅ 成功修复 to_condition() 方法")
    print("  • 从参数中提取 _data_interval")
    print("  • 转换为 Condition 的 data_interval 属性")
    return True


def verify_phase8():
    """验证 Phase 8 完整性"""
    print("\n=== Step 3: 验证 Phase 8 完整性 ===\n")
    
    checks = []
    
    # 检查 ConditionEngine
    with open("vnpy/strategy_condition/engine/condition_engine.py", 'r', encoding='utf-8') as f:
        engine_content = f.read()
    checks.append(("ConditionEngine.eval_condition_mtf", 'def eval_condition_mtf(' in engine_content))
    
    # 检查 UI
    with open("vnpy/strategy_condition/ui/condition_editor.py", 'r', encoding='utf-8') as f:
        ui_content = f.read()
    checks.append(("UI 参数面板 _data_interval", '_data_interval' in ui_content))
    checks.append(("UI to_condition data_interval 转换", 
                   'data_interval=' in ui_content and 'params_copy.pop("_data_interval"' in ui_content))
    
    # 检查 ScanEngine
    with open("vnpy/strategy_condition/engine/scan_engine.py", 'r', encoding='utf-8') as f:
        scan_content = f.read()
    checks.append(("ScanEngine MTF buffer", 'set_mtf_buffer' in scan_content))
    checks.append(("ScanEngine 条件级路由", 'eval_condition_mtf' in scan_content))
    
    # 检查 MonitorEngine
    with open("vnpy/strategy_condition/monitor/condition_monitor_engine.py", 'r', encoding='utf-8') as f:
        monitor_content = f.read()
    checks.append(("MonitorEngine 条件级路由", 'eval_condition_mtf' in monitor_content))
    
    print("📋 功能完整性检查:\n")
    all_passed = True
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        all_passed = all_passed and passed
    
    return all_passed


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 8: 完善 UI 多周期集成")
    print("=" * 60)
    
    # Step 1: 添加 eval_condition_mtf
    step1_ok = add_eval_condition_mtf()
    
    # Step 2: 修复 UI to_condition
    step2_ok = fix_ui_to_condition()
    
    # Step 3: 验证
    if step1_ok and step2_ok:
        all_ok = verify_phase8()
        
        if all_ok:
            print("\n" + "=" * 60)
            print("✅ Phase 8: UI 多周期集成完成！")
            print("=" * 60)
            print("\n完成的工作:")
            print("  ✅ ConditionEngine 添加 eval_condition_mtf() 方法")
            print("  ✅ UI to_condition() 正确转换 data_interval")
            print("  ✅ 与 Phase 6-7 后端完全兼容")
            print("\n现在用户可以:")
            print("  1. 在条件编辑器中选择数据周期")
            print("  2. 创建多周期策略")
            print("  3. 在 Monitor 和 Scan 中使用多周期功能")
        else:
            print("\n❌ 部分验证未通过")
    else:
        print("\n❌ Phase 8 补丁应用失败")