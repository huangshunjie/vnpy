# -*- coding: utf-8 -*-
"""
test_core_engines_simple.py

K-Line Market Behavior Lab 核心引擎测试脚本（简化版）
测试Phase 2-4开发的所有组件
"""
import sys
import os

# 设置UTF-8输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def test_phase2_data_models():
    """测试Phase 2：数据模型"""
    print("\n" + "="*60)
    print("Phase 2: Data Models Test")
    print("="*60)
    
    try:
        # 测试特征模型
        from vnpy.quant_research.model.kline_feature_model import (
            KLineFeatureDefinition,
            KLineFeatureType,
            FeatureComplexity
        )
        print("[OK] Feature model imported")
        
        # 测试特征预设库
        from vnpy.quant_research.model.kline_feature_presets import (
            PRESET_KLINE_FEATURES,
            get_feature_summary
        )
        summary = get_feature_summary()
        print(f"[OK] Feature library loaded")
        print(f"     Total features: {summary['total']}")
        print(f"     For condition: {summary['suitable_for_condition']}")
        print(f"     For alpha: {summary['suitable_for_alpha']}")
        
        # 测试事件模型
        from vnpy.quant_research.model.kline_event_model import (
            EventRecord,
            EventSamplingRule,
            EventStatistics
        )
        print("[OK] Event model imported")
        
        # 测试研究实验模型
        from vnpy.quant_research.model.research_experiment_model import (
            BehaviorResearchExperiment,
            ExperimentStatus,
            BUILTIN_EXPERIMENT_TEMPLATES
        )
        print(f"[OK] Experiment model imported")
        print(f"     Built-in templates: {len(BUILTIN_EXPERIMENT_TEMPLATES)}")
        
        print("\n[PASS] Phase 2 Test Passed")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Phase 2 Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase3_feature_engine():
    """测试Phase 3：特征计算引擎"""
    print("\n" + "="*60)
    print("Phase 3: Feature Engine Test")
    print("="*60)
    
    try:
        # 测试特征注册中心
        from vnpy.quant_research.behavior import get_global_registry
        registry = get_global_registry()
        print("[OK] Feature registry initialized")
        
        stats = registry.get_statistics()
        print(f"     Total features: {stats['total_features']}")
        print(f"     Preset features: {stats['preset_features']}")
        print(f"     Custom features: {stats['custom_features']}")
        
        # 测试依赖解析
        features = ['ma_alignment']
        resolved = registry.resolve_dependencies(features)
        print(f"[OK] Dependency resolution: {features} -> {resolved}")
        
        # 测试特征引擎
        from vnpy.quant_research.behavior import FeatureEngine
        engine = FeatureEngine(registry)
        print("[OK] Feature engine initialized")
        
        # 创建测试数据
        import pandas as pd
        import numpy as np
        
        test_data = pd.DataFrame({
            'open': np.random.rand(100) * 10 + 10,
            'high': np.random.rand(100) * 10 + 15,
            'low': np.random.rand(100) * 10 + 5,
            'close': np.random.rand(100) * 10 + 10,
            'volume': np.random.rand(100) * 1000000,
        })
        
        # 测试特征计算
        features_to_calc = ['return_1', 'body_ratio', 'volume_ratio']
        result = engine.calculate(test_data, features_to_calc, validate=True)
        print(f"[OK] Feature calculation test passed")
        print(f"     Input rows: {len(test_data)}")
        print(f"     Features: {features_to_calc}")
        print(f"     Output columns: {len(result.columns)}")
        
        # 测试缓存
        stats = engine.get_statistics()
        print(f"[OK] Performance stats:")
        print(f"     Total calculations: {stats['total_calculations']}")
        print(f"     Cache hit rate: {stats['cache_hit_rate']:.2%}")
        
        print("\n[PASS] Phase 3 Test Passed")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Phase 3 Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase4_event_research():
    """测试Phase 4：事件研究引擎"""
    print("\n" + "="*60)
    print("Phase 4: Event Research Engine Test")
    print("="*60)
    
    try:
        # 测试条件构建器
        from vnpy.quant_research.behavior import ConditionBuilder
        builder = ConditionBuilder()
        print("[OK] Condition builder initialized")
        
        # 测试简单条件构建
        simple_cond = builder.build_simple_condition('return_1', '<', -0.03)
        print(f"[OK] Simple condition: {simple_cond}")
        
        # 测试复合条件构建
        conditions = [
            'return_1 < -0.03',
            'lower_shadow_ratio > 0.4',
            'volume_ratio > 1.5'
        ]
        compound_cond = builder.build_compound_condition(conditions, 'AND')
        print(f"[OK] Compound condition: {compound_cond[:50]}...")
        
        # 测试条件验证
        valid, error, features = builder.validate_expression(compound_cond)
        print(f"[OK] Condition validation: {'Valid' if valid else 'Invalid'}")
        print(f"     Dependencies: {features}")
        
        # 测试条件模板
        templates = builder.get_condition_templates()
        print(f"[OK] Condition templates: {len(templates)} templates")
        for i, t in enumerate(templates[:3], 1):
            print(f"     {i}. {t['name']} - {t['category']}")
        
        # 测试采样引擎
        from vnpy.quant_research.behavior import SamplingEngine
        from vnpy.quant_research.model.kline_event_model import (
            EventRecord,
            EventSamplingRule
        )
        from datetime import datetime
        
        sampling_engine = SamplingEngine()
        print("[OK] Sampling engine initialized")
        
        # 创建测试事件
        test_events = [
            EventRecord(
                event_id=f"E{i}",
                symbol="000001.SZ",
                datetime=datetime(2024, 1, i+1)
            )
            for i in range(10)
        ]
        
        # 测试冷却期采样
        sampled = sampling_engine.sample(
            test_events,
            rule=EventSamplingRule.COOLDOWN,
            cooldown_days=3
        )
        print(f"[OK] Cooldown sampling: {len(test_events)} events -> {len(sampled)} events")
        
        # 测试首次触发采样
        first = sampling_engine.sample(
            test_events,
            rule=EventSamplingRule.FIRST_TRIGGER
        )
        print(f"[OK] First trigger sampling: {len(test_events)} events -> {len(first)} events")
        
        print("\n[PASS] Phase 4 Test Passed")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Phase 4 Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """测试完整集成"""
    print("\n" + "="*60)
    print("Integration Test: Complete Research Flow")
    print("="*60)
    
    try:
        import pandas as pd
        import numpy as np
        from vnpy.quant_research.behavior import (
            FeatureEngine,
            ConditionBuilder,
            get_global_registry
        )
        
        # 1. 准备数据
        print("\nStep 1: Prepare data")
        np.random.seed(42)
        df = pd.DataFrame({
            'open': np.random.rand(200) * 10 + 10,
            'high': np.random.rand(200) * 10 + 15,
            'low': np.random.rand(200) * 10 + 5,
            'close': np.random.rand(200) * 10 + 10,
            'volume': np.random.rand(200) * 1000000,
        })
        print(f"[OK] Generated test data: {len(df)} rows")
        
        # 2. 构建条件
        print("\nStep 2: Build condition")
        builder = ConditionBuilder()
        condition = "(return_1 < -0.03) & (volume_ratio > 1.5)"
        valid, error, features = builder.validate_expression(condition)
        
        if not valid:
            print(f"[FAIL] Condition validation failed: {error}")
            return False
        
        print(f"[OK] Condition: {condition}")
        print(f"[OK] Dependencies: {features}")
        
        # 3. 计算特征
        print("\nStep 3: Calculate features")
        engine = FeatureEngine()
        df_with_features = engine.calculate(df, features)
        print(f"[OK] Calculation complete: {len(df_with_features.columns)} columns")
        
        # 4. 评估条件
        print("\nStep 4: Evaluate condition")
        result = builder.evaluate_on_data(condition, df_with_features)
        trigger_count = result.sum()
        print(f"[OK] Found {trigger_count} trigger points")
        
        # 5. 性能统计
        print("\nStep 5: Performance stats")
        stats = engine.get_statistics()
        print(f"[OK] Total calculations: {stats['total_calculations']}")
        print(f"[OK] Cache hit rate: {stats['cache_hit_rate']:.2%}")
        print(f"[OK] Average time: {stats['avg_time']:.4f}s")
        
        print("\n[PASS] Integration Test Passed")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Integration Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("K-Line Market Behavior Lab - Core Engine Test")
    print("="*60)
    print("\nTesting all Phase 2-4 components")
    
    results = {
        'Phase 2 - Data Models': test_phase2_data_models(),
        'Phase 3 - Feature Engine': test_phase3_feature_engine(),
        'Phase 4 - Event Research': test_phase4_event_research(),
        'Integration Test': test_integration(),
    }
    
    # 输出总结
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    all_passed = True
    for name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} - {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("SUCCESS: All tests passed! Core engines are working properly.")
        print("="*60)
        print("\nReady to proceed with UI development (Phase 5)")
    else:
        print("WARNING: Some tests failed, need to fix issues.")
        print("="*60)
        print("\nPlease fix failed tests before continuing.")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
