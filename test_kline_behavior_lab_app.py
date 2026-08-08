"""
K-Line Market Behavior Lab - 测试脚本

测试独立应用是否正常工作
"""
import sys

def test_app():
    """测试应用加载"""
    print("\n" + "="*60)
    print("Testing K-Line Behavior Lab App")
    print("="*60)
    
    try:
        # 导入应用
        from vnpy.kline_behavior_lab import KLineBehaviorLabApp
        print("[OK] KLineBehaviorLabApp imported")
        
        # 检查应用属性
        print(f"[OK] App name: {KLineBehaviorLabApp.app_name}")
        print(f"[OK] Display name: {KLineBehaviorLabApp.display_name}")
        print(f"[OK] Widget name: {KLineBehaviorLabApp.widget_name}")
        print(f"[OK] Engine class: {KLineBehaviorLabApp.engine_class}")
        
        # 测试核心引擎导入
        from vnpy.kline_behavior_lab.engine import KLineBehaviorLabEngine
        print("[OK] KLineBehaviorLabEngine imported")
        
        # 测试Widget导入
        from vnpy.kline_behavior_lab.widget import KLineBehaviorLabWidget
        print("[OK] KLineBehaviorLabWidget imported")
        
        print("\n" + "="*60)
        print("SUCCESS: K-Line Behavior Lab App is ready!")
        print("="*60)
        print("\nNext steps:")
        print("1. Restart VeighNa Studio")
        print("2. Look for 'K-Line Behavior Lab' in the Apps panel")
        print("3. Click to open the standalone app")
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_app()
    sys.exit(0 if success else 1)
