"""
test_core_engines.py

K-Line Market Behavior Lab 核心引擎测试脚本
测试Phase 2-4开发的所有组件
"""

def test_phase2_data_models():
    """测试Phase 2：数据模型"""
    print("\n" + "="*60)
    print("Phase 2: 数据模型测试")
    print("="*60)
    
    try:
        # 测试特征模型
        from vnpy.quant_research.model.kline_feature_model import (
            KLineFeatureDefinition,
            KLineFeatureType,
            FeatureComplexity
        )
        print("✓ 特征模型导入成功")
        
        # 测试特征预设库
        from vnpy.quant_research.model.kline_feature_presets import (
            PRESET_KLINE_FEATURES,
            get_feature_summary
        )
        summary = get_feature_summary()
        print(f"✓ 特征预设库加载成功")
        print(f"  - 总特征数: {summary['total']}")
        print(f"  - 适合条件: {summary['suitable_for_condition']}")
        print(f"  - 适合因子: {summary['suitable_for_alpha']}")
        
        # 测试事件模型
        from vnpy.quant_research.model.kline_event_model import (
            EventRecord,
            EventSamplingRule,
            EventStatistics
        )
        print("✓ 事件模型导入成功")
        
        # 测试研究实验模型
        from vnpy.quant_research.model.research_experiment_model import (
            BehaviorResearchExperiment,
            ExperimentStatus,
            BUILTIN_EXPERIMENT_TEMPLATES
        )
        print(f"✓ 研究实验模型导入成功")
        print(f"  - 内置模板数: {len(BUILTIN_EXPERIMENT_TEMPLATES)}")
        
        print("\n✅ Phase 2 数据模型测试通过")
        return True
        
    except Exception as e:
        print(f"\n❌ Phase 2 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase3_feature_engine():
    """测试Phase 3：特征计算引擎"""
    print("\n" + "="*60)
    print("Phase 3: 特征计算引擎测试")
    print("="*60)
    
    try:
        # 测试特征注册中心
        from vnpy.quant_research.behavior import get_global_registry
        registry = get_global_registry()
        print("✓ 特征注册中心初始化成功")
        
        stats = registry.get_statistics()
        print(f"  - 总特征数: {stats['total_features']}")
        print(f"  - 预置特征: {stats['preset_features']}")
        print(f"  - 自定义特征: {stats['custom_features']}")
        
        # 测试特征查询
        simple_features = registry.list_features(
            complexity=registry.list_features()[0].complexity.__class__.SIMPLE
        )
        print(f"  - 简单特征数: {len(simple_features)}")
        
        # 测试依赖解析
        features = ['ma_alignment']
        resolved = registry.resolve_dependencies(features)
        print(f"✓ 依赖解析测试: {features} -> {resolved}")
        
        # 测试特征引擎
        from vnpy.quant_research.behavior import FeatureEngine
        engine = FeatureEngine(registry)
        print("✓ 特征计算引擎初始化成功")
        
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
        print(f"✓ 特征计算测试通过")
        print(f"  - 输入数据: {len(test_data)}行")
        print(f"  - 计算特征: {features_to_calc}")
        print(f"  - 输出列数: {len(result.columns)}")
        
        # 测试缓存
        stats = engine.get_statistics()
        print(f"✓ 性能统计:")
        print(f"  - 总计算次数: {stats['total_calculations']}")
        print(f"  - 缓存命中率: {stats['cache_hit_rate']:.2%}")
        
        print("\n✅ Phase 3 特征计算引擎测试通过")
        return True
        
    except Exception as e:
        print(f"\n❌ Phase 3 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase4_event_research():
    """测试Phase 4：事件研究引擎"""
    print("\n" + "="*60)
    print("Phase 4: 事件研究引擎测试")
    print("="*60)
    
    try:
        # 测试条件构建器
        from vnpy.quant_research.behavior import ConditionBuilder
        builder = ConditionBuilder()
        print("✓ 条件构建器初始化成功")
        
        # 测试简单条件构建
        simple_cond = builder.build_simple_condition('return_1', '<', -0.03)
        print(f"✓ 简单条件构建: {simple_cond}")
        
        # 测试复合条件构建
        conditions = [
            'return_1 < -0.03',
            'lower_shadow_ratio > 0.4',
            'volume_ratio > 1.5'
        ]
        compound_cond = builder.build_compound_condition(conditions, 'AND')
        print(f"✓ 复合条件构建: {compound_cond[:50]}...")
        
        # 测试条件验证
        valid, error, features = builder.validate_expression(compound_cond)
        print(f"✓ 条件验证: {'有效' if valid else '无效'}")
        print(f"  - 依赖特征: {features}")
        
        # 测试特征提取
        extracted = builder.extract_features(compound_cond)
        print(f"✓ 特征提取: {extracted}")
        
        # 测试条件模板
        templates = builder.get_condition_templates()
        print(f"✓ 条件模板: {len(templates)}个")
        for i, t in enumerate(templates[:3], 1):
            print(f"  {i}. {t['name']} - {t['category']}")
        
        # 测试采样引擎
        from vnpy.quant_research.behavior import SamplingEngine
        from vnpy.quant_research.model.kline_event_model import (
            EventRecord,
            EventSamplingRule
        )
        from datetime import datetime
        
        sampling_engine = SamplingEngine()
        print("✓ 采样引擎初始化成功")
        
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
        print(f"✓ 冷却期采样: {len(test_events)}个事件 -> {len(sampled)}个")
        
        # 测试首次触发采样
        first = sampling_engine.sample(
            test_events,
            rule=EventSamplingRule.FIRST_TRIGGER
        )
        print(f"✓ 首次触发采样: {len(test_events)}个事件 -> {len(first)}个")
        
        print("\n✅ Phase 4 事件研究引擎测试通过")
        return True
        
    except Exception as e:
        print(f"\n❌ Phase 4 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """测试完整集成"""
    print("\n" + "="*60)
    print("集成测试：完整研究流程模拟")
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
        print("\n步骤1: 准备数据")
        np.random.seed(42)
        df = pd.DataFrame({
            'open': np.random.rand(200) * 10 + 10,
            'high': np.random.rand(200) * 10 + 15,
            'low': np.random.rand(200) * 10 + 5,
            'close': np.random.rand(200) * 10 + 10,
            'volume': np.random.rand(200) * 1000000,
        })
        print(f"✓ 生成测试数据: {len(df)}行")
        
        # 2. 构建条件
        print("\n步骤2: 构建研究条件")
        builder = ConditionBuilder()
        condition = "(return_1 < -0.03) & (volume_ratio > 1.5)"
        valid, error, features = builder.validate_expression(condition)
        
        if not valid:
            print(f"✗ 条件验证失败: {error}")
            return False
        
        print(f"✓ 条件: {condition}")
        print(f"✓ 依赖特征: {features}")
        
        # 3. 计算特征
        print("\n步骤3: 计算K线特征")
        engine = FeatureEngine()
        df_with_features = engine.calculate(df, features)
        print(f"✓ 计算完成: {len(df_with_features.columns)}列")
        
        # 4. 评估条件
        print("\n步骤4: 评估条件")
        result = builder.evaluate_on_data(condition, df_with_features)
        trigger_count = result.sum()
        print(f"✓ 找到 {trigger_count} 个触发点")
        
        # 5. 性能统计
        print("\n步骤5: 性能统计")
        stats = engine.get_statistics()
        print(f"✓ 总计算: {stats['total_calculations']}次")
        print(f"✓ 缓存命中率: {stats['cache_hit_rate']:.2%}")
        print(f"✓ 平均耗时: {stats['avg_time']:.4f}秒")
        
        print("\n✅ 集成测试通过")
        return True
        
    except Exception as e:
        print(f"\n❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("K-Line Market Behavior Lab - 核心引擎测试")
    print("="*60)
    print("\n测试 Phase 2-4 开发的所有核心组件")
    
    results = {
        'Phase 2 - 数据模型': test_phase2_data_models(),
        'Phase 3 - 特征引擎': test_phase3_feature_engine(),
        'Phase 4 - 事件研究': test_phase4_event_research(),
        '集成测试': test_integration(),
    }
    
    # 输出总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 所有测试通过！核心引擎运行正常。")
        print("="*60)
        print("\n可以继续进行UI开发（Phase 5）")
    else:
        print("⚠️  部分测试失败，需要修复问题。")
        print("="*60)
        print("\n建议先修复失败的测试，再继续开发。")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
