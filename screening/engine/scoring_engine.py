"""
screening/engine/scoring_engine.py

Stock Scoring Engine — 股票综合评分引擎（Phase 5）。

实现：
  - 将 RankResult 的加权 Z-score 映射为 0~100 综合评分
  - 计算每只股票的排名和因子贡献分解
  - 支持 Top N / Top % / 分位数筛选
  - 输出 ScreeningResult
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..model.factor_score import RankResult
from ..model.screening_result import ScreeningResult, StockScore


def _z_to_score(z: float) -> float:
    """将 Z-score [-3, +3] 线性映射到 [0, 100]。"""
    return max(0.0, min(100.0, 50.0 + z * 100.0 / 6.0))


class ScoringEngine:
    """
    股票综合评分引擎（Phase 5 完整实现）。
    """

    def __init__(
        self,
        log_fn: Optional[Callable[[str], None]] = None,
        main_engine: Any = None,
    ) -> None:
        self._log = log_fn or print
        self._last_result: Optional[ScreeningResult] = None

    # ── 主接口 ────────────────────────────────────────────────────────

    def score_symbols(
        self,
        symbols: List[str],
        rank_result: Optional[RankResult] = None,
        run_id: str = "",
        universe_name: str = "",
        condition_name: str = "",
        factor_config_name: str = "",
    ) -> Optional[ScreeningResult]:
        """
        对通过条件过滤的股票计算综合评分。

        若无 rank_result（因子排序未执行），则生成等分评分作为 fallback。
        """
        if not symbols:
            self._log("[ScoringEngine] 输入股票池为空")
            return None

        self._log(f"[ScoringEngine] 开始评分：{len(symbols)} 只股票")
        t0 = datetime.now()
        run_id = run_id or str(uuid.uuid4())[:8]

        stock_scores: List[StockScore] = []

        if rank_result and rank_result.symbol_composite:
            stock_scores = self._score_from_rank_result(symbols, rank_result)
        else:
            stock_scores = self._score_equal(symbols)

        # 计算百分位
        n = len(stock_scores)
        sorted_by_score = sorted(stock_scores, key=lambda s: s.composite_score, reverse=True)
        for rank, ss in enumerate(sorted_by_score):
            ss.rank = rank + 1
            ss.percentile = 1.0 - rank / max(n - 1, 1)

        elapsed = (datetime.now() - t0).total_seconds()

        self._last_result = ScreeningResult(
            run_id=run_id,
            universe_name=universe_name,
            condition_name=condition_name,
            factor_config_name=factor_config_name,
            stocks=sorted_by_score,
            total_universe=len(symbols),
            total_passed_condition=len(symbols),
            total_passed_risk=len(symbols),
            final_count=len(sorted_by_score),
            generated_at=datetime.now(),
            elapsed_seconds=elapsed,
        )

        self._log(
            f"[ScoringEngine] 评分完成：{len(sorted_by_score)} 只，"
            f"耗时 {elapsed:.2f}s，"
            f"Top1={sorted_by_score[0].symbol if sorted_by_score else 'N/A'}"
            f" score={sorted_by_score[0].composite_score:.1f}" if sorted_by_score else ""
        )
        return self._last_result

    # ── 评分方法 ──────────────────────────────────────────────────────

    def _score_from_rank_result(
        self, symbols: List[str], rank_result: RankResult
    ) -> List[StockScore]:
        """从 RankResult 的综合得分计算 0~100 评分。"""
        composites = rank_result.symbol_composite

        # 收集因子得分（symbol → {factor: z_score}）
        factor_map: Dict[str, Dict[str, float]] = {s: {} for s in symbols}
        for fs in rank_result.scores:
            if fs.symbol in factor_map:
                factor_map[fs.symbol][fs.factor_name] = fs.z_score

        # 将综合 z-score 映射到 0-100
        # 先对综合得分做一次 z-score 标准化再映射，避免数值过小导致分数集中
        vals = [composites.get(s, 0.0) for s in symbols]
        if vals:
            mu = sum(vals) / len(vals)
            std = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5
            if std < 1e-9:
                std = 1.0
        else:
            mu, std = 0.0, 1.0

        result = []
        for sym in symbols:
            raw_composite = composites.get(sym, 0.0)
            z_normalized = (raw_composite - mu) / std
            score = _z_to_score(z_normalized)

            # 因子贡献（各因子 z_score 占总分贡献比例）
            fcontrib: Dict[str, float] = {}
            for fname, fz in factor_map.get(sym, {}).items():
                fcontrib[fname] = round(_z_to_score(fz), 2)

            result.append(StockScore(
                symbol=sym,
                composite_score=round(score, 2),
                factor_contributions=fcontrib,
                passed_condition=True,
                passed_risk_filter=True,
            ))
        return result

    def _score_equal(self, symbols: List[str]) -> List[StockScore]:
        """无因子排序时的 fallback：按字母序分配均匀评分。"""
        n = len(symbols)
        result = []
        for i, sym in enumerate(symbols):
            score = 50.0 + (n / 2 - i) * (50.0 / max(n, 1))
            result.append(StockScore(
                symbol=sym,
                composite_score=round(max(0.0, min(100.0, score)), 2),
                passed_condition=True,
                passed_risk_filter=True,
            ))
        return result

    # ── 查询接口 ──────────────────────────────────────────────────────

    def get_top_n(self, n: int) -> List[StockScore]:
        if self._last_result:
            return self._last_result.get_top_n(n)
        return []

    def get_top_pct(self, pct: float) -> List[StockScore]:
        if self._last_result:
            return self._last_result.get_top_pct(pct)
        return []

    def get_last_result(self) -> Optional[ScreeningResult]:
        return self._last_result

    def summary(self) -> dict:
        if self._last_result:
            return {
                "run_id": self._last_result.run_id,
                "final_count": self._last_result.final_count,
                "generated_at": str(self._last_result.generated_at)[:19],
                "top1": self._last_result.stocks[0].symbol if self._last_result.stocks else "",
            }
        return {"status": "no_result"}
