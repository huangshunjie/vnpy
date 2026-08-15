# -*- coding: utf-8 -*-
"""
测试直接从E盘数据库读取数据
"""
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 70)
print("测试读取E盘数据库")
print("=" * 70)

# 1. 确认配置
from vnpy.trader.setting import SETTINGS
print(f"\n1. 配置检查:")
print(f"   database.database = {SETTINGS.get('database.database')}")
print(f"   database.driver = {SETTINGS.get('database.driver')}")

# 2. 获取数据库实例
from vnpy.trader.database import get_database
db = get_database()
print(f"\n2. 数据库实例:")
print(f"   类型: {type(db)}")
print(f"   类名: {db.__class__.__name__}")

# 3. 测试get_bar_overview()
print(f"\n3. 测试 get_bar_overview():")
try:
    overview = db.get_bar_overview()
    print(f"   返回类型: {type(overview)}")
    print(f"   返回长度: {len(overview)}")
    
    if len(overview) > 0:
        print(f"\n   前5个条目:")
        for i, item in enumerate(list(overview)[:5]):
            print(f"     {i+1}. {item}")
    else:
        print(f"   [警告] 返回为空！")
        
except Exception as e:
    print(f"   [错误] {e}")
    import traceback
    traceback.print_exc()

# 4. 直接查询数据库
print(f"\n4. 直接SQL查询:")
try:
    # 对于vnpy_sqlite，获取底层peewee数据库连接
    if hasattr(db, 'db'):
        print(f"   有db属性")
        import vnpy_sqlite.sqlite_database as sqlite_module
        
        # 直接查询
        DbBarData = sqlite_module.DbBarData
        
        # 统计总数
        total = DbBarData.select().count()
        print(f"   总记录数: {total:,}")
        
        # 按交易所统计
        from vnpy.trader.constant import Exchange
        for exchange in [Exchange.SSE, Exchange.SZSE]:
            count = DbBarData.select().where(
                DbBarData.exchange == exchange.value
            ).count()
            
            # 获取唯一股票数
            symbols = DbBarData.select(DbBarData.symbol).where(
                DbBarData.exchange == exchange.value
            ).distinct()
            symbol_count = len(list(symbols))
            
            print(f"   {exchange.value}: {symbol_count} 只股票，{count:,} 条记录")
        
        # 显示样本数据
        print(f"\n   前3条记录:")
        for bar in DbBarData.select().limit(3):
            print(f"     {bar.symbol}.{bar.exchange} {bar.datetime} {bar.interval}")
            
    else:
        print(f"   [警告] 数据库对象没有db属性")
        
except Exception as e:
    print(f"   [错误] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
