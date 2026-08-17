# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
from vnpy.strategy_condition.core.mtf_context import MultiTimeframeContext, DataRequirement, analyze_data_requirements
from vnpy.trader.constant import Interval
from vnpy.strategy_condition.core.condition import Condition
from vnpy.strategy_condition.core.condition_tree import ConditionNode
from vnpy.strategy_condition.constant import ConditionCategory, ConditionIndicator
print("[OK] All imports")
ctx = MultiTimeframeContext("600028.SH")
ctx.set_bars(Interval.DAILY, [type("B",(),{"close":10.2})()])
print("[OK] MTFContext:", ctx)
print("[OK] Available:", [i.value for i in ctx.get_available_intervals()])
c1 = Condition(ConditionCategory.TREND, ConditionIndicator.MA_SLOPE, {"ma_period":20}, data_interval=Interval.DAILY)
c2 = Condition(ConditionCategory.KLINE, ConditionIndicator.BIG_YANG_COUNT, {}, data_interval=Interval.MINUTE_5)
tree = ConditionNode.and_node([ConditionNode.leaf(c1), ConditionNode.leaf(c2)])
req = analyze_data_requirements(tree, Interval.MINUTE_5)
print("[OK] DataReq:", [i.value for i in req.intervals])
assert Interval.DAILY in req.intervals
assert Interval.MINUTE_5 in req.intervals
print("[OK] Requirements correct")
d = c1.to_dict()
c_restore = Condition.from_dict(d)
assert c_restore.data_interval == Interval.DAILY
print("[OK] Serialization OK")
old = Condition(ConditionCategory.TREND, ConditionIndicator.MA_SLOPE, {"ma_period":20})
assert old.data_interval is None
print("[OK] Backward compat OK")
print("\n" + "="*50)
print("ALL PHASE 1 TESTS PASSED")
print("="*50)
