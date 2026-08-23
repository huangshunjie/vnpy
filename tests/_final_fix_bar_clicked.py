"""
最终修复：直接在KlineChartWidget类添加bar_clicked信号和点击处理
"""
import re

def apply_fix():
    kline_view_path = "vnpy/strategy_condition/ui/kline_view.py"
    
    with open(kline_view_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 在类定义后添加bar_clicked信号
    class_def_pattern = r'(class KlineChartWidget\(QtWidgets\.QWidget\):\s*\n\s*"""[^"]*""")'
    signal_code = r'\1\n\n    # 信号：当用户点击K线时发射，参数为点击的日期(datetime)\n    bar_clicked = QtCore.Signal(object)'
    
    if 'bar_clicked = QtCore.Signal(object)' not in content:
        content = re.sub(class_def_pattern, signal_code, content)
        print("[OK] 添加了 bar_clicked 信号定义")
    else:
        print("[SKIP] bar_clicked 信号已存在")
    
    # 2. 在_build_ui方法中连接点击信号
    build_ui_pattern = r'(# Connect mouse click for measure tool and bar selection\s*\n\s*self\._main_plot\.scene\(\)\.sigMouseClicked\.connect\(self\._on_mouse_clicked\))'
    
    if 'self._main_plot.scene().sigMouseClicked.connect(self._on_mouse_clicked)' not in content:
        # 找到self._main_plot.scene().sigMouseMoved.connect的位置
        mouse_moved_pattern = r'(self\._main_plot\.scene\(\)\.sigMouseMoved\.connect\(self\._on_mouse_moved\))'
        connect_code = r'\1\n        # Connect mouse click for measure tool and bar selection\n        self._main_plot.scene().sigMouseClicked.connect(self._on_mouse_clicked)'
        content = re.sub(mouse_moved_pattern, connect_code, content)
        print("[OK] 添加了 sigMouseClicked 信号连接")
    else:
        print("[SKIP] sigMouseClicked 连接已存在")
    
    # 3. 在_on_mouse_moved方法后添加_on_mouse_clicked方法
    if 'def _on_mouse_clicked(self, evt):' not in content:
        # 找到_on_mouse_moved方法的结束位置
        mouse_moved_method_pattern = r'(def _on_mouse_moved\(self, evt\):.*?(?=\n    def |\n\nclass |\Z))'
        
        click_method = '''
    def _on_mouse_clicked(self, evt):
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
        
        # 在_on_mouse_moved方法后插入
        content = re.sub(
            r'(def _on_mouse_moved\(self, evt\):.*?\n        self\._update_info_bar.*?\n\n)',
            r'\1' + click_method,
            content,
            flags=re.DOTALL
        )
        print("[OK] 添加了 _on_mouse_clicked 方法")
    else:
        print("[SKIP] _on_mouse_clicked 方法已存在")
    
    # 保存文件
    with open(kline_view_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n[SUCCESS] 文件已保存: {kline_view_path}")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("最终修复：添加日线点击联动功能")
    print("=" * 60)
    
    success = apply_fix()
    
    if success:
        print("\n修复完成！请执行以下操作：")
        print("1. 再次清理Python缓存：python tests\\_clean_pycache_and_restart.py")
        print("2. 关闭vnpy程序")
        print("3. 重新启动vnpy程序")
        print("4. 测试日线点击联动功能")
    else:
        print("\n[FAILED] 修复失败")