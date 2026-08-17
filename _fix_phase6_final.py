#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fix Phase 6 Monitor Engine integration issues
"""

def fix_monitor_engine():
    """Fix duplicate mtf_context parameter in condition_monitor_engine.py"""
    path = 'vnpy/strategy_condition/monitor/condition_monitor_engine.py'
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the duplicate mtf_context parameter
    # Look for the pattern: pos_ctx, mtf_context, mtf_context)
    content = content.replace(
        'pos_ctx, mtf_context, mtf_context)',
        'pos_ctx, mtf_context)'
    )
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Fixed {path}")


def fix_test_file():
    """Fix MultiTimeframeCandleBuffer.set_base_bars() calls in test"""
    path = 'tests/test_mtf_phase6_monitor.py'
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace set_base_bars with inject
    content = content.replace(
        'mtf_buffer.set_base_bars("TEST.SH", minute_bars, Interval.MINUTE_5)',
        'mtf_buffer.inject("TEST.SH", Interval.MINUTE_5, minute_bars)'
    )
    content = content.replace(
        'mtf_buffer.set_base_bars("TEST.SH", daily_bars, Interval.DAILY)',
        'mtf_buffer.inject("TEST.SH", Interval.DAILY, daily_bars)'
    )
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Fixed {path}")


def clear_pycache():
    """Clear Python bytecode cache"""
    import os
    import shutil
    
    pycache_dir = 'vnpy/strategy_condition/monitor/__pycache__'
    if os.path.isdir(pycache_dir):
        for fname in os.listdir(pycache_dir):
            if 'condition_monitor_engine' in fname:
                fpath = os.path.join(pycache_dir, fname)
                os.remove(fpath)
                print(f"✓ Removed {fpath}")


if __name__ == '__main__':
    print("=== Fixing Phase 6 Issues ===\n")
    fix_monitor_engine()
    fix_test_file()
    clear_pycache()
    print("\n=== All fixes applied ===")