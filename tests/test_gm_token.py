"""test_gm_token.py — 测试掘金 token 是否有效"""
from gm.api import set_token, get_trading_dates

token = "e76f23e41181807f6c29d08cf88b894f8f8d9c76"

try:
    set_token(token)
    dates = get_trading_dates(exchange="SHFE", start_date="2025-07-01", end_date="2025-07-08")
    print(f"Token 有效！获取到 {len(dates)} 个交易日")
    print(dates)
except Exception as e:
    print(f"Token 无效或连接失败: {e}")
