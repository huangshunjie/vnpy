"""修复股票池按钮无响应问题 - V3改进版

问题根因：
stock_pool.py 使用异步后台加载，首次点击返回空列表

V3 改进：
1. 增加重试延迟：从1.5秒改为3秒（首次数据库查询需要5-10秒）
2. 添加多次重试：最多重试3次，每次间隔递增（3秒、5秒、8秒）
3. 更清晰的用户反馈：显示重试次数和等待时间
4. 添加手动刷新按钮提示
"""

import re

# 读取widget.py
with open("vnpy/strategy_condition/ui/widget.py", "r", encoding="utf-8") as f:
    content = f.read()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 修改 _set_exchange_pool 函数 - 增加重试延迟和次数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

old_exchange = r'''    def _set_exchange_pool\(self, exchange_key: str, name: str = ""\) -> None:
        """按交易所筛选股票（带加载提示和重试）"""
        try:
            from vnpy\.trader\.stock_pool import get_symbols_by_exchange
            symbols = get_symbols_by_exchange\(exchange_key\)
            
            if symbols:
                self\._current_pool_name = name or exchange_key
                self\._pool_edit\.setPlainText\("\\n"\.join\(symbols\)\)
                self\._pool_count_lbl\.setText\(
                    f"✓ 已加载 \{name or exchange_key\}: \{len\(symbols\)\} 只股票"
                \)
            else:
                # 数据可能正在后台加载，显示友好提示并自动重试
                self\._pool_count_lbl\.setText\(
                    f"⏳ 正在加载 \{name or exchange_key\} 数据，请稍候\.\.\."
                \)
                QtCore\.QTimer\.singleShot\(1500, lambda: self\._retry_exchange_pool\(exchange_key, name\)\)
                
        except Exception as e:
            self\._show_msg\(f"交易所筛选失败: \{e\}"\)
            self\._pool_count_lbl\.setText\(f"✗ 加载失败: \{e\}"\)'''

new_exchange = '''    def _set_exchange_pool(self, exchange_key: str, name: str = "", retry_count: int = 0) -> None:
        """按交易所筛选股票（带加载提示和多次重试）"""
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
                # 数据可能正在后台加载，自动重试（最多3次）
                max_retries = 3
                if retry_count < max_retries:
                    # 重试延迟递增：3秒、5秒、8秒
                    delays = [3000, 5000, 8000]
                    delay = delays[retry_count]
                    self._pool_count_lbl.setText(
                        f"⏳ 正在加载 {name or exchange_key} 数据...\\n"
                        f"   第 {retry_count + 1}/{max_retries} 次重试（{delay//1000}秒后）"
                    )
                    QtCore.QTimer.singleShot(
                        delay, 
                        lambda: self._set_exchange_pool(exchange_key, name, retry_count + 1)
                    )
                else:
                    self._pool_count_lbl.setText(
                        f"⚠ {name or exchange_key} 数据加载超时。\\n"
                        f"可能原因：\\n"
                        f"1. 首次启动需要10-20秒查询数据库\\n"
                        f"2. 未下载K线数据\\n"
                        f"解决方案：\\n"
                        f"• 等待20秒后重新点击按钮\\n"
                        f"• 或点击【刷新股票池】按钮手动加载"
                    )
                
        except Exception as e:
            self._show_msg(f"交易所筛选失败: {e}")
            self._pool_count_lbl.setText(f"✗ 加载失败: {e}")'''

content = re.sub(old_exchange, new_exchange, content, flags=re.DOTALL)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 删除旧的 _retry_exchange_pool 函数（不再需要）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

