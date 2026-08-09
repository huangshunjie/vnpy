"""修改 behavior_tab.py 的 _populate_feature_tree 方法，增加量价二级分组"""
import sys

filepath = "vnpy/quant_research/ui/behavior_tab.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 查找方法位置
start_idx = None
for i, line in enumerate(lines):
    if "def _populate_feature_tree(self):" in line:
        start_idx = i
        break

if start_idx is None:
    print("ERROR: _populate_feature_tree not found")
    sys.exit(1)

# 找方法结束（下一个同级或更低缩进的非空行）
base_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
end_idx = start_idx + 1
while end_idx < len(lines):
    line = lines[end_idx]
    stripped = line.rstrip("\n")
    if stripped.strip() == "":
        end_idx += 1
        continue
    current_indent = len(stripped) - len(stripped.lstrip())
    if current_indent <= base_indent:
        break
    end_idx += 1

print(f"Found method at lines {start_idx+1}-{end_idx}, base_indent={base_indent}")

# 新方法
new_method = '''\
    def _populate_feature_tree(self):
        features_by_type = {}
        for name in self.feature_registry.get_feature_names():
            feat = self.feature_registry.get_feature(name)
            if feat:
                features_by_type.setdefault(feat.feature_type, []).append(feat)

        # 量价子分类映射
        _VP_SUBCAT_ORDER = [
            ("vp_grid", "九宫格(量x价)"),
            ("vp_extreme", "极端形态"),
            ("vp_expand", "放量专题"),
            ("vp_shrink", "缩量专题"),
            ("vp_structure", "量能结构"),
            ("vp_divergence", "量价背离"),
            ("vp_gap", "缺口量价"),
            ("vp_whale", "主力行为"),
        ]

        def _vp_subcat(n: str) -> str:
            if n in ("vp_vol_break","vp_vol_stall","vp_vol_crash","vp_vol_retest","vp_vol_pulse"):
                return "vp_expand"
            if n in ("vp_vol_pile","vp_vol_pit","vp_flat_vol_push"):
                return "vp_structure"
            if n.startswith("vp_vol_up_") or n.startswith("vp_vol_flat_") or n.startswith("vp_vol_down_"):
                return "vp_grid"
            if n.startswith("vp_sky_") or n.startswith("vp_ground_") or n.startswith("vp_panic_"):
                return "vp_extreme"
            if n.startswith("vp_shrink_"):
                return "vp_shrink"
            if n.startswith("vp_divergence_"):
                return "vp_divergence"
            if n.startswith("vp_gap_"):
                return "vp_gap"
            if n in ("vp_fake_vol_churn","vp_washout_vol","vp_test_vol"):
                return "vp_whale"
            return ""

        type_labels = {
            KLineFeatureType.PATTERN: "\U0001f56f 形态  Shape",
            KLineFeatureType.VOLUME: "\U0001f4ca 量价  Volume",
            KLineFeatureType.TREND: "\U0001f4c8 趋势  Trend",
            KLineFeatureType.MOMENTUM: "\u26a1 动量  Momentum",
            KLineFeatureType.VOLATILITY: "\U0001f30a 波动  Volatility",
            KLineFeatureType.CROSS_SECTIONAL: "\U0001f3af 综合  Composite",
        }
        for ft, label in type_labels.items():
            features = features_by_type.get(ft, [])
            if not features:
                continue
            parent = QTreeWidgetItem([label])
            parent.setForeground(0, QColor(_YLW))
            color = _FEATURE_COLORS.get(ft, _FG)
            if ft == KLineFeatureType.VOLUME:
                sg: dict = {}
                for feat in sorted(features, key=lambda x: x.name):
                    sg.setdefault(_vp_subcat(feat.name), []).append(feat)
                for sc_key, sc_label in _VP_SUBCAT_ORDER:
                    sc_feats = sg.get(sc_key, [])
                    if not sc_feats:
                        continue
                    sub = QTreeWidgetItem([f"  {sc_label}"])
                    sub.setForeground(0, QColor(_TEAL))
                    for feat in sc_feats:
                        child = QTreeWidgetItem([f"    {feat.display_name}"])
                        child.setData(0, Qt.ItemDataRole.UserRole, feat)
                        child.setForeground(0, QColor(color))
                        child.setToolTip(0, f"{feat.name}\\n{feat.description}")
                        sub.addChild(child)
                    parent.addChild(sub)
                for feat in sg.get("", []):
                    child = QTreeWidgetItem([f"  {feat.display_name}"])
                    child.setData(0, Qt.ItemDataRole.UserRole, feat)
                    child.setForeground(0, QColor(color))
                    child.setToolTip(0, f"{feat.name}\\n{feat.description}")
                    parent.addChild(child)
            else:
                for feat in sorted(features, key=lambda x: x.name):
                    child = QTreeWidgetItem([f"  {feat.display_name}"])
                    child.setData(0, Qt.ItemDataRole.UserRole, feat)
                    child.setForeground(0, QColor(color))
                    child.setToolTip(0, f"{feat.name}\\n{feat.description}")
                    parent.addChild(child)
            self._lib_tree.addTopLevelItem(parent)

'''

new_lines = lines[:start_idx] + [new_method] + lines[end_idx:]

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

# 验证
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()
print(f"_VP_SUBCAT_ORDER count: {content.count('_VP_SUBCAT_ORDER')}")
print(f"_vp_subcat count: {content.count('_vp_subcat')}")
print("SUCCESS")