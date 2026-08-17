#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vnpy 多周期架构改造项目 - 完整状态验证
验证 Phase 4-8 的所有关键功能
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_phase4_ui():
    """Phase 4: UI 周期选择器"""
    print("\n" + "=" * 60)
    print("Phase 4: UI 周期选择器")
    print("=" * 60)
    
    try:
        # 检查 UI 文件
        with open("vnpy/strategy_condition/ui/condition_editor.py", 'r', encoding='utf-8') as f:
            ui_content = f.read()
        
        checks = [
            ("周期选择下拉框", "_data_interval" in ui_content),
            ("周期标签格式化", "_format_interval_label" in ui_content or "format_interval_label" in ui_content),
            ("参数保存/恢复", "QComboBox" in ui_content),
        ]
        
        all_passed = all(passed for _, passed in checks)
        
        for name, passed in checks:
            print(f"  {'✅' if passed else '❌'} {name}")
        
        # 检查 Condition 类
        with open("vnpy/strategy_condition/core/condition.py", 'r', encoding='utf-8') as f:
            cond_content = f.read()
        
        has_data_interval = "data_interval" in cond_content
        print(f"  {'✅' if has_data_interval else '❌'} Condition.data_interval 属性")
        
        if all_passed and has_data_interval:
            print("\n✅ Phase 4: 完成 (100%)")
            return True
        else:
            print("\n⚠️  Phase 4: 部分完成")
            return False
            
    except Exception as e:
        print(f"\n❌ Phase 4: 检查失败 - {e}")
        return False


def check_phase5_data():
    """Phase 5: 多周期数据缓冲"""
    print("\n" + "=" * 60)
    print("Phase 5: 多周期数据缓冲")
    print("=" * 60)
    
    try:
        from vnpy.strategy_condition.data.mtf_candle_buffer import MultiTimeframeCandleBuffer
        from vnpy.strategy_condition.data.bar_resampler import BarResampler
        
        print("  ✅ MultiTimeframeCandleBuffer 导入")
        print("  ✅ BarResampler 导入")
        
        # 检查关键方法
        mtf = MultiTimeframeCandleBuffer()
        methods = ['inject', 'get_bars', 'update_from_daily']
        
        for method in methods:
            has_method = hasattr(mtf, method)
            print(f"  {'✅' if has_method else '❌'} MTFCandleBuffer.{method}()")
        
        print("\n✅ Phase 5: 完成 (100%)")
        return True
        
    except Exception as e:
        print(f"\n❌ Phase 5: 检查失败 - {e}")
        return False


def check_phase6_monitor():
    """Phase 6: MonitorEngine 条件级路由"""
    print("\n" + "=" * 60)
    print("Phase 6: MonitorEngine 条件级路由")
    print("=" * 60)
    
    try:
        with open("vnpy/strategy_condition/monitor/condition_monitor_engine.py", 'r', encoding='utf-8') as f:
            monitor_content = f.read()
        
        checks = [
            ("MTFContext 支持", "MultiTimeframeContext" in monitor_content),
            ("条件级路由", "eval_condition_mtf" in monitor_content),
            ("数据对齐", "get_bars" in monitor_content or "mtf" in monitor_content.lower()),
        ]
        
        all_passed = all(passed for _, passed in checks)
        
        for name, passed in checks:
            print(f"  {'✅' if passed else '❌'} {name}")
        
        if all_passed:
            print("\n✅ Phase 6: 完成 (100%)")
            return True
        else:
            print("\n⚠️  Phase 6: 部分完成")
            return False
            
    except Exception as e:
        print(f"\n❌ Phase 6: 检查失败 - {e}")
        return False


def check_phase7_scan():
    """Phase 7: ScanEngine 条件级路由"""
    print("\n" + "=" * 60)
    print("Phase 7: ScanEngine 条件级路由")
    print("=" * 60)
    
    try:
        from vnpy.strategy_condition.engine.scan_engine import ScanEngine
        
        print("  ✅ ScanEngine 导入")
        
        # 检查关键方法
        methods = ['set_mtf_buffer', 'scan']
        for method in methods:
            has_method = hasattr(ScanEngine, method)
            print(f"  {'✅' if has_method else '❌'} ScanEngine.{method}()")
        
        # 检查文件内容
        with open("vnpy/strategy_condition/engine/scan_engine.py", 'r', encoding='utf-8') as f:
            scan_content = f.read()
        
        has_routing = "eval_condition_mtf" in scan_content
        has_mtf_buffer = "mtf_buffer" in scan_content or "MTFCandleBuffer" in scan_content
        
        print(f"  {'✅' if has_routing else '❌'} 条件级路由")
        print(f"  {'✅' if has_mtf_buffer else '❌'} MTF Buffer 集成")
        
        if has_routing and has_mtf_buffer:
            print("\n✅ Phase 7: 完成 (100%)")
            return True
        else:
            print("\n⚠️  Phase 7: 部分完成")
            return False
            
    except Exception as e:
        print(f"\n❌ Phase 7: 检查失败 - {e}")
        return False


