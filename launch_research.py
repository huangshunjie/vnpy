"""
量化研究平台 - 简化独立启动

最简单可靠的启动方式
"""

import sys
import os

# 添加路径
sys.path.insert(0, r'c:\Users\11229\Documents\GitHub\vnpy')
os.chdir(r'c:\Users\11229\Documents\GitHub\vnpy')

print("=" * 80)
print("正在启动量化研究平台...")
print("=" * 80)

try:
    from PySide6.QtWidgets import QApplication
    from vnpy.event import EventEngine
    from vnpy.trader.engine import MainEngine
    
    # 创建Qt应用
    app = QApplication(sys.argv)
    
    # 创建引擎
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    
    print("[1/3] 引擎创建完成")
    
    # 导入并创建研究平台组件
    from vnpy.quant_research.ui.widget import ResearchPlatformWidget
    
    print("[2/3] UI组件加载完成")
    
    # 创建主窗口
    widget = ResearchPlatformWidget(main_engine, event_engine)
    widget.setWindowTitle("量化研究平台")
    widget.showMaximized()
    
    print("[3/3] 量化研究平台启动成功！")
    print("=" * 80)
    
    # 运行
    sys.exit(app.exec())
    
except Exception as e:
    print(f"\n[错误] 启动失败: {e}")
    import traceback
    traceback.print_exc()
    input("\n按回车键退出...")
