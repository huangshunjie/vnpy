"""检查数据库中的股票数据"""
import sqlite3

db_path = r'C:\Users\11229\.vntrader\database.db'
print(f"数据库路径: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查看所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"\n数据库表: {[t[0] for t in tables]}")

# 查询K线数据表
if any('dbbardata' in t[0].lower() for t in tables):
    # 统计总记录数
    cursor.execute("SELECT COUNT(*) FROM dbbardata")
    total = cursor.fetchone()[0]
    print(f"\nK线总记录数: {total}")
    
    # 统计唯一合约数
    cursor.execute("SELECT COUNT(DISTINCT symbol || '.' || exchange) FROM dbbardata")
    contracts = cursor.fetchone()[0]
    print(f"唯一合约数: {contracts}")
    
    # 统计各交易所
    cursor.execute("""
        SELECT exchange, COUNT(DISTINCT symbol) as count 
        FROM dbbardata 
        GROUP BY exchange
    """)
    exchanges = cursor.fetchall()
    print(f"\n各交易所股票数:")
    for ex, count in exchanges:
        print(f"  {ex}: {count} 只")
    
    # 查看SSE和SZSE的示例
    for exchange in ['SSE', 'SZSE']:
        cursor.execute(f"""
            SELECT DISTINCT symbol 
            FROM dbbardata 
            WHERE exchange = '{exchange}'
            LIMIT 5
        """)
        symbols = cursor.fetchall()
        if symbols:
            print(f"\n{exchange} 示例股票: {[s[0] for s in symbols]}")
        else:
            print(f"\n{exchange}: 无数据")
else:
    print("\n[ERROR] 未找到 dbbardata 表！")

conn.close()
