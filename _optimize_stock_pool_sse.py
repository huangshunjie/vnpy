"""
优化股票池沪市按钮性能问题

问题分析：
1. 当缓存过期时，_ensure_symbols_cache() 会在UI线程同步查询数据库
2. 沪市2000+股票，查询需要数秒，导致UI冻结
3. 虽然有异步查询函数，但没有被使用

优化方案：
1. 真正使用异步加载：缓存过期时启动后台线程，UI不阻塞
2. 添加加载状态标志：让UI知道正在后台加载
3. 改进用户体验：显示友好的"正在加载"提示
4. 保留同步刷新函数：仅用于force_refresh_cache()
"""

import re

# 读取原文件
with open("vnpy/trader/stock_pool.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 添加全局加载标志（在缓存变量定义之后）
cache_vars_pattern = r'(_CACHE_LOCK = Lock\(\)  # 线程锁（保留用于未来扩展）)'
cache_vars_replacement = r'\1\n_CACHE_LOADING = False  # 标记：是否正在后台加载数据'

content = re.sub(cache_vars_pattern, cache_vars_replacement, content)

# 2. 修改 _ensure_symbols_cache() 函数，使用真正的异步加载
old_ensure_function = r'''def _ensure_symbols_cache\(\) -> Set\[str\]:
    """
    Ensure symbols cache is available\.
    Strategy: memory cache -> disk cache -> async database query \(return empty first\)
    
    性能优化关键：
    1\. 优先使用内存缓存（5分钟有效期）
    2\. 其次使用磁盘缓存（24小时有效期）
    3\. 如果都没有，启动后台线程查询数据库，先返回空集合
    4\. 避免在主线程（UI线程）阻塞查询大数据库
    """
    global _LOCAL_SYMBOLS_CACHE, _CACHE_TIMESTAMP, _CACHE_LOADING

    current_time = time\.time\(\)

    # 1\. 检查内存缓存（最快）
    if _LOCAL_SYMBOLS_CACHE is not None and \(current_time - _CACHE_TIMESTAMP\) <= _CACHE_EXPIRE_SECONDS:
        return _LOCAL_SYMBOLS_CACHE

    # 2\. 检查磁盘缓存（较快）
    if _LOCAL_SYMBOLS_CACHE is None:
        disk_cache = _load_symbols_disk_cache\(\)
        if disk_cache is not None:
            _LOCAL_SYMBOLS_CACHE = disk_cache
            _CACHE_TIMESTAMP = current_time
            return _LOCAL_SYMBOLS_CACHE

    # 3\. 磁盘缓存也过期了，同步查询数据库（修复UI不更新问题）
    try:
        from vnpy\.trader\.database import get_database
        from vnpy\.trader\.constant import Interval
        
        logger\.info\("缓存过期，开始同步查询数据库\.\.\."\)
        start_time = time\.time\(\)
        
        db = get_database\(\)
        overview = db\.get_bar_overview\(\)
        
        local_symbols = set\(\)
        for o in overview:
            if o\.interval == Interval\.DAILY:
                local_symbols\.add\(f"\{o\.symbol\}\.\{o\.exchange\.value\}"\)
        
        elapsed = time\.time\(\) - start_time
        logger\.info\(f"数据库查询完成: \{len\(local_symbols\)\} symbols, 耗时 \{elapsed:\.1f\}秒"\)
        
        _LOCAL_SYMBOLS_CACHE = local_symbols
        _CACHE_TIMESTAMP = time\.time\(\)
        _save_symbols_disk_cache\(local_symbols\)
        
        return _LOCAL_SYMBOLS_CACHE
    except Exception as e:
        logger\.error\(f"同步查询数据库失败: \{e\}"\)
        if _LOCAL_SYMBOLS_CACHE is not None:
            logger\.warning\("使用过期的内存缓存"\)
            return _LOCAL_SYMBOLS_CACHE
        return set\(\)'''

new_ensure_function = '''def _ensure_symbols_cache() -> Set[str]:
    """
    Ensure symbols cache is available.
    Strategy: memory cache -> disk cache -> async database query (return empty first)
    
    性能优化关键（真正的异步实现）：
    1. 优先使用内存缓存（5分钟有效期）
    2. 其次使用磁盘缓存（24小时有效期）
    3. 如果都没有，启动后台线程查询数据库，先返回空集合（UI不阻塞）
    4. 避免在主线程（UI线程）阻塞查询大数据库
    """
    global _LOCAL_SYMBOLS_CACHE, _CACHE_TIMESTAMP, _CACHE_LOADING

    current_time = time.time()

    # 1. 检查内存缓存（最快）
    if _LOCAL_SYMBOLS_CACHE is not None and (current_time - _CACHE_TIMESTAMP) <= _CACHE_EXPIRE_SECONDS:
        return _LOCAL_SYMBOLS_CACHE

    # 2. 检查磁盘缓存（较快）
    if _LOCAL_SYMBOLS_CACHE is None:
        disk_cache = _load_symbols_disk_cache()
        if disk_cache is not None:
            _LOCAL_SYMBOLS_CACHE = disk_cache
            _CACHE_TIMESTAMP = current_time
            return _LOCAL_SYMBOLS_CACHE

    # 3. 磁盘缓存也过期了，启动后台异步加载（UI不阻塞）
    if not _CACHE_LOADING:
        _CACHE_LOADING = True
        logger.info("缓存过期，启动后台异步加载...")
        thread = Thread(target=_query_database_async, daemon=True)
        thread.start()
    
    # 返回当前缓存（可能为空或过期），UI不会被阻塞
    # UI层会显示"正在加载"提示，用户可以稍后重试
    if _LOCAL_SYMBOLS_CACHE is not None:
        logger.info("使用过期缓存，后台正在更新...")
        return _LOCAL_SYMBOLS_CACHE
    else:
        logger.info("缓存为空，后台正在加载，请稍后重试")
        return set()'''

content = re.sub(old_ensure_function, new_ensure_function, content, flags=re.DOTALL)

# 3. 添加新的同步查询函数（仅用于force_refresh）
sync_function = '''

def _query_database_sync() -> Set[str]:
    """同步查询数据库（阻塞式）
    
    仅用于 force_refresh_cache()，不要在UI线程调用！
    """
    try:
        from vnpy.trader.database import get_database
        from vnpy.trader.constant import Interval
        
        logger.info("开始同步查询数据库...")
        start_time = time.time()
        
        db = get_database()
        overview = db.get_bar_overview()
        
        local_symbols = set()
        for o in overview:
            if o.interval == Interval.DAILY:
                local_symbols.add(f"{o.symbol}.{o.exchange.value}")
        
        elapsed = time.time() - start_time
        logger.info(f"数据库查询完成: {len(local_symbols)} symbols, 耗时 {elapsed:.1f}秒")
        
        return local_symbols
    except Exception as e:
        logger.error(f"同步查询数据库失败: {e}")
        return set()
'''

# 在 preload_cache() 之前插入
content = content.replace(
    '\ndef preload_cache():',
    sync_function + '\ndef preload_cache():'
)

# 4. 更新 force_refresh_cache() 使用同步查询
old_force_refresh = r'''def force_refresh_cache\(\):
    """强制刷新缓存（立即查询数据库，阻塞式）
    
    注意：此函数会阻塞当前线程，不要在UI线程调用！
    适用场景：用户导入了新数据，需要立即更新缓存。
    """
    global _LOCAL_SYMBOLS_CACHE, _CACHE_TIMESTAMP
    
    try:
        from vnpy\.trader\.database import get_database
        from vnpy\.trader\.constant import Interval
        
        logger\.info\("强制刷新缓存：查询数据库\.\.\."\)
        start_time = time\.time\(\)
        
        db = get_database\(\)
        overview = db\.get_bar_overview\(\)
        
        local_symbols = set\(\)
        for o in overview:
            if o\.interval == Interval\.DAILY:
                local_symbols\.add\(f"\{o\.symbol\}\.\{o\.exchange\.value\}"\)
        
        elapsed = time\.time\(\) - start_time
        logger\.info\(f"缓存刷新完成: \{len\(local_symbols\)\} symbols, 耗时 \{elapsed:\.1f\}秒"\)
        
        _LOCAL_SYMBOLS_CACHE = local_symbols
        _CACHE_TIMESTAMP = time\.time\(\)
        _save_symbols_disk_cache\(local_symbols\)
        
        return True, f"成功刷新 \{len\(local_symbols\)\} 只股票"
    
    except Exception as e:
        error_msg = f"刷新缓存失败: \{e\}"
        logger\.error\(error_msg\)
        return False, error_msg'''

new_force_refresh = '''def force_refresh_cache():
    """强制刷新缓存（立即查询数据库，阻塞式）
    
    注意：此函数会阻塞当前线程，不要在UI线程调用！
    适用场景：用户导入了新数据，需要立即更新缓存。
    """
    global _LOCAL_SYMBOLS_CACHE, _CACHE_TIMESTAMP, _CACHE_LOADING
    
    _CACHE_LOADING = True  # 防止并发查询
    
    try:
        local_symbols = _query_database_sync()
        
        if local_symbols:
            _LOCAL_SYMBOLS_CACHE = local_symbols
            _CACHE_TIMESTAMP = time.time()
            _save_symbols_disk_cache(local_symbols)
            
            msg = f"成功刷新 {len(local_symbols)} 只股票"
            logger.info(msg)
            return True, msg
        else:
            return False, "查询数据库返回空结果"
    
    except Exception as e:
        error_msg = f"刷新缓存失败: {e}"
        logger.error(error_msg)
        return False, error_msg
    finally:
        _CACHE_LOADING = False'''

content = re.sub(old_force_refresh, new_force_refresh, content, flags=re.DOTALL)

# 5. 添加检查加载状态的函数
status_function = '''

def is_cache_loading() -> bool:
    """检查缓存是否正在后台加载"""
    return _CACHE_LOADING


def get_cache_status() -> dict:
    """获取缓存状态信息（用于UI显示）"""
    return {
        "has_cache": _LOCAL_SYMBOLS_CACHE is not None,
        "cache_count": len(_LOCAL_SYMBOLS_CACHE) if _LOCAL_SYMBOLS_CACHE else 0,
        "is_loading": _CACHE_LOADING,
        "cache_age_seconds": time.time() - _CACHE_TIMESTAMP if _CACHE_TIMESTAMP > 0 else None,
    }
'''

# 在文件末尾添加
content = content.rstrip() + status_function

# 写入文件
with open("vnpy/trader/stock_pool.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 已优化 stock_pool.py")
print("\n主要改进：")
print("1. ✅ 添加 _CACHE_LOADING 全局标志")
print("2. ✅ _ensure_symbols_cache() 使用真正的异步加载")
print("3. ✅ 添加 _query_database_sync() 同步查询函数")
print("4. ✅ 更新 force_refresh_cache() 使用新的同步函数")
print("5. ✅ 添加 is_cache_loading() 和 get_cache_status() 状态检查")
print("\n现在需要更新 UI 代码以显示加载状态...")
