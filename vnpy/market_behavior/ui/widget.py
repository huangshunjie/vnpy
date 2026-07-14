"""
market_behavior/ui/widget.py  —  主窗口 + Worker 线程（完整实现）
"""
from __future__ import annotations
import datetime
from typing import Any, Dict, List

from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine, Event
from vnpy.trader.database import get_database
from vnpy.trader.constant import Exchange, Interval

from ..constant import APP_NAME
from ..event import (
    EVENT_MB_LOG, EVENT_MB_STARTED, EVENT_MB_STOPPED,
    EVENT_MB_EVENT_DETECTED, EVENT_MB_PATTERN_FOUND,
    EVENT_MB_SEQUENCE_FOUND, EVENT_MB_BREAKOUT_FOUND,
    EVENT_MB_FACTOR_UPDATED, EVENT_MB_LABEL_UPDATED,
    EVENT_MB_BACKTEST_DONE, EVENT_MB_ERROR,
)
from .behavior_editor import BehaviorEditorTab
from .pattern_view    import PatternViewTab
from .factor_view     import FactorViewTab
from .result_view     import ResultViewTab

_BG    = "#1e1e2e"
_PANEL = "#181825"
_PAN2  = "#11111b"
_BORD  = "#45475a"
_FG    = "#cdd6f4"
_MUT   = "#6c7086"
_BLU   = "#89b4fa"
_GRN   = "#a6e3a1"
_YLW   = "#f9e2af"
_RED   = "#f38ba8"
_MAV   = "#cba6f7"


def _lbl(text, color=_FG, size=11, bold=False):
    w = QtWidgets.QLabel(text)
    w.setStyleSheet(
        f"color:{color};font-size:{size}px;"
        f"font-weight:{'bold' if bold else 'normal'};"
        f"background:transparent;border:none;")
    return w


def _hline():
    f = QtWidgets.QFrame()
    f.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    f.setStyleSheet(f"border:none;border-top:1px solid {_BORD};")
    return f


