"""write_reg_main2.py — RegistryTab part2: CRUD + search + stats methods (append only)"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\registry_tab.py"
)

# These are methods to append INSIDE the RegistryTab class body.
# We validate by wrapping in a dummy class for ast.parse.
CODE_METHODS = """
    def _current_tab(self) -> int:
        return self._sub_tabs.currentIndex()

    def _selected_id(self):
        idx = self._current_tab()
        if idx == 0: return self._ds_list.selected_id()
        if idx == 1: return self._ft_list.selected_id()
        if idx == 2: return self._st_list.selected_id()
        if idx == 3: return self._ml_list.selected_id()
        return None

    def _on_new(self):
        idx = self._current_tab()
        if idx == 0:
            dlg = DatasetDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                ds = self._engine.register_dataset(
                    name=dlg.get_name(), source=dlg.get_source(),
                    description=dlg.get_description(),
                    start_date=dlg.get_start_date(),
                    end_date=dlg.get_end_date(),
                    row_count=dlg.get_row_count(),
                    tags=dlg.get_tags())
                self._set_status("Dataset \\u300c" + ds.name + "\\u300d\\u5df2\\u6ce8\\u518c")
                self._refresh_stats()
        elif idx == 1:
            dlg = FeatureDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                ft = self._engine.register_feature(
                    name=dlg.get_name(), category=dlg.get_category(),
                    author=dlg.get_author(), description=dlg.get_description(),
                    formula=dlg.get_formula(), tags=dlg.get_tags())
                self._set_status("Feature \\u300c" + ft.name + "\\u300d\\u5df2\\u6ce8\\u518c")
                self._refresh_stats()
        elif idx == 2:
            dlg = StrategyDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                st = self._engine.register_strategy(
                    name=dlg.get_name(), author=dlg.get_author(),
                    description=dlg.get_description(), tags=dlg.get_tags())
                self._set_status("Strategy \\u300c" + st.name + "\\u300d\\u5df2\\u6ce8\\u518c")
                self._refresh_stats()
        elif idx == 3:
            dlg = ModelDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                ml = self._engine.register_model(
                    name=dlg.get_name(), model_type=dlg.get_model_type(),
                    framework=dlg.get_framework(), author=dlg.get_author(),
                    description=dlg.get_description(), tags=dlg.get_tags())
                self._set_status("Model \\u300c" + ml.name + "\\u300d\\u5df2\\u6ce8\\u518c")
                self._refresh_stats()

    def _on_edit(self):
        idx = self._current_tab()
        sel = self._selected_id()
        if not sel:
            self._set_status("\\u8bf7\\u5148\\u9009\\u62e9\\u8981\\u7f16\\u8f91\\u7684\\u6761\\u76ee")
            return
        if idx == 0:
            ds = self._engine.get_dataset(sel)
            if not ds: return
            dlg = DatasetDialog(parent=self, record=ds)
            if dlg.exec() == QDialog.Accepted:
                ds.name = dlg.get_name(); ds.description = dlg.get_description()
                ds.source = dlg.get_source(); ds.start_date = dlg.get_start_date()
                ds.end_date = dlg.get_end_date(); ds.row_count = dlg.get_row_count()
                ds.tags = dlg.get_tags()
                self._engine.update_dataset(ds)
                self._ds_detail.load(sel)
                self._set_status("Dataset \\u300c" + ds.name + "\\u300d\\u5df2\\u66f4\\u65b0")
        elif idx == 1:
            ft = self._engine.get_feature(sel)
            if not ft: return
            dlg = FeatureDialog(parent=self, record=ft)
            if dlg.exec() == QDialog.Accepted:
                ft.name = dlg.get_name(); ft.description = dlg.get_description()
                ft.category = dlg.get_category(); ft.author = dlg.get_author()
                ft.formula = dlg.get_formula(); ft.tags = dlg.get_tags()
                self._engine.update_feature(ft)
                self._ft_detail.load(sel)
                self._set_status("Feature \\u300c" + ft.name + "\\u300d\\u5df2\\u66f4\\u65b0")
        elif idx == 2:
            st = self._engine.get_strategy(sel)
            if not st: return
            dlg = StrategyDialog(parent=self, record=st)
            if dlg.exec() == QDialog.Accepted:
                st.name = dlg.get_name(); st.description = dlg.get_description()
                st.author = dlg.get_author(); st.tags = dlg.get_tags()
                self._engine.update_strategy(st)
                self._st_detail.load(sel)
                self._set_status("Strategy \\u300c" + st.name + "\\u300d\\u5df2\\u66f4\\u65b0")
        elif idx == 3:
            ml = self._engine.get_model(sel)
            if not ml: return
            dlg = ModelDialog(parent=self, record=ml)
            if dlg.exec() == QDialog.Accepted:
                ml.name = dlg.get_name(); ml.description = dlg.get_description()
                ml.model_type = dlg.get_model_type(); ml.framework = dlg.get_framework()
                ml.author = dlg.get_author(); ml.tags = dlg.get_tags()
                self._engine.update_model(ml)
                self._ml_detail.load(sel)
                self._set_status("Model \\u300c" + ml.name + "\\u300d\\u5df2\\u66f4\\u65b0")

    def _on_delete(self):
        idx = self._current_tab()
        sel = self._selected_id()
        if not sel: return
        labels   = {0:"Dataset", 1:"Feature", 2:"Strategy", 3:"Model"}
        getters  = {0:self._engine.get_dataset,    1:self._engine.get_feature,
                    2:self._engine.get_strategy,   3:self._engine.get_model}
        deleters = {0:self._engine.delete_dataset,  1:self._engine.delete_feature,
                    2:self._engine.delete_strategy, 3:self._engine.delete_model}
        obj = getters[idx](sel)
        if not obj: return
        if QMessageBox.question(
            self, "\\u786e\\u8ba4\\u5220\\u9664",
            "\\u5220\\u9664 " + labels[idx] + " \\u300c" + obj.name + "\\u300d\\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            deleters[idx](sel)
            self._set_status(labels[idx] + " \\u300c" + obj.name + "\\u300d\\u5df2\\u5220\\u9664")
            self._refresh_stats()

    def _on_search(self):
        kw = self._search_box.text().strip()
        if not kw: return
        idx = self._current_tab()
        lists = {0:self._ds_list, 1:self._ft_list,
                 2:self._st_list, 3:self._ml_list}
        lists[idx].set_keyword(kw)
        self._set_status("\\u641c\\u7d22\\u300c" + kw + "\\u300d")

    def _on_reset(self):
        self._search_box.clear()
        for lst in (self._ds_list, self._ft_list,
                    self._st_list, self._ml_list):
            lst.set_keyword("")
        self._set_status("\\u5c31\\u7eea")

    def _on_stats_event(self, _=None):
        self._refresh_stats()

    def _refresh_stats(self):
        s = self._engine.stats()
        self._stats_bar.setText(
            "Dataset: "  + str(s.get("datasets", 0))
            + "    Feature: "  + str(s.get("features", 0))
            + "    Strategy: " + str(s.get("strategies", 0))
            + "    Model: "    + str(s.get("models", 0))
            + "    \\u8840\\u7f18\\u8282\\u70b9: " + str(s.get("lineage_nodes", 0)))

    def _set_status(self, msg: str):
        self._status.setText(msg)
"""

# validate by wrapping in dummy class
ast.parse("class _T:\n" + CODE_METHODS)

# append directly — these are already indented as class methods
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE_METHODS)

# final full-file syntax check
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("RegistryTab complete OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
