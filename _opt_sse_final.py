"""
修复股票池按钮点击后不更新的问题 - 简化版

问题原因：
stock_pool.py的_ensure_symbols_cache()使用异步后台加载，
第一次调用时返回空集合，导致UI文本框不更新。

解决方案：
修改stock_pool.py，使用同步加载而不是异步加载。
"""

# 读取stock_pool.py
with open("vnpy/trader/stock_pool.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# 找到_ensure_symbols_cache函数并修改
new_lines = []
in_ensure_cache = False
skip_until_return = False

for i, line in enumerate(lines):
    if "def _ensure_symbols_cache() -> Set[str]:" in line:
        in_ensure_cache = True
        new_lines.append(line)
        continue
    
    if in_ensure_cache and line.strip().startswith("# 3. 磁盘缓存也过期了"):
        # 替换异步加载逻辑为同步加载
        new_lines.append("    # 3. 磁盘缓存也过期了，同步查询数据库（修复UI不更新问题）\n")
        new_lines.append("    try:\n")
        new_lines.append("        from vnpy.trader.database import get_database\n")
        new_lines.append("        from vnpy.trader.constant import Interval\n")
        new_lines.append("        import time\n")
        new_lines.append("        \n")
        new_lines.append("        logger.info(\"缓存过期，开始同步查询数据库...\")\n")
        new_lines.append("        start_time = time.time()\n")
        new_lines.append("        \n")
        new_lines.append("        db = get_database()\n")
        new_lines.append("        overview = db.get_bar_overview()\n")
        new_lines.append("        \n")
        new_lines.append("        local_symbols = set()\n")
        new_lines.append("        for o in overview:\n")
        new_lines.append("            if o.interval == Interval.DAILY:\n")
        new_lines.append("                local_symbols.add(f\"{o.symbol}.{o.exchange.value}\")\n")
        new_lines.append("        \n")
        new_lines.append("        elapsed = time.time() - start_time\n")
        new_lines.append("        logger.info(f\"数据库查询完成: {len(local_symbols)} symbols, 耗时 {elapsed:.1f}秒\")\n")
        new_lines.append("        \n")
        new_lines.append("        _LOCAL_SYMBOLS_CACHE = local_symbols\n")
        new_lines.append("        _CACHE_TIMESTAMP = time.time()\n")
        new_lines.append("        _save_symbols_disk_cache(local_symbols)\n")
        new_lines.append("        \n")
        new_lines.append("        return _LOCAL_SYMBOLS_CACHE\n")
        new_lines.append("    except Exception as e:\n")
        new_lines.append("        logger.error(f\"同步查询数据库失败: {e}\")\n")
        new_lines.append("        return set()\n")
        
        skip_until_return = True
        continue
    
    if skip_until_return:
        # 跳过原有的异步加载代码，直到遇到下一个函数定义
        if line.strip().startswith("def ") and "def _ensure_symbols_cache" not in line:
            in_ensure_cache = False
            skip_until_return = False
            new_lines.append("\n")
            new_lines.append(line)
        continue
    
    new_lines.append(line)

# 保存文件
with open("vnpy/trader/stock_pool.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("✓ 修复完成！")
print("\n修改说明：")
print("1. 将_ensure_symbols_cache从异步加载改为同步加载")
print("2. 现在点击按钮后会直接查询数据库并更新UI")
print("3. 首次加载可能需要几秒钟，但UI会正确显示数据")
print("\n请重新启动应用程序测试！")
