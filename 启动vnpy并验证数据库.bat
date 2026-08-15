@echo off
chcp 65001 >nul
echo ========================================
echo VNPy 启动脚本 - 带数据库验证
echo ========================================
echo.

echo [1/4] 检查配置文件...
python -c "import json; from pathlib import Path; config = Path.home() / '.vntrader' / 'vt_setting.json'; settings = json.load(open(config, encoding='utf-8')); print('数据库配置:', settings.get('database.database', '未配置'))"
echo.

echo [2/4] 验证数据库文件...
python -c "import os; db_path = r'E:\vnpy_data\database.db'; print('文件存在:', os.path.exists(db_path)); print('文件大小:', f'{os.path.getsize(db_path)/1024/1024/1024:.2f} GB' if os.path.exists(db_path) else 'N/A')"
echo.

echo [3/4] 测试数据库数据...
python -c "import sqlite3; conn = sqlite3.connect(r'E:\vnpy_data\database.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(DISTINCT symbol) FROM dbbardata WHERE exchange=\"SSE\"'); sse = cursor.fetchone()[0]; cursor.execute('SELECT COUNT(DISTINCT symbol) FROM dbbardata WHERE exchange=\"SZSE\"'); szse = cursor.fetchone()[0]; print(f'沪市股票: {sse} 只'); print(f'深市股票: {szse} 只'); conn.close()"
echo.

echo [4/4] 启动程序...
echo 提示：程序启动后，请测试股票池功能
echo.
python examples\veighna_trader\run.py

pause
