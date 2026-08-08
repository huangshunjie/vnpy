"""
验证 Quant Research Platform 是否正常
"""
import sys

print("=" * 80)
print("验证 Quant Research Platform")
print("=" * 80)

# 1. 测试导入
try:
    from vnpy.quant_research import QuantResearchApp
    print("\n[OK] QuantResearchApp 导入成功")
    print(f"    App Name: {QuantResearchApp.app_name}")
    print(f"    Display Name: {QuantResearchApp.display_name}")
    print(f"    Widget Name: {QuantResearchApp.widget_name}")
except Exception as e:
    print(f"\n[ERROR] 导入失败: {e}")
    sys.exit(1)

# 2. 测试 Widget 导入
try:
    from vnpy.quant_research.ui.widget import ResearchPlatformWidget
    print("\n[OK] ResearchPlatformWidget 导入成功")
except Exception as e:
    print(f"\n[ERROR] Widget 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. 测试 BehaviorResearchTab 导入
try:
    from vnpy.quant_research.ui.behavior_tab import BehaviorResearchTab
    print("\n[OK] BehaviorResearchTab 导入成功")
except Exception as e:
    print(f"\n[ERROR] BehaviorResearchTab 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. 检查 vnpy 安装路径
import vnpy
print(f"\n[INFO] vnpy 安装路径: {vnpy.__file__}")

print("\n" + "=" * 80)
print("所有检查通过！应该可以正常使用了。")
print("=" * 80)
print("\n请重启 VN Trader 查看效果。")
