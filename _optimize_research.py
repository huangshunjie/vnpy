"""
Optimize _ResearchWorker.run() in behavior_tab.py:
- Use ThreadPoolExecutor for parallel data loading + feature calculation
- Create EventSearcher/Calculator once outside loop
- Simplify event index lookup
"""

filepath = "vnpy/quant_research/ui/behavior_tab.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Find the old run() method body and replace it
old_run = '''            def run(self):
                try:
                    from vnpy.trader.database import get_database
                    from vnpy.trader.constant import Interval, Exchange
                    import pandas as pd

                    db = get_database()
                    all_events = []
                    events_bars = {}
                    event_indices = {}

                    for idx, sym_full in enumerate(self._symbols):
                        if self._cancelled:
                            break
                        self.progress.emit(idx + 1)

                        parts_sym = sym_full.split(".")
                        if len(parts_sym) != 2:
                            continue
                        symbol, exchange_str = parts_sym
                        try:
                            exchange = Exchange(exchange_str)
                        except ValueError:
                            continue

                        bars = db.load_bar_data(
                            symbol=symbol, exchange=exchange,
                            interval=Interval.DAILY,
                            start=self._start_dt, end=self._end_dt)
                        if not bars or len(bars) < 30:
                            continue

                        df = pd.DataFrame([{
                            "open": b.open_price, "high": b.high_price,
                            "low": b.low_price, "close": b.close_price,
                            "volume": float(b.volume), "datetime": b.datetime,
                        } for b in bars])
                        df.set_index("datetime", inplace=True)

                        features_df = self._calculator.calculate(
                            df, self._feature_names, use_cache=False)
                        searcher = EventSearcher(research_id=self._research_name)
                        event_records = searcher.search_events(
                            data=features_df,
                            condition_expression=self._condition_expr,
                            required_features=self._feature_names,
                            cooldown_days=self._cooldown,
                            forward_periods=self._periods,
                        )

                        if event_records:
                            events_bars[sym_full] = df
                            trigger_indices = []
                            for evt in event_records:
                                evt_dt = getattr(evt, 'datetime', None)
                                if evt_dt is None:
                                    continue
                                if evt_dt in df.index:
                                    trigger_indices.append(df.index.get_loc(evt_dt))
                                else:
                                    try:
                                        ts = pd.Timestamp(evt_dt)
                                        if ts in df.index:
                                            trigger_indices.append(df.index.get_loc(ts))
                                        else:
                                            date_str = str(evt_dt)[:10]
                                            mask = df.index.astype(str).str[:10] == date_str
                                            locs = [i for i, v in enumerate(mask) if v]
                                            if locs:
                                                trigger_indices.append(locs[0])
                                    except Exception:
                                        pass
                            event_indices[sym_full] = trigger_indices'''

new_run = '''            def run(self):
                try:
                    from vnpy.trader.database import get_database
                    from vnpy.trader.constant import Interval, Exchange
                    from concurrent.futures import ThreadPoolExecutor, as_completed
                    import pandas as pd

                    db = get_database()
                    all_events = []
                    events_bars = {}
                    event_indices = {}

                    # 创建一次 searcher，避免循环内反复创建
                    searcher = EventSearcher(research_id=self._research_name)

                    def _process_symbol(sym_full):
                        """处理单个股票：加载数据 + 计算特征 + 搜索事件"""
                        parts_sym = sym_full.split(".")
                        if len(parts_sym) != 2:
                            return None
                        symbol, exchange_str = parts_sym
                        try:
                            exchange = Exchange(exchange_str)
                        except ValueError:
                            return None

                        bars = db.load_bar_data(
                            symbol=symbol, exchange=exchange,
                            interval=Interval.DAILY,
                            start=self._start_dt, end=self._end_dt)
                        if not bars or len(bars) < 30:
                            return None

                        # 高效构建 DataFrame
                        opens = [b.open_price for b in bars]
                        highs = [b.high_price for b in bars]
                        lows = [b.low_price for b in bars]
                        closes = [b.close_price for b in bars]
                        volumes = [float(b.volume) for b in bars]
                        dts = [b.datetime for b in bars]
                        df = pd.DataFrame({
                            "open": opens, "high": highs,
                            "low": lows, "close": closes,
                            "volume": volumes
                        }, index=pd.DatetimeIndex(dts, name="datetime"))

                        features_df = self._calculator.calculate(
                            df, self._feature_names, use_cache=False)
                        event_records = searcher.search_events(
                            data=features_df,
                            condition_expression=self._condition_expr,
                            required_features=self._feature_names,
                            cooldown_days=self._cooldown,
                            forward_periods=self._periods,
                        )

                        if not event_records:
                            return None

                        # 快速事件索引查找
                        trigger_indices = []
                        idx_set = set(df.index)
                        for evt in event_records:
                            evt_dt = getattr(evt, 'datetime', None)
                            if evt_dt is None:
                                continue
                            try:
                                ts = pd.Timestamp(evt_dt)
                                if ts in idx_set:
                                    trigger_indices.append(df.index.get_loc(ts))
                                else:
                                    # 日期级别匹配
                                    ts_date = ts.normalize()
                                    norm_idx = df.index.normalize()
                                    mask = norm_idx == ts_date
                                    locs = mask.nonzero()[0]
                                    if len(locs) > 0:
                                        trigger_indices.append(int(locs[0]))
                            except Exception:
                                pass

                        return (sym_full, df, event_records, trigger_indices)

                    # 使用线程池并行处理（I/O密集型，线程并行效果好）
                    max_workers = min(8, max(2, len(self._symbols) // 100))
                    processed = 0

                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = {}
                        for sym_full in self._symbols:
                            if self._cancelled:
                                break
                            fut = executor.submit(_process_symbol, sym_full)
                            futures[fut] = sym_full

                        for fut in as_completed(futures):
                            if self._cancelled:
                                # 取消剩余任务
                                for f in futures:
                                    f.cancel()
                                break
                            processed += 1
                            self.progress.emit(processed)

                            try:
                                result = fut.result()
                            except Exception:
                                continue

                            if result is None:
                                continue

                            sym_full, df, event_records, trigger_indices = result
                            events_bars[sym_full] = df
                            event_indices[sym_full] = trigger_indices'''

if old_run in content:
    content = content.replace(old_run, new_run, 1)
    print("SUCCESS: Replaced run() method with optimized parallel version")
else:
    print("ERROR: Could not find exact old_run text")
    # Try to find partial match for diagnosis
    check = "for idx, sym_full in enumerate(self._symbols):"
    if check in content:
        print("  Found loop marker - indentation/whitespace mismatch?")
    else:
        print("  Loop marker also not found")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

import py_compile
try:
    py_compile.compile(filepath, doraise=True)
    print("COMPILE OK")
except py_compile.PyCompileError as e:
    print(f"COMPILE ERROR: {e}")