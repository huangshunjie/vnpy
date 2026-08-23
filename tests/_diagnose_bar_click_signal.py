"""
诊断日线点击信号连接情况
"""
import sys
sys.path.insert(0, ".")

def check_signal_definition():
    """检查bar_clicked信号是否正确定义"""
    print("=" * 60)
    print("检查 KlineChartWidget.bar_clicked 信号")
    print("=" * 60)
    
    from vnpy.strategy_condition.ui.kline_view import KlineChartWidget
    from PyQt5 import QtCore
    
    # 检查类属性
    if hasattr(KlineChartWidget, 'bar_clicked'):
        print("[OK] KlineChartWidget 类有 bar_clicked 属性")
        attr = getattr(KlineChartWidget, 'bar_clicked')
        print(f"[INFO] bar_clicked 类型: {type(attr)}")
        print(f"[INFO] 是否是Signal: {isinstance(attr, QtCore.pyqtSignal)}")
    else:
        print("[FAIL] KlineChartWidget 类没有 bar_clicked 属性")
        return False
    
    # 创建实例检查
    try:
        widget = KlineChartWidget()
        if hasattr(widget, 'bar_clicked'):
            print("[OK] KlineChartWidget 实例有 bar_clicked 属性")
            
            # 尝试连接信号
            def test_slot(date):
                print(f"[TEST] 信号触发，接收到日期: {date}")
            
            widget.bar_clicked.connect(test_slot)
            print("[OK] 信号连接成功")
            
            # 测试发射信号
            from datetime import datetime
            test_date = datetime(2026, 6, 22)
            widget.bar_clicked.emit(test_date)
            print("[OK] 信号发射成功")
        else:
            print("[FAIL] KlineChartWidget 实例没有 bar_clicked 属性")
            return False
            
    except Exception as e:
        print(f"[ERROR] 创建实例或测试信号时出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def check_monitor_connection():
    """检查Monitor面板是否连接了信号"""
    print("\n" + "=" * 60)
    print("检查 Monitor 面板信号连接")
    print("=" * 60)
    
    try:
        from vnpy.strategy_condition.ui.condition_monitor_widget import DualPeriodMonitorPanel
        
        # 读取源代码检查连接逻辑
        import inspect
        source = inspect.getsource(DualPeriodMonitorPanel.__init__)
        
        if 'bar_clicked.connect' in source:
            print("[OK] DualPeriodMonitorPanel.__init__ 中有 bar_clicked.connect 代码")
        else:
            print("[WARN] DualPeriodMonitorPanel.__init__ 中没有找到 bar_clicked.connect")
            print("[INFO] 检查是否在其他方法中连接...")
            
            # 检查其他可能的连接位置
            for method_name, method in inspect.getmembers(DualPeriodMonitorPanel, predicate=inspect.isfunction):
                method_source = inspect.getsource(method)
                if 'bar_clicked.connect' in method_source:
                    print(f"[OK] 在 {method_name} 方法中找到 bar_clicked.connect")
                    break
            else:
                print("[FAIL] 在所有方法中都没有找到 bar_clicked.connect")
                return False
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 检查Monitor连接时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_click_handler():
    """检查点击处理方法"""
    print("\n" + "=" * 60)
    print("检查 _on_mouse_clicked 方法")
    print("=" * 60)
    
    try:
        from vnpy.strategy_condition.ui.kline_view import KlineChartWidget
        import inspect
        
        if hasattr(KlineChartWidget, '_on_mouse_clicked'):
            print("[OK] KlineChartWidget 有 _on_mouse_clicked 方法")
            
            # 检查方法签名
            sig = inspect.signature(KlineChartWidget._on_mouse_clicked)
            print(f"[INFO] 方法签名: {sig}")
            
            # 检查方法内容
            source = inspect.getsource(KlineChartWidget._on_mouse_clicked)
            if 'bar_clicked.emit' in source:
                print("[OK] _on_mouse_clicked 中有 bar_clicked.emit 调用")
            else:
                print("[FAIL] _on_mouse_clicked 中没有 bar_clicked.emit 调用")
                return False
                
        else:
            print("[FAIL] KlineChartWidget 没有 _on_mouse_clicked 方法")
            return False
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 检查点击处理方法时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_signal_connection_in_build_ui():
    """检查_build_ui中是否连接了sigMouseClicked"""
    print("\n" + "=" * 60)
    print("检查 _build_ui 中的信号连接")
    print("=" * 60)
    
    try:
        from vnpy.strategy_condition.ui.kline_view import KlineChartWidget
        import inspect
        
        source = inspect.getsource(KlineChartWidget._build_ui)
        
        if 'sigMouseClicked.connect' in source:
            print("[OK] _build_ui 中有 sigMouseClicked.connect")
            if '_on_mouse_clicked' in source:
                print("[OK] 连接到 _on_mouse_clicked 方法")
            else:
                print("[WARN] 未连接到 _on_mouse_clicked 方法")
        else:
            print("[FAIL] _build_ui 中没有 sigMouseClicked.connect")
            return False
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 检查_build_ui时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n开始诊断日线点击信号...\n")
    
    results = []
    
    # 1. 检查信号定义
    results.append(("信号定义", check_signal_definition()))
    
    # 2. 检查点击处理方法
    results.append(("点击处理方法", check_click_handler()))
    
    # 3. 检查_build_ui中的连接
    results.append(("_build_ui连接", check_signal_connection_in_build_ui()))
    
    # 4. 检查Monitor连接
    results.append(("Monitor连接", check_monitor_connection()))
    
    # 总结
    print("\n" + "=" * 60)
    print("诊断结果总结")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")
    
    if all(r[1] for r in results):
        print("\n[SUCCESS] 所有检查通过！")
        print("\n可能的问题:")
        print("1. Monitor Tab没有正确初始化")
        print("2. 信号连接时机不对（在数据加载前就连接了）")
        print("3. 点击的位置不对（点击在了其他组件上）")
    else:
        print("\n[FAILED] 发现问题，请根据上述信息修复")