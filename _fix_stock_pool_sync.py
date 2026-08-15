"""
修复股票池按钮点击后不更新的问题

问题原因：
stock_pool.py的_ensure_symbols_cache()使用异步后台加载，
第一次调用时返回空集合，导致UI文本框不更新。

解决方案：
在widget.py的_set_exchange_pool中添加重试逻辑，
如果检测到后台正在加载，等待后重试。
"""

import re

# 读取widget.py
with open("vnpy/strategy_condition/ui/widget.py", "r", encoding="utf-8") as f:
    content = f.read()

# 找到_set_exchange_pool方法并替换
old_method = r'''    def _set_exchange_pool\(self, exchange_key: str, name: str = ""\) -> None:
        """按交易所筛选股票"""
        try:
            from vnpy\.trader\.stock_pool import get_symbols_by_exchange, _CACHE_LOADING
            
            # 检查是否正在后台加载
            if _CACHE_LOADING:
                self\._show_msg\(
                    "股票池数据正在后台加载中..\.\\n\\n"
                    "首次启动或缓存过期时需要查询数据库，通常需要10-20秒。\\n"
                    "请稍后重新点击此按钮即可加载数据。"
                \)
                return
            
            symbols = get_symbols_by_exchange\(exchange_key\)
            if symbols:
                self\._current_pool_name = name or exchange_key
                self\._pool_edit\.setPlainText\("\\n"\.join\(symbols\)\)
            else:
                # 区分：后台加载中 vs 真的没有数据
                if _CACHE_LOADING:
                    self\._show_msg\("数据正在加载中，请稍后重试"\)
                else:
                    self\._show_msg\(f"\{name or exchange_key\} 没有找到任何股票数据\\n\\n请先通过【数据管理器】下载历史K线数据。"\)
        except Exception as e:
            self\._show_msg\(f"交易所筛选失败: \{e\}"\)'''

new_method = '''    def _set_exchange_pool(self, exchange_key: str, name: str = "") -> None:
        """按交易所筛选股票（带重试机制）"""
        try:
            from vnpy.trader.stock_pool import get_symbols_by_exchange, _CACHE_LOADING
            
            # 检查是否正在后台加载
            if _CACHE_LOADING:
                self._show_msg(
                    "股票池数据正在后台加载中...\\n\\n"
                    "首次启动或缓存过期时需要查询数据库，通常需要10-20秒。\\n"
                    "请稍后重新点击此按钮即可加载数据。"
                )
                return
            
            symbols = get_symbols_by_exchange(exchange_key)
            
            # 如果返回空列表但数据正在后台加载，启动定时器重试
            if not symbols and _CACHE_LOADING:
                self._show_msg("数据正在加载中，将在5秒后自动重试...")
                # 5秒后自动重试
                QtCore.QTimer.singleShot(5000, lambda: self._retry_exchange_pool(exchange_key, name))
                return
            
            if symbols:
                self._current_pool_name = name or exchange_key
                self._pool_edit.setPlainText("\\n".join(symbols))
            else:
                self._show_msg(f"{name or exchange_key} 没有找到任何股票数据\\n\\n请先通过【数据管理器】下载历史K线数据。")
        except Exception as e:
            self._show_msg(f"交易所筛选失败: {e}")
    
    def _retry_exchange_pool(self, exchange_key: str, name: str, retry_count: int = 0) -> None:
        """重试加载交易所股票池"""
        try:
            from vnpy.trader.stock_pool import get_symbols_by_exchange, _CACHE_LOADING
            
            # 最多重试3次
            if retry_count >= 3:
                self._show_msg(f"加载{name or exchange_key}超时，请手动重试或检查数据库连接。")
                return
            
            symbols = get_symbols_by_exchange(exchange_key)
            
            if symbols:
                self._current_pool_name = name or exchange_key
                self._pool_edit.setPlainText("\\n".join(symbols))
                self._show_msg(f"成功加载{len(symbols)}只{name or exchange_key}股票")
            elif _CACHE_LOADING:
                # 仍在加载，继续重试
                QtCore.QTimer.singleShot(5000, lambda: self._retry_exchange_pool(exchange_key, name, retry_count + 1))
            else:
                self._show_msg(f"{name or exchange_key} 没有找到任何股票数据")
        except Exception as e:
            self._show_msg(f"重试失败: {e}")'''

# 替换方法
if re.search(old_method, content):
    content = re.sub(old_method, new_method, content)
    print("✓ 已替换 _set_exchange_pool 方法")
else:
    print("✗ 未找到原方法，尝试手动定位...")
    # 手动查找并替换
    pattern = r'(    def _set_exchange_pool\(self, exchange_key: str, name: str = ""\) -> None:.*?)(    def _set_board_pool)'
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(
            pattern,
            new_method + '\\n\\n\\1',
            content,
            flags=re.DOTALL
        )
        print("✓ 使用替代方法替换成功")
    else:
        print("✗ 替换失败，需要手动修复")
        exit(1)

# 保存文件
with open("vnpy/strategy_condition/ui/widget.py", "w", encoding="utf-8") as f:
    f.write(content)

print("\\n修复完成！")
print("\\n修改说明：")
print("1. _set_exchange_pool现在会检测后台加载状态")
print("2. 如果数据正在加载，会自动在5秒后重试")
print("3. 最多重试3次，避免无限等待")
print("4. 加载成功后会显示成功消息")
