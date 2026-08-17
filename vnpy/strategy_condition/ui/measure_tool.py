"""
K线图测量距离工具
"""
from typing import Optional, Tuple, List
import pyqtgraph as pg
from vnpy.trader.ui import QtCore, QtGui


class MeasureLine:
    """单条测量线"""
    
    def __init__(self, plot_item: pg.PlotItem, bars: list, dates: list):
        self.plot = plot_item
        self.bars = bars
        self.dates = dates
        
        # 起点和终点的索引
        self.start_idx: Optional[int] = None
        self.end_idx: Optional[int] = None
        
        # 图形元素
        self.line: Optional[pg.PlotDataItem] = None
        self.label: Optional[pg.TextItem] = None
        
        # 用于点击检测的区域
        self._clickable = False
        
    def set_start(self, idx: int) -> None:
        """设置起点"""
        self.start_idx = idx
        
    def set_end(self, idx: int) -> None:
        """设置终点并绘制"""
        self.end_idx = idx
        self._draw()
        self._clickable = True
        
    def update_preview(self, idx: int) -> None:
        """更新预览（鼠标移动时）"""
        if self.start_idx is None:
            return
        self.end_idx = idx
        self._draw()
        
    def _draw(self) -> None:
        """绘制测量线和标注"""
        if self.start_idx is None or self.end_idx is None:
            return
            
        # 清除旧的元素
        if self.line:
            self.plot.removeItem(self.line)
        if self.label:
            self.plot.removeItem(self.label)
            
        # 绘制虚线
        x = [self.start_idx, self.end_idx]
        y = [self.bars[self.start_idx][3], self.bars[self.end_idx][3]]  # close price
        
        pen = pg.mkPen(color=(255, 165, 0), width=2, style=QtCore.Qt.PenStyle.DashLine)
        self.line = pg.PlotDataItem(x, y, pen=pen)
        self.plot.addItem(self.line)
        
        # 计算数据
        time_span = abs(self.end_idx - self.start_idx)
        date_span = time_span  # 简化：假设每根K线=1天
        
        price_start = self.bars[self.start_idx][3]
        price_end = self.bars[self.end_idx][3]
        price_change = price_end - price_start
        price_pct = (price_change / price_start * 100) if price_start > 0 else 0
        
        # 创建标注文本
        sign = '+' if price_change >= 0 else ''
        text = f"时间: {time_span}根K线 ({date_span}天)\n"
        text += f"价格: {price_start:.2f}→{price_end:.2f}\n"
        text += f"涨跌: {sign}{price_pct:.2f}% ({sign}{price_change:.2f}元)"
        
        # 创建标注
        mid_x = (self.start_idx + self.end_idx) / 2
        mid_y = (y[0] + y[1]) / 2
        
        self.label = pg.TextItem(text, color=(255, 255, 255), anchor=(0.5, 0.5))
        self.label.setPos(mid_x, mid_y)
        
        # 设置背景
        bg_color = QtGui.QColor(30, 30, 46, 200)  # 半透明深色背景
        self.label.fill = pg.mkBrush(bg_color)
        self.label.border = pg.mkPen(color=(255, 165, 0), width=1)
        
        self.plot.addItem(self.label)
        
    def is_near_click(self, pos_x: float, pos_y: float, tolerance: float = 20) -> bool:
        """检测点击位置是否接近此测量线"""
        if not self._clickable or self.start_idx is None or self.end_idx is None:
            return False
            
        # 检查是否点击在标注框附近
        if self.label:
            label_pos = self.label.pos()
            label_x, label_y = label_pos.x(), label_pos.y()
            
            # 简单的距离检测
            dist = ((pos_x - label_x)**2 + (pos_y - label_y)**2)**0.5
            if dist < tolerance:
                return True
                
        return False
        
    def remove(self) -> None:
        """移除测量线"""
        if self.line:
            self.plot.removeItem(self.line)
        if self.label:
            self.plot.removeItem(self.label)
        self._clickable = False


