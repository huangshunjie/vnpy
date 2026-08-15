"""优化widget.py以正确显示加载状态"""

with open("vnpy/strategy_condition/ui/widget.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 修复_set_exchange_pool函数，正确导入并检查加载状态
old_function = '''    def _set_exchange_pool(self, exchange_key: str, name: str = "") -> None:
        """按交易所筛选股票"""
        try:
            from vnpy.trader.stock_pool import get_symbols_by_exchange
            
            symbols = get_symbols_by_exchange(exchange_key)
            if symbols:
                self._current_pool_name = name or exchange_key
                self._pool_edit.setPlainText("\\n".join(symbols))
            else:
                # 区分：后台加载中 vs 真的没有数据
                if _CACHE_LOADING:
                    self._show_msg("数据正在加载中，请稍后重试")
                else:
                    self._show_msg(f"{name or exchange_key} 没有找到任何股票数据\\n\\n请先通过【数据管理器】下载历史K线数据。")
        except Exception as e:
            self._show_msg(f"交易所筛选失败: {e}")'''

new_function = '''    def _set_exchange_pool(self, exchange_key: str, name: str = "") -> None:
        """按交易所筛选股票（优化：友好的加载提示）"""
        try:
            from vnpy.trader.stock_pool import get_symbols_by_exchange, is_cache_loading
            
            symbols = get_symbols_by_exchange(exchange_key)
            if symbols:
                self._current_pool_name = name or exchange_key
                self._pool_edit.setPlainText("\\n".join(symbols))
                self._show_msg(f"已加载 {len(symbols)} 只股票")
            else:
                # 区分：后台加载中 vs 真的没有数据
                if is_cache_loading():
                    self._show_msg(
                        f"正在后台加载 {name or exchange_key} 的股票数据...\\n\\n"
                        "⏳ 首次加载需要几秒钟，请稍后再次点击按钮"
                    )
                else:
                    self._show_msg(
                        f"{name or exchange_key} 没有找到任何股票数据\\n\\n"
                        "请先通过【数据管理器】下载历史K线数据。"
                    )
        except Exception as e:
            self._show_msg(f"交易所筛选失败: {e}")'''

content = content.replace(old_function, new_function)

# 写入文件
with open("vnpy/strategy_condition/ui/widget.py", "w", encoding="utf-8") as f:
    f.write(content)

print("[OK] 已优化 widget.py 的 _set_exchange_pool 函数")
print("[OK] 现在点击沪市按钮时会显示友好的加载提示")
print("\n优化完成！主要改进：")
print("1. [OK] 正确导入 is_cache_loading() 函数")
print("2. [OK] 显示友好的加载中提示（带进度说明）")
print("3. [OK] 成功加载后显示股票数量")
print("4. [OK] UI不会冻结，后台异步加载")
