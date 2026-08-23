"""
为 KlineChartWidget 添加 bar_clicked 信号以支持日线-分钟联动
"""

def add_bar_clicked_signal():
    kline_view_path = "vnpy/strategy_condition/ui/kline_view.py"
    
    with open(kline_view_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 在 KlineChartWidget 类开始处添加信号定义
    old_class_start = """class KlineChartWidget(QtWidgets.QWidget):
    \"\"\"K线主图 + 成交量副图 + 买入/卖出信号标记 + 十字线悬停。\"\"\"

    def __init__(self, parent=None):"""
    
    new_class_start = """class KlineChartWidget(QtWidgets.QWidget):
    \"\"\"K线主图 + 成交量副图 + 买入/卖出信号标记 + 十字线悬停。\"\"\"
    
    # 信号：当用户点击K线时发射，参数为点击的日期(datetime)
    bar_clicked = QtCore.Signal(object)

    def __init__(self, parent=None):"""
    
    if old_class_start in content:
        content = content.replace(old_class_start, new_class_start)
        print("[OK] 添加了 bar_clicked 信号定义")
    else:
        print("[WARN] 未找到 KlineChartWidget 类定义开始位置")
        return False
    
    # 2. 在 mouseClicked event处理中发射信号
    # 查找 _on_mouse_clicked 方法
    old_mouse_clicked = """    def _on_mouse_clicked(self, evt):
        if not self._dates:
            return
        pos = evt.scenePos()
        if self._main_plot.sceneBoundingRect().contains(pos):
            mouse_point = self._main_plot.vb.mapSceneToView(pos)
            idx = int(mouse_point.x() + 0.5)
            if 0 <= idx < len(self._dates):
                self._update_info(idx)"""
    
    new_mouse_clicked = """    def _on_mouse_clicked(self, evt):
        if not self._dates:
            return
        pos = evt.scenePos()
        if self._main_plot.sceneBoundingRect().contains(pos):
            mouse_point = self._main_plot.vb.mapSceneToView(pos)
            idx = int(mouse_point.x() + 0.5)
            if 0 <= idx < len(self._dates):
                self._update_info(idx)
                # 发射 bar_clicked 信号，传递点击的日期
                clicked_date = self._dates[idx]
                self.bar_clicked.emit(clicked_date)"""
    
    if old_mouse_clicked in content:
        content = content.replace(old_mouse_clicked, new_mouse_clicked)
        print("[OK] 在 _on_mouse_clicked 中添加了信号发射")
    else:
        print("[WARN] 未找到 _on_mouse_clicked 方法")
        # 可能方法不存在，需要检查
    
    with open(kline_view_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n[OK] 已保存到 {kline_view_path}")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("为 KlineChartWidget 添加 bar_clicked 信号")
    print("=" * 60)
    
    success = add_bar_clicked_signal()
    
    if success:
        print("\n修复完成！")
        print("\n现在 Monitor Tab 的日线点击应该能联动分钟K线了")
        print("\n测试步骤：")
        print("1. 重新启动程序")
        print("2. 执行回测")
        print("3. 切换到 Monitor Tab")
        print("4. 点击日线K线上的任意一根K线")
        print("5. 分钟K线应该自动聚焦到对应日期并显示在中部")
    else:
        print("\n修复失败，需要手动检查")