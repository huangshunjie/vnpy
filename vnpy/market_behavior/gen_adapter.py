import pathlib, ast

BASE = pathlib.Path(r'C:\Users\hdec\Documents\GitHub\vnpy\vnpy\vnpy\market_behavior')
ae   = BASE / 'engine' / 'adapter_engine.py'
src  = ae.read_text(encoding='utf-8', errors='replace')

# ── 1. 加 Phase 11.1 常量 ─────────────────────────────────────────────
ANCHOR_CONST = 'COND_TREND_SLOPE          = "trend_slope"'
NEW_CONSTS = '''
# ── Phase 11.1 技术指标条件 ───────────────────────────────────────────
COND_MACD_GOLDEN      = "macd_golden"       # MACD 金叉
COND_MACD_DEATH       = "macd_death"        # MACD 死叉（可用于排除）
COND_WEEKLY_MA_SLOPE  = "weekly_ma_slope"   # 周线 MA 斜率向上
COND_PULLBACK         = "pullback"          # 回踩（多模式）
COND_RSI_RANGE        = "rsi_range"         # RSI 范围过滤
COND_BOLL_WIDTH       = "boll_width"        # 布林带宽度（波动收缩/扩张）
COND_ATR_RATIO        = "atr_ratio"         # ATR 相对振幅'''

if ANCHOR_CONST in src and 'COND_MACD_GOLDEN' not in src:
    src = src.replace(ANCHOR_CONST, ANCHOR_CONST + NEW_CONSTS)
    print('1: constants added')
else:
    print('1: skip')

# ── 2. 加 eval 分支（插在最后 return False, 0.0 前）─────────────────
# 找 Phase 10.1 最后一个分支末尾（trend_slope 的 return 语句后）作为插入点
ANCHOR_EVAL = '            return passed, score if passed else 0.0\n\n        return False, 0.0\n\n    # ── 工具方法'

NEW_EVAL = '''            return passed, score if passed else 0.0

        # ── Phase 11.1: MACD 金叉 ────────────────────────────────────
        if ct == COND_MACD_GOLDEN:
            from .signal_engine import is_golden_cross
            fast   = int(p.get("fast", 12))
            slow   = int(p.get("slow", 26))
            signal = int(p.get("signal", 9))
            closes = [b.close for b in bars]
            passed = is_golden_cross(closes, fast, slow, signal)
            return passed, 1.0 if passed else 0.0

        # ── Phase 11.1: MACD 死叉（可用于排除强势反转） ───────────────
        if ct == COND_MACD_DEATH:
            from .signal_engine import is_death_cross
            fast   = int(p.get("fast", 12))
            slow   = int(p.get("slow", 26))
            signal = int(p.get("signal", 9))
            closes = [b.close for b in bars]
            passed = is_death_cross(closes, fast, slow, signal)
            return passed, 1.0 if passed else 0.0

        # ── Phase 11.1: 周线 MA 斜率向上 ─────────────────────────────
        if ct == COND_WEEKLY_MA_SLOPE:
            ma_period    = int(p.get("ma_period", 13))
            slope_window = int(p.get("slope_window", 5))
            min_slope    = float(p.get("min_slope", 0.0))
            multi_tf     = p.get("multi_tf_engine")
            if multi_tf is None:
                return False, 0.0
            import math as _math
            slope = multi_tf.get_weekly_ma_slope(
                symbol if hasattr(bars[0], "symbol") else (bars[0].symbol if bars else ""),
                ma_period, slope_window)
            if _math.isnan(slope):
                return False, 0.0
            passed = slope >= min_slope
            score  = min(max((slope - min_slope) / (abs(min_slope) + 0.5), 0.0), 1.0)
            return passed, score if passed else 0.0

        # ── Phase 11.1: 回踩检测 ──────────────────────────────────────
        if ct == COND_PULLBACK:
            from .signal_engine import detect_pullback
            mode       = p.get("mode", "pct_drop")   # pct_drop / from_high / to_ma
            window     = int(p.get("window", 10))
            min_drop   = float(p.get("min_drop", -8.0))
            max_drop   = float(p.get("max_drop", -2.0))
            ma_period  = int(p.get("ma_period", 20))
            ma_tol_pct = float(p.get("ma_tol_pct", 2.0))
            closes = [b.close for b in bars]
            highs  = [b.high  for b in bars]
            return detect_pullback(closes, highs, mode, window,
                                   min_drop, max_drop, ma_period, ma_tol_pct)

        # ── Phase 11.1: RSI 范围过滤 ──────────────────────────────────
        if ct == COND_RSI_RANGE:
            from .signal_engine import rsi as _rsi
            period  = int(p.get("period", 14))
            min_rsi = float(p.get("min", 30.0))
            max_rsi = float(p.get("max", 70.0))
            closes  = [b.close for b in bars]
            val     = _rsi(closes, period)
            import math as _math
            if _math.isnan(val):
                return False, 0.0
            passed = min_rsi <= val <= max_rsi
            score  = 1.0 - abs(val - (min_rsi + max_rsi) / 2) / ((max_rsi - min_rsi) / 2 + 1e-9)
            return passed, max(score, 0.0) if passed else 0.0

        # ── Phase 11.1: 布林带宽度 ────────────────────────────────────
        if ct == COND_BOLL_WIDTH:
            from .signal_engine import bollinger as _boll
            period    = int(p.get("period", 20))
            std_mult  = float(p.get("std_mult", 2.0))
            min_width = float(p.get("min", 0.0))
            max_width = float(p.get("max", 9999.0))
            closes    = [b.close for b in bars]
            boll      = _boll(closes, period, std_mult)
            import math as _math
            w = boll["width"]
            if _math.isnan(w):
                return False, 0.0
            passed = min_width <= w <= max_width
            return passed, min(w / (max_width if max_width < 9999 else w + 1), 1.0) if passed else 0.0

        # ── Phase 11.1: ATR 相对振幅 ─────────────────────────────────
        if ct == COND_ATR_RATIO:
            from .signal_engine import atr as _atr
            period    = int(p.get("period", 14))
            min_ratio = float(p.get("min", 0.0))
            max_ratio = float(p.get("max", 9999.0))
            closes    = [b.close for b in bars]
            highs     = [b.high  for b in bars]
            lows      = [b.low   for b in bars]
            atr_val   = _atr(highs, lows, closes, period)
            import math as _math
            if _math.isnan(atr_val) or bars[-1].close <= 0:
                return False, 0.0
            ratio  = atr_val / bars[-1].close * 100   # ATR 占收盘价的 %
            passed = min_ratio <= ratio <= max_ratio
            score  = min(ratio / (min_ratio * 2 if min_ratio > 0 else ratio + 1), 1.0)
            return passed, score if passed else 0.0

        return False, 0.0

    # ── 工具方法'''

if ANCHOR_EVAL in src and 'COND_MACD_GOLDEN' not in src.split('def _eval_condition')[1]:
    src = src.replace(ANCHOR_EVAL, NEW_EVAL)
    print('2: eval branches added')
else:
    print('2: skip (already exists or anchor not found)')
    # 调试
    idx = src.find('return False, 0.0')
    print(f'  first return False at char {idx}')

ae.write_text(src, encoding='utf-8')

# 验证
try:
    ast.parse(src)
    print(f'syntax OK, {len(src.splitlines())} lines')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')
