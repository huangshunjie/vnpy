import pathlib, ast

BASE = pathlib.Path(r'C:\Users\hdec\Documents\GitHub\vnpy\vnpy\vnpy\market_behavior')

# ══════════════════════════════════════════════════════════════════════
# 1. behavior_editor.py — 参数面板加止盈/止损配置
# ══════════════════════════════════════════════════════════════════════
be   = BASE / 'ui' / 'behavior_editor.py'
src  = be.read_text(encoding='utf-8', errors='replace')

# 在「回测持有天数」后面插入止盈止损参数，在「最少K线数」之前
OLD_HOLD = '''        v.addWidget(_hline())
        v.addWidget(_lbl("回测持有天数", _MUT))
        self._hold_sp = QtWidgets.QSpinBox()
        self._hold_sp.setRange(1, 60)
        self._hold_sp.setValue(5)
        self._hold_sp.setStyleSheet(_SPIN_SS)
        v.addWidget(self._hold_sp)

        v.addWidget(_lbl("最少K线数（过滤新股）", _MUT))'''

NEW_HOLD = '''        v.addWidget(_hline())
        v.addWidget(_lbl("回测卖出设置", _YLW, 13, True))

        v.addWidget(_lbl("最大持仓天数", _MUT))
        self._hold_sp = QtWidgets.QSpinBox()
        self._hold_sp.setRange(1, 120)
        self._hold_sp.setValue(20)
        self._hold_sp.setStyleSheet(_SPIN_SS)
        self._hold_sp.setToolTip("超过此天数强制卖出（兜底）")
        v.addWidget(self._hold_sp)

        v.addWidget(_lbl("止盈触发（%，盈利达到）", _MUT))
        self._tp_sp = QtWidgets.QDoubleSpinBox()
        self._tp_sp.setRange(0.0, 200.0)
        self._tp_sp.setValue(15.0)
        self._tp_sp.setSingleStep(1.0)
        self._tp_sp.setDecimals(1)
        self._tp_sp.setStyleSheet(_SPIN_SS)
        self._tp_sp.setToolTip("盈利达到N%后，启动追踪止盈（0=不启用）")
        v.addWidget(self._tp_sp)

        v.addWidget(_lbl("追踪止盈回撤（%，从最高点）", _MUT))
        self._tp_trail_sp = QtWidgets.QDoubleSpinBox()
        self._tp_trail_sp.setRange(0.0, 50.0)
        self._tp_trail_sp.setValue(10.0)
        self._tp_trail_sp.setSingleStep(1.0)
        self._tp_trail_sp.setDecimals(1)
        self._tp_trail_sp.setStyleSheet(_SPIN_SS)
        self._tp_trail_sp.setToolTip("触发止盈后，从最高点回撤N%时卖出")
        v.addWidget(self._tp_trail_sp)

        v.addWidget(_lbl("止损触发（%，亏损达到）", _MUT))
        self._sl_sp = QtWidgets.QDoubleSpinBox()
        self._sl_sp.setRange(0.0, 50.0)
        self._sl_sp.setValue(7.0)
        self._sl_sp.setSingleStep(0.5)
        self._sl_sp.setDecimals(1)
        self._sl_sp.setStyleSheet(_SPIN_SS)
        self._sl_sp.setToolTip("亏损达到N%时止损卖出（0=不启用）")
        v.addWidget(self._sl_sp)

        v.addWidget(_lbl("最少K线数（过滤新股）", _MUT))'''

if OLD_HOLD in src:
    src = src.replace(OLD_HOLD, NEW_HOLD)
    print('1a: hold/tp/sl widgets added')
else:
    print('1a: anchor not found')

# _get_cfg 里加新参数
OLD_CFG = '''            "hold_days":  self._hold_sp.value(),'''
NEW_CFG = '''            "hold_days":  self._hold_sp.value(),
            "take_profit":       self._tp_sp.value(),
            "trail_drawdown":    self._tp_trail_sp.value(),
            "stop_loss":         self._sl_sp.value(),'''

if OLD_CFG in src:
    src = src.replace(OLD_CFG, NEW_CFG)
    print('1b: _get_cfg updated')
else:
    print('1b: cfg anchor not found')

be.write_text(src, encoding='utf-8')
try:
    ast.parse(src)
    print(f'behavior_editor.py OK: {len(src.splitlines())} lines')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')

# ══════════════════════════════════════════════════════════════════════
# 2. backtest_engine.py — _fill_forward_returns 改为逐天模拟止盈止损
# ══════════════════════════════════════════════════════════════════════
bt   = BASE / 'engine' / 'backtest_engine.py'
src2 = bt.read_text(encoding='utf-8', errors='replace')