class ScanWorker(QtCore.QThread):
    sig_progress = QtCore.Signal(int, str)
    sig_done     = QtCore.Signal(list, dict, dict)
    sig_error    = QtCore.Signal(str)

    def __init__(self, symbols, conditions, cfg):
        super().__init__()
        self._syms  = symbols
        self._conds = conditions
        self._cfg   = cfg

    def run(self):
        try:
            from vnpy.trader.database import get_database
            from vnpy.trader.constant import Exchange, Interval
            from vnpy.market_behavior.engine.candle_engine import (
                CandleParser, LimitRuleEngine, CandleBuffer)
            from vnpy.market_behavior.engine.factor_engine  import FactorEngine
            from vnpy.market_behavior.engine.label_engine   import LabelEngine
            from vnpy.market_behavior.engine.adapter_engine import AdapterEngine
            from vnpy.market_behavior.constant import BoardType

            cfg   = self._cfg
            db    = get_database()
            lr    = LimitRuleEngine()
            parser= CandleParser(lr)

            stock_list = (self._resolve(self._syms)
                          if self._syms else self._all_syms(db, cfg["boards"]))
            total = len(stock_list)
            if not total:
                self.sig_error.emit("未找到候选股票，请检查板块设置或数据库。")
                return

            self.sig_progress.emit(5, f"共 {total} 只，加载数据...")
            all_bufs, all_bars = {}, {}
            for i, (sym, exch, board) in enumerate(stock_list):
                if i % 300 == 0 and i:
                    self.sig_progress.emit(5 + int(i/total*30), f"加载 {i}/{total}...")
                raw = db.load_bar_data(sym, exch, Interval.DAILY,
                                       cfg["start"], cfg["end"])
                if not raw or len(raw) < cfg["min_bars"]:
                    continue
                buf  = CandleBuffer()
                prev = raw[0].open_price * 0.99
                cbars= []
                for b in raw:
                    cb = parser.parse(sym, b.datetime,
                                      b.open_price, b.high_price,
                                      b.low_price,  b.close_price,
                                      b.volume, prev, board)
                    if cb:
                        buf.push(cb); cbars.append(cb)
                    prev = b.close_price
                if len(cbars) >= cfg["window"] + 5:
                    all_bufs[sym] = buf
                    all_bars[sym] = cbars

            syms = list(all_bufs.keys())
            self.sig_progress.emit(40, f"有效 {len(syms)} 只，计算因子...")

            class MB:
                def __init__(self, d): self._d = d
                def get(self, s, n=60):
                    return self._d[s].get(s, n) if s in self._d else []

            fe = FactorEngine(log_fn=lambda m: None)
            le = LabelEngine (log_fn=lambda m: None)
            ae = AdapterEngine(log_fn=lambda m: None)
            for eng in [fe, le, ae]:
                eng.init(); eng.start(); eng.set_candle_buffer(MB(all_bufs))
            ae.set_factor_engine(fe)
            ae.set_label_engine(le)

            fmap, lmap = {}, {}
            for i, sym in enumerate(syms):
                if i % 300 == 0 and i:
                    self.sig_progress.emit(40+int(i/len(syms)*35), f"因子 {i}/{len(syms)}...")
                factors = fe.compute(sym, window=cfg["window"])
                label   = le.label(sym, factors=factors)
                fmap[sym] = {f.factor_type.value: f for f in factors}
                lmap[sym] = label

            self.sig_progress.emit(80, "运行选股...")
            conds = self._build_conds(ae, cfg["window"])
            if not conds:
                conds = [ae.build_condition("kline_strength", min=0.0, weight=1.0)]

            spec = ae.build_spec("UI选股", conditions=conds,
                                  require_all=cfg.get("require_all", True),
                                  sort_by=cfg.get("sort_by","kline_strength"),
                                  order="desc" if cfg.get("sort_desc",True) else "asc",
                                  top_n=cfg.get("top_n", 30))
            results = ae.screen(syms, spec)
            self.sig_progress.emit(100, f"完成，通过 {len(results)} 只")
            self.sig_done.emit(results, fmap, lmap)

        except Exception:
            import traceback
            self.sig_error.emit(traceback.format_exc())

    def _build_conds(self, ae, win):
        conds = []
        for c in self._conds:
            ct, thr, wt = c["cond_type"], c["threshold"], c["weight"]
            if ct == "rise_pct":
                conds.append(ae.build_condition(ct, threshold=thr,
                                                window=win, min=1, weight=wt))
            elif ct == "continuous":
                conds.append(ae.build_condition(ct, kind="rise",
                                                days=max(1,int(thr)), weight=wt))
            else:
                conds.append(ae.build_condition(ct, min=thr, weight=wt))
        return conds

    @staticmethod
    def _resolve(raw_syms):
        from vnpy.trader.constant import Exchange
        from vnpy.market_behavior.constant import BoardType
        out = []
        for s in raw_syms:
            if s.startswith(("300","301")):
                out.append((s, Exchange.SZSE, BoardType.GEM))
            elif s.startswith(("000","001","002","003")):
                out.append((s, Exchange.SZSE, BoardType.MAIN))
            elif s.startswith("688"):
                out.append((s, Exchange.SSE, BoardType.STAR))
            elif s.startswith(("600","601","603","605")):
                out.append((s, Exchange.SSE, BoardType.MAIN))
        return out

    @staticmethod
    def _all_syms(db, boards):
        from vnpy.trader.constant import Exchange, Interval
        from vnpy.market_behavior.constant import BoardType
        out = []
        for o in db.get_bar_overview():
            if o.interval != Interval.DAILY:
                continue
            s = o.symbol
            if o.exchange == Exchange.SZSE:
                if s.startswith(("000","001","002","003")) and boards.get("main_sz"):
                    out.append((s, Exchange.SZSE, BoardType.MAIN))
                elif s.startswith(("300","301")) and boards.get("gem"):
                    out.append((s, Exchange.SZSE, BoardType.GEM))
            elif o.exchange == Exchange.SSE:
                if s.startswith(("600","601","603","605")) and boards.get("main_ss"):
                    out.append((s, Exchange.SSE, BoardType.MAIN))
                elif s.startswith("688") and boards.get("star"):
                    out.append((s, Exchange.SSE, BoardType.STAR))
        return out


