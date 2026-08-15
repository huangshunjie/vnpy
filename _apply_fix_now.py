import re

with open("vnpy/strategy_condition/ui/widget.py", "r", encoding="utf-8") as f:
    content = f.read()

# 应用所有修复
modifications = [
    # 1. _set_exchange_pool
    (
        r'def _set_exchange_pool\(self, exchange_key: str, name: str = ""\) -> None:\s*"""按交易所筛选股票（带加载提示和重试）""".*?(?=\n    def )',
        '''def _set_exchange_pool(self, exchange_key: str, name: str = "", retry_count: int = 0) -> None:
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
                max_retries = 3
                if retry_count < max_retries:
                    delays = [3000, 5000, 8000]
                    delay = delays[retry_count]
                    self._pool_count_lbl.setText(
                        f"⏳ 正在加载 {name or exchange_key} 数据...\\n第 {retry_count + 1}/{max_retries} 次重试（{delay//1000}秒后）"
                    )
                    QtCore.QTimer.singleShot(
                        delay, 
                        lambda: self._set_exchange_pool(exchange_key, name, retry_count + 1)
                    )
                else:
                    self._pool_count_lbl.setText(
                        f"⚠ {name or exchange_key} 数据加载超时\\n等待20秒后重新点击按钮"
                    )
        except Exception as e:
            self._show_msg(f"交易所筛选失败: {e}")
            self._pool_count_lbl.setText(f"✗ 加载失败: {e}")

    def '''
    ),
]

for pattern, replacement in modifications:
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open("vnpy/strategy_condition/ui/widget.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✓ 修复已应用")
