import pathlib, ast

BASE = pathlib.Path(r'C:\Users\hdec\Documents\GitHub\vnpy\vnpy\vnpy\market_behavior')

# ══════════════════════════════════════════════════════════════════════
# 1. backtest_engine.py — run() 签名加 take_profit / trail_drawdown / stop_loss
# ══════════════════════════════════════════════════════════════════════
bt   = BASE / 'engine' / 'backtest_engine.py'
src2 = bt.read_text(encoding='utf-8', errors='replace')

OLD_SIG = '''        hold_days: int = 0,
        commission_rate: float = None,   # 买入手续费率，默认读 DEFAULT_CFG
        stamp_duty_rate: float = None,   # 卖出印花税率，默认读 DEFAULT_CFG
        slippage_rate:   float = None,   # 买卖总滑点，默认读 DEFAULT_CFG
    ) -> BacktestResult:'''

NEW_SIG = '''        hold_days:       int   = 0,
        commission_rate: float = None,
        stamp_duty_rate: float = None,
        slippage_rate:   float = None,
        take_profit:     float = 0.0,    # 止盈触发收益率（%），0=不启用
        trail_drawdown:  float = 0.0,    # 追踪止盈回撤（%），0=不启用
        stop_loss:       float = 0.0,    # 止损触发亏损（%），0=不启用
    ) -> BacktestResult:'''

if OLD_SIG in src2:
    src2 = src2.replace(OLD_SIG, NEW_SIG)
    print('1a: run() signature updated')
else:
    print('1a: signature anchor not found')

# run() 方法体里把止盈止损存进 cfg 供 _fill_forward_returns 使用
OLD_CFG_SET = '''        hold = hold_days or self._cfg["hold_days"]
        comm  = commission_rate if commission_rate is not None else self._cfg["commission_rate"]
        stamp = stamp_duty_rate if stamp_duty_rate is not None else self._cfg["stamp_duty_rate"]
        slip  = slippage_rate   if slippage_rate   is not None else self._cfg["slippage_rate"]'''

NEW_CFG_SET = '''        hold  = hold_days or self._cfg["hold_days"]
        comm  = commission_rate if commission_rate is not None else self._cfg["commission_rate"]
        stamp = stamp_duty_rate if stamp_duty_rate is not None else self._cfg["stamp_duty_rate"]
        slip  = slippage_rate   if slippage_rate   is not None else self._cfg["slippage_rate"]
        # 止盈止损参数注入 cfg，供 _fill_forward_returns 读取
        cfg   = dict(self._cfg)
        cfg["take_profit"]    = take_profit
        cfg["trail_drawdown"] = trail_drawdown
        cfg["stop_loss"]      = stop_loss'''

if OLD_CFG_SET in src2:
    src2 = src2.replace(OLD_CFG_SET, NEW_CFG_SET)
    print('1b: cfg injection added')
else:
    print('1b: cfg anchor not found')

bt.write_text(src2, encoding='utf-8')
try:
    ast.parse(src2)
    print(f'backtest_engine.py OK: {len(src2.splitlines())} lines')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')

# ══════════════════════════════════════════════════════════════════════
# 2. widget.py — be.run() 调用加止盈止损参数
# ══════════════════════════════════════════════════════════════════════
wt  = BASE / 'ui' / 'widget.py'
src3 = wt.read_text(encoding='utf-8', errors='replace')

OLD_RUN = '''            result = be.run(sym, bars, spec, hold_days=hold,
                           commission_rate=cfg.get("comm_rate",  0.0003),
                           stamp_duty_rate=cfg.get("stamp_rate", 0.0010),
                           slippage_rate=  cfg.get("slip_rate",  0.0002))'''

NEW_RUN = '''            result = be.run(sym, bars, spec,
                           hold_days=      hold,
                           commission_rate=cfg.get("comm_rate",       0.0003),
                           stamp_duty_rate=cfg.get("stamp_rate",      0.0010),
                           slippage_rate=  cfg.get("slip_rate",       0.0002),
                           take_profit=    cfg.get("take_profit",     0.0),
                           trail_drawdown= cfg.get("trail_drawdown",  0.0),
                           stop_loss=      cfg.get("stop_loss",       0.0))'''

if OLD_RUN in src3:
    src3 = src3.replace(OLD_RUN, NEW_RUN)
    print('2: widget.py be.run() updated')
else:
    print('2: widget.py run() anchor not found')
    # 找实际内容
    idx = src3.find('be.run(sym')
    print(f'  be.run at char {idx}')
    print(repr(src3[idx:idx+300]))

wt.write_text(src3, encoding='utf-8')
try:
    ast.parse(src3)
    print(f'widget.py OK: {len(src3.splitlines())} lines')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')