old_retry_exchange = r'''    def _retry_exchange_pool\(self, exchange_key: str, name: str = ""\) -> None:
        """重试加载交易所股票池"""
        try:
            from vnpy\.trader\.stock_pool import get_symbols_by_exchange
            symbols = get_symbols_by_exchange\(exchange_key\)
            
            if symbols:
                self\._current_pool_name = name or exchange_key
                self\._pool_edit\.setPlainText\("\\n"\.join\(symbols\)\)
                self\._pool_count_lbl\.setText\(
                    f"✓ 已加载 \{name or exchange_key\}: \{len\(symbols\)\} 只股票"
                \)
            else:
                self\._pool_count_lbl\.setText\(
                    f"⚠ \{name or exchange_key\} 暂无数据。\\n"
                    f"请先通过【数据管理】下载K线数据，或等待后台加载完成后重试。"
                \)
        except Exception as e:
            self\._pool_count_lbl\.setText\(f"✗ 重试失败: \{e\}"\)'''

content = re.sub(old_retry_exchange, '', content, flags=re.DOTALL)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 修改 _set_board_pool 函数 - 同样增加重试机制
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

old_board = r'''    def _set_board_pool\(self, board_name: str\) -> None:
        """按板块筛选股票（带加载提示和重试）"""
        try:
            from vnpy\.trader\.stock_pool import get_symbols_by_board
            symbols = get_symbols_by_board\(board_name\)
            
            if symbols:
                self\._current_pool_name = board_name
                self\._pool_edit\.setPlainText\("\\n"\.join\(symbols\)\)
                self\._pool_count_lbl\.setText\(
                    f"✓ 已加载 \{board_name\}: \{len\(symbols\)\} 只股票"
                \)
            else:
                # 数据可能正在后台加载，显示友好提示并自动重试
                self\._pool_count_lbl\.setText\(
                    f"⏳ 正在加载 \{board_name\} 数据，请稍候\.\.\."
                \)
                QtCore\.QTimer\.singleShot\(1500, lambda: self\._retry_board_pool\(board_name\)\)
                
        except Exception as e:
            self\._show_msg\(f"板块筛选失败: \{e\}"\)
            self\._pool_count_lbl\.setText\(f"✗ 加载失败: \{e\}"\)'''

new_board = '''    def _set_board_pool(self, board_name: str, retry_count: int = 0) -> None:
        """按板块筛选股票（带加载提示和多次重试）"""
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
                # 数据可能正在后台加载，自动重试（最多3次）
                max_retries = 3
                if retry_count < max_retries:
                    delays = [3000, 5000, 8000]
                    delay = delays[retry_count]
                    self._pool_count_lbl.setText(
                        f"⏳ 正在加载 {board_name} 数据...\\n"
                        f"   第 {retry_count + 1}/{max_retries} 次重试（{delay//1000}秒后）"
                    )
                    QtCore.QTimer.singleShot(
                        delay,
                        lambda: self._set_board_pool(board_name, retry_count + 1)
                    )
                else:
                    self._pool_count_lbl.setText(
                        f"⚠ {board_name} 数据加载超时。\\n"
                        f"解决方案：等待20秒后重新点击按钮"
                    )
                
        except Exception as e:
            self._show_msg(f"板块筛选失败: {e}")
            self._pool_count_lbl.setText(f"✗ 加载失败: {e}")'''

content = re.sub(old_board, new_board, content, flags=re.DOTALL)

# 删除旧的 _retry_board_pool
old_retry_board = r'''    def _retry_board_pool\(self, board_name: str\) -> None:
        """重试加载板块股票池"""
        try:
            from vnpy\.trader\.stock_pool import get_symbols_by_board
            symbols = get_symbols_by_board\(board_name\)
            
            if symbols:
                self\._current_pool_name = board_name
                self\._pool_edit\.setPlainText\("\\n"\.join\(symbols\)\)
                self\._pool_count_lbl\.setText\(
                    f"✓ 已加载 \{board_name\}: \{len\(symbols\)\} 只股票"
                \)
            else:
                self\._pool_count_lbl\.setText\(
                    f"⚠ \{board_name\} 暂无数据。\\n"
                    f"请先通过【数据管理】下载K线数据，或等待后台加载完成后重试。"
                \)
        except Exception as e:
            self\._pool_count_lbl\.setText\(f"✗ 重试失败: \{e\}"\)'''

content = re.sub(old_retry_board, '', content, flags=re.DOTALL)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 修改 _set_index_pool 函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

