"""
在股票池数量显示右侧添加更新时间

修改内容：
1. 在 stock_pool.py 中添加获取更新时间的函数
2. 在 behavior_tab.py 中修改显示股票池数量的3处代码，添加更新时间
"""

import re
from pathlib import Path

def add_get_update_time_function():
    """在stock_pool.py中添加获取更新时间的函数"""
    
    stock_pool_path = Path("vnpy/trader/stock_pool.py")
    content = stock_pool_path.read_text(encoding="utf-8")
    
    # 检查函数是否已存在
    if "def get_pool_update_time" in content:
        print("[OK] get_pool_update_time函数已存在")
        return
    
    # 在get_cache_status函数后添加新函数
    new_function = '''

def get_pool_update_time() -> str:
    """获取股票池数据的更新时间（用于UI显示）"""
    try:
        cache_path = _get_cache_path()
        if cache_path.exists():
            import json
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                update_time = data.get('update_time', '')
                if update_time:
                    # 格式化时间显示，例如：2026-08-15 14:30
                    from datetime import datetime
                    dt = datetime.fromisoformat(update_time)
                    return dt.strftime('%Y-%m-%d %H:%M')
        return ''
    except Exception as e:
        return ''
'''
    
    # 在文件末尾添加新函数
    content = content.rstrip() + new_function + "\n"
    
    stock_pool_path.write_text(content, encoding="utf-8")
    print("[OK] 已在stock_pool.py中添加get_pool_update_time函数")


def modify_behavior_tab():
    """修改behavior_tab.py中的显示代码"""
    
    behavior_tab_path = Path("vnpy/quant_research/ui/behavior_tab.py")
    content = behavior_tab_path.read_text(encoding="utf-8")
    
    # 检查是否已经导入stock_pool模块
    if "from vnpy.trader import stock_pool" not in content:
        # 在导入部分添加stock_pool导入
        import_pattern = r'(from \.\.engine import ResearchEngine)'
        import_replacement = r'from vnpy.trader import stock_pool\n\1'
        content = re.sub(import_pattern, import_replacement, content)
        print("[OK] 已添加stock_pool模块导入")
    
    # 修改第一处：_set_board_pool函数中的显示
    pattern1 = r'self\._pool_count_lbl\.setText\(f"{self\._current_pool_name} - {len\(symbols\)} 只"\)'
    replacement1 = '''update_time = stock_pool.get_pool_update_time()
            time_str = f" (更新: {update_time})" if update_time else ""
            self._pool_count_lbl.setText(f"{self._current_pool_name} - {len(symbols)} 只{time_str}")'''
    
    if re.search(pattern1, content):
        content = re.sub(pattern1, replacement1, content)
        print("[OK] 已修改_set_board_pool函数中的显示代码")
    else:
        print("[WARN] 未找到_set_board_pool函数中的显示代码")
    
    # 修改第二处：有name参数的显示
    pattern2 = r'self\._pool_count_lbl\.setText\(f"{name} - {count} 只"\)'
    replacement2 = '''update_time = stock_pool.get_pool_update_time()
            time_str = f" (更新: {update_time})" if update_time else ""
            self._pool_count_lbl.setText(f"{name} - {count} 只{time_str}")'''
    
    if re.search(pattern2, content):
        content = re.sub(pattern2, replacement2, content)
        print("[OK] 已修改有name参数的显示代码")
    else:
        print("[WARN] 未找到有name参数的显示代码")
    
    # 修改第三处：只有count的显示
    pattern3 = r'(\s+)else:\s+self\._pool_count_lbl\.setText\(f"{count} 只"\)'
    replacement3 = r'''\1else:
\1    update_time = stock_pool.get_pool_update_time()
\1    time_str = f" (更新: {update_time})" if update_time else ""
\1    self._pool_count_lbl.setText(f"{count} 只{time_str}")'''
    
    if re.search(pattern3, content):
        content = re.sub(pattern3, replacement3, content)
        print("[OK] 已修改只有count的显示代码")
    else:
        print("[WARN] 未找到只有count的显示代码")
    
    behavior_tab_path.write_text(content, encoding="utf-8")
    print("[OK] 已保存behavior_tab.py")


def main():
    print("=" * 60)
    print("开始添加股票池更新时间显示功能")
    print("=" * 60)
    
    try:
        # 步骤1：添加获取更新时间的函数
        print("\n步骤1: 在stock_pool.py中添加get_pool_update_time函数...")
        add_get_update_time_function()
        
        # 步骤2：修改behavior_tab.py的显示代码
        print("\n步骤2: 修改behavior_tab.py的显示代码...")
        modify_behavior_tab()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] 修改完成!")
        print("=" * 60)
        print("\n现在重启应用程序，股票池数量右侧将显示更新时间")
        print("例如：创业板 - 1402 只 (更新: 2026-08-15 14:30)")
        
    except Exception as e:
        print(f"\n[ERROR] 修改失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
