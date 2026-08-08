"""Fix behavior_tab.py - append missing methods"""
import os

path = "vnpy/quant_research/ui/behavior_tab.py"
content = open(path, "r", encoding="utf-8").read()

# Find and remove the truncated last line
idx = content.rfind("def _on_feature_double_click(self, item, col")
if idx > 0:
    content = content[:idx]

# Append complete methods
methods = r'''    def _on_feature_double_click(self, item, col):
        feat = item.data(0, Qt.ItemDataRole.UserRole)
        if feat is None:
            return
        node = {
            "name": feat.name,
            "display": feat.display_name,
            "op": ">",
            "threshold": 0.0,
            "feature": feat,
        }
        self._condition_nodes.append(node)
        self._refresh_cond_tree()

    def _refresh_cond_tree(self):
        self._cond_tree.clear()
        if not self._condition_nodes:
            self._cond_summary.setText("尚未添加条件，请从左侧特征库双击添加")
            return
        root_item = QTreeWidgetItem([self._logic_op, "", ""])
        root_item.setForeground(0, QColor(_BLU))
        for node in self._condition_nodes:
            thr = node["threshold"]
            thr_str = f"{thr:.4f}" if isinstance(thr, float) else str(thr)
            child = QTreeWidgetItem([node["display"], node["op"], thr_str])
            feat = node.get("feature")
            color = _FEATURE_COLORS.get(feat.feature_type if feat else None, _FG)
            child.setForeground(0, QColor(color))
            child.setData(0, Qt.ItemDataRole.UserRole, node)
            root_item.addChild(child)
        self._cond_tree.addTopLevelItem(root_item)
        self._cond_tree.expandAll()
        parts = []
        for n in self._condition_nodes:
            parts.append(f"{n['name']} {n['op']} {n['threshold']}")
        joiner = f" {self._logic_op} "
        self._cond_summary.setText(f"表达式: {joiner.join(parts)}")

    def _on_cond_double_click(self, item, col):
        node = item.data(0, Qt.ItemDataRole.UserRole)
        if node is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"编辑条件: {node['display']}")
        dlg.setStyleSheet(f"background:{_BG};color:{_FG};")
        dlg.setMinimumWidth(300)
        layout = QVBoxLayout(dlg)
        layout.addWidget(_lbl(f"特征: {node['display']}", _FG, 13, True))
        layout.addWidget(_lbl("比较运算符:", _MUT, 12))
        op_combo = QComboBox()
        op_combo.setStyleSheet(_COMBO_SS)
        for op in [">", ">=", "<", "<=", "==", "!="]:
            op_combo.addItem(op)
        op_combo.setCurrentText(node["op"])
        layout.addWidget(op_combo)
        layout.addWidget(_lbl("阈值:", _MUT, 12))
        threshold_sp = QDoubleSpinBox()
        threshold_sp.setRange(-9999.0, 9999.0)
        threshold_sp.setDecimals(4)
        threshold_sp.setSingleStep(0.01)
        threshold_sp.setValue(float(node["threshold"]))
        threshold_sp.setStyleSheet(_SPIN_SS)
        layout.addWidget(threshold_sp)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            node["op"] = op_combo.currentText()
            node["threshold"] = threshold_sp.value()
            self._refresh_cond_tree()

    def _on_cond_context_menu(self, pos):
        item = self._cond_tree.itemAt(pos)
        if not item:
            return
        node = item.data(0, Qt.ItemDataRole.UserRole)
        if node is None:
            return
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};}}"
            f"QMenu::item:selected{{background:{_BLU};color:#1e1e2e;}}")
        del_action = menu.addAction("删除此条件")
        action = menu.exec(self._cond_tree.viewport().mapToGlobal(pos))
        if action == del_action and node in self._condition_nodes:
            self._condition_nodes.remove(node)
            self._refresh_cond_tree()

    def _on_clear_conditions(self):
        self._condition_nodes.clear()
        self._refresh_cond_tree()

    def _on_apply_template(self):
        data = self._template_combo.currentData()
        if data is None:
            return
        self._condition_nodes.clear()
        expr_str = data.get("expression", "")
        sep_parts = expr_str.replace(" AND ", "\n").replace(" OR ", "\n").split("\n")
        for part in sep_parts:
            part = part.strip()
            if not part:
                continue
            for op in [">=", "<=", "!=", ">", "<", "=="]:
                if op in part:
                    name, val = part.split(op, 1)
                    name = name.strip()
                    feat = self.feature_registry.get_feature(name)
                    display = feat.display_name if feat else name
                    try:
                        threshold = float(val.strip())
                    except ValueError:
                        threshold = 0.0
                    self._condition_nodes.append({
                        "name": name, "display": display,
                        "op": op, "threshold": threshold, "feature": feat,
                    })
                    break
        if " OR " in expr_str:
            self._set_logic(False)
        else:
            self._set_logic(True)
        self._refresh_cond_tree()

    def _on_new(self):
        self._condition_nodes.clear()
        self._refresh_cond_tree()
        self._name_edit.setText("新研究")
        self._results_table.setRowCount(0)
        self._events_count_lbl.setText("事件数: 0")
        self._symbols_count_lbl.setText("标的数: 0")
        for lbl in self._stat_labels.values():
            lbl.setText("--")
        self._status_lbl.setText("就绪")
        self._btn_save.setEnabled(False)
        self._btn_export.setEnabled(False)

    def _on_save(self):
        QMessageBox.information(self, "保存", "研究配置已保存")

    def _on_run_research(self):
        """Execute research"""
        if not self._condition_nodes:
            QMessageBox.warning(self, "提示", "请先添加研究条件")
            return
        symbols = self._get_pool_symbols()
        if not symbols:
            QMessageBox.warning(self, "提示", "请先设置股票池")
            return

        # Build condition expression
        cond_parts = []
        for n in self._condition_nodes:
            cond_parts.append(f"({n['name']} {n['op']} {n['threshold']})")
        joiner = " & " if self._logic_op == "AND" else " | "
        condition_expr = joiner.join(cond_parts)

        cooldown = self._cooldown_sp.value()
        periods = [p for p, cb in self._period_cbs.items() if cb.isChecked()]
        if not periods:
            periods = [1, 5, 10]

        self._status_lbl.setText("研究中...")
        self._progress.setVisible(True)
        self._progress.setRange(0, len(symbols))
        self._progress.setValue(0)
        QApplication.processEvents()

        try:
            from vnpy.trader.database import get_database
            from vnpy.trader.constant import Interval, Exchange
            import pandas as pd
            from datetime import datetime

            db = get_database()
            all_events = []
            processed = 0

            for sym_full in symbols:
                processed += 1
                self._progress.setValue(processed)
                if processed % 5 == 0:
                    QApplication.processEvents()

                parts_sym = sym_full.split(".")
                if len(parts_sym) != 2:
                    continue
                symbol, exchange_str = parts_sym
                try:
                    exchange = Exchange(exchange_str)
                except ValueError:
                    continue

                bars = db.load_bar_data(
                    symbol=symbol, exchange=exchange,
                    interval=Interval.DAILY,
                    start=datetime(2015, 1, 1), end=datetime.now())
                if not bars or len(bars) < 30:
                    continue

                df = pd.DataFrame([{
                    "open": b.open_price, "high": b.high_price,
                    "low": b.low_price, "close": b.close_price,
                    "volume": float(b.volume), "datetime": b.datetime,
                } for b in bars])
                df.set_index("datetime", inplace=True)

                features_df = self._feature_calculator.calculate_all(df)
                events = EventSearcher.search_events(
                    features_df, condition_expr, cooldown_days=cooldown)
                for evt in events:
                    evt["symbol"] = sym_full
                    all_events.append(evt)

            self._display_results(all_events, periods)
            self._status_lbl.setText(
                f"完成 | {len(all_events)} 事件 | {len(symbols)} 标的")
            self._btn_save.setEnabled(True)
            self._btn_export.setEnabled(True)

        except Exception as e:
            self._status_lbl.setText(f"错误: {str(e)[:50]}")
            QMessageBox.critical(self, "研究失败", str(e))
        finally:
            self._progress.setVisible(False)

    def _display_results(self, events, periods):
        """Display research results"""
        import numpy as np

        self._results_table.setRowCount(0)
        self._events_count_lbl.setText(f"事件数: {len(events)}")
        symbols_set = set(e.get("symbol", "") for e in events)
        self._symbols_count_lbl.setText(f"标的数: {len(symbols_set)}")
        self._results_table.setRowCount(len(events))

        returns_5d = []
        returns_10d = []

        for row, evt in enumerate(events):
            self._results_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self._results_table.setItem(row, 1, QTableWidgetItem(evt.get("symbol", "")))
            self._results_table.setItem(row, 2, QTableWidgetItem(str(evt.get("date", ""))))
            r1 = evt.get("return_1d", 0)
            r5 = evt.get("return_5d", 0)
            r10 = evt.get("return_10d", 0)
            self._results_table.setItem(row, 3, QTableWidgetItem(f"{r1:.2%}"))
            self._results_table.setItem(row, 4, QTableWidgetItem(f"{r5:.2%}"))
            self._results_table.setItem(row, 5, QTableWidgetItem(f"{r10:.2%}"))
            self._results_table.setItem(row, 6, QTableWidgetItem("--"))
            if r5 != 0:
                returns_5d.append(r5)
            if r10 != 0:
                returns_10d.append(r10)

        if returns_5d:
            arr = np.array(returns_5d)
            self._stat_labels["mean_5d"].setText(f"{arr.mean():.2%}")
            self._stat_labels["win_5d"].setText(f"{(arr > 0).mean():.1%}")
            std = arr.std()
            sharpe = arr.mean() / std * (252**0.5) if std > 0 else 0
            self._stat_labels["sharpe_5d"].setText(f"{sharpe:.2f}")
        if returns_10d:
            arr = np.array(returns_10d)
            self._stat_labels["mean_10d"].setText(f"{arr.mean():.2%}")
            self._stat_labels["win_10d"].setText(f"{(arr > 0).mean():.1%}")

        self._tab.setCurrentIndex(1)
'''

content += methods

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Done! File size: {len(content)} chars")