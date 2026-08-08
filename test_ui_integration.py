# -*- coding: utf-8 -*-
"""
test_ui_integration.py

测试UI集成核心引擎
"""
import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_ui_imports():
    """测试UI可以导入核心引擎"""
    print("\n" + "="*60)
    print("Testing UI Integration")
    print("="*60)
    
    try:
        # 测试behavior_tab可以导入
        from vnpy.quant_research.ui.behavior_tab import BehaviorResearchTab
        print("[OK] BehaviorResearchTab imported")
        
        # 检查是否有核心引擎
        # 这需要实际创建实例，但需要ResearchEngine
        from vnpy.quant_research.engine import ResearchEngine
        from vnpy.event import EventEngine
        from vnpy.trader.engine import MainEngine
        
        print("[OK] All dependencies available")
        
        # 测试核心引擎可以独立工作
        from vnpy.quant_research.behavior import (
            FeatureEngine,
            ConditionBuilder,
            SamplingEngine,
            get_global_registry
        )
        
        registry = get_global_registry()
        print(f"[OK] Feature registry: {len(registry.get_feature_names())} features")
        
        builder = ConditionBuilder()
        templates = builder.get_condition_templates()
        print(f"[OK] Condition templates: {len(templates)} templates")
        
        engine = FeatureEngine()
        print("[OK] Feature engine ready")
        
        sampling = SamplingEngine()
        print("[OK] Sampling engine ready")
        
        print("\n[PASS] UI Integration Test Passed")
        print("\nCore engines are ready for UI integration!")
        print("\nNext step: Apply UI enhancements from BEHAVIOR_TAB_ENHANCEMENT_PLAN.md")
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] UI Integration Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ui_imports()
    sys.exit(0 if success else 1)
