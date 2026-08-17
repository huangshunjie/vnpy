"""测试MA图例颜色是否正确显示"""
import sys
from vnpy.trader.ui import QtWidgets, QtCore

_GRN = "#a6e3a1"
_RED = "#f38ba8"
_C_UP = "#ff5555"
_C_DN = "#00e676"

def _lbl(text, color, size=14):
    w = QtWidgets.QLabel(text)
    w.setStyleSheet(
        f"color:{color};font-size:{size}px;"
        f"font-weight:normal;"
        f"background:transparent;border:none;")
    return w

app = QtWidgets.QApplication(sys.argv)

win = QtWidgets.QWidget()
win.setWindowTitle("MA图例颜色测试")
win.setStyleSheet("background:#1e1e2e;")
win.resize(800, 100)

layout = QtWidgets.QHBoxLayout(win)
layout.setSpacing(18)

# 创建测试标签
layout.addWidget(_lbl("▲ 买入信号", _GRN, 13))
layout.addWidget(_lbl("▼ 卖出信号", _RED, 13))
layout.addWidget(_lbl("■ 阳线（涨）", _C_UP, 13))
layout.addWidget(_lbl("■ 阴线（跌）", _C_DN, 13))

# MA图例
colors = ['#f9e2af', '#94e2d5', '#89b4fa', '#cba6f7', '#f5c2e7', '#a6e3a1']
periods = ['5', '10', '20', '60', '120', '250']
for period, color in zip(periods, colors):
    lbl = _lbl(f"— MA{period}", color, 13)
    layout.addWidget(lbl)
    print(f"Created label MA{period} with color {color}")
    print(f"  StyleSheet: {lbl.styleSheet()}")

win.show()
sys.exit(app.exec())