class BacktestWorker(QtCore.QThread):
    sig_progress = QtCore.Signal(int, str)
    sig_done     = QtCore.Signal(dict, list, int)
    sig_error    = QtCore.Signal(str)

    def __init__(self, symbols, conditions, cfg):
        super().__init__()
        self._syms  = symbols
        self._conds = conditions
        self._cfg   = cfg

    def run(self):
        try:
            from vnpy.trader.database import get_database
            from vnpy.trader.constant import Exchange, Interval
            from vnpy.market_behavior.engine.candle_engine import (
                CandleParser, LimitRuleEngine, CandleBuffer)
            from vnpy.market_behavior.engine.factor_engine   import FactorEngine
            from vnpy.market_behavior.engine.label_engine    import LabelEngine
            from vnpy.market_behavior.engine.adapter_engine  import AdapterEngine
            from vnpy.market_behavior.engine.backtest_engine import BacktestEngine
            from vnpy.market_behavior.constant import BoardType

            cfg  = self._cfg
            sym  = self._syms[0]
            hold = cfg["hold_days"]

            if sym.startswith(("300","301")):
                exch, board = Exchange.SZSE, BoardType.GEM
            elif sym.startswith(("000","001","002","003")):
                exch, board = Exchange.SZSE, BoardType.MAIN
            elif sym.startswith("688"):
                exch, board = Exchange.SSE,  BoardType.STAR
            else:
                exch, board = Exchange.SSE,  BoardType.MAIN

            self.sig_progress.emit(10, f"加载 {sym} 数据...")
            db  = get_database()
            raw = db.load_bar_data(sym, exch, Interval.DAILY,
                                   cfg["start"], cfg["end"])
            if not raw or len(raw) < cfg["min_bars"]:
                self.sig_error.emit(f"{sym} 数据不足（{len(raw) if raw else 0} 根）")
                return

            lr = LimitRuleEngine()
            parser = CandleParser(lr)
            buf  = CandleBuffer()
            prev = raw[0].open_price * 0.99
            bars = []
            for b in raw:
                cb = parser.parse(sym, b.datetime,
                                  b.open_price, b.high_price,
                                  b.low_price,  b.close_price,
                                  b.volume, prev, board)
                if cb:
                    buf.push(cb); bars.append(cb)
                prev = b.close_price

            self.sig_progress.emit(30, "初始化引擎...")
            fe = FactorEngine(log_fn=lambda m: None)
            le = LabelEngine (log_fn=lambda m: None)
            ae = AdapterEngine(log_fn=lambda m: None)
            be = BacktestEngine(log_fn=lambda m: None)
            for eng in [fe, le, ae]:
                eng.init(); eng.start(); eng.set_candle_buffer(buf)
            ae.set_factor_engine(fe); ae.set_label_engine(le)
            be.set_adapter_engine(ae)
            be.configure(warmup_bars=cfg["window"], allow_overlap=False)

            self.sig_progress.emit(50, "构建条件...")
            win   = cfg["window"]
            conds = []
            for c in self._conds:
                ct, thr, wt = c["cond_type"], c["threshold"], c["weight"]
                if ct == "rise_pct":
                    conds.append(ae.build_condition(ct, threshold=thr,
                                                    window=win, min=1, weight=wt))
                elif ct == "continuous":
                    conds.append(ae.build_condition(ct, kind="rise",
                                                    days=max(1,int(thr)), weight=wt))
                else:
                    conds.append(ae.build_condition(ct, min=thr, weight=wt))

            spec   = ae.build_spec("回测", conditions=conds,
                                    require_all=cfg.get("require_all", True))
            self.sig_progress.emit(70, f"回测中（持有 {hold} 天）...")
            result = be.run(sym, bars, spec, hold_days=hold)
            report = be.report(result)

            self.sig_progress.emit(100, f"完成，触发 {report['trigger_count']} 次")
            self.sig_done.emit(report, result.triggers, hold)

        except Exception:
            import traceback
            self.sig_error.emit(traceback.format_exc())


