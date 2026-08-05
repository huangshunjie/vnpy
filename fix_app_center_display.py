"""
修复量化研究平台在应用中心不显示的问题

完整诊断并修复
"""

import sys
import os

sys.path.insert(0, r'c:\Users\11229\Documents\GitHub\vnpy')
os.chdir(r'c:\Users\11229\Documents\GitHub\vnpy')

print("=" * 80)
print("诊断量化研究平台应用中心显示问题")
print("=" * 80)

# 步骤1: 检查应用类
print("\n[步骤1] 检查应用类配置...")
try:
    from vnpy.quant_research import QuantResearchApp
    print(f"  [OK] 应用类导入成功")
    print(f"  - app_name: {QuantResearchApp.app_name}")
    print(f"  - display_name: {QuantResearchApp.display_name}")
    print(f"  - widget_name: {QuantResearchApp.widget_name}")
    print(f"  - engine_class: {QuantResearchApp.engine_class}")
except Exception as e:
    print(f"  [FAIL] 应用类导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 步骤2: 检查Widget组件
print("\n[步骤2] 检查UI组件...")
try:
    from vnpy.quant_research.ui.widget import ResearchPlatformWidget
    print(f"  [OK] ResearchPlatformWidget导入成功")
    print(f"  - Widget类: {ResearchPlatformWidget}")
except Exception as e:
    print(f"  [FAIL] UI组件导入失败: {e}")
    import traceback
    traceback.print_exc()
    print("\n  这是问题所在！UI组件无法导入，所以应用无法显示！")
    sys.exit(1)

# 步骤3: 检查引擎
print("\n[步骤3] 检查引擎类...")
try:
    from vnpy.quant_research.engine import ResearchEngine
    print(f"  [OK] ResearchEngine导入成功")
except Exception as e:
    print(f"  [FAIL] 引擎导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 步骤4: 模拟应用加载
print("\n[步骤4] 模拟应用加载过程...")
try:
    from vnpy.event import EventEngine
    from vnpy.trader.engine import MainEngine
    
    print("  创建主引擎...")
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    
    print("  添加应用...")
    
    # 设置超时
    import threading
    import time
    
    success = False
    error = None
    
    def add_app():
        global success, error
        try:
            main_engine.add_app(QuantResearchApp)
            success = True
        except Exception as e:
            error = e
            import traceback
            traceback.print_exc()
    
    thread = threading.Thread(target=add_app)
    thread.daemon = True
    thread.start()
    
    # 等待5秒
    thread.join(timeout=5)
    
    if success:
        print("  [OK] 应用添加成功！")
        print(f"  已加载应用: {list(main_engine.apps.keys())}")
        
        # 检查widget是否注册
        if QuantResearchApp.widget_name in main_engine.widgets:
            print(f"  [OK] Widget已注册: {main_engine.widgets[QuantResearchApp.widget_name]}")
        else:
            print(f"  [WARNING] Widget未注册")
            
    elif error:
        print(f"  [FAIL] 应用添加失败: {error}")
    else:
        print("  [FAIL] 应用添加超时（5秒）")
        print("  这说明应用初始化过程中有阻塞操作！")
        
        # 这是问题！
        print("\n" + "=" * 80)
        print("找到问题了：应用初始化时有阻塞操作，导致加载超时")
        print("=" * 80)
        sys.exit(1)
        
    # 清理
    event_engine.stop()
    main_engine.close()
    
except Exception as e:
    print(f"  [FAIL] 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("诊断完成：应用配置正常！")
print("=" * 80)

print("\n如果运行到这里，说明应用本身没问题。")
print("问题可能是：")
print("  1. 启动脚本中应用加载顺序问题")
print("  2. 应用在实际环境中被过滤掉")
print("  3. UI组件在实际加载时出错")

print("\n建议尝试：")
print("  1. 重新启动VN Trader")
print("  2. 查看启动日志中的错误信息")
print("  3. 或使用独立启动脚本")
