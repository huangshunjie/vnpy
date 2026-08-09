"""
测试量价关系特征体系
验证：
1. 特征定义正确注册到 PRESET_KLINE_FEATURES
2. 向量化计算函数能正确执行
3. KLineFeatureCalculator 能路由到量价计算函数
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd


def make_sample_df(n: int = 100) -> pd.DataFrame:
    """生成模拟K线数据"""
    np.random.seed(42)
    close = 10.0 + np.cumsum(np.random.randn(n) * 0.3)
    open_ = close + np.random.randn(n) * 0.1
    high = np.maximum(open_, close) + np.abs(np.random.randn(n) * 0.2)
    low = np.minimum(open_, close) - np.abs(np.random.randn(n) * 0.2)
    volume = np.random.randint(1000, 100000, size=n).astype(float)
    # 制造一些放量日
    volume[50] = volume.mean() * 5
    volume[70] = volume.mean() * 0.1
    return pd.DataFrame({
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    })


def test_feature_registration():
    """测试36个量价特征是否已注册到 PRESET_KLINE_FEATURES"""
    from vnpy.quant_research.model.kline_feature_presets import PRESET_KLINE_FEATURES
    from vnpy.quant_research.model.kline_feature_volume_price import VOLUME_PRICE_FEATURES

    print(f"[注册检查] VOLUME_PRICE_FEATURES 数量: {len(VOLUME_PRICE_FEATURES)}")
    assert len(VOLUME_PRICE_FEATURES) == 36, f"期望36个，实际{len(VOLUME_PRICE_FEATURES)}"

    for name in VOLUME_PRICE_FEATURES:
        assert name in PRESET_KLINE_FEATURES, f"{name} 未注册到 PRESET_KLINE_FEATURES"
    
    print(f"[注册检查] 全部36个量价特征已注册 ✓")
    print(f"[注册检查] PRESET_KLINE_FEATURES 总数: {len(PRESET_KLINE_FEATURES)}")


def test_calculator_map():
    """测试 VP_CALCULATOR_MAP 包含全部36个计算函数"""
    from vnpy.quant_research.behavior.volume_price_calculator import VP_CALCULATOR_MAP
    from vnpy.quant_research.model.kline_feature_volume_price import VOLUME_PRICE_FEATURES

    for name in VOLUME_PRICE_FEATURES:
        assert name in VP_CALCULATOR_MAP, f"{name} 缺少计算函数"
    
    print(f"[计算映射] 全部36个计算函数已就位 ✓")


def test_all_calculators_run():
    """测试全部36个计算函数能正常执行"""
    from vnpy.quant_research.behavior.volume_price_calculator import VP_CALCULATOR_MAP

    df = make_sample_df(100)
    errors = []
    
    for name, func in VP_CALCULATOR_MAP.items():
        try:
            result = func(df)
            assert isinstance(result, pd.Series), f"{name} 返回类型错误"
            assert len(result) == len(df), f"{name} 长度不匹配"
            # 检查非全NaN（至少有部分有效值）
            valid_count = result.notna().sum()
            assert valid_count > 0, f"{name} 全部为NaN"
        except Exception as e:
            errors.append(f"{name}: {e}")
    
    if errors:
        print(f"[计算执行] 失败 {len(errors)} 个:")
        for err in errors:
            print(f"  × {err}")
        raise AssertionError(f"{len(errors)}个计算函数执行失败")
    
    print(f"[计算执行] 全部36个函数执行成功 ✓")


def test_kline_calculator_integration():
    """测试 KLineFeatureCalculator 能正确计算量价特征"""
    from vnpy.quant_research.behavior.kline_calculator import KLineFeatureCalculator

    df = make_sample_df(100)
    calc = KLineFeatureCalculator()

    # 选几个代表性特征测试
    test_features = [
        "vp_vol_up_price_up",
        "vp_vol_break",
        "vp_shrink_pullback",
        "vp_divergence_top",
        "vp_gap_up_vol_up",
    ]
    
    result = calc.calculate(df, test_features)
    
    for feat in test_features:
        assert feat in result.columns, f"{feat} 未出现在结果中"
        assert result[feat].notna().sum() > 0, f"{feat} 全NaN"
    
    print(f"[集成测试] KLineFeatureCalculator 正确路由量价特征 ✓")


def test_calculate_volume_price_feature_api():
    """测试统一接口 calculate_volume_price_feature"""
    from vnpy.quant_research.behavior.volume_price_calculator import calculate_volume_price_feature

    df = make_sample_df(100)
    
    result = calculate_volume_price_feature(df, "vp_vol_up_price_up")
    assert isinstance(result, pd.Series)
    assert len(result) == 100
    
    # 测试未知特征名报错
    try:
        calculate_volume_price_feature(df, "vp_unknown_feature")
        assert False, "应该抛出 ValueError"
    except ValueError:
        pass
    
    print(f"[统一接口] calculate_volume_price_feature 正常工作 ✓")


def test_feature_summary():
    """测试特征库摘要信息"""
    from vnpy.quant_research.model.kline_feature_presets import get_feature_summary

    summary = get_feature_summary()
    print(f"\n[特征库摘要]")
    print(f"  总特征数: {summary['total']}")
    print(f"  适合条件: {summary['suitable_for_condition']}")
    print(f"  适合Alpha: {summary['suitable_for_alpha']}")
    print(f"  按类型分布: {summary['by_type']}")
    print(f"  按复杂度分布: {summary['by_complexity']}")
    
    # VOLUME 类型应包含量价特征
    assert summary['by_type'].get('volume', 0) >= 36, "VOLUME类型应至少包含36个量价特征"
    print(f"  VOLUME类型特征 >= 36 ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("量价关系特征体系 - 单元测试")
    print("=" * 60)
    
    test_feature_registration()
    test_calculator_map()
    test_all_calculators_run()
    test_kline_calculator_integration()
    test_calculate_volume_price_feature_api()
    test_feature_summary()
    
    print("\n" + "=" * 60)
    print("全部测试通过 ✓")
    print("=" * 60)