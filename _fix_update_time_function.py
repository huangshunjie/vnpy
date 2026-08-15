"""修复 stock_pool.py 中的 get_pool_update_time 函数"""

import re

# 读取文件
with open('vnpy/trader/stock_pool.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换 get_pool_update_time 函数
# 旧的函数实现
old_function = r'''def get_pool_update_time\(\) -> str:
    """获取股票池数据的更新时间（用于UI显示）"""
    try:
        cache_path = Path\.home\(\) / "\.vnpy" / "stock_pool_cache\.json"
        if cache_path\.exists\(\):
            with open\(cache_path, 'r', encoding='utf-8'\) as f:
                cache_data = json\.load\(f\)
                return cache_data\.get\('update_time', ''\)
    except Exception:
        pass
    return ""'''

# 新的函数实现
new_function = '''def get_pool_update_time() -> str:
    """获取股票池数据的更新时间（用于UI显示）"""
    try:
        cache_path = _CACHE_DIR / "symbols_cache.json"
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                return cache_data.get('update_time', '')
    except Exception:
        pass
    return ""'''

# 执行替换
content_new = re.sub(old_function, new_function, content, flags=re.DOTALL)

if content_new != content:
    # 写回文件
    with open('vnpy/trader/stock_pool.py', 'w', encoding='utf-8') as f:
        f.write(content_new)
    print("✓ 已修复 get_pool_update_time 函数")
    print("  - 修改缓存路径为: _CACHE_DIR / 'symbols_cache.json'")
else:
    print("× 未找到需要替换的内容，尝试手动查找...")
    
    # 查找函数位置
    match = re.search(r'def get_pool_update_time.*?(?=\ndef [a-z_]|\nclass |\Z)', content, re.DOTALL)
    if match:
        print(f"\n找到的函数内容：\n{match.group(0)[:500]}")
    else:
        print("未找到 get_pool_update_time 函数")