old_index = r'''    def _set_index_pool\(self, index_code: str, name: str = ""\) -> None:
        """按指数成分股筛选（带加载提示和重试）"""
        try:
            from vnpy\.trader\.index_constituents import get_constituents
            symbols = get_constituents\(index_code\)
            
            if symbols:
                self\._current_pool_name = name or index_code
                self\._pool_edit\.setPlainText\("\\n"\.join\(symbols\)\)
                self\._pool_count_lbl\.setText\(
                    f"✓ 已加载 \{name or index_code\}: \{len\(symbols\)\} 只股票"
                \)
            else:
                self\._pool_count_lbl\.setText\(
                    f"⏳ 正在加载 \{name or index_code\} 数据，请稍候\.\.\."
                \)
                QtCore\.QTimer\.singleShot\(1500, lambda: self\._retry_index_pool\(index_code, name\)\)
                
        except Exception as e:
            self\._show_msg\(f"指数成分股加载失败: \{e\}"\)
            self\._pool_count_lbl\.setText\(f"✗ 加载失败: \{e\}"\)'''

new_index = '''    def _set_index_pool(self, index_code: str, name: str = "", retry_count: int = 0) -> None:
        """按指数成分股筛选（带加载提示和多次重试）"""
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
                max_retries = 3
                if retry_count < max_retries:
                    delays = [3000, 5000, 8000]
                    delay = delays[retry_count]
                    self._pool_count_lbl.setText(
                        f"⏳ 正在加载 {name or index_code} 数据...\\n"
                        f"   第 {retry_count + 1}/{max_retries} 次重试（{delay//1000}秒后）"
                    )
                    QtCore.QTimer.singleShot(
                        delay,
                        lambda: self._set_index_pool(index_code, name, retry_count + 1)
                    )
                else:
                    self._pool_count_lbl.setText(
                        f"⚠ {name or index_code} 数据加载超时。"
                    )
                
        except Exception as e:
            self._show_msg(f"指数成分股加载失败: {e}")
            self._pool_count_lbl.setText(f"✗ 加载失败: {e}")'''

content = re.sub(old_index, new_index, content, flags=re.DOTALL)

# 删除旧的 _retry_index_pool
old_retry_index = r'''    def _retry_index_pool\(self, index_code: str, name: str = ""\) -> None:
        """重试加载指数成分股"""
        try:
            from vnpy\.trader\.index_constituents import get_constituents
            symbols = get_constituents\(index_code\)
            
            if symbols:
                self\._current_pool_name = name or index_code
                self\._pool_edit\.setPlainText\("\\n"\.join\(symbols\)\)
                self\._pool_count_lbl\.setText\(
                    f"✓ 已加载 \{name or index_code\}: \{len\(symbols\)\} 只股票"
                \)
            else:
                self\._pool_count_lbl\.setText\(
                    f"⚠ \{name or index_code\} 暂无数据。\\n"
                    f"请先通过【数据管理】下载相关股票的K线数据。"
                \)
        except Exception as e:
            self\._pool_count_lbl\.setText\(f"✗ 重试失败: \{e\}"\)'''

content = re.sub(old_retry_index, '', content, flags=re.DOTALL)

# 写回文件
with open("vnpy/strategy_condition/ui/widget.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✓ 股票池按钮修复完成（V3 改进版）")
print("\n改进内容:")
print("  1. ✓ 重试延迟增加：3秒 → 5秒 → 8秒（共3次）")
print("  2. ✓ 移除独立重试函数，使用递归重试")
print("  3. ✓ 更清晰的进度提示（显示第几次重试）")
print("  4. ✓ 超时后提供明确的解决方案")
print("\n预期效果:")
print("  • 首次点击：显示'正在加载...'并自动重试")
print("  • 3秒后：第1次重试")
print("  • 8秒后：第2次重试")
print("  • 16秒后：第3次重试")
print("  • 如果仍失败：提示用户等待20秒后手动点击")
print("\n请重启应用测试！")
