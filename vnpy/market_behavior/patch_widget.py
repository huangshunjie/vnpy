import pathlib

p = pathlib.Path(r'C:\Users\hdec\Documents\GitHub\vnpy\vnpy\vnpy\market_behavior\ui\widget.py')
src = p.read_text(encoding='utf-8', errors='replace')

# _build_conds 里的 else 分支，改为对新条件做专门映射
# 原来：
#   else:
#       conds.append(ae.build_condition(ct, min=thr, weight=wt))
# 改为带完整参数的分支

OLD = '''\
            if ct == "rise_pct":
                conds.append(ae.build_condition(ct, threshold=thr,
                                                window=win, min=1, weight=wt))
            elif ct == "continuous":
                conds.append(ae.build_condition(ct, kind="rise",
                                                days=max(1,int(thr)), weight=wt))
            else:
                conds.append(ae.build_condition(ct, min=thr, weight=wt))'''

NEW = '''\
            if ct == "rise_pct":
                conds.append(ae.build_condition(ct, threshold=thr,
                                                window=win, min=1, weight=wt))
            elif ct == "continuous":
                conds.append(ae.build_condition(ct, kind="rise",
                                                days=max(1, int(thr)), weight=wt))
            elif ct == "return_n_days":
                conds.append(ae.build_condition(ct, window=win, min=thr, weight=wt))
            elif ct == "new_high_n":
                conds.append(ae.build_condition(ct, window=win, weight=wt))
            elif ct == "ma_alignment":
                conds.append(ae.build_condition(ct, weight=wt))
            elif ct == "volume_price_confirm":
                # thr = 放量倍数（默认 1.5）
                conds.append(ae.build_condition(ct, vol_window=win,
                                                vol_mult=max(thr, 1.0),
                                                min_chg=3.0, weight=wt))
            elif ct == "trend_slope":
                # thr = 最小斜率（%/天），默认 0.1
                conds.append(ae.build_condition(ct, ma_period=20,
                                                slope_window=max(int(win/2), 5),
                                                min_slope=thr, weight=wt))
            else:
                conds.append(ae.build_condition(ct, min=thr, weight=wt))'''

count = src.count(OLD)
if count == 0:
    print('ERROR: anchor not found')
else:
    src = src.replace(OLD, NEW)
    print(f'replaced {count} occurrence(s)')

p.write_text(src, encoding='utf-8')
print(f'widget.py saved: {len(src.splitlines())} lines')

# 语法验证
import ast
ast.parse(src)
print('syntax OK')
