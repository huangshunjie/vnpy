"""清理stock_pool.py中的重复定义并完成优化"""

# 读取文件
with open("vnpy/trader/stock_pool.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# 移除重复的_CACHE_LOADING定义（第60行）
new_lines = []
cache_loading_seen = False
for i, line in enumerate(lines):
    if "_CACHE_LOADING = False  # 标记：是否正在后台加载数据" in line:
        if not cache_loading_seen:
            new_lines.append(line)
            cache_loading_seen = True
        else:
            print(f"移除重复行 {i+1}: {line.strip()}")
    else:
        new_lines.append(line)

# 写回文件
with open("vnpy/trader/stock_pool.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("[OK] 已清理重复定义")
print("[OK] stock_pool.py 优化完成")
