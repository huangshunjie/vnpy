import pathlib, ast

BASE = pathlib.Path(r'C:\Users\hdec\Documents\GitHub\vnpy\vnpy\vnpy\market_behavior')
wt   = BASE / 'ui' / 'widget.py'
src  = wt.read_text(encoding='utf-8', errors='replace')

# 找现有 _build_conds 里的 else 分支，在它前面插入新条件分支
OLD = '''            elif ct == "trend_slope":
                # thr = 最小斜率（%/天），默认 0.1
                conds.append(ae.build_condition(ct, ma_period=20,
                                                slope_window=max(int(win/2), 5),
                                                min_slope=thr, weight=wt))
            else:
                conds.append(ae.build_condition(ct, min=thr, weight=wt))'''

NEW = '''            elif ct == "trend_slope":
                conds.append(ae.build_condition(ct, ma_period=20,
                                                slope_window=max(int(win/2), 5),
                                                min_slope=thr, weight=wt))
            elif ct == "macd_golden":
                conds.append(ae.build_condition(ct, weight=wt))
            elif ct == "macd_death":
                conds.append(ae.build_condition(ct, weight=wt))
            elif ct == "weekly_ma_slope":
                conds.append(ae.build_condition(
                    ct, ma_period=13, slope_window=5,
                    min_slope=max(thr, 0.0), weight=wt,
                    multi_tf_engine=getattr(ae, "_multi_tf", None)))
            elif ct == "pullback":
                # thr = 负数跌幅下限，如 -5 代表至多下跌5%
                # mode 默认 pct_drop；窗口用 win
                conds.append(ae.build_condition(
                    ct, mode="pct_drop", window=win,
                    min_drop=min(thr, -0.5),
                    max_drop=0.0, weight=wt))
            elif ct == "rsi_range":
                # thr = RSI 下限，上限固定 80
                conds.append(ae.build_condition(
                    ct, period=14,
                    min=max(thr, 0.0), max=80.0, weight=wt))
            elif ct == "boll_width":
                conds.append(ae.build_condition(
                    ct, period=20, std_mult=2.0,
                    min=thr, weight=wt))
            elif ct == "atr_ratio":
                conds.append(ae.build_condition(
                    ct, period=14, min=thr, weight=wt))
            else:
                conds.append(ae.build_condition(ct, min=thr, weight=wt))'''

count = src.count(OLD)
if count > 0:
    src = src.replace(OLD, NEW)
    print(f'replaced {count} occurrence(s)')
else:
    print('anchor not found')
    # 查找实际内容辅助调试
    idx = src.find('"trend_slope"')
    print(f'trend_slope at char {idx}')
    print(repr(src[idx-20:idx+200]))

wt.write_text(src, encoding='utf-8')

try:
    ast.parse(src)
    print(f'syntax OK: {len(src.splitlines())} lines')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')
