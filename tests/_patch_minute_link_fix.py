"""精确修复 widget.py 中日线-5分钟联动失败的 bug

修复点:
1. 降级路径错误使用空 minute_bars (line 1144):
   当 generate_snapshots 失败时,minute_bars 仍然有效,
   但代码却推 [] 给 UI,导致"5分钟 0 根"+"缺少5分钟数据"。
   修复:把 minute_bars 推给 UI,UI 内部已有 _build_minute_snapshots_fallback。

2. 缓存空 minute_snapshots 污染后续渲染:
   line 1114-1119 缓存了 (snapshots=[], bars),下次 tab 切换时,
   load_layered_data 拿到 snapshots=[] 但 bars!=[] 时会走 fallback 重建。
   这本身没问题,但如果 minute_snapshots 已经生成,不应被新空值覆盖。

3. _feed_monitor 主流程对 minute_snapshots 失败只 print 但外层 try/except
   会把整个 _feed_monitor 当作失败,降级到全 [] 路径。
   修复:确保外层 except 块中仍能访问 minute_bars(本来就在 try 内赋过值)。
"""
import io

path = "vnpy/strategy_condition/ui/widget.py"

with io.open(path, "r", encoding="utf-8") as f:
    src = f.read()

# 修复点 1: minute_snapshots 失败时 print traceback,方便调试
original_block_1 = """                except Exception as e:
                    print(f"[SCE] minute snapshots 生成失败: {e}")
                    minute_snapshots = []

            # 回测结果的卖出日期是权威来源
            effective_sell_dates = sell_dates

            # ── 存入缓存 ──
            self._snapshot_cache[cache_key] = (
                daily_snapshots, daily_bars,
                minute_snapshots, minute_bars,
            )"""

new_block_1 = """                except Exception as e:
                    # 关键：只 print+记日志,不要 raise,
                    # 否则外层 try/except 会把整个 _feed_monitor 当作失败,
                    # 走降级路径（且该路径会清空 minute_bars,导致 UI 显示
                    # "5分钟 0 根"+"缺少5分钟数据"）。
                    # 后续 _monitor_tab.load_layered_data 内部有
                    # _build_minute_snapshots_fallback 兜底。
                    print(f"[SCE] minute snapshots 生成失败: {e}")
                    import traceback as _tb_snap
                    _tb_snap.print_exc()
                    minute_snapshots = []

            # 回测结果的卖出日期是权威来源
            effective_sell_dates = sell_dates

            # ── 存入缓存 ──
            # 关键：即使 minute_snapshots 为空（生成失败）也照常缓存，
            # 因为 minute_bars 是有效的（数据库加载阶段已成功）。
            # load_layered_data 内部有 `_build_minute_snapshots_fallback`
            # 会用 bars+buy_dates/sell_dates 重建。
            self._snapshot_cache[cache_key] = (
                daily_snapshots, daily_bars,
                minute_snapshots, minute_bars,
            )"""

assert original_block_1 in src, "未找到 original_block_1"
src = src.replace(original_block_1, new_block_1, 1)
print("[OK] 修复点 1: minute snapshots 失败时 print traceback,保留 minute_bars")

# 修复点 2: 降级路径不再清空 minute_bars
# 在 except 块之前（line 1053）,minute_bars 已被赋值（try 块内的局部变量）
# 所以在 except 块中可以直接访问

original_block_2 = """        except Exception as e:
            import traceback
            print(f"[SCE] Monitor 快照生成失败: {e}")
            traceback.print_exc()
            # 降级：哪怕 snapshots 生成失败，也要保证 K 线画出来
            # （条件波形可能没数据，但至少 K 线 + 成交量能看到）
            try:
                if daily_bars:
                    # 走 load_layered_data 走双面板；minute_bars 可能没有，
                    # 但 load_layered_data 内部有 fallback 路径，能容忍空 minute。
                    self._monitor_tab.load_layered_data(
                        symbol,
                        daily_snapshots or [], daily_bars,
                        [], [],                      # minute 双空
                        buy_dates=buy_dates or [],
                        sell_dates=sell_dates or [],
                    )
                    print(
                        f"[SCE] 降级到 K 线模式："
                        f"{len(daily_bars)} 日线 (snapshots={len(daily_snapshots or [])})",
                        flush=True,
                    )"""

new_block_2 = """        except Exception as e:
            import traceback
            print(f"[SCE] Monitor 快照生成失败: {e}")
            traceback.print_exc()
            # 降级：哪怕 snapshots 生成失败，也要保证 K 线画出来
            # （条件波形可能没数据，但至少 K 线 + 成交量能看到）
            try:
                if daily_bars:
                    # 关键修复：minute_bars 不要清空！
                    # 它的赋值（line ~1054）在 try 块顶部完成，
                    # 与 generate_snapshots 失败无关。
                    # load_layered_data 内部有 _build_minute_snapshots_fallback
                    # 兜底（用 bars+signals 重建 snapshots）。
                    # 同样的，minute_snapshots 已在 try 块内被赋值（即使为空），
                    # 用其当前真实值，不要硬编码 []。
                    self._monitor_tab.load_layered_data(
                        symbol,
                        daily_snapshots or [], daily_bars,
                        minute_snapshots if minute_snapshots else [],
                        minute_bars if minute_bars else [],
                        buy_dates=buy_dates or [],
                        sell_dates=sell_dates or [],
                    )
                    print(
                        f"[SCE] 降级到 K 线模式："
                        f"{len(daily_bars)} 日线, "
                        f"{len(minute_bars) if minute_bars else 0} 分钟 "
                        f"(daily_snapshots={len(daily_snapshots or [])})",
                        flush=True,
                    )"""

assert original_block_2 in src, "未找到 original_block_2"
src = src.replace(original_block_2, new_block_2, 1)
print("[OK] 修复点 2: 降级路径保留 minute_bars 和 minute_snapshots")

with io.open(path, "w", encoding="utf-8") as f:
    f.write(src)

print(f"\n[完成] 已修复 {path}")
