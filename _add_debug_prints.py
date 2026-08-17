#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
在 widget.py 回测逻辑中添加调试打印
"""

def add_debug_prints():
    filepath = 'vnpy/strategy_condition/ui/widget.py'
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在 analyze_strategy_data_requirements 调用后添加打印
    old_code = '''            req = analyze_strategy_data_requirements(
                self._strategy, anchor_interval, n_bars
            )
            
            # 使用自动确定的执行周期
            execution_interval = req.execution_interval'''
    
    new_code = '''            req = analyze_strategy_data_requirements(
                self._strategy, anchor_interval, n_bars
            )
            
            # === DEBUG: 打印周期信息 ===
            print(f"[DEBUG] req.required_intervals: {req.required_intervals}")
            print(f"[DEBUG] req.anchor_interval: {req.anchor_interval}")
            print(f"[DEBUG] req.execution_interval: {req.execution_interval}")
            if hasattr(self._strategy, 'buy_tree'):
                print(f"[DEBUG] buy_tree type: {type(self._strategy.buy_tree)}")
                if hasattr(self._strategy.buy_tree, 'children'):
                    for i, child in enumerate(self._strategy.buy_tree.children):
                        print(f"[DEBUG] buy_tree.children[{i}]: {child}")
                        if hasattr(child, 'condition'):
                            print(f"[DEBUG]   condition: {child.condition}")
                            if hasattr(child.condition, 'data_interval'):
                                print(f"[DEBUG]   data_interval: {child.condition.data_interval}")
            # === END DEBUG ===
            
            # 使用自动确定的执行周期
            execution_interval = req.execution_interval'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✓ Debug prints added to widget.py")
        return True
    else:
        print("✗ Target code not found")
        return False

if __name__ == '__main__':
    add_debug_prints()