class MarketBehaviorWidget(QtWidgets.QMainWindow):
    """Quant Market Behavior Engine 主窗口（完整实现）。"""

    widget_name = f"{APP_NAME}Widget"

    def __init__(self, main_engine: MainEngine,
                 event_engine: EventEngine) -> None:
        super().__init__()
        self.main_engine  = main_engine
        self.event_engine = event_engine
        self.engine       = main_engine.get_engine(APP_NAME)
        self._worker      = None   # 当前后台 worker

        self._init_ui()
        self._register_events()

        if self.engine:
            self.engine.init_engine()

    # ── UI 构建 ──────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setWindowTitle(
            "Quant Market Behavior Engine  量化市场行为分析引擎")
        self.setMinimumSize(1440, 900)
        self.setStyleSheet(f"QMainWindow{{background:{_BG};}}")

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        root.addWidget(self._build_header(), stretch=0)
        root.addWidget(self._build_tabs(),   stretch=1)
        root.addWidget(_hline(),             stretch=0)
        root.addWidget(self._build_log(),    stretch=0)

    def _build_header(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(48)
        w.setStyleSheet(
            f"background:{_PANEL};border-radius:6px;"
            f"border:1px solid {_BORD};")
        lay = QtWidgets.QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(12)

        icon = QtWidgets.QLabel("📊")
        icon.setStyleSheet("font-size:20px;background:transparent;border:none;")
        lay.addWidget(icon)
        lay.addWidget(_lbl(
            "Quant Market Behavior Engine  量化市场行为分析引擎",
            _MAV, 14, True))
        lay.addStretch()

        self._status_dot = QtWidgets.QLabel("●")
        self._status_dot.setStyleSheet(
            f"color:{_MUT};font-size:14px;background:transparent;border:none;")
        self._status_lbl = _lbl("STOPPED", _MUT, 11, True)
        self._phase_lbl  = _lbl("Phase 9 · Full", _MUT, 10)

        lay.addWidget(self._status_dot)
        lay.addWidget(self._status_lbl)
        lay.addWidget(_lbl("|", _BORD, 11))
        lay.addWidget(self._phase_lbl)
        return w

    def _build_tabs(self) -> QtWidgets.QTabWidget:
        self._tabs = QtWidgets.QTabWidget()
        self._tabs.setStyleSheet(
            f"QTabWidget::pane{{border:1px solid {_BORD};background:{_BG};}}"
            f"QTabBar::tab{{background:{_PANEL};color:{_MUT};"
            f"  border:1px solid {_BORD};padding:7px 18px;font-size:11px;}}"
            f"QTabBar::tab:selected{{background:{_PAN2};color:{_MAV};"
            f"  border-bottom:2px solid {_MAV};}}"
            f"QTabBar::tab:hover{{color:{_FG};}}")

        self.editor_tab  = BehaviorEditorTab(engine=self.engine)
        self.pattern_tab = PatternViewTab(engine=self.engine)
        self.factor_tab  = FactorViewTab(engine=self.engine)
        self.result_tab  = ResultViewTab(engine=self.engine)

        self._tabs.addTab(self.editor_tab,  "条件编辑器  Editor")
        self._tabs.addTab(self.pattern_tab, "形态视图  Patterns")
        self._tabs.addTab(self.factor_tab,  "行为因子  Factors")
        self._tabs.addTab(self.result_tab,  "筛选结果  Results")

        # 连接编辑器信号
        self.editor_tab.sig_run_screen.connect(self._on_run_screen)
        self.editor_tab.sig_run_backtest.connect(self._on_run_backtest)
        self.result_tab.sig_backtest_symbol.connect(self._on_result_backtest)

        return self._tabs

    def _build_log(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(120)
        w.setStyleSheet(f"background:{_PAN2};border-radius:4px;")
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(4)
        lay.addWidget(_lbl("系统日志  System Log", _BLU, 10, True))
        self._log_edit = QtWidgets.QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setStyleSheet(
            f"QTextEdit{{background:{_PAN2};color:{_GRN};"
            f"  border:none;"
            f"  font-family:Consolas,monospace;font-size:10px;}}")
        lay.addWidget(self._log_edit)
        return w

    # ── 事件注册 ─────────────────────────────────────────────────────

    def _register_events(self) -> None:
        for ev_type, handler in [
            (EVENT_MB_LOG,            self._on_log),
            (EVENT_MB_STARTED,        self._on_started),
            (EVENT_MB_STOPPED,        self._on_stopped),
            (EVENT_MB_EVENT_DETECTED, self._on_event_detected),
            (EVENT_MB_PATTERN_FOUND,  self._on_pattern_found),
            (EVENT_MB_SEQUENCE_FOUND, self._on_sequence_found),
            (EVENT_MB_BREAKOUT_FOUND, self._on_breakout_found),
            (EVENT_MB_FACTOR_UPDATED, self._on_factor_updated),
            (EVENT_MB_LABEL_UPDATED,  self._on_label_updated),
            (EVENT_MB_BACKTEST_DONE,  self._on_backtest_done),
            (EVENT_MB_ERROR,          self._on_error),
        ]:
            self.event_engine.register(ev_type, handler)

    # ── 运行选股 ─────────────────────────────────────────────────────

    def _on_run_screen(self, symbols: list, conditions: list, cfg: dict) -> None:
        if self._worker and self._worker.isRunning():
            QtWidgets.QMessageBox.warning(self, "提示", "当前有任务运行中，请稍候。")
            return

        self._log(f"开始选股扫描，候选 {len(symbols) if symbols else '全市场'} 只...")
        self.result_tab.clear()
        self.factor_tab.clear_history()

        self._worker = ScanWorker(symbols, conditions, cfg)
        self._worker.sig_progress.connect(self._on_scan_progress)
        self._worker.sig_done.connect(self._on_scan_done)
        self._worker.sig_error.connect(self._on_worker_error)
        self._worker.start()

        # 切到结果 Tab
        self._tabs.setCurrentWidget(self.result_tab)

    def _on_run_backtest(self, symbols: list, conditions: list, cfg: dict) -> None:
        if self._worker and self._worker.isRunning():
            QtWidgets.QMessageBox.warning(self, "提示", "当前有任务运行中，请稍候。")
            return

        sym = symbols[0] if symbols else ""
        self._log(f"开始回测 {sym}，持有 {cfg['hold_days']} 天...")

        self._worker = BacktestWorker(symbols, conditions, cfg)
        self._worker.sig_progress.connect(self._on_scan_progress)
        self._worker.sig_done.connect(self._on_backtest_done_ui)
        self._worker.sig_error.connect(self._on_worker_error)
        self._worker.start()

        self._tabs.setCurrentWidget(self.result_tab)

    # ── Worker 回调 ───────────────────────────────────────────────────

    def _on_scan_progress(self, value: int, msg: str) -> None:
        self.editor_tab.set_progress(value, msg)
        self._log(msg)

    def _on_scan_done(self, results: list, factor_map: dict,
                      label_map: dict) -> None:
        self._last_factor_map = factor_map
        self._last_label_map  = label_map
        self._log(f"选股完成，通过 {len(results)} 只")
        self.editor_tab.set_progress(100, f"完成 — {len(results)} 只通过")

        # 结果 Tab
        self.result_tab.show_screen_results(results, factor_map)

        # 因子 Tab：显示排名第一的股票详情
        if results:
            top_sym = results[0].symbol
            fmap    = factor_map.get(top_sym, {})
            label   = label_map.get(top_sym)
            factors = list(fmap.values())
            lbs     = [(lt.value, label.scores.get(lt.value, 0))
                       for lt in label.labels] if label else []
            self.factor_tab.show_symbol(top_sym, factors, lbs)

            # 因子 Tab 扫描记录
            self.factor_tab.clear_history()
            for r in results:
                fm   = factor_map.get(r.symbol, {})
                lbl  = label_map.get(r.symbol)
                ks   = fm.get("kline_strength")
                rd   = fm.get("rise_days")
                bk   = fm.get("breakout_count")
                lu   = fm.get("limit_up_count")
                lbs2 = [lt.value for lt in lbl.labels] if lbl else []
                self.factor_tab.append_scan_row(
                    r.symbol,
                    ks.value if ks else 0,
                    rd.value if rd else 0,
                    bk.value if bk else 0,
                    lu.value if lu else 0,
                    lbs2,
                )
            self._run_pattern(top_sym)
            # 形态 Tab：对排名第一的股票自动运行形态检测


    def _on_backtest_done_ui(self, report: dict, triggers: list,
                              hold_days: int) -> None:
        self._log(
            f"回测完成 — 触发{report.get('trigger_count',0)}次  "
            f"胜率{report.get('hit_rate','N/A')}  "
            f"均收益{report.get('avg_return','N/A')}")
        self.editor_tab.set_progress(100, "回测完成")
        self.result_tab.show_backtest_report(report, triggers, hold_days)

    def _on_worker_error(self, msg: str) -> None:
        self._log(f"[ERROR] {msg[:200]}")
        self.editor_tab.set_progress(0, "出错，请查看日志")
        QtWidgets.QMessageBox.critical(self, "运行出错", msg[:500])

    # ── vnpy 事件回调 ─────────────────────────────────────────────────

    def _on_log(self, event: Event) -> None:
        self._log(event.data.get("msg", "") if event.data else "")

    def _on_started(self, event: Event) -> None:
        self._status_dot.setStyleSheet(
            f"color:{_GRN};font-size:14px;background:transparent;border:none;")
        self._status_lbl.setText("RUNNING")
        self._status_lbl.setStyleSheet(
            f"color:{_GRN};font-size:11px;font-weight:bold;"
            f"background:transparent;border:none;")
        self._log("Market Behavior Engine started.")

    def _on_stopped(self, event: Event) -> None:
        self._status_dot.setStyleSheet(
            f"color:{_MUT};font-size:14px;background:transparent;border:none;")
        self._status_lbl.setText("STOPPED")
        self._status_lbl.setStyleSheet(
            f"color:{_MUT};font-size:11px;font-weight:bold;"
            f"background:transparent;border:none;")
        self._log("Engine stopped.")

    def _on_event_detected(self, event: Event) -> None:
        d = event.data or {}
        sym = d.get("symbol", "")
        et  = d.get("event_type", "")
        dt  = d.get("dt", "")
        self._log(f"[Event] {sym}  {et}")
        self.pattern_tab.append_event(sym, et, dt)

    def _on_pattern_found(self, event: Event) -> None:
        d = event.data or {}
        self._log(f"[Pattern] {d.get('symbol','')}  {d.get('pattern_type','')}")

    def _on_sequence_found(self, event: Event) -> None:
        d = event.data or {}
        self._log(f"[Sequence] {d.get('symbol','')}  {d.get('sequence_type','')}")

    def _on_breakout_found(self, event: Event) -> None:
        d = event.data or {}
        self._log(f"[Breakout] {d.get('symbol','')}  {d.get('breakout_type','')}")

    def _on_factor_updated(self, event: Event) -> None:
        d = event.data or {}
        self._log(f"[Factor] {d.get('symbol','')}  "
                  f"{d.get('factor_type','')}={d.get('value','')}")

    def _on_label_updated(self, event: Event) -> None:
        d = event.data or {}
        self._log(f"[Label] {d.get('symbol','')}  {d.get('labels','')}")

    def _on_backtest_done(self, event: Event) -> None:
        d = event.data or {}
        self._log(f"[Backtest] triggers={d.get('trigger_count',0)}")

    def _on_error(self, event: Event) -> None:
        d = event.data or {}
        self._log(f"[ERROR] {d.get('msg','unknown error')}")

    # ── 工具 ─────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        from datetime import datetime
        ts   = str(datetime.now())[11:19]
        line = f"[{ts}] {msg}"
        self._log_edit.append(line)
        sb = self._log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(3000)
        if self.engine:
            self.engine.close()
        super().closeEvent(event)
    def _on_result_backtest(self, sym: str) -> None:
        """从结果表格双击/右键/按钮触发回测。"""
        # 特殊前缀：查看因子详情
        if sym.startswith("__factor__:"):
            real_sym = sym[len("__factor__:"):]
            fmap = getattr(self, "_last_factor_map", {})
            lmap = getattr(self, "_last_label_map", {})
            if real_sym in fmap:
                factors = list(fmap[real_sym].values())
                label   = lmap.get(real_sym)
                lbs     = [(lt.value, label.scores.get(lt.value, 0))
                           for lt in label.labels] if label else []
                self.factor_tab.show_symbol(real_sym, factors, lbs)
                self._tabs.setCurrentWidget(self.factor_tab)
            return
        elif sym.startswith("__pattern__:"):
            real_sym2 = sym[len("__pattern__:"):]
            self._run_pattern(real_sym2)
            return


        # 正常回测：用编辑器当前的条件和配置
        conds = self.editor_tab._get_conditions()
        cfg   = self.editor_tab._get_cfg()
        self._log(f"对 {sym} 运行历史回测（持有 {cfg['hold_days']} 天）...")
        self._on_run_backtest([sym], conds, cfg)


    def _run_pattern(self, sym: str) -> None:
        """后台运行形态检测，完成后填充 Pattern Tab。"""
        if self._worker and self._worker.isRunning():
            return
        cfg = self.editor_tab._get_cfg()
        self._pattern_worker = PatternWorker(sym, cfg)
        self._pattern_worker.sig_done.connect(self._on_pattern_done)
        self._pattern_worker.sig_error.connect(
            lambda msg: self._log(f"[Pattern] {msg[:120]}"))
        self._pattern_worker.start()
        self._log(f"形态检测：{sym} ...")

    def _on_pattern_done(self, sym: str, patterns: list,
                          sequences: list, breakouts: list) -> None:
        total = len(patterns) + len(sequences) + len(breakouts)
        self._log(
            f"[Pattern] {sym}  检测完成："
            f"{len(patterns)} 个单K形态  "
            f"{len(sequences)} 个组合形态  "
            f"{len(breakouts)} 个突破信号  共 {total} 条"
        )
        self.pattern_tab.show_patterns(sym, patterns, sequences, breakouts)

class PatternWorker(QtCore.QThread):
    """后台形态检测线程：对单只股票跑 Pattern/Sequence/Breakout 三个引擎。"""
    sig_done  = QtCore.Signal(str, list, list, list)   # sym, patterns, seqs, bks
    sig_error = QtCore.Signal(str)

    def __init__(self, symbol: str, cfg: dict):
        super().__init__()
        self._sym = symbol
        self._cfg = cfg

    def run(self):
        try:
            from vnpy.trader.database import get_database
            from vnpy.trader.constant import Exchange, Interval
            from vnpy.market_behavior.engine.candle_engine  import (
                CandleParser, LimitRuleEngine, CandleBuffer)
            from vnpy.market_behavior.engine.pattern_engine  import PatternEngine
            from vnpy.market_behavior.engine.sequence_engine import SequenceEngine
            from vnpy.market_behavior.engine.breakout_engine import BreakoutEngine
            from vnpy.market_behavior.constant import BoardType

            sym  = self._sym
            cfg  = self._cfg
            if sym.startswith(("300","301")):
                exch, board = Exchange.SZSE, BoardType.GEM
            elif sym.startswith(("000","001","002","003")):
                exch, board = Exchange.SZSE, BoardType.MAIN
            elif sym.startswith("688"):
                exch, board = Exchange.SSE,  BoardType.STAR
            else:
                exch, board = Exchange.SSE,  BoardType.MAIN

            db  = get_database()
            raw = db.load_bar_data(sym, exch, Interval.DAILY,
                                   cfg["start"], cfg["end"])
            if not raw or len(raw) < 10:
                self.sig_error.emit(f"{sym} 数据不足（{len(raw) if raw else 0} 根）")
                return

            lr = LimitRuleEngine()
            parser = CandleParser(lr)
            buf  = CandleBuffer()
            prev = raw[0].open_price * 0.99
            for b in raw:
                cb = parser.parse(sym, b.datetime,
                                  b.open_price, b.high_price,
                                  b.low_price, b.close_price,
                                  b.volume, prev, board)
                if cb:
                    buf.push(cb)
                prev = b.close_price

            pe = PatternEngine (log_fn=lambda m: None)
            se = SequenceEngine(log_fn=lambda m: None)
            be = BreakoutEngine(log_fn=lambda m: None)
            for e in [pe, se, be]:
                e.set_candle_buffer(buf); e.init(); e.start()

            patterns  = pe.detect(sym)
            sequences = se.detect(sym)
            breakouts = be.detect(sym)
            self.sig_done.emit(sym, patterns, sequences, breakouts)

        except Exception:
            import traceback
            self.sig_error.emit(traceback.format_exc())
