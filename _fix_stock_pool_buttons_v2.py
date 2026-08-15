"""修复股票池按钮无响应问题 - 完整版

问题根因：
stock_pool.py 使用异步后台加载，首次点击返回空列表，用户看不到反馈

解决方案：
1. 检测到空结果时，显示"正在加载"提示
2. 添加重试机制（等待1秒后自动重试）
3. 提供友好的用户反馈
"""

import re

# 读取widget.py
with open("vnpy/strategy_condition/ui/widget.py", "r", encoding="utf-8") as f:
    content = f.read()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 修改 _set_exchange_pool 函数 - 添加加载提示和重试
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

old_exchange = r'''    def _set_exchange_pool\(self, exchange_key: str, name: str = ""\) -> None:
        """按交易所筛选股票"""
        try:
            from vnpy\.trader\.stock_pool import get_symbols_by_exchange
            symbols = get_symbols_by_exchange\(exchange_key\)
            if symbols:
                self\._current_pool_name = name or exchange_key
                self\._pool_edit\.setPlainText\("\\n"\.join\(symbols\)\)
        except Exception as e:
            self\._show_msg\(f"交易所筛选失败: \{e\}"\)'''

new_exchange = '''    def _set_exchange_pool(self, exchange_key: str, name: str = "") -> None:
        """按交易所筛选股票（带加载提示和重试）"""
        try:
            from vnpy.trader.stock_pool import get_symbols_by_exchange
            symbols = get_symbols_by_exchange(exchange_key)
            
            if symbols:
                self._current_pool_name = name or exchange_key
                self._pool_edit.setPlainText("\\n".join(symbols))
                self._pool_count_lbl.setText(
                    f"✓ 已加载 {name or exchange_key}: {len(symbols)} 只股票"
                )
            else:
                # 数据可能正在后台加载，显示友好提示并自动重试
                self._pool_count_lbl.setText(
                    f"⏳ 正在加载 {name or exchange_key} 数据，请稍候..."
                )
                QtCore.QTimer.singleShot(1500, lambda: self._retry_exchange_pool(exchange_key, name))
                
        except Exception as e:
            self._show_msg(f"交易所筛选失败: {e}")
            self._pool_count_lbl.setText(f"✗ 加载失败: {e}")
    
    def _retry_exchange_pool(self, exchange_key: str, name: str = "") -> None:
        """重试加载交易所股票池"""
        try:
            from vnpy.trader.stock_pool import get_symbols_by_exchange
            symbols = get_symbols_by_exchange(exchange_key)
            
            if symbols:
                self._current_pool_name = name or exchange_key
                self._pool_edit.setPlainText("\\n".join(symbols))
                self._pool_count_lbl.setText(
                    f"✓ 已加载 {name or exchange_key}: {len(symbols)} 只股票"
                )
            else:
                self._pool_count_lbl.setText(
                    f"⚠ {name or exchange_key} 暂无数据。\\n"
                    f"请先通过【数据管理】下载K线数据，或等待后台加载完成后重试。"
                )
        except Exception as e:
            self._pool_count_lbl.setText(f"✗ 重试失败: {e}")'''

content = re.sub(old_exchange, new_exchange, content, flags=re.DOTALL)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 修改 _set_board_pool 函数 - 添加加载提示和重试
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

old_board = r'''    def _set_board_pool\(self, board_name: str\) -> None:
        """按板块筛选股票"""
        try:
            from vnpy\.trader\.stock_pool import get_symbols_by_board
            symbols = get_symbols_by_board\(board_name\)
            if symbols:
                self\._current_pool_name = board_name
                self\._pool_edit\.setPlainText\("\\n"\.join\(symbols\)\)
        except Exception as e:
            self\._show_msg\(f"板块筛选失败: \{e\}"\)'''

