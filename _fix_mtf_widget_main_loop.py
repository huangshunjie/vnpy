#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复 widget.py 多周期回测主循环数据加载逻辑

问题：多周期回测时，主循环需要遍历分钟线，但 bars_dict 传入的是日线数据
解决：当 execution_interval != anchor_interval 时，加载分钟线数据替换 bars_dict
"""

def fix_widget():
    filepath = 'vnpy/strategy_condition/ui/widget.py'
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找要替换的代码段
    old_code = '''            # 使用自动确定的执行周期
            execution_interval = req.execution_interval
            is_intraday = (execution_interval != Interval.DAILY)

            batch  = se.backtest(loaded, self._strategy, bars_dict,
                                 warmup=warmup, is_intraday=is_intraday,
                                 execution_interval=execution_interval)'''
    
    new_code = '''            # 使用自动确定的执行周期
            execution_interval = req.execution_interval
            is_intraday = (execution_interval != Interval.DAILY)

            # ═══ 多周期关键逻辑：主循环数据需要是 execution_interval 的数据 ═══
            # 当 execution_interval(分钟) != anchor_interval(日线) 时：
            #   - bars_dict 替换为分钟线数据（主循环遍历分钟K线）
            #   - 日线数据已在 MTF Buffer 中，供日线条件查询
            #   - 日线条件评估时：历史完整日线 + 当天虚拟日线(close=当前分钟close)
            if (execution_interval != anchor_interval
                    and len(req.required_intervals) > 1):
                # 加载 execution_interval 的数据作为主循环
                exec_bars_dict = {}
                if bars_dict and any(bars_dict.values()):
                    first_sym = next(s for s, b in bars_dict.items() if b)
                    anchor_bars_tmp = bars_dict[first_sym]
                    sd, ed = get_date_range_from_anchor_bars(anchor_bars_tmp)
                    _exec_cnt = 0
                    for sym in loaded:
                        _exec_cnt += 1
                        if _exec_cnt % 5 == 0:
                            QtWidgets.QApplication.processEvents()
                        eb = self._load_bars_by_date_range(
                            sym, execution_interval, sd, ed
                        )
                        exec_bars_dict[sym] = eb if eb else []
                    exec_loaded = [s for s, b in exec_bars_dict.items() if b]
                    if exec_loaded:
                        bars_dict = exec_bars_dict
                        loaded = exec_loaded
                        print(f"[SCE] 多周期回测：主循环使用 {execution_interval.value} "
                              f"数据({len(loaded)}只, 首只{len(bars_dict[loaded[0]])}根)")
                    else:
                        # 无分钟数据，降级为锚定周期
                        print(f"[SCE] 警告：无 {execution_interval.value} 数据，"
                              f"降级为 {anchor_interval.value}")
                        execution_interval = anchor_interval
                        is_intraday = False

            batch  = se.backtest(loaded, self._strategy, bars_dict,
                                 warmup=warmup, is_intraday=is_intraday,
                                 execution_interval=execution_interval)'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ widget.py 修复成功")
        print("修改位置：_on_backtest() 方法，line ~1529")
        return True
    else:
        print("❌ 未找到目标代码段")
        print("可能原因：")
        print("1. 文件已被修改")
        print("2. 行号或缩进不匹配")
        
        # 尝试找到大致位置
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'execution_interval = req.execution_interval' in line:
                print(f"\n找到相关代码在第 {i+1} 行附近")
                print("上下文：")
                for j in range(max(0, i-2), min(len(lines), i+8)):
                    print(f"{j+1:4d} | {lines[j]}")
                break
        return False

if __name__ == '__main__':
    fix_widget()