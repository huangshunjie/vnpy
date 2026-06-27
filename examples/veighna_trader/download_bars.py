"""
download_bars.py

批量从 Tushare 下载 A 股日线数据到本地 SQLite 数据库。
运行一次即可，数据永久保存，后续批量回测直接从数据库读取。

用法：
    D:\veighna_studio\python.exe download_bars.py
"""

from datetime import datetime
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import HistoryRequest
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.database import get_database

# ------------------------------------------------------------------ #
#  配置：要下载的股票池
# ------------------------------------------------------------------ #

SYMBOLS = [
    # 沪深300成分股（示例，可自行扩充）
    ("000001", Exchange.SZSE),   # 平安银行
    ("000002", Exchange.SZSE),   # 万科A
    ("000333", Exchange.SZSE),   # 美的集团
    ("000651", Exchange.SZSE),   # 格力电器
    ("000858", Exchange.SZSE),   # 五粮液
    ("001979", Exchange.SZSE),   # 招商蛇口
    ("002415", Exchange.SZSE),   # 海康威视
    ("002594", Exchange.SZSE),   # 比亚迪
    ("300059", Exchange.SZSE),   # 东方财富
    ("300750", Exchange.SZSE),   # 宁德时代
    ("600000", Exchange.SSE),    # 浦发银行
    ("600009", Exchange.SSE),    # 上海机场
    ("600016", Exchange.SSE),    # 民生银行
    ("600019", Exchange.SSE),    # 宝钢股份
    ("600028", Exchange.SSE),    # 中国石化
    ("600030", Exchange.SSE),    # 中信证券
    ("600036", Exchange.SSE),    # 招商银行
    ("600050", Exchange.SSE),    # 中国联通
    ("600276", Exchange.SSE),    # 恒瑞医药
    ("600309", Exchange.SSE),    # 万华化学
    ("600519", Exchange.SSE),    # 贵州茅台
    ("600585", Exchange.SSE),    # 海螺水泥
    ("600588", Exchange.SSE),    # 用友网络
    ("600690", Exchange.SSE),    # 海尔智家
    ("600887", Exchange.SSE),    # 伊利股份
    ("600900", Exchange.SSE),    # 长江电力
    ("601012", Exchange.SSE),    # 隆基绿能
    ("601066", Exchange.SSE),    # 中信建投
    ("601088", Exchange.SSE),    # 中国神华
    ("601166", Exchange.SSE),    # 兴业银行
    ("601288", Exchange.SSE),    # 农业银行
    ("601318", Exchange.SSE),    # 中国平安
    ("601398", Exchange.SSE),    # 工商银行
    ("601601", Exchange.SSE),    # 中国太保
    ("601628", Exchange.SSE),    # 中国人寿
    ("601688", Exchange.SSE),    # 华泰证券
    ("601857", Exchange.SSE),    # 中国石油
    ("601888", Exchange.SSE),    # 中国中免
    ("601899", Exchange.SSE),    # 紫金矿业
    ("603288", Exchange.SSE),    # 海天味业
]

START = datetime(2020, 1, 1)
END   = datetime(2024, 12, 31)
INTERVAL = Interval.DAILY

# ------------------------------------------------------------------ #
#  下载
# ------------------------------------------------------------------ #

def main():
    datafeed = get_datafeed()
    database = get_database()

    total   = len(SYMBOLS)
    success = 0
    failed  = []

    print(f"开始下载：{total} 只股票  {START.date()} ~ {END.date()}")
    print("-" * 55)

    for i, (symbol, exchange) in enumerate(SYMBOLS, 1):
        vt_symbol = f"{symbol}.{exchange.value}"
        req = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            start=START,
            end=END,
            interval=INTERVAL,
        )
        try:
            bars = datafeed.query_bar_history(req)
            if bars:
                database.save_bar_data(bars)
                print(f"[{i:3}/{total}]  OK   {vt_symbol}  {len(bars)} 根")
                success += 1
            else:
                print(f"[{i:3}/{total}]  空   {vt_symbol}  (无数据返回)")
                failed.append(vt_symbol)
        except Exception as e:
            print(f"[{i:3}/{total}]  ERR  {vt_symbol}  {e}")
            failed.append(vt_symbol)

    print("-" * 55)
    print(f"完成：成功 {success}，失败 {len(failed)}")
    if failed:
        print("失败列表：", failed)


if __name__ == "__main__":
    main()
