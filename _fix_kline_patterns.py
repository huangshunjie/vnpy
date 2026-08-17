"""
修复 ConditionEngine 中缺失的 K线形态指标路由

Bug: KLINE_YANG、KLINE_YIN 等指标在 _dispatch 方法中没有对应的 if 分支，
导致所有 K线形态条件都返回 False，回测永远无结果。
"""

import re

# 读取文件
with open("vnpy/strategy_condition/engine/condition_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 添加 import（如果还没有）
if "from ..indicators.kline_patterns import" not in content:
    import_block = """from ..indicators.kline_patterns import (
    check_kline_yin, check_kline_yang, check_kline_shrink_yin,
    check_kline_doji, check_kline_big_yang, check_kline_limit_up,
    check_kline_long_lower
)
"""
    # 在 volatility import 之后插入
    content = content.replace(
        'from ..indicators.volatility import check_atr_ratio, check_boll_width',
        'from ..indicators.volatility import check_atr_ratio, check_boll_width\n' + import_block
    )
    print("✓ 添加了 kline_patterns 模块的 import")

# 2. 在 _dispatch 方法中添加 K线形态指标的处理逻辑
# 找到 "# ── 波动 ──" 这一行，在它之前插入 K线形态处理逻辑
kline_dispatch = """
        # ── K线形态（单根） ───────────────────────────────────────────
        if ind == CI.KLINE_YANG:
            opens = [b.open for b in bars]
            return check_kline_yang(closes, opens)
        if ind == CI.KLINE_YIN:
            opens = [b.open for b in bars]
            return check_kline_yin(closes, opens)
        if ind == CI.KLINE_SHRINK_YIN:
            opens = [b.open for b in bars]
            return check_kline_shrink_yin(closes, opens, volumes,
                                          int(p.get("vol_period", 5)))
        if ind == CI.KLINE_DOJI:
            opens = [b.open for b in bars]
            return check_kline_doji(closes, opens, highs, lows,
                                    float(p.get("max_body_ratio", 0.1)))
        if ind == CI.KLINE_BIG_YANG:
            opens = [b.open for b in bars]
            return check_kline_big_yang(closes, opens, float(p.get("min_pct", 5.0)))
        if ind == CI.KLINE_LIMIT_UP:
            return check_kline_limit_up(closes, closes)
        if ind == CI.KLINE_LONG_LOWER:
            opens = [b.open for b in bars]
            return check_kline_long_lower(closes, opens, highs, lows,
                                          float(p.get("min_ratio", 2.0)))

"""

# 检查是否已经有 KLINE_YANG 的处理
if "if ind == CI.KLINE_YANG:" not in content:
    # 在 "# ── 波动 ──" 之前插入
    content = content.replace(
        "        # ── 波动 ──────────────────────────────────────────────────────\n        if ind == CI.ATR_RATIO:",
        kline_dispatch + "        # ── 波动 ──────────────────────────────────────────────────────\n        if ind == CI.ATR_RATIO:"
    )
    print("✓ 添加了 K线形态指标的 dispatch 逻辑")
else:
    print("  K线形态指标的 dispatch 逻辑已存在")

# 保存文件
with open("vnpy/strategy_condition/engine/condition_engine.py", "w", encoding="utf-8") as f:
    f.write(content)

print("\n修复完成！")
print("\n影响的指标：")
print("  - KLINE_YANG (阳线)")
print("  - KLINE_YIN (阴线)")
print("  - KLINE_SHRINK_YIN (缩量阴线)")
print("  - KLINE_DOJI (十字星)")
print("  - KLINE_BIG_YANG (大阳线)")
print("  - KLINE_LIMIT_UP (涨停)")
print("  - KLINE_LONG_LOWER (长下影)")