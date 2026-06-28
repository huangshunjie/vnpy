"""
data_manager.py

A 股数据管理工具：
  1. 查看本地数据库中已有的数据
  2. 从 Tushare 下载全市场（或指定范围）A 股日线数据

用法：
    # 只查看数据库现有数据
    python data_manager.py --show

    # 下载全市场日线（自动跳过已有的）
    python data_manager.py --download

    # 下载并强制更新已有数据（追加最新 K 线）
    python data_manager.py --download --update

    # 只下载沪市
    python data_manager.py --download --exchange SSE

    # 自定义时间范围
    python data_manager.py --download --start 2018-01-01 --end 2024-12-31
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path


# ------------------------------------------------------------------ #
#  CLI 参数解析
# ------------------------------------------------------------------ #

def parse_args():
    p = argparse.ArgumentParser(description="A 股日线数据管理工具")
    p.add_argument("--show",     action="store_true", help="查看数据库现有数据")
    p.add_argument("--download", action="store_true", help="下载全市场日线数据")
    p.add_argument("--update",   action="store_true", help="配合 --download：强制更新已有数据")
    p.add_argument("--exchange", default="",          help="限定交易所：SSE / SZSE / BSE，默认全部")
    p.add_argument("--start",    default="2010-01-01",help="下载起始日期，默认 2010-01-01")
    p.add_argument("--end",      default="",          help="下载结束日期，默认今天")
    p.add_argument("--workers",  type=int, default=1, help="并行下载线程数，默认 1（Tushare 免费版建议 1）")
    p.add_argument("--batch",    type=int, default=20, help="每批下载只数，批次间休眠以避免限频")
    p.add_argument("--sleep",    type=float, default=1.2, help="每批下载后的休眠秒数")
    return p.parse_args()


# ------------------------------------------------------------------ #
#  查看数据库现有数据
# ------------------------------------------------------------------ #

def show_database():
    from vnpy.trader.database import get_database
    from vnpy.trader.constant import Interval

    db = get_database()
    overviews = db.get_bar_overview()

    if not overviews:
        print("数据库为空，还没有任何 K 线数据。")
        return

    # 只看日线
    daily = [o for o in overviews if o.interval == Interval.DAILY]
    others = [o for o in overviews if o.interval != Interval.DAILY]

    print(f"\n{'=' * 65}")
    print(f"  数据库概况：共 {len(overviews)} 条记录，其中日线 {len(daily)} 只")
    print(f"{'=' * 65}")

    if daily:
        # 按交易所分组统计
        from collections import defaultdict
        by_ex: dict[str, list] = defaultdict(list)
        for o in sorted(daily, key=lambda x: x.symbol):
            by_ex[o.exchange.value].append(o)

        total_bars = sum(o.count for o in daily)
        print(f"\n  日线数据汇总（总 K 线数：{total_bars:,}）\n")

        for ex in sorted(by_ex):
            items = by_ex[ex]
            bars = sum(o.count for o in items)
            start_dates = [str(o.start)[:10] for o in items]
            end_dates   = [str(o.end)[:10]   for o in items]
            print(f"  {ex:6s}  {len(items):4d} 只  "
                  f"最早 {min(start_dates)}  最新 {max(end_dates)}  "
                  f"共 {bars:,} 根")

        print(f"\n  {'股票代码':<16} {'交易所':<6} {'起始日期':<12} {'结束日期':<12} {'K线数':>8}")
        print(f"  {'-'*60}")
        for o in sorted(daily, key=lambda x: (x.exchange.value, x.symbol)):
            print(f"  {o.symbol + '.' + o.exchange.value:<16} "
                  f"{o.exchange.value:<6} "
                  f"{str(o.start)[:10]:<12} "
                  f"{str(o.end)[:10]:<12} "
                  f"{o.count:>8,}")

    if others:
        print(f"\n  其他周期数据：")
        for o in others:
            print(f"  {o.symbol}.{o.exchange.value}  {o.interval.value}  "
                  f"{str(o.start)[:10]} ~ {str(o.end)[:10]}  {o.count} 根")

    print(f"\n{'=' * 65}\n")


# ------------------------------------------------------------------ #
#  下载全市场数据
# ------------------------------------------------------------------ #

def get_all_a_stocks(exchange_filter: str) -> list[tuple[str, str]]:
    """从 Tushare 获取全部上市 A 股列表，返回 [(symbol, exchange), ...]"""
    import tushare as ts
    from vnpy.trader.setting import SETTINGS

    token = SETTINGS.get("datafeed.password", "")
    if not token:
        raise RuntimeError("未找到 datafeed.password（Tushare token），请在全局配置中填写。")

    pro = ts.pro_api(token)

    # Tushare 交易所代码 → VeighNa Exchange
    ex_map = {"SSE": "SSE", "SZSE": "SZSE", "BSE": "BSE"}

    all_stocks: list[tuple[str, str]] = []
    for ts_ex, vt_ex in ex_map.items():
        if exchange_filter and exchange_filter.upper() != vt_ex:
            continue
        df = pro.stock_basic(
            exchange=ts_ex,
            list_status="L",
            fields="ts_code,symbol,name,exchange,list_date",
        )
        for _, row in df.iterrows():
            sym = row["symbol"]          # 纯数字代码，如 600519
            all_stocks.append((sym, vt_ex))

    return all_stocks


def download_all(args) -> None:
    from vnpy.trader.constant import Exchange, Interval
    from vnpy.trader.object import HistoryRequest
    from vnpy.trader.datafeed import get_datafeed
    from vnpy.trader.database import get_database

    start_dt = datetime.strptime(args.start, "%Y-%m-%d")
    end_dt   = (datetime.strptime(args.end, "%Y-%m-%d")
                if args.end else datetime.today().replace(hour=0, minute=0, second=0, microsecond=0))

    print(f"\n正在获取股票列表...")
    stocks = get_all_a_stocks(args.exchange)
    print(f"共找到 {len(stocks)} 只股票（交易所：{args.exchange or '全部'}）\n")

    # 查询数据库已有记录
    db = get_database()
    overviews = db.get_bar_overview()
    from vnpy.trader.constant import Interval as Iv
    have: dict[str, tuple[datetime, datetime]] = {
        f"{o.symbol}.{o.exchange.value}": (o.start, o.end)
        for o in overviews if o.interval == Iv.DAILY
    }

    datafeed = get_datafeed()

    total   = len(stocks)
    success = 0
    skipped = 0
    failed  = []

    ex_obj_map = {
        "SSE":  Exchange.SSE,
        "SZSE": Exchange.SZSE,
        "BSE":  Exchange.BSE,
    }

    print(f"下载范围：{start_dt.date()} ~ {end_dt.date()}")
    print(f"跳过已有：{'否（强制更新）' if args.update else '是（增量下载）'}")
    print(f"批次大小：{args.batch} 只 / 批，批间休眠 {args.sleep}s")
    print(f"{'─' * 65}\n")

    for i, (symbol, vt_ex) in enumerate(stocks, 1):
        vt_symbol = f"{symbol}.{vt_ex}"

        # 增量模式：已有数据且不需要更新 → 跳过
        if not args.update and vt_symbol in have:
            skipped += 1
            if i % 100 == 0:
                print(f"  [{i:4}/{total}]  进度 {i/total*100:.0f}%  "
                      f"已完成 {success} 只  跳过 {skipped} 只  失败 {len(failed)} 只")
            continue

        exchange = ex_obj_map.get(vt_ex)
        if not exchange:
            failed.append(vt_symbol)
            continue

        # 增量更新：只下载数据库最新日期之后的数据
        dl_start = start_dt
        if args.update and vt_symbol in have:
            _, db_end = have[vt_symbol]
            # 从已有数据结束日期后一天开始
            from datetime import timedelta
            dl_start = db_end + timedelta(days=1)
            if dl_start >= end_dt:
                skipped += 1
                continue

        req = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            start=dl_start,
            end=end_dt,
            interval=Interval.DAILY,
        )
        try:
            bars = datafeed.query_bar_history(req)
            if bars:
                db.save_bar_data(bars)
                success += 1
                if i <= 20 or i % 50 == 0 or success % 100 == 0:
                    print(f"  [{i:4}/{total}]  OK    {vt_symbol:<16}  "
                          f"{len(bars):4} 根  "
                          f"{str(bars[0].datetime)[:10]} ~ {str(bars[-1].datetime)[:10]}")
            else:
                failed.append(vt_symbol)
                if i <= 20 or i % 50 == 0:
                    print(f"  [{i:4}/{total}]  EMPTY {vt_symbol}")
        except Exception as e:
            failed.append(vt_symbol)
            print(f"  [{i:4}/{total}]  ERR   {vt_symbol}  {e}")

        # 批次限频：每下载 batch 只暂停一次
        if i % args.batch == 0:
            time.sleep(args.sleep)

    print(f"\n{'─' * 65}")
    print(f"完成：成功 {success}  跳过 {skipped}  失败 {len(failed)}  共 {total} 只")
    if failed:
        # 把失败列表写到文件，方便后续重试
        fail_path = Path(__file__).parent / "download_failed.txt"
        fail_path.write_text("\n".join(failed), encoding="utf-8")
        print(f"失败列表已写入：{fail_path}")
        if len(failed) <= 20:
            print("失败：", failed)
    print()


# ------------------------------------------------------------------ #
#  入口
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    args = parse_args()

    if not args.show and not args.download:
        print("请指定 --show 或 --download，用 --help 查看帮助。")
    else:
        if args.show:
            show_database()
        if args.download:
            download_all(args)
