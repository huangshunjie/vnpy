"""
live_production/utils/sync_utils.py

订单状态比对工具（Phase 4）。

职责：
  - 定义本地订单状态 vs 交易所状态的比对逻辑
  - 生成不一致报告
  - 提供修复建议类型枚举

❌ 不执行任何撤单 / 补单操作
❌ 不直接访问交易所 API
✔  纯数据比对，输出修复建议供 OrderSyncEngine 决策
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SyncAction(str, Enum):
    """不一致时的修复建议动作。"""
    NONE          = "none"           # 无需操作
    FLAG_PENDING  = "flag_pending"   # 标记为待确认
    MARK_CANCEL   = "mark_cancel"    # 本地标记撤销（交易所已撤）
    MARK_FILL     = "mark_fill"      # 本地标记成交（交易所已成交）
    ALERT_MISMATCH = "alert_mismatch" # 严重不一致，发出告警


class LocalOrderStatus(str, Enum):
    """本地订单状态（从 VeighNa OrderData 映射）。"""
    SUBMITTING  = "submitting"
    NOTTRADED   = "nottraded"
    PARTTRADED  = "parttraded"
    ALLTRADED   = "alltraded"
    CANCELLED   = "cancelled"
    REJECTED    = "rejected"
    UNKNOWN     = "unknown"


class ExchangeOrderStatus(str, Enum):
    """交易所订单状态（从网关回报映射）。"""
    PENDING     = "pending"
    PARTIAL     = "partial"
    FILLED      = "filled"
    CANCELLED   = "cancelled"
    REJECTED    = "rejected"
    UNKNOWN     = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
#  不一致记录
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MismatchRecord:
    """单笔订单不一致记录。"""
    order_id:        str
    vt_orderid:      str              = ""
    local_status:    str              = ""
    exchange_status: str              = ""
    action:          SyncAction       = SyncAction.FLAG_PENDING
    detail:          str              = ""
    detected_at:     datetime         = field(default_factory=datetime.now)
    resolved:        bool             = False
    resolved_at:     datetime | None  = None

    def to_dict(self) -> dict:
        return {
            "order_id":        self.order_id,
            "vt_orderid":      self.vt_orderid,
            "local_status":    self.local_status,
            "exchange_status": self.exchange_status,
            "action":          self.action.value,
            "detail":          self.detail,
            "detected_at":     str(self.detected_at)[:19],
            "resolved":        self.resolved,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  比对函数
# ─────────────────────────────────────────────────────────────────────────────

def compare_order_status(
    order_id:        str,
    local_status:    str,
    exchange_status: str,
    vt_orderid:      str = "",
) -> MismatchRecord | None:
    """
    比对本地状态与交易所状态，返回不一致记录。

    若状态一致则返回 None。

    Parameters
    ----------
    order_id        : 内部订单 ID
    local_status    : 本地状态字符串
    exchange_status : 交易所状态字符串
    vt_orderid      : VeighNa vt_orderid（可选）

    Returns
    -------
    MismatchRecord | None
    """
    ls = local_status.lower()
    es = exchange_status.lower()

    # 状态映射到简化集合
    local_final    = ls in ("alltraded", "cancelled", "rejected")
    exchange_final = es in ("filled", "cancelled", "rejected")

    # 一致判断
    if (
        (ls in ("alltraded",) and es == "filled")
        or (ls == "cancelled"  and es == "cancelled")
        or (ls == "rejected"   and es == "rejected")
        or (ls == "nottraded"  and es == "pending")
        or (ls == "parttraded" and es == "partial")
        or (ls == "submitting" and es == "pending")
    ):
        return None   # 一致，无需处理

    # 确定修复动作
    if es == "filled" and ls not in ("alltraded",):
        action = SyncAction.MARK_FILL
        detail = f"交易所已成交但本地状态为 {ls}"
    elif es == "cancelled" and ls not in ("cancelled",):
        action = SyncAction.MARK_CANCEL
        detail = f"交易所已撤销但本地状态为 {ls}"
    elif exchange_final and not local_final:
        action = SyncAction.ALERT_MISMATCH
        detail = f"交易所终态={es} 本地未终态={ls}，需人工核查"
    elif not exchange_final and local_final:
        action = SyncAction.ALERT_MISMATCH
        detail = f"本地终态={ls} 但交易所未终态={es}，可能延迟"
    else:
        action = SyncAction.FLAG_PENDING
        detail = f"状态不匹配 local={ls} exchange={es}"

    return MismatchRecord(
        order_id        = order_id,
        vt_orderid      = vt_orderid,
        local_status    = local_status,
        exchange_status = exchange_status,
        action          = action,
        detail          = detail,
    )


def batch_compare(
    orders: list[dict],
) -> list[MismatchRecord]:
    """
    批量比对订单状态。

    Parameters
    ----------
    orders : list[dict]，每项包含：
        - order_id        (str)
        - local_status    (str)
        - exchange_status (str)
        - vt_orderid      (str, optional)

    Returns
    -------
    list[MismatchRecord]  仅包含不一致的记录
    """
    result = []
    for o in orders:
        rec = compare_order_status(
            order_id        = o.get("order_id", ""),
            local_status    = o.get("local_status", "unknown"),
            exchange_status = o.get("exchange_status", "unknown"),
            vt_orderid      = o.get("vt_orderid", ""),
        )
        if rec is not None:
            result.append(rec)
    return result
