"""
完整修复strategy_dialogs.py中的StrategyPerformanceDialog
"""

import os

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"
file_path = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "ui", "strategy_dialogs.py")

print("=" * 80)
print("修复StrategyPerformanceDialog的SpinBox变量定义")
print("=" * 80)

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到SpinBox变量定义的起始位置
# 查找包含 "self._annual_spin" 的行
start_idx = None
for i, line in enumerate(lines):
    if 'self._annual_spin' in line and i > 240:
        start_idx = i
        break

if start_idx:
    print(f"[找到] SpinBox定义起始位置: 第{start_idx+1}行")
    
    # 替换这几行代码
    # 需要确保所有8个SpinBox变量都正确定义
    correct_code = """        self._annual_spin   = _pct()
        self._dd_spin       = _pct(-1.0, 0.01)
        self._dd_spin.setValue(0.0)
        self._sharpe_spin   = _ratio()
        self._sortino_spin  = _ratio()
        self._calmar_spin   = _ratio()
        self._winrate_spin  = _pct(0.0, 1.0)
        self._turnover_spin = _ratio(0.0, 100.0)
        self._pf_spin       = _ratio(0.0, 20.0)

"""
    
    # 找到form.addRow的位置
    form_idx = None
    for i in range(start_idx, min(start_idx + 20, len(lines))):
        if 'form.addRow' in lines[i]:
            form_idx = i
            break
    
    if form_idx:
        print(f"[找到] form.addRow位置: 第{form_idx+1}行")
        
        # 删除start_idx到form_idx之间的所有行
        del lines[start_idx:form_idx]
        
        # 在start_idx位置插入正确的代码
        lines.insert(start_idx, correct_code)
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print("[完成] 已修复所有SpinBox变量定义")
        print("\n修复的变量:")
        print("  1. self._annual_spin   = _pct()")
        print("  2. self._dd_spin       = _pct(-1.0, 0.01)")
        print("  3. self._dd_spin.setValue(0.0)")
        print("  4. self._sharpe_spin   = _ratio()")
        print("  5. self._sortino_spin  = _ratio()")
        print("  6. self._calmar_spin   = _ratio()")
        print("  7. self._winrate_spin  = _pct(0.0, 1.0)")
        print("  8. self._turnover_spin = _ratio(0.0, 100.0)")
        print("  9. self._pf_spin       = _ratio(0.0, 20.0)")
    else:
        print("[错误] 未找到form.addRow位置")
else:
    print("[错误] 未找到SpinBox定义起始位置")

print("\n" + "=" * 80)
print("修复完成！现在重启VN Trader应该可以正常打开录入绩效对话框了！")
print("=" * 80)
