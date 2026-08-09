"""优化SCE股票池 - 第2步：替换方法"""
filepath = r'C:\Users\11229\Documents\GitHub\vnpy\vnpy\strategy_condition\ui\widget.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_methods = '''    # ── 股票池辅助 ────────────────────────────────────────────────────

    def _set_pool(self, symbols: list) -> None:
        if not symbols:
            self._pool_edit.clear()
        else:
            self._pool_edit.setPlainText("\\n".join(symbols))

    def _on_pool_changed(self) -> None:
        n = len(self._get_pool_symbols())
        self._pool_count_lbl.setText(f"{n} 只")'''

new_methods = '''    # ── 股票池辅助（完整版）────────────────────────────────────────────

    def _set_pool(self, symbols: list) -> None:
        if not symbols:
            self._pool_edit.clear()
        else:
            self._pool_edit.setPlainText("\\n".join(symbols))

    def _on_pool_changed(self) -> None:
        n = len(self._get_pool_symbols())
        name = getattr(self, '_current_pool_name', '')
        if name:
            self._pool_count_lbl.setText(f"{name} - {n} 只")
        else:
            self._pool_count_lbl.setText(f"{n} 只")

    def _set_exchange_pool(self, exchange_key: str, name: str = "") -> None:
        """按交易所筛选股票"""
        try:
            from vnpy.trader.stock_pool import get_symbols_by_exchange
            symbols = get_symbols_by_exchange(exchange_key)
            if symbols:
                self._current_pool_name = name or exchange_key
                self._pool_edit.setPlainText("\\n".join(symbols))
        except Exception as e:
            self._show_msg(f"交易所筛选失败: {e}")

    def _set_board_pool(self, board_name: str) -> None:
        """按板块筛选股票"""
        try:
            from vnpy.trader.stock_pool import get_symbols_by_board
            symbols = get_symbols_by_board(board_name)
            if symbols:
                self._current_pool_name = board_name
                self._pool_edit.setPlainText("\\n".join(symbols))
        except Exception as e:
            self._show_msg(f"板块筛选失败: {e}")

    def _set_index_pool(self, pool_key: str, name: str = "") -> None:
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
                self._set_pool(_POOL_CSI500)

    def _on_sce_index_changed(self, index: int) -> None:
        """从更多指数下拉框选择"""
        data = self._sce_index_combo.currentData()
        if not data:
            return
        text = self._sce_index_combo.currentText().strip()
        self._set_index_pool(data, text)
        self._sce_index_combo.blockSignals(True)
        self._sce_index_combo.setCurrentIndex(0)
        self._sce_index_combo.blockSignals(False)

    def _on_sce_industry_changed(self, index: int) -> None:
        """从行业下拉框选择"""
        industry = self._sce_industry_combo.currentData()
        if not industry:
            return
        try:
            from vnpy.trader.stock_pool import get_symbols_by_industry
            symbols = get_symbols_by_industry(industry)
            if symbols:
                self._current_pool_name = industry
                self._pool_edit.setPlainText("\\n".join(symbols))
        except Exception as e:
            self._show_msg(f"行业筛选失败: {e}")
        self._sce_industry_combo.blockSignals(True)
        self._sce_industry_combo.setCurrentIndex(0)
        self._sce_industry_combo.blockSignals(False)'''

if old_methods in content:
    content = content.replace(old_methods, new_methods)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("[OK] Step 2: Methods replaced")
else:
    print("[FAIL] Could not find old methods pattern")
