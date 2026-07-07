"""patch_reg_enums.py — 修正 registry_tab.py 中错误的枚举成员名"""
import pathlib, re

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\registry_tab.py"
)
src = P.read_text(encoding="utf-8")

# DatasetStatus: DRAFT->PENDING, DEPRECATED->OUTDATED, ARCHIVED->ERROR
# (READY stays)
ds_map = {
    "DatasetStatus.DRAFT":       "DatasetStatus.PENDING",
    "DatasetStatus.DEPRECATED":  "DatasetStatus.OUTDATED",
    "DatasetStatus.ARCHIVED":    "DatasetStatus.ERROR",
    "DatasetStatus.DEPRECATED":  "DatasetStatus.OUTDATED",
}
for old, new in ds_map.items():
    src = src.replace(old, new)

# FeatureStatus: VALIDATED->STABLE, ARCHIVED->DEPRECATED (DRAFT, DEPRECATED ok)
# FeatureStatus.VALIDATED -> FeatureStatus.STABLE
ft_map = {
    "FeatureStatus.VALIDATED":  "FeatureStatus.STABLE",
    "FeatureStatus.ARCHIVED":   "FeatureStatus.DEPRECATED",
}
for old, new in ft_map.items():
    src = src.replace(old, new)

# StrategyStatus: DRAFT->IDEA, BACKTESTED->RESEARCH, VALIDATED->VALIDATED(ok),
#   LIVE->PRODUCTION, RETIRED->DEPRECATED
st_map = {
    "StrategyStatus.DRAFT":      "StrategyStatus.IDEA",
    "StrategyStatus.BACKTESTED": "StrategyStatus.RESEARCH",
    "StrategyStatus.LIVE":       "StrategyStatus.PRODUCTION",
    "StrategyStatus.RETIRED":    "StrategyStatus.DEPRECATED",
    "StrategyStatus.ARCHIVED":   "StrategyStatus.DEPRECATED",
}
for old, new in st_map.items():
    src = src.replace(old, new)

# ModelStatus: DRAFT->TRAINING, TRAINED->TRAINING, EVALUATED->EVALUATED(ok),
#   DEPLOYED->DEPLOYED(ok), RETIRED->RETIRED(ok)
ml_map = {
    "ModelStatus.DRAFT":    "ModelStatus.TRAINING",
    "ModelStatus.TRAINED":  "ModelStatus.TRAINING",
}
for old, new in ml_map.items():
    src = src.replace(old, new)

# Also fix the color dict keys in the palette dicts
# DS_STATUS_COLOR
src = src.replace(
    "DS_STATUS_COLOR = {\n    DatasetStatus.DRAFT:       \"#6c757d\",\n    DatasetStatus.READY:       \"#198754\",\n    DatasetStatus.DEPRECATED:  \"#dc3545\",\n    DatasetStatus.ARCHIVED:    \"#adb5bd\",\n}",
    "DS_STATUS_COLOR = {\n    DatasetStatus.PENDING:  \"#6c757d\",\n    DatasetStatus.READY:    \"#198754\",\n    DatasetStatus.OUTDATED: \"#dc3545\",\n    DatasetStatus.ERROR:    \"#adb5bd\",\n}"
)

P.write_text(src, encoding="utf-8")

import ast
ast.parse(src)
print("Enums patched, syntax OK, lines:", len(src.splitlines()))

# Quick sanity check
assert "DatasetStatus.DRAFT" not in src
assert "StrategyStatus.BACKTESTED" not in src
assert "ModelStatus.TRAINED" not in src
print("Sanity checks passed")
