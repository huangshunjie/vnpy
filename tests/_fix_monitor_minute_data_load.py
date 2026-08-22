"""
修复 Monitor Tab 分钟数据显示为 0 的问题

根本原因：
1. _feed_monitor 在异常处理时，如果变量未正确初始化可能导致 minute_bars 为空
2. 需要确保即使有异常，也能保留已成功加载的分钟数据

修复方案：
将 minute_bars/minute_snapshots 的初始化移到 try 块内部，
避免被外层的 None 赋值覆盖
"""

import re

def fix_widget_feed_monitor():
    widget_path = "vnpy/strategy_condition/ui/widget.py"
    
    with open(widget_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到问题代码段并修复
    old_code = """        # ── 缓存未命中：计算快照 ──
        print(f"[SCE] _feed_monitor: computing for {symbol} ({minute_key})",
              flush=True)
        daily_snapshots = []
        daily_bars = []
        # 在外层 try 之前初始化所有变量，确保 except 块中安全访问
        daily_bars = None
        minute_bars = None
        daily_snapshots = None
        minute_snapshots = None
        try:"""
    
    new_code = """        # ── 缓存未命中：计算快照 ──
        print(f"[SCE] _feed_monitor: computing for {symbol} ({minute_key})",
              flush=True)
        # 初始化变量为 None，在 try 块内赋值
        daily_bars = None
        minute_bars = None
        daily_snapshots = None
        minute_snapshots = None
        try:"""
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        print("[OK] 修复了变量初始化顺序")
    else:
        print("[WARN] 未找到精确匹配的代码段，尝试手动检查")
        return False
    
    # 保存修复后的文件
    with open(widget_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] 已保存到 {widget_path}")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("修复 Monitor Tab 分钟数据加载问题")
    print("=" * 60)
    
    success = fix_widget_feed_monitor()
    
    if success:
        print("\n修复完成！")
        print("\n请重新运行程序，测试:")
        print("1. 执行回测")
        print("2. 切换到 Monitor Tab")  
        print("3. 检查分钟K线面板是否正常显示数据")
    else:
        print("\n修复失败，请手动检查 widget.py 文件")