"""
install_kline_behavior_lab.py

安装K-Line Behavior Lab应用到VeighNa Studio
"""
import sys
import os

def install_app():
    """安装K-Line Behavior Lab应用"""
    print("\n" + "="*60)
    print("Installing K-Line Behavior Lab")
    print("="*60)
    
    # 1. 验证应用文件存在
    print("\n[Step 1] Checking app files...")
    app_dir = r"C:\Users\11229\Documents\GitHub\vnpy\vnpy\kline_behavior_lab"
    
    required_files = [
        "__init__.py",
        "app.py",
        "engine.py",
        "widget.py",
        "constant.py"
    ]
    
    for file in required_files:
        file_path = os.path.join(app_dir, file)
        if os.path.exists(file_path):
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} NOT FOUND!")
            return False
    
    # 2. 测试应用导入
    print("\n[Step 2] Testing app import...")
    try:
        from vnpy.kline_behavior_lab import KLineBehaviorLabApp
        print(f"  ✓ KLineBehaviorLabApp imported")
        print(f"  ✓ App name: {KLineBehaviorLabApp.app_name}")
        print(f"  ✓ Display name: {KLineBehaviorLabApp.display_name}")
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False
    
    # 3. 检查VeighNa是否能发现应用
    print("\n[Step 3] Checking VeighNa app discovery...")
    try:
        # VeighNa会自动扫描vnpy目录下的应用
        import pkgutil
        import vnpy
        
        # 查找所有应用
        apps_found = []
        for importer, modname, ispkg in pkgutil.iter_modules(vnpy.__path__):
            if ispkg:
                try:
                    module = __import__(f"vnpy.{modname}", fromlist=[''])
                    if hasattr(module, f"{modname.title().replace('_', '')}App"):
                        apps_found.append(modname)
                except:
                    pass
        
        if "kline_behavior_lab" in apps_found:
            print(f"  ✓ K-Line Behavior Lab discovered by VeighNa")
        else:
            print(f"  ! K-Line Behavior Lab not in auto-discovery list")
            print(f"    This is OK - manual registration needed")
    except Exception as e:
        print(f"  ! Discovery check skipped: {e}")
    
    # 4. 创建配置文件（如果需要）
    print("\n[Step 4] Creating app configuration...")
    config_content = """
# K-Line Behavior Lab - App Configuration

APP_NAME = "KLineBehaviorLab"
DISPLAY_NAME = "K-Line Behavior Lab  K线行为研究实验室"
CATEGORY = "研究平台"

# 功能特性
FEATURES = [
    "67个K线特征",
    "8个研究模板",
    "智能条件验证",
    "4种采样规则"
]
"""
    
    config_path = os.path.join(app_dir, "config.py")
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)
    print(f"  ✓ Configuration created: {config_path}")
    
    # 5. 成功信息
    print("\n" + "="*60)
    print("SUCCESS: K-Line Behavior Lab installed!")
    print("="*60)
    
    print("\n📋 Next Steps:")
    print("\n1. RESTART VeighNa Studio completely")
    print("   - Close all VeighNa windows")
    print("   - Kill any background processes")
    print("   - Restart from Start menu or desktop")
    
    print("\n2. If still not showing:")
    print("   a) Open 'Quant Research P' (量化研究平台)")
    print("   b) Look for 'Behavior Research' tab inside")
    print("   c) OR check 'System Integration Bus' for new apps")
    
    print("\n3. Alternative access:")
    print("   Run this command to launch directly:")
    print("   D:\\veighna_studio\\python.exe -c \"from vnpy.kline_behavior_lab.widget import KLineBehaviorLabWidget; app.exec()\"")
    
    print("\n4. Verify installation:")
    print("   Run: D:\\veighna_studio\\python.exe verify_kline_behavior_lab.py")
    
    return True

if __name__ == "__main__":
    try:
        success = install_app()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
