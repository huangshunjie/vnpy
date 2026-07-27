"""
strategy_condition/ui/condition_editor.py
条件树可视化编辑器 — QTreeWidget + 参数面板
"""
from __future__ import annotations
import os
import sys
import faulthandler
import traceback
import datetime
from typing import Optional, Tuple

from vnpy.trader.ui import QtWidgets, QtCore, QtGui

# ══════════════════════════════════════════════════════════════════════════
# 崩溃诊断：启用 faulthandler + 日志输出，帮助定位 C++ 层 segfault
# ══════════════════════════════════════════════════════════════════════════
_LOG_DIR = os.path.join(os.path.expanduser("~"), ".vnpy_sce_logs")
try:
    os.makedirs(_LOG_DIR, exist_ok=True)
    _CRASH_LOG_PATH = os.path.join(_LOG_DIR, "condition_editor_crash.log")
    _crash_log_fp = open(_CRASH_LOG_PATH, "a", encoding="utf-8", buffering=1)
    faulthandler.enable(file=_crash_log_fp)
except Exception:
    _crash_log_fp = None
    _CRASH_LOG_PATH = ""


def _log(msg: str) -> None:
    """向 stdout 和崩溃日志文件同时写入调试信息"""
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] [SCE-CondEditor] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    if _crash_log_fp is not None:
        try:
            _crash_log_fp.write(line + "\n")
            _crash_log_fp.flush()
        except Exception:
            pass


def _show_exc_dialog(title: str, exc: Exception) -> None:
    """通用异常弹窗（同时写日志）"""
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    _log(f"[EXCEPTION] {title}: {type(exc).__name__}: {exc}\n{tb_str}")
    try:
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        msg.setWindowTitle(title)
        msg.setText(f"{type(exc).__name__}: {exc}")
        msg.setDetailedText(tb_str)
        msg.exec()
    except Exception:
        pass


_log(f"condition_editor 模块加载完成，崩溃日志: {_CRASH_LOG_PATH}")


# 安装全局 Python 异常钩子（Qt 事件循环内的未捕获异常也会弹窗）
_orig_excepthook = sys.excepthook


def _global_excepthook(exc_type, exc, tb):
    tb_str = "".join(traceback.format_exception(exc_type, exc, tb))
    _log(f"[UNCAUGHT] {exc_type.__name__}: {exc}\n{tb_str}")
    try:
        app = QtWidgets.QApplication.instance()
        if app is not None:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            msg.setWindowTitle("未捕获异常")
            msg.setText(f"{exc_type.__name__}: {exc}")
            msg.setDetailedText(tb_str)
            msg.exec()
    except Exception:
        pass
    _orig_excepthook(exc_type, exc, tb)


sys.excepthook = _global_excepthook

from ..constant import (NodeOp, ConditionCategory, ConditionIndicator,
                         SignalType)
from ..core.condition import (
    Condition, condition_from_dict,
    cond_ma_slope, cond_weekly_ma_slope, cond_ma_alignment, cond_new_high_n,
    cond_pullback_pct, cond_pullback_from_high, cond_pullback_to_ma,
    cond_macd_golden, cond_macd_death, cond_rsi_range, cond_return_n_days,
    cond_volume_ratio, cond_volume_price_up, cond_volume_shrink,
    cond_continuous_rise, cond_limit_up_count, cond_big_yang_count,
    cond_kline_strength, cond_atr_ratio, cond_boll_width,
    cond_stop_loss, cond_take_profit, cond_trailing_stop,
    cond_max_hold_days, cond_ma_break_down, cond_macd_death_sell,
    cond_time_of_day,
)
from ..core.condition_advanced import (
    cond_trend_strength, cond_price_above_ma, cond_trend_days,
    cond_trend_intact, cond_ma_bindong, cond_trend_score,
    cond_strength_returnn, cond_strength_limit_up_count as cond_adv_limit_up,
    cond_strength_big_yang_count, cond_strength_vol_break, cond_strength_score,
    cond_volume_layer, cond_volume_upphase, cond_volume_yin_filter, cond_fund_intensity,
    cond_pullback_to_ma5, cond_pullback_to_ma10, cond_pullback_to_ma20,
    cond_pullback_to_ma30, cond_first_pullback, cond_shrink_pullback,
    cond_strong_pullback_score,
    cond_kline_yin, cond_kline_yang, cond_kline_shrink_yin, cond_kline_volyin,
    cond_kline_long_lower, cond_kline_doji, cond_kline_big_yang, cond_kline_limit_up,
    cond_dev_ma5, cond_dev_ma10, cond_dev_ma20, cond_dev_ma10_ma20,
    cond_dev_overbought,
    cond_market_index_trend, cond_market_risk,
    cond_score_node,
)
from ..core.condition_tree import ConditionNode

# ── 颜色 ──────────────────────────────────────────────────────────────
_BG   = "#1e1e2e"; _PAN2 = "#11111b"; _BORD = "#45475a"
_FG   = "#cdd6f4"; _MUT  = "#6c7086"; _BLU  = "#89b4fa"
_GRN  = "#a6e3a1"; _YLW  = "#f9e2af"; _RED  = "#f38ba8"
_MAV  = "#cba6f7"; _PNK  = "#f5c2e7"

# ── 拖放指示器颜色 ────────────────────────────────────────────────────
_DROP_HIGHLIGHT = "#585b70"
_DROP_BETWEEN   = "#89b4fa"

# ── 条件元数据表 ──────────────────────────────────────────────────────
# (显示名, factory_fn, 默认参数描述)
_COND_META = {
    ConditionIndicator.MA_SLOPE:          ("MA斜率向上",     cond_ma_slope,          {"ma_period":20,"slope_window":10,"min_slope":0.0}),
    ConditionIndicator.WEEKLY_MA_SLOPE:   ("13周均线向上",   cond_weekly_ma_slope,   {"ma_period":13,"slope_window":5,"min_slope":0.0}),
    ConditionIndicator.MA_ALIGNMENT:      ("均线多头排列",   cond_ma_alignment,      {"periods":[5,10,20,60],"max_gap_pct":0.0}),
    ConditionIndicator.NEW_HIGH_N:        ("N日新高突破",    cond_new_high_n,        {"n":20}),
    ConditionIndicator.PULLBACK_PCT:      ("跌幅回调",       cond_pullback_pct,      {"window":10,"min_drop":-8.0,"max_drop":-2.0}),
    ConditionIndicator.PULLBACK_FROM_HIGH:("从高点回撤",     cond_pullback_from_high,{"window":20,"min_drop":-10.0,"max_drop":-2.0}),
    ConditionIndicator.PULLBACK_TO_MA:    ("回踩均线",       cond_pullback_to_ma,    {"ma_period":20,"tol_pct":2.0}),
    ConditionIndicator.MACD_GOLDEN:       ("MACD 金叉",      cond_macd_golden,       {"fast":12,"slow":26,"signal":9}),
    ConditionIndicator.MACD_DEATH:        ("MACD 死叉",      cond_macd_death,        {"fast":12,"slow":26,"signal":9}),
    ConditionIndicator.RSI_RANGE:         ("RSI 范围",       cond_rsi_range,         {"period":14,"min_rsi":30.0,"max_rsi":70.0}),
    ConditionIndicator.RETURN_N_DAYS:     ("N日收益率",      cond_return_n_days,     {"n":10,"min_return":5.0}),
    ConditionIndicator.VOLUME_RATIO:      ("量比过滤",       cond_volume_ratio,      {"period":20,"min_ratio":1.5}),
    ConditionIndicator.VOLUME_PRICE_UP:   ("放量上涨",       cond_volume_price_up,   {"period":20,"min_ratio":1.5,"min_chg":1.0}),
    ConditionIndicator.VOLUME_SHRINK:     ("缩量调整",       cond_volume_shrink,     {"period":20,"max_ratio":0.7}),
    ConditionIndicator.CONTINUOUS_RISE:   ("连续上涨",       cond_continuous_rise,   {"window":10,"min_days":3}),
    ConditionIndicator.LIMIT_UP_COUNT:    ("涨停次数",       cond_limit_up_count,    {"window":20,"min_count":1}),
    ConditionIndicator.BIG_YANG_COUNT:    ("大阳线次数",     cond_big_yang_count,    {"window":20,"min_count":2,"min_pct":3.0}),
    ConditionIndicator.KLINE_STRENGTH:    ("K线综合强度",    cond_kline_strength,    {"min_score":0.4}),
    ConditionIndicator.ATR_RATIO:         ("ATR振幅",        cond_atr_ratio,         {"period":14,"min_ratio":1.0}),
    ConditionIndicator.BOLL_WIDTH:        ("布林带宽度",     cond_boll_width,        {"period":20,"min_width":0.05}),
    ConditionIndicator.STOP_LOSS:         ("固定止损",       cond_stop_loss,         {"pct":8.0}),
    ConditionIndicator.TAKE_PROFIT:       ("固定止盈",       cond_take_profit,       {"pct":15.0}),
    ConditionIndicator.TRAILING_STOP:     ("追踪止盈",       cond_trailing_stop,     {"take_profit":15.0,"trail_drawdown":10.0}),
    ConditionIndicator.MAX_HOLD_DAYS:     ("最大持仓天数",   cond_max_hold_days,     {"days":60}),
    ConditionIndicator.MA_BREAK_DOWN:     ("跌破均线",       cond_ma_break_down,     {"ma_period":20}),
    ConditionIndicator.MACD_DEATH_SELL:   ("MACD死叉卖出",   cond_macd_death_sell,   {"fast":12,"slow":26,"signal":9}),
    ConditionIndicator.TIME_OF_DAY:       ("日内时间过滤",   cond_time_of_day,       {"min_time":"14:30","max_time":"15:00"}),
    # ── 趋势升级 ──
    ConditionIndicator.TREND_STRENGTH:    ("均线多头强度",   cond_trend_strength,    {"periods":[5,10,20,30]}),
    ConditionIndicator.PRICE_ABOVE_MA:    ("价格站上均线",   cond_price_above_ma,    {"ma_period":20}),
    ConditionIndicator.TREND_DAYS:        ("趋势持续天数",   cond_trend_days,        {"ma_period":20,"min_days":5}),
    ConditionIndicator.TREND_INTACT:      ("趋势未破坏",    cond_trend_intact,      {"ma_period":20}),
    ConditionIndicator.MA_BINDONG:        ("均线粘合",       cond_ma_bindong,        {"periods":[5,10,20],"max_spread_pct":2.0}),
    ConditionIndicator.TREND_SCORE:       ("趋势综合评分",   cond_trend_score,       {}),
    # ── 强势股 ──
    ConditionIndicator.STRENGTH_RETURN_N: ("N日涨幅",       cond_strength_returnn,  {"n":20,"min_return":20.0}),
    ConditionIndicator.STRENGTH_LIMIT_UP_COUNT: ("涨停次数(强势)", cond_adv_limit_up,     {"n":20,"min_count":1}),
    ConditionIndicator.STRENGTH_BIG_YANG_COUNT: ("大阳线(强势)",   cond_strength_big_yang_count, {"n":20,"min_count":2,"min_pct":5.0}),
    ConditionIndicator.STRENGTH_VOL_BREAK:("放量突破",       cond_strength_vol_break,{"n":20}),
    ConditionIndicator.STRENGTH_SCORE:    ("强势股评分",     cond_strength_score,    {"n":20}),
    # ── 量能升级 ──
    ConditionIndicator.VOLUME_UP_PHASE:   ("上涨阶段量能",   cond_volume_upphase,    {"n":20,"min_ratio":1.3}),
    ConditionIndicator.VOLUME_LAYER:      ("分层量能",       cond_volume_layer,      {"up_window":10,"dn_window":5,"max_ratio":0.6}),
    ConditionIndicator.VOLUME_YIN_FILTER: ("放量阴线过滤",   cond_volume_yin_filter, {}),
    ConditionIndicator.FUND_INTENSITY:    ("资金介入强度",   cond_fund_intensity,    {"n":10,"min_score":0.5}),
    # ── 回调升级 ──
    ConditionIndicator.PULLBACK_TO_MA5:   ("回踩MA5",       cond_pullback_to_ma5,   {"tol_pct":2.0}),
    ConditionIndicator.PULLBACK_TO_MA10:  ("回踩MA10",      cond_pullback_to_ma10,  {"tol_pct":2.0}),
    ConditionIndicator.PULLBACK_TO_MA20:  ("回踩MA20",      cond_pullback_to_ma20,  {"tol_pct":2.0}),
    ConditionIndicator.PULLBACK_TO_MA30:  ("回踩MA30",      cond_pullback_to_ma30,  {"tol_pct":2.0}),
    ConditionIndicator.FIRST_PULLBACK:    ("首次回踩",       cond_first_pullback,    {"ma_period":10,"tol_pct":2.0,"lookback":20}),
    ConditionIndicator.SHRINK_PULLBACK:   ("缩量回调",       cond_shrink_pullback,   {"pullback_days":3,"vol_period":10,"max_vol_ratio":0.7}),
    ConditionIndicator.STRONG_PULLBACK_SCORE: ("强势回调评分",   cond_strong_pullback_score, {}),
    # ── K线升级 ──
    ConditionIndicator.KLINE_YIN:         ("阴线",          cond_kline_yin,         {}),
    ConditionIndicator.KLINE_YANG:        ("阳线",          cond_kline_yang,        {}),
    ConditionIndicator.KLINE_SHRINK_YIN:  ("缩量阴线",      cond_kline_shrink_yin,  {"vol_period":5}),
    ConditionIndicator.KLINE_VOL_YIN:     ("放量阴线",      cond_kline_volyin,      {}),
    ConditionIndicator.KLINE_LONG_LOWER:  ("长下影线",      cond_kline_long_lower,  {"min_ratio":2.0}),
    ConditionIndicator.KLINE_DOJI:        ("十字星",        cond_kline_doji,        {"max_body_ratio":0.1}),
    ConditionIndicator.KLINE_BIG_YANG:    ("大阳线K线",     cond_kline_big_yang,    {"min_pct":5.0}),
    ConditionIndicator.KLINE_LIMIT_UP:    ("涨停K线",       cond_kline_limit_up,    {}),
    # ── 偏离 ──
    ConditionIndicator.DEV_MA5:           ("MA5乖离率",     cond_dev_ma5,           {"max_dev_pct":5.0}),
    ConditionIndicator.DEV_MA10:          ("MA10乖离率",    cond_dev_ma10,          {"max_dev_pct":5.0}),
    ConditionIndicator.DEV_MA20:          ("MA20乖离率",    cond_dev_ma20,          {"max_dev_pct":8.0}),
    ConditionIndicator.DEV_MA10_MA20:     ("MA10-MA20距离", cond_dev_ma10_ma20,     {"max_distance_pct":8.0}),
    ConditionIndicator.DEV_OVERBOUGHT:    ("超涨过滤",      cond_dev_overbought,    {"ma_period":10,"max_above_pct":10.0}),
    # ── 市场环境 ──
    ConditionIndicator.MARKET_INDEX_TREND:("指数趋势",      cond_market_index_trend, {"ma_period":20}),
    ConditionIndicator.MARKET_RISK:       ("市场风险状态",   cond_market_risk,       {}),
    # ── 评分系统 ──
    ConditionIndicator.SCORE_NODE:        ("综合评分≥阈值", cond_score_node,        {"min_score":80.0,"weights":{"trend":25,"strength":20,"volume":20,"pullback":20,"kline":10,"market":5}}),
}