new_board = '''    def _set_board_pool(self, board_name: str) -> None:
        """按板块筛选股票（带加载提示和重试）"""
        try:
            from vnpy.trader.stock_pool import get_symbols_by_board
            symbols = get_symbols_by_board(board_name)
            
            if symbols:
                self._current_pool_name = board_name
                self._pool_edit.setPlainText("\\n".join(symbols))
                self._pool_count_lbl.setText(
                    f"✓ 已加载 {board_name}: {len(symbols)} 只股票"
                )
            else:
                # 数据可能正在后台加载，显示友好提示并自动重试
                self._pool_count_lbl.setText(
                    f"⏳ 正在加载 {board_name} 数据，请稍候..."
                )
                QtCore.QTimer.singleShot(1500, lambda: self._retry_board_pool(board_name))
                
        except Exception as e:
            self._show_msg(f"板块筛选失败: {e}")
            self._pool_count_lbl.setText(f"✗ 加载失败: {e}")
    
    def _retry_board_pool(self, board_name: str) -> None:
        """重试加载板块股票池"""
        try:
            from vnpy.trader.stock_pool import get_symbols_by_board
            symbols = get_symbols_by_board(board_name)
            
            if symbols:
                self._current_pool_name = board_name
                self._pool_edit.setPlainText("\\n".join(symbols))
                self._pool_count_lbl.setText(
                    f"✓ 已加载 {board_name}: {len(symbols)} 只股票"
                )
            else:
                self._pool_count_lbl.setText(
                    f"⚠ {board_name} 暂无数据。\\n"
                    f"请先通过【数据管理】下载K线数据，或等待后台加载完成后重试。"
                )
        except Exception as e:
            self._pool_count_lbl.setText(f"✗ 重试失败: {e}")'''

content = re.sub(old_board, new_board, content, flags=re.DOTALL)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 同样修改 _set_index_pool 函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

old_index = r'''    def _set_index_pool\(self, index_code: str, name: str = ""\) -> None:
        """按指数成分股筛选"""
        try:
            from vnpy\.trader\.index_constituents import get_constituents
            symbols = get_constituents\(index_code\)
            if symbols:
                self\._current_pool_name = name or index_code
                self\._pool_edit\.setPlainText\("\\n"\.join\(symbols\)\)
        except Exception as e:
            self\._show_msg\(f"指数成分股加载失败: \{e\}"\)'''

new_index = '''    def _set_index_pool(self, index_code: str, name: str = "") -> None:
        """按指数成分股筛选（带加载提示和重试）"""
        try:
            from vnpy.trader.index_constituents import get_constituents
            symbols = get_constituents(index_code)
            
            if symbols:
                self._current_pool_name = name or index_code
                self._pool_edit.setPlainText("\\n".join(symbols))
                self._pool_count_lbl.setText(
                    f"✓ 已加载 {name or index_code}: {len(symbols)} 只股票"
                )
            else:
                self._pool_count_lbl.setText(
                    f"⏳ 正在加载 {name or index_code} 数据，请稍候..."
                )
                QtCore.QTimer.singleShot(1500, lambda: self._retry_index_pool(index_code, name))
                
        except Exception as e:
            self._show_msg(f"指数成分股加载失败: {e}")
            self._pool_count_lbl.setText(f"✗ 加载失败: {e}")
    
    def _retry_index_pool(self, index_code: str, name: str = "") -> None:
        """重试加载指数成分股"""
        try:
            from vnpy.trader.index_constituents import get_constituents
            symbols = get_constituents(index_code)
            
            if symbols:
                self._current_pool_name = name or index_code
                self._pool_edit.setPlainText("\\n".join(symbols))
                self._pool_count_lbl.setText(
                    f"✓ 已加载 {name or index_code}: {len(symbols)} 只股票"
                )
            else:
                self._pool_count_lbl.setText(
                    f"⚠ {name or index_code} 暂无数据。\\n"
                    f"请先通过【数据管理】下载相关股票的K线数据。"
                )
        except Exception as e:
            self._pool_count_lbl.setText(f"✗ 重试失败: {e}")'''

content = re.sub(old_index, new_index, content, flags=re.DOTALL)

# 写回文件
with open("vnpy/strategy_condition/ui/widget.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✓ 股票池按钮修复完成（V2版本）")
print("\n修复内容:")
print("  1. 添加 '正在加载...' 友好提示")
print("  2. 空结果时自动1.5秒后重试")
print("  3. 重试失败后显示清晰的操作指引")
print("  4. 适用于：交易所、板块、指数成分")
print("\n请重启应用测试效果！")
