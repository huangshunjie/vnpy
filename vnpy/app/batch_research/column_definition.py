"""
column_definition.py

ColumnDefinition  —  描述结果表格中一列的全部固有属性。

设计约定：
- 只描述列"是什么"，不描述"当前状态"（visible / order / width 由 ColumnManager 管理）
- frozen=True：不可变，可安全用作字典键或集合元素
- 不依赖 Qt，不依赖数据库，可在任何上下文使用
- 不含 export_only / placeholder 等运行时属性（已废弃）

group 取值：
    "basic"    基本信息（股票代码、名称、行业、状态）
    "return"   收益指标
    "risk"     风险指标
    "trade"    交易指标
    "capital"  资金/成本指标
    "factor"   因子分析指标（LF层）
    "meta"     元信息（任务ID、错误信息等，仅导出）

fmt 取值：
    "pct"    → f"{v:.2f}"        百分比数值，不带 % 符号
    "float1" → f"{v:.1f}"
    "float2" → f"{v:.2f}"
    "float3" → f"{v:.3f}"
    "int"    → str(int(v))
    "money"  → f"{v:,.0f}"      千位分隔符，无小数
    "str"    → str(v)

align 取值：
    "left" / "right" / "center"

color_rule 取值：
    "pnl"      正值绿色文字，负值红色文字，零白色
    "neg_bad"  绝对值越大越红（回撤幅度、波动率）
    None       统一白色，不着色

pinned=True：固定列，不允许用户隐藏（如股票代码、状态）
default_visible=True：默认在 UI 中显示
ui_only=True：只在 UI 显示，不写入任何导出文件
export_always=True：无论用户是否隐藏，始终写入导出文件（meta 组使用）
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnDefinition:
    """
    列元数据描述符。

    实例由 column_registry.py 统一创建并注册，
    外部代码只读不写。
    """

    key:             str            # 对应 BatchBacktestResult 的字段名
    header:          str            # UI 表头显示文字
    group:           str            # 所属功能分组
    width:           int            # 默认列宽（像素）
    fmt:             str            # 格式化类型
    align:           str            # 对齐方式
    sortable:        bool           # 是否支持点击排序
    color_rule:      str | None     # 文字着色规则
    tooltip:         str            # 表头悬浮提示

    cn_header:       str  = ""      # 导出文件列名（空字符串则使用 header）
    default_visible: bool = True    # 是否默认显示
    pinned:          bool = False   # 固定列，不可隐藏
    ui_only:         bool = False   # 仅 UI 显示，不写入导出文件
    export_always:   bool = False   # 始终写入导出文件（即使用户隐藏）

    @property
    def export_header(self) -> str:
        """导出文件实际使用的列名。"""
        return self.cn_header or self.header

    def __repr__(self) -> str:
        vis = "visible" if self.default_visible else "hidden"
        pin = " pinned" if self.pinned else ""
        return (
            f"ColumnDefinition(key={self.key!r}, "
            f"header={self.header!r}, "
            f"group={self.group!r}, "
            f"{vis}{pin})"
        )
