"""修复 _feed_monitor 中 except 块引用未初始化变量导致 NameError 的 bug"""
import io

path = "vnpy/strategy_condition/ui/widget.py"

with io.open(path, "r", encoding="utf-8") as f:
    src = f.read()

# 在 try: 之前插入变量初始化，确保 except 块安全访问
old = """        try:
            n_bars = self._nbars_sp.value()

            # 1. 优先复用 Chart Tab 已加载的原始 bars 作为日线"""

new = """        # 在外层 try 之前初始化所有变量，确保 except 块中安全访问
        daily_bars = None
        minute_bars = None
        daily_snapshots = None
        minute_snapshots = None
        try:
            n_bars = self._nbars_sp.value()

            # 1. 优先复用 Chart Tab 已加载的原始 bars 作为日线"""

assert old in src, "未找到目标代码块"
src = src.replace(old, new, 1)
print("[OK] 1: 在 try 之前初始化 daily_bars/minute_bars/daily_snapshots/minute_snapshots = None")

# 修复降级路径中 need a fallback for daily_bars
# 当 early return (line 1048-1050) 发生时，daily_bars 可能为 None 且被外层 except 捕获
# 但 early return 不会抛异常，所以不会被 except 捕获。真正的风险是：
# daily_bars 赋值后（line 1039/1046），daily_snapshots 生成失败（line 1070-1077）
# 此时 daily_bars 有值，但 daily_snapshots 可能未定义
# 不过 daily_snapshots 在 line 1070 被赋值，如果它抛异常，daily_snapshots 也未定义
# 所以初始化是必要的

# 另外，降级路径中 print 用了 len(minute_bars) if minute_bars else 0
# 但如果 minute_bars 是 None，len(None) 会 TypeError
# 已经在 print 中用 ternary 保护了，但 line 1169 的 len(minute_bars) if minute_bars else 0 是安全的

with io.open(path, "w", encoding="utf-8") as f:
    f.write(src)

print(f"\n[完成] 已修复 {path}")
print("初始化: daily_bars=None, minute_bars=None, daily_snapshots=None, minute_snapshots=None")
print("这样外层 except 块中引用这些变量时不会 NameError")