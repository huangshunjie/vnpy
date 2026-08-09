# -*- coding: utf-8 -*-
"""修复 SCE _set_index_pool：直接使用 get_index_symbols 而非从 behavior_tab 导入"""

filepath = r'C:\Users\11229\Documents\GitHub\vnpy\vnpy\strategy_condition\ui\widget.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    def _set_index_pool(self, pool_key: str, name: str = "") -> None:
        """按指数成分筛选股票"""
        self._current_pool_name = name
        if pool_key.startswith("IDX:"):
            index_code = pool_key[4:]
            try:
                from vnpy.quant_research.ui.behavior_tab import _load_index_pool
                symbols = _load_index_pool(index_code)
                if symbols:
                    self._pool_edit.setPlainText("\\n".join(symbols))
                    return
            except Exception:
                pass
            # fallback
            if index_code == "000300":
                self._set_pool(_POOL_CSI300)
            elif index_code == "000905":
                self._set_pool(_POOL_CSI500)'''

new = '''    def _set_index_pool(self, pool_key: str, name: str = "") -> None:
        """按指数成分筛选股票"""
        self._current_pool_name = name
        if pool_key.startswith("IDX:"):
            index_code = pool_key[4:]
            try:
                from vnpy.trader.index_constituents import get_index_symbols
                symbols = get_index_symbols(index_code)
                if symbols:
                    self._pool_edit.setPlainText("\\n".join(symbols))
                    return
            except Exception:
                pass
            # fallback: 使用内置池
            if index_code == "000300":
                self._set_pool(_POOL_CSI300)
            elif index_code == "000905":
                self._set_pool(_POOL_CSI500)
            else:
                self._show_msg(f"\u5c1a\u65e0 {name or index_code} \u7684\u6210\u5206\u80a1\u7f13\u5b58\u6570\u636e\u3002\\n\u8bf7\u5728\u6570\u636e\u7ba1\u7406App\u4e2d\u5148\u66f4\u65b0\u3002")'''

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - fixed _set_index_pool')
else:
    print('FAIL - pattern not found')
