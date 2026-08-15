# -*- coding: utf-8 -*-
from pathlib import Path

cond_path = Path(r'C:\Users\11229\Documents\GitHub\vnpy\vnpy\strategy_condition\core\condition.py')
strategy_path = Path(r'C:\Users\11229\Documents\GitHub\vnpy\vnpy\strategy_condition\core\strategy.py')

cond_text = cond_path.read_text(encoding='utf-8')
start = cond_text.index('@dataclass\nclass Condition:')
end = cond_text.index('\n\n\n# ── 趋势条件', start)
new_cond = '''@dataclass
class Condition:
    """条件叶节点。评估逻辑由 condition_engine.py 负责，此处只做数据建模。"""
    category:  ConditionCategory
    indicator: ConditionIndicator
    params:    Dict[str, Any] = field(default_factory=dict)
    weight:    float          = 1.0
    label:     str            = ""
    enabled:   bool           = True
    interval_scope: str       = "all"

    def __post_init__(self) -> None:
        if not self.interval_scope or self.interval_scope == "all":
            self.interval_scope = INDICATOR_INTERVAL_SCOPE.get(self.indicator, "all")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category":  self.category.value,
            "indicator": self.indicator.value,
            "params":    self.params,
            "weight":    self.weight,
            "label":     self.label,
            "enabled":   self.enabled,
            "interval_scope": self.interval_scope,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Condition":
        indicator = ConditionIndicator(d["indicator"])
        return cls(
            category=  ConditionCategory(d["category"]),
            indicator= indicator,
            params=    d.get("params", {}),
            weight=    d.get("weight", 1.0),
            label=     d.get("label", ""),
            enabled=   d.get("enabled", True),
            interval_scope=d.get("interval_scope", INDICATOR_INTERVAL_SCOPE.get(indicator, "all")),
        )

    def display_name(self) -> str:
        return self.label if self.label else self.indicator.value

    def __repr__(self) -> str:
        return (f"Condition({self.indicator.value}, "
                f"params={self.params}, w={self.weight})")'''
cond_text = cond_text[:start] + new_cond + cond_text[end:]
cond_path.write_text(cond_text, encoding='utf-8')

strategy_text = strategy_path.read_text(encoding='utf-8')
insert_after = '    def sell_condition_count(self) -> int:\n        return self.sell_tree.count_leaves()\n\n'
add_block = '''    def validate_interval_scopes(self) -> List[str]:
        """校验买卖树中的条件周期约束，返回警告列表。"""
        warnings: List[str] = []
        for side_name, tree in (("买入", self.buy_tree), ("卖出", self.sell_tree)):
            has_daily = False
            has_minute = False
            for cond in tree.all_conditions():
                scope = getattr(cond, "interval_scope", "all")
                if scope == "daily":
                    has_daily = True
                elif scope == "minute":
                    has_minute = True
            if has_daily and has_minute:
                warnings.append(f"{side_name}条件同时包含日线和分钟线条件，建议拆成“日线过滤层 + 分钟触发层”。")
        return warnings

    def summary_with_scope(self) -> str:
        warnings = self.validate_interval_scopes()
        base = self.summary()
        if warnings:
            return base + "\n\n[周期校验]\n" + "\n".join(f"- {w}" for w in warnings)
        return base

'''
if insert_after in strategy_text and 'validate_interval_scopes' not in strategy_text:
    strategy_text = strategy_text.replace(insert_after, insert_after + add_block)
strategy_path.write_text(strategy_text, encoding='utf-8')
print('patched condition.py and strategy.py')