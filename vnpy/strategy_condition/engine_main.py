"""
strategy_condition/engine_main.py
主引擎：初始化并持有所有子引擎，对接 VeighNa MainEngine 生命周期
"""
from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME
from .engine.condition_engine import ConditionEngine
from .engine.rule_engine import RuleEngine
from .engine.scan_engine import ScanEngine


class StrategyConditionEngine(BaseEngine):
    """
    策略条件引擎主入口。

    子引擎组合：
      ConditionEngine  — 叶节点指标计算与评估
      RuleEngine       — 策略 JSON 存取与版本管理
      ScanEngine       — 批量选股与历史回测

    外部依赖（可选注入，不注入时降级运行）：
      candle_buffer    — market_behavior 的 CandleBuffer
      multi_tf         — MultiTFEngine（周线聚合）
      factor_engine    — FactorEngine（K线强度因子）
    """

    def __init__(self, main_engine: MainEngine,
                 event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)

        self._main_engine  = main_engine
        self._event_engine = event_engine

        # 子引擎初始化
        self._condition_engine = ConditionEngine(log_fn=self._log)
        self._rule_engine      = RuleEngine(log_fn=self._log)
        self._scan_engine      = ScanEngine(
            condition_engine=self._condition_engine,
            log_fn=self._log,
        )

        # 立即从磁盘加载已保存的策略（确保重启后策略不丢失）
        self._rule_engine.load_all()

        self._log("StrategyConditionEngine 初始化完成")

    # ── 生命周期 ──────────────────────────────────────────────────────

    def init_engine(self) -> None:
        """由 MainEngine 调用，完成引擎初始化。"""
        self._log("StrategyConditionEngine 启动中...")
        self._try_inject_market_behavior()
        self._rule_engine.load_all()   # 加载历史保存的策略
        self._log("StrategyConditionEngine 就绪")

    def close(self) -> None:
        self._log("StrategyConditionEngine 关闭")

    # ── 外部依赖注入 ──────────────────────────────────────────────────

    def _try_inject_market_behavior(self) -> None:
        """
        尝试从 MainEngine 获取 MarketBehaviorEngine 的子引擎，
        注入到 ConditionEngine。失败时静默降级（不影响基础功能）。
        """
        try:
            mb_engine = self._main_engine.get_engine("MarketBehavior")
            if mb_engine is None:
                self._log("MarketBehaviorEngine 未加载，部分条件（周线/K线强度）不可用")
                return

            # 注入 CandleBuffer
            if hasattr(mb_engine, "_candle_engine"):
                buf = getattr(mb_engine._candle_engine, "_buffer", None)
                if buf:
                    self._condition_engine.set_candle_buffer(buf)
                    self._scan_engine.set_candle_buffer(buf)
                    self._log("CandleBuffer 注入成功")

            # 注入 MultiTFEngine
            if hasattr(mb_engine, "_multi_tf"):
                self._condition_engine.set_multi_tf(mb_engine._multi_tf)
                self._log("MultiTFEngine 注入成功")

            # 注入 FactorEngine
            if hasattr(mb_engine, "_factor_engine"):
                self._condition_engine.set_factor_engine(mb_engine._factor_engine)
                self._log("FactorEngine 注入成功")

        except Exception as e:
            self._log(f"依赖注入异常（非致命）: {e}")

    def inject_candle_buffer(self, buf) -> None:
        """外部手动注入 CandleBuffer（供测试或独立运行使用）"""
        self._condition_engine.set_candle_buffer(buf)
        self._scan_engine.set_candle_buffer(buf)

    def inject_multi_tf(self, mt) -> None:
        self._condition_engine.set_multi_tf(mt)

    def inject_factor_engine(self, fe) -> None:
        self._condition_engine.set_factor_engine(fe)

    # ── 公开接口（供 UI 调用） ────────────────────────────────────────

    @property
    def condition_engine(self) -> ConditionEngine:
        return self._condition_engine

    @property
    def rule_engine(self) -> RuleEngine:
        return self._rule_engine

    @property
    def scan_engine(self) -> ScanEngine:
        return self._scan_engine

    def get_strategies(self):
        """返回所有已注册策略的名称列表"""
        return self._rule_engine.list_names()

    def get_strategy(self, name: str):
        return self._rule_engine.get(name)

    def save_strategy(self, strategy) -> None:
        self._rule_engine.save(strategy, bump_version=False)

    def delete_strategy(self, name: str) -> bool:
        """删除策略（内存注册表 + 磁盘文件）"""
        return self._rule_engine.delete_file(name)

    # ── 工具 ──────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        print(f"[StrategyCondition] {msg}")
        try:
            self.write_log(msg)
        except Exception:
            pass
