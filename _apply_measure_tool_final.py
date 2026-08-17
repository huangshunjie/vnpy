"""
最终完整地为K线图添加测量工具
"""

# 1. 首先应用之前的脚本添加基础功能
import subprocess
result = subprocess.run(['python', '_add_measure_tool_to_kline.py'], 
                       capture_output=True, text=True, encoding='utf-8')
print("Step 1:", result.stdout if result.returncode == 0 else result.stderr)

# 2. 然后手动添加全屏K线图的测量工具支持
with open('vnpy/strategy_condition/ui/kline_view.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到需要修改的位置
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # 1. 在工具栏的 self._trig_chk 后添加测量按钮
    if 'tl.addWidget(self._trig_chk)' in line and '_KlineFullscreenWindow' in ''.join(lines[max(0,i-50):i]):
        new_lines.append(line)
        new_lines.append('        \n')
        new_lines.append('        # 测量工具按钮\n')
        new_lines.append('        self._measure_btn = QtWidgets.QPushButton("📏 测量")\n')
        new_lines.append('        self._measure_btn.setCheckable(True)\n')
        new_lines.append('        self._measure_btn.setFixedHeight(26)\n')
        new_lines.append('        self._measure_btn.setStyleSheet(\n')
        new_lines.append("            'background:#a6e3a1;color:#11111b;border:none;'\n")
        new_lines.append("            'border-radius:4px;font-size:13px;font-weight:bold;padding:0 10px;')\n")
        new_lines.append('        self._measure_btn.clicked.connect(self._on_measure_toggle)\n')
        new_lines.append('        tl.addWidget(self._measure_btn)\n')
        i += 1
        continue
        
    # 2. 在 _KlineFullscreenWindow 添加 _on_measure_toggle 方法
    if 'def keyPressEvent(self, event) -> None:' in line and '_KlineFullscreenWindow' in ''.join(lines[max(0,i-100):i]):
        new_lines.append('    def _on_measure_toggle(self, checked: bool) -> None:\n')
        new_lines.append('        """切换测量工具"""\n')
        new_lines.append('        if checked:\n')
        new_lines.append('            self._measure_btn.setStyleSheet(\n')
        new_lines.append("                'background:#89b4fa;color:#11111b;border:none;'\n")
        new_lines.append("                'border-radius:4px;font-size:13px;font-weight:bold;padding:0 10px;')\n")
        new_lines.append('        else:\n')
        new_lines.append('            self._measure_btn.setStyleSheet(\n')
        new_lines.append("                'background:#a6e3a1;color:#11111b;border:none;'\n")
        new_lines.append("                'border-radius:4px;font-size:13px;font-weight:bold;padding:0 10px;')\n')
        new_lines.append('        self._chart._measure_tool.set_active(checked)\n')
        new_lines.append('\n')
        new_lines.append(line)
        i += 1
        continue
    
    # 3. 在 _FullscreenChart.__init__ 修改测量工具初始化
    if 'self._measure_mode = False' in line and '_FullscreenChart' in ''.join(lines[max(0,i-50):i]):
        # 跳过旧的三行
        new_lines.append('        self._measure_tool = None  # 将在 _build_ui 后初始化\n')
        i += 3  # 跳过 _measure_mode, _measure_start, _measure_line
        continue
        
    # 4. 在 _build_ui 结尾初始化 MeasureTool，替换原有的连接
    if 'self._main_plot.scene().sigMouseClicked.connect(self._on_measure_click)' in line:
        new_lines.append('        # 初始化测量工具\n')
        new_lines.append('        from .measure_tool import MeasureTool\n')
        new_lines.append('        self._measure_tool = MeasureTool(self._main_plot, self._bars, self._dates)\n')
        i += 1
        continue
        
    # 5. 在 _redraw 开始更新 MeasureTool
    if 'def _redraw(self) -> None:' in line and '_FullscreenChart' in ''.join(lines[max(0,i-50):i]):
        new_lines.append(line)
        i += 1
        new_lines.append(lines[i])  # self._main_plot.clear()
        i += 1
        new_lines.append(lines[i])  # self._vol_plot.clear()
        i += 1
        new_lines.append('\n')
        new_lines.append('        # 更新测量工具数据\n')
        new_lines.append('        if self._measure_tool:\n')
        new_lines.append('            self._measure_tool.update_data(self._bars, self._dates)\n')
        continue
        
    # 6. 删除旧的 _on_measure_click 方法
    if 'def _on_measure_click(self, evt) -> None:' in line and '_FullscreenChart' in ''.join(lines[max(0,i-100):i]):
        # 跳过整个方法直到下一个方法定义或类结束
        while i < len(lines):
            if i + 1 < len(lines) and lines[i+1].strip() and not lines[i+1].startswith(' '):
                break
            if i + 1 < len(lines) and lines[i+1].strip().startswith('def ') and not lines[i+1].startswith('        def'):
                break
            i += 1
        continue
    
    new_lines.append(line)
    i += 1

# 写回文件
with open('vnpy/strategy_condition/ui/kline_view.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Step 2: 已为全屏K线图添加测量工具支持")