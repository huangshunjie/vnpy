"""
为 KlineChartWidget 添加 bar_clicked 信号以支持日线-分钟联动

实现方案：
1. 添加 bar_clicked 信号定义
2. 连接 scene.sigMouseClicked 信号
3. 在点击处理中发射bar_clicked信号
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
    
    # 2. 在 _build_ui 方法中连接鼠标点击信号（在已有的sigMouseMoved连接后面）
    old_proxy_setup = """        self._proxy = pg.SignalProxy(
            self._main_plot.scene().sigMouseMoved,
            rateLimit=60, slot=self._on_mouse_moved)

        # Connect mouse click for measure tool"""
    
    new_proxy_setup = """        self._proxy = pg.SignalProxy(
            self._main_plot.scene().sigMouseMoved,
            rateLimit=60, slot=self._on_mouse_moved)

        # Connect mouse click for measure tool and bar selection
        self._main_plot.scene().sigMouseClicked.connect(self._on_mouse_clicked)"""
    
    if old_proxy_setup in content:
        content = content.replace(old_proxy_setup, new_proxy_setup)
        print("[OK] 连接了 sigMouseClicked 信号")
    else:
        print("[WARN] 未找到 proxy setup 代码")
        # 尝试备选方案
        old_comment = "        # Connect mouse click for measure tool"
        if old_comment in content:
            new_comment = """        # Connect mouse click for measure tool and bar selection
        self._main_plot.scene().sigMouseClicked.connect(self._on_mouse_clicked)"""
            content = content.replace(old_comment, new_comment)
            print("[OK] 使用备选方案连接了 sigMouseClicked 信号")
    
    # 3. 添加 _on_mouse_clicked 方法（在 _on_mouse_moved 方法后面）
    # 先找到 _on_mouse_moved 方法的结束位置
    search_pattern = """    def _on_mouse_moved(self, args):
        \"\"\"鼠标移动时更新十字线和信息栏。\"\"\"
        if not self._dates:
            return
        pos = args[0]
        if self._main_plot.sceneBoundingRect().contains(pos):
            mouse_point = self._main_plot.vb.mapSceneToView(pos)
            idx = int(mouse_point.x() + 0.5)
            if 0 <= idx < len(self._dates):
                self._update_info(idx)
                self._vline.setPos(idx)
                self._hline.setPos(mouse_point.y())

    def _update_info(self, idx: int) -> None:"""
    
    new_with_click_handler = """    def _on_mouse_moved(self, args):
        \"\"\"鼠标移动时更新十字线和信息栏。\"\"\"
        if not self._dates:
            return
        pos = args[0]
        if self._main_plot.sceneBoundingRect().contains(pos):
            mouse_point = self._main_plot.vb.mapSceneToView(pos)
            idx = int(mouse_point.x() + 0.5)
            if 0 <= idx < len(self._dates):
                self._update_info(idx)
                self._vline.setPos(idx)
                self._hline.setPos(mouse_point.y())

    def _on_mouse_clicked(self, evt):
        \"\"\"鼠标点击时发射bar_clicked信号\"\"\"
        if not self._dates:
            return
        pos = evt.scenePos()
        if self._main_plot.sceneBoundingRect().contains(pos):
            mouse_point = self._main_plot.vb.mapSceneToView(pos)
            idx = int(mouse_point.x() + 0.5)
            if 0 <= idx < len(self._datetimes):
                clicked_date = self._datetimes[idx]
                self.bar_clicked.emit(clicked_date)

    def _update_info(self, idx: int) -> None:"""
    
    if search_pattern in content:
        content = content.replace(search_pattern, new_with_click_handler)
        print("[OK] 添加了 _on_mouse_clicked 方法")
    else:
        print("[WARN] 未找到 _on_mouse_moved 方法，无法插入点击处理")
        return False
    
    with open(kline_view_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n[OK] 已保存到 {kline_view_path}")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("为 KlineChartWidget 添加 bar_clicked 信号 v2")
    print("=" * 60)
    
    success = add_bar_clicked_signal()
    
    if success:
        print("\n✅ 修复完成！")
        print("\n现在 Monitor Tab 的日线点击应该能联动分钟K线了")
        print("\n测试步骤：")
        print("1. 重新启动程序")
        print("2. 执行回测")
        print("3. 切换到 Monitor Tab")
        print("4. 点击日线K线上的任意一根K线")
        print("5. 分钟K线应该自动聚焦到对应日期并显示在中部")
    else:
        print("\n❌ 修复失败，需要手动检查")