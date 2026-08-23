"""
手动添加 _on_mouse_clicked 方法到 KlineChartWidget
"""

def apply_fix():
    kline_view_path = "vnpy/strategy_condition/ui/kline_view.py"
    
    with open(kline_view_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 查找 _on_mouse_moved 方法的结束位置
    insert_line = None
    for i, line in enumerate(lines):
        if line.strip().startswith('def _update_info(self, idx: int)'):
            insert_line = i
            break
    
    if insert_line is None:
        print("[ERROR] 未找到 _update_info 方法")
        return False
    
    # 在 _update_info 之前插入 _on_mouse_clicked 方法
    click_handler = '''    def _on_mouse_clicked(self, evt):
        """鼠标点击时发射bar_clicked信号"""
        if not self._dates:
            return
        pos = evt.scenePos()
        if self._main_plot.sceneBoundingRect().contains(pos):
            mouse_point = self._main_plot.vb.mapSceneToView(pos)
            idx = int(mouse_point.x() + 0.5)
            if 0 <= idx < len(self._datetimes):
                clicked_date = self._datetimes[idx]
                self.bar_clicked.emit(clicked_date)

'''
    
    lines.insert(insert_line, click_handler)
    
    with open(kline_view_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"[OK] 已在第 {insert_line} 行插入 _on_mouse_clicked 方法")
    print(f"[OK] 保存到 {kline_view_path}")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("添加 _on_mouse_clicked 方法到 KlineChartWidget")
    print("=" * 60)
    
    success = apply_fix()
    
    if success:
        print("\n[SUCCESS] 日线点击联动功能修复完成!")
        print("\n现在可以：")
        print("1. 重新启动程序")
        print("2. 执行回测并切换到 Monitor Tab")
        print("3. 点击日线K线，分钟K线会自动聚焦到对应日期")
    else:
        print("\n[FAILED] 修复失败")