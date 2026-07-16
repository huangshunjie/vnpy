import pathlib, ast

BASE = pathlib.Path(r'C:\Users\hdec\Documents\GitHub\vnpy\vnpy\vnpy\market_behavior')
be   = BASE / 'ui' / 'behavior_editor.py'
src  = be.read_text(encoding='utf-8', errors='replace')

# ── 1. 在 COND_GROUPS 末尾加「技术指标」和「周期指标」两个分组 ─────────
OLD_TAIL = '''    ("🌊 波动行为  Volatility", [
        ("  波动强度  volatility",    "volatility",     2.00, "% 振幅",   "日均振幅 >= N%"),
    ]),
]
# 向后兼容
COND_OPTIONS = [item for _, group in COND_GROUPS for item in group]'''

NEW_TAIL = '''    ("🌊 波动行为  Volatility", [
        ("  波动强度  volatility",    "volatility",     2.00, "% 振幅",    "日均振幅 >= N%"),
        ("  ATR振幅   atr_ratio",     "atr_ratio",      1.00, "% (ATR/价)","ATR占收盘价的比例 >= N%"),
        ("  布林带宽  boll_width",    "boll_width",     0.05, "宽度比",    "布林带宽度(上下轨/中轨) >= N"),
    ]),
    ("⚡ 技术指标  Indicator", [
        ("  MACD金叉  macd_golden",   "macd_golden",    0.00, "（无阈值）", "日线MACD DIF上穿DEA（金叉）"),
        ("  MACD死叉  macd_death",    "macd_death",     0.00, "（无阈值）", "日线MACD DIF下穿DEA（死叉）"),
        ("  RSI范围   rsi_range",     "rsi_range",     30.00, "RSI下限",   "RSI(14)在[N, 70]范围内，N=下限"),
        ("  回踩检测  pullback",      "pullback",       -5.0, "% 跌幅",    "近期跌幅在合理范围，表示健康回踩"),
    ]),
    ("📅 周线指标  Weekly", [
        ("  13周均线↑ weekly_ma_slope","weekly_ma_slope",0.00,"（无阈值）","周线MA(13)斜率向上"),
    ]),
]
# 向后兼容
COND_OPTIONS = [item for _, group in COND_GROUPS for item in group]'''

if OLD_TAIL in src:
    src = src.replace(OLD_TAIL, NEW_TAIL)
    print('1: new groups added')
else:
    print('1: anchor not found, trying alt...')
    # 找实际内容
    idx = src.find('COND_OPTIONS = [item for')
    print(f'  COND_OPTIONS compat line at char {idx}')
    print(f'  context: {repr(src[idx-200:idx+50])}')

be.write_text(src, encoding='utf-8')

try:
    ast.parse(src)
    print(f'syntax OK: {len(src.splitlines())} lines')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')