def _spin_ss(bg: str = _PAN2) -> str:
    return (f"QDoubleSpinBox,QSpinBox{{background:{bg};color:{_FG};"
            f"border:1px solid {_BORD};border-radius:4px;"
            f"padding:3px 6px;font-size:13px;}}")


def _lbl(text: str, color: str = _FG, size: int = 13) -> QtWidgets.QLabel:
    w = QtWidgets.QLabel(text)
    w.setStyleSheet(f"color:{color};font-size:{size}px;"
                    f"background:transparent;border:none;")
    return w


# ── 条件使用说明 ──────────────────────────────────────
_COND_HELP: dict = {
    #── 趋势 Trend ──
    ConditionIndicator.MA_SLOPE: (
        "MA斜率向上",
        "【功能】判断均线斜率是否为正，表明趋势向上。\n\n"
        "【计算方法】\n"
        "  MA(今日) - MA(N日前) > min_slope\n"
        "  即均线在slope_window天内的绝对变化量。\n\n"
        "【参数说明】\n"
        "  · MA周期：均线计算周期，默认20，范围5-120\n"
        "  · 斜率窗口：比较间隔天数，默认5，范围1-30\n"
        "  · 最小斜率：斜率阈值，默认0（>0即为向上）\n\n"
        "【使用示例】\n"
        "  设置 MA周期=20, 斜率窗口=5, 最小斜率=0\n"
        "  含义：20日均线在5天内上涨，确认上升趋势\n\n"
        "【适用场景】买入条件，确认趋势方向\n"
        "【建议搭配】均线多头排列 + 价格站上均线"
    ),
    ConditionIndicator.WEEKLY_MA_SLOPE: (
        "13周均线向上",
        "【功能】判断周线级别MA斜率>0，即中期趋势向上。\n\n"
        "【参数说明】\n"
        "  · ma_period：均线周期，默认13（约一季度）\n"
        "  · slope_window：斜率回看，默认5根K线\n\n"
        "【使用示例】\n"
        "  13周均线向上 = 过去一个季度股价重心抬升\n"
        "  适合中线持股策略，过滤短期震荡\n\n"
        "【适用场景】中线策略过滤条件\n"
        "【建议搭配】日线级别的回踩买入信号"
    ),
    ConditionIndicator.MA_ALIGNMENT: (
        "均线多头排列",
        "【功能】判断短期均线在上、长期均线在下，形成多头排列。\n\n"
        "【计算方法】\n"
        "  MA5 > MA10 > MA20 > MA30（默认配置）\n"
        "  所有相邻均线严格递减排列。\n\n"
        "【参数说明】\n"
        "  · periods：均线列表，默认[5,10,20,30]\n"
        "  · max_gap_pct：相邻均线间距上限%(0=不限)\n\n"
        "【使用示例】\n"
        "  periods=[5,10,20,60]：加入60日线，更严格\n"
        "  max_gap_pct=3：相邻均线间距不超过3%\n\n"
        "【适用场景】买入条件，确认强势多头趋势\n"
        "【注意事项】在震荡市中此条件很难满足，\n"
        "  适合用于趋势行情的筛选。"
    ),
    ConditionIndicator.TREND_STRENGTH: (
        "均线趋势强度",
        "【功能】综合判断均线排列、斜率、价格位置的强度评分。\n\n"
        "【评分维度】\n"
        "  · 均线是否多头排列（权重40%）\n"
        "  · 均线斜率是否为正（权重30%）\n"
        "  · 价格是否在均线上方（权重30%）\n\n"
        "【参数说明】\n"
        "  · periods：参考均线列表，默认[5,10,20,30]\n\n"
        "【使用示例】\n"
        "  评分80以上=强趋势，60-80=中等趋势\n"
        "  例：MA多头排列+斜率向上+价格在方=满分\n\n"
        "【适用场景】趋势质量的化评估"
    ),
    ConditionIndicator.PRICE_ABOVE_MA: (
        "价格站上均线",
        "【功能】判断 Close > MA(N)。\n\n"
        "【参数】ma_period：均线周期，默认20，范围5-120\n\n"
        "【示例】ma_period=20 → 收盘价 > 20日均线\n\n"
        "【场景】最基础的趋势确认条件"
    ),
    ConditionIndicator.TREND_DAYS: (
        "趋势持续天数",
        "【功能】统计连续收盘在MA上方的天数。\n\n"
        "【参数】ma_period / min_days\n\n"
        "【示例】min_days=10 → 至少连续10天站上均线\n\n"
        "【场景】过滤刚突破的弱趋势"
    ),
    ConditionIndicator.TREND_INTACT: (
        "趋势未破坏",
        "【功能】近N日内最低价未跌破指定均线。\n\n"
        "【参数】ma_period / n(回看天数)\n\n"
        "【示例】n=10, ma_period=20 → 近10日Low都在MA20上方\n\n"
        "【场景】确认趋势健康，未被破坏"
    ),
    ConditionIndicator.MA_BINDONG: (
        "均线粘合",
        "【功能】多条均线距离极小，即将选择方向。\n\n"
        "【参数】max_gap_pct：粘合阈值%(默认2%)\n\n"
        "【示例】MA5/10/20/30之间最大差距<2%\n"
        "  表示筹码高度集中，突破在即\n\n"
        "【场景】突破前夕的预警信号"
    ),
    ConditionIndicator.TREND_SCORE: (
        "趋势综合评分",
        "【功能】综合多因子为趋势打分(0-100)。\n\n"
        "【示例】min_score=75 → 趋势评分>=75才通过\n\n"
        "【场景】替代多个趋势条件的AND组合"
    ),
    ConditionIndicator.NEW_HIGH_N: (
        "N日新高突破",
        "【功能】今日最高价 = 近N日最高。\n\n"
        "【参数】n：回看天数，默认20\n\n"
        "【示例】n=60 → 创60日新高（季度突破）\n\n"
        "【场景】突破买入策略"
    ),
    # ── 回调 Pullback ──
    ConditionIndicator.PULLBACK_FROM_HIGH: (
        "从高点回撤",
        "【功能】当前价相对N日最高点的回撤幅度。\n\n"
        "【参数】n / min_drop / max_drop\n\n"
        "【示例】n=20, min_drop=-5, max_drop=-15\n"
        "  含义：从20日高点回调5%~15%之间\n\n"
        "【场景】低吸策略，等充分回调后入场"
    ),
    ConditionIndicator.PULLBACK_PCT: (
        "跌幅回调",
        "【功能】近N日跌幅在指定范围内。\n\n"
        "【示例】3日跌幅在-2%~-8%之间\n\n"
        "【场景】短线回调幅度确认"
    ),
    ConditionIndicator.PULLBACK_TO_MA: (
        "回踩均线",
        "【功能】价格回落到指定均线附近。\n\n"
        "【参数】ma_period / tol_pct(容忍偏差%)\n\n"
        "【示例】ma_period=10, tol_pct=2\n"
        "  含义：Close距MA10在±2%以内\n\n"
        "【场景】经典均线支撑买点"
    ),
    ConditionIndicator.PULLBACK_TO_MA5: (
        "回踩MA5",
        "【功能】价格回落至MA5附近。\n\n"
        "【参数】tol_pct：容忍偏差%(默认1.5%)\n\n"
        "【示例】股价从10元涨到11元后回落至10.85\n"
        "  MA5≈10.8, 偏差约0.5%<1.5% → 触发\n\n"
        "【场景】超短线，灵敏度高，易假信号"
    ),
    ConditionIndicator.PULLBACK_TO_MA10: (
        "回踩MA10",
        "【功能】价格回落至MA10附近，短线经典买点。\n\n"
        "【参数】tol_pct：容忍偏差%(默认2%)\n\n"
        "【示例】强势股涨停后3天回落至MA10附近\n"
        "  配合缩量阴线 → 典型低吸信号\n\n"
        "【场景】强势股短线低吸首选"
    ),
    ConditionIndicator.PULLBACK_TO_MA20: (
        "回踩MA20",
        "【功能】价格回落至MA20附近。\n\n"
        "【参数】tol_pct：容忍偏差%(默认2.5%)\n\n"
        "【示例】趋势股回调2-3周触及MA20\n\n"
        "【场景】中线趋势中的回调入场"
    ),
    ConditionIndicator.PULLBACK_TO_MA30: (
        "回踩MA30",
        "【功能】价格回落至MA30附近。\n\n"
        "【参数】tol_pct：容忍偏差%(默认3%)\n\n"
        "【示例】月线级别支撑买入\n\n"
        "【场景】大级别趋势低吸"
    ),
    ConditionIndicator.FIRST_PULLBACK: (
        "首次回踩",
        "【功能】趋势启动后第一次回踩均线。\n\n"
        "【参数】ma_period / lookback_n\n\n"
        "【示例】涨停突破后首次回踩MA10\n"
        "  首次成功率远高于多次回踩\n\n"
        "【场景】强势启动后第一个低吸机会"
    ),
    ConditionIndicator.SHRINK_PULLBACK: (
        "缩量回调",
        "【功能】回调时成交量萎缩，卖压不大。\n\n"
        "【参数说明】\n"
        "  · 回调天数(pullback_days)：回调持续最少天数(默认=3，范围1~10)\n"
        "  · 均量周期(vol_period)：均量计算天数(默认=10，范围3~20)\n"
        "  · 缩量比例(max_vol_ratio)：缩量阈值，当日量/均量上限(默认=0.7，范围0.2~1.0)\n\n"
        "【示例】回调3天量能 < 10日均量×0.7\n"
        "  说明无人愿意低价卖出\n\n"
        "【场景】配合回踩均线使用，大幅提高胜率"
    ),
    ConditionIndicator.STRONG_PULLBACK_SCORE: (
        "强势回调评分",
        "【功能】综合评估回调质量(0-100)。\n\n"
        "【评分维度】缩量+阴线+幅度适中+位置好\n\n"
        "【示例】min_score=70 → 高质量回调\n\n"
        "【场景】一键筛选优质回调买点"
    ),
    # ── 动量 Momentum ──
    ConditionIndicator.MACD_GOLDEN: (
        "MACD金叉",
        "【功能】MACD线上穿信号线(DIF>DEA)。\n\n"
        "【参数】fast=12, slow=26, signal=9\n\n"
        "【示例】DIF从下方上穿DEA → 买入信号\n\n"
        "【场景】趋势反转确认"
    ),
    ConditionIndicator.MACD_DEATH: (
        "MACD死叉",
        "【功能】MACD线下穿信号线。\n\n"
        "【示例】DIF从上方下穿DEA → 卖出警告\n\n"
        "【场景】卖出条件 或 买入过滤（排除死叉）"
    ),
    ConditionIndicator.RSI_RANGE: (
        "RSI范围",
        "【功能】RSI在指定范围内。\n\n"
        "【参数】period=14, min_rsi, max_rsi\n\n"
        "【示例】min_rsi=30, max_rsi=50\n"
        "  含义：RSI处于超卖回升区间\n\n"
        "【场景】超卖买入(30-50)或动量确认(50-80)"
    ),
    ConditionIndicator.RETURN_N_DAYS: (
        "N日收益率",
        "【功能】近N日涨幅在指定范围。\n\n"
        "【示例】n=5, min=-3%, max=3% → 近5日震荡\n\n"
        "【场景】筛选近期涨幅适中的票"
    ),
    # ── 成交量 Volume ──
    ConditionIndicator.VOLUME_PRICE_UP: (
        "放量上涨",
        "【功能】价格上涨且成交量放大。\n\n"
        "【参数】min_ratio：量比下限(默认1.5)\n\n"
        "【示例】今日涨2%且量是5日均量的1.8倍\n\n"
        "【场景】确认上涨有资金支持"
    ),
    ConditionIndicator.VOLUME_RATIO: (
        "量比过滤",
        "【功能】今日量/MA(量,N)在指定范围。\n\n"
        "【示例】min=0.5, max=3.0\n"
        "  排除极度缩量(<0.5)和异常放量(>3.0)\n\n"
        "【场景】正常量能环境确认"
    ),
    ConditionIndicator.VOLUME_SHRINK: (
        "缩量调整",
        "【功能】成交量萎缩到均量一定比例以下。\n\n"
        "【参数】max_ratio：最大量比(默认0.6)\n\n"
        "【示例】今日量 < 5日均量×0.6 → 缩量确认\n\n"
        "【场景】确认调整阶段卖压释放"
    ),
    ConditionIndicator.VOLUME_UP_PHASE: (
        "上涨阶段量能",
        "【功能】上涨日均量 > 下跌日均量×倍数。\n\n"
        "【参数】n=20, min_ratio=1.5\n\n"
        "【示例】20日内上涨日均量是下跌日的2倍\n"
        "  说明资金积极做多\n\n"
        "【场景】确认上涨有主力参与"
    ),
    ConditionIndicator.VOLUME_LAYER: (
        "分层量能",
        "【功能】对比上涨阶段和调整阶段的量能层次。\n\n"
        "【核心逻辑】调整量 < 上涨量 × 0.6\n\n"
        "【示例】上涨5天日均量5000万\n"
        "  回调3天日均量2000万(40%)\n"
        "  2000/5000=0.4 < 0.6 → 通过\n\n"
        "【场景】量价结构的核心判断因子"
    ),
    ConditionIndicator.VOLUME_YIN_FILTER: (
        "放量阴线过滤",
        "【功能】排除放量阴线（主力出货信号）。\n\n"
        "【判断】close<open 且 volume>MA(vol,5)\n\n"
        "【示例】今日收阴且量比>1.5 → 可能出货\n"
        "  此条件用于过滤（取反=安全）\n\n"
        "【场景】买入过滤，排除出货K线"
    ),
    ConditionIndicator.FUND_INTENSITY: (
        "资金介入强度",
        "【功能】综合评估量价配合度(0-100)。\n\n"
        "【示例】min_score=60 → 有明显资金关注\n\n"
        "【场景】筛选有主力资金介入的标的"
    ),
    # ── K线 Kline ──
    ConditionIndicator.KLINE_YIN: (
        "阴线",
        "【功能】判断close < open（当日下跌）。\n\n"
        "【示例】配合缩量条件 → 缩量阴线买点\n\n"
        "【场景】与成交量组合构成低吸信号"
    ),
    ConditionIndicator.KLINE_YANG: (
        "阳线",
        "【功能】判断close > open（当日上涨）。\n\n"
        "【示例】回调后首根阳线 → 反转确认\n\n"
        "【场景】确认反转或突破"
    ),
    ConditionIndicator.KLINE_SHRINK_YIN: (
        "缩量阴线",
        "【功能】close<open 且 volume<MA(vol,5)。\n\n"
        "【核心含义】下跌但无卖压 = 惜售\n\n"
        "【示例】强势股回调第3天，收小阴线\n"
        "  成交量仅为5日均量的50%\n"
        "  → 经典低吸买点\n\n"
        "【场景】低吸策略的关键K线形态"
    ),
    ConditionIndicator.KLINE_VOL_YIN: (
        "放量阴线",
        "【功能】close<open 且 volume>MA(vol,5)。\n\n"
        "【核心含义】大量卖出 = 主力可能出货\n\n"
        "【示例】高位放量收阴 → 危险信号\n"
        "  用作过滤条件（排除此类K线）\n\n"
        "【场景】买入排除过滤 或 卖出触发"
    ),
    ConditionIndicator.KLINE_LONG_LOWER: (
        "长下影线",
        "【功能】下影线 > 实体×2，有支撑。\n\n"
        "【示例】盘中大跌后尾盘拉回\n"
        "  说明下方有强支撑\n\n"
        "【场景】底部确认辅助信号"
    ),
    ConditionIndicator.KLINE_DOJI: (
        "十字星",
        "【功能】实体极小(<振幅10%)，多空平衡。\n\n"
        "【示例】连续下跌后出现十字星\n"
        "  可能是变盘信号\n\n"
        "【场景】变盘预警，需配合其他条件"
    ),
    ConditionIndicator.KLINE_BIG_YANG: (
        "大阳线",
        "【功能】涨幅超过指定百分比。\n\n"
        "【参数】min_pct：最小涨幅%(默认5%)\n\n"
        "【示例】min_pct=7 → 涨幅>7%的强势K线\n\n"
        "【场景】突破确认 或 强势统计"
    ),
    ConditionIndicator.KLINE_LIMIT_UP: (
        "涨停K线",
        "【功能】当日涨幅>=9.5%（涨停）。\n\n"
        "【示例】统计近20日涨停次数\n\n"
        "【场景】强势信号 或 活跃度筛选"
    ),
    ConditionIndicator.CONTINUOUS_RISE: (
        "连续上涨",
        "【功能】连续N日收阳线。\n\n"
        "【参数】min_days：最少连续天数\n\n"
        "【示例】min_days=3 → 连续3天收阳\n\n"
        "【场景】趋势启动确认"
    ),
    ConditionIndicator.LIMIT_UP_COUNT: (
        "涨停次数",
        "【功能】近N日涨停次数>=min_count。\n\n"
        "【示例】n=20, min_count=1\n"
        "  含义：近20日至少有1次涨停\n\n"
        "【场景】筛选近期活跃妖股"
    ),
    ConditionIndicator.BIG_YANG_COUNT: (
        "大阳线次数",
        "【功能】近N日涨幅>5%的大阳线次数。\n\n"
        "【示例】n=20, min_count=2 → 近20日至少2根大阳\n\n"
        "【场景】确认有主力运作"
    ),
    ConditionIndicator.KLINE_STRENGTH: (
        "K线强度",
        "【功能】综合K线形态的强度评分(0-100)。\n\n"
        "【示例】min_score=60 → K线形态偏多\n\n"
        "【场景】K线质量综合评估"
    ),
    # ── 强势股 Strength ──
    ConditionIndicator.STRENGTH_RETURN_N: (
        "N日涨幅",
        "【功能】过去N日累计涨幅>=min_return%。\n\n"
        "【参数】n=20, min_return=20\n\n"
        "【示例】近20日涨幅>=20% → 阶段强势股\n\n"
        "【场景】筛选强势标的"
    ),
    ConditionIndicator.STRENGTH_LIMIT_UP_COUNT: (
        "涨停次数(强势)",
        "【功能】过去N日涨停次数>=min_count。\n\n"
        "【示例】n=20, min_count=1\n"
        "  近20日至少有1次涨停的票\n\n"
        "【场景】筛选近期有涨停的活跃票"
    ),
    ConditionIndicator.STRENGTH_BIG_YANG_COUNT: (
        "大阳线次数(强势)",
        "【功能】过去N日大阳线次数>=min_count。\n\n"
        "【参数】min_pct=5(大阳定义)\n\n"
        "【示例】近20日3根涨幅>5%的K线\n\n"
        "【场景】确认有主力资金运作"
    ),
    ConditionIndicator.STRENGTH_VOL_BREAK: (
        "放量突破",
        "【功能】价格创N日新高且成交量放大。\n\n"
        "【示例】创20日新高+量是均量2倍\n\n"
        "【场景】趋势启动或加速确认"
    ),
    ConditionIndicator.STRENGTH_SCORE: (
        "强势股评分",
        "【功能】综合涨幅/涨停/大阳/放量的评分。\n\n"
        "【示例】min_score=70 → 高强度标的\n\n"
        "【场景】一键筛选强势股"
    ),
    # ── 偏离 Deviation ──
    ConditionIndicator.DEV_MA5: (
        "MA5乖离率",
        "【功能】(Close-MA5)/MA5 × 100%。\n\n"
        "【参数】max_dev：最大允许偏离%(默认5%)\n\n"
        "【示例】max_dev=5 → 乖离率不超过5%\n"
        "  超过5%说明短线超涨\n\n"
        "【场景】排除短线涨幅过大的票"
    ),
    ConditionIndicator.DEV_MA10: (
        "MA10乖离率",
        "【功能】(Close-MA10)/MA10 × 100%。\n\n"
        "【参数】max_dev：最大偏离%\n\n"
        "【示例】max_dev=8 → 中短线偏离<8%\n\n"
        "【场景】中短线超涨/超跌判断"
    ),
    ConditionIndicator.DEV_MA20: (
        "MA20乖离率",
        "【功能】(Close-MA20)/MA20 × 100%。\n\n"
        "【示例】正偏离>15% → 严重超涨\n\n"
        "【场景】中期趋势偏离评估"
    ),
    ConditionIndicator.DEV_MA10_MA20: (
        "MA10-MA20距离",
        "【功能】两条均线之间的距离比例。\n\n"
        "【参数】max_gap_pct：最大允许距离%\n\n"
        "【示例】max_gap_pct=5\n"
        "  MA10与MA20距离>5% → 趋势过热\n"
        "  MA10与MA20距离<1% → 粘合震荡\n\n"
        "【场景】过滤均线发散过大的票"
    ),
    ConditionIndicator.DEV_OVERBOUGHT: (
        "超涨过滤",
        "【功能】排除短期涨幅过大的票。\n\n"
        "【示例】综合MA5/10/20乖离率判断\n\n"
        "【场景】低吸策略必备过滤条件"
    ),
    # ── 市场 Market ──
    ConditionIndicator.MARKET_INDEX_TREND: (
        "指数趋势",
        "【功能】大盘指数均线趋势判断。\n\n"
        "【示例】上证MA20向上 → 市场偏多\n"
        "  MA20向下 → 停止买入\n\n"
        "【场景】市场环境过滤开关"
    ),
    ConditionIndicator.MARKET_RISK: (
        "市场风险状态",
        "【功能】综合跌停数/涨跌比/指数评估风险。\n\n"
        "【参数】max_risk：最大风险等级(1-5)\n\n"
        "【示例】max_risk=3 → 风险等级>3时停止策略\n\n"
        "【场景】极端行情保护"
    ),
    # ── 波动 Volatility ──
    ConditionIndicator.ATR_RATIO: (
        "ATR波动率",
        "【功能】ATR/Close反映个股波动水平。\n\n"
        "【示例】ATR/Close>5% → 高波动股\n\n"
        "【场景】排除波动过大或过小的票"
    ),
    ConditionIndicator.BOLL_WIDTH: (
        "布林带宽",
        "【功能】(上轨-下轨)/中轨，反映波动。\n\n"
        "【示例】带宽<5% → 低波动即将突破\n\n"
        "【场景】突破前夕关注 或 风险控制"
    ),
    # ── 时间 Time ──
    ConditionIndicator.TIME_OF_DAY: (
        "时间窗口",
        "【功能】限制信号只在指定时间段触发。\n\n"
        "【参数】min_time / max_time (H:MM)\n\n"
        "【示例】min_time=9:30, max_time=10:00\n"
        "  仅在开盘半小时内触发\n\n"
        "【场景】日内分时策略时段控制"
    ),
    # ── 卖出 Exit ──
    ConditionIndicator.STOP_LOSS: (
        "止损",
        "【功能】跌破买入价×(1-pct%)时卖出。\n\n"
        "【参数】pct：止损比例%(默认8%)\n\n"
        "【示例】pct=8 → 亏损8%强制止损\n\n"
        "【场景】风控底线，建议始终设置"
    ),
    ConditionIndicator.TAKE_PROFIT: (
        "止盈",
        "【功能】涨到买入价×(1+pct%)时卖出。\n\n"
        "【参数】pct：止盈比例%(默认15%)\n\n"
        "【示例】pct=15 → 盈利15%锁定利润\n\n"
        "【场景】固定止盈，防止利润回吐"
    ),
    ConditionIndicator.TRAILING_STOP: (
        "追踪止盈",
        "【功能】从最高点回撤超过指定比例时卖出。\n\n"
        "【参数】take_profit=10, trail_drawdown=5\n\n"
        "【示例】盈利10%后启动追踪，从最高点回撤5%止盈\n"
        "  如：买入10元→涨到12元(+20%)→回落到11.4(-5%)卖出\n\n"
        "【场景】让利润奔跑，同时保护已有收益"
    ),
    ConditionIndicator.MA_BREAK_DOWN: (
        "跌破均线",
        "【功能】价格跌破指定均线时卖出。\n\n"
        "【参数】ma_period：均线周期(默认20)\n\n"
        "【示例】Close < MA20 → 趋势破坏卖出\n\n"
        "【场景】趋势跟踪策略的退出条件"
    ),
    ConditionIndicator.MACD_DEATH_SELL: (
        "MACD死叉卖出",
        "【功能】MACD线下穿信号线时触发卖出。\n\n"
        "【示例】持仓期间DIF下穿DEA → 卖出\n\n"
        "【场景】趋势反转卖出信号"
    ),
    ConditionIndicator.MAX_HOLD_DAYS: (
        "最大持仓天数",
        "【功能】持仓超过N天强制卖出。\n\n"
        "【参数】days：最大天数(默认60)\n\n"
        "【示例】days=30 → 持仓超过30天无论盈亏都卖\n\n"
        "【场景】避免长期套牢，释放资金"
    ),
    # ── 评分 Score ──
    ConditionIndicator.SCORE_NODE: (
        "综合评分节点",
        "【功能】对所有维度条件进行加权评分。\n\n"
        "【权重配置】\n"
        "  趋势25分 / 强势20分 / 成交量20分\n"
        "  回调20分 / K线10分 / 市场5分\n\n"
        "【参数】min_score：最低触发分(默认80)\n\n"
        "【示例】趋势满分+量能满分+回调满分=65分\n"
        "  加上K线10分+市场5分=80分 → 刚好触发\n\n"
        "【场景】替代AND逻辑，允许部分条件不满足\n"
        "  但总评分够高仍然触发信号"
    ),
}


