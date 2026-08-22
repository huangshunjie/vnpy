"""
修复Monitor全屏模式下分钟K线不显示买入信号的问题

问题：
- Monitor点击日线联动加载分钟数据时，直接调用 _chart.load()
- 这绕过了 KlineViewTab.show_symbol 中的全屏同步逻辑（961-967行）
- 导致已打开的全屏窗口不会更新信号标记

解决：
- 在 _PeriodMonitorPanel.load_snapshots 中，数据加载后检查是否有全屏窗口
- 如果有，手动同步 buy_triggers 和 sell_triggers 到全屏窗口并重绘
"""

def fix_fullscreen_minute_signal():
    file_path = "vnpy/strategy_condition/ui/condition_monitor_widget.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在 load_snapshots 方法中 _chart.load() 调用后，添加全屏窗口同步逻辑
    # 找到：self._kline_tab._chart.load(bars, buy_indices=buy_indices, sell_indices=sell_indices)
    # 之后插入全屏同步代码
    
    search_pattern = '''            self._kline_tab._chart.load(bars,
                                        buy_indices=buy_indices,
                                        sell_indices=sell_indices)'''
    
    sync_code = '''
            
            # 同步信号到已打开的全屏窗口
            fs_win = getattr(self._kline_tab, '_fullscreen_window', None)
            if fs_win and hasattr(fs_win, '_chart'):
                fs_win._chart._buy_triggers = self._kline_tab._chart._buy_triggers
                fs_win._chart._sell_triggers = self._kline_tab._chart._sell_triggers
                fs_win._chart._redraw()'''
    
    if search_pattern in content and sync_code not in content:
        content = content.replace(search_pattern, search_pattern + sync_code)
        print("✓ 添加全屏窗口信号同步逻辑")
    elif sync_code in content:
        print("✓ 全屏窗口信号同步逻辑已存在")
    else:
        print("✗ 未找到插入位置")
        return False
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✓ 修复完成：{file_path}")
    return True

if __name__ == "__main__":
    try:
        if fix_fullscreen_minute_signal():
            print("\n验证语法...")
            import ast
            with open("vnpy/strategy_condition/ui/condition_monitor_widget.py", 'r', encoding='utf-8') as f:
                ast.parse(f.read())
            print("✓ 语法正确")
            
            print("\n修复说明：")
            print("- Monitor分钟面板加载数据后，自动同步信号到已打开的全屏窗口")
            print("- 全屏模式下点击日线K线联动时，分钟图会正确显示买入信号")
            print("\n测试步骤：")
            print("1. 打开Monitor，加载某策略扫描结果")
            print("2. 点击分钟面板的全屏按钮")
            print("3. 在日线面板点击有买入信号的K线")
            print("4. 观察全屏分钟图是否显示绿色三角形买入信号")
    except SyntaxError as e:
        print(f"\n✗ 语法错误: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n✗ 修复失败: {e}")
        import traceback
        traceback.print_exc()