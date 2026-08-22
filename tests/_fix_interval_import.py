"""
修复 _minute_key_to_interval 方法的 ImportError

问题：尝试导入不存在的 MINUTE, MINUTE_5 等常量
正确：应该导入 Interval.MINUTE, Interval.MINUTE_5 等
"""

def fix_interval_import():
    widget_path = "vnpy/strategy_condition/ui/widget.py"
    
    with open(widget_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复 _minute_key_to_interval 方法的导入
    old_import = """        from vnpy.trader.constant import (
            MINUTE, MINUTE_5, MINUTE_15, MINUTE_30, HOUR,
        )
        return {
            "1m":  MINUTE,
            "5m":  MINUTE_5,
            "15m": MINUTE_15,
            "30m": MINUTE_30,
            "1h":  HOUR,
        }.get(key, MINUTE_5)"""
    
    new_import = """        from vnpy.trader.constant import Interval
        return {
            "1m":  Interval.MINUTE,
            "5m":  Interval.MINUTE_5,
            "15m": Interval.MINUTE_15,
            "30m": Interval.MINUTE_30,
            "1h":  Interval.HOUR,
        }.get(key, Interval.MINUTE_5)"""
    
    if old_import in content:
        content = content.replace(old_import, new_import)
        print("[OK] 修复了 Interval 常量导入")
    else:
        print("[WARN] 未找到需要修复的代码")
        return False
    
    with open(widget_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] 已保存到 {widget_path}")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("修复 Monitor Tab Interval 导入错误")
    print("=" * 60)
    
    success = fix_interval_import()
    
    if success:
        print("\n修复完成！")
        print("\n现在可以重新运行程序测试：")
        print("1. 执行回测")
        print("2. 切换到 Monitor Tab")
        print("3. 分钟K线应该能正常显示了")
    else:
        print("\n修复失败，请检查")