"""
测试 quant_research 导入
"""
import sys
import traceback

sys.path.insert(0, r'c:\Users\11229\Documents\GitHub\vnpy')

print("=" * 80)
print("测试 quant_research 导入")
print("=" * 80)

try:
    from vnpy.quant_research import QuantResearchApp
    print("\n[OK] 导入成功！")
    print(f"App Name: {QuantResearchApp.app_name}")
    print(f"Display Name: {QuantResearchApp.display_name}")
    print(f"Widget Name: {QuantResearchApp.widget_name}")
except Exception as e:
    print("\n[ERROR] 导入失败！")
    print("\n错误详情：")
    traceback.print_exc()
    print("\n" + "=" * 80)
    print("可能的原因：")
    print("1. behavior_tab.py 有语法错误")
    print("2. widget.py 修改有问题")
    print("3. 缺少依赖模块")
    print("=" * 80)