# ══════════════════════════════════════════════════════════════════════════
# 拖放树控件 — 手动拖放实现（不使用 InternalMove，避免 C++ 层崩溃）
# ══════════════════════════════════════════════════════════════════════════

class _DraggableTreeWidget(QtWidgets.QTreeWidget):
    """
    支持内部拖放排序的条件树控件。

    关键设计：**不使用** InternalMove 模式。
    InternalMove 会让 Qt 在 C++ 层自行移动 item，与 Python 层频繁
    clear()/rebuild 配合时产生野指针崩溃。

    替代方案：
    - 使用 DragDrop 模式，但在 dropEvent 中 **不调用 super()**
    - 完全在 Python 层面操作 ConditionNode 树结构
    - 操作完成后重建整个 QTreeWidget（安全、可控）
    """

    # 当拖放完成后发射，通知外层 editor 重建树
    node_moved = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(
            QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        # 关闭 Qt 默认 drop indicator，改由 paintEvent 自绘（默认的太细太暗）
        self.setDropIndicatorShown(False)
        self.setAutoExpandDelay(400)  # 悬停 400ms 自动展开分组，便于拖入
        # 显式记录被拖动的节点（比 currentItem() 更可靠，避免时序问题）
        self._drag_node: Optional[ConditionNode] = None

        # 自绘 drop indicator 的运行时状态
        self._drop_target_item: Optional[QtWidgets.QTreeWidgetItem] = None
        self._drop_position = (
            QtWidgets.QAbstractItemView.DropIndicatorPosition.OnViewport)
        self._drop_invalid: bool = False

        # 缓存最后一次 dragMoveEvent 计算的放置目标节点和位置
        # dropEvent 直接使用这些缓存值，避免松开鼠标时微小位移导致重新计算
        # 得出不同结果
        self._cached_drop_target_node: Optional[ConditionNode] = None
        self._cached_drop_pos = (
            QtWidgets.QAbstractItemView.DropIndicatorPosition.OnViewport)

        # 悬浮提示 QLabel（附着在 viewport 上，光标旁显示放置位置的文字）
        self._hint_label = QtWidgets.QLabel(self.viewport())
        self._hint_label.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._hint_label.hide()

    def startDrag(self, supported_actions) -> None:
        """
        重写拖动起点：显式记录被拖动的 ConditionNode。

        为什么不依赖 dropEvent 里的 self.currentItem()：
          currentItem() 反映的是"当前选中项"，在快速点击-拖动、或拖动
          过程中选中态被其他逻辑改变时，可能与真正被拖动的项不一致，
          导致移动错节点。startDrag 在拖动真正开始时被调用，此刻的
          selected/pressed item 就是用户抓起的那一项，最为准确。
        """
        item = self.currentItem()
        if item is not None:
            node = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            self._drag_node = node
            _log(f"startDrag: node={getattr(node, 'label', None)}")
        else:
            self._drag_node = None
        super().startDrag(supported_actions)

    def dragEnterEvent(self, event) -> None:
        """只接受来自自身的拖放"""
        if event.source() is self:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        """拖动过程中更新自绘的 drop indicator +悬浮提示文字。
        解析当前光标位置的放置目标和位置类型（Above/Below/On），
        校验合法性，更新自绘状态并触发 viewport 重绘。
        """
        if event.source() is not self:
            event.ignore()
            self._clear_drop_visuals()
            return

        view_pos = event.position().toPoint()
        target_item, drop_pos = self._compute_drop_target(view_pos)

        # 校验：不能放到自身或后代，根节点不可拖
        invalid_reason = ""
        dragged_node = self._drag_node
        if dragged_node is not None:
            editor = self._get_editor()
            if editor and editor._tree_data:
                if dragged_node is editor._tree_data:
                    invalid_reason = "根节点不可移动"
                elif target_item is not None:
                    target_node = target_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                    if target_node and self._is_ancestor_of(dragged_node, target_node):
                        invalid_reason = "不能放到自身或后代上"

        self._drop_target_item = target_item
        self._drop_position = drop_pos
        self._drop_invalid = bool(invalid_reason)

        # 缓存目标节点和位置，供 dropEvent 直接使用
        # 这样即使松开鼠标时光标微移几像素，也不会重新计算出不同的结果
        if target_item is not None:
            self._cached_drop_target_node = target_item.data(
                0, QtCore.Qt.ItemDataRole.UserRole)
        else:
            self._cached_drop_target_node = None
        self._cached_drop_pos = drop_pos

        self.viewport().update()

        # 更新悬浮提示文字
        hint = self._build_hint_text(dragged_node, target_item, drop_pos, invalid_reason)
        self._update_hint_label(view_pos, hint, self._drop_invalid)

        event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        """离开视口时清除自绘状态"""
        self._clear_drop_visuals()
        super().dragLeaveEvent(event)

    def paintEvent(self, event) -> None:
        """先调用基类绘制树，再自绘醒目的 drop indicator"""
        super().paintEvent(event)
        if self._drop_target_item is None:
            return
        painter = QtGui.QPainter(self.viewport())
        try:
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            color = QtGui.QColor(_RED if self._drop_invalid else _DROP_BETWEEN)
            rect = self.visualItemRect(self._drop_target_item)
            if rect.isEmpty():
                return
            DIP = QtWidgets.QAbstractItemView.DropIndicatorPosition
            if self._drop_position == DIP.AboveItem:
                y = rect.top()
                pen = QtGui.QPen(color, 4)
                pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawLine(rect.left() + 4, y, rect.right() - 4, y)
                painter.setBrush(color)
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.drawEllipse(QtCore.QPoint(rect.left() + 4, y), 5, 5)
                painter.drawEllipse(QtCore.QPoint(rect.right() - 4, y), 5, 5)
            elif self._drop_position == DIP.BelowItem:
                y = rect.bottom()
                pen = QtGui.QPen(color, 4)
                pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawLine(rect.left() + 4, y, rect.right() - 4, y)
                painter.setBrush(color)
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.drawEllipse(QtCore.QPoint(rect.left() + 4, y), 5, 5)
                painter.drawEllipse(QtCore.QPoint(rect.right() - 4, y), 5, 5)
            elif self._drop_position == DIP.OnItem:
                fill = QtGui.QColor(color)
                fill.setAlpha(60)
                painter.setBrush(fill)
                pen = QtGui.QPen(color, 2)
                painter.setPen(pen)
                inner = rect.adjusted(2, 2, -2, -2)
                painter.drawRoundedRect(inner, 5, 5)
        finally:
            painter.end()

    def _compute_drop_target(
        self, view_pos: QtCore.QPoint
    ) -> Tuple[Optional[QtWidgets.QTreeWidgetItem],
               "QtWidgets.QAbstractItemView.DropIndicatorPosition"]:
        """根据光标位置计算放置目标和位置（Above/Below/On/OnViewport）

        关键设计：对于**已展开且有子节点**的分组节点，不提供 BelowItem
        选项。因为 BelowItem 意味着"在父列表中插到该分组之后"，但视觉上
        该位置在分组所有展开子节点的下方，而指示线却画在分组头部底边，
        导致视觉与实际不一致。此类分组只有 AboveItem（顶部20%）和
        OnItem（其余区域=放入组内）。"放到分组下方"通过悬停在分组最后
        一个子节点的下半部分来自然触发。
        """
        DIP = QtWidgets.QAbstractItemView.DropIndicatorPosition
        target_item = self.itemAt(view_pos)
        if target_item is None:
            return None, DIP.OnViewport
        rect = self.visualItemRect(target_item)
        if rect.height() <= 0:
            return target_item, DIP.OnItem
        y_offset = view_pos.y() - rect.y()
        h = rect.height()
        node = target_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        is_group = (node is not None and node.op != NodeOp.LEAF)

        # 根节点（顶层 item，无 parent）：不能有兄弟，所以只有 OnItem
        is_root_item = (target_item.parent() is None)
        if is_root_item and is_group:
            return target_item, DIP.OnItem

        if is_group:
            # 判断该分组是否已展开且有可见子节点
            is_expanded_with_children = (
                target_item.isExpanded() and target_item.childCount() > 0)
            if is_expanded_with_children:
                # 已展开的分组：只有 Above(顶部20%) 和 OnItem(其余)
                # 不提供 BelowItem，避免指示线位置与实际放置位置不一致
                if y_offset < h * 0.2:
                    return target_item, DIP.AboveItem
                return target_item, DIP.OnItem
            else:
                # 收起的分组或空分组：正常三段式
                if y_offset < h * 0.2:
                    return target_item, DIP.AboveItem
                if y_offset > h * 0.8:
                    return target_item, DIP.BelowItem
                return target_item, DIP.OnItem
        else:
            if y_offset < h * 0.5:
                return target_item, DIP.AboveItem
            return target_item, DIP.BelowItem

    def _build_hint_text(
        self,
        dragged_node: Optional[ConditionNode],
        target_item: Optional[QtWidgets.QTreeWidgetItem],
        pos: "QtWidgets.QAbstractItemView.DropIndicatorPosition",
        invalid_reason: str = "",
    ) -> str:
        """生成悬浮提示文字"""
        if invalid_reason:
            return f"⛔ {invalid_reason}"
        DIP = QtWidgets.QAbstractItemView.DropIndicatorPosition
        if target_item is None or pos == DIP.OnViewport:
            return "➜ 放入根节点末尾"
        target_node = target_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        tgt_name = ""
        if target_node:
            tgt_name = target_node.label or (
                target_node.condition.display_name() if target_node.condition else "?")
        if pos == DIP.AboveItem:
            return f"➜ 放到「{tgt_name}」上方"
        if pos == DIP.BelowItem:
            return f"➜ 放到「{tgt_name}」下方"
        if pos == DIP.OnItem:
            if target_node and target_node.op != NodeOp.LEAF:
                return f"➜ 放入「{tgt_name}」组内"
            return f"➜ 放到「{tgt_name}」后面"
        return ""

    def _update_hint_label(self, view_pos: QtCore.QPoint, text: str,
                            is_invalid: bool = False) -> None:
        """更新并显示悬浮提示 label"""
        if not text:
            self._hint_label.hide()
            return
        color = _RED if is_invalid else _DROP_BETWEEN
        self._hint_label.setStyleSheet(
            f"QLabel{{background:rgba(30,30,46,235);color:{_FG};"
            f"border:2px solid {color};border-radius:6px;"
            f"padding:6px 10px;font-size:13px;font-weight:bold;}}")
        self._hint_label.setText(text)
        self._hint_label.adjustSize()
        vw = self.viewport().width()
        vh = self.viewport().height()
        w = self._hint_label.width()
        h = self._hint_label.height()
        x = view_pos.x() +18
        y = view_pos.y() + 18
        if x + w > vw:
            x = view_pos.x() - w - 8
        if y + h > vh:
            y = view_pos.y() - h - 8
        x = max(2, min(x, vw - w - 2))
        y = max(2, min(y, vh - h - 2))
        self._hint_label.move(x, y)
        self._hint_label.show()
        self._hint_label.raise_()

    def _clear_drop_visuals(self) -> None:
        """清除自绘 drop indicator 和悬浮标签"""
        self._drop_target_item = None
        self._drop_position = QtWidgets.QAbstractItemView.DropIndicatorPosition.OnViewport
        self._drop_invalid = False
        self._hint_label.hide()
        self.viewport().update()

    def dropEvent(self, event) -> None:
        """
        关键：不调用 super().dropEvent()！
        Qt 不会在 C++ 层移动任何 item，因此不会产生野指针。
        我们在 Python 层直接操作 ConditionNode 树，然后**延迟**重建视图。

        延迟重建的原因：
          dropEvent 在 Qt 的拖放事件处理链中，如果此时同步重建树，
          会 clear() 掉正在被 Qt 内部引用的 QTreeWidgetItem，可能导致
          C++ 层野指针。改用 QTimer.singleShot(0, ...) 把重建放到下
          一个事件循环，此时 Qt 已完成拖放处理，可以安全 clear()。

        放置位置识别（三种）：
          - OnItem       (放在目标上)     → 目标是分组则放入其中，
                                            叶节点则放入其父分组末尾
          - AboveItem    (放到目标之前)   → 与目标同级，插在目标之前
          - BelowItem    (放到目标之后)   → 与目标同级，插在目标之后
          - OnViewport   (放到空白处)     → 放入根节点末尾
        """
        _log(f"dropEvent START, pos={event.position().toPoint()}")
        try:
            if event.source() is not self:
                _log("  source != self, ignore")
                event.ignore()
                return

            # 获取被拖动的 node：优先使用 startDrag 记录的 _drag_node
            # （最可靠），回退到 currentItem()。
            dragged_node: Optional[ConditionNode] = self._drag_node
            if dragged_node is None:
                dragged_item = self.currentItem()
                if dragged_item is not None:
                    dragged_node = dragged_item.data(
                        0, QtCore.Qt.ItemDataRole.UserRole)
            if dragged_node is None:
                _log("  dragged_node is None, ignore")
                event.ignore()
                return
            _log(f"  dragged_node: op={dragged_node.op}, label={dragged_node.label}")

            editor = self._get_editor()
            if editor is None or editor._tree_data is None:
                _log("  no editor / no tree_data, ignore")
                event.ignore()
                return

            # 根节点不可拖动（额外保险）
            if dragged_node is editor._tree_data:
                _log("  dragged_node is root, ignore")
                event.ignore()
                return

            # 使用 dragMoveEvent 中缓存的目标节点和位置
            # 这样即使松开鼠标时光标微移几像素，放置结果仍与最后一次
            # 视觉指示线完全一致
            drop_pos = self._cached_drop_pos
            cached_target_node = self._cached_drop_target_node
            _log(f"  drop_pos={drop_pos}, cached_target_node={getattr(cached_target_node, 'label', None) or (cached_target_node.condition.display_name() if cached_target_node and cached_target_node.condition else 'None')}")

            if cached_target_node is None:
                # 放到空白处 → 根节点末尾
                new_parent = editor._tree_data
                insert_index = -1  # -1 表示末尾
            else:
                target_node: ConditionNode = cached_target_node
                if target_node is None:
                    _log("  target_node is None, ignore")
                    event.ignore()
                    return

                # 不能把节点放到自身或自己的后代节点上
                if self._is_ancestor_of(dragged_node, target_node):
                    _log("  target is descendant of dragged, ignore")
                    event.ignore()
                    return

                DIP = QtWidgets.QAbstractItemView.DropIndicatorPosition
                if drop_pos == DIP.OnItem:
                    # 放到目标上
                    if target_node.op != NodeOp.LEAF:
                        # 目标是分组 → 放入其中末尾
                        new_parent = target_node
                        insert_index = -1
                    else:
                        # 目标是叶节点 → 放入其父分组末尾
                        new_parent = self._find_parent_node(
                            editor._tree_data, target_node) or editor._tree_data
                        insert_index = -1
                elif drop_pos in (DIP.AboveItem, DIP.BelowItem):
                    # 上/下方 → 与目标同级
                    if target_node is editor._tree_data:
                        # 根节点不能有兄弟，退化为放入根节点末尾
                        new_parent = editor._tree_data
                        insert_index = -1
                    else:
                        new_parent = self._find_parent_node(
                            editor._tree_data, target_node) or editor._tree_data
                        try:
                            base_index = new_parent.children.index(target_node)
                        except ValueError:
                            base_index = len(new_parent.children)
                        insert_index = (base_index
                                        if drop_pos == DIP.AboveItem
                                        else base_index + 1)
                else:
                    # OnViewport 或其他 → 根节点末尾
                    new_parent = editor._tree_data
                    insert_index = -1

            # 二次校验：new_parent 不能是被拖动节点的后代（或自身）
            if self._is_ancestor_of(dragged_node, new_parent):
                _log("  new_parent is descendant of dragged, ignore")
                event.ignore()
                return

            # 从原父节点中移除
            old_parent = self._find_parent_node(editor._tree_data, dragged_node)
            if old_parent is None:
                _log("  cannot find old_parent, ignore")
                event.ignore()
                return
            try:
                old_index = old_parent.children.index(dragged_node)
            except ValueError:
                _log("  dragged_node not in old_parent.children, ignore")
                event.ignore()
                return

            # 处理"移动到同一父节点内"的索引偏移：
            # 从旧位置移除后，若插入位置在旧位置之后，需要减 1
            if old_parent is new_parent and insert_index >= 0 and insert_index > old_index:
                insert_index -= 1

            old_parent.children.pop(old_index)

            # 添加到新父节点的指定位置
            if insert_index < 0 or insert_index >= len(new_parent.children):
                new_parent.children.append(dragged_node)
            else:
                new_parent.children.insert(insert_index, dragged_node)

            _log(f"  moved: old_parent={old_parent.label}[{old_index}] "
                 f"-> new_parent={new_parent.label}[{insert_index}]")

            # 记录待选中项，重建后恢复选中被拖动的节点
            editor._pending_select = dragged_node

            event.acceptProposedAction()

            # 延迟重建视图 —— 避开 Qt 拖放事件处理中的野指针陷阱
            QtCore.QTimer.singleShot(0, self.node_moved.emit)
            _log("dropEvent DONE (rebuild deferred)")
        except Exception as e:
            event.ignore()
            _show_exc_dialog("拖放操作异常", e)
        finally:
            # 清理本次拖动记录，避免残留影响下一次拖动判断
            self._drag_node = None

    def _is_ancestor_of(self, ancestor: ConditionNode,
                        descendant: ConditionNode) -> bool:
        """检查 ancestor 是否是 descendant 的祖先（或自身）"""
        if ancestor is descendant:
            return True
        if ancestor.op == NodeOp.LEAF:
            return False
        for child in ancestor.children:
            if self._is_ancestor_of(child, descendant):
                return True
        return False

    def _find_parent_node(self, root: ConditionNode,
                          target: ConditionNode) -> Optional[ConditionNode]:
        """在树中找到 target 的父节点"""
        if root.op == NodeOp.LEAF:
            return None
        for child in root.children:
            if child is target:
                return root
            result = self._find_parent_node(child, target)
            if result is not None:
                return result
        return None

    def _remove_node_from_tree(self, root: ConditionNode,
                               target: ConditionNode) -> bool:
        """从树中移除 target 节点"""
        if root.op == NodeOp.LEAF:
            return False
        for i, child in enumerate(root.children):
            if child is target:
                root.children.pop(i)
                return True
            if self._remove_node_from_tree(child, target):
                return True
        return False

    def _get_editor(self) -> Optional["ConditionTreeEditor"]:
        """向上查找 ConditionTreeEditor 父控件"""
        p = self.parent()
        while p is not None:
            if isinstance(p, ConditionTreeEditor):
                return p
            p = p.parent()
        return None


class ParamPanel(QtWidgets.QWidget):
    params_changed = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._widgets: dict = {}
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._layout.addWidget(_lbl("选择条件后显示参数", _MUT, 12))

    def load(self, indicator: ConditionIndicator,
             current_params: Optional[dict] = None) -> None:
        self._widgets.clear()
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if indicator not in _COND_META:
            self._layout.addWidget(_lbl("无可配置参数", _MUT, 12))
            return
        _, _, default_params = _COND_META[indicator]
        merged = {**default_params, **(current_params or {})}
        ss = _spin_ss()
        for key, val in merged.items():
            self._layout.addWidget(_lbl(self._param_label(key), _MUT, 12))
            if isinstance(val, float):
                sp = QtWidgets.QDoubleSpinBox()
                sp.setRange(-9999.0, 9999.0); sp.setValue(val)
                sp.setDecimals(2); sp.setSingleStep(0.5)
                sp.setStyleSheet(ss); sp.valueChanged.connect(self._emit)
                self._widgets[key] = sp; self._layout.addWidget(sp)
            elif isinstance(val, int):
                sp = QtWidgets.QSpinBox()
                sp.setRange(1, 9999); sp.setValue(val)
                sp.setStyleSheet(ss); sp.valueChanged.connect(self._emit)
                self._widgets[key] = sp; self._layout.addWidget(sp)
            elif isinstance(val, str):
                edit = QtWidgets.QLineEdit(val)
                edit.setProperty("_is_str", True)
                edit.setStyleSheet(
                    f"QLineEdit{{background:{_PAN2};color:{_FG};"
                    f"border:1px solid {_BORD};border-radius:4px;"
                    f"padding:3px 6px;font-size:13px;}}")
                edit.textChanged.connect(self._emit)
                self._widgets[key] = edit; self._layout.addWidget(edit)
            elif isinstance(val, list):
                edit = QtWidgets.QLineEdit(str(val))
                edit.setStyleSheet(
                    f"QLineEdit{{background:{_PAN2};color:{_FG};"
                    f"border:1px solid {_BORD};border-radius:4px;"
                    f"padding:3px 6px;font-size:13px;}}")
                edit.textChanged.connect(self._emit)
                self._widgets[key] = edit; self._layout.addWidget(edit)
        self._layout.addWidget(_lbl("权重 weight", _MUT, 12))
        wsp = QtWidgets.QDoubleSpinBox()
        wsp.setRange(0.1, 5.0); wsp.setValue(1.0)
        wsp.setSingleStep(0.1); wsp.setDecimals(1)
        wsp.setStyleSheet(ss); wsp.valueChanged.connect(self._emit)
        self._widgets["weight"] = wsp; self._layout.addWidget(wsp)

        # ── Insight 解读区域（内联渲染） ──
        self._render_insight_inline(indicator)

        self._layout.addStretch()

    def get_params(self) -> dict:
        result = {}
        for key, w in self._widgets.items():
            if isinstance(w, QtWidgets.QDoubleSpinBox):
                result[key] = w.value()
            elif isinstance(w, QtWidgets.QSpinBox):
                result[key] = w.value()
            elif isinstance(w, QtWidgets.QLineEdit):
                if w.property("_is_str"):
                    result[key] = w.text()
                else:
                    try: result[key] = eval(w.text())
                    except Exception: result[key] = w.text()
        return result

    def _emit(self) -> None:
        self.params_changed.emit(self.get_params())

    def _render_insight_inline(self, indicator: ConditionIndicator) -> None:
        """内联渲染 Insight 解读内容，完全使用 QLabel（零外部依赖）"""
        try:
            from ..insight.manager import ConditionInsightManager
            mgr = ConditionInsightManager.instance()
            insight = mgr.get(indicator)
        except Exception:
            insight = None

        if not insight:
            # fallback 到旧帮助文字
            help_text = self._get_help_text(indicator)
            if help_text:
                sep = QtWidgets.QFrame()
                sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
                sep.setStyleSheet(f"border:none;border-top:1px solid {_BORD};margin-top:8px;")
                self._layout.addWidget(sep)
                lbl = QtWidgets.QLabel(help_text)
                lbl.setWordWrap(True)
                lbl.setStyleSheet(
                    f"color:{_FG};font-size:13px;background:transparent;"
                    f"border:none;padding:4px 2px;line-height:1.6;")
                self._layout.addWidget(lbl)
            return

        # ── 分隔线 ──
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(f"border:none;border-top:1px solid {_BORD};margin-top:8px;")
        self._layout.addWidget(sep)

        # ── 构建富文本内容 ──
        lines = []
        lines.append(f'<span style="color:{_BLU};font-size:17px;font-weight:bold;">'
                     f'\U0001f4ca {insight.name}</span>')
        if insight.description:
            lines.append(f'<span style="color:{_FG};font-size:17px;">'
                         f'{insight.description}</span>')
        if insight.formula:
            lines.append(f'<br/><span style="color:{_YLW};font-size:17px;font-weight:bold;">'
                         f'\U0001f4d0 \u8ba1\u7b97\u516c\u5f0f</span>')
            lines.append(f'<span style="color:{_GRN};font-size:17px;'
                         f'font-family:Consolas,monospace;">{insight.formula}</span>')
        if insight.trigger:
            lines.append(f'<br/><span style="color:{_YLW};font-size:17px;font-weight:bold;">'
                         f'\u26a1 \u89e6\u53d1\u6761\u4ef6</span>')
            lines.append(f'<span style="color:#f9e2af;font-size:17px;">'
                         f'{insight.trigger}</span>')
        if insight.parameters:
            lines.append(f'<br/><span style="color:{_YLW};font-size:17px;font-weight:bold;">'
                         f'\u2699\ufe0f \u53c2\u6570\u8bf4\u660e</span>')
            for p in insight.parameters:
                ptxt = f'\u2022 {p.label}\uff08{p.name}\uff09'
                if p.description:
                    ptxt += f'\uff1a{p.description}'
                parts = []
                if p.default is not None:
                    parts.append(f'\u9ed8\u8ba4={p.default}')
                if p.range_min is not None and p.range_max is not None:
                    parts.append(f'\u8303\u56f4 {p.range_min}~{p.range_max}')
                if parts:
                    ptxt += f'({", ".join(parts)})'
                lines.append(f'<span style="color:{_FG};font-size:17px;">{ptxt}</span>')
        if insight.scenarios_good:
            lines.append(f'<br/><span style="color:{_GRN};font-size:17px;font-weight:bold;">'
                         f'\U0001f3af \u9002\u7528\u573a\u666f</span>')
            lines.append(f'<span style="color:{_GRN};font-size:17px;">'
                         f'\u2705 {" / ".join(insight.scenarios_good)}</span>')
        if insight.scenarios_bad:
            lines.append(f'<span style="color:{_YLW};font-size:17px;">'
                         f'\u26a0\ufe0f {" / ".join(insight.scenarios_bad)}</span>')
        if insight.combinations:
            lines.append(f'<br/><span style="color:{_BLU};font-size:17px;font-weight:bold;">'
                         f'\U0001f517 \u63a8\u8350\u642d\u914d</span>')
            lines.append(f'<span style="color:{_BLU};font-size:17px;">'
                         f'{" + ".join(insight.combinations)}</span>')
        if insight.risks:
            lines.append(f'<br/><span style="color:{_RED};font-size:17px;font-weight:bold;">'
                         f'\u26a0\ufe0f \u98ce\u9669\u63d0\u793a</span>')
            for r in insight.risks:
                lines.append(f'<span style="color:{_RED};font-size:17px;">\u2022 {r}</span>')
        if insight.experience:
            lines.append(f'<br/><span style="color:{_PNK};font-size:17px;font-weight:bold;">'
                         f'\U0001f4a1 \u7ecf\u9a8c\u603b\u7ed3</span>')
            lines.append(f'<span style="color:{_PNK};font-size:17px;">'
                         f'{insight.experience}</span>')

        html = '<br/>'.join(lines)
        content_lbl = QtWidgets.QLabel(html)
        content_lbl.setTextFormat(QtCore.Qt.TextFormat.RichText)
        content_lbl.setWordWrap(True)
        content_lbl.setStyleSheet(
            f"background:transparent;border:none;padding:4px 2px;")
        self._layout.addWidget(content_lbl)

    @staticmethod
    def _get_help_text(indicator: ConditionIndicator) -> str:
        """从 _COND_HELP 获取帮助文字，找不到返回空"""
        entry = _COND_HELP.get(indicator)
        if entry and len(entry) >= 2:
            return entry[1]
        return ""

    @staticmethod
    def _param_label(key: str) -> str:
        return {
            "ma_period":"MA周期","slope_window":"斜率窗口","min_slope":"最小斜率",
            "n":"天数N","window":"窗口(天)","min_drop":"最小跌幅(%)","max_drop":"最大跌幅(%)",
            "tol_pct":"偏差容忍(%)","fast":"快线","slow":"慢线","signal":"信号线",
            "period":"计算周期","min_rsi":"RSI下限","max_rsi":"RSI上限",
            "min_return":"最小收益(%)","min_ratio":"量比下限","max_ratio":"量比上限",
            "min_chg":"涨幅下限(%)","min_days":"最少上涨天数","min_count":"最少次数",
            "min_pct":"最小涨幅(%)","min_score":"最小得分","pct":"触发比例(%)",
            "take_profit":"止盈触发(%)","trail_drawdown":"追踪回撤(%)",
            "days":"最大天数","std_mult":"标准差倍数","min_width":"最小带宽",
            "periods":"均线列表(如[10,20,30])","max_gap_pct":"相邻间距上限(%,0=不限)","weight":"权重",
            "min_time":"起始时间(HH:MM)","max_time":"截止时间(HH:MM)",
            "lookback":"回看天数","pullback_days":"回调天数","vol_period":"均量周期",
            "max_vol_ratio":"缩量比例上限","vol_ratio":"量比倍数","price_pct":"涨幅阈值(%)",
            "max_spread_pct":"最大粘合距离(%)","max_distance_pct":"最大距离(%)",
            "up_window":"上涨窗口(天)","dn_window":"下跌窗口(天)","min_vol_ratio":"最小量比",
            "max_above_pct":"最大偏离(%)","max_dev_pct":"最大乖离(%)","max_body_ratio":"最大实体比",
        }.get(key, key)


class ConditionTreeEditor(QtWidgets.QWidget):
    """条件树可视化编辑器（树控件 + 参数面板）"""

    tree_changed = QtCore.Signal()

    def __init__(self, parent=None, root_display_label: str = ""):
        super().__init__(parent)
        self._tree_data: Optional[ConditionNode] = None
        self._pending_select: Optional[ConditionNode] = None
        self._root_display_label: str = root_display_label
        # 关键防崩溃标志：True 表示正在重建树，此时任何来自 QTree
        # 的信号槽都直接 return，避免访问被销毁的 QTreeWidgetItem
        self._rebuilding: bool = False
        self._init_ui()

    def _make_qtree(self) -> "_DraggableTreeWidget":
        """
        创建并配置一个全新的条件树控件（含全部信号连接）。

        用于「控件替换法」重建：每次重建时都新建一个干净的 QTreeWidget，
        彻底避免对同一控件反复 clear() 导致的 Qt C++ 内部野指针崩溃。
        """
        qtree = _DraggableTreeWidget()
        qtree.setHeaderHidden(True)
        qtree.setStyleSheet(
            f"QTreeWidget{{background:{_PAN2};color:{_FG};"
            f"border:1px solid {_BORD};border-radius:4px;font-size:13px;}}"
            f"QTreeWidget::item{{padding:4px 2px;}}"
            f"QTreeWidget::item:hover{{background:#313244;}}"
            f"QTreeWidget::item:selected{{background:{_BLU};color:#1e1e2e;}}"
            f"QScrollBar:vertical{{background:{_PAN2};width:8px;border:none;}}"
            f"QScrollBar::handle:vertical{{background:{_BORD};border-radius:4px;}}"
        )
        qtree.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        qtree.customContextMenuRequested.connect(self._show_context_menu)
        qtree.currentItemChanged.connect(self._on_item_selected)
        qtree.node_moved.connect(self._on_node_moved)
        return qtree

    def _init_ui(self) -> None:
        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self._main_layout = h  # 保存引用，供控件替换法使用

        # 左：树控件（支持拖放排序）
        self._qtree = self._make_qtree()
        h.addWidget(self._qtree, 3)

        # 右：参数面板
        right = QtWidgets.QWidget()
        right.setStyleSheet(f"background:{_BG};")
        rv = QtWidgets.QVBoxLayout(right)
        rv.setContentsMargins(8, 4, 0, 0)
        rv.setSpacing(4)
        rv.addWidget(_lbl("参数设置", _YLW, 13))
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(f"border:none;border-top:1px solid {_BORD};")
        rv.addWidget(sep)

        self._param_panel = ParamPanel()
        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(self._param_panel)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea{{background:{_BG};border:none;}}"
            f"QScrollBar:vertical{{background:{_PAN2};width:8px;border:none;}}"
            f"QScrollBar::handle:vertical{{background:{_BORD};border-radius:4px;}}"
        )
        rv.addWidget(scroll, 1)

        apply_btn = QtWidgets.QPushButton("✓  应用参数")
        apply_btn.setStyleSheet(
            f"QPushButton{{background:{_GRN};color:#1e1e2e;"
            f"border:none;border-radius:4px;padding:6px 14px;"
            f"font-size:13px;font-weight:bold;}}"
            f"QPushButton:hover{{background:#b9f0b2;}}"
        )
        apply_btn.clicked.connect(self._apply_params)
        rv.addWidget(apply_btn)
        h.addWidget(right, 2)

    # ── 公开接口 ──────────────────────────────────────────────────────

    def load_tree(self, node: ConditionNode) -> None:
        """
        重建条件树视图 —— 采用「控件替换法」彻底根治 clear() 崩溃。

        崩溃根因（由崩溃日志确认）：
          错误类型 = Windows fatal exception: access violation（C++ 野指针），
          堆栈定位在 self._qtree.clear() 这一行。QTreeWidget.clear() 会同步
          销毁全部 QTreeWidgetItem 的 C++ 对象，但 Qt 内部（hover 状态、
          viewport、item 委托、拖放状态机等）在某些时机仍持有指向这些已销毁
          item 的指针，随后访问即触发 access violation。这是 C++ 层崩溃，
          **Python 的 try/except 完全无法捕获**，表现为程序直接闪退。
          前几次 clear() 侥幸成功、多次操作后才崩，属于典型偶发竞态。

        根治方案（控件替换法）：
          不再对同一个 QTreeWidget 反复 clear() + 原地重建，而是每次都：
            1. 构建一个全新的 QTreeWidget（内部状态干净，无历史野指针）
            2. 填充新数据后，用新控件替换掉布局中的旧控件
            3. 把旧控件从父级摘除并 deleteLater()，交给 Qt 在事件循环空闲时
               安全销毁——此时不再有任何操作触碰它的内部 item 指针。
          这样彻底规避了「销毁旧 item 的同时 Qt 仍引用它」的竞态。
        """
        _log(f"load_tree START, node.op={node.op if node else None}, "
             f"children_count={len(node.children) if node else 0}")
        try:
            self._tree_data = node

            old_tree = self._qtree

            # 步骤 1: 隔离旧控件——断开其所有信号、禁用拖放，防止在替换/销毁
            #         过程中它的槽函数或内部状态机被触发访问已失效数据。
            try:
                old_tree.blockSignals(True)
            except Exception:
                pass
            try:
                old_tree.currentItemChanged.disconnect(self._on_item_selected)
            except (TypeError, RuntimeError):
                pass
            try:
                old_tree.customContextMenuRequested.disconnect(
                    self._show_context_menu)
            except (TypeError, RuntimeError):
                pass
            try:
                old_tree.node_moved.disconnect(self._on_node_moved)
            except (TypeError, RuntimeError):
                pass
            try:
                old_tree.setDragDropMode(
                    QtWidgets.QAbstractItemView.DragDropMode.NoDragDrop)
                old_tree.setDragEnabled(False)
                old_tree.setAcceptDrops(False)
            except Exception:
                pass

            # 步骤 2: 构建全新树控件并填充数据（在加入布局前完成，避免闪烁）
            new_tree = self._make_qtree()
            new_tree.blockSignals(True)
            root_item = self._build_qtree_item(node)
            new_tree.addTopLevelItem(root_item)
            new_tree.expandAll()
            _log("  新控件 rebuild 完成")

            # 步骤 3: 用新控件替换布局中的旧控件
            self._main_layout.replaceWidget(old_tree, new_tree)
            self._qtree = new_tree

            # 步骤 4: 安全销毁旧控件——先从父级摘除，再 deleteLater()
            #         deleteLater() 会把销毁推迟到事件循环空闲，此时 Qt 已
            #         不再处理任何指向旧 item 的事件，销毁绝对安全。
            old_tree.setParent(None)
            old_tree.deleteLater()
            _log("  旧控件已 deleteLater")

            # 步骤 5: 处理待选中项（信号仍 block，不会触发槽）
            if self._pending_select is not None:
                self._select_node_item(self._pending_select)
                self._pending_select = None
                _log("  pending_select 已应用")

            # 步骤 6: 解除信号屏蔽（信号连接已在 _make_qtree 中建立）
            new_tree.blockSignals(False)
            _log("load_tree DONE")
        except Exception as e:
            self._show_error("load_tree", e)

    def _select_node_item(self, target: ConditionNode) -> None:
        """遍历树控件，选中与 target 对应的 item"""
        it = QtWidgets.QTreeWidgetItemIterator(self._qtree)
        while it.value():
            item = it.value()
            if item.data(0, QtCore.Qt.ItemDataRole.UserRole) is target:
                self._qtree.setCurrentItem(item)
                item.setExpanded(True)
                return
            it += 1

    def get_tree(self) -> Optional[ConditionNode]:
        return self._tree_data

    def add_condition(self, indicator: ConditionIndicator) -> None:
        try:
            if self._tree_data is None or indicator not in _COND_META:
                return
            _, factory, _ = _COND_META[indicator]
            leaf = ConditionNode.leaf(factory())

            # 目标分组：优先使用当前选中节点所在的分组
            target = self._resolve_target_group()
            target.add_child(leaf)

            # 记录待选中的目标分组，重建后展开并高亮，便于连续添加
            self._pending_select = target
            self.load_tree(self._tree_data)
            self.tree_changed.emit()
        except Exception as e:
            self._show_error("add_condition", e)

    def _resolve_target_group(self) -> ConditionNode:
        """
        解析条件应挂载到的分组节点：
          - 未选中任何节点        → 根节点
          - 选中分组(AND/OR/NOT)  → 该分组自身
          - 选中叶条件            → 其所在的父分组
        """
        item = self._qtree.currentItem()
        if item is None:
            return self._tree_data
        node: ConditionNode = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if node is None:
            return self._tree_data
        if node.op != NodeOp.LEAF:
            return node
        # 叶节点 → 找父分组（通过树控件的父 item）
        parent_item = item.parent()
        if parent_item is not None:
            parent_node = parent_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if parent_node is not None:
                return parent_node
        return self._tree_data

    # ── 构建 QTreeWidgetItem ──────────────────────────────────────────

    def _build_qtree_item(self, node: ConditionNode) -> QtWidgets.QTreeWidgetItem:
        if node.op == NodeOp.LEAF:
            cond = node.condition
            name = cond.display_name() if cond else "?"
            cat  = cond.category      if cond else None
            item = QtWidgets.QTreeWidgetItem([f"  {name}"])
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, node)
            item.setForeground(0, QtGui.QColor(self._cat_color(cat)))
            # 叶节点：可拖动，不可接收放置
            item.setFlags(
                QtCore.Qt.ItemFlag.ItemIsEnabled
                | QtCore.Qt.ItemFlag.ItemIsSelectable
                | QtCore.Qt.ItemFlag.ItemIsDragEnabled
            )
            return item

        op_colors = {NodeOp.AND: _GRN, NodeOp.OR: _YLW,
                     NodeOp.NOT: _RED, NodeOp.SEQUENCE: _MAV}
        is_root = (node is self._tree_data)
        # SEQUENCE 节点在标签后追加间隔/窗口摘要，便于一眼看清配置
        # 清理 label 中冗余的操作符名称（例如 "AND 条件组" → "条件组"）
        display_label = node.label
        for prefix in ("AND ", "OR ", "NOT "):
            if display_label.startswith(prefix):
                display_label = display_label[len(prefix):]
                break

        if node.op == NodeOp.SEQUENCE:
            gap_txt = (f"间隔≤{node.default_gap}根"
                       if node.default_gap > 0 else "间隔不限")
            win_txt = (f"末步≤{node.recent_window}根内"
                       if node.recent_window > 0 else "末步不限")
            head = f"[顺序]  {display_label}  ({gap_txt}, {win_txt})"
        elif is_root:
            # 根节点：如果设置了固定显示标签则使用，否则用节点自身 label
            root_label = self._root_display_label or display_label
            head = f"{root_label}"
        else:
            head = f"[{node.op.value}]  {display_label}"
        item = QtWidgets.QTreeWidgetItem([head])
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, node)
        item.setForeground(0, QtGui.QColor(op_colors.get(node.op, _FG)))
        f = QtGui.QFont(); f.setBold(True)
        item.setFont(0, f)
        # 设置拖放 flags
        if is_root:
            # 根节点：不可拖动，但可以接收放置
            item.setFlags(
                QtCore.Qt.ItemFlag.ItemIsEnabled
                | QtCore.Qt.ItemFlag.ItemIsSelectable
                | QtCore.Qt.ItemFlag.ItemIsDropEnabled
            )
        else:
            # 非根分组节点：可拖动，可接收放置
            item.setFlags(
                QtCore.Qt.ItemFlag.ItemIsEnabled
                | QtCore.Qt.ItemFlag.ItemIsSelectable
                | QtCore.Qt.ItemFlag.ItemIsDragEnabled
                | QtCore.Qt.ItemFlag.ItemIsDropEnabled
            )
        for child in node.children:
            item.addChild(self._build_qtree_item(child))
        return item

    # ── 右键菜单 ──────────────────────────────────────────────────────

    def _show_context_menu(self, pos) -> None:
        item = self._qtree.itemAt(pos)
        if item is None:
            return
        node: ConditionNode = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{_PAN2};color:{_FG};"
            f"border:1px solid {_BORD};font-size:13px;}}"
            f"QMenu::item{{padding:6px 20px;}}"
            f"QMenu::item:selected{{background:{_BLU};color:#1e1e2e;}}"
        )
        if node.op != NodeOp.LEAF:
            menu.addAction("＋ 添加 AND 子树",
                           lambda: self._add_op_node(node, NodeOp.AND))
            menu.addAction("＋ 添加 OR 子树",
                           lambda: self._add_op_node(node, NodeOp.OR))
            menu.addAction("＋ 添加 顺序(SEQUENCE)子树",
                           lambda: self._add_op_node(node, NodeOp.SEQUENCE))
            menu.addSeparator()
        if node.op == NodeOp.SEQUENCE:
            menu.addAction("⚙ 配置顺序参数…",
                           lambda: self._config_sequence(node))
            menu.addSeparator()
        if item.parent() is not None:
            menu.addAction("🗑  删除此节点",
                           lambda: self._delete_node(node))
        menu.exec(self._qtree.viewport().mapToGlobal(pos))

    def _add_op_node(self, parent: ConditionNode, op: NodeOp) -> None:
        label = {NodeOp.AND: "条件组", NodeOp.OR: "条件组",
                 NodeOp.SEQUENCE: "顺序组"}.get(op, op.value)
        if op == NodeOp.SEQUENCE:
            child = ConditionNode.sequence_node(
                default_gap=10, recent_window=5, label=label)
        else:
            child = ConditionNode(op=op, label=label)
        parent.add_child(child)
        self._pending_select = child
        self.load_tree(self._tree_data)
        self.tree_changed.emit()

    def _config_sequence(self, node: ConditionNode) -> None:
        """弹窗配置 SEQUENCE 节点的默认间隔与末步窗口（K线根数）。"""
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("顺序组参数配置")
        dlg.setStyleSheet(f"QDialog{{background:{_BG};color:{_FG};}}"
                          f"QLabel{{color:{_FG};font-size:13px;}}")
        form = QtWidgets.QFormLayout(dlg)

        gap_sp = QtWidgets.QSpinBox()
        gap_sp.setRange(0, 9999); gap_sp.setValue(node.default_gap)
        gap_sp.setStyleSheet(_spin_ss())
        form.addRow("相邻步骤最大间隔(K线根数, 0=不限)", gap_sp)

        win_sp = QtWidgets.QSpinBox()
        win_sp.setRange(0, 9999); win_sp.setValue(node.recent_window)
        win_sp.setStyleSheet(_spin_ss())
        form.addRow("末步须落在最近(K线根数, 0=不限)", win_sp)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)

        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            node.default_gap    = gap_sp.value()
            node.recent_window  = win_sp.value()
            self.load_tree(self._tree_data)
            self.tree_changed.emit()

    def _delete_node(self, node: ConditionNode) -> None:
        def _remove(par: ConditionNode) -> bool:
            for i, ch in enumerate(par.children):
                if ch is node:
                    par.children.pop(i)
                    return True
                if _remove(ch):
                    return True
            return False
        if self._tree_data:
            _remove(self._tree_data)
            self.load_tree(self._tree_data)
            self.tree_changed.emit()

    # ── 拖放完成回调 ─────────────────────────────────────────────────

    def _on_node_moved(self) -> None:
        """拖放操作完成后重建树视图并通知外部"""
        try:
            if self._tree_data:
                self.load_tree(self._tree_data)
                self.tree_changed.emit()
        except Exception as e:
            import traceback
            tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            msg = QtWidgets.QMessageBox(self)
            msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            msg.setWindowTitle("拖放重建树异常")
            msg.setText(f"重建条件树时发生异常：\n{type(e).__name__}: {e}")
            msg.setDetailedText(tb_str)
            msg.exec()

    # ── 参数面板联动 ──────────────────────────────────────────────────

    def _on_item_selected(self, current, _prev) -> None:
        try:
            if current is None:
                return
            node: ConditionNode = current.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if node and node.op == NodeOp.LEAF and node.condition:
                self._param_panel.load(node.condition.indicator,
                                       node.condition.params)
        except Exception as e:
            self._show_error("_on_item_selected", e)

    def _apply_params(self) -> None:
        item = self._qtree.currentItem()
        if item is None:
            return
        node: ConditionNode = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if node and node.op == NodeOp.LEAF and node.condition:
            p = self._param_panel.get_params()
            node.condition.params = {k: v for k, v in p.items() if k != "weight"}
            node.condition.weight = p.get("weight", 1.0)
            self.load_tree(self._tree_data)
            self.tree_changed.emit()

    # ── 工具 ──────────────────────────────────────────────────────────

    def _show_error(self, method_name: str, exc: Exception) -> None:
        """统一错误弹窗，显示异常详情"""
        import traceback
        tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        msg.setWindowTitle("条件编辑器异常")
        msg.setText(f"在 {method_name} 中发生异常：\n{type(exc).__name__}: {exc}")
        msg.setDetailedText(tb_str)
        msg.exec()

    @staticmethod
    def _cat_color(cat) -> str:
        if cat is None:
            return _FG
        return {
            ConditionCategory.TREND:      _GRN,
            ConditionCategory.PULLBACK:   _BLU,
            ConditionCategory.MOMENTUM:   _YLW,
            ConditionCategory.VOLUME:     _MAV,
            ConditionCategory.KLINE:      _PNK,
            ConditionCategory.VOLATILITY: "#94e2d5",
            ConditionCategory.EXIT:       _RED,
            ConditionCategory.STRENGTH:   "#fab387",
            ConditionCategory.DEVIATION:  "#74c7ec",
            ConditionCategory.MARKET:     "#94e2d5",
            ConditionCategory.SCORE:      _YLW,
        }.get(cat, _FG)