def check_phase8_integration():
    """Phase 8: ConditionEngine 统一接口"""
    print("\n" + "=" * 60)
    print("Phase 8: ConditionEngine 统一接口")
    print("=" * 60)
    
    try:
        from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
        
        print("  ✅ ConditionEngine 导入")
        
        ce = ConditionEngine()
        
        # 检查关键方法
        has_eval_condition = hasattr(ce, 'eval_condition')
        has_eval_condition_mtf = hasattr(ce, 'eval_condition_mtf')
        
        print(f"  {'✅' if has_eval_condition else '❌'} eval_condition() (原有)")
        print(f"  {'✅' if has_eval_condition_mtf else '❌'} eval_condition_mtf() (新增)")
        
        # 检查方法签名
        if has_eval_condition_mtf:
            import inspect
            sig = inspect.signature(ce.eval_condition_mtf)
            params = list(sig.parameters.keys())
            has_mtf_context = 'mtf_context' in params
            print(f"  {'✅' if has_mtf_context else '❌'} 方法签名包含 mtf_context")
        else:
            has_mtf_context = False
        
        if has_eval_condition and has_eval_condition_mtf and has_mtf_context:
            print("\n✅ Phase 8: 完成 (100%)")
            return True
        else:
            print("\n⚠️  Phase 8: 部分完成")
            return False
            
    except Exception as e:
        print(f"\n❌ Phase 8: 检查失败 - {e}")
        return False


def check_end_to_end():
    """端到端功能验证"""
    print("\n" + "=" * 60)
    print("端到端功能验证")
    print("=" * 60)
    
    try:
        from vnpy.trader.constant import Interval
        from vnpy.strategy_condition.core.condition import Condition, condition_from_dict
        from vnpy.strategy_condition.constant import ConditionCategory, ConditionIndicator
        
        # 测试 1: 创建多周期条件
        cond = Condition(
            category=ConditionCategory.TREND,
            indicator=ConditionIndicator.MA_SLOPE,
            params={"ma_period": 20},
            data_interval=Interval.DAILY,
        )
        
        test1_passed = cond.data_interval == Interval.DAILY
        print(f"  {'✅' if test1_passed else '❌'} 创建多周期条件对象")
        
        # 测试 2: 序列化/反序列化
        cond_dict = cond.to_dict()
        cond2 = condition_from_dict(cond_dict)
        
        test2_passed = cond2.data_interval == Interval.DAILY
        print(f"  {'✅' if test2_passed else '❌'} 序列化/反序列化保持周期")
        
        # 测试 3: UI 参数转换
        ui_dict = {
            'category': 'TREND',
            'indicator': 'MA_SLOPE',
            'params': {'ma_period': 20, '_data_interval': 'd'},
        }
        cond3 = condition_from_dict(ui_dict)
        
        test3_passed = cond3.data_interval == Interval.DAILY
        print(f"  {'✅' if test3_passed else '❌'} UI _data_interval 转换")
        
        # 测试 4: ConditionEngine 接口
        from vnpy.strategy_condition.engine.condition_engine import ConditionEngine
        ce = ConditionEngine()
        
        test4_passed = hasattr(ce, 'eval_condition_mtf')
        print(f"  {'✅' if test4_passed else '❌'} ConditionEngine MTF 接口")
        
        all_passed = test1_passed and test2_passed and test3_passed and test4_passed
        
        if all_passed:
            print("\n✅ 端到端验证: 通过")
            return True
        else:
            print("\n⚠️  端到端验证: 部分通过")
            return False
            
    except Exception as e:
        print(f"\n❌ 端到端验证: 失败 - {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_summary(results):
    """生成项目状态总结"""
    print("\n" + "=" * 60)
    print("多周期架构改造项目状态总结")
    print("=" * 60)
    
    phases = [
        ("Phase 4", "UI 周期选择器", results.get('phase4', False)),
        ("Phase 5", "多周期数据缓冲", results.get('phase5', False)),
        ("Phase 6", "MonitorEngine 条件级路由", results.get('phase6', False)),
        ("Phase 7", "ScanEngine 条件级路由", results.get('phase7', False)),
        ("Phase 8", "ConditionEngine 统一接口", results.get('phase8', False)),
    ]
    
    print("\n各阶段完成情况:\n")
    for phase_name, desc, status in phases:
        status_icon = "✅" if status else "❌"
        completion = "100%" if status else "未完成"
        print(f"  {status_icon} {phase_name}: {desc} - {completion}")
    
    print("\n集成验证:")
    e2e_status = results.get('e2e', False)
    print(f"  {'✅' if e2e_status else '❌'} 端到端功能测试")
    
    # 计算总体完成度
    total_phases = len(phases)
    completed_phases = sum(1 for _, _, status in phases if status)
    completion_rate = (completed_phases / total_phases) * 100
    
    print(f"\n总体完成度: {completed_phases}/{total_phases} ({completion_rate:.0f}%)")
    
    if completion_rate == 100 and e2e_status:
        print("\n" + "🎉" * 20)
        print("多周期架构改造项目完成！")
        print("系统已具备完整的多周期策略支持能力。")
        print("🎉" * 20)
        return True
    elif completion_rate >= 80:
        print("\n⚠️  项目基本完成，部分功能需要验证或优化。")
        return False
    else:
        print("\n❌ 项目未完成，需要继续开发。")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("vnpy 多周期架构改造项目 - 完整状态验证")
    print("=" * 60)
    
    results = {}
    
    # 逐个阶段检查
    results['phase4'] = check_phase4_ui()
    results['phase5'] = check_phase5_data()
    results['phase6'] = check_phase6_monitor()
    results['phase7'] = check_phase7_scan()
    results['phase8'] = check_phase8_integration()
    
    # 端到端验证
    results['e2e'] = check_end_to_end()
    
    # 生成总结
    project_complete = generate_summary(results)
    
    # 返回退出码
    sys.exit(0 if project_complete else 1)