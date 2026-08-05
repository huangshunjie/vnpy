"""
诊断量化研究平台应用加载问题
"""

import sys
sys.path.insert(0, r'c:\Users\11229\Documents\GitHub\vnpy')

print("=" * 80)
print("诊断量化研究平台应用加载")
print("=" * 80)

# 测试1: 导入应用类
print("\n[测试1] 导入应用类...")
try:
    from vnpy.quant_research import QuantResearchApp
    print(f"  [OK] QuantResearchApp导入成功")
    print(f"  App Name: {QuantResearchApp.app_name}")
    print(f"  Display Name: {QuantResearchApp.display_name}")
    print(f"  Widget Name: {QuantResearchApp.widget_name}")
    print(f"  Engine Class: {QuantResearchApp.engine_class}")
except Exception as e:
    print(f"  [FAIL] 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试2: 创建引擎
print("\n[测试2] 创建引擎...")
try:
    from vnpy.event import EventEngine
    from vnpy.trader.engine import MainEngine
    
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    print("  [OK] 主引擎创建成功")
except Exception as e:
    print(f"  [FAIL] 引擎创建失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试3: 加载应用（重点）
print("\n[测试3] 加载应用到主引擎...")
try:
    print("  正在添加应用...")
    # 设置超时检测
    import threading
    import time
    
    loading_done = False
    error_msg = None
    
    def load_app():
        global loading_done, error_msg
        try:
            main_engine.add_app(QuantResearchApp)
            loading_done = True
        except Exception as e:
            error_msg = str(e)
            import traceback
            traceback.print_exc()
    
    # 启动加载线程
    thread = threading.Thread(target=load_app)
    thread.daemon = True
    thread.start()
    
    # 等待最多10秒
    for i in range(10):
        if loading_done:
            print("  [OK] 应用加载成功")
            print(f"  已加载的应用: {list(main_engine.apps.keys())}")
            break
        if error_msg:
            print(f"  [FAIL] 应用加载失败: {error_msg}")
            break
        time.sleep(1)
        print(f"  等待中... {i+1}秒")
    else:
        print("  [FAIL] 应用加载超时（超过10秒）")
        print("  这说明应用初始化过程中有阻塞操作")
        
        # 尝试获取线程栈信息
        import traceback
        print("\n  当前线程状态:")
        for thread_id, frame in sys._current_frames().items():
            print(f"\n  Thread {thread_id}:")
            traceback.print_stack(frame)
        
except Exception as e:
    print(f"  [FAIL] 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("诊断完成")
print("=" * 80)

# 如果成功加载，继续测试UI
if loading_done:
    print("\n[测试4] 测试UI组件...")
    try:
        widget_class = main_engine.widgets[QuantResearchApp.widget_name]
        print(f"  [OK] UI组件类: {widget_class}")
    except Exception as e:
        print(f"  [FAIL] UI组件获取失败: {e}")
