# -*- coding: utf-8 -*-
"""
将 _on_run_research 的核心循环移到 QThread 子线程，彻底解决100%后卡死问题。

策略：
1. 在文件中插入 ResearchWorker 类（在 _on_run_research 方法之前）
2. 重写 _on_run_research 为启动 worker
3. 添加 _on_research_progress / _on_research_finished / _on_research_error 回调
"""

filepath = r'C:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\ui\behavior_tab.py'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# ─── 找到 _on_run_research 方法的起始行 ───
run_research_start = None
for i, line in enumerate(lines):
    if '    def _on_run_research(self):' in line:
        run_research_start = i
        break

if run_research_start is None:
    print("FAIL: could not find _on_run_research")
    exit(1)

print(f"Found _on_run_research at line {run_research_start + 1}")

# ─── 找到 _on_run_research 方法的结束行（下一个同级方法的开始）───
run_research_end = None
for i in range(run_research_start + 1, len(lines)):
    # 找到下一个顶级方法（4空格缩进的 def）
    if lines[i].startswith('    def ') and not lines[i].startswith('        '):
        run_research_end = i
        break

if run_research_end is None:
    print("FAIL: could not find end of _on_run_research")
    exit(1)

print(f"_on_run_research spans lines {run_research_start+1} to {run_research_end}")

# ─── 构建新的代码块 ───
# 这段代码将替换从 _on_run_research 开始到下一个方法之前的所有内容

new_code = '''    def _on_run_research(self):
        """Execute research (异步版本：子线程执行，不卡UI)"""
        if not self._condition_nodes:
            QMessageBox.warning(self, "提示", "请先添加研究条件")
            return
        symbols = self._get_pool_symbols()
        if not symbols:
            QMessageBox.warning(self, "提示", "请先设置股票池")
            return

        # Build condition expression
        cond_parts = []
        for n in self._condition_nodes:
            cond_parts.append(f"({n['name']} {n['op']} {n['threshold']})")
        joiner = " & " if self._logic_op == "AND" else " | "
        condition_expr = joiner.join(cond_parts)

        cooldown = self._cooldown_sp.value()
        periods = [p for p, cb in self._period_cbs.items() if cb.isChecked()]
        if not periods:
            periods = [1, 5, 10]

        # 解析时间范围
        try:
            _start_str = self._date_start.text().strip()
            start_dt = datetime.strptime(_start_str, "%Y-%m-%d")
        except Exception:
            start_dt = datetime(2020, 1, 1)
        _end_str = self._date_end.text().strip()
        if _end_str in ("今日", "today", ""):
            end_dt = datetime.now()
        else:
            try:
                end_dt = datetime.strptime(_end_str, "%Y-%m-%d")
            except Exception:
                end_dt = datetime.now()

        feature_names = [n["name"] for n in self._condition_nodes]
        research_name = self._name_edit.text() or "behavior_research"

        # UI准备
        self._status_lbl.setText("研究中...")
        self._progress.setVisible(True)
        self._progress.setRange(0, len(symbols))
        self._progress.setValue(0)
        self._btn_run.setEnabled(False)

        # 保存参数供回调使用
        self._research_periods = periods
        self._research_symbols = symbols
        self._research_condition_expr = condition_expr

        # 启动子线程
        from PySide6.QtCore import QThread, Signal

        class _ResearchWorker(QThread):
            progress = Signal(int)
            finished = Signal(list, dict, dict)
            error = Signal(str)

            def __init__(self, symbols, feature_names, condition_expr,
                         cooldown, periods, start_dt, end_dt,
                         research_name, calculator):
                super().__init__()
                self._symbols = symbols
                self._feature_names = feature_names
                self._condition_expr = condition_expr
                self._cooldown = cooldown
                self._periods = periods
                self._start_dt = start_dt
                self._end_dt = end_dt
                self._research_name = research_name
                self._calculator = calculator
                self._cancelled = False

            def cancel(self):
                self._cancelled = True

            def run(self):
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
                            event_indices[sym_full] = trigger_indices

                        for evt in event_records:
                            d = {
                                "symbol": sym_full,
                                "date": str(getattr(evt, 'datetime', '')),
                                "event_id": getattr(evt, 'event_id', ''),
                            }
                            fwd = getattr(evt, 'forward_returns', [])
                            for fr in fwd:
                                period = getattr(fr, 'period', 0)
                                ret = getattr(fr, 'return_pct', 0.0)
                                d[f"return_{period}d"] = ret
                                d[f"mfe_{period}d"] = getattr(fr, 'mfe', 0.0)
                                d[f"mae_{period}d"] = getattr(fr, 'mae', 0.0)
                            all_events.append(d)

                    self.finished.emit(all_events, events_bars, event_indices)
                except Exception as e:
                    self.error.emit(str(e))

        worker = _ResearchWorker(
            symbols, feature_names, condition_expr,
            cooldown, periods, start_dt, end_dt,
            research_name, self._feature_calculator
        )
        worker.progress.connect(self._on_research_progress)
        worker.finished.connect(self._on_research_finished)
        worker.error.connect(self._on_research_error)
        self._research_worker = worker
        worker.start()

    def _on_research_progress(self, current: int):
        """子线程进度回调"""
        self._progress.setValue(current)

    def _on_research_finished(self, all_events: list, events_bars: dict, event_indices: dict):
        """子线程完成回调（在主线程执行）"""
        periods = self._research_periods
        symbols = self._research_symbols
        condition_expr = self._research_condition_expr

        self._display_results(all_events, periods)

        # 更新形态统计 tab（延迟执行避免卡顿）
        if events_bars and event_indices:
            try:
                self._pattern_stats_tab.update_stats(events_bars, event_indices)
            except Exception as e:
                print(f"[BehaviorLab] 形态统计更新异常: {e}")

        # 延迟生成监控数据
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, lambda: self._generate_monitor_data(symbols[:10], condition_expr))

        self._status_lbl.setText(
            f"完成 | {len(all_events)} 事件 | {len(symbols)} 标的")
        self._btn_save.setEnabled(True)
        self._btn_export.setEnabled(True)
        self._btn_run.setEnabled(True)
        self._progress.setVisible(False)

    def _on_research_error(self, error_msg: str):
        """子线程错误回调"""
        self._status_lbl.setText(f"错误: {error_msg[:50]}")
        self._btn_run.setEnabled(True)
        self._progress.setVisible(False)
        QMessageBox.critical(self, "研究失败", error_msg)

'''

# ─── 替换原方法 ───
new_lines = lines[:run_research_start] + [new_code] + lines[run_research_end:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Replaced _on_run_research ({run_research_end - run_research_start} lines) with async version")
print("Done!")
