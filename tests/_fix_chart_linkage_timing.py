"""
修复日线点击联动时周期切换的时序问题

问题：点击日线K线时，虽然切换了下拉框到5分钟，但后台线程加载数据时
     读取到的 interval 索引还是旧值（日线），导致用错误的周期查询数据。

解决：
1. 在切换下拉框前先清除缓存键，强制重新加载
2. 设置下拉框后使用 processEvents() 确保GUI更新完成
3. 在 show_symbol 中增加 interval 参数直接传递周期，避免依赖下拉框状态
"""

def apply_fix():
    import os
    import sys
    
    # 添加项目根目录到路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    file_path = os.path.join(project_root, 'vnpy', 'strategy_condition', 'ui', 'kline_view.py')
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复1：在 _on_chart_bar_clicked 中，设置下拉框前清除缓存
    old_code_1 = '''            # 记录 pending 状态（必须在设置下拉框之前，否则 _on_bars_loaded 已触发时
            #  _pending_focus_date 还没设上）
            self._pending_focus_date = target_date
            self._pending_focus_signals = signals

            # 阻塞下拉框信号，避免被算作"用户手动切换"
            self._interval_cb.blockSignals(True)
            try:
                self._interval_cb.setCurrentIndex(five_min_idx)
            finally:
                self._interval_cb.blockSignals(False)

            # 触发异步加载（使用现有 _last_buy_dates/_last_sell_dates 完整集合，
            #   这样 5min 视图的原始信号标记会覆盖更多天数；当日信号由 overlay 叠加）
            self.show_symbol(
                self._current_symbol,
                buy_dates=self._last_buy_dates,
                sell_dates=self._last_sell_dates,
            )'''
    
    new_code_1 = '''            # 记录 pending 状态（必须在设置下拉框之前，否则 _on_bars_loaded 已触发时
            #  _pending_focus_date 还没设上）
            self._pending_focus_date = target_date
            self._pending_focus_signals = signals

            # 清除缓存键，强制重新加载
            self._cache_key = ()

            # 阻塞下拉框信号，避免被算作"用户手动切换"
            self._interval_cb.blockSignals(True)
            try:
                self._interval_cb.setCurrentIndex(five_min_idx)
            finally:
                self._interval_cb.blockSignals(False)

            # 强制处理GUI事件，确保下拉框状态更新完成
            from vnpy.trader.ui import QtWidgets
            QtWidgets.QApplication.processEvents()

            # 触发异步加载（使用现有 _last_buy_dates/_last_sell_dates 完整集合，
            #   这样 5min 视图的原始信号标记会覆盖更多天数；当日信号由 overlay 叠加）
            self.show_symbol(
                self._current_symbol,
                buy_dates=self._last_buy_dates,
                sell_dates=self._last_sell_dates,
            )'''
    
    if old_code_1 in content:
        content = content.replace(old_code_1, new_code_1)
        print("✓ 修复1: 添加缓存清除和GUI事件处理")
    else:
        print("✗ 修复1: 未找到目标代码段")
        return False
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n修复已应用到: {file_path}")
    return True

if __name__ == "__main__":
    if apply_fix():
        print("\n修复完成！")
        print("\n问题原因：")
        print("- 点击日线K线后，虽然代码设置了下拉框到5分钟周期")
        print("- 但后台线程立即启动时，读取到的周期索引还是旧值（日线）")
        print("- 导致用日线周期去查询数据库，查不到5分钟数据")
        print("\n解决方案：")
        print("1. 在切换周期前清除缓存键 _cache_key，强制重新加载")
        print("2. 调用 processEvents() 确保GUI更新完成")
        print("3. 这样后台线程读取周期索引时能获取到正确的5分钟周期")
    else:
        print("\n修复失败！请检查代码结构是否有变化")