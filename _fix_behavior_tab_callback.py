"""在 behavior_tab.py 中注册刷新回调并添加单标的重算方法"""
import sys

filepath = "vnpy/quant_research/ui/behavior_tab.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 注册回调 - 在 self._tab.addTab(self._monitor_tab, ...) 之后
old_1 = '        self._monitor_tab = BehaviorMonitorTab()\n        self._tab.addTab(self._monitor_tab, "🔍 条件监控")'
new_1 = '        self._monitor_tab = BehaviorMonitorTab()\n        self._monitor_tab.set_refresh_callback(self._refresh_single_symbol)\n        self._tab.addTab(self._monitor_tab, "🔍 条件监控")'

if old_1 in content:
    content = content.replace(old_1, new_1, 1)
    print("OK - 回调注册已添加")
else:
    print("ERROR - 找不到回调注册位置")
    sys.exit(1)

# 2. 在文件末尾添加 _refresh_single_symbol 方法
new_method = '''
    def _refresh_single_symbol(self, symbol: str):
        """
        刷新回调：为单个标的重新计算条件监控数据并更新缓存。
        当用户在 Monitor Tab 切换标的后点刷新时被调用。
        """
        import pandas as pd
        from datetime import datetime

        if not self._condition_nodes:
            return

        try:
            from vnpy.trader.database import get_database
            from vnpy.trader.constant import Interval, Exchange

            parts_sym = symbol.split(".")
            if len(parts_sym) != 2:
                return
            sym, exchange_str = parts_sym
            try:
                exchange = Exchange(exchange_str)
            except ValueError:
                return

            db = get_database()
            bars = db.load_bar_data(
                symbol=sym, exchange=exchange,
                interval=Interval.DAILY,
                start=datetime(2020, 1, 1), end=datetime.now())
            if not bars or len(bars) < 30:
                return

            df = pd.DataFrame([{
                "open": b.open_price, "high": b.high_price,
                "low": b.low_price, "close": b.close_price,
                "volume": float(b.volume), "datetime": b.datetime,
            } for b in bars])
            df.set_index("datetime", inplace=True)

            feature_names = [n["name"] for n in self._condition_nodes]
            condition_displays = [n["display"] for n in self._condition_nodes]

            # 计算特征
            features_df = self._feature_calculator.calculate(df, feature_names)

            # 为每个条件逐行计算 True/False
            cond_results = pd.DataFrame(index=features_df.index)
            for node in self._condition_nodes:
                name = node["name"]
                op = node["op"]
                threshold = node["threshold"]
                display = node["display"]

                if name not in features_df.columns:
                    cond_results[display] = False
                    continue

                col = features_df[name]
                if op == ">":
                    cond_results[display] = col > threshold
                elif op == ">=":
                    cond_results[display] = col >= threshold
                elif op == "<":
                    cond_results[display] = col < threshold
                elif op == "<=":
                    cond_results[display] = col <= threshold
                elif op == "==":
                    cond_results[display] = col == threshold
                elif op == "!=":
                    cond_results[display] = col != threshold
                else:
                    cond_results[display] = False

            # 收集事件信息
            if self._logic_op == "AND":
                all_met = cond_results.all(axis=1)
            else:
                all_met = cond_results.any(axis=1)

            events = []
            for dt_idx in cond_results.index[all_met]:
                events.append({"date": str(dt_idx)[:10]})

            # 更新 monitor_tab 的缓存数据
            self._monitor_tab._monitor_data[symbol] = {
                "df": df,
                "events": events,
                "conditions": condition_displays,
                "condition_results": cond_results,
            }

            # 如果 combo 中没有这个标的，追加进去
            combo = self._monitor_tab._symbol_combo
            if combo.findText(symbol) < 0:
                combo.addItem(symbol)

        except Exception as e:
            print(f"[BehaviorLab] 刷新单标的 {symbol} 异常: {e}")
'''

# 追加到文件末尾
content = content.rstrip() + "\n" + new_method + "\n"

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("OK - behavior_tab.py 已添加 _refresh_single_symbol 方法")