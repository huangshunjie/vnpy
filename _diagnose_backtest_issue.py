"""
诊断回测无结果问题

检查 ConditionEngine 是否已经包含 K线形态指标的处理逻辑
"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("回测无结果问题诊断")
print("=" * 60)

# 1. 检查 ConditionEngine 文件内容
print("\n1. 检查 condition_engine.py 是否包含 K线形态处理逻辑...")
with open("vnpy/strategy_condition/engine/condition_engine.py", "r", encoding="utf-8") as f:
    content = f.read()
    
has_import = "from ..indicators.kline_patterns import" in content
has_yang = "if ind == CI.KLINE_YANG:" in content
has_yin = "if ind == CI.KLINE_YIN:" in content

print(f"  - kline_patterns import: {'✓' if has_import else '✗'}")
print(f"  - KLINE_YANG dispatch: {'✓' if has_yang else '✗'}")
print(f"  - KLINE_YIN dispatch: {'✓' if has_yin else '✗'}")

if not (has_import and has_yang and has_yin):
    print("\n❌ condition_engine.py 文件缺少 K线形态处理逻辑！")
    print("请运行：python _fix_kline_patterns.py")
    sys.exit(1)

# 2. 测试运行时加载
print("\n2. 测试运行时加载...")
try:
    from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
    from vnpy.strategy_condition.constant import ConditionIndicator, ConditionCategory
    from vnpy.strategy_condition.core.condition import Condition
    from types import SimpleNamespace
    from datetime import datetime
    
    engine = ConditionEngine()
    
    # 创建测试数据
    bars = [
        SimpleNamespace(datetime=datetime(2024,1,i), open=100, high=105, low=95, close=102, volume=1e6)
        for i in range(10)
    ]
    bars.append(SimpleNamespace(datetime=datetime(2024,1,11), open=100, high=107, low=99, close=105, volume=1.2e6))
    
    # 测试 KLINE_YANG
    cond = Condition(
        category=ConditionCategory.KLINE,
        indicator=ConditionIndicator.KLINE_YANG,
        params={}
    )
    
    passed, score = engine.eval_condition(cond, "TEST", bars)
    print(f"  - KLINE_YANG 评估: passed={passed}, score={score:.2f}")
    
    if passed:
        print("\n✓ ConditionEngine 运行时加载正常，K线形态指标工作正常")
    else:
        print("\n✗ KLINE_YANG 应该返回 True（最后一根是阳线），但返回了 False")
        print("这说明虽然代码修改了，但运行时可能加载了旧版本")
        
except Exception as e:
    print(f"\n✗ 运行时测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. 给出操作建议
print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
print("\n如果你的回测界面还是没有结果，请按以下步骤操作：")
print("1. 完全关闭 vnpy 主界面")
print("2. 重新启动 vnpy")
print("3. 重新运行回测")
print("\nPython 模块加载机制：修改 .py 文件后，已经运行的进程不会自动重新加载。")
print("必须重启进程才能使用新代码。")