class MeasureTool:
    """测量工具管理器"""
    
    def __init__(self, plot_item: pg.PlotItem, bars: list, dates: list):
        self.plot = plot_item
        self.bars = bars
        self.dates = dates
        
        self.active = False
        self.lines: List[MeasureLine] = []
        self.current_line: Optional[MeasureLine] = None
        
        # 鼠标事件代理
        self._mouse_proxy: Optional[pg.SignalProxy] = None
        self._click_proxy: Optional[pg.SignalProxy] = None
        
    def set_active(self, active: bool) -> None:
        """激活/停用测量工具"""
        self.active = active
        
        if active:
            self._setup_mouse_events()
            # 设置十字光标
            self.plot.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        else:
            self._remove_mouse_events()
            # 恢复默认光标
            self.plot.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            # 清除未完成的线
            if self.current_line:
                self.current_line.remove()
                self.current_line = None
            # 清空所有已完成的测量线
            self.clear_all_lines()
                
    def clear_all_lines(self) -> None:
        """清空所有测量线"""
        for line in self.lines:
            line.remove()
        self.lines.clear()
        
    def update_data(self, bars: list, dates: list) -> None:
        """更新数据"""
        self.bars = bars
        self.dates = dates
        # 清除所有测量线
        self.clear_all_lines()
        if self.current_line:
            self.current_line.remove()
            self.current_line = None
            
    def _setup_mouse_events(self) -> None:
        """设置鼠标事件"""
        scene = self.plot.scene()
        if scene:
            # 鼠标移动
            self._mouse_proxy = pg.SignalProxy(
                scene.sigMouseMoved,
                rateLimit=60,
                slot=self._on_mouse_moved
            )
            # 鼠标点击
            scene.sigMouseClicked.connect(self._on_mouse_clicked)
            
    def _remove_mouse_events(self) -> None:
        """移除鼠标事件"""
        scene = self.plot.scene()
        if scene:
            try:
                scene.sigMouseClicked.disconnect(self._on_mouse_clicked)
            except:
                pass
        self._mouse_proxy = None
        
    def _on_mouse_moved(self, evt) -> None:
        """鼠标移动事件"""
        if not self.active or not self.current_line:
            return
            
        pos = evt[0]
        if self.plot.sceneBoundingRect().contains(pos):
            mouse_point = self.plot.vb.mapSceneToView(pos)
            idx = int(round(mouse_point.x()))
            if 0 <= idx < len(self.bars):
                self.current_line.update_preview(idx)
                
    def _on_mouse_clicked(self, evt) -> None:
        """鼠标点击事件"""
        if not self.active:
            return
            
        # 右键取消
        if evt.button() == QtCore.Qt.MouseButton.RightButton:
            if self.current_line:
                self.current_line.remove()
                self.current_line = None
            return
            
        # 左键设置点或删除
        if evt.button() == QtCore.Qt.MouseButton.LeftButton:
            pos = evt.scenePos()
            if self.plot.sceneBoundingRect().contains(pos):
                mouse_point = self.plot.vb.mapSceneToView(pos)
                idx = int(round(mouse_point.x()))
                mouse_x = mouse_point.x()
                mouse_y = mouse_point.y()
                
                # 先检查是否双击已有的测量线（删除功能）
                if evt.double():
                    for line in self.lines[:]:  # 使用切片创建副本以避免迭代时修改
                        if line.is_near_click(mouse_x, mouse_y, tolerance=30):
                            line.remove()
                            self.lines.remove(line)
                            return
                
                # 正常绘制流程
                if 0 <= idx < len(self.bars):
                    if self.current_line is None:
                        # 设置起点
                        self.current_line = MeasureLine(self.plot, self.bars, self.dates)
                        self.current_line.set_start(idx)
                    else:
                        # 设置终点
                        self.current_line.set_end(idx)
                        self.lines.append(self.current_line)
                        self.current_line = None