OLD_FILL = '''    @staticmethod
    def _fill_forward_returns(
        triggers:  List[TriggerRecord],
        all_bars:  List[CandleBar],
        hold_days: List[int],
        commission_rate: float = 0.0,
        stamp_duty_rate: float = 0.0,
        slippage_rate:   float = 0.0,
    ) -> None:
        """为每条触发记录填充各持有天数的收益率。"""
        for rec in triggers:
            i = rec.trigger_bar
            p0 = rec.trigger_price
            if p0 <= 0:
                continue
            for h in hold_days:
                j = i + h
                if j < len(all_bars):
                    pn = all_bars[j].close
                else:
                    pn = all_bars[-1].close
                cost = commission_rate + stamp_duty_rate + slippage_rate
                raw_return = (pn - p0) / p0
                rec.forward_returns[h] = raw_return - cost
                rec.gross_returns[h]   = raw_return'''

NEW_FILL = '''    @staticmethod
    def _fill_forward_returns(
        triggers:        List[TriggerRecord],
        all_bars:        List[CandleBar],
        hold_days:       List[int],
        commission_rate: float = 0.0,
        stamp_duty_rate: float = 0.0,
        slippage_rate:   float = 0.0,
        take_profit:     float = 0.0,
        trail_drawdown:  float = 0.0,
        stop_loss:       float = 0.0,
    ) -> None:
        """
        为每条触发记录填充持有收益率，支持动态止盈止损。

        take_profit > 0：盈利达到 take_profit% 后启动追踪止盈
        trail_drawdown > 0：触发止盈后，从最高点回撤 trail_drawdown% 卖出
        stop_loss > 0：亏损达到 stop_loss% 时止损卖出
        hold_days[-1]：最大持仓天数兜底
        """
        cost_total = commission_rate + stamp_duty_rate + slippage_rate
        use_dynamic = (take_profit > 0 or stop_loss > 0)
        max_hold = max(hold_days) if hold_days else 20

        for rec in triggers:
            i  = rec.trigger_bar
            p0 = rec.trigger_price
            if p0 <= 0:
                continue

            if use_dynamic:
                # ── 逐天模拟持仓 ──────────────────────────────────
                peak_price    = p0          # 持仓期间最高价（用于追踪止盈）
                tp_activated  = False       # 是否已触发止盈激活
                exit_bar      = min(i + max_hold, len(all_bars) - 1)
                exit_price    = all_bars[exit_bar].close
                exit_reason   = "max_hold"

                for k in range(i + 1, min(i + max_hold + 1, len(all_bars))):
                    bar   = all_bars[k]
                    price = bar.close
                    ret   = (price - p0) / p0 * 100   # 当前收益率 %

                    # 更新最高价
                    if price > peak_price:
                        peak_price = price

                    # 止损检查
                    if stop_loss > 0 and ret <= -stop_loss:
                        exit_price  = price
                        exit_bar    = k
                        exit_reason = "stop_loss"
                        break

                    # 止盈激活检查
                    if take_profit > 0 and ret >= take_profit:
                        tp_activated = True

                    # 追踪止盈检查（已激活且从最高点回撤超阈值）
                    if tp_activated and trail_drawdown > 0:
                        drawdown = (peak_price - price) / peak_price * 100
                        if drawdown >= trail_drawdown:
                            exit_price  = price
                            exit_bar    = k
                            exit_reason = "take_profit"
                            break

                raw_return = (exit_price - p0) / p0
                rec.details["exit_reason"] = exit_reason
                rec.details["exit_bar"]    = exit_bar
                rec.details["hold_actual"] = exit_bar - i

                for h in hold_days:
                    rec.forward_returns[h] = raw_return - cost_total
                    rec.gross_returns[h]   = raw_return

            else:
                # ── 原有逻辑：固定持有天数 ────────────────────────
                for h in hold_days:
                    j = i + h
                    pn = all_bars[j].close if j < len(all_bars) else all_bars[-1].close
                    raw_return = (pn - p0) / p0
                    rec.forward_returns[h] = raw_return - cost_total
                    rec.gross_returns[h]   = raw_return'''

if OLD_FILL in src2:
    src2 = src2.replace(OLD_FILL, NEW_FILL)
    print('2: _fill_forward_returns updated')
else:
    print('2: anchor not found')
    idx = src2.find('def _fill_forward_returns')
    print(f'  method at char {idx}')

# run() 里的调用也要传新参数
OLD_CALL = '''        self._fill_forward_returns(triggers, all_bars, [hold], comm, stamp, slip)'''
NEW_CALL = '''        tp       = cfg.get("take_profit",    0.0)
        trail    = cfg.get("trail_drawdown", 0.0)
        sl       = cfg.get("stop_loss",      0.0)
        self._fill_forward_returns(triggers, all_bars, [hold],
                                   comm, stamp, slip, tp, trail, sl)'''

if OLD_CALL in src2:
    src2 = src2.replace(OLD_CALL, NEW_CALL)
    print('2b: run() call updated')
else:
    print('2b: call anchor not found')
    idx = src2.find('_fill_forward_returns')
    print(f'  call at char {idx}')

bt.write_text(src2, encoding='utf-8')
try:
    ast.parse(src2)
    print(f'backtest_engine.py OK: {len(src2.splitlines())} lines')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')
