"""
check_veighna_trader_target.py

检查桌面VeighNa Trader快捷方式指向哪个脚本
"""
import win32com.client
import os

def check_shortcut():
    """检查快捷方式"""
    shortcut_path = r"C:\Users\11229\Desktop\VeighNa Trader.lnk"
    
    print("="*60)
    print("检查 VeighNa Trader 快捷方式")
    print("="*60)
    
    if not os.path.exists(shortcut_path):
        print("\n[ERROR] 未找到快捷方式")
        return
    
    # 读取快捷方式
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    
    print(f"\n目标程序: {shortcut.Targetpath}")
    print(f"参数: {shortcut.Arguments}")
    print(f"工作目录: {shortcut.WorkingDirectory}")
    print(f"描述: {shortcut.Description}")
    
    # 分析目标
    target = shortcut.Targetpath
    args = shortcut.Arguments
    
    print("\n" + "="*60)
    print("分析结果")
    print("="*60)
    
    if "python" in target.lower() or "python" in args.lower():
        print("\n[Python脚本启动]")
        if "run.py" in args:
            print(f"✓ 启动脚本: {args}")
            
            # 检查是否是我们修改过的run.py
            target_script = args.strip('"')
            if os.path.exists(target_script):
                with open(target_script, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "KLineBehaviorLabApp" in content:
                        print("✓ 这个run.py已包含K-Line Behavior Lab!")
                        print("✓ 启动VeighNa Trader后，在功能菜单中查找")
                    else:
                        print("✗ 这个run.py还没有K-Line Behavior Lab")
                        print(f"✗ 需要修改: {target_script}")
            else:
                print(f"! 脚本不存在: {target_script}")
        else:
            print(f"启动命令: {target} {args}")
    
    elif "veighna" in target.lower():
        print("\n[VeighNa可执行文件]")
        print(f"启动程序: {target}")
        print("\n这是VeighNa Studio的启动器")
        print("它会显示应用中心界面（你看到的VeighNa Apps）")
        print("不是VeighNa Trader主程序")
    
    else:
        print(f"\n[其他启动方式]")
        print(f"目标: {target}")
        print(f"参数: {args}")

if __name__ == "__main__":
    check_shortcut()
