"""修复股票池按钮无响应问题"""

import re

# 读取widget.py
with open("vnpy/strategy_condition/ui/widget.py", "r", encoding="utf-8") as f:
    content = f.read()

# 修改 _set_exchange_pool 函数
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
        """按交易所筛选股票"""
        try:
            from vnpy.trader.stock_pool import get_symbols_by_exchange
            symbols = get_symbols_by_exchange(exchange_key)
            if symbols:
                self._current_pool_name = name or exchange_key
                self._pool_edit.setPlainText("\\n".join(symbols))
            else:
                self._show_msg(
                    f"未能加载 {name or exchange_key} 的股票数据。\\n\\n"
                    "可能原因：\\n"
                    "1. 数据正在后台加载中，请稍后重试\\n"
                    "2. 本地数据库没有该交易所的K线数据\\n\\n"
                    "解决方法：请先通过【数据管理器】下载K线数据。"
                )
        except Exception as e:
            self._show_msg(f"交易所筛选失败: {e}")'''

content = re.sub(old_exchange, new_exchange, content, flags=re.DOTALL)

# 修改 _set_board_pool 函数
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
        """按板块筛选股票"""
        try:
            from vnpy.trader.stock_pool import get_symbols_by_board
            symbols = get_symbols_by_board(board_name)
            if symbols:
                self._current_pool_name = board_name
                self._pool_edit.setPlainText("\\n".join(symbols))
            else:
                self._show_msg(
                    f"未能加载 {board_name} 的股票数据。\\n\\n"
                    "可能原因：\\n"
                    "1. 数据正在后台加载中，请稍后重试\\n"
                    "2. 本地数据库没有该板块的K线数据\\n\\n"
                    "解决方法：请先通过【数据管理器】下载K线数据。"
                )
        except Exception as e:
            self._show_msg(f"板块筛选失败: {e}")'''

content = re.sub(old_board, new_board, content, flags=re.DOTALL)

# 写回文件
with open("vnpy/strategy_condition/ui/widget.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✓ 已修复股票池按钮响应问题")
print("  - _set_exchange_pool: 添加友好提示")
print("  - _set_board_pool: 添加友好提示")
