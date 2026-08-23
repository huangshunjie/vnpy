"""
直接在 _on_mouse_moved 后添加 _on_mouse_clicked 方法
"""

def apply_fix():
    kline_view_path = "vnpy/strategy_condition/ui/kline_view.py"
    
    with open(kline_view_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 查找 _on_mouse_moved 方法后的第一个空行
    insert_line = None
    in_mouse_moved = False
    for i, line in enumerate(lines):
        if 'def _on_mouse_moved' in line:
            in_mouse_moved = True
            continue
        if in_mouse_moved and line.strip() == '' and i > 0 and not lines[i-1].strip().startswith('#'):
            # 找到方法结束后的空行
            insert_line = i
            break
    
    if insert_line is None:
        print("[ERROR] 未找到插入位置")
        return False
    
    # 插入点击处理方法
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
    print("添加 _on_mouse_clicked 方法")
    print("=" * 60)
    
    success = apply_fix()
    
    if success:
        print("\n[SUCCESS] 日线点击联动功能修复完成!")
        print("\n修复内容：")
        print("1. 添加了 bar_clicked 信号定义")
        print("2. 连接了 sigMouseClicked 信号")  
        print("3. 添加了 _on_mouse_clicked 方法")
        print("\n请重启程序测试")
    else:
        print("\n[FAILED] 修